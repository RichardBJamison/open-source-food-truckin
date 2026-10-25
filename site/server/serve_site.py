#!/usr/bin/env python3
"""Serve the OSFT website with an email-gated download and a public download counter.

  python3 serve_site.py --root site --port 8930 --data data

Static files come from --root. The program zips (<root>/downloads/osft-*-mac.zip / -win.zip) are never
served directly: the page POSTs /api/download {email, os, lang}, the email is saved to <data>/signups.csv,
the counter in <data>/downloads.json goes up by one, and the reply carries a short-lived /get/<token> link.

  GET  /api/download-count  -> {"total": n}
  POST /api/download        -> {"ok": true, "url": "/get/<token>", "total": n}  or 400 {"ok": false, "error": code}
  GET  /get/<token>         -> the zip as an attachment (link works for 15 minutes)
Every signup is stored in <data>/contacts.db (SQLite, table `contacts`) and still appended to
<data>/signups.csv as a plain export. Existing CSV rows are imported into the db on first start.
Each signup also queues a notification email (default to me@richardbjamison.com) in the `outbox`
table; a background thread sends it, so the download never waits on or fails because of email.
Failed sends are logged and retried with backoff (up to 8 tries).

Email config (env vars, or a git-ignored <data>/mail.json with the same keys):
  OSFT_NOTIFY_TO          recipient (default me@richardbjamison.com)
  OSFT_MAIL_MODE          forwardemail | smtp | off  (default: auto - forwardemail if creds, else smtp, else off)
  FORWARD_EMAIL_USER / FORWARD_EMAIL_PASS / FORWARD_EMAIL_FROM   (same as Open Source Barware's signup)
  OSFT_SMTP_HOST / OSFT_SMTP_PORT (465 SSL or 587 STARTTLS) / OSFT_SMTP_USER / OSFT_SMTP_PASS / OSFT_SMTP_FROM
Standard library only (runs on the macOS system Python 3.9).
"""
import argparse
import base64
import hashlib
import smtplib
import sqlite3
import ssl
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage
import csv
import json
import os
import re
import secrets
import shutil
import threading
import time
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

EMAIL = re.compile(r"^[^@\s<>\"',;]+@[^@\s<>\"',;]+\.[A-Za-z]{2,}$")
TOKEN_SECONDS = 15 * 60
RATE_LIMIT = 20  # downloads per IP per hour
LOCK = threading.Lock()
TOKENS = {}  # token -> (path, expires)
HITS = {}  # ip -> [timestamps]


DEFAULT_TO = "me@richardbjamison.com"
MAIL_KEYS = ("OSFT_NOTIFY_TO", "OSFT_MAIL_MODE", "FORWARD_EMAIL_USER", "FORWARD_EMAIL_PASS", "FORWARD_EMAIL_FROM",
             "OSFT_SMTP_HOST", "OSFT_SMTP_PORT", "OSFT_SMTP_USER", "OSFT_SMTP_PASS", "OSFT_SMTP_FROM")
WAKE = threading.Event()


def log(msg):
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", file=sys.stderr, flush=True)


def mail_config(data_dir):
    cfg = {}
    f = data_dir / "mail.json"
    if f.is_file():
        try:
            cfg.update({k: str(v) for k, v in json.loads(f.read_text()).items() if k in MAIL_KEYS})
        except (OSError, ValueError) as e:
            log(f"mail.json unreadable: {e}")
    cfg.update({k: os.environ[k] for k in MAIL_KEYS if os.environ.get(k)})
    mode = cfg.get("OSFT_MAIL_MODE", "").lower()
    if not mode:
        mode = ("forwardemail" if cfg.get("FORWARD_EMAIL_USER") and cfg.get("FORWARD_EMAIL_PASS")
                else "smtp" if cfg.get("OSFT_SMTP_HOST") else "off")
    cfg["mode"] = mode
    cfg["to"] = cfg.get("OSFT_NOTIFY_TO") or DEFAULT_TO
    return cfg


def db_connect(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(data_dir / "contacts.db"), timeout=10)
    con.executescript("""
      CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, time_utc TEXT, email TEXT, os TEXT, lang TEXT,
        country TEXT, file TEXT, ip_hash TEXT, user_agent TEXT, source TEXT DEFAULT 'download');
      CREATE INDEX IF NOT EXISTS contacts_email ON contacts(email);
      CREATE TABLE IF NOT EXISTS outbox (id INTEGER PRIMARY KEY, contact_id INTEGER, to_addr TEXT, subject TEXT,
        body TEXT, status TEXT DEFAULT 'pending', tries INTEGER DEFAULT 0, next_try REAL DEFAULT 0,
        last_error TEXT, sent_utc TEXT);
    """)
    return con


def migrate_csv(data_dir):
    con = db_connect(data_dir)
    csvp = data_dir / "signups.csv"
    if csvp.is_file() and not con.execute("SELECT 1 FROM contacts LIMIT 1").fetchone():
        with csvp.open(newline="", encoding="utf-8") as f:
            rows = [(r.get("time_utc"), r.get("email"), r.get("os"), r.get("lang"), r.get("country"), r.get("file"))
                    for r in csv.DictReader(f)]
        with con:
            con.executemany("INSERT INTO contacts(time_utc,email,os,lang,country,file,source) VALUES (?,?,?,?,?,?,'csv-import')", rows)
        log(f"imported {len(rows)} existing signups.csv rows into contacts.db")
    con.close()


def send_one(cfg, to, subject, body):
    if cfg["mode"] == "forwardemail":
        user, pw = cfg["FORWARD_EMAIL_USER"], cfg["FORWARD_EMAIL_PASS"]
        data = urllib.parse.urlencode({"from": cfg.get("FORWARD_EMAIL_FROM") or user, "to": to,
                                       "subject": subject, "text": body}).encode()
        req = urllib.request.Request("https://api.forwardemail.net/v1/emails", data=data, method="POST")
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode())
        with urllib.request.urlopen(req, timeout=20) as r:
            if r.status >= 300:
                raise RuntimeError(f"forwardemail HTTP {r.status}")
        return
    if cfg["mode"] == "smtp":
        host, port = cfg["OSFT_SMTP_HOST"], int(cfg.get("OSFT_SMTP_PORT") or 465)
        msg = EmailMessage()
        msg["From"] = cfg.get("OSFT_SMTP_FROM") or cfg.get("OSFT_SMTP_USER")
        msg["To"], msg["Subject"] = to, subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) if port == 465 else smtplib.SMTP(host, port, timeout=20)
        with s:
            if port != 465:
                s.starttls(context=ctx)
            if cfg.get("OSFT_SMTP_USER"):
                s.login(cfg["OSFT_SMTP_USER"], cfg.get("OSFT_SMTP_PASS", ""))
            s.send_message(msg)
        return
    raise RuntimeError("mail disabled (no credentials configured)")


def mailer(data_dir):
    while True:
        WAKE.wait(60)
        WAKE.clear()
        try:
            cfg = mail_config(data_dir)
            if cfg["mode"] == "off":
                continue  # stays pending until credentials are added
            con = db_connect(data_dir)
            rows = con.execute("SELECT id,to_addr,subject,body,tries FROM outbox WHERE status='pending' AND next_try<=? "
                               "ORDER BY id LIMIT 20", (time.time(),)).fetchall()
            for oid, to, subj, body, tries in rows:
                try:
                    send_one(cfg, to, subj, body)
                    with con:
                        con.execute("UPDATE outbox SET status='sent',tries=?,sent_utc=?,last_error=NULL WHERE id=?",
                                    (tries + 1, datetime.now(timezone.utc).isoformat(timespec="seconds"), oid))
                    log(f"notify email {oid} sent to {to}")
                except Exception as e:  # noqa: BLE001 - never let email break the site
                    t = tries + 1
                    with con:
                        con.execute("UPDATE outbox SET tries=?,next_try=?,last_error=?,status=? WHERE id=?",
                                    (t, time.time() + min(3600, 60 * 2 ** t), str(e)[:300],
                                     "failed" if t >= 8 else "pending", oid))
                    log(f"notify email {oid} failed (try {t}): {e}")
            con.close()
        except Exception as e:  # noqa: BLE001
            log(f"mailer error: {e}")


class Handler(SimpleHTTPRequestHandler):
    data_dir: Path = Path("data")

    # -- helpers -------------------------------------------------------------------------------
    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def client_ip(self):
        return (self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or self.client_address[0])

    def zip_for(self, kind):
        files = sorted(Path(self.directory, "downloads").glob(f"osft-*-{kind}.zip"), key=lambda p: p.stat().st_mtime)
        return files[-1] if files else None

    def count_path(self):
        return self.data_dir / "downloads.json"

    def read_total(self):
        try:
            return int(json.loads(self.count_path().read_text())["total"])
        except (OSError, ValueError, KeyError):
            return 0

    # -- routes --------------------------------------------------------------------------------
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/download-count":
            return self.send_json(200, {"total": self.read_total()})
        if path.startswith("/get/"):
            return self.serve_token(path[5:])
        if path.startswith("/downloads/") and path.endswith((".zip", ".tgz")):
            self.send_response(302)
            self.send_header("Location", "/download/#get-program")
            self.end_headers()
            return
        return super().do_GET()

    def do_HEAD(self):
        path = self.path.split("?", 1)[0]
        if path.startswith(("/api/", "/get/")) or (path.startswith("/downloads/") and path.endswith((".zip", ".tgz"))):
            self.send_response(405)
            self.end_headers()
            return
        return super().do_HEAD()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/download":
            return self.send_json(404, {"ok": False, "error": "not_found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 4096:
                raise ValueError
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return self.send_json(400, {"ok": False, "error": "bad_request"})
        email = str(body.get("email", "")).strip()
        kind = str(body.get("os", ""))
        lang = "es" if body.get("lang") == "es" else "en"
        if body.get("website"):  # honeypot field a person never sees
            return self.send_json(200, {"ok": True, "url": "/download/", "total": self.read_total()})
        if len(email) > 254 or not EMAIL.match(email):
            return self.send_json(400, {"ok": False, "error": "email"})
        if kind not in ("mac", "win"):
            return self.send_json(400, {"ok": False, "error": "os"})
        zp = self.zip_for(kind)
        if not zp:
            return self.send_json(503, {"ok": False, "error": "unavailable"})
        ip, now = self.client_ip(), time.time()
        with LOCK:
            recent = [t for t in HITS.get(ip, []) if now - t < 3600]
            if len(recent) >= RATE_LIMIT:
                return self.send_json(429, {"ok": False, "error": "busy"})
            HITS[ip] = recent + [now]
            for t in [t for t, (_, exp) in TOKENS.items() if exp < now]:
                del TOKENS[t]
            self.data_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            country = self.headers.get("CF-IPCountry", "")
            signups = self.data_dir / "signups.csv"
            new = not signups.exists()
            with signups.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["time_utc", "email", "os", "lang", "country", "file"])
                w.writerow([ts, email, kind, lang, country, zp.name])
            try:
                con = db_connect(self.data_dir)
                ua = (self.headers.get("User-Agent") or "")[:300]
                iph = hashlib.sha256(("osft:" + ip).encode()).hexdigest()[:16]
                with con:
                    cid = con.execute("INSERT INTO contacts(time_utc,email,os,lang,country,file,ip_hash,user_agent) "
                                      "VALUES (?,?,?,?,?,?,?,?)", (ts, email, kind, lang, country, zp.name, iph, ua)).lastrowid
                    cfg = mail_config(self.data_dir)
                    con.execute("INSERT INTO outbox(contact_id,to_addr,subject,body) VALUES (?,?,?,?)", (
                        cid, cfg["to"], f"OSFT download signup: {email}",
                        f"New Open Source Food Truckin' download signup\n\nEmail: {email}\nOS: {kind}\n"
                        f"Language: {lang}\nCountry: {country or '-'}\nFile: {zp.name}\nTime (UTC): {ts}\n"
                        f"Contact id: {cid} (saved in contacts.db)\n"))
                con.close()
                WAKE.set()
            except sqlite3.Error as e:
                log(f"contacts.db write failed (CSV still has it): {e}")
            total = self.read_total() + 1
            tmp = self.count_path().with_suffix(".tmp")
            tmp.write_text(json.dumps({"total": total}))
            os.replace(tmp, self.count_path())
            token = secrets.token_urlsafe(18)
            TOKENS[token] = (zp, now + TOKEN_SECONDS)
        return self.send_json(200, {"ok": True, "url": f"/get/{token}", "total": total})

    def serve_token(self, token):
        with LOCK:
            hit = TOKENS.get(token)
        if not hit or hit[1] < time.time() or not hit[0].is_file():
            self.send_response(302)
            self.send_header("Location", "/download/?expired=1#get-program")
            self.end_headers()
            return
        zp = hit[0]
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{zp.name}"')
        self.send_header("Content-Length", str(zp.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with zp.open("rb") as f:
            shutil.copyfileobj(f, self.wfile)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--bind", default="127.0.0.1")
    a = ap.parse_args()
    Handler.data_dir = Path(a.data).resolve()
    migrate_csv(Handler.data_dir)
    threading.Thread(target=mailer, args=(Handler.data_dir,), daemon=True).start()
    WAKE.set()
    log(f"notify mail mode: {mail_config(Handler.data_dir)['mode']} -> {mail_config(Handler.data_dir)['to']}")
    handler = partial(Handler, directory=str(Path(a.root).resolve()))
    print(f"OSFT site {a.root} -> http://{a.bind}:{a.port}/  (data: {Handler.data_dir})", flush=True)
    ThreadingHTTPServer((a.bind, a.port), handler).serve_forever()


if __name__ == "__main__":
    main()
