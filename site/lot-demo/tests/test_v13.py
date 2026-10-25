"""v1.3: edit on the Reconcile screen (pending state) — nothing saves until Confirm."""
import json

from tests.test_v11 import REPLY, connect, mock_ai  # noqa: F401
from tests.test_v12 import INV1, INV2, walk, upload


def setup(client, mock_ai):
    walk(client)
    connect(client, mock_ai)
    REPLY["content"] = json.dumps(INV1)
    upload(client, "a.png", b"png")
    REPLY["content"] = json.dumps(INV2)
    upload(client, "b.png", b"png")
    return {i["name"]: i for i in client.get("/api/items").json["items"]}


def pend(client, **kw):
    r = client.post("/api/setup/reconcile/pending", json=kw)
    assert r.status_code == 200, r.json
    assert r.json["saved"] is False
    return r.json


def rows(rep):
    return {r["name"]: r for s in rep["sections"] for r in s["items"]}


def test_edit_move_unit_flag_nothing_persists(client, mock_ai):
    items = setup(client, mock_ai)
    snap = client.get("/api/items").json["items"]
    ch = items["Chicken thigh"]["id"]
    rep = pend(client, op="edit", id=ch, changes={"unit": "case", "on_hand": 2})
    r = rows(rep)["Chicken thigh"]
    assert r["unit"] == "case" and r["spoken_qty"] == 2 and "unit_differs" in r["flags"]  # invoice says lb
    rep = pend(client, op="edit", id=ch, changes={"unit": "lb", "name": "Chicken thigh boneless", "zone": "line",
                                                    "cost": 3.1, "pack": "4x10 lb", "vendor": "Local Farm"})
    r = rows(rep)["Chicken thigh boneless"]
    assert r["flags"] == [] and r["zone"] == "line" and r["cost"] == 3.1 and not r["cost_from_invoice"]
    assert r["vendor"] == "Local Farm" and r["pack"] == "4x10 lb"
    assert [s for s in rep["sections"] if s["key"] == "line"][0]["items"][0]["name"] == "Chicken thigh boneless"
    assert rep["pending"]["edits"] == 1
    assert client.get("/api/items").json["items"] == snap  # nothing saved
    bad = client.post("/api/setup/reconcile/pending", json={"op": "edit", "id": ch, "changes": {"cost": "abc"}})
    assert bad.status_code == 400
    assert client.post("/api/setup/reconcile/pending", json={"op": "edit", "id": ch, "changes": {"zone": "nope"}}).status_code == 400
    r = client.post("/api/setup/reconcile/apply", json={"instructions": []})
    assert r.status_code == 200, r.json
    it = {i["name"]: i for i in client.get("/api/items").json["items"]}["Chicken thigh boneless"]
    assert it["zone"] == "line" and it["cost"] == 3.1 and it["unit"] == "lb" and it["on_hand"] == 2 and it["pack"] == "4x10 lb"
    assert "_locked" not in it and "_edited" not in it
    v = next(x for x in client.get("/api/vendors").json["vendors"] if x["id"] == it["vendor_id"])
    assert v["name"] == "Local Farm"
    assert client.get("/api/setup/reconcile").json["pending"]["total"] == 0


def test_delete_restore_add_merge(client, mock_ai):
    items = setup(client, mock_ai)
    snap = client.get("/api/items").json["items"]
    salsa, corn = items["Salsa verde"]["id"], items["Corn tortillas"]["id"]
    rep = pend(client, op="delete", id=salsa)
    assert "Salsa verde" not in rows(rep) and rep["deleted"][0]["name"] == "Salsa verde" and rep["stats"]["no_cost"] == 0
    rep = pend(client, op="restore", id=salsa)
    assert "Salsa verde" in rows(rep)
    rep = pend(client, op="add", name="Flour tortillas", zone="dry-shelf", unit="case", on_hand=2)
    new = rows(rep)["Flour tortillas"]
    assert new["pending_new"] and new["spoken_qty"] == 2 and rep["stats"]["products"] == 4
    pend(client, op="edit", id=new["id"], changes={"cost": 30})
    assert client.post("/api/setup/reconcile/pending", json={"op": "add", "name": "", "zone": "line"}).status_code == 400
    # merge salsa verde into corn (silly, but proves count + alias carry)
    rep = pend(client, op="merge", id=salsa, into=corn)
    assert "Salsa verde" not in rows(rep) and rows(rep)["Corn tortillas"]["spoken_qty"] == 5
    assert client.get("/api/items").json["items"] == snap
    client.post("/api/setup/reconcile/apply", json={"instructions": []})
    its = {i["name"]: i for i in client.get("/api/items").json["items"]}
    assert "Salsa verde" not in its and its["Corn tortillas"]["on_hand"] == 5 and "Salsa verde" in its["Corn tortillas"]["aliases"]
    assert its["Flour tortillas"]["cost"] == 30 and its["Flour tortillas"]["zone"] == "dry-shelf" and its["Flour tortillas"]["on_hand"] == 2


def test_unlink_relink_and_link_unplaced_to_pending_new(client, mock_ai):
    items = setup(client, mock_ai)
    rep = client.get("/api/setup/reconcile").json
    corn = rows(rep)["Corn tortillas"]
    assert corn["from_invoice"]
    rep = pend(client, op="unlink", keys=corn["invoice_keys"])
    assert not rows(rep)["Corn tortillas"]["from_invoice"]
    un = {g["name"]: g for g in rep["unplaced"]}
    assert "Corn Tortillas 6in 12x80ct" in un and un["Corn Tortillas 6in 12x80ct"]["unlinked"]
    # relink corn invoice line to chicken (wrong on purpose) then back
    k = un["Corn Tortillas 6in 12x80ct"]["key"]
    rep = pend(client, op="link", key=k, item_id=items["Salsa verde"]["id"])
    assert rows(rep)["Salsa verde"]["from_invoice"] and rows(rep)["Salsa verde"]["cost"] == 36.0
    # lime: add a new product, link the invoice line to it
    rep = pend(client, op="add", name="Limes", zone="lowboy-cooler", unit="case", on_hand=1)
    assert rows(rep)["Limes"]["cost"] == 31.0 and all(g["name"] != "Lime 200ct" for g in rep["unplaced"])  # auto-matched
    rep = pend(client, op="add", name="Cleaning", zone="line", unit="ea")
    cid = rows(rep)["Cleaning"]["id"]
    sk = next(g["key"] for g in rep["unplaced"] if g["name"].startswith("Sanitizer"))
    rep = pend(client, op="link", key=sk, item_id=cid)
    assert rows(rep)["Cleaning"]["cost"] == 14.0 and "unit_differs" in rows(rep)["Cleaning"]["flags"]
    client.post("/api/setup/reconcile/apply", json={"instructions": []})
    its = {i["name"]: i for i in client.get("/api/items").json["items"]}
    assert its["Limes"]["cost"] == 31.0 and its["Salsa verde"]["cost"] == 36.0 and its["Corn tortillas"]["cost"] is None and its["Cleaning"]["cost"] == 14.0


def test_reset_and_unknown(client, mock_ai):
    items = setup(client, mock_ai)
    pend(client, op="delete", id=items["Salsa verde"]["id"])
    rep = pend(client, op="reset")
    assert rep["pending"]["total"] == 0 and "Salsa verde" in rows(rep)
    assert client.post("/api/setup/reconcile/pending", json={"op": "zap"}).status_code == 400
