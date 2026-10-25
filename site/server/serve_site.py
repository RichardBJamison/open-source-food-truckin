#!/usr/bin/env python3
"""Serve the OSFT website with an email-gated download and a public download counter.

  python3 serve_site.py --root site --port 8930 --data data

Static files come from --root. The program zips (<root>/downloads/osft-*-mac.zip / -win.zip) are never
served directly: the page POSTs /api/download {email, os, lang}, the email is saved to <data>/signups.csv,
the counter in <data>/downloads.json goes up by one, and the reply carries a short-lived /get/<token> link.

  GET  /api/download-count  -> {"total": n}
  POST /api/download        -> {"ok": true, "url": "/get/<token>", "total": n}  or 400 {"ok": false, "error": code}
  GET  /get/<token>         -> the zip as an attachment (link works for 15 minutes)
Standard library only (runs on the macOS system Python 3.9).
"""
import argparse
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
            signups = self.data_dir / "signups.csv"
            new = not signups.exists()
            with signups.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(["time_utc", "email", "os", "lang", "country", "file"])
                w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), email, kind, lang,
                            self.headers.get("CF-IPCountry", ""), zp.name])
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
    handler = partial(Handler, directory=str(Path(a.root).resolve()))
    print(f"OSFT site {a.root} -> http://{a.bind}:{a.port}/  (data: {Handler.data_dir})", flush=True)
    ThreadingHTTPServer((a.bind, a.port), handler).serve_forever()


if __name__ == "__main__":
    main()
