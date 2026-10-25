"""First-party, privacy-friendly analytics for the OSFT site (no cookies required, no raw IPs).

Stored in <data>/analytics.db. Visitors are a daily-salted SHA-256 of IP+User-Agent (salt rotates each
day in America/New_York and is never stored with the rows), so a visitor can't be followed across days.
Hourly buckets are America/New_York. Dashboard: /admin/stats?k=<token from <data>/admin.json>.
"""
import csv, hashlib, html, io, json, re, secrets, sqlite3, threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
BOT = re.compile(r"bot|crawl|spider|slurp|preview|monitor|curl|wget|python|httpx|go-http|headless|lighthouse|facebookexternalhit|bingpreview|scan", re.I)
EVENTS = {"pageview", "download_click", "email_submit", "popup_open", "download", "email_saved"}
_lock = threading.Lock()


class Analytics:
    def __init__(self, data_dir: Path):
        self.dir = Path(data_dir)
        self.db = self.dir / "analytics.db"
        with self.conn() as c:
            c.execute("""create table if not exists events(id integer primary key, ts_utc text, day text, hour text,
                event text, path text, ref text, lang text, country text, device text, visitor text,
                utm_source text, utm_medium text, utm_campaign text, os text, test integer default 0)""")
            c.execute("create index if not exists ev_hour on events(hour)")
        adm = self.dir / "admin.json"
        if not adm.exists():
            adm.write_text(json.dumps({"stats_token": secrets.token_urlsafe(32)}))
            adm.chmod(0o600)
        self.token = json.loads(adm.read_text())["stats_token"]

    def conn(self):
        return sqlite3.connect(self.db, timeout=10)

    @staticmethod
    def device(ua):
        u = ua.lower()
        if "ipad" in u or "tablet" in u: return "tablet"
        if "mobi" in u or "iphone" in u or "android" in u: return "mobile"
        return "desktop"

    def visitor(self, ip, ua, day):
        salt = hashlib.sha256(f"{self.token}:{day}".encode()).hexdigest()
        return hashlib.sha256(f"{salt}|{ip}|{ua}".encode()).hexdigest()[:20]

    def record(self, event, *, ip, ua, path="", ref="", lang="", country="", os="", utm=None, test=False):
        if event not in EVENTS or BOT.search(ua or "") or not ua:
            return False
        now = datetime.now(timezone.utc); loc = now.astimezone(NY)
        day = loc.strftime("%Y-%m-%d")
        utm = utm or {}
        refhost = urlparse(ref).netloc if ref else ""
        if refhost.endswith("osfoodtrucking.com"): refhost = "(internal)"
        row = (now.isoformat(timespec="seconds"), day, loc.strftime("%Y-%m-%d %H:00"), event, (path or "")[:200],
               refhost[:120], (lang or "")[:5], (country or "")[:3], self.device(ua), self.visitor(ip, ua, day),
               str(utm.get("utm_source", ""))[:60], str(utm.get("utm_medium", ""))[:60], str(utm.get("utm_campaign", ""))[:60],
               (os or "")[:5], 1 if test else 0)
        with _lock, self.conn() as c:
            c.execute("insert into events(ts_utc,day,hour,event,path,ref,lang,country,device,visitor,utm_source,utm_medium,utm_campaign,os,test) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        return True

    # ---------------- dashboard ----------------
    def rows(self, sql, args=()):
        with self.conn() as c:
            return c.execute(sql, args).fetchall()

    def csv(self, days=30):
        since = (datetime.now(NY) - timedelta(days=days)).strftime("%Y-%m-%d")
        out = io.StringIO(); w = csv.writer(out)
        w.writerow(["hour_ny", "pageviews", "visitors", "email_submits", "downloads", "downloads_mac", "downloads_win", "popup_opens"])
        for r in self.rows("""select hour, sum(event='pageview'), count(distinct case when event='pageview' then visitor end),
              sum(event='email_saved'), sum(event='download'), sum(event='download' and os='mac'), sum(event='download' and os='win'),
              sum(event='popup_open') from events where test=0 and day>=? group by hour order by hour""", (since,)):
            w.writerow(r)
        return out.getvalue()

    def dashboard(self, k):
        now = datetime.now(NY); today = now.strftime("%Y-%m-%d"); week = (now - timedelta(days=6)).strftime("%Y-%m-%d")
        e = html.escape
        def table(title, head, rows):
            h = "".join(f"<th>{e(x)}</th>" for x in head)
            b = "".join("<tr>" + "".join(f"<td>{e(str(v))}</td>" for v in r) + "</tr>" for r in rows) or f"<tr><td colspan={len(head)}>No data yet</td></tr>"
            return f"<h2>{e(title)}</h2><table><tr>{h}</tr>{b}</table>"
        def tot(day_from):
            return self.rows("""select sum(event='pageview'), count(distinct case when event='pageview' then visitor end),
                sum(event='email_saved'), sum(event='download'), sum(event='download' and os='mac'), sum(event='download' and os='win')
                from events where test=0 and day>=?""", (day_from,))[0]
        alltime = self.rows("select sum(event='pageview'), count(distinct visitor||day), sum(event='email_saved'), sum(event='download'), sum(event='download' and os='mac'), sum(event='download' and os='win') from events where test=0")[0]
        hours = {r[0]: r for r in self.rows("""select hour, sum(event='pageview'), count(distinct case when event='pageview' then visitor end),
            sum(event='email_saved'), sum(event='download') from events where test=0 and day=? group by hour""", (today,))}
        mx = max([r[1] for r in hours.values()] + [1])
        bars = ""
        for h in range(24):
            key = f"{today} {h:02d}:00"; r = hours.get(key, (key, 0, 0, 0, 0))
            bars += (f"<div class=bar title='{h:02d}:00 — {r[1]} views, {r[2]} visitors, {r[4]} downloads'>"
                     f"<i style='height:{int(100 * r[1] / mx)}%'></i><b>{r[4] or ''}</b><span>{h:02d}</span></div>")
        week_hours = self.rows("""select hour, sum(event='pageview'), count(distinct case when event='pageview' then visitor end),
            sum(event='email_saved'), sum(event='download'), sum(event='download' and os='mac'), sum(event='download' and os='win')
            from events where test=0 and day>=? group by hour having count(*)>0 order by hour desc""", (week,))
        days = self.rows("""select day, sum(event='pageview'), count(distinct case when event='pageview' then visitor end),
            sum(event='email_saved'), sum(event='download') from events where test=0 and day>=? group by day order by day desc""", (week,))
        def top(col):
            return self.rows(f"select coalesce(nullif({col},''),'(none)'), count(*) from events where test=0 and event='pageview' and day>=? group by 1 order by 2 desc limit 15", (week,))
        utm = self.rows("select utm_source, utm_medium, utm_campaign, count(*) from events where test=0 and day>=? and utm_source!='' group by 1,2,3 order by 4 desc limit 20", (week,))
        H = ["views", "visitors", "emails", "downloads", "mac", "win"]
        t, w = tot(today), tot(week)
        body = (f"<h1>OSFT site analytics</h1><p class=m>Times are America/New_York (ET). Updated {now:%b %d, %I:%M %p} ET. "
                f"<a href='/admin/stats.csv?k={e(k)}'>CSV export (hourly, 30 days)</a></p>"
                + table("Totals", ["range"] + H, [["Today", *t], ["Last 7 days", *w], ["All time", *alltime]])
                + f"<h2>Today by hour (bars = page views, number = downloads)</h2><div class=bars>{bars}</div>"
                + table("Last 7 days by hour", ["hour (ET)"] + H, week_hours)
                + table("Last 7 days by day", ["day", "views", "visitors", "emails", "downloads"], days)
                + table("Top pages (7d)", ["path", "views"], top("path"))
                + table("Referrers (7d)", ["site", "views"], top("ref"))
                + table("Countries (7d)", ["country", "views"], top("country"))
                + table("Devices (7d)", ["device", "views"], top("device"))
                + table("Language (7d)", ["lang", "views"], top("lang"))
                + table("Campaigns / UTM (7d)", ["source", "medium", "campaign", "views"], utm))
        css = ("body{background:#0b1230;color:#f4efe6;font:15px/1.5 system-ui;margin:0;padding:1.5rem;max-width:1100px;margin:auto}"
               "h1{color:#ff9a3c}h2{color:#3ff0e0;font-size:1.05rem;margin-top:1.6rem}.m{color:#aab}a{color:#3ff0e0}"
               "table{border-collapse:collapse;width:100%;background:#101a3a}td,th{border:1px solid #24305e;padding:.3rem .5rem;text-align:left}"
               ".bars{display:flex;gap:3px;height:160px;align-items:flex-end;background:#101a3a;padding:.5rem}"
               ".bar{flex:1;height:100%;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;font-size:.7rem}"
               ".bar i{display:block;width:100%;background:#ff7a1a;min-height:1px}.bar b{color:#3ff0e0}.bar span{color:#889}")
        return f"<!doctype html><meta charset=utf-8><meta name=robots content=noindex><title>OSFT analytics</title><style>{css}</style>{body}"

    def purge_test(self):
        with _lock, self.conn() as c:
            return c.execute("delete from events where test=1").rowcount
