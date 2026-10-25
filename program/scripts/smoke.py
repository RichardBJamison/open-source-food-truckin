#!/usr/bin/env python3
"""OSFT smoke script — hits health + core API routes; exits 0 on success."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5053"
PASS = 0
FAIL = 0


def req(method: str, path: str, body: dict | None = None):
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"error": raw}
        return e.code, payload


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))


def main():
    print(f"OSFT smoke against {BASE}")
    print("-" * 48)

    # T-001 health + root
    try:
        status, body = req("GET", "/api/health")
        check("T-001 GET /api/health → 200", status == 200 and body.get("ok") is True, f"v={body.get('version')}")
    except Exception as e:
        check("T-001 GET /api/health → 200", False, str(e))
        print("Server not reachable. Start with: python server.py")
        sys.exit(1)

    try:
        r = urllib.request.Request(BASE + "/", method="GET")
        with urllib.request.urlopen(r, timeout=5) as resp:
            check("T-001 GET / → 200", resp.status == 200)
    except Exception as e:
        check("T-001 GET / → 200", False, str(e))

    # Reset for clean empty state
    status, _ = req("POST", "/api/reset", {})
    check("reset store", status == 200)

    # T-002 empty
    status, body = req("GET", "/api/items")
    check("T-002 empty inventory", status == 200 and body.get("empty") is True)

    status, body = req("GET", "/api/dashboard")
    check("T-002 dashboard empty", status == 200 and body.get("empty") is True)

    # T-006 validation (no 500)
    status, body = req("POST", "/api/items", {"name": ""})
    check("T-006 validation rejects empty name", status == 400 and "error" in body)

    status, body = req("POST", "/api/items", {"name": "X", "unit": "lb", "par": "nope", "category": "A", "zone": "cooler"})
    check("T-006 invalid PAR → 400", status == 400)

    # T-003 create
    status, body = req(
        "POST",
        "/api/items",
        {"name": "Test salsa", "unit": "qt", "par": 4, "category": "Sauce", "zone": "prep", "on_hand": 1},
    )
    check("T-003 create item", status == 201 and body.get("item", {}).get("id"))
    item_id = body.get("item", {}).get("id")

    # T-004 edit
    status, body = req("PUT", f"/api/items/{item_id}", {"par": 5, "name": "Test salsa verde"})
    check("T-004 edit item", status == 200 and body.get("item", {}).get("par") == 5)

    # T-009 zones
    status, body = req("GET", "/api/zones")
    check("T-009 zones map", status == 200 and "prep" in (body.get("by_zone") or {}))

    # T-016 setup
    status, body = req("PUT", "/api/settings", {"truck_name": "Smoke Truck", "units": "imperial"})
    check("T-016 setup persist", status == 200 and body.get("settings", {}).get("truck_name") == "Smoke Truck")
    status, body = req("GET", "/api/settings")
    check("T-016 setup reload", body.get("settings", {}).get("truck_name") == "Smoke Truck")

    # T-014 seed
    status, body = req("POST", "/api/seed", {})
    check(
        "T-014 demo seed ≥8 / 4 zones",
        status == 200 and body.get("seeded", 0) >= 8 and len(body.get("zones") or []) == 4,
        f"seeded={body.get('seeded')} zones={body.get('zones')}",
    )

    # T-012 receive
    items = req("GET", "/api/items")[1].get("items") or []
    target = items[0]
    before = float(target.get("on_hand") or 0)
    status, body = req("POST", "/api/receives", {"item_id": target["id"], "qty": 3, "note": "smoke"})
    after = float(body.get("item", {}).get("on_hand") or 0)
    check("T-012 receive bumps on-hand", status == 201 and after == before + 3)

    # T-013 low-PAR
    status, body = req("GET", "/api/dashboard")
    check("T-013 low-PAR dashboard", status == 200 and "low_par" in body)

    # T-010 count walk
    status, body = req("POST", "/api/counts/start", {})
    check("T-010 start count", status == 201)
    sid = body.get("session", {}).get("id")
    counts = {i["id"]: float(i.get("on_hand") or 0) for i in items[:5]}
    status, _ = req("PUT", f"/api/counts/{sid}", {"counts": counts})
    check("T-010 save count qtys", status == 200)
    status, body = req("POST", f"/api/counts/{sid}/complete", {})
    check("T-010 complete count", status == 200 and body.get("session", {}).get("status") == "completed")

    status, body = req("GET", "/api/counts/latest")
    check("T-010 latest count after reload", status == 200 and body.get("session") is not None)

    # T-011 variance
    status, body = req("GET", "/api/variance")
    check("T-011 variance present", status == 200 and isinstance(body.get("variance"), list) and len(body["variance"]) > 0)

    # T-015 i18n
    status, body = req("GET", "/api/locales/en")
    check("T-015 locale en", status == 200 and body.get("strings"))
    status, body = req("GET", "/api/locales/es")
    check("T-015 locale es stubs", status == 200 and body.get("strings"))

    # T-005 archive
    status, body = req("DELETE", f"/api/items/{item_id}")
    # item may have been replaced by seed — create fresh then delete
    if status != 200:
        st, created = req(
            "POST",
            "/api/items",
            {"name": "Temp del", "unit": "ea", "par": 1, "category": "X", "zone": "dry"},
        )
        item_id = created.get("item", {}).get("id")
        status, body = req("DELETE", f"/api/items/{item_id}")
    check("T-005 archive/delete", status == 200 and body.get("archived") is True)

    print("-" * 48)
    print(f"Result: {PASS} passed, {FAIL} failed")
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
