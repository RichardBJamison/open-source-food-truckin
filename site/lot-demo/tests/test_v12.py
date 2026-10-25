"""v1.2: product invoices uploaded in the setup walk + Reconcile step (fake AI endpoint)."""
import io
import json

from tests.test_v11 import REPLY, CALLS, connect, mock_ai  # noqa: F401  (fixture re-export)
from osft import setup_reconcile as recon

INV1 = {"vendor": "Sysco", "invoice_no": "A1", "date": "2026-10-01", "lines": [
    {"description": "Corn Tortillas 6in 12x80ct", "qty": 2, "unit": "case", "unit_cost": 38.5, "total": 77},
    {"description": "Chicken Thigh Boneless", "qty": 40, "unit": "lb", "unit_cost": 2.89, "total": 115.6},
    {"description": "Fryer Oil 35 lb", "qty": 1, "unit": "ea", "unit_cost": 42.0, "total": 42},
    {"description": "Sanitizer Quat 1 gal", "qty": 2, "unit": "gal", "unit_cost": 14.0, "total": 28}]}
INV2 = {"vendor": "Restaurant Depot", "lines": [
    {"description": "corn tortillas 6 in", "qty": 1, "unit": "case", "unit_cost": 36.0},
    {"description": "Lime 200ct", "qty": 1, "unit": "case", "unit_cost": 31.0}]}


def walk(client):
    client.put("/api/sections", json={"sections": ["Lowboy cooler", "Dry shelf", "Line"]})
    for name, z, q, u in [("Corn tortillas", "dry-shelf", 3, "case"), ("Chicken thigh", "lowboy-cooler", 20, "lb"),
                          ("Salsa verde", "line", 2, "qt")]:
        r = client.post("/api/items", json={"name": name, "zone": z, "unit": u, "on_hand": q, "par": 0, "category": "Food"})
        assert r.status_code == 201, r.json


def upload(client, name, data, ctype=None):
    return client.post("/api/setup/invoices", data={"files": [(io.BytesIO(data), name)]}, content_type="multipart/form-data")


def test_order_has_reconcile_after_walk(client):
    ph = client.get("/api/onboarding").json["phases"]
    assert ph.index("reconcile") == ph.index("walk") + 1 and ph.index("review") == ph.index("reconcile") + 1


def test_upload_with_ai_and_reconcile_merge_dedupe(client, mock_ai):
    walk(client)
    connect(client, mock_ai)
    REPLY["content"] = json.dumps(INV1)
    r = upload(client, "sysco.jpg", b"\xff\xd8fakejpeg")
    assert r.status_code == 201, r.json
    assert r.json["added"][0]["source"] == "ai" and len(r.json["added"][0]["lines"]) == 4 and r.json["added"][0]["vendor"] == "Sysco"
    REPLY["content"] = json.dumps(INV2)
    assert upload(client, "depot.png", b"png").status_code in (201,)
    items_before = client.get("/api/items").json["items"]
    rep = client.get("/api/setup/reconcile").json
    assert rep["saved"] is False
    rows = {r["name"]: r for s in rep["sections"] for r in s["items"]}
    assert rows["Corn tortillas"]["from_invoice"] and rows["Corn tortillas"]["cost"] == 36.0  # latest cost wins
    assert rows["Corn tortillas"]["invoice_qty"] == 3  # two invoices deduped and summed
    assert rows["Chicken thigh"]["cost"] == 2.89 and rows["Chicken thigh"]["vendor"] == "Sysco"
    assert not rows["Salsa verde"]["from_invoice"] and "no_cost" in rows["Salsa verde"]["flags"]
    names = sorted(g["name"] for g in rep["unplaced"])
    assert names == ["Fryer Oil 35 lb", "Lime 200ct", "Sanitizer Quat 1 gal"]
    assert rep["stats"]["to_place"] == 3 and rep["stats"]["no_cost"] == 1 and rep["stats"]["invoices"] == 2
    # nothing saved yet
    assert client.get("/api/items").json["items"] == items_before


def test_unplaced_instructions_apply(client, mock_ai):
    walk(client)
    connect(client, mock_ai)
    REPLY["content"] = json.dumps(INV1)
    upload(client, "a.png", b"png")
    REPLY["content"] = json.dumps(INV2)
    upload(client, "b.png", b"png")
    rep = client.get("/api/setup/reconcile").json
    k = {g["name"]: g["key"] for g in rep["unplaced"]}
    bad = client.post("/api/setup/reconcile/apply", json={"instructions": [{"key": k["Lime 200ct"], "action": "section", "section": "zzz"}]})
    assert bad.status_code == 400
    r = client.post("/api/setup/reconcile/apply", json={"instructions": [
        {"key": k["Lime 200ct"], "action": "section", "section": "lowboy-cooler", "name": "Limes"},
        {"key": k["Fryer Oil 35 lb"], "action": "new_section", "section_name": "Fryer station"},
        {"key": k["Sanitizer Quat 1 gal"], "action": "not_stocked"}]})
    assert r.status_code == 200, r.json
    assert r.json["saved"] and r.json["updated"] == 2 and len(r.json["created"]) == 2
    assert "Sysco" in r.json["vendors_created"]
    items = {i["name"]: i for i in client.get("/api/items").json["items"]}
    assert items["Limes"]["zone"] == "lowboy-cooler" and items["Limes"]["cost"] == 31.0 and items["Limes"]["on_hand"] == 0
    assert items["Fryer Oil 35 lb"]["zone"] == "fryer-station"
    assert items["Corn tortillas"]["cost"] == 36.0 and items["Corn tortillas"]["on_hand"] == 3  # spoken count untouched
    assert items["Chicken thigh"]["vendor_id"]
    assert "Sanitizer Quat 1 gal" not in items
    assert any(s["key"] == "fryer-station" for s in client.get("/api/sections").json["sections"])
    rep = client.get("/api/setup/reconcile").json
    assert rep["unplaced"] == [] and [g["name"] for g in rep["not_stocked"]] == ["Sanitizer Quat 1 gal"]


def test_commissary_skip_and_same_as(client, mock_ai):
    walk(client)
    connect(client, mock_ai)
    REPLY["content"] = json.dumps({"vendor": "X", "lines": [{"description": "Paper boats #2", "qty": 1, "unit": "case", "unit_cost": 20},
                                                             {"description": "Napkins", "qty": 1, "unit": "case", "unit_cost": 15},
                                                             {"description": "Crema mexicana tub", "qty": 2, "unit": "qt", "unit_cost": 6}]})
    upload(client, "x.jpg", b"j")
    rep = client.get("/api/setup/reconcile").json
    k = {g["name"]: g for g in rep["unplaced"]}
    salsa = client.get("/api/items").json["items"]
    sid = next(i["id"] for i in salsa if i["name"] == "Salsa verde")
    r = client.post("/api/setup/reconcile/apply", json={"instructions": [
        {"key": k["Paper boats #2"]["key"], "action": "commissary"},
        {"key": k["Napkins"]["key"], "action": "skip"},
        {"key": k["Crema mexicana tub"]["key"], "action": "same_as", "item_id": sid}]})
    assert r.status_code == 200, r.json
    items = {i["name"]: i for i in client.get("/api/items").json["items"]}
    assert items["Paper boats #2"]["zone"] == "commissary" and "Commissary" in items["Paper boats #2"]["notes"]
    assert items["Salsa verde"]["cost"] == 6 and "Crema mexicana tub" in items["Salsa verde"]["aliases"]
    rep = client.get("/api/setup/reconcile").json
    assert [g["name"] for g in rep["unplaced"]] == ["Napkins"]  # skipped = asked again


def test_ai_off_csv_text_and_photo(client):
    walk(client)
    csv = b"Item Description,Qty,Unit,Unit Price\nCorn Tortillas 6in,2,cs,38.50\nLimes 200ct,1,cs,31.00\n"
    r = upload(client, "inv.csv", csv)
    assert r.status_code == 201 and r.json["ai_enabled"] is False
    assert r.json["added"][0]["source"] == "csv" and len(r.json["added"][0]["lines"]) == 2
    r = upload(client, "photo.jpg", b"\xff\xd8")
    a = r.json["added"][0]
    assert a["lines"] == [] and "needs AI" in a["note"]
    r = client.post("/api/setup/invoices/text", json={"vendor": "Depot", "text": "2 cs Ground beef 4.89\n1 bag Onions 12.00\nTotal 50"})
    assert r.status_code == 201 and [l["description"] for l in r.json["added"][0]["lines"]] == ["Ground beef", "Onions"]
    assert client.post("/api/setup/invoices/text", json={"text": "hello"}).status_code == 400
    rep = client.get("/api/setup/reconcile").json
    assert rep["stats"]["from_invoice"] == 1 and {g["name"] for g in rep["unplaced"]} == {"Limes 200ct", "Ground beef", "Onions"}
    iid = r.json["added"][0]["id"]
    assert client.delete(f"/api/setup/invoices/{iid}").status_code == 200
    assert len(client.get("/api/setup/invoices").json["invoices"]) == 2
    assert upload(client, "x.exe", b"MZ").status_code == 400


def test_parse_text_layer_layouts():
    txt = """SYSCO  INVOICE 12345
    Item   Description              Qty  Unit   Price   Ext
    10234  CHICKEN THIGH BNLS 4x10LB  2   cs   58.20  116.40
    Corn tortillas 6in               3   cs   38.50  115.50
    Subtotal 231.90"""
    lines, unread = recon.parse_text(txt)
    names = [l["description"] for l in lines]
    assert "CHICKEN THIGH BNLS 4x10LB" in names and "Corn tortillas 6in" in names
    ch = next(l for l in lines if l["description"].startswith("CHICKEN"))
    assert ch["qty"] == 2 and ch["unit_cost"] == 58.2 and ch["pack"]
