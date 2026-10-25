"""v1.1 browser walk-through of the new first run (OSBW order) + AI settings, AI shelf, AI invoice — AI is a LOCAL MOCK.
Usage: python tests/e2e_v11.py BASE OUTDIR TAG WIDTH HEIGHT [pin]"""
import sys, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from playwright.sync_api import sync_playwright

BASE, OUT, TAG, W, H = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
USE_PIN = "pin" in sys.argv[6:]
errors, calls = [], []
INVOICE = {"vendor": "Restaurant Depot", "invoice_no": "RD-4471", "date": "2026-10-22", "total": 158.4,
           "lines": [{"description": "Chicken thigh boneless 40lb", "qty": 2, "unit": "cs", "unit_cost": 52.0, "total": 104.0},
                     {"description": "Crema mexicana 1gal", "qty": 4, "unit": "tub", "unit_cost": 9.6, "total": 38.4},
                     {"description": "Takis Fuego 46ct", "qty": 1, "unit": "cs", "unit_cost": 16.0, "total": 16.0}]}
SHELF = {"items": [{"name": "Sour cream", "qty": 3, "unit": "tub", "category": "Dairy"},
                   {"name": "Queso fresco", "qty": 5, "unit": "lb", "category": "Dairy"}]}

class Mock(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        txt = json.dumps(body["messages"]).lower()
        calls.append(txt[:80])
        c = INVOICE if "invoice" in txt else SHELF if ("shelf" in txt or "section" in txt) else {"ok": True}
        out = json.dumps({"choices": [{"message": {"content": json.dumps(c)}}], "model": "mock-vision"}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

srv = HTTPServer(("127.0.0.1", 0), Mock); threading.Thread(target=srv.serve_forever, daemon=True).start()
MOCK = f"http://127.0.0.1:{srv.server_port}/v1"
IMG = "static/img/seal.webp"

def shot(page, name):
    page.wait_for_timeout(350); page.evaluate("window.scrollTo(0, 0)"); page.wait_for_timeout(100)
    page.screenshot(path=f"{OUT}/{TAG}-{name}.png", full_page=True)
    sw = page.evaluate("document.documentElement.scrollWidth")
    if sw > W + 2: errors.append(f"overflow {name}: scrollWidth {sw} > {W}")

def next_section(page, n):
    page.click("#walk-next"); page.wait_for_function(f"document.body.innerText.includes('{n} of') || document.body.innerText.includes('{n} de')")

def check(cond, msg):
    if not cond: errors.append("FAIL " + msg)

with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_context(viewport={"width": W, "height": H}).new_page()
    page.on("pageerror", lambda e: errors.append(f"pageerror {e}"))
    page.on("console", lambda m: m.type == "error" and "409" not in m.text and errors.append(f"console {m.text}"))
    try:
        page.goto(BASE); page.wait_for_selector("#ob-start")
        # Welcome: two passes + optional AI connect (OSBW welcome)
        check(page.locator(".ob-pass-card").count() == 2, "welcome shows two passes")
        shot(page, "01-welcome")
        page.click("#ob-ai summary"); page.select_option("#ob-ai-provider", "custom")
        page.fill("#ob-ai-url", MOCK); page.fill("#ob-ai-model", "mock-vision"); page.fill("#ob-ai-key", "sk-test-e2e-0000")
        page.click("#ob-ai-connect"); page.wait_for_selector("#ob-ai .alert-ok"); shot(page, "02-welcome-ai-connected")
        page.click("#ob-start"); page.wait_for_selector("#ob-name")
        # Step 1 Your truck
        page.fill("#ob-name", "Tacos El Gordo Test"); page.check("[name=ob-cyc][value='7']"); shot(page, "03-business")
        page.click("#ob-biz button[type=submit]"); page.wait_for_selector("#sec-list")
        # Step 2 Sections: rename, add suggestion, add custom, reorder, delete
        page.fill("#sec-name-0", "Big cooler")
        page.locator("[data-sec-sugg]").filter(has_text="Lowboy").first.click()
        page.fill("#sec-new", "Salsa station"); page.click("#sec-add")
        n = page.locator(".sec-row").count()
        page.click(f"[data-sec-up='{n-1}']")
        for _ in range(10):  # drop legacy sections we don't use (keep Big cooler, Freezer, Lowboy, Salsa station)
            names = [page.input_value(f"#sec-name-{i}") for i in range(page.locator(".sec-row").count())]
            drop = [i for i, x in enumerate(names) if x in ("Dry storage", "Prep", "Outside", "Window", "Commissary")]
            if not drop: break
            page.click(f"[data-sec-del='{drop[0]}']")
        shot(page, "04-sections")
        page.click("#sec-save"); page.wait_for_selector("#walk-text")
        secs = page.evaluate("fetch('/api/sections').then(r=>r.json()).then(d=>d.sections.map(s=>s.name))")
        check(secs[0] == "Big cooler" and "Salsa station" in secs and "Lowboy (under-counter)" in secs, f"sections saved {secs}")
        # Step 3 Walk — section 1 by typed voice
        page.fill("#walk-text", "chicken thighs 3 cases, crema 2 tubs, limes 12"); shot(page, "05-walk-cooler")
        page.click("#walk-check"); page.wait_for_selector("#walk-apply"); shot(page, "06-walk-check")
        page.click("#walk-apply"); page.wait_for_selector(".chip.static")
        # section 2 — AI tidy of a messy walk (proposal only)
        next_section(page, 2)
        page.fill("#walk-text", "uh frozen... no wait, sour cream like three, and um queso fresco five pounds")
        page.click("#walk-tidy"); page.wait_for_selector("#walk-apply")
        before = page.evaluate("fetch('/api/items').then(r=>r.json()).then(d=>d.items.length)")
        check(before == 3, f"AI tidy did not save anything (items={before})")
        shot(page, "07-walk-ai-tidy"); page.click("#walk-apply"); page.wait_for_selector(".chip.static")
        # section 3 — AI shelf photo
        next_section(page, 3)
        page.set_input_files("#walk-photo", IMG); page.wait_for_selector("#walk-apply"); shot(page, "08-walk-ai-photo")
        page.uncheck("[data-wp-keep='1']"); page.click("#walk-apply"); page.wait_for_selector(".chip.static")
        next_section(page, 4)
        page.fill("#walk-text", "salsa roja 4 quarts, salsa verde 3 quarts"); page.click("#walk-check"); page.wait_for_selector("#walk-apply"); page.click("#walk-apply")
        page.wait_for_selector(".chip.static"); shot(page, "09-walk-last")
        page.click("#walk-next"); page.wait_for_selector("#rc-confirm"); page.click("#rc-confirm"); page.wait_for_selector("#rv-save")
        # Step 4 Review & approve map
        shot(page, "10-review"); page.click("#rv-save"); page.wait_for_selector("#fc-save")
        # Step 5 First count, per section
        shot(page, "11-count-1")
        page.fill("#fc-text", "chicken thighs 2, limes 10"); page.click("#fc-hear"); page.wait_for_timeout(600); shot(page, "12-count-voice")
        for _ in range(8):
            page.click("#fc-save"); page.wait_for_timeout(700)
            if page.locator("#ob-acct, #ob-next").count(): break
        shot(page, "13-account")
        if USE_PIN:
            page.fill("#ob-uname", "Richard P"); page.fill("#ob-pin", "123456"); page.fill("#ob-pin2", "123456"); page.click("#ob-acct button[type=submit]")
        else:
            page.click("#ob-skip")
        page.wait_for_selector("#ob-finish"); shot(page, "14-done")
        page.click("#ob-finish"); page.wait_for_timeout(1200); shot(page, "15-home")
        st = page.evaluate("fetch('/api/items').then(r=>r.json())")["items"]
        byname = {i["name"].lower(): i for i in st}
        check(len(st) == 7, f"7 products built (sour cream merged), got {len(st)}: {sorted(byname)}")
        sess = page.evaluate("fetch('/api/counts').then(r=>r.ok?r.json():{}).catch(()=>({}))")
        # Settings views
        for v in ("sections", "ai", "setup"):
            page.evaluate(f"OSFT.showView('{v}')"); page.wait_for_timeout(700); shot(page, f"20-settings-{v}")
        # Invoice: upload + AI read → review → match/new → save
        page.evaluate("OSFT.showView('invoice')"); page.wait_for_selector("#inv11-files", state="attached")
        page.set_input_files("#inv11-files", IMG); page.wait_for_selector("#inv11-read"); shot(page, "21-invoice-attached")
        page.click("#inv11-read"); page.wait_for_selector("#inv11-save"); shot(page, "22-invoice-review")
        check(page.input_value("#inv11-vendor") == "Restaurant Depot", "vendor read")
        page.click("#inv11-save"); page.wait_for_selector("#inv11-ok:not(.hidden)"); shot(page, "23-invoice-saved")
        rec = page.evaluate("fetch('/api/receives').then(r=>r.json())")
        rl = rec.get("receives", rec if isinstance(rec, list) else [])
        check(len(rl) >= 3 and all(r.get("photos") for r in rl[:3]), f"3 receives with the invoice file attached ({len(rl)})")
        items2 = page.evaluate("fetch('/api/items').then(r=>r.json())")["items"]
        check(any("takis" in i["name"].lower() for i in items2), "new product created from invoice line")
        # AI off → no AI buttons, upload still attaches
        page.evaluate("fetch('/api/ai/settings',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:false})})")
        n0 = len(calls)
        page.evaluate("OSFT.showView('invoice')"); page.wait_for_selector("#inv11-files", state="attached")
        page.set_input_files("#inv11-files", IMG); page.wait_for_timeout(800)
        check(page.locator("#inv11-read").count() == 0, "no AI read button when AI off"); shot(page, "24-invoice-ai-off")
        check(len(calls) == n0, "AI never called while off")
        # Spanish
        page.locator(".locale-switch [data-locale=es]:visible").first.click(); page.wait_for_timeout(800)
        page.evaluate("OSFT.showView('sections')"); page.wait_for_timeout(700); shot(page, "30-sections-es")

    except Exception as e:
        errors.append(f'EXCEPTION {str(e)[:300]}'); page.screenshot(path=f'{OUT}/{TAG}-ZZ-fail.png', full_page=True)
    b.close()
print(f"mock AI calls: {len(calls)}")
print("\n".join(errors) or "ALL CHECKS PASSED, NO JS ERRORS")
