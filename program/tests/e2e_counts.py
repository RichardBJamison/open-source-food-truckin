"""v1.3 UI e2e: Settings › Count types, crew limited to daily, scoped count walk, history, ES. usage: BASE SHOTS W H"""
import sys
from playwright.sync_api import sync_playwright
BASE, SHOTS, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
tag = "phone" if W < 600 else "desk"
errs, fails = [], []


def ok(c, m):
    print(("PASS " if c else "FAIL ") + m)
    if not c: fails.append(m)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    r = pg.request
    pg.on("response", lambda x: x.status == 403 and errs.append("403 " + x.url))
    r.post(BASE + "/api/seed", data={})
    r.put(BASE + "/api/onboarding", data={"phase": "done"})
    r.post(BASE + "/api/people", data={"name": "Owner", "login": "owner", "role": "admin", "pin": "111111"})
    r.post(BASE + "/api/auth/login", data={"pin": "111111"})
    pg.goto(BASE + "/"); pg.wait_for_timeout(1200)
    pg.evaluate("OSFT.showView('counttypes')"); pg.wait_for_timeout(900)
    ok(pg.locator("[data-ct]").count() == 3, "settings shows 3 count types")
    pg.screenshot(path=f"{SHOTS}/ct-settings-{tag}.png", full_page=True)
    # switch daily to watch the Cooler section too, save
    pg.locator("[data-ct='0'] [data-sec='cooler']").check()
    pg.click("#ct-save"); pg.wait_for_timeout(700)
    ok("cooler" in r.get(BASE + "/api/count-types").json()["count_types"][0]["sections"], "daily scope saved")
    # people: crew limited to daily via UI form
    pg.evaluate("OSFT.showView('people')"); pg.wait_for_timeout(800)
    pg.click("#pp-add"); pg.wait_for_timeout(300)
    pg.fill("#pp-name", "Ana"); pg.fill("#pp-login", "ana"); pg.select_option("#pp-role", "crew"); pg.fill("#pp-pin", "222222")
    pg.locator("[data-pp-ct='daily']").check()
    pg.screenshot(path=f"{SHOTS}/ct-people-{tag}.png", full_page=True)
    pg.click("#pp-f button[type=submit]"); pg.wait_for_timeout(800)
    ana = [x for x in r.get(BASE + "/api/people").json()["people"] if x["login"] == "ana"][0]
    ok(ana.get("count_types") == ["daily"], "crew saved with daily only")
    r.post(BASE + "/api/auth/logout", data={})
    r.post(BASE + "/api/auth/login", data={"pin": "222222"})
    pg.goto(BASE + "/"); pg.wait_for_timeout(1200)
    pg.evaluate("OSFT.showView('count')"); pg.wait_for_timeout(900)
    opts = pg.locator("#count-type option").all_inner_texts()
    ok(len(opts) == 1 and "Daily" in opts[0], f"crew sees only daily ({opts})")
    pg.click("#btn-start-count"); pg.wait_for_timeout(1000)
    sc = r.get(BASE + "/api/count-types").json()["count_types"][0]["item_count"]
    rows = pg.locator("[data-count-item]").count()
    ok(rows == sc and rows < len(r.get(BASE + "/api/items").json()["items"]), f"scoped walk shows {rows} of scope {sc}")
    ok(pg.locator("#count-scope.ct-partial").is_visible(), "partial banner visible")
    pg.screenshot(path=f"{SHOTS}/ct-daily-walk-{tag}.png", full_page=True)
    pg.locator("[data-count-item]").first.fill("1")
    pg.click("#btn-complete-count"); pg.wait_for_timeout(1200)
    h = r.get(BASE + "/api/counts/history").json()["history"]
    ok(h[0]["type"] == "daily" and h[0]["by"] == "Ana" and h[0]["summary"]["missing_in_scope"] == [], "history: daily by Ana, nothing missing")
    zero = [i for i in r.get(BASE + "/api/items").json()["items"] if i["on_hand"] == 0]
    pg.evaluate("OSFT.showView('count')"); pg.wait_for_timeout(900)
    ok(pg.locator("[data-ct-hist='daily']").count() >= 1, "history table shows daily row")
    pg.screenshot(path=f"{SHOTS}/ct-history-{tag}.png", full_page=True)
    pg.locator("button[data-locale=es]:visible").first.click(); pg.wait_for_timeout(900)
    pg.evaluate("OSFT.showView('count')"); pg.wait_for_timeout(900)
    ok("Historial de conteos" in pg.content(), "ES strings")
    pg.screenshot(path=f"{SHOTS}/ct-history-es-{tag}.png", full_page=True)
    b.close()
ok(not errs, f"no JS errors {errs[:3]}")
print("ALL CHECKS PASSED, NO JS ERRORS" if not fails else f"{len(fails)} FAILED")
sys.exit(1 if fails else 0)
