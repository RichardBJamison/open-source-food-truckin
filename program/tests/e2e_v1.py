"""Browser walk-through for v1.0-beta. Usage: python tests/e2e_v1.py http://127.0.0.1:5098 OUTDIR"""
import sys, re
from playwright.sync_api import sync_playwright
BASE, OUT = sys.argv[1], sys.argv[2]
errors = []

def shot(page, name):
    page.wait_for_timeout(350)
    page.screenshot(path=f"{OUT}/{name}.png", full_page=True)
    sw = page.evaluate("document.documentElement.scrollWidth"); vw = page.viewport_size["width"]
    if sw > vw + 2: errors.append(f"overflow {name}: scrollWidth {sw} > {vw}")

def go(page, view):
    page.evaluate(f"OSFT.showView('{view}')"); page.wait_for_timeout(600)

def run(pw, w, h, tag, fresh):
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": w, "height": h}, permissions=[])
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(f"[{tag}] pageerror {e}"))
    page.on("console", lambda m: m.type == "error" and errors.append(f"[{tag}] console {m.text}"))
    page.goto(BASE); page.wait_for_timeout(1200)
    if fresh:
        shot(page, f"{tag}-01-welcome")
        page.click("#ob-start"); page.wait_for_selector("#ob-name")
        page.fill("#ob-name", "Tacos El Gordo Test"); shot(page, f"{tag}-02-business")
        page.click("#ob-biz button[type=submit]"); page.wait_for_selector("#sec-save")
        page.click("#sec-save"); page.wait_for_selector("#walk-text")
        page.fill("#walk-text", "3 cases chicken thighs, 2 tubs crema, 12 limes, 4 cases corn tortillas, 2 bags rice")
        shot(page, f"{tag}-04-walk")
        page.click("#walk-check"); page.wait_for_selector("#walk-apply"); shot(page, f"{tag}-05-walk-review")
        page.click("#walk-apply"); page.wait_for_selector(".chip.static")
        for _ in range(10):
            page.click("#walk-next"); page.wait_for_timeout(500)
            if page.locator("#rc-confirm").count():
                page.click("#rc-confirm"); page.wait_for_selector("#rv-save")
            if page.locator("#rv-save").count(): break
        shot(page, f"{tag}-06-review")
        page.click("#rv-save"); page.wait_for_selector("#fc-save")
        for _ in range(10):
            page.click("#fc-save"); page.wait_for_timeout(600)
            if page.locator("#ob-acct").count(): break
        page.fill("#ob-uname", "Richard P"); page.fill("#ob-pin", "123456"); page.fill("#ob-pin2", "123456")
        shot(page, f"{tag}-03-account")
        page.click("#ob-acct button[type=submit]")
        page.wait_for_selector("#ob-finish"); shot(page, f"{tag}-07-done")
        page.click("#ob-finish"); page.wait_for_timeout(1000)
    else:
        page.wait_for_selector("#login-pin"); shot(page, f"{tag}-00-login")
        for d in "123456": page.click(f'.pin-key[data-k="{d}"]')
        page.wait_for_timeout(1500)
        if page.locator("#login-pin").count() and page.locator("#login-pin").is_visible():
            page.keyboard.press("Enter"); page.wait_for_timeout(1200)
        go(page, "data"); page.once("dialog", lambda d: d.accept()); page.click("#dt-sample"); page.wait_for_timeout(2000)
    shot(page, f"{tag}-10-home")
    go(page, "voice")
    page.fill("#voice-text", "cooler chicken thighs two cases, crema 1, limes 20, corn tortillas 3")
    shot(page, f"{tag}-11-voice")
    page.click("#voice-check"); page.wait_for_timeout(900); shot(page, f"{tag}-12-voice-review")
    for v in ["catalog", "starter", "reorder", "orders", "invoice", "log", "money", "trucks", "board", "people", "vendors", "accounts", "data", "setup", "reports", "zones", "count", "variance"]:
        go(page, v); shot(page, f"{tag}-v-{v}")
    page.locator(".locale-switch [data-locale=es]:visible").first.click(); page.wait_for_timeout(800)
    go(page, "voice"); shot(page, f"{tag}-20-voice-es"); go(page, "home"); shot(page, f"{tag}-21-home-es")
    b.close()

with sync_playwright() as pw:
    if "desktop-only" not in sys.argv: run(pw, 390, 844, "m390", fresh=True)
    run(pw, 1440, 900, "d1440", fresh=False)
print("\n".join(errors) or "NO JS ERRORS")
