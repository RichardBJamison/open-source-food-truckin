"""v1.0 parity API tests: accounts, trucks, vendors, categories, POS accounts, catalog, import/export,
voice apply, orders, invoice, reports, backups, onboarding."""
import io


def test_fresh_install_starts_onboarding(client):
    ob = client.get("/api/onboarding").json
    assert ob["onboarding"]["phase"] == "welcome" and not ob["onboarding"]["completed"]
    assert not ob["has_admin"]


def test_sample_taco_truck(client):
    r = client.post("/api/onboarding/sample")
    assert r.status_code == 200 and r.json["seeded"] >= 8
    ob = client.get("/api/onboarding").json["onboarding"]
    assert ob["completed"]
    assert len(client.get("/api/vendors").json["vendors"]) == 3
    assert client.get("/api/orders").json["orders"][0]["number"] == "PO-1001"


def test_people_and_pin_login(client):
    # open mode until the first admin
    assert client.get("/api/items").status_code == 200
    r = client.post("/api/people", json={"name": "Rich", "login": "rich", "role": "admin", "pin": "123456"})
    assert r.status_code == 201, r.json
    assert "pin_hash" not in r.json["person"]
    # creator is logged in automatically
    assert client.get("/api/auth/status").json["user"]["name"] == "Rich"
    r = client.post("/api/people", json={"name": "Ana", "login": "ana", "role": "crew", "pin": "654321"})
    assert r.status_code == 201, r.json
    ana = r.json["person"]
    assert client.post("/api/people", json={"name": "Bad", "login": "bad", "role": "crew", "pin": "12"}).status_code == 400
    client.post("/api/auth/logout")
    assert client.get("/api/items").status_code == 401
    assert client.post("/api/auth/login", json={"pin": "000000"}).status_code == 401
    assert client.post("/api/auth/login", json={"pin": "654321"}).status_code == 200
    # crew can't manage people or settings
    assert client.get("/api/people").status_code == 403
    assert client.put("/api/business", json={"name": "X"}).status_code == 403
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"pin": "123456"})
    assert client.put(f"/api/people/{ana['id']}", json={"name": "Ana M"}).json["person"]["name"] == "Ana M"
    rich = next(p for p in client.get("/api/people").json["people"] if p["login"] == "rich")
    assert client.delete(f"/api/people/{rich['id']}").status_code == 400  # last admin protected


def test_business_profile(client):
    r = client.put("/api/business", json={"name": "Taco Fuego", "email": "a@b.co", "cycle_days": 7})
    assert r.json["business"]["name"] == "Taco Fuego"
    assert client.put("/api/business", json={"cycle_days": 99}).status_code == 400
    assert client.put("/api/business", json={"logo_data_url": "javascript:1"}).status_code == 400


def test_vendors_crud(client):
    r = client.post("/api/vendors", json={"name": "Sysco", "email": "x@y.com", "lead_days": "2"})
    vid = r.json["vendor"]["id"]
    assert client.post("/api/vendors", json={"name": "sysco"}).status_code == 400
    assert client.post("/api/vendors", json={"name": "Bad", "email": "nope"}).status_code == 400
    assert client.put(f"/api/vendors/{vid}", json={"rep": "Joe"}).json["vendor"]["rep"] == "Joe"
    assert client.delete(f"/api/vendors/{vid}").status_code == 200


def test_categories_gl_and_rename(seeded):
    cats = seeded.get("/api/accounts/categories").json["categories"]
    prot = next(c for c in cats if c["name"] == "Protein")
    r = seeded.put(f"/api/accounts/categories/{prot['id']}", json={"name": "Meat", "gl_code": "5010", "target_pct": 30})
    assert r.json["category"]["gl_code"] == "5010"
    items = seeded.get("/api/items").json["items"]
    assert any(i["category"] == "Meat" for i in items) and not any(i["category"] == "Protein" for i in items)
    assert seeded.delete(f"/api/accounts/categories/{prot['id']}").status_code == 400


def test_pos_accounts(client):
    r = client.post("/api/accounts/pos", json={"label": "Square main", "provider": "square"})
    assert r.status_code == 201 and r.json["account"]["default"]
    assert client.post("/api/accounts/pos", json={"label": "x", "provider": "nope"}).status_code == 400


def test_trucks_and_transfer(seeded):
    r = seeded.post("/api/trucks", json={"name": "Truck 2", "copy_products": True})
    t2 = r.json["truck"]["id"]
    assert r.json["truck"]["item_count"] >= 8
    beef = next(i for i in seeded.get("/api/items").json["items"] if i["name"] == "Ground beef")
    before = beef["on_hand"]
    r = seeded.post("/api/transfers", json={"to_truck_id": t2, "lines": [{"item_id": beef["id"], "qty": 4}]})
    assert r.status_code == 201, r.json
    beef2 = next(i for i in seeded.get("/api/items").json["items"] if i["name"] == "Ground beef")
    assert beef2["on_hand"] == before - 4
    assert seeded.post("/api/transfers", json={"to_truck_id": t2, "lines": [{"item_id": beef["id"], "qty": 9999}]}).status_code == 400
    seeded.post(f"/api/trucks/{t2}/activate")
    beef_t2 = next(i for i in seeded.get("/api/items").json["items"] if i["name"] == "Ground beef")
    assert beef_t2["on_hand"] == 4
    seeded.post("/api/trucks/main/activate")
    assert seeded.delete("/api/trucks/main").status_code == 400
    assert seeded.delete(f"/api/trucks/{t2}").status_code == 200


def test_starter_catalog_add_no_prices(client):
    cat = client.get("/api/catalog/starter").json
    assert cat["count"] >= 300
    ids = [c["id"] for c in cat["items"][:5]]
    r = client.post("/api/catalog/starter/add", json={"ids": ids})
    assert r.json["added"] == 5 and all(i["cost"] is None for i in r.json["items"])
    assert client.post("/api/catalog/starter/add", json={"ids": ids}).json["added"] == 0


def test_import_export_roundtrip(seeded):
    csv_text = seeded.get("/api/items/export.csv").data.decode("utf-8-sig")
    assert csv_text.startswith("name,") and "Ground beef" in csv_text
    new = "name,unit,par,zone,cost,vendor\nAvocados,ea,40,cooler,1.25,New Produce Co\nBad,ea,abc,dry,,\n"
    dry = seeded.post("/api/items/import?dry_run=1", json={"text": new}).json
    assert dry["created"] == 1 and len(dry["errors"]) == 1
    assert not any(i["name"] == "Avocados" for i in seeded.get("/api/items").json["items"])
    r = seeded.post("/api/items/import", json={"text": new}).json
    assert r["created"] == 1 and r["new_vendors"] == ["New Produce Co"]
    av = next(i for i in seeded.get("/api/items").json["items"] if i["name"] == "Avocados")
    assert av["par"] == 40 and av["vendor_id"]


def test_voice_parse_and_apply(seeded):
    p = seeded.post("/api/voice/parse", json={"text": "cooler: ground beef 9 pounds, chicken thigh 11"}).json
    assert p["summary"]["matched"] == 2 and p["can_apply"]
    counts = {k: v for k, v in p["totals"].items()}
    r = seeded.post("/api/voice/apply", json={"counts": counts, "text": "x", "complete": True}).json
    assert r["session"]["status"] == "completed" and r["session"]["source"] == "voice"
    beef = next(i for i in seeded.get("/api/items").json["items"] if i["name"] == "Ground beef")
    assert beef["on_hand"] == 9
    assert seeded.post("/api/voice/parse", json={"text": ""}).status_code == 400


def test_voice_walk_builds_list(client):
    w = client.post("/api/voice/walk", json={"text": "cooler: ground beef, sour cream. freezer: ice"}).json
    assert len(w["proposals"]) >= 3
    r = client.post("/api/voice/walk/apply", json={"proposals": w["proposals"]}).json
    assert r["added"] >= 3
    assert all(i["cost"] is None for i in client.get("/api/items").json["items"])


def test_orders_flow(seeded):
    rep = seeded.get("/api/reorder").json
    g = rep["groups"][0]
    r = seeded.post("/api/orders", json={"from_reorder": True, "vendor_id": g["vendor_id"], "vendor": g["vendor"]})
    assert r.status_code == 201, r.json
    po = r.json["order"]
    t = seeded.get(f"/api/orders/{po['id']}/text").json
    assert po["number"] in t["subject"] and po["lines"][0]["name"] in t["body"]
    assert seeded.post(f"/api/orders/{po['id']}/sent").json["order"]["status"] == "sent"
    first = po["lines"][0]
    rr = seeded.post(f"/api/orders/{po['id']}/receive", json={"received": {first["item_id"]: 0}}).json
    assert rr["order"]["status"] == "received" and rr["discrepancies"][0]["received"] == 0
    assert seeded.get(f"/api/orders/{po['id']}.csv").status_code == 200


def test_invoice_parse_and_batch_receive(seeded):
    lines = seeded.post("/api/invoice/parse", json={"text": "2 cs Ground beef 4.89\n3 Ice\nnonsense"}).json["lines"]
    beef = lines[0]
    assert beef["item_name"] == "Ground beef" and beef["qty"] == 20 and beef["unit_cost"] == 4.89
    r = seeded.post("/api/receives/batch", json={"vendor": "Example Meat Co.", "invoice_no": "77",
                                                  "lines": [{"item_id": beef["item_id"], "qty": 20, "unit_cost": 5}]})
    assert r.status_code == 201
    log = seeded.get("/api/inputs/log?type=invoice").json["rows"]
    assert any(x["title"] == "Example Meat Co." for x in log)


def test_reports_and_exports(seeded):
    rep = seeded.get("/api/reports/summary").json
    assert rep["stock"]["total_value"] > 0 and rep["money"]["ready"]
    assert rep["money"]["sales"] > 0 and rep["money"]["food_cost_pct"] is not None
    for p in ("report", "count", "variance", "reorder"):
        assert seeded.get(f"/api/export/{p}.csv").status_code == 200


def test_backup_restore_reset(seeded, tmp_path):
    assert seeded.post("/api/backups").status_code == 201
    z = seeded.get("/api/backup").data
    assert z[:2] == b"PK"
    assert seeded.post("/api/reset/all", json={"confirm": "no"}).status_code == 400
    assert seeded.post("/api/reset/all", json={"confirm": "RESET"}).status_code == 200
    assert seeded.get("/api/items").json["items"] == []
    r = seeded.post("/api/restore", data={"file": (io.BytesIO(z), "b.zip")}, content_type="multipart/form-data")
    assert r.status_code == 200, r.json
    assert len(seeded.get("/api/items").json["items"]) >= 8
    bad = seeded.post("/api/restore", data={"file": (io.BytesIO(b"hello"), "b.txt")}, content_type="multipart/form-data")
    assert bad.status_code == 400


def test_onboarding_walkthrough(client):
    client.put("/api/business", json={"name": "Fuego"})
    client.put("/api/onboarding", json={"phase": "account"})
    client.post("/api/catalog/starter/add", json={"ids": [c["id"] for c in client.get("/api/catalog/starter").json["items"][:3]]})
    assert client.post("/api/onboarding/first-count").status_code == 200
    r = client.put("/api/onboarding", json={"phase": "done"}).json
    assert r["onboarding"]["completed"]
    assert client.get("/api/settings").json["settings"]["truck_name"] == "Fuego"


def test_staff_board(client):
    p = client.post("/api/staff-board", json={"text": "Clean fryer"}).json["post"]
    assert client.post(f"/api/staff-board/{p['id']}/pin").json["post"]["pinned"]
    assert len(client.get("/api/staff-board").json["posts"]) == 1


def test_zones_configurable(seeded):
    assert seeded.put("/api/settings/zones", json={"zones": ["cooler", "window"]}).json["zones"][-1] == "window"
    assert "window" in [z if isinstance(z, str) else z.get("id") for z in seeded.get("/api/zones").json["zones"]]
    assert seeded.put("/api/settings/zones", json={"zones": ["moon"]}).status_code == 400
