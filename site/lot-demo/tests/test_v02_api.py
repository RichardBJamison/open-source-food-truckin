import io

from conftest import SAMPLES


def test_v01_smoke_still_works(client):
    assert client.get("/api/health").json["ok"]
    r = client.post("/api/items", json={"name": "Buns", "unit": "pack", "par": 4, "category": "Bread", "zone": "dry", "cost": 2.5})
    assert r.status_code == 201 and r.json["item"]["cost"] == 2.5
    assert client.post("/api/items", json={"name": "x", "unit": "u", "par": 1, "category": "c", "zone": "dry", "cost": "abc"}).status_code == 400


def test_seed_covers_new_features(seeded):
    menu = seeded.get("/api/menu").json["menu"]
    assert len(menu) == 4 and all(m["example"] for m in menu)
    beef = next(m for m in menu if "beef" in m["name"])
    assert beef["plate_cost"] > 0 and 0 < beef["food_cost_pct"] < 100
    assert round(beef["margin"], 4) == round(beef["price"] - beef["plate_cost"], 4)
    assert len(seeded.get("/api/stops").json["stops"]) == 3


def test_sales_variance_flags_overportioned_beef(seeded):
    v = seeded.get("/api/variance/sales").json
    assert v["ready"]
    beef = next(r for r in v["rows"] if r["name"] == "Ground beef")
    # example data over-uses beef by 15%
    assert abs(beef["variance_pct"] - 15.0) < 0.5
    tort = next(r for r in v["rows"] if r["name"] == "Corn tortillas")
    assert abs(tort["variance"]) < 0.01
    assert "Horchata" in v["unmatched_sales"]


def test_pos_preview_and_import(seeded):
    data = {"file": (io.BytesIO((SAMPLES / "toast-item-selection-details-EXAMPLE.csv").read_bytes()), "t.csv")}
    p = seeded.post("/api/pos/preview", data=data, content_type="multipart/form-data").json
    assert p["adapter"] == "toast" and p["line_count"] == 2 and p["adapter_info"]["verified"] is False
    assert all(l["menu_item_id"] for l in p["lines"])  # linked through pos_names
    data = {"file": (io.BytesIO((SAMPLES / "toast-item-selection-details-EXAMPLE.csv").read_bytes()), "t.csv"), "adapter": "toast"}
    r = seeded.post("/api/pos/import", data=data, content_type="multipart/form-data")
    assert r.status_code == 201 and r.json["import"]["total_qty"] == 3
    assert len(seeded.get("/api/sales").json["imports"]) == 2
    assert seeded.delete(f"/api/sales/{r.json['import']['id']}").status_code == 200


def test_pos_import_errors(client):
    assert client.post("/api/pos/import", data={}, content_type="multipart/form-data").status_code == 400
    data = {"file": (io.BytesIO(b"a,b\n1,2\n"), "x.csv"), "adapter": "generic_csv"}
    assert client.post("/api/pos/import", data=data, content_type="multipart/form-data").status_code == 400
    data = {"file": (io.BytesIO(b"a,b\n1,2\n"), "x.csv"), "adapter": "square_api"}
    assert client.post("/api/pos/import", data=data, content_type="multipart/form-data").status_code == 400


def test_menu_crud_and_validation(seeded):
    items = seeded.get("/api/items").json["items"]
    assert seeded.post("/api/menu", json={"name": "", "price": 1}).status_code == 400
    assert seeded.post("/api/menu", json={"name": "X", "price": 5, "ingredients": [{"item_id": "nope", "qty": 1}]}).status_code == 400
    r = seeded.post("/api/menu", json={"name": "Nachos", "price": 8, "ingredients": [{"item_id": items[0]["id"], "qty": 0.5}]})
    assert r.status_code == 201
    mid = r.json["menu_item"]["id"]
    assert r.json["menu_item"]["plate_cost"] == round(items[0]["cost"] * 0.5, 4)
    assert seeded.put(f"/api/menu/{mid}", json={"name": "Nachos", "price": 9}).json["menu_item"]["price"] == 9
    assert seeded.delete(f"/api/menu/{mid}").status_code == 200


def test_stops_and_load_list(seeded):
    stops = seeded.get("/api/stops").json["stops"]
    fest = next(s for s in stops if "Festival" in s["name"])
    ll = seeded.get(f"/api/stops/{fest['id']}/loadlist").json
    beef = next(r for r in ll["rows"] if r["name"] == "Ground beef")
    assert beef["load"] == 45 and beef["short"] == 45 - beef["on_hand"] and beef["par_source"] == "stop"
    html = seeded.get(f"/print/loadlist/{fest['id']}?date=2026-10-25").data.decode()
    assert "Ground beef" in html and "2026-10-25" in html and "window.print" in html
    items = seeded.get("/api/items").json["items"]
    r = seeded.post("/api/stops", json={"name": "Wedding", "pars": {items[0]["id"]: 3}})
    assert r.status_code == 201
    assert seeded.post("/api/stops", json={"name": "Bad", "pars": {items[0]["id"]: -1}}).status_code == 400
    assert seeded.get("/print/loadlist/nope").status_code == 404


def test_receive_photo_and_ai_off_by_default(client, tmp_path):
    it = client.post("/api/items", json={"name": "Beef", "unit": "lb", "par": 1, "category": "P", "zone": "cooler"}).json["item"]
    rec = client.post("/api/receives", json={"item_id": it["id"], "qty": 5, "unit_cost": 4.5, "vendor": "Acme"}).json
    assert rec["item"]["cost"] == 4.5
    rid = rec["receive"]["id"]
    bad = client.post(f"/api/receives/{rid}/photos", data={"photo": (io.BytesIO(b"x"), "a.exe")}, content_type="multipart/form-data")
    assert bad.status_code == 400
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    up = client.post(f"/api/receives/{rid}/photos", data={"photo": (io.BytesIO(png), "inv.png")}, content_type="multipart/form-data")
    assert up.status_code == 201
    name = up.json["photo"]
    assert (tmp_path / "photos" / name).exists()
    assert client.get(f"/photos/{name}").status_code == 200
    # AI is off by default → 409, no network call
    assert client.get("/api/settings/ai").json["ai_reader"]["enabled"] is False
    r = client.post(f"/api/receives/{rid}/photos/{name}/read", json={})
    assert r.status_code == 409
    # cannot enable without key; key never echoed back
    assert client.put("/api/settings/ai", json={"enabled": True}).status_code == 400
    r = client.put("/api/settings/ai", json={"enabled": True, "api_key": "sk-test-123"})
    assert r.json["ai_reader"]["has_key"] is True
    assert "sk-test-123" not in client.get("/api/settings").get_data(as_text=True)
    assert "sk-test-123" not in client.get("/api/dashboard").get_data(as_text=True)


def test_locales_have_same_keys():
    import json
    from conftest import ROOT
    en = json.loads((ROOT / "locales/en.json").read_text())
    es = json.loads((ROOT / "locales/es.json").read_text())
    assert set(en) == set(es)


def test_v03_reorder_groups_by_vendor(seeded):
    r = seeded.get("/api/reorder").json
    assert r["ok"] and r["line_count"] >= 1
    names = [l["name"] for g in r["groups"] for l in g["lines"]]
    assert "Ground beef" in names
    for g in r["groups"]:
        for l in g["lines"]:
            assert l["order_qty"] > 0 and l["on_hand"] < l["par"]
    d = seeded.get("/api/dashboard").json
    assert d["version"] and d["inventory_value"] > 0 and d["menu_count"] == 4 and d["stop_count"] == 3
