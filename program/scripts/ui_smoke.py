#!/usr/bin/env python3
"""Browser smoke for OSFT v0.3 (needs `pip install playwright`).
Opens every view at phone (390px) and desktop (1440px) widths through the
OSBW-style sidebar + workbook tabs, checks for JS errors, imports a sample CSV,
logs a receive with a photo, checks Spanish, and saves screenshots.
Run against a server with demo data:  python scripts/ui_smoke.py [BASE] [OUTDIR]"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5053"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/osft-ui"); OUT.mkdir(parents=True, exist_ok=True)
ROOT = Path(__file__).resolve().parents[1]
VIEWS = ["home", "count", "variance", "reorder", "catalog", "reports", "zones", "sales", "receive", "menu", "stops", "setup"]
errors = []


def goto(pg, view, mobile):
    # navigate the way a user would: sidebar group, then workbook tab
    groups = {"count": "sheets", "variance": "sheets", "reorder": "sheets", "catalog": "sheets",
              "reports": "reports", "zones": "inhouse", "sales": "inputs", "receive": "inputs",
              "menu": "menu", "stops": "stops", "setup": "setup", "home": "home"}
    if mobile:
        pg.click("#menu-toggle"); pg.wait_for_timeout(250)
    pg.click(f'#main-nav [data-group="{groups[view]}"]'); pg.wait_for_timeout(350)
    if not pg.locator(f"#view-{view}").is_visible():
        pg.click(f'#view-{view} .workbook-tab[data-tab="{view}"]' if False else f'.view:not(.hidden) [data-tab="{view}"]')
        pg.wait_for_timeout(350)
    assert pg.locator(f"#view-{view}").is_visible(), f"{view} not visible"


with sync_playwright() as p:
    b = p.chromium.launch()
    for label, vp, mobile in (("mobile", {"width": 390, "height": 844}, True), ("desktop", {"width": 1440, "height": 900}, False)):
        ctx = b.new_context(viewport=vp, device_scale_factor=2 if mobile else 1, is_mobile=mobile, has_touch=mobile)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e, l=label: errors.append(f"[{l}] {e}"))
        pg.on("console", lambda m, l=label: m.type == "error" and "fonts.g" not in m.text and errors.append(f"[{l}] {m.text}"))
        pg.goto(BASE + "/"); pg.wait_for_timeout(900)
        for v in VIEWS:
            goto(pg, v, mobile)
            # no horizontal page overflow
            ow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            if ow > 2:
                errors.append(f"[{label}] {v}: page overflows by {ow}px")
            pg.screenshot(path=str(OUT / f"{v}-{label}.png"), full_page=True)
        ctx.close()

    # functional checks at phone width
    ctx = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pg = ctx.new_page(); pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/"); pg.wait_for_timeout(800)
    goto(pg, "sales", True)
    pg.set_input_files("#sales-file", str(ROOT / "samples/square-item-sales-EXAMPLE.csv")); pg.wait_for_timeout(700)
    assert "Beef Taco" in pg.inner_text("#sales-preview"), "preview missing"
    pg.click("#btn-sales-import"); pg.wait_for_timeout(700)
    assert "square" in pg.inner_text("#sales-list")
    goto(pg, "receive", True)
    pg.fill("#recv-qty", "2"); pg.fill("#recv-cost", "3.10"); pg.fill("#recv-vendor", "UI Test Vendor")
    png = OUT / "test-invoice.png"; pg.screenshot(path=str(png))
    pg.set_input_files("#recv-photo", str(png))
    pg.click('#receive-form button[type="submit"]'); pg.wait_for_timeout(900)
    assert pg.locator("#receive-list img.thumb").count() >= 1, "photo thumb missing"
    goto(pg, "menu", True)
    pg.click("#btn-add-menu"); pg.wait_for_timeout(200)
    assert pg.locator("#menu-ings .ing-row").count() == 1
    goto(pg, "reorder", True)
    assert "Ground beef" in pg.inner_text("#reorder-list") or "PAR" in pg.inner_text("#reorder-list")
    # count stepper
    goto(pg, "count", True)
    if pg.locator("#btn-start-count").is_enabled():
        pg.click("#btn-start-count"); pg.wait_for_timeout(600)
    if pg.locator(".step-btn[data-step='1']").count():
        inp = pg.locator("[data-count-item]").first; before = float(inp.input_value() or 0)
        pg.locator(".step-btn[data-step='1']").first.click(); pg.wait_for_timeout(200)
        assert float(inp.input_value()) == before + 1, "stepper failed"
    # Spanish
    pg.click('.topbar .locale-switch button[data-locale="es"]'); pg.wait_for_timeout(600)
    goto(pg, "stops", True)
    pg.click("#menu-toggle"); pg.wait_for_timeout(250)
    assert "Paradas" in pg.inner_text("#main-nav"), "Spanish nav missing"
    pg.keyboard.press("Escape")
    pg.screenshot(path=str(OUT / "stops-es-mobile.png"), full_page=True)
    pg.click('.topbar .locale-switch button[data-locale="en"]'); pg.wait_for_timeout(400)
    href = pg.get_attribute("#btn-print-load", "href")
    pg.goto(BASE + href); pg.wait_for_timeout(300)
    pg.screenshot(path=str(OUT / "print-loadlist.png"), full_page=True)
    ctx.close(); b.close()
print("JS errors:", errors or "none")
print("UI smoke OK" if not errors else "UI smoke had errors"); sys.exit(1 if errors else 0)
