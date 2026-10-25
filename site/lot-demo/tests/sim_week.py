"""End-to-end week simulation against a REAL running OSFT server (fresh throwaway data dir).

usage: sim_week.py BASE_URL N_PRODUCTS {exact|short} OUT_JSON [SHOTS_DIR]

Week: Mon 2026-10-05 opening full count (10 each, before service) → POS CSV imports Mon–Sat whose recipe usage
consumes exactly 5 of every product → two daily end-of-shift partial counts by a crew login (Tue, Thu) →
weekly full count Mon 2026-10-12 (before service) with 5 left of each (or 2 items short by 2 in the 'short' variant).
"""
import io, json, math, sys
import requests

BASE, N, MODE, OUT = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
SHOTS = sys.argv[5] if len(sys.argv) > 5 else None
DAYS = ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-10"]
SPLIT = [0.1, 0.2, 0.2, 0.2, 0.15, 0.15]   # share of each menu item's weekly sales per day

SECTIONS = [{"name": "Line"}, {"name": "Cooler"}, {"name": "Freezer"}, {"name": "Dry storage"}, {"name": "Paper & supplies"}]
CATALOG = [  # name, unit, cost, category, section index
    ("Ground beef", "lb", 4.89, "Protein", 1), ("Chicken thigh", "lb", 2.79, "Protein", 1), ("Carnitas", "lb", 5.25, "Protein", 2),
    ("Al pastor pork", "lb", 4.10, "Protein", 1), ("Flour tortillas 12in", "pack", 3.49, "Tortillas", 3),
    ("Corn tortillas", "pack", 2.29, "Tortillas", 3), ("Shredded cheese", "lb", 3.99, "Dairy", 1), ("Sour cream", "qt", 3.20, "Dairy", 1),
    ("Pico de gallo", "qt", 5.50, "Produce", 0), ("Limes", "lb", 1.60, "Produce", 0),
    ("Cilantro", "bunch", 0.89, "Produce", 0), ("White onion", "lb", 0.99, "Produce", 0), ("Avocados", "ea", 1.25, "Produce", 1),
    ("Jalapeños", "lb", 1.49, "Produce", 0), ("Romaine", "head", 1.79, "Produce", 1), ("Tomatoes", "lb", 1.89, "Produce", 0),
    ("Salsa roja", "qt", 4.25, "Sauce", 0), ("Salsa verde", "qt", 4.00, "Sauce", 0), ("Crema", "qt", 4.60, "Dairy", 1),
    ("Queso fresco", "lb", 5.10, "Dairy", 1), ("Black beans", "can", 1.35, "Pantry", 3), ("Rice", "lb", 0.85, "Pantry", 3),
    ("Fryer oil", "jug", 28.00, "Pantry", 3), ("Tortilla chips", "bag", 6.50, "Pantry", 3), ("Shrimp", "lb", 8.90, "Protein", 2),
    ("Fish fillet", "lb", 7.40, "Protein", 2), ("Chorizo", "lb", 4.30, "Protein", 1), ("Eggs", "dozen", 3.10, "Dairy", 1),
    ("Cabbage", "head", 1.20, "Produce", 0), ("Radishes", "bunch", 1.10, "Produce", 0), ("Chipotle mayo", "qt", 5.80, "Sauce", 1),
    ("Horchata mix", "bag", 7.25, "Beverage", 3), ("Mexican Coke", "case", 32.00, "Beverage", 3), ("Jarritos", "case", 24.00, "Beverage", 3),
    ("Bottled water", "case", 6.00, "Beverage", 3), ("Ice", "bag", 2.50, "Beverage", 2), ("Foil wraps", "pack", 9.00, "Paper", 4),
    ("Clamshells", "case", 38.00, "Paper", 4), ("Napkins", "case", 22.00, "Paper", 4), ("Cups 16oz", "sleeve", 4.50, "Paper", 4),
]
MENUS_10 = [  # name, price, sold/week, ingredient indexes  (each product in exactly one or two menus)
    ("Beef taco", 3.5, 40, [0, 5, 6, 8]), ("Chicken burrito", 11.0, 20, [1, 4, 7, 9]),
    ("Carnitas taco", 3.75, 40, [2, 5, 8]),
]


def menus_40():
    m = [("Beef taco", 3.5, 40, [0, 5, 6, 8, 10]), ("Chicken burrito", 11.0, 20, [1, 4, 7, 21, 20, 36]),
         ("Carnitas taco", 3.75, 40, [2, 5, 11, 17]), ("Al pastor taco", 3.75, 40, [3, 5, 9, 16]),
         ("Quesadilla", 9.0, 20, [4, 6, 19, 18]), ("Guac & chips", 7.0, 20, [12, 13, 15, 23, 22]),
         ("Shrimp taco", 4.5, 20, [24, 28, 30, 9]), ("Fish taco", 4.25, 20, [25, 29, 14, 22]),
         ("Chorizo & egg burrito", 10.0, 20, [26, 27, 4, 37]), ("Horchata", 4.0, 20, [31, 39, 35]),
         ("Mexican Coke", 3.5, 20, [32]), ("Jarritos", 3.0, 20, [33]), ("Water", 2.0, 20, [34, 38])]
    return m


def die(msg):
    print("FATAL", msg); sys.exit(2)


class C:
    def __init__(s):
        s.s = requests.Session()

    def __call__(s, method, path, ok=(200, 201), **kw):
        r = s.s.request(method, BASE + path, **kw)
        if r.status_code not in ok:
            die(f"{method} {path} → {r.status_code} {r.text[:300]}")
        return r.json()


owner, crew = C(), C()
log = []


def main():
    # --- setup: sections, owner + crew logins, count types ---
    owner("PUT", "/api/sections", json={"sections": SECTIONS})
    secs = owner("GET", "/api/sections")["sections"]
    owner("POST", "/api/people", json={"name": "Owner", "login": "owner", "role": "admin", "pin": "111111"})
    owner("POST", "/api/auth/login", json={"pin": "111111"})
    owner("POST", "/api/people", json={"name": "Crew Ana", "login": "ana", "role": "crew", "pin": "222222", "count_types": ["daily"]})
    crew("POST", "/api/auth/login", json={"pin": "222222"})
    cat = CATALOG[:N]
    items = []
    for name, unit, cost, category, si in cat:
        r = owner("POST", "/api/items", json={"name": name, "unit": unit, "cost": cost, "category": category,
                                               "zone": secs[si]["key"], "par": 8, "on_hand": 0})
        items.append(r["item"])
    menus = MENUS_10 if N == 10 else menus_40()
    if N == 10:  # 10th product used by burrito AND quesadilla-free → put product 3 (Al pastor) on a 4th menu
        menus = MENUS_10 + [("Al pastor taco", 3.75, 40, [3, 5])]
    # usage per product = sum(sold * qty) — choose qty so every product totals exactly 5
    uses = {}
    for _, _, sold, ing in menus:
        for k in ing:
            uses.setdefault(k, []).append(sold)
    missing = [k for k in range(N) if k not in uses]
    if missing:
        die(f"products not on any menu: {missing}")
    menu_rows = []
    for name, price, sold, ing in menus:
        ingr = [{"item_id": items[k]["id"], "qty": round(5.0 / sum(uses[k]), 6)} for k in ing]
        r = owner("POST", "/api/menu", json={"name": name, "price": price, "ingredients": ingr, "pos_names": [name]})
        menu_rows.append((name, price, sold, ing))
    # watch list for daily: proteins (by category) — default count type already scopes Protein
    ct = owner("GET", "/api/count-types")["count_types"]
    daily = next(x for x in ct if x["key"] == "daily")
    scope_ids = {i["id"] for i in items if i["category"] == "Protein"}
    log.append(f"daily scope: {daily['scope_label']} → {daily['item_count']} products")

    # --- Mon opening weekly full count (before service), 10 each ---
    def do_count(cl, typ, date, counts):
        s = cl("POST", "/api/counts/start", json={"type": typ, "date": date})["session"]
        cl("PUT", f"/api/counts/{s['id']}", json={"counts": counts})
        return cl("POST", f"/api/counts/{s['id']}/complete")

    do_count(owner, "weekly", "2026-10-05", {i["id"]: 10 for i in items})

    # --- POS imports per day; track true usage by day ---
    true_used = {i["id"]: 0.0 for i in items}
    used_by_day = {}
    sales_total = 0.0
    sold_counts = {}
    for di, day in enumerate(DAYS):
        lines = ["Date,Item,Qty,Net Sales"]
        for name, price, sold, ing in menu_rows:
            # integer split that sums to `sold`
            q = round(sold * sum(SPLIT[:di + 1])) - round(sold * sum(SPLIT[:di]))
            if q:
                lines.append(f"{day},{name},{q},{q * price:.2f}")
                sales_total += q * price
                sold_counts[name] = sold_counts.get(name, 0) + q
                for k in ing:
                    true_used[items[k]["id"]] += q * 5.0 / sum(uses[k])
        used_by_day[day] = dict(true_used)
        r = owner("POST", "/api/pos/import", files={"file": (f"pos-{day}.csv", "\n".join(lines).encode())},
                  data={"adapter": "generic_csv"})
        if any(not l.get("menu_item_id") for l in r["import"]["lines"]):
            die("POS lines not linked to menu items")
        # crew daily partial counts, end of shift Tue + Thu
        if day in ("2026-10-06", "2026-10-08"):
            # crew may NOT start a weekly
            rr = crew.s.post(BASE + "/api/counts/start", json={"type": "weekly", "date": day})
            if rr.status_code != 403:
                die("crew was allowed to start a weekly count")
            got = do_count(crew, "daily", day, {iid: round(10 - true_used[iid], 4) for iid in scope_ids})
            sm = got["session"]["summary"]
            oh = {i["id"]: i["on_hand"] for i in owner("GET", "/api/items")["items"]}
            out_scope = [i for i in items if i["id"] not in scope_ids]
            log.append({"partial": day, "counted": sm["counted"], "missing_flagged": len(sm["missing_in_scope"]),
                        "out_of_scope_kept_10": all(oh[i["id"]] == 10 for i in out_scope),
                        "out_of_scope_zeroed": sum(1 for i in out_scope if oh[i["id"]] == 0),
                        "by": got["session"]["counted_by"]})
    # --- weekly full count Mon 10-12 before service ---
    short = [items[1]["id"], items[N - 3]["id"]] if MODE == "short" else []
    end = {i["id"]: (3 if i["id"] in short else 5) for i in items}
    do_count(owner, "weekly", "2026-10-12", end)

    # --- read back everything ---
    its = {i["id"]: i for i in owner("GET", "/api/items")["items"]}
    sv = owner("GET", "/api/variance/sales")
    rep = owner("GET", "/api/reports/summary")
    ro = owner("GET", "/api/reorder")
    dash = owner("GET", "/api/dashboard")
    menu = owner("GET", "/api/menu")
    rows = {r["item_id"]: r for r in sv["rows"]}
    checks, table = [], []

    def chk(label, exp, act, tol=0.011):
        ok = (abs(float(exp) - float(act)) <= tol) if isinstance(exp, (int, float)) and act is not None and not isinstance(exp, bool) else exp == act
        checks.append({"check": label, "expected": exp, "actual": act, "ok": ok})
        return ok

    for i in items:
        iid = i["id"]
        r = rows.get(iid, {})
        exp_end = end[iid]
        exp_var = 10 - exp_end - 5
        table.append({"name": i["name"], "unit": i["unit"], "cost": i["cost"], "on_hand": its[iid]["on_hand"], "exp_on_hand": exp_end,
                      "theoretical": r.get("theoretical"), "exp_theoretical": 5, "counted_usage": r.get("counted_usage"),
                      "exp_counted": 10 - exp_end, "variance": r.get("variance"), "exp_variance": exp_var,
                      "variance_cost": r.get("variance_cost"), "exp_variance_cost": round(exp_var * i["cost"], 2),
                      "start_date": r.get("start_date")})
    bad_rows = [t for t in table if not (abs(t["on_hand"] - t["exp_on_hand"]) < 1e-6 and t["theoretical"] is not None
                and abs(t["theoretical"] - 5) < 0.011 and abs(t["variance"] - t["exp_variance"]) < 0.011)]
    chk("rows with wrong on-hand/theoretical/variance", 0, len(bad_rows))
    chk("variance rows reported", N, sum(1 for r in sv["rows"] if r.get("variance") is not None))
    flagged = sorted(its[r["item_id"]]["name"] for r in sv["rows"] if abs(r.get("variance") or 0) > 0.011)
    chk("items flagged by variance report", sorted(its[x]["name"] for x in short), flagged)
    chk("report start = opening weekly 2026-10-05", "2026-10-05", sv["start"]["business_date"])
    chk("report end = weekly 2026-10-12", "2026-10-12", sv["end"]["business_date"])
    chk("daily partials skipped by weekly report", 2, len(sv.get("skipped_partials") or []))
    exp_var_cost = round(sum(2 * its[x]["cost"] for x in short), 2)
    chk("total variance $", exp_var_cost, sv["total_variance_cost"])
    exp_value = round(sum(end[i["id"]] * i["cost"] for i in items), 2)
    chk("inventory value $", exp_value, rep["stock"]["total_value"])
    m = rep["money"]
    exp_ideal = round(sum(5 * i["cost"] for i in items), 2)
    exp_cogs = round(sum((10 - end[i["id"]]) * i["cost"] for i in items), 2)
    chk("sales $ in window", round(sales_total, 2), m.get("sales"))
    chk("ideal COGS $ (theoretical × cost)", exp_ideal, m.get("ideal_cogs"))
    chk("actual COGS $ (counted × cost)", exp_cogs, m.get("cogs"))
    chk("food cost %", round(exp_cogs / sales_total * 100, 1), m.get("food_cost_pct"), 0.051)
    chk("ideal food cost %", round(exp_ideal / sales_total * 100, 1), m.get("ideal_pct"), 0.051)
    lines = {l["id"]: l for g in ro["groups"] for l in g["lines"]}
    chk("order list lines (all below par 8)", N, len(lines))
    chk("order qty = par − on-hand", 0, sum(1 for i in items if abs(lines[i["id"]]["order_qty"] - (8 - end[i["id"]])) > 1e-6))
    exp_order = round(sum((8 - end[i["id"]]) * i["cost"] for i in items), 2)
    chk("order list $", exp_order, ro.get("total") if ro.get("total") is not None else ro.get("total_cost"))
    chk("dashboard low-par count", N, dash["low_par_count"])
    for p in [x for x in log if isinstance(x, dict)]:
        chk(f"daily {p['partial']}: no out-of-scope item zeroed", 0, p["out_of_scope_zeroed"])
        chk(f"daily {p['partial']}: nothing flagged missing", 0, p["missing_flagged"])
        chk(f"daily {p['partial']}: counted by crew login", "Crew Ana", p["by"])
    plate = []
    for mi in menu["menu"]:
        name = mi["name"]
        mr = next(x for x in menu_rows if x[0] == name)
        exp_plate = sum(5.0 / sum(uses[k]) * CATALOG[k][2] for k in mr[3])
        plate.append({"menu": name, "price": mi["price"], "plate_cost": mi.get("plate_cost"), "exp_plate_cost": round(exp_plate, 4),
                      "food_cost_pct": mi.get("food_cost_pct"), "sold": sold_counts.get(name)})
        chk(f"plate cost {name}", round(exp_plate, 4), mi.get("plate_cost"), 0.001)
    hist = owner("GET", "/api/counts/history")["history"]
    chk("count history types (newest first)", ["weekly", "daily", "daily", "weekly"], [h["type"] for h in hist])
    json.dump({"n": N, "mode": MODE, "checks": checks, "table": table, "plates": plate, "history": hist, "log": log,
               "sv_daily_check": None}, open(OUT, "w"), indent=1, default=str)
    failed = [c for c in checks if not c["ok"]]
    print(f"N={N} {MODE}: {len(checks) - len(failed)}/{len(checks)} checks OK")
    for c in failed:
        print("  FAIL", c)
    if SHOTS:
        shots(f"{N}-{MODE}")
    sys.exit(1 if failed else 0)


def shots(tag):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        for W, H, dev in ((1440, 1000, "desk"), (390, 844, "phone")):
            pg = b.new_page(viewport={"width": W, "height": H})
            pg.goto(BASE + "/")
            pg.request.post(BASE + "/api/auth/login", data={"pin": "111111"})
            pg.request.put(BASE + "/api/onboarding", data={"phase": "done"})
            pg.goto(BASE + "/"); pg.wait_for_timeout(1200)
            for v in ("count", "reports", "money", "reorder"):
                pg.evaluate(f"OSFT.showView('{v}')"); pg.wait_for_timeout(900)
                pg.screenshot(path=f"{SHOTS}/{tag}-{dev}-{v}.png", full_page=True)
            pg.close()
        b.close()


main()
