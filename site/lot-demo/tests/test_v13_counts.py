"""v1.3 count types: daily partial (end of shift), weekly full, monthly in-depth; scope, roles, variance math."""
import io


def mk(client, n=4):
    ids = []
    for k in range(n):
        r = client.post("/api/items", json={"name": f"P{k}", "unit": "ea", "par": 8, "category": "Protein" if k < 2 else "Dry",
                                            "zone": "dry", "cost": 1.0})
        ids.append(r.json["item"]["id"])
    return ids


def count(client, typ, date, counts, **kw):
    r = client.post("/api/counts/start", json={"type": typ, "date": date, **kw})
    assert r.status_code in (200, 201), r.json
    sid = r.json["session"]["id"]
    r = client.put(f"/api/counts/{sid}", json={"counts": counts})
    assert r.status_code == 200, r.json
    r = client.post(f"/api/counts/{sid}/complete")
    assert r.status_code == 200
    return r.json


def sell(client, ids, date, qty):
    if not client.get("/api/menu").json.get("menu"):
        client.post("/api/menu", json={"name": "Plate", "price": 10, "ingredients": [{"item_id": i, "qty": 1} for i in ids]})
    csv = f"Day,Product,Sold,Amount\n{date},Plate,{qty},{qty*10}\n"
    r = client.post("/api/pos/import", data={"file": (io.BytesIO(csv.encode()), "s.csv")}, content_type="multipart/form-data")
    assert r.status_code == 201, r.json


def test_types_default_and_settings(client):
    ids = mk(client)
    r = client.get("/api/count-types").json
    keys = [x["key"] for x in r["count_types"]]
    assert keys == ["daily", "weekly", "monthly"]
    daily = r["count_types"][0]
    assert daily["full"] is False and daily["item_count"] == 2 and daily["timing"] == "end_of_shift"
    assert r["count_types"][2]["checklist"]
    types = r["count_types"]
    types[0] = {**daily, "categories": [], "items": [ids[3]]}
    r = client.put("/api/count-types", json={"count_types": types})
    assert r.status_code == 200 and r.json["count_types"][0]["item_count"] == 1
    bad = [{**types[0], "items": []}] + types[1:]
    assert client.put("/api/count-types", json={"count_types": bad}).status_code == 400
    nofull = [{**x, "enabled": False} if x["full"] else x for x in types]
    assert client.put("/api/count-types", json={"count_types": nofull}).status_code == 400


def test_partial_does_not_zero_or_flag_and_scope_enforced(client):
    ids = mk(client)
    full = count(client, "weekly", "2026-10-01", {i: 10 for i in ids})
    assert full["session"]["summary"]["missing_in_scope"] == []
    s = client.post("/api/counts/start", json={"type": "daily", "date": "2026-10-02"}).json["session"]
    assert s["scope"]["full"] is False and set(s["scope"]["item_ids"]) == set(ids[:2])
    assert client.put(f"/api/counts/{s['id']}", json={"counts": {ids[3]: 1}}).status_code == 400  # outside scope
    client.put(f"/api/counts/{s['id']}", json={"counts": {ids[0]: 7}})   # P1 left blank
    done = client.post(f"/api/counts/{s['id']}/complete").json
    assert done["session"]["summary"]["missing_in_scope"] == [] and done["session"]["summary"]["not_counted_kept"] == 1
    oh = {i["id"]: i["on_hand"] for i in client.get("/api/items").json["items"]}
    assert oh[ids[0]] == 7 and oh[ids[1]] == 10 and oh[ids[3]] == 10   # nothing zeroed
    v = {r["item_id"]: r for r in done["variance"]}
    assert set(v) == {ids[0]} and v[ids[0]]["prior"] == 10
    # a full count with a blank IS flagged missing
    w = count(client, "weekly", "2026-10-03", {i: 5 for i in ids[:3]})
    assert w["session"]["summary"]["missing_in_scope"] == ["P3"]
    v = {r["item_id"]: r for r in w["variance"]}
    assert v[ids[0]]["prior"] == 7 and v[ids[2]]["prior"] == 10        # per-item prior, not "last session"
    h = client.get("/api/counts/history").json["history"]
    assert [x["type"] for x in h] == ["weekly", "daily", "weekly"] and h[1]["full"] is False and h[1]["scope_label"]


def test_sales_variance_skips_partials_and_end_of_shift_window(client):
    ids = mk(client)
    count(client, "weekly", "2026-10-05", {i: 10 for i in ids})            # Monday before service
    sell(client, ids, "2026-10-05", 2)
    sell(client, ids, "2026-10-06", 3)
    count(client, "daily", "2026-10-06", {ids[0]: 5, ids[1]: 4})            # end of shift Tue (P1 short 1 — real)
    count(client, "weekly", "2026-10-07", {ids[0]: 5, ids[1]: 4, ids[2]: 5, ids[3]: 3})   # Wed before service
    sv = client.get("/api/variance/sales").json
    assert sv["ready"] and sv["start"]["type"] == "weekly" and sv["end"]["type"] == "weekly"
    assert len(sv["skipped_partials"]) == 1
    rows = {r["item_id"]: r for r in sv["rows"]}
    assert rows[ids[0]]["theoretical"] == 5 and rows[ids[0]]["variance"] == 0
    assert rows[ids[1]]["variance"] == 1 and rows[ids[3]]["variance"] == 2 and rows[ids[2]]["variance"] == 0
    # daily-only window (partial end): start = weekly Mon, end-of-shift Tue includes Tue sales
    daily = [h for h in client.get("/api/counts/history").json["history"] if h["type"] == "daily"][0]
    sv2 = client.get(f"/api/variance/sales?end={daily['id']}").json
    rows2 = {r["item_id"]: r for r in sv2["rows"]}
    assert set(i for i, r in rows2.items() if r.get("variance") is not None) == set(ids[:2])
    assert rows2[ids[0]]["theoretical"] == 5 and rows2[ids[0]]["variance"] == 0 and rows2[ids[1]]["variance"] == 1


def test_crew_limited_to_daily(client):
    mk(client)
    client.post("/api/people", json={"name": "Rich", "login": "rich", "role": "admin", "pin": "123456"})
    r = client.post("/api/people", json={"name": "Ana", "login": "ana", "role": "crew", "pin": "654321", "count_types": ["daily"]})
    assert r.json["person"]["count_types"] == ["daily"]
    client.post("/api/auth/login", json={"pin": "654321"})
    t = {x["key"]: x["allowed"] for x in client.get("/api/count-types").json["count_types"]}
    assert t == {"daily": True, "weekly": False, "monthly": False}
    assert client.post("/api/counts/start", json={"type": "weekly"}).status_code == 403
    s = client.post("/api/counts/start", json={"type": "daily"})
    assert s.status_code in (200, 201) and s.json["session"]["counted_by"] == "Ana"
    assert client.put("/api/count-types", json={"count_types": []}).status_code == 403
