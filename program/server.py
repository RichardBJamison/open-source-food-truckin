#!/usr/bin/env python3
"""Open Source Food Truckin (OSFT) 1.0 — local-first food-truck inventory (Flask)."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, Response, has_request_context, jsonify, request, send_from_directory, session

from osft import accounts as acct
from osft import ai as ai_mod
from osft import sections as sections_mod
from osft import ai_reader
from osft import starter_catalog
from osft import voice
from osft import setup_reconcile as recon
from osft import count_types as ctypes
from osft import pos_adapters as pos
from osft import library as library_mod
from osft import public_demo

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STORE_PATH = DATA_DIR / "store.json"
LOCALES_DIR = BASE_DIR / "locales"
STATIC_DIR = BASE_DIR / "static"
VERSION = (BASE_DIR / "VERSION.txt").read_text(encoding="utf-8").strip()

ZONES = ("cooler", "freezer", "dry", "prep")          # the four core zones (always present)
EXTRA_ZONES = ("outside", "window", "commissary")     # optional areas a truck can turn on
VALID_UNITS_PREF = ("imperial", "metric")

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def empty_store() -> dict:
    return {
        "settings": {
            "truck_name": "",
            "units": "imperial",
            "locale": "en",
            "setup_complete": False,
            "zones": list(ZONES),
        },
        "items": [],
        "count_sessions": [],
        "receives": [],
        "menu_items": [],
        "sales_imports": [],
        "stop_types": [],
        "purchase_orders": [],
        "transfers": [],
    }


def active_store_path() -> Path:
    tid = active_truck_id()
    if tid == "main":
        return STORE_PATH
    return DATA_DIR / "trucks" / f"{tid}.json"


def load_store() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = active_store_path()
    if not path.exists():
        store = empty_store()
        save_store(store)
        return store
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = empty_store()
        save_store(data)
        return data
    # Ensure required keys
    base = empty_store()
    for k, v in base.items():
        if k not in data:
            data[k] = v
    for k, v in base["settings"].items():
        data["settings"].setdefault(k, v)
    return data


def save_store(store: dict) -> None:
    path = active_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(store, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def public_settings(settings: dict) -> dict:
    """Settings safe to send to the browser (never the AI API key)."""
    out = {k: v for k, v in settings.items() if k != "ai_reader"}
    out["ai_reader"] = ai_reader.public_config(settings.get("ai_reader"))
    return out


def err(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def active_items(store: dict) -> list:
    return [i for i in store["items"] if not i.get("archived")]


def find_item(store: dict, item_id: str):
    for item in store["items"]:
        if item["id"] == item_id:
            return item
    return None


def store_sections(store: dict | None = None) -> list:
    """Ordered [{key, name}] — owner-defined truck sections, or the legacy zones."""
    store = store or load_store()
    secs = store.get("settings", {}).get("sections")
    if isinstance(secs, list) and secs:
        return [dict(x) for x in secs]
    return sections_mod.from_zones(_legacy_zones(store))


def store_zones(store: dict | None = None) -> list:
    store = store or load_store()
    return [x["key"] for x in store_sections(store)]


def default_zone(zones: list) -> str:
    return "dry" if "dry" in zones else (zones[0] if zones else "dry")


def _legacy_zones(store: dict) -> list:
    zs = [z for z in (store.get("settings", {}).get("zones") or list(ZONES)) if z]
    for z in ZONES:
        if z not in zs:
            zs.insert(ZONES.index(z), z)
    return zs


def validate_item_payload(data: dict, partial: bool = False, zones=None) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    name = data.get("name")
    unit = data.get("unit")
    category = data.get("category")
    zone = data.get("zone")
    par = data.get("par")

    out: dict = {}

    if not partial or "name" in data:
        if name is None or str(name).strip() == "":
            return None, "Name is required."
        out["name"] = str(name).strip()

    if not partial or "unit" in data:
        if unit is None or str(unit).strip() == "":
            return None, "Unit is required."
        out["unit"] = str(unit).strip()

    if not partial or "category" in data:
        if category is None or str(category).strip() == "":
            return None, "Category is required."
        out["category"] = str(category).strip()

    if not partial or "zone" in data:
        z = str(zone or "").strip().lower()
        allowed = zones or list(ZONES)
        if z not in allowed:
            return None, f"Zone must be one of: {', '.join(allowed)}."
        out["zone"] = z

    if not partial or "par" in data:
        try:
            par_val = float(par)
        except (TypeError, ValueError):
            return None, "PAR/min must be a number."
        if par_val < 0:
            return None, "PAR/min cannot be negative."
        out["par"] = par_val

    if "cost" in data:
        if data["cost"] in (None, ""):
            out["cost"] = None
        else:
            try:
                c = float(data["cost"])
            except (TypeError, ValueError):
                return None, "Unit cost must be a number."
            if c < 0:
                return None, "Unit cost cannot be negative."
            out["cost"] = c

    if "on_hand" in data:
        try:
            oh = float(data["on_hand"])
        except (TypeError, ValueError):
            return None, "On-hand must be a number."
        if oh < 0:
            return None, "On-hand cannot be negative."
        out["on_hand"] = oh

    # v1.0 product fields (all optional)
    if "case_size" in data:
        if data["case_size"] in (None, ""):
            out["case_size"] = None
        else:
            try:
                cs = float(data["case_size"])
            except (TypeError, ValueError):
                return None, "Units per case must be a number."
            if cs <= 0:
                return None, "Units per case must be greater than zero."
            out["case_size"] = cs
    for key in ("vendor_id", "barcode", "notes", "name_es", "pack", "sku"):
        if key in data:
            out[key] = str(data[key] or "").strip() or None
    if "aliases" in data:
        al = data["aliases"]
        if isinstance(al, str):
            al = [a for a in (x.strip() for x in al.replace(";", ",").split(",")) if a]
        if not isinstance(al, list):
            return None, "aliases must be a list or comma-separated text."
        out["aliases"] = [str(a).strip() for a in al if str(a).strip()][:20]

    return out, None


# ---------- Pages ----------

@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


# ---------- Health ----------

@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "status": "healthy",
            "version": VERSION,
            "service": "osft",
        }
    )


# ---------- Settings / Setup (T-016) ----------

@app.get("/api/settings")
def get_settings():
    store = load_store()
    return jsonify({"ok": True, "settings": public_settings(store["settings"])})


@app.put("/api/settings")
def put_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Request body must be a JSON object.")

    store = load_store()
    settings = store["settings"]

    if "truck_name" in data:
        name = str(data["truck_name"] or "").strip()
        if not name:
            return err("Truck/business name is required.")
        settings["truck_name"] = name

    if "units" in data:
        units = str(data["units"] or "").strip().lower()
        if units not in VALID_UNITS_PREF:
            return err("Units must be 'imperial' or 'metric'.")
        settings["units"] = units

    if "locale" in data:
        locale = str(data["locale"] or "").strip().lower()
        if locale not in ("en", "es"):
            return err("Locale must be 'en' or 'es'.")
        settings["locale"] = locale

    if settings.get("truck_name"):
        settings["setup_complete"] = True

    store["settings"] = settings
    save_store(store)
    return jsonify({"ok": True, "settings": public_settings(settings)})


# ---------- i18n (T-015) ----------

@app.get("/api/locales/<lang>")
def get_locale(lang: str):
    lang = lang.lower()
    path = LOCALES_DIR / f"{lang}.json"
    if not path.exists():
        return err(f"Locale '{lang}' not found.", 404)
    with path.open("r", encoding="utf-8") as f:
        strings = json.load(f)
    return jsonify({"ok": True, "locale": lang, "strings": strings})


# ---------- Catalog CRUD (T-003–T-006) ----------

@app.get("/api/items")
def list_items():
    store = load_store()
    include_archived = request.args.get("archived", "0") == "1"
    items = store["items"] if include_archived else active_items(store)
    return jsonify({"ok": True, "items": items, "empty": len(items) == 0})


@app.post("/api/items")
def create_item():
    data = request.get_json(silent=True)
    store = load_store()
    fields, message = validate_item_payload(data or {}, partial=False, zones=store_zones(store))
    if message:
        return err(message)
    item = {
        "id": str(uuid.uuid4()),
        "name": fields["name"],
        "unit": fields["unit"],
        "par": fields["par"],
        "category": fields["category"],
        "zone": fields["zone"],
        "on_hand": fields.get("on_hand", 0.0),
        "cost": fields.get("cost"),
        "archived": False,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    for k in ("case_size", "vendor_id", "barcode", "notes", "name_es", "pack", "sku", "aliases"):
        if k in fields:
            item[k] = fields[k]
    store["items"].append(item)
    save_store(store)
    return jsonify({"ok": True, "item": item}), 201


@app.get("/api/items/<item_id>")
def get_item(item_id: str):
    store = load_store()
    item = find_item(store, item_id)
    if not item:
        return err("Item not found.", 404)
    return jsonify({"ok": True, "item": item})


@app.put("/api/items/<item_id>")
def update_item(item_id: str):
    data = request.get_json(silent=True)
    store = load_store()
    fields, message = validate_item_payload(data or {}, partial=True, zones=store_zones(store))
    if message:
        return err(message)
    item = find_item(store, item_id)
    if not item or item.get("archived"):
        return err("Item not found.", 404)

    for k, v in fields.items():
        item[k] = v
    item["updated_at"] = utc_now()
    save_store(store)
    return jsonify({"ok": True, "item": item})


@app.delete("/api/items/<item_id>")
def delete_item(item_id: str):
    """Archive (soft-delete) so count history stays coherent."""
    store = load_store()
    item = find_item(store, item_id)
    if not item or item.get("archived"):
        return err("Item not found.", 404)
    item["archived"] = True
    item["updated_at"] = utc_now()
    save_store(store)
    return jsonify({"ok": True, "archived": True, "id": item_id})


# ---------- Zones (T-009) ----------

@app.get("/api/zones")
def get_zones():
    store = load_store()
    items = active_items(store)
    zs = store_zones(store)
    by_zone = {z: [] for z in zs}
    for item in items:
        z = item.get("zone", "dry")
        if z not in by_zone:
            by_zone[z] = []
        by_zone[z].append(item)
    return jsonify({"ok": True, "zones": zs, "by_zone": by_zone})


# ---------- Count walk (T-010) + Variance (T-011) ----------

@app.get("/api/counts")
def list_counts():
    store = load_store()
    sessions = sorted(
        store["count_sessions"],
        key=lambda s: s.get("completed_at") or s.get("started_at") or "",
        reverse=True,
    )
    return jsonify({"ok": True, "sessions": sessions})


@app.get("/api/counts/latest")
def latest_count():
    store = load_store()
    completed = completed_sessions(store)
    if not completed:
        return jsonify({"ok": True, "session": None})
    return jsonify({"ok": True, "session": completed[-1]})


def _bdate(s: dict) -> str:
    return s.get("business_date") or (s.get("completed_at") or s.get("started_at") or "")[:10]


def completed_sessions(store: dict) -> list:
    """Completed counts in business order (business date, then completion time)."""
    return sorted([s for s in store["count_sessions"] if s.get("status") == "completed"],
                  key=lambda s: (_bdate(s), s.get("completed_at") or ""))


def _history_row(s: dict) -> dict:
    sc = s.get("scope") or {}
    return {"id": s["id"], "completed_at": s.get("completed_at"), "business_date": _bdate(s),
            "lines": len(s.get("counts") or {}), "source": s.get("source") or "manual", "by": s.get("counted_by"),
            "example": s.get("example", False), "type": s.get("type") or "weekly",
            "type_name": s.get("type_name") or "Full count", "full": sc.get("full", True),
            "scope_label": sc.get("label") or "Full truck", "timing": s.get("timing") or "before_service",
            "in_scope": len(sc.get("item_ids") or []) or None, "summary": s.get("summary"),
            "checklist_done": s.get("checklist_done") or {}}


@app.get("/api/counts/history")
def counts_history():
    st = load_store()
    rows = [_history_row(s) for s in reversed(completed_sessions(st))]
    t = request.args.get("type")
    return jsonify({"ok": True, "history": [r for r in rows if not t or r["type"] == t]})


def _is_full(s: dict) -> bool:
    return (s.get("scope") or {}).get("full", True)


@app.get("/api/count-types")
def count_types_get():
    st = load_store()
    cfg = load_config()
    u = current_user(cfg)
    names = {x["key"]: x["name"] for x in store_sections(st)}
    items = active_items(st)
    out = []
    for t in ctypes.get_types(st["settings"]):
        out.append({**t, "scope_label": ctypes.scope_label(t, names), "item_count": len(ctypes.scope_items(t, items)),
                    "allowed": ctypes.allowed(u, t["key"])})
    cats = sorted({i.get("category") or "Other" for i in items})
    return jsonify({"ok": True, "count_types": out, "categories": cats, "timings": list(ctypes.TIMINGS)})


@app.put("/api/count-types")
def count_types_put():
    cfg = load_config()
    u = current_user(cfg)
    if acct.auth_enabled(cfg.get("people", [])) and u and u.get("role") != "admin" and not (u.get("permissions") or {}).get("settings"):
        return err("Only an owner/admin can change count types.", 403)
    st = load_store()
    new, e = ctypes.normalize(_body().get("count_types"), store_zones(st), {i["id"] for i in active_items(st)})
    if e:
        return err(e)
    st["settings"]["count_types"] = new
    save_store(st)
    return count_types_get()


@app.post("/api/counts/start")
def start_count():
    d = _body()
    store = load_store()
    cfg = load_config()
    u = current_user(cfg)
    types = {t["key"]: t for t in ctypes.get_types(store["settings"])}
    key = str(d.get("type") or "weekly")
    ct = types.get(key)
    if not ct or not ct.get("enabled", True):
        return err("Unknown or switched-off count type.")
    if acct.auth_enabled(cfg.get("people", [])) and not ctypes.allowed(u, key):
        return err(f"Your login can only do: {', '.join(u.get('count_types') or [])} counts.", 403)
    bd = str(d.get("date") or "")[:10] or datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(bd, "%Y-%m-%d")
    except ValueError:
        return err("Date must be YYYY-MM-DD.")
    timing = d.get("timing") if d.get("timing") in ctypes.TIMINGS else ct.get("timing", "before_service")
    names = {x["key"]: x["name"] for x in store_sections(store)}
    scope_ids = [i["id"] for i in ctypes.scope_items(ct, active_items(store))]
    # Close any in-progress session as abandoned
    for s in store["count_sessions"]:
        if s.get("status") == "in_progress":
            s["status"] = "abandoned"
            s["completed_at"] = utc_now()

    session = {
        "id": str(uuid.uuid4()),
        "status": "in_progress",
        "started_at": utc_now(),
        "completed_at": None,
        "counts": {},  # item_id -> qty
        "type": key, "type_name": ct["name"], "business_date": bd, "timing": timing,
        "scope": {"full": bool(ct.get("full")), "label": ctypes.scope_label(ct, names), "item_ids": scope_ids,
                  "checklist": ct.get("checklist") or []},
        "checklist_done": {}, "counted_by": current_user_name(), "source": "manual",
    }
    store["count_sessions"].append(session)
    save_store(store)
    return jsonify({"ok": True, "session": session}), 201


@app.get("/api/counts/<session_id>")
def get_count(session_id: str):
    store = load_store()
    for s in store["count_sessions"]:
        if s["id"] == session_id:
            return jsonify({"ok": True, "session": s})
    return err("Count session not found.", 404)


@app.put("/api/counts/<session_id>")
def update_count(session_id: str):
    """Save qty entries for a count session. Body: {counts: {item_id: qty}}"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Request body must be a JSON object.")
    counts_in = data.get("counts")
    if not isinstance(counts_in, dict):
        return err("counts must be an object of item_id → qty.")

    store = load_store()
    session = None
    for s in store["count_sessions"]:
        if s["id"] == session_id:
            session = s
            break
    if not session:
        return err("Count session not found.", 404)
    if session.get("status") != "in_progress":
        return err("Count session is not in progress.")

    cleaned = dict(session.get("counts") or {})
    for item_id, qty in counts_in.items():
        item = find_item(store, str(item_id))
        if not item or item.get("archived"):
            return err(f"Unknown item: {item_id}")
        sc = session.get("scope") or {}
        if not sc.get("full", True) and str(item_id) not in (sc.get("item_ids") or []):
            return err(f"{item['name']} isn't part of this {session.get('type_name') or 'count'}.", 400)
        if qty in (None, ""):
            cleaned.pop(str(item_id), None)
            continue
        try:
            q = float(qty)
        except (TypeError, ValueError):
            return err(f"Invalid qty for item {item_id}.")
        if q < 0:
            return err(f"Qty cannot be negative for item {item_id}.")
        cleaned[str(item_id)] = q

    session["counts"] = cleaned
    if isinstance(data.get("checklist_done"), dict):
        session["checklist_done"] = {str(k)[:60]: bool(v) for k, v in data["checklist_done"].items()}
    if not session.get("counted_by"):
        session["counted_by"] = current_user_name()
    save_store(store)
    return jsonify({"ok": True, "session": session})


@app.post("/api/counts/<session_id>/complete")
def complete_count(session_id: str):
    store = load_store()
    session = None
    for s in store["count_sessions"]:
        if s["id"] == session_id:
            session = s
            break
    if not session:
        return err("Count session not found.", 404)
    if session.get("status") != "in_progress":
        return err("Count session is not in progress.")

    # Apply counts to on_hand
    for item_id, qty in (session.get("counts") or {}).items():
        item = find_item(store, item_id)
        if item and not item.get("archived"):
            item["on_hand"] = float(qty)
            item["updated_at"] = utc_now()

    session["status"] = "completed"
    session["completed_at"] = utc_now()
    session.setdefault("business_date", session["completed_at"][:10])
    sc = session.get("scope") or {"full": True}
    counted = set((session.get("counts") or {}).keys())
    in_scope = sc.get("item_ids") or [i["id"] for i in active_items(store)]
    missing = [i for i in in_scope if i not in counted and find_item(store, i)]
    # OSBW: missing only inside the stations this count covers. Partial counts never flag the rest.
    session["summary"] = {"counted": len(counted), "in_scope": len(in_scope),
                          "missing_in_scope": [find_item(store, i)["name"] for i in missing] if sc.get("full", True) else [],
                          "not_counted_kept": len(missing) if not sc.get("full", True) else 0,
                          "outside_scope_kept": max(0, len(active_items(store)) - len(in_scope))}
    save_store(store)

    variance = compute_variance(store, session)
    return jsonify({"ok": True, "session": session, "variance": variance})


def compute_variance(store: dict, session: dict) -> list:
    """Variance vs PAR and vs prior completed count when available."""
    me = (_bdate(session), session.get("completed_at") or "9999")
    completed = [s for s in completed_sessions(store) if s["id"] != session["id"]
                 and (_bdate(s), s.get("completed_at") or "") <= me]
    prior_counts: dict = {}
    for s in completed:   # oldest → newest: last count that actually counted each item wins
        prior_counts.update(s.get("counts") or {})

    rows = []
    for item in active_items(store):
        iid = item["id"]
        counted = session.get("counts", {}).get(iid)
        if counted is None:
            continue
        counted = float(counted)
        par = float(item.get("par") or 0)
        vs_par = counted - par
        prior_qty = prior_counts.get(iid)
        vs_prior = None if prior_qty is None else counted - float(prior_qty)
        rows.append(
            {
                "item_id": iid,
                "name": item["name"],
                "zone": item["zone"],
                "unit": item["unit"],
                "counted": counted,
                "par": par,
                "vs_par": vs_par,
                "below_par": counted < par,
                "prior": None if prior_qty is None else float(prior_qty),
                "vs_prior": vs_prior,
            }
        )
    return rows


@app.get("/api/variance")
def get_variance():
    store = load_store()
    completed = completed_sessions(store)
    if not completed:
        return jsonify({"ok": True, "session": None, "variance": []})
    latest = find_by_id(completed, request.args.get("id") or "") or completed[-1]
    return jsonify(
        {"ok": True, "session": latest, "variance": compute_variance(store, latest)}
    )


# ---------- Purchase / receive (T-012) ----------

@app.get("/api/receives")
def list_receives():
    store = load_store()
    receives = sorted(
        store["receives"], key=lambda r: r.get("received_at") or "", reverse=True
    )
    return jsonify({"ok": True, "receives": receives})


@app.post("/api/receives")
def create_receive():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Request body must be a JSON object.")

    item_id = str(data.get("item_id") or "").strip()
    if not item_id:
        return err("item_id is required.")

    try:
        qty = float(data.get("qty"))
    except (TypeError, ValueError):
        return err("qty must be a number.")
    if qty <= 0:
        return err("qty must be greater than zero.")

    note = str(data.get("note") or "").strip()
    vendor = str(data.get("vendor") or "").strip()
    unit_cost = None
    if data.get("unit_cost") not in (None, ""):
        try:
            unit_cost = float(data.get("unit_cost"))
        except (TypeError, ValueError):
            return err("unit_cost must be a number.")
        if unit_cost < 0:
            return err("unit_cost cannot be negative.")

    store = load_store()
    item = find_item(store, item_id)
    if not item or item.get("archived"):
        return err("Item not found.", 404)

    item["on_hand"] = float(item.get("on_hand") or 0) + qty
    item["updated_at"] = utc_now()

    rec = {
        "id": str(uuid.uuid4()),
        "item_id": item_id,
        "item_name": item["name"],
        "qty": qty,
        "unit": item["unit"],
        "note": note,
        "vendor": vendor,
        "unit_cost": unit_cost,
        "photos": [],
        "received_at": utc_now(),
    }
    if unit_cost is not None and data.get("update_cost", True):
        item["cost"] = unit_cost  # last-cost costing
    store["receives"].append(rec)
    save_store(store)
    return jsonify({"ok": True, "receive": rec, "item": item}), 201


# ---------- Dashboard / low-PAR (T-013) ----------

@app.get("/api/dashboard")
def dashboard():
    store = load_store()
    items = active_items(store)
    low_par = [
        {
            "id": i["id"],
            "name": i["name"],
            "zone": i["zone"],
            "unit": i["unit"],
            "on_hand": float(i.get("on_hand") or 0),
            "par": float(i.get("par") or 0),
            "shortfall": float(i.get("par") or 0) - float(i.get("on_hand") or 0),
        }
        for i in items
        if float(i.get("on_hand") or 0) < float(i.get("par") or 0)
    ]
    low_par.sort(key=lambda x: -x["shortfall"])

    completed = [s for s in store["count_sessions"] if s.get("status") == "completed"]
    completed.sort(key=lambda s: s.get("completed_at") or "", reverse=True)
    last_count = completed[0] if completed else None

    return jsonify(
        {
            "ok": True,
            "settings": public_settings(store["settings"]),
            "item_count": len(items),
            "low_par": low_par,
            "low_par_count": len(low_par),
            "last_count": last_count,
            "receive_count": len(store["receives"]),
            "inventory_value": round(sum(float(i.get("on_hand") or 0) * float(i.get("cost") or 0) for i in items), 2),
            "menu_count": len(store.get("menu_items", store.get("menu", [])) or []),
            "stop_count": len(store.get("stop_types", []) or []),
            "sales_import_count": len(store.get("sales_imports", store.get("sales", [])) or []),
            "empty": len(items) == 0,
            "version": VERSION,
        }
    )


# ---------- Order list / reorder (v0.3, mirrors OSBW "Order Generator") ----------

def build_reorder(store: dict) -> dict:
    items = active_items(store)
    last_vendor: dict = {}
    for r in sorted(store.get("receives", []), key=lambda r: r.get("received_at") or r.get("created_at") or ""):
        if r.get("vendor"):
            last_vendor[r.get("item_id")] = r["vendor"]
    vendors = {v["id"]: v for v in load_config().get("vendors", [])}
    groups: dict = {}
    total = 0.0
    import math
    for i in items:
        par = float(i.get("par") or 0)
        oh = float(i.get("on_hand") or 0)
        if oh >= par:
            continue
        need = par - oh
        cost = i.get("cost")
        ext = round(need * float(cost), 2) if cost not in (None, "") else None
        if ext is not None:
            total += ext
        v = vendors.get(i.get("vendor_id") or "")
        vendor = (v or {}).get("name") or last_vendor.get(i["id"]) or ""
        cs = i.get("case_size")
        cases = math.ceil(need / float(cs) - 1e-9) if cs else None
        groups.setdefault(vendor, []).append({"id": i["id"], "name": i["name"], "unit": i["unit"], "zone": i["zone"],
                                              "on_hand": oh, "par": par, "order_qty": round(need, 2),
                                              "case_size": cs, "order_cases": cases, "pack": i.get("pack"),
                                              "vendor_id": (v or {}).get("id"),
                                              "cost": cost, "ext_cost": ext})
    by_name = {v["name"]: v for v in vendors.values()}
    out = [{"vendor": v, "vendor_id": (by_name.get(v) or {}).get("id"), "lines": sorted(ls, key=lambda x: x["name"]),
            "subtotal": round(sum(l["ext_cost"] or 0 for l in ls), 2)} for v, ls in groups.items()]
    out.sort(key=lambda g: (g["vendor"] == "", g["vendor"].lower()))
    return {"ok": True, "groups": out, "total": round(total, 2),
            "line_count": sum(len(g["lines"]) for g in out)}


@app.get("/api/reorder")
def reorder():
    return jsonify(build_reorder(load_store()))


# ---------- Demo seed (T-014) ----------

DEMO_ITEMS = [
    {"name": "Flour tortillas", "cost": 3.49, "unit": "pack", "par": 12, "category": "Tortillas", "zone": "dry", "on_hand": 8},
    {"name": "Corn tortillas", "cost": 2.29, "unit": "pack", "par": 8, "category": "Tortillas", "zone": "dry", "on_hand": 10},
    {"name": "Ground beef", "cost": 4.89, "unit": "lb", "par": 20, "category": "Protein", "zone": "cooler", "on_hand": 14},
    {"name": "Chicken thigh", "cost": 2.79, "unit": "lb", "par": 15, "category": "Protein", "zone": "cooler", "on_hand": 18},
    {"name": "Shredded cheese", "cost": 3.99, "unit": "lb", "par": 10, "category": "Dairy", "zone": "cooler", "on_hand": 6},
    {"name": "Ice", "cost": 2.5, "unit": "bag", "par": 6, "category": "Beverage", "zone": "freezer", "on_hand": 4},
    {"name": "Frozen carnitas", "cost": 5.25, "unit": "lb", "par": 12, "category": "Protein", "zone": "freezer", "on_hand": 12},
    {"name": "Salsa verde", "cost": 4.0, "unit": "qt", "par": 4, "category": "Sauce", "zone": "prep", "on_hand": 2},
    {"name": "Pico de gallo", "cost": 5.5, "unit": "qt", "par": 3, "category": "Produce", "zone": "prep", "on_hand": 3},
    {"name": "Lime wedges", "cost": 3.0, "unit": "pan", "par": 2, "category": "Produce", "zone": "prep", "on_hand": 1},
    {"name": "Hot sauce bottles", "cost": 1.75, "unit": "ea", "par": 8, "category": "Condiment", "zone": "dry", "on_hand": 5},
    {"name": "Black beans (can)", "cost": 1.1, "unit": "can", "par": 24, "category": "Pantry", "zone": "dry", "on_hand": 30},
]


# v0.2 demo additions — all EXAMPLE data (made-up prices, recipes and sales).
# Pack/case conversions are simplified: recipe qty is in the item's own unit.
DEMO_MENU = [
    {"name": "Street taco — beef (EXAMPLE)", "price": 3.50, "category": "Tacos", "pos_names": ["Beef Taco"],
     "ingredients": {"Corn tortillas": 0.04, "Ground beef": 0.15, "Pico de gallo": 0.03, "Lime wedges": 0.02}},
    {"name": "Street taco — carnitas (EXAMPLE)", "price": 3.75, "category": "Tacos", "pos_names": ["Carnitas Taco"],
     "ingredients": {"Corn tortillas": 0.04, "Frozen carnitas": 0.15, "Salsa verde": 0.03, "Lime wedges": 0.02}},
    {"name": "Chicken burrito (EXAMPLE)", "price": 11.00, "category": "Burritos", "pos_names": ["Chicken Burrito"],
     "ingredients": {"Flour tortillas": 0.1, "Chicken thigh": 0.33, "Shredded cheese": 0.1,
                     "Black beans (can)": 0.25, "Pico de gallo": 0.05}},
    {"name": "Quesadilla (EXAMPLE)", "price": 9.00, "category": "Mains", "pos_names": ["Cheese Quesadilla"],
     "ingredients": {"Flour tortillas": 0.1, "Shredded cheese": 0.25, "Salsa verde": 0.04}},
]
DEMO_STOPS = [
    {"name": "Weekday lunch spot (EXAMPLE)", "notes": "Office park, ~120 plates",
     "pars": {"Corn tortillas": 6, "Flour tortillas": 6, "Ground beef": 12, "Chicken thigh": 10, "Ice": 4}},
    {"name": "Brewery night (EXAMPLE)", "notes": "Taproom 5–10 pm, ~200 plates, heavy on tacos",
     "pars": {"Corn tortillas": 12, "Ground beef": 20, "Frozen carnitas": 15, "Lime wedges": 3, "Ice": 6}},
    {"name": "Festival (EXAMPLE)", "notes": "All-day festival, ~600 plates — bring backup ice",
     "pars": {"Corn tortillas": 30, "Flour tortillas": 20, "Ground beef": 45, "Chicken thigh": 40,
              "Frozen carnitas": 35, "Shredded cheese": 20, "Ice": 20, "Salsa verde": 8, "Pico de gallo": 8,
              "Lime wedges": 6, "Hot sauce bottles": 12}},
]
DEMO_SALES = [("Beef Taco", 64, 3.50), ("Carnitas Taco", 48, 3.75), ("Chicken Burrito", 22, 11.00),
              ("Cheese Quesadilla", 12, 9.00), ("Horchata", 30, 4.00)]


def seed_demo_v02(store: dict, items: list) -> None:
    from datetime import timedelta
    by_name = {i["name"]: i for i in items}
    now = datetime.now(timezone.utc)
    store["menu_items"] = [{
        "id": str(uuid.uuid4()), "name": m["name"], "price": m["price"], "category": m["category"],
        "pos_names": m["pos_names"], "example": True, "archived": False,
        "ingredients": [{"item_id": by_name[n]["id"], "qty": q} for n, q in m["ingredients"].items()],
        "created_at": utc_now(), "updated_at": utc_now(),
    } for m in DEMO_MENU]
    store["stop_types"] = [{
        "id": str(uuid.uuid4()), "name": s_["name"], "notes": s_["notes"], "example": True, "archived": False,
        "pars": {by_name[n]["id"]: float(q) for n, q in s_["pars"].items()}, "created_at": utc_now(),
    } for s_ in DEMO_STOPS]
    # Two example counts (yesterday 7am, today 7am) with one receive and a day of sales between.
    t_start = (now - timedelta(days=1)).replace(hour=11, minute=0, second=0, microsecond=0)
    t_end = now.replace(hour=11, minute=0, second=0, microsecond=0)
    if t_end > now:
        t_start -= timedelta(days=1)
        t_end -= timedelta(days=1)
    sales_day = t_start.strftime("%Y-%m-%d")
    menu_by_pos = {m["pos_names"][0]: m for m in store["menu_items"]}
    usage = {}
    for pos_name, qty, _price in DEMO_SALES:
        m = menu_by_pos.get(pos_name)
        for ing in (m or {}).get("ingredients", []):
            usage[ing["item_id"]] = usage.get(ing["item_id"], 0) + qty * ing["qty"]
    beef = by_name["Ground beef"]["id"]
    start_counts, end_counts = {}, {}
    for it in items:
        end = float(it["on_hand"])
        used = usage.get(it["id"], 0.0) * (1.15 if it["id"] == beef else 1.0)  # example: beef over-portioned
        recv = 10.0 if it["id"] == beef else 0.0
        start_counts[it["id"]] = round(end + used - recv, 2)
        end_counts[it["id"]] = end
    store["count_sessions"] = [
        {"id": str(uuid.uuid4()), "status": "completed", "counts": start_counts, "example": True,
         "started_at": (t_start - timedelta(minutes=20)).isoformat(), "completed_at": t_start.isoformat()},
        {"id": str(uuid.uuid4()), "status": "completed", "counts": end_counts, "example": True,
         "started_at": (t_end - timedelta(minutes=20)).isoformat(), "completed_at": t_end.isoformat()},
    ]
    store["receives"] = [{
        "id": str(uuid.uuid4()), "item_id": beef, "item_name": "Ground beef", "qty": 10.0, "unit": "lb",
        "note": "EXAMPLE invoice #1042", "vendor": "Example Meat Co.", "unit_cost": 4.89, "photos": [],
        "example": True, "received_at": (t_start + timedelta(hours=2)).isoformat(),
    }]
    lines = [{"date": sales_day, "menu_item": n, "qty": float(q), "price": round(q * p, 2)} for n, q, p in DEMO_SALES]
    store["sales_imports"] = [{
        "id": str(uuid.uuid4()), "adapter": "generic_csv", "filename": "EXAMPLE-sales.csv", "example": True,
        "imported_at": utc_now(), "lines": _link_menu(store, lines),
        "total_qty": sum(l["qty"] for l in lines), "total_sales": round(sum(l["price"] for l in lines), 2),
    }]


@app.post("/api/seed")
def seed_demo():
    """Load taco-truck demo catalog (≥8 items, all 4 zones). Replaces catalog items."""
    store = load_store()
    now = utc_now()
    items = []
    for d in DEMO_ITEMS:
        items.append(
            {
                "id": str(uuid.uuid4()),
                "name": d["name"],
                "unit": d["unit"],
                "par": float(d["par"]),
                "category": d["category"],
                "zone": d["zone"],
                "on_hand": float(d["on_hand"]),
                "cost": d.get("cost"),
                "example": True,
                "archived": False,
                "created_at": now,
                "updated_at": now,
            }
        )
    store["items"] = items
    # Keep settings; clear operational history for a clean demo
    store["count_sessions"] = []
    store["receives"] = []
    seed_demo_v02(store, items)
    seed_demo_v1(store, items)
    if not store["settings"].get("truck_name"):
        store["settings"]["truck_name"] = "Taco Libre Demo"
        store["settings"]["setup_complete"] = True
    save_store(store)
    zones_hit = sorted({i["zone"] for i in items})
    return jsonify(
        {
            "ok": True,
            "seeded": len(items),
            "zones": zones_hit,
            "menu_items": len(store["menu_items"]),
            "stop_types": len(store["stop_types"]),
            "sales_lines": sum(len(i["lines"]) for i in store["sales_imports"]),
            "items": items,
        }
    )


@app.post("/api/reset")
def reset_store():
    """Hard reset this truck (OSBW "hard reset"): auto-backup first, then wipe to an empty store."""
    backup_path = write_backup("reset")
    store = empty_store()
    save_store(store)
    return jsonify({"ok": True, "reset": True, "backup": backup_path.name if backup_path else None})


# =====================================================================
# v0.2 — POS import, recipes/costing, sales variance, stop types / load
# lists, receive photos + optional AI reader.
# =====================================================================

PHOTOS_DIR = DATA_DIR / "photos"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif", ".pdf"}
MAX_UPLOAD_MB = 15
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


def _num(v, field: str, allow_zero: bool = True, minimum: float = 0.0):
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number.")
    if n < minimum or (not allow_zero and n == 0):
        raise ValueError(f"{field} must be {'greater than' if not allow_zero else 'at least'} {minimum:g}.")
    return n


def find_by_id(rows: list, rid: str):
    return next((r for r in rows if r.get("id") == rid), None)


# ---------- POS adapters ----------

@app.get("/api/pos/adapters")
def pos_adapters_list():
    return jsonify({"ok": True, "adapters": [a.describe() for a in pos.ADAPTERS.values()]})


def _upload_text() -> tuple[str, str]:
    f = request.files.get("file")
    pasted = (request.form.get("text") or "").strip()
    if (f is None or not f.filename) and pasted:
        return pasted, "pasted.csv"
    if f is None or not f.filename:
        raise pos.AdapterError("Choose a CSV file to upload.")
    raw = f.read()
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return raw.decode(enc), f.filename
        except UnicodeDecodeError:
            continue
    raise pos.AdapterError("Could not read file encoding — save it as CSV (UTF-8).")


def _mapping_from_form() -> dict:
    raw = request.form.get("mapping") or "{}"
    try:
        m = json.loads(raw)
    except json.JSONDecodeError:
        raise pos.AdapterError("mapping must be JSON.")
    return {k: v for k, v in (m or {}).items() if isinstance(v, str) and v}


def _link_menu(store: dict, lines: list) -> list:
    by_name = {}
    for mi in store["menu_items"]:
        by_name[mi["name"].strip().lower()] = mi["id"]
        for alias in mi.get("pos_names") or []:
            by_name[alias.strip().lower()] = mi["id"]
    for ln in lines:
        ln["menu_item_id"] = by_name.get(ln["menu_item"].strip().lower())
    return lines


@app.post("/api/pos/preview")
def pos_preview():
    """Upload CSV → headers, guessed adapter, detected mapping, first parsed lines."""
    try:
        text, filename = _upload_text()
        headers, rows = pos.read_csv(text)
        key = request.form.get("adapter") or pos.guess_adapter(headers)
        adapter = pos.get_adapter(key)
        detected = adapter.detect(headers)
        mapping = {**detected, **_mapping_from_form()}
        lines, parse_error = [], None
        try:
            lines = adapter.parse(text, mapping, request.form.get("default_date") or None)
        except pos.AdapterError as e:
            parse_error = str(e)
        store = load_store()
        _link_menu(store, lines)
    except pos.AdapterError as e:
        return err(str(e))
    return jsonify({
        "ok": True, "filename": filename, "headers": headers, "row_count": len(rows),
        "adapter": key, "adapter_info": adapter.describe(), "mapping": mapping,
        "fields": list(adapter.columns.keys()), "lines": lines[:25], "line_count": len(lines),
        "unmatched": sorted({l["menu_item"] for l in lines if not l["menu_item_id"]}),
        "parse_error": parse_error,
    })


@app.post("/api/pos/import")
def pos_import():
    try:
        text, filename = _upload_text()
        adapter = pos.get_adapter(request.form.get("adapter") or "generic_csv")
        default_date = request.form.get("default_date") or datetime.now().strftime("%Y-%m-%d")
        lines = adapter.parse(text, _mapping_from_form(), default_date)
    except pos.AdapterError as e:
        return err(str(e))
    if not lines:
        return err("No sales lines found in the file.")
    store = load_store()
    _link_menu(store, lines)
    imp = {
        "id": str(uuid.uuid4()), "adapter": adapter.key, "filename": filename,
        "imported_at": utc_now(), "lines": lines,
        "total_qty": sum(l["qty"] for l in lines),
        "total_sales": round(sum(l["price"] for l in lines), 2),
        "pos_account_id": request.form.get("pos_account_id") or None,
        "imported_by": current_user_name(),
    }
    store["sales_imports"].append(imp)
    save_store(store)
    return jsonify({"ok": True, "import": imp}), 201


@app.get("/api/sales")
def sales_list():
    store = load_store()
    imports = sorted(store["sales_imports"], key=lambda i: i["imported_at"], reverse=True)
    summary = [{k: v for k, v in i.items() if k != "lines"} | {"line_count": len(i["lines"])} for i in imports]
    return jsonify({"ok": True, "imports": summary})


@app.delete("/api/sales/<imp_id>")
def sales_delete(imp_id: str):
    store = load_store()
    imp = find_by_id(store["sales_imports"], imp_id)
    if not imp:
        return err("Import not found.", 404)
    store["sales_imports"].remove(imp)
    save_store(store)
    return jsonify({"ok": True, "deleted": imp_id})


# ---------- Menu items / recipes / costing ----------

def validate_menu_payload(store: dict, data) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."
    name = str(data.get("name") or "").strip()
    if not name:
        return None, "Name is required."
    try:
        price = _num(data.get("price"), "Menu price")
    except ValueError as e:
        return None, str(e)
    ingredients = []
    for ing in data.get("ingredients") or []:
        iid = str((ing or {}).get("item_id") or "")
        if not iid:
            continue
        item = find_item(store, iid)
        if not item or item.get("archived"):
            return None, f"Unknown ingredient item: {iid}"
        try:
            q = _num(ing.get("qty"), f"Qty for {item['name']}", allow_zero=False)
        except ValueError as e:
            return None, str(e)
        ingredients.append({"item_id": iid, "qty": q})
    pos_names = [s.strip() for s in (data.get("pos_names") or []) if str(s).strip()]
    return {
        "name": name, "price": price, "category": str(data.get("category") or "").strip(),
        "ingredients": ingredients, "pos_names": pos_names,
    }, None


def cost_menu_item(store: dict, mi: dict) -> dict:
    lines, total, missing = [], 0.0, []
    for ing in mi.get("ingredients") or []:
        item = find_item(store, ing["item_id"])
        if not item:
            continue
        uc = item.get("cost")
        line_cost = None if uc is None else float(uc) * float(ing["qty"])
        if line_cost is None:
            missing.append(item["name"])
        else:
            total += line_cost
        lines.append({"item_id": item["id"], "name": item["name"], "unit": item["unit"],
                      "qty": ing["qty"], "unit_cost": uc, "line_cost": line_cost})
    price = float(mi.get("price") or 0)
    margin = price - total
    return {
        **mi, "ingredient_lines": lines, "plate_cost": round(total, 4),
        "margin": round(margin, 4),
        "margin_pct": round(margin / price * 100, 1) if price else None,
        "food_cost_pct": round(total / price * 100, 1) if price else None,
        "missing_costs": missing,
    }


@app.get("/api/menu")
def menu_list():
    store = load_store()
    rows = [cost_menu_item(store, m) for m in store["menu_items"] if not m.get("archived")]
    rows.sort(key=lambda r: (r.get("category") or "", r["name"].lower()))
    return jsonify({"ok": True, "menu": rows})


@app.post("/api/menu")
def menu_create():
    store = load_store()
    fields, message = validate_menu_payload(store, request.get_json(silent=True))
    if message:
        return err(message)
    mi = {"id": str(uuid.uuid4()), **fields, "archived": False, "created_at": utc_now(), "updated_at": utc_now()}
    store["menu_items"].append(mi)
    save_store(store)
    return jsonify({"ok": True, "menu_item": cost_menu_item(store, mi)}), 201


@app.put("/api/menu/<mid>")
def menu_update(mid: str):
    store = load_store()
    mi = find_by_id(store["menu_items"], mid)
    if not mi or mi.get("archived"):
        return err("Menu item not found.", 404)
    fields, message = validate_menu_payload(store, request.get_json(silent=True))
    if message:
        return err(message)
    mi.update(fields)
    mi["updated_at"] = utc_now()
    save_store(store)
    return jsonify({"ok": True, "menu_item": cost_menu_item(store, mi)})


@app.delete("/api/menu/<mid>")
def menu_delete(mid: str):
    store = load_store()
    mi = find_by_id(store["menu_items"], mid)
    if not mi or mi.get("archived"):
        return err("Menu item not found.", 404)
    mi["archived"] = True
    save_store(store)
    return jsonify({"ok": True, "archived": True, "id": mid})


# ---------- Variance from sales (theoretical vs counted usage) ----------

def _sales_after(sess: dict, d: str) -> bool:
    """True if a POS line dated d happened after this count.
    before_service counts (default) happen before that day's sales; end_of_shift counts include them."""
    bd = _bdate(sess)
    return d > bd if sess.get("timing") == "end_of_shift" else d >= bd


def compute_sales_variance(store: dict, start_id: str | None = None, end_id: str | None = None) -> dict:
    """Theoretical (POS × recipes) vs counted usage.

    v1.3: per-item windows so partial (daily) counts never distort a weekly reconcile.
    * end = the chosen count, else the latest FULL count (else the latest count).
    * start per item = the chosen start count if it counted the item; else, when the end is a full count
      and a prior full count exists, that full count; else the latest earlier count that actually counted it.
    * Only items counted at both ends get a variance; nothing un-scanned is treated as zero.
    """
    completed = completed_sessions(store)
    if len(completed) < 2 and not (start_id and end_id):
        return {"ready": False, "reason": "Need two completed counts (start and end of the period).", "rows": []}
    end = find_by_id(completed, end_id) if end_id else (
        next((x for x in reversed(completed) if _is_full(x)), None) or completed[-1])
    start = find_by_id(completed, start_id) if start_id else None
    if not end or (start_id and not start):
        return {"ready": False, "reason": "Count session not found.", "rows": []}
    pos = {x["id"]: n for n, x in enumerate(completed)}
    if start and pos[start["id"]] > pos[end["id"]]:
        start, end = end, start
    before = completed[:pos[end["id"]]]
    if not before:
        return {"ready": False, "reason": "Need an earlier count to compare against.", "rows": []}
    if not start and _is_full(end):
        start = next((x for x in reversed(before) if _is_full(x)), None)
    ec = end.get("counts") or {}

    def start_for(iid):
        if start and iid in (start.get("counts") or {}):
            return start
        for x in reversed(before):
            if iid in (x.get("counts") or {}):
                return x
        return None

    menu = {m["id"]: m for m in store["menu_items"]}
    lines = [ln for imp in store["sales_imports"] for ln in imp["lines"]]

    def in_window(st_s, d):
        if _bdate(st_s) == _bdate(end) and st_s.get("timing") != "end_of_shift" and end.get("timing") != "end_of_shift":
            return d == _bdate(end)          # legacy: same-day start/end take that day's sales
        return _sales_after(st_s, d) and not _sales_after(end, d)

    cache: dict[str, tuple] = {}
    sales_total: dict[str, float] = {}

    def window(st_s):
        if st_s["id"] in cache:
            return cache[st_s["id"]]
        theo, sold, unm, rec = {}, {}, {}, {}
        sales_total[st_s["id"]] = 0.0
        for ln in lines:
            if not in_window(st_s, ln.get("date") or ""):
                continue
            sales_total[st_s["id"]] += float(ln.get("price") or 0)
            mi = menu.get(ln.get("menu_item_id") or "")
            if not mi:
                unm[ln["menu_item"]] = unm.get(ln["menu_item"], 0) + ln["qty"]
                continue
            sold[mi["name"]] = sold.get(mi["name"], 0) + ln["qty"]
            for ing in mi.get("ingredients") or []:
                theo[ing["item_id"]] = theo.get(ing["item_id"], 0.0) + ln["qty"] * float(ing["qty"])
        t0, t1 = st_s.get("completed_at") or "", end.get("completed_at") or ""
        for r in store["receives"]:
            if t0 < (r.get("received_at") or "") <= t1:
                rec[r["item_id"]] = rec.get(r["item_id"], 0.0) + float(r["qty"])
        cache[st_s["id"]] = (theo, sold, unm, rec)
        return cache[st_s["id"]]

    main_start = start or (before[-1] if before else None)
    rows, starts_used = [], {}
    for item in active_items(store):
        iid = item["id"]
        ss = start_for(iid) if iid in ec else None
        if not ss:
            theo_any = window(main_start)[0].get(iid) if main_start else None
            if theo_any:
                rows.append({"item_id": iid, "name": item["name"], "unit": item["unit"], "zone": item["zone"],
                             "theoretical": round(theo_any, 3), "counted_usage": None, "variance": None,
                             "note": "not counted in this count — last known on-hand carried" if iid not in ec
                             else "no earlier count of this item"})
            continue
        theo_d, _, _, rec_d = window(ss)
        starts_used[ss["id"]] = starts_used.get(ss["id"], 0) + 1
        sq, eq, rq = float(ss["counts"][iid]), float(ec[iid]), rec_d.get(iid, 0.0)
        counted_usage = sq + rq - eq
        theo = theo_d.get(iid, 0.0)
        var = counted_usage - theo
        cost = item.get("cost")
        rows.append({
            "item_id": iid, "name": item["name"], "unit": item["unit"], "zone": item["zone"],
            "start": sq, "start_count": ss["id"], "start_date": _bdate(ss), "received": rq, "end": eq,
            "counted_usage": round(counted_usage, 3), "theoretical": round(theo, 3),
            "variance": round(var, 3),
            "variance_pct": round(var / theo * 100, 1) if theo else None,
            "variance_cost": None if cost is None else round(var * float(cost), 2),
        })
    rows.sort(key=lambda r: -(abs(r["variance_cost"]) if r.get("variance_cost") is not None else abs(r.get("variance") or 0)))
    ms = main_start or end
    _, sold, unmatched, _ = window(ms)

    def brief(x):
        return {"id": x["id"], "completed_at": x.get("completed_at"), "business_date": _bdate(x),
                "type": x.get("type") or "weekly", "type_name": x.get("type_name") or "Full count",
                "full": _is_full(x), "counted_by": x.get("counted_by")}
    return {
        "ready": True, "start": brief(ms), "end": brief(end),
        "period": [_bdate(ms), _bdate(end)], "sales": round(sales_total.get(ms["id"], 0.0), 2), "sold": sold, "unmatched_sales": unmatched, "rows": rows,
        "mixed_starts": len(starts_used) > 1,
        "skipped_partials": [brief(x) for x in completed[pos[ms["id"]] + 1:pos[end["id"]]] if not _is_full(x)],
        "total_variance_cost": round(sum(r["variance_cost"] or 0 for r in rows if r.get("variance_cost") is not None), 2),
    }


@app.get("/api/variance/sales")
def sales_variance():
    store = load_store()
    return jsonify({"ok": True, **compute_sales_variance(store, request.args.get("start"), request.args.get("end"))})


# ---------- Stop types + load list ----------

def validate_stop_payload(store: dict, data) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."
    name = str(data.get("name") or "").strip()
    if not name:
        return None, "Name is required."
    pars = {}
    for iid, q in (data.get("pars") or {}).items():
        if q in (None, ""):
            continue
        item = find_item(store, str(iid))
        if not item or item.get("archived"):
            return None, f"Unknown item: {iid}"
        try:
            pars[str(iid)] = _num(q, f"PAR for {item['name']}")
        except ValueError as e:
            return None, str(e)
    return {"name": name, "notes": str(data.get("notes") or "").strip(), "pars": pars}, None


@app.get("/api/stops")
def stops_list():
    store = load_store()
    return jsonify({"ok": True, "stops": [s for s in store["stop_types"] if not s.get("archived")]})


@app.post("/api/stops")
def stops_create():
    store = load_store()
    fields, message = validate_stop_payload(store, request.get_json(silent=True))
    if message:
        return err(message)
    st = {"id": str(uuid.uuid4()), **fields, "archived": False, "created_at": utc_now()}
    store["stop_types"].append(st)
    save_store(store)
    return jsonify({"ok": True, "stop": st}), 201


@app.put("/api/stops/<sid>")
def stops_update(sid: str):
    store = load_store()
    st = find_by_id(store["stop_types"], sid)
    if not st or st.get("archived"):
        return err("Stop type not found.", 404)
    fields, message = validate_stop_payload(store, request.get_json(silent=True))
    if message:
        return err(message)
    st.update(fields)
    save_store(store)
    return jsonify({"ok": True, "stop": st})


@app.delete("/api/stops/<sid>")
def stops_delete(sid: str):
    store = load_store()
    st = find_by_id(store["stop_types"], sid)
    if not st or st.get("archived"):
        return err("Stop type not found.", 404)
    st["archived"] = True
    save_store(store)
    return jsonify({"ok": True, "archived": True, "id": sid})


def build_load_list(store: dict, stop: dict) -> dict:
    rows = []
    for item in active_items(store):
        par = stop["pars"].get(item["id"])
        if par is None:
            par = float(item.get("par") or 0)  # fall back to the item's everyday PAR
            source = "item"
        else:
            source = "stop"
        if par <= 0:
            continue
        on_hand = float(item.get("on_hand") or 0)
        rows.append({
            "item_id": item["id"], "name": item["name"], "unit": item["unit"], "zone": item["zone"],
            "category": item.get("category"), "par": par, "par_source": source,
            "on_hand": on_hand, "load": par, "short": max(0.0, par - on_hand),
        })
    zorder = {z: i for i, z in enumerate(ZONES)}
    rows.sort(key=lambda r: (zorder.get(r["zone"], 9), r["name"].lower()))
    return {"stop": stop, "rows": rows, "short_count": sum(1 for r in rows if r["short"] > 0)}


@app.get("/api/stops/<sid>/loadlist")
def stops_loadlist(sid: str):
    store = load_store()
    st = find_by_id(store["stop_types"], sid)
    if not st or st.get("archived"):
        return err("Stop type not found.", 404)
    return jsonify({"ok": True, **build_load_list(store, st)})


@app.get("/print/loadlist/<sid>")
def print_loadlist(sid: str):
    """Printer-friendly load list (server-rendered so it prints from any phone)."""
    from html import escape
    store = load_store()
    st = find_by_id(store["stop_types"], sid)
    if not st or st.get("archived"):
        return "Stop type not found", 404
    es = store["settings"].get("locale") == "es"
    L = (lambda en, sp: sp if es else en)
    data = build_load_list(store, st)
    date = escape(request.args.get("date") or "")
    out = [f"<!DOCTYPE html><html lang='{'es' if es else 'en'}'><head><meta charset='utf-8'>"
           "<meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>{L('Load list', 'Lista de carga')} — {escape(st['name'])}</title>"
           "<style>body{font-family:system-ui,sans-serif;margin:1rem;color:#000}table{width:100%;border-collapse:collapse}"
           "th,td{border-bottom:1px solid #999;padding:.4rem;text-align:left}td.box{width:2rem;font-size:1.2rem}"
           "h2{margin:.8rem 0 .3rem;font-size:1rem;text-transform:uppercase}.short{font-weight:700}"
           "@media print{.noprint{display:none}}</style></head><body>",
           f"<h1>{escape(store['settings'].get('truck_name') or 'OSFT')} — {L('Load list', 'Lista de carga')}</h1>",
           f"<p><b>{L('Stop', 'Parada')}:</b> {escape(st['name'])} {('· ' + date) if date else ''}<br>",
           f"{escape(st.get('notes') or '')}</p>",
           f"<p class='noprint'><button onclick='window.print()'>{L('Print', 'Imprimir')}</button></p>"]
    zone_names = {"cooler": L("Cooler", "Refrigerador"), "freezer": L("Freezer", "Congelador"),
                  "dry": L("Dry storage", "Seco"), "prep": "Prep"}
    for z in ZONES:
        zr = [r for r in data["rows"] if r["zone"] == z]
        if not zr:
            continue
        out.append(f"<h2>{zone_names[z]}</h2><table><tr><th></th><th>{L('Item', 'Artículo')}</th>"
                   f"<th>{L('Load', 'Cargar')}</th><th>{L('On hand', 'En mano')}</th><th>{L('Buy/prep', 'Comprar/preparar')}</th></tr>")
        for r in zr:
            short = f"<span class='short'>{r['short']:g}</span>" if r["short"] > 0 else ""
            out.append(f"<tr><td class='box'>☐</td><td>{escape(r['name'])}</td><td>{r['load']:g} {escape(r['unit'])}</td>"
                       f"<td>{r['on_hand']:g}</td><td>{short}</td></tr>")
        out.append("</table>")
    out.append(f"<p style='margin-top:1rem;font-size:.8rem'>OSFT v{VERSION}</p></body></html>")
    return "".join(out)


# ---------- Receive photos + optional AI reader ----------

@app.post("/api/receives/<rid>/photos")
def receive_photo_upload(rid: str):
    store = load_store()
    rec = find_by_id(store["receives"], rid)
    if not rec:
        return err("Receive entry not found.", 404)
    f = request.files.get("photo")
    if f is None or not f.filename:
        return err("Choose a photo to upload.")
    ext = Path(f.filename).suffix.lower()
    if ext not in PHOTO_EXT:
        return err(f"Photo type {ext or '?'} not allowed. Use: {', '.join(sorted(PHOTO_EXT))}.")
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{rid[:8]}-{uuid.uuid4().hex[:10]}{ext}"
    f.save(PHOTOS_DIR / fname)
    rec.setdefault("photos", []).append(fname)
    save_store(store)
    return jsonify({"ok": True, "receive": rec, "photo": fname, "url": f"/photos/{fname}"}), 201


@app.get("/photos/<name>")
def photo_get(name: str):
    if "/" in name or "\\" in name or name.startswith("."):
        return err("Bad name.", 400)
    return send_from_directory(PHOTOS_DIR, name)


@app.post("/api/receives/<rid>/photos/<name>/read")
def receive_photo_ai_read(rid: str, name: str):
    store = load_store()
    rec = find_by_id(store["receives"], rid)
    if not rec or name not in (rec.get("photos") or []):
        return err("Photo not found.", 404)
    try:
        p = PHOTOS_DIR / name
        result = ai_mod.extract_invoice(get_ai_cfg(), [(p.read_bytes(), _mime_of(p))])
    except ai_mod.AIOff as e:
        return err(str(e), 409)
    except Exception as e:  # network / provider / JSON errors → never crash
        return err(f"AI reader failed: {e}", 502)
    return jsonify({"ok": True, "suggestion": result, "applied": False})


@app.get("/api/settings/ai")
def ai_settings_get():
    c = ai_mod.public(get_ai_cfg())
    return jsonify({"ok": True, "ai_reader": {"enabled": c["enabled"], "endpoint": c["base_url"], "model": c["model"],
                                              "has_key": c["has_key"]}, "ai": c})


@app.put("/api/settings/ai")
def ai_settings_put():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return err("Request body must be a JSON object.")
    if data.get("endpoint") is not None and "base_url" not in data:
        data["base_url"] = data.pop("endpoint")
    return _ai_save(data)


@app.errorhandler(413)
def too_large(_e):
    return err(f"File too large (max {MAX_UPLOAD_MB} MB).", 413)


# ---------- Error handlers (no naked 500 for bad JSON) ----------

@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return err("Not found.", 404)
    return send_from_directory(STATIC_DIR, "index.html")


@app.errorhandler(405)
def method_not_allowed(_e):
    return err("Method not allowed.", 405)


@app.errorhandler(500)
def server_error(_e):
    return err("Internal server error.", 500)


# =====================================================================
# v1.0 — OSBW parity: business + people accounts (PIN login), trucks
# (multi-venue) + transfers, vendors / category (GL) / POS accounts,
# onboarding wizard, starter catalog, product import/export, voice
# counting, purchase orders, invoice text reading, input log, reports,
# exports, backups / restore / hard reset, staff board.
# =====================================================================

import csv as _csv
import io as _io
import re as _re
import secrets as _secrets
import shutil as _shutil
import zipfile as _zipfile
from datetime import timedelta as _td


def config_path() -> Path:
    return DATA_DIR / "config.json"


def default_config() -> dict:
    return {
        "business": {"name": "", "legal_name": "", "address": "", "phone": "", "email": "", "website": "",
                     "logo_data_url": "", "panel_title": "", "timezone": "America/New_York", "currency": "USD",
                     "cycle_days": 7, "anchor_day": "monday", "updates_opt_in": False},
        "trucks": [{"id": "main", "notes": "", "created_at": utc_now()}],
        "active_truck_id": "main",
        "people": [],
        "vendors": [],
        "categories": [],
        "pos_accounts": [],
        "staff_board": [],
        "onboarding": {"phase": "welcome", "completed": False, "started_at": utc_now(), "completed_at": None},
    }


def _read_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.replace(path)


def load_config() -> dict:
    cfg = _read_json(config_path())
    fresh = not isinstance(cfg, dict)
    if fresh:
        cfg = default_config()
        # Upgrading an existing v0.x install: don't force onboarding on a truck that's already set up.
        old = _read_json(STORE_PATH)
        if isinstance(old, dict) and (old.get("settings") or {}).get("setup_complete"):
            cfg["onboarding"].update(phase="done", completed=True, completed_at=utc_now())
            cfg["business"]["name"] = (old.get("settings") or {}).get("truck_name", "")
    base = default_config()
    for k, v in base.items():
        cfg.setdefault(k, v)
    for k, v in base["business"].items():
        cfg["business"].setdefault(k, v)
    if not any(t.get("id") == "main" for t in cfg["trucks"]):
        cfg["trucks"].insert(0, base["trucks"][0])
    if fresh and DATA_DIR.exists():
        save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    _write_json(config_path(), cfg)


def current_user(cfg: dict | None = None):
    if not has_request_context():
        return None
    uid = session.get("user_id")
    if not uid:
        return None
    cfg = cfg or load_config()
    for u in cfg.get("people", []):
        if u.get("id") == uid and u.get("active", True):
            return u
    return None


def current_user_name() -> str | None:
    u = current_user()
    return u.get("name") if u else None


def active_truck_id() -> str:
    cfg = load_config()
    tid = cfg.get("active_truck_id") or "main"
    u = current_user(cfg)
    if u and u.get("truck_id") and u.get("role") != "admin" and not (u.get("permissions") or {}).get("other_trucks"):
        tid = u["truck_id"]
    if not any(t.get("id") == tid for t in cfg.get("trucks", [])):
        tid = "main"
    return tid


def truck_store_path(tid: str) -> Path:
    return STORE_PATH if tid == "main" else DATA_DIR / "trucks" / f"{tid}.json"


def load_truck_store(tid: str) -> dict:
    data = _read_json(truck_store_path(tid))
    if not isinstance(data, dict):
        data = empty_store()
    base = empty_store()
    for k, v in base.items():
        data.setdefault(k, v)
    for k, v in base["settings"].items():
        data["settings"].setdefault(k, v)
    return data


def save_truck_store(tid: str, store: dict) -> None:
    _write_json(truck_store_path(tid), store)


def _secret_key() -> str:
    p = BASE_DIR / "data" / ".session_secret"
    try:
        if p.exists():
            k = p.read_text().strip()
            if k:
                return k
        p.parent.mkdir(parents=True, exist_ok=True)
        k = _secrets.token_hex(32)
        p.write_text(k)
        return k
    except OSError:
        return _secrets.token_hex(32)


app.secret_key = os.environ.get("OSFT_SECRET") or _secret_key()
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = _td(days=14)

OPEN_PATHS = {"/api/health", "/api/auth/status", "/api/auth/login", "/api/auth/logout", "/api/onboarding"}


@app.before_request
def _public_demo_gate():
    """Only active when OSFT_PUBLIC_DEMO=1 (the copy shared on the internet). See osft/public_demo.py."""
    if not public_demo.ENABLED:
        return None
    public_demo.maybe_restore(DATA_DIR)
    if public_demo.blocked(request.method, request.path):
        return jsonify({"ok": False, "error": public_demo.MESSAGE, "public_demo": True}), 403
    return None


@app.before_request
def _auth_gate():
    path = request.path
    if not path.startswith("/api/") or path in OPEN_PATHS or path.startswith("/api/locales/"):
        return None
    cfg = load_config()
    if not acct.auth_enabled(cfg.get("people", [])):
        return None  # open mode until the first admin PIN exists (same as OSBW)
    u = current_user(cfg)
    if not u:
        return jsonify({"ok": False, "error": "Log in with your 6-digit PIN.", "login_required": True}), 401
    perm = acct.required_perm(path, request.method)
    if perm and u.get("role") != "admin" and not (u.get("permissions") or {}).get(perm):
        return jsonify({"ok": False, "error": f"Your login doesn't have “{perm}” access. Ask an admin.",
                        "forbidden": perm}), 403
    return None


def _body() -> dict:
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}


# ---------- Auth + people (accounts) ----------

def _auth_status(cfg: dict) -> dict:
    people = cfg.get("people", [])
    u = current_user(cfg)
    return {
        "auth_enabled": acct.auth_enabled(people),
        "user": acct.public_user(u) if u else None,
        "people": [{"id": p["id"], "name": p["name"], "login": p["login"], "role": p["role"]}
                   for p in people if p.get("active", True) and p.get("pin_hash")],
        "permissions": acct.PERMISSIONS,
        "roles": list(acct.ROLES),
        "active_truck_id": active_truck_id(),
    }


@app.get("/api/auth/status")
def auth_status():
    return jsonify({"ok": True, **_auth_status(load_config())})


@app.post("/api/auth/login")
def auth_login():
    d = _body()
    pin = str(d.get("pin") or "").strip()
    if not acct.valid_pin(pin):
        return err("PIN must be exactly 6 digits.")
    cfg = load_config()
    users = [u for u in cfg.get("people", []) if u.get("active", True) and u.get("pin_hash")]
    if not users:
        return err("No logins set up yet — add people in Settings → People & access.")
    uid, login = d.get("user_id"), str(d.get("login") or "").strip().lower()
    if uid or login:
        target = next((u for u in users if u["id"] == uid or (login and u["login"] == login)), None)
        if not target:
            return err("Unknown or inactive login.", 404)
        if not acct.check_pin(pin, target["pin_hash"], target["pin_salt"]):
            return err("Wrong PIN.", 401)
    else:
        target = next((u for u in users if acct.check_pin(pin, u["pin_hash"], u["pin_salt"])), None)
        if not target:
            return err("Wrong PIN.", 401)
    session.clear()
    session.permanent = True
    session["user_id"] = target["id"]
    return jsonify({"ok": True, **_auth_status(cfg)})


@app.post("/api/auth/logout")
def auth_logout():
    session.clear()
    return jsonify({"ok": True, **_auth_status(load_config())})


@app.get("/api/people")
def people_list():
    cfg = load_config()
    return jsonify({"ok": True, "people": [acct.public_user(u) for u in cfg["people"]],
                    "permissions": acct.PERMISSIONS, "defaults": acct.DEFAULT_PERMS, "roles": list(acct.ROLES)})


@app.post("/api/people")
def people_create():
    cfg = load_config()
    was_open = not acct.auth_enabled(cfg.get("people", []))
    u, message = acct.make_user(_body(), cfg["people"])
    if message:
        return err(message)
    cfg["people"].append(u)
    save_config(cfg)
    if was_open and acct.auth_enabled(cfg.get("people", [])) and u["role"] == "admin":
        session.clear()
        session.permanent = True
        session["user_id"] = u["id"]          # first admin PIN → you're logged in, not locked out
    return jsonify({"ok": True, "person": acct.public_user(u), "auth_enabled": acct.auth_enabled(cfg.get("people", []))}), 201


def _admins_left(people: list, excluding: str) -> int:
    return sum(1 for p in people if p["id"] != excluding and p.get("role") == "admin" and p.get("active", True)
               and p.get("pin_hash"))


@app.put("/api/people/<pid>")
def people_update(pid: str):
    cfg = load_config()
    u = next((p for p in cfg["people"] if p["id"] == pid), None)
    if not u:
        return err("Person not found.", 404)
    d = _body()
    demoting = ("role" in d and d["role"] != "admin") or ("active" in d and not d["active"])
    if demoting and u.get("role") == "admin" and acct.auth_enabled(cfg.get("people", [])) and not _admins_left(cfg["people"], pid):
        return err("Keep at least one active admin with a PIN.")
    message = acct.update_user(u, d, cfg["people"])
    if message:
        return err(message)
    save_config(cfg)
    return jsonify({"ok": True, "person": acct.public_user(u)})


@app.post("/api/people/<pid>/reset-pin")
def people_reset_pin(pid: str):
    cfg = load_config()
    u = next((p for p in cfg["people"] if p["id"] == pid), None)
    if not u:
        return err("Person not found.", 404)
    pin = str(_body().get("pin") or "")
    if not acct.valid_pin(pin):
        return err("PIN must be exactly 6 digits.")
    u["pin_hash"], u["pin_salt"] = acct.hash_pin(pin)
    save_config(cfg)
    return jsonify({"ok": True, "person": acct.public_user(u)})


@app.delete("/api/people/<pid>")
def people_delete(pid: str):
    cfg = load_config()
    u = next((p for p in cfg["people"] if p["id"] == pid), None)
    if not u:
        return err("Person not found.", 404)
    if u.get("role") == "admin" and acct.auth_enabled(cfg.get("people", [])) and not _admins_left(cfg["people"], pid):
        return err("Keep at least one active admin with a PIN.")
    cfg["people"] = [p for p in cfg["people"] if p["id"] != pid]
    save_config(cfg)
    if session.get("user_id") == pid:
        session.clear()
    return jsonify({"ok": True, "deleted": pid})


# ---------- Business profile ----------

BUSINESS_FIELDS = ("name", "legal_name", "address", "phone", "email", "website", "panel_title", "timezone",
                   "currency", "anchor_day")


@app.get("/api/business")
def business_get():
    return jsonify({"ok": True, "business": load_config()["business"]})


@app.put("/api/business")
def business_put():
    d = _body()
    cfg = load_config()
    b = cfg["business"]
    for k in BUSINESS_FIELDS:
        if k in d:
            b[k] = str(d[k] or "").strip()[:300]
    if "name" in d and not b["name"]:
        return err("Business name is required.")
    if "email" in d and b["email"] and not _re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", b["email"]):
        return err("That email doesn't look right.")
    if "cycle_days" in d:
        try:
            cd = int(d["cycle_days"])
        except (TypeError, ValueError):
            return err("Count cycle must be a whole number of days.")
        if not 1 <= cd <= 31:
            return err("Count cycle must be 1–31 days.")
        b["cycle_days"] = cd
    if "updates_opt_in" in d:
        b["updates_opt_in"] = bool(d["updates_opt_in"])
    if "logo_data_url" in d:
        logo = str(d["logo_data_url"] or "")
        if logo and not logo.startswith("data:image/"):
            return err("Logo must be an image.")
        if len(logo) > 400_000:
            return err("Logo is too big — use an image under ~300 KB.")
        b["logo_data_url"] = logo
    save_config(cfg)
    return jsonify({"ok": True, "business": b})


# ---------- Trucks (OSBW venues) + transfers ----------

def _truck_summary(t: dict) -> dict:
    st = load_truck_store(t["id"])
    items = active_items(st)
    done = sorted([s for s in st["count_sessions"] if s.get("status") == "completed"],
                  key=lambda s: s.get("completed_at") or "")
    return {"id": t["id"], "name": st["settings"].get("truck_name") or ("Truck" if t["id"] == "main" else t["id"]),
            "notes": t.get("notes", ""), "item_count": len(items),
            "inventory_value": round(sum(float(i.get("on_hand") or 0) * float(i.get("cost") or 0) for i in items), 2),
            "low_par": sum(1 for i in items if float(i.get("on_hand") or 0) < float(i.get("par") or 0)),
            "last_count": done[-1]["completed_at"] if done else None}


@app.get("/api/trucks")
def trucks_list():
    cfg = load_config()
    rows = [_truck_summary(t) for t in cfg["trucks"]]
    return jsonify({"ok": True, "trucks": rows, "active_truck_id": active_truck_id(),
                    "total_value": round(sum(r["inventory_value"] for r in rows), 2)})


@app.post("/api/trucks")
def trucks_create():
    d = _body()
    name = str(d.get("name") or "").strip()
    if not name:
        return err("Truck name is required.")
    cfg = load_config()
    tid = "t-" + uuid.uuid4().hex[:8]
    cfg["trucks"].append({"id": tid, "notes": str(d.get("notes") or ""), "created_at": utc_now()})
    st = empty_store()
    st["settings"].update(truck_name=name, setup_complete=True)
    if d.get("copy_products"):
        src = load_store()
        st["settings"]["zones"] = list(src["settings"].get("zones") or ZONES)
        for it in active_items(src):
            c = {k: v for k, v in it.items() if k != "id"}
            c.update(id=str(uuid.uuid4()), on_hand=0.0, created_at=utc_now(), updated_at=utc_now())
            st["items"].append(c)
    save_truck_store(tid, st)
    save_config(cfg)
    return jsonify({"ok": True, "truck": _truck_summary({"id": tid})}), 201


@app.put("/api/trucks/<tid>")
def trucks_update(tid: str):
    cfg = load_config()
    t = next((x for x in cfg["trucks"] if x["id"] == tid), None)
    if not t:
        return err("Truck not found.", 404)
    d = _body()
    if "notes" in d:
        t["notes"] = str(d["notes"] or "")
    if "name" in d:
        n = str(d["name"] or "").strip()
        if not n:
            return err("Truck name is required.")
        st = load_truck_store(tid)
        st["settings"]["truck_name"] = n
        st["settings"]["setup_complete"] = True
        save_truck_store(tid, st)
    save_config(cfg)
    return jsonify({"ok": True, "truck": _truck_summary(t)})


@app.delete("/api/trucks/<tid>")
def trucks_delete(tid: str):
    if tid == "main":
        return err("The first truck can't be deleted — rename it instead.")
    cfg = load_config()
    if not any(t["id"] == tid for t in cfg["trucks"]):
        return err("Truck not found.", 404)
    write_backup("delete-truck")
    cfg["trucks"] = [t for t in cfg["trucks"] if t["id"] != tid]
    if cfg.get("active_truck_id") == tid:
        cfg["active_truck_id"] = "main"
    save_config(cfg)
    p = truck_store_path(tid)
    if p.exists():
        p.unlink()
    return jsonify({"ok": True, "deleted": tid})


@app.post("/api/trucks/<tid>/activate")
def trucks_activate(tid: str):
    cfg = load_config()
    if not any(t["id"] == tid for t in cfg["trucks"]):
        return err("Truck not found.", 404)
    u = current_user(cfg)
    if u and u.get("role") != "admin" and not (u.get("permissions") or {}).get("other_trucks") and u.get("truck_id") \
            and u["truck_id"] != tid:
        return err("Your login is locked to one truck.", 403)
    cfg["active_truck_id"] = tid
    save_config(cfg)
    return jsonify({"ok": True, "active_truck_id": tid, "truck": _truck_summary({"id": tid})})


@app.get("/api/transfers")
def transfers_list():
    st = load_store()
    return jsonify({"ok": True, "transfers": sorted(st.get("transfers", []), key=lambda x: x.get("at") or "", reverse=True)})


@app.post("/api/transfers")
def transfers_create():
    d = _body()
    to_id = str(d.get("to_truck_id") or "")
    from_id = active_truck_id()
    cfg = load_config()
    if not any(t["id"] == to_id for t in cfg["trucks"]):
        return err("Pick the truck you're sending to.")
    if to_id == from_id:
        return err("That's the truck you're on — pick a different one.")
    lines_in = d.get("lines") or []
    if not isinstance(lines_in, list) or not lines_in:
        return err("Add at least one product to transfer.")
    src = load_truck_store(from_id)
    dst = load_truck_store(to_id)
    moved = []
    for ln in lines_in:
        it = find_item(src, str(ln.get("item_id") or ""))
        if not it or it.get("archived"):
            return err("Unknown product in transfer.")
        try:
            q = float(ln.get("qty"))
        except (TypeError, ValueError):
            return err(f"Qty for {it['name']} must be a number.")
        if q <= 0:
            continue
        if q > float(it.get("on_hand") or 0) + 1e-9:
            return err(f"Only {float(it.get('on_hand') or 0):g} {it['unit']} of {it['name']} on this truck.")
        target = next((x for x in active_items(dst) if x["name"].lower() == it["name"].lower()
                       and x["unit"].lower() == it["unit"].lower()), None)
        if not target:
            target = dict(it)
            target.update(id=str(uuid.uuid4()), on_hand=0.0, par=0.0, created_at=utc_now())
            if target.get("zone") not in store_zones(dst):
                target["zone"] = "dry"
            dst["items"].append(target)
        it["on_hand"] = round(float(it.get("on_hand") or 0) - q, 4)
        target["on_hand"] = round(float(target.get("on_hand") or 0) + q, 4)
        it["updated_at"] = target["updated_at"] = utc_now()
        moved.append({"item_id": it["id"], "to_item_id": target["id"], "name": it["name"], "qty": q, "unit": it["unit"],
                      "unit_cost": it.get("cost")})
    if not moved:
        return err("Nothing to move — quantities were zero.")
    rec = {"id": str(uuid.uuid4()), "at": utc_now(), "from_truck_id": from_id, "to_truck_id": to_id,
           "from_name": src["settings"].get("truck_name"), "to_name": dst["settings"].get("truck_name"),
           "lines": moved, "note": str(d.get("note") or ""), "by": current_user_name()}
    src.setdefault("transfers", []).append({**rec, "direction": "out"})
    dst.setdefault("transfers", []).append({**rec, "direction": "in"})
    save_truck_store(from_id, src)
    save_truck_store(to_id, dst)
    return jsonify({"ok": True, "transfer": rec}), 201


# ---------- Vendor / category (GL) / POS accounts ----------

VENDOR_FIELDS = ("name", "rep", "phone", "email", "account_no", "cutoff", "delivery_days", "lead_days", "terms",
                 "order_method", "notes")
EMAIL_RE = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _vendor_clean(d: dict, partial: bool):
    out = {k: str(d[k] or "").strip()[:500] for k in VENDOR_FIELDS if k in d}
    if (not partial or "name" in d) and not out.get("name"):
        return None, "Vendor name is required."
    if out.get("email") and not EMAIL_RE.match(out["email"]):
        return None, "That email doesn't look right."
    if out.get("lead_days"):
        try:
            out["lead_days"] = str(int(float(out["lead_days"])))
        except ValueError:
            return None, "Lead time must be a number of days."
    return out, None


@app.get("/api/vendors")
def vendors_list():
    return jsonify({"ok": True, "vendors": load_config()["vendors"]})


@app.post("/api/vendors")
def vendors_create():
    out, message = _vendor_clean(_body(), False)
    if message:
        return err(message)
    cfg = load_config()
    if any(v["name"].lower() == out["name"].lower() for v in cfg["vendors"]):
        return err("You already have a vendor with that name.")
    v = {"id": str(uuid.uuid4()), **{k: "" for k in VENDOR_FIELDS}, **out, "created_at": utc_now()}
    cfg["vendors"].append(v)
    save_config(cfg)
    return jsonify({"ok": True, "vendor": v}), 201


@app.put("/api/vendors/<vid>")
def vendors_update(vid: str):
    cfg = load_config()
    v = find_by_id(cfg["vendors"], vid)
    if not v:
        return err("Vendor not found.", 404)
    out, message = _vendor_clean(_body(), True)
    if message:
        return err(message)
    v.update(out)
    save_config(cfg)
    return jsonify({"ok": True, "vendor": v})


@app.delete("/api/vendors/<vid>")
def vendors_delete(vid: str):
    cfg = load_config()
    if not find_by_id(cfg["vendors"], vid):
        return err("Vendor not found.", 404)
    cfg["vendors"] = [v for v in cfg["vendors"] if v["id"] != vid]
    save_config(cfg)
    st = load_store()
    for it in st["items"]:
        if it.get("vendor_id") == vid:
            it["vendor_id"] = None
    save_store(st)
    return jsonify({"ok": True, "deleted": vid})


CATEGORY_KINDS = ["food", "beverage", "packaging", "supplies", "fuel", "other"]


def _ensure_categories(cfg: dict, store: dict | None = None) -> list:
    cats = cfg.setdefault("categories", [])
    names = {c["name"].lower() for c in cats}
    wanted = list(starter_catalog.CATEGORIES)
    if store:
        wanted += sorted({i.get("category") for i in active_items(store) if i.get("category")})
    for n in wanted:
        if n and n.lower() not in names:
            kind = ("packaging" if "Packaging" in n else "supplies" if ("Paper" in n or "Smallwares" in n)
                    else "fuel" if "Propane" in n else "beverage" if "Beverage" in n else "food")
            cats.append({"id": str(uuid.uuid4()), "name": n, "gl_code": "", "kind": kind, "target_pct": None})
            names.add(n.lower())
    return cats


@app.get("/api/accounts/categories")
def categories_list():
    cfg = load_config()
    before = len(cfg.get("categories", []))
    cats = _ensure_categories(cfg, load_store())
    if len(cats) != before:
        save_config(cfg)
    return jsonify({"ok": True, "categories": cats, "kinds": CATEGORY_KINDS})


def _cat_clean(d: dict, partial: bool):
    out = {}
    if "name" in d or not partial:
        n = str(d.get("name") or "").strip()
        if not n:
            return None, "Category name is required."
        out["name"] = n
    if "gl_code" in d:
        out["gl_code"] = str(d["gl_code"] or "").strip()[:40]
    if "kind" in d:
        k = str(d["kind"] or "food")
        if k not in CATEGORY_KINDS:
            return None, "Kind must be food, beverage, packaging, supplies, fuel or other."
        out["kind"] = k
    if "target_pct" in d:
        if d["target_pct"] in (None, ""):
            out["target_pct"] = None
        else:
            try:
                tp = float(d["target_pct"])
            except (TypeError, ValueError):
                return None, "Target % must be a number."
            if not 0 <= tp <= 100:
                return None, "Target % must be 0–100."
            out["target_pct"] = tp
    return out, None


@app.post("/api/accounts/categories")
def categories_create():
    out, message = _cat_clean(_body(), False)
    if message:
        return err(message)
    cfg = load_config()
    if any(c["name"].lower() == out["name"].lower() for c in cfg["categories"]):
        return err("That category already exists.")
    c = {"id": str(uuid.uuid4()), "gl_code": "", "kind": "food", "target_pct": None, **out}
    cfg["categories"].append(c)
    save_config(cfg)
    return jsonify({"ok": True, "category": c}), 201


@app.put("/api/accounts/categories/<cid>")
def categories_update(cid: str):
    cfg = load_config()
    c = find_by_id(cfg["categories"], cid)
    if not c:
        return err("Category not found.", 404)
    out, message = _cat_clean(_body(), True)
    if message:
        return err(message)
    old = c["name"]
    c.update(out)
    save_config(cfg)
    if out.get("name") and out["name"] != old:      # rename flows through to products
        st = load_store()
        for it in st["items"]:
            if it.get("category") == old:
                it["category"] = out["name"]
        save_store(st)
    return jsonify({"ok": True, "category": c})


@app.delete("/api/accounts/categories/<cid>")
def categories_delete(cid: str):
    cfg = load_config()
    c = find_by_id(cfg["categories"], cid)
    if not c:
        return err("Category not found.", 404)
    if any(i.get("category") == c["name"] for i in active_items(load_store())):
        return err("Products still use this category — move them first.")
    cfg["categories"] = [x for x in cfg["categories"] if x["id"] != cid]
    save_config(cfg)
    return jsonify({"ok": True, "deleted": cid})


POS_ACCOUNT_FIELDS = ("label", "provider", "location", "account_ref", "notes")


@app.get("/api/accounts/pos")
def pos_accounts_list():
    return jsonify({"ok": True, "pos_accounts": load_config()["pos_accounts"]})


def _pos_clean(d: dict, partial: bool):
    out = {k: str(d[k] or "").strip()[:300] for k in POS_ACCOUNT_FIELDS if k in d}
    if (not partial or "label" in d) and not out.get("label"):
        return None, "Give this POS account a name."
    if "provider" in out and out["provider"] not in pos.ADAPTERS:
        return None, "Unknown POS type."
    if "mapping" in d:
        m = d["mapping"] if isinstance(d["mapping"], dict) else {}
        out["mapping"] = {k: v for k, v in m.items() if isinstance(v, str) and v}
    if "default" in d:
        out["default"] = bool(d["default"])
    return out, None


@app.post("/api/accounts/pos")
def pos_accounts_create():
    out, message = _pos_clean(_body(), False)
    if message:
        return err(message)
    cfg = load_config()
    a = {"id": str(uuid.uuid4()), "provider": "generic_csv", "location": "", "account_ref": "", "notes": "",
         "mapping": {}, "default": not cfg["pos_accounts"], "truck_id": active_truck_id(), **out}
    if a["default"]:
        for x in cfg["pos_accounts"]:
            x["default"] = False
    cfg["pos_accounts"].append(a)
    save_config(cfg)
    return jsonify({"ok": True, "account": a}), 201


@app.put("/api/accounts/pos/<aid>")
def pos_accounts_update(aid: str):
    cfg = load_config()
    a = find_by_id(cfg["pos_accounts"], aid)
    if not a:
        return err("POS account not found.", 404)
    out, message = _pos_clean(_body(), True)
    if message:
        return err(message)
    if out.get("default"):
        for x in cfg["pos_accounts"]:
            x["default"] = False
    a.update(out)
    save_config(cfg)
    return jsonify({"ok": True, "account": a})


@app.delete("/api/accounts/pos/<aid>")
def pos_accounts_delete(aid: str):
    cfg = load_config()
    if not find_by_id(cfg["pos_accounts"], aid):
        return err("POS account not found.", 404)
    cfg["pos_accounts"] = [x for x in cfg["pos_accounts"] if x["id"] != aid]
    save_config(cfg)
    return jsonify({"ok": True, "deleted": aid})


@app.post("/api/pos/match")
def pos_match():
    """Link an unmatched POS item name to a menu item (OSBW POS review → match)."""
    d = _body()
    pos_name = str(d.get("pos_name") or "").strip()
    st = load_store()
    mi = find_by_id(st["menu_items"], str(d.get("menu_item_id") or ""))
    if not pos_name or not mi:
        return err("Pick the POS item and the menu item it should count as.")
    if pos_name.lower() not in [p.lower() for p in mi.get("pos_names") or []]:
        mi.setdefault("pos_names", []).append(pos_name)
    for imp in st["sales_imports"]:
        _link_menu(st, imp["lines"])
    save_store(st)
    return jsonify({"ok": True, "menu_item": mi})


# ---------- Settings: zones ----------

@app.put("/api/settings/zones")
def settings_zones():
    zs = _body().get("zones")
    allowed = list(ZONES) + list(EXTRA_ZONES)
    if not isinstance(zs, list) or any(z not in allowed for z in zs):
        return err(f"Zones must come from: {', '.join(allowed)}.")
    st = load_store()
    final = [z for z in allowed if z in zs or z in ZONES]
    missing = {i["zone"] for i in active_items(st)} - set(final)
    if missing:
        return err(f"Products still live in: {', '.join(sorted(missing))}. Move them first.")
    st["settings"]["zones"] = final
    if st["settings"].get("sections"):
        names = {x["key"]: x["name"] for x in st["settings"]["sections"]}
        keep = [x for x in st["settings"]["sections"] if x["key"] not in EXTRA_ZONES or x["key"] in final]
        for z in final:
            if z not in [x["key"] for x in keep]:
                keep.append({"key": z, "name": names.get(z) or sections_mod.from_zones([z])[0]["name"]})
        st["settings"]["sections"] = keep
    save_store(st)
    return jsonify({"ok": True, "zones": store_zones(st)})


# ---------- Staff board ----------

@app.get("/api/staff-board")
def staff_board_list():
    cfg = load_config()
    tid = active_truck_id()
    posts = [p for p in cfg["staff_board"] if not p.get("truck_id") or p["truck_id"] == tid]
    posts = sorted(posts, key=lambda p: p.get("created_at") or "", reverse=True)
    posts.sort(key=lambda p: not p.get("pinned"))
    return jsonify({"ok": True, "posts": posts})


@app.post("/api/staff-board")
def staff_board_post():
    d = _body()
    text = str(d.get("text") or "").strip()
    if not text:
        return err("Write a note first.")
    cfg = load_config()
    p = {"id": str(uuid.uuid4()), "text": text[:2000],
         "author": current_user_name() or str(d.get("author") or "").strip() or None,
         "truck_id": active_truck_id() if d.get("this_truck_only") else None, "pinned": bool(d.get("pinned")),
         "created_at": utc_now()}
    cfg["staff_board"] = (cfg["staff_board"] + [p])[-300:]
    save_config(cfg)
    return jsonify({"ok": True, "post": p}), 201


@app.delete("/api/staff-board/<pid>")
def staff_board_delete(pid: str):
    cfg = load_config()
    if not find_by_id(cfg["staff_board"], pid):
        return err("Note not found.", 404)
    cfg["staff_board"] = [p for p in cfg["staff_board"] if p["id"] != pid]
    save_config(cfg)
    return jsonify({"ok": True})


@app.post("/api/staff-board/<pid>/pin")
def staff_board_pin(pid: str):
    cfg = load_config()
    p = find_by_id(cfg["staff_board"], pid)
    if not p:
        return err("Note not found.", 404)
    p["pinned"] = not p.get("pinned")
    save_config(cfg)
    return jsonify({"ok": True, "post": p})


# ---------- Starter catalog + product import / export ----------

@app.get("/api/catalog/starter")
def catalog_starter():
    st = load_store()
    have = {i["name"].lower() for i in active_items(st)}
    rows = [{**c, "in_list": c["name"].lower() in have} for c in starter_catalog.CATALOG]
    return jsonify({"ok": True, "items": rows, "categories": list(starter_catalog.CATEGORIES), "count": len(rows)})


def _new_item(d: dict) -> dict:
    now = utc_now()
    return {"id": str(uuid.uuid4()), "name": d["name"], "unit": d.get("unit") or "ea", "par": float(d.get("par") or 0),
            "category": d.get("category") or "Other", "zone": d.get("zone") or "dry",
            "on_hand": float(d.get("on_hand") or 0), "cost": d.get("cost"), "case_size": d.get("case_size"),
            "pack": d.get("pack") or "", "name_es": d.get("name_es") or "", "aliases": list(d.get("aliases") or []),
            "vendor_id": d.get("vendor_id"), "barcode": d.get("barcode") or "", "sku": d.get("sku") or "",
            "notes": d.get("notes") or "", "archived": False, "created_at": now, "updated_at": now}


@app.post("/api/catalog/starter/add")
def catalog_starter_add():
    d = _body()
    ids = d.get("ids") or []
    pars = d.get("pars") or {}
    if not isinstance(ids, list) or not ids:
        return err("Pick at least one product.")
    by_id = {c["id"]: c for c in starter_catalog.CATALOG}
    st = load_store()
    zones = store_zones(st)
    have = {i["name"].lower() for i in active_items(st)}
    added = []
    for sid in ids:
        c = by_id.get(sid)
        if not c or c["name"].lower() in have:
            continue
        it = _new_item({**c, "cost": None, "par": pars.get(sid) or 0})   # never invent a price
        if it["zone"] not in zones:
            it["zone"] = "dry"
        it["starter_id"] = sid
        st["items"].append(it)
        have.add(c["name"].lower())
        added.append(it)
    save_store(st)
    return jsonify({"ok": True, "added": len(added), "items": added})


EXPORT_COLS = ["name", "name_es", "category", "zone", "unit", "pack", "case_size", "par", "on_hand", "cost",
               "vendor", "sku", "barcode", "aliases", "notes"]


def _csv_response(rows: list, cols: list, filename: str) -> Response:
    buf = _io.StringIO()
    w = _csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow(["" if r.get(c) is None else r.get(c) for c in cols])
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.get("/api/items/export.csv")
def items_export():
    st = load_store()
    vendors = {v["id"]: v["name"] for v in load_config()["vendors"]}
    rows = []
    for i in sorted(active_items(st), key=lambda x: (x.get("zone") or "", x["name"].lower())):
        rows.append({**i, "vendor": vendors.get(i.get("vendor_id") or "", ""), "aliases": "|".join(i.get("aliases") or [])})
    return _csv_response(rows, EXPORT_COLS, "osft-products.csv")


def _f(v):
    v = str(v or "").strip().replace("$", "").replace(",", "")
    if not v:
        return None
    return float(v)


@app.post("/api/items/import")
def items_import():
    f = request.files.get("file")
    text = (request.form.get("text") or "") if request.form else ""
    if f is not None and f.filename:
        text = f.read().decode("utf-8-sig", errors="replace")
    if not text.strip():
        d = _body()
        text = str(d.get("text") or "")
    if not text.strip():
        return err("Choose a CSV file or paste rows.")
    dry = str(request.args.get("dry_run") or request.form.get("dry_run") or "").lower() in ("1", "true", "yes")
    rows = list(_csv.DictReader(_io.StringIO(text.lstrip("\ufeff"))))
    if not rows:
        return err("No rows found — the first line must be headers (name, unit, par …).")
    st = load_store()
    cfg = load_config()
    zones = store_zones(st)
    by_name = {i["name"].lower(): i for i in active_items(st)}
    vend = {v["name"].lower(): v for v in cfg["vendors"]}
    created, updated, errors, new_vendors = [], [], [], []
    for n, raw in enumerate(rows, start=2):
        r = {str(k or "").strip().lower().replace(" ", "_"): (v or "").strip() for k, v in raw.items()}
        name = r.get("name") or r.get("product") or r.get("item")
        if not name:
            errors.append({"row": n, "error": "missing name"})
            continue
        try:
            vals = {"par": _f(r.get("par")), "on_hand": _f(r.get("on_hand")), "cost": _f(r.get("cost")),
                    "case_size": _f(r.get("case_size"))}
        except ValueError:
            errors.append({"row": n, "error": "par / on_hand / cost / case_size must be numbers"})
            continue
        zone = (r.get("zone") or "").lower()
        if zone and zone not in zones:
            errors.append({"row": n, "error": f"unknown zone “{zone}”"})
            continue
        vid = None
        vname = r.get("vendor") or ""
        if vname:
            v = vend.get(vname.lower())
            if not v:
                v = {"id": str(uuid.uuid4()), **{k: "" for k in VENDOR_FIELDS}, "name": vname, "created_at": utc_now()}
                vend[vname.lower()] = v
                new_vendors.append(v)
            vid = v["id"]
        patch = {k: v for k, v in vals.items() if v is not None}
        for k in ("name_es", "category", "unit", "pack", "sku", "barcode", "notes"):
            if r.get(k):
                patch[k] = r[k]
        if zone:
            patch["zone"] = zone
        if r.get("aliases"):
            patch["aliases"] = [a.strip() for a in r["aliases"].split("|") if a.strip()]
        if vid:
            patch["vendor_id"] = vid
        ex = by_name.get(name.lower())
        if ex:
            if not dry:
                ex.update(patch)
                ex["updated_at"] = utc_now()
            updated.append(name)
        else:
            if not dry:
                it = _new_item({"name": name, **patch})
                st["items"].append(it)
                by_name[name.lower()] = it
            created.append(name)
    if not dry:
        if new_vendors:
            cfg["vendors"].extend(new_vendors)
            save_config(cfg)
        save_store(st)
    return jsonify({"ok": True, "dry_run": dry, "created": len(created), "updated": len(updated),
                    "created_names": created[:50], "updated_names": updated[:50], "errors": errors,
                    "new_vendors": [v["name"] for v in new_vendors]})


# ---------- Voice counting (OSBW speak-your-inventory) ----------

@app.post("/api/voice/parse")
def voice_parse():
    d = _body()
    text = str(d.get("text") or "")
    if not text.strip():
        return err("Say or type what you counted first.")
    st = load_store()
    scope = "all" if d.get("scope") == "all" else "mentioned_zones"
    return jsonify({"ok": True, **voice.reconcile(text, active_items(st), store_zones(st), scope)})


@app.post("/api/voice/apply")
def voice_apply():
    """Body: {counts: {item_id: qty}, text, complete: bool, zero_missing: [item_id]}"""
    d = _body()
    counts = d.get("counts")
    if not isinstance(counts, dict) or not counts:
        return err("Nothing to save — confirm at least one line.")
    st = load_store()
    clean = {}
    for iid, q in counts.items():
        it = find_item(st, str(iid))
        if not it or it.get("archived"):
            return err(f"Unknown product: {iid}")
        try:
            qv = float(q)
        except (TypeError, ValueError):
            return err(f"Qty for {it['name']} must be a number.")
        if qv < 0 or qv > voice.MAX_QTY:
            return err(f"Qty for {it['name']} is out of range.")
        clean[it["id"]] = round(qv, 4)
    for iid in d.get("zero_missing") or []:
        if find_item(st, str(iid)):
            clean.setdefault(str(iid), 0.0)
    sess = next((s for s in st["count_sessions"] if s.get("status") == "in_progress"), None)
    if not sess:
        sess = {"id": str(uuid.uuid4()), "status": "in_progress", "started_at": utc_now(), "completed_at": None,
                "counts": {}, "source": "voice"}
        st["count_sessions"].append(sess)
    _sc = sess.get("scope") or {}
    if not _sc.get("full", True):
        outside = [find_item(st, i)["name"] for i in clean if i not in (_sc.get("item_ids") or [])]
        if outside:
            return err(f"Not part of this {sess.get('type_name') or 'count'}: {', '.join(outside[:5])}")
    sess["counts"] = {**(sess.get("counts") or {}), **clean}
    sess.setdefault("voice_notes", []).append({"at": utc_now(), "text": str(d.get("text") or "")[:5000],
                                               "lines": len(clean), "by": current_user_name()})
    sess["source"] = sess.get("source") or "voice"
    variance = None
    if d.get("complete"):
        for iid, q in sess["counts"].items():
            it = find_item(st, iid)
            if it and not it.get("archived"):
                it["on_hand"] = float(q)
                it["updated_at"] = utc_now()
        sess["status"] = "completed"
        sess["completed_at"] = utc_now()
        sess["counted_by"] = current_user_name()
        variance = compute_variance(st, sess)
    save_store(st)
    return jsonify({"ok": True, "session": sess, "saved": len(clean), "variance": variance})


@app.post("/api/voice/walk")
def voice_walk():
    text = str(_body().get("text") or "")
    if not text.strip():
        return err("Walk your truck out loud first — e.g. “cooler: ground beef, cheese. freezer: ice”.")
    st = load_store()
    out = voice.walk_build(text, active_items(st), starter_catalog.CATALOG)
    sec = _body().get("section")
    if sec:
        if sec not in store_zones(st):
            return err("Unknown section.")
        for p in out["proposals"]:
            p["zone"] = sec
        out["zones"] = [sec]
    return jsonify({"ok": True, **out})


@app.post("/api/voice/walk/apply")
def voice_walk_apply():
    props = _body().get("proposals") or []
    if not isinstance(props, list) or not props:
        return err("Nothing to add.")
    st = load_store()
    zones = store_zones(st)
    by_starter = {c["id"]: c for c in starter_catalog.CATALOG}
    have = {i["name"].lower(): i for i in active_items(st)}
    added, updated = 0, 0
    for p in props:
        if not isinstance(p, dict) or p.get("skip"):
            continue
        name = str(p.get("name") or "").strip()
        if not name:
            continue
        zone = p.get("zone") if p.get("zone") in zones else default_zone(zones)
        ex = have.get(name.lower())
        if ex:
            if p.get("on_hand") is not None:
                ex["on_hand"] = float(p["on_hand"])
            if p.get("par") not in (None, ""):
                ex["par"] = float(p["par"])
            ex["zone"] = zone
            updated += 1
            continue
        tmpl = by_starter.get(p.get("starter_id") or "") or {}
        it = _new_item({**tmpl, "name": name, "zone": zone, "unit": p.get("unit") or tmpl.get("unit") or "ea",
                        "category": p.get("category") or tmpl.get("category") or "Other",
                        "on_hand": p.get("on_hand") or 0, "par": p.get("par") or 0, "cost": None})
        st["items"].append(it)
        have[name.lower()] = it
        added += 1
    st["settings"]["setup_complete"] = True
    save_store(st)
    return jsonify({"ok": True, "added": added, "updated": updated})


# ---------- Receiving (batch) + invoice text ----------

@app.post("/api/receives/batch")
def receives_batch():
    d = _body()
    lines_in = d.get("lines") or []
    if not isinstance(lines_in, list) or not lines_in:
        return err("Add at least one line.")
    st = load_store()
    vendor = str(d.get("vendor") or "").strip()
    note = str(d.get("note") or "").strip()
    inv = str(d.get("invoice_no") or "").strip()
    batch = str(uuid.uuid4())
    recs = []
    photos = [str(x) for x in (d.get("photos") or []) if isinstance(x, str)]
    for ph in photos:
        if "/" in ph or "\\" in ph or ph.startswith(".") or not (PHOTOS_DIR / ph).is_file():
            return err("Attached invoice file not found — upload it again.")
    zones = store_zones(st)
    for ln in lines_in:
        if not isinstance(ln, dict):
            return err("Bad line.")
        if not ln.get("item_id") and isinstance(ln.get("new_item"), dict):
            ni = ln["new_item"]
            nm = str(ni.get("name") or "").strip()
            if not nm:
                return err("A new product needs a name.")
            ex = next((i for i in active_items(st) if i["name"].lower() == nm.lower()), None)
            if ex:
                ln["item_id"] = ex["id"]
            else:
                z = ni.get("zone") if ni.get("zone") in zones else default_zone(zones)
                it_new = _new_item({"name": nm[:80], "unit": str(ni.get("unit") or "ea")[:20], "zone": z,
                                    "category": str(ni.get("category") or "Other")[:40], "cost": None, "par": 0, "on_hand": 0})
                st["items"].append(it_new)
                ln["item_id"] = it_new["id"]
    for ln in lines_in:
        it = find_item(st, str(ln.get("item_id") or ""))
        if not it or it.get("archived"):
            return err("Unknown product on a line.")
        try:
            q = float(ln.get("qty"))
        except (TypeError, ValueError):
            return err(f"Qty for {it['name']} must be a number.")
        if q <= 0:
            return err(f"Qty for {it['name']} must be more than zero.")
        uc = ln.get("unit_cost")
        if uc not in (None, ""):
            try:
                uc = float(uc)
            except (TypeError, ValueError):
                return err(f"Cost for {it['name']} must be a number.")
            it["cost"] = uc
        else:
            uc = None
        it["on_hand"] = float(it.get("on_hand") or 0) + q
        it["updated_at"] = utc_now()
        r = {"id": str(uuid.uuid4()), "batch_id": batch, "item_id": it["id"], "item_name": it["name"], "qty": q,
             "unit": it["unit"], "note": note, "vendor": vendor, "invoice_no": inv, "unit_cost": uc, "photos": list(photos),
             "received_at": utc_now(), "by": current_user_name(), "po_id": d.get("po_id")}
        st["receives"].append(r)
        recs.append(r)
    save_store(st)
    return jsonify({"ok": True, "batch_id": batch, "receives": recs}), 201


INV_LINE = _re.compile(r"^\s*(?P<qty>\d+(?:\.\d+)?)\s*(?:x\s*)?(?P<unit>cs|case|cases|lb|lbs|ea|each|bag|bags|box|gal|qt|pk|pack|ct)?\s+"
                       r"(?P<name>.+?)(?:\s+@?\s*\$?(?P<price>\d+(?:\.\d{1,2})))?\s*$", _re.I)


def parse_invoice_text(text: str, items: list) -> list:
    out = []
    for raw in text.splitlines():
        if not raw.strip():
            continue
        m = INV_LINE.match(raw)
        if not m:
            out.append({"raw": raw, "status": "unread"})
            continue
        name = m.group("name").strip(" -–:")
        mt = voice.match_entry(name, items, None)
        qty = float(m.group("qty"))
        unit = (m.group("unit") or "").lower()
        line = {"raw": raw, "name": name, "qty": qty, "unit": unit or None,
                "unit_cost": float(m.group("price")) if m.group("price") else None,
                "status": mt["status"], "item_id": None, "item_name": None}
        if mt["item"] is not None and mt["status"] != "unmatched":
            line["item_id"], line["item_name"] = mt["item"]["id"], mt["item"]["name"]
            if unit.startswith("c") and unit != "ct" and mt["item"].get("case_size"):
                line["qty"] = qty * float(mt["item"]["case_size"])
                line["note"] = f"{qty:g} case × {float(mt['item']['case_size']):g}"
        out.append(line)
    return out


@app.post("/api/invoice/parse")
def invoice_parse():
    text = str(_body().get("text") or "")
    if not text.strip():
        return err("Paste the invoice lines first (one product per line).")
    return jsonify({"ok": True, "lines": parse_invoice_text(text, active_items(load_store()))})


# ---------- Purchase orders ----------

def _po_totals(po: dict) -> None:
    po["total"] = round(sum(float(l.get("qty") or 0) * float(l.get("unit_cost") or 0) for l in po["lines"]), 2)


@app.get("/api/orders")
def orders_list():
    st = load_store()
    return jsonify({"ok": True, "orders": sorted(st.get("purchase_orders", []), key=lambda p: p.get("created_at") or "",
                                                 reverse=True)})


@app.post("/api/orders")
def orders_create():
    d = _body()
    st = load_store()
    cfg = load_config()
    lines = []
    if d.get("from_reorder"):
        rep = build_reorder(st)
        grp = next((g for g in rep["groups"] if (g.get("vendor_id") or "") == (d.get("vendor_id") or "")
                    or g["vendor"] == d.get("vendor")), None)
        if not grp:
            return err("Nothing below PAR for that vendor.")
        for l in grp["lines"]:
            lines.append({"item_id": l["id"], "name": l["name"], "qty": l["order_qty"], "unit": l["unit"],
                          "cases": l["order_cases"], "case_size": l["case_size"], "unit_cost": l["cost"]})
        vendor_id, vendor_name = grp.get("vendor_id"), grp["vendor"]
    else:
        for l in d.get("lines") or []:
            it = find_item(st, str(l.get("item_id") or ""))
            if not it:
                return err("Unknown product on order.")
            try:
                q = float(l.get("qty"))
            except (TypeError, ValueError):
                return err(f"Qty for {it['name']} must be a number.")
            if q <= 0:
                continue
            lines.append({"item_id": it["id"], "name": it["name"], "qty": q, "unit": it["unit"],
                          "cases": None, "case_size": it.get("case_size"), "unit_cost": it.get("cost")})
        vendor_id = d.get("vendor_id")
        vendor_name = (find_by_id(cfg["vendors"], vendor_id or "") or {}).get("name") or str(d.get("vendor") or "")
    if not lines:
        return err("Add at least one product.")
    po = {"id": str(uuid.uuid4()), "number": f"PO-{len(st.get('purchase_orders', [])) + 1001}",
          "vendor_id": vendor_id, "vendor": vendor_name, "status": "draft", "lines": lines,
          "note": str(d.get("note") or ""), "created_at": utc_now(), "sent_at": None, "received_at": None,
          "created_by": current_user_name()}
    _po_totals(po)
    st.setdefault("purchase_orders", []).append(po)
    save_store(st)
    return jsonify({"ok": True, "order": po}), 201


def _get_po(st, oid):
    return find_by_id(st.get("purchase_orders", []), oid)


@app.put("/api/orders/<oid>")
def orders_update(oid: str):
    st = load_store()
    po = _get_po(st, oid)
    if not po:
        return err("Order not found.", 404)
    if po["status"] == "received":
        return err("This order was already received.")
    d = _body()
    if "note" in d:
        po["note"] = str(d["note"] or "")
    if "lines" in d:
        new = []
        for l in d["lines"] or []:
            try:
                q = float(l.get("qty"))
            except (TypeError, ValueError):
                return err("Qty must be a number.")
            if q > 0:
                new.append({**l, "qty": q})
        if not new:
            return err("An order needs at least one line.")
        po["lines"] = new
    _po_totals(po)
    save_store(st)
    return jsonify({"ok": True, "order": po})


@app.delete("/api/orders/<oid>")
def orders_delete(oid: str):
    st = load_store()
    if not _get_po(st, oid):
        return err("Order not found.", 404)
    st["purchase_orders"] = [p for p in st["purchase_orders"] if p["id"] != oid]
    save_store(st)
    return jsonify({"ok": True})


@app.post("/api/orders/<oid>/sent")
def orders_sent(oid: str):
    st = load_store()
    po = _get_po(st, oid)
    if not po:
        return err("Order not found.", 404)
    po["status"] = "sent"
    po["sent_at"] = utc_now()
    save_store(st)
    return jsonify({"ok": True, "order": po})


@app.post("/api/orders/<oid>/receive")
def orders_receive(oid: str):
    st = load_store()
    po = _get_po(st, oid)
    if not po:
        return err("Order not found.", 404)
    if po["status"] == "received":
        return err("Already received.")
    got = _body().get("received") or {}
    discrepancies = []
    batch = str(uuid.uuid4())
    for l in po["lines"]:
        q = got.get(l["item_id"], l["qty"])
        try:
            q = float(q)
        except (TypeError, ValueError):
            return err(f"Qty for {l['name']} must be a number.")
        if abs(q - float(l["qty"])) > 1e-9:
            discrepancies.append({"item_id": l["item_id"], "name": l["name"], "ordered": l["qty"], "received": q})
        l["received_qty"] = q
        it = find_item(st, l["item_id"])
        if it and q > 0:
            it["on_hand"] = float(it.get("on_hand") or 0) + q
            it["updated_at"] = utc_now()
            st["receives"].append({"id": str(uuid.uuid4()), "batch_id": batch, "item_id": it["id"],
                                   "item_name": it["name"], "qty": q, "unit": it["unit"], "note": po["number"],
                                   "vendor": po["vendor"], "unit_cost": l.get("unit_cost"), "photos": [],
                                   "received_at": utc_now(), "po_id": po["id"], "by": current_user_name()})
    po["status"] = "received"
    po["received_at"] = utc_now()
    po["discrepancies"] = discrepancies
    save_store(st)
    return jsonify({"ok": True, "order": po, "discrepancies": discrepancies})


@app.get("/api/orders/<oid>/text")
def orders_text(oid: str):
    st = load_store()
    po = _get_po(st, oid)
    if not po:
        return err("Order not found.", 404)
    cfg = load_config()
    v = find_by_id(cfg["vendors"], po.get("vendor_id") or "") or {}
    biz = cfg["business"].get("name") or st["settings"].get("truck_name") or "our truck"
    rows = []
    for l in po["lines"]:
        q = f"{l['cases']:g} cs ({l['qty']:g} {l['unit']})" if l.get("cases") else f"{l['qty']:g} {l['unit']}"
        rows.append(f"- {l['name']}: {q}")
    acct_no = f" (acct {v['account_no']})" if v.get("account_no") else ""
    body = (f"Hi{(' ' + v['rep']) if v.get('rep') else ''},\n\nOrder {po['number']} for {biz}{acct_no}:\n\n"
            + "\n".join(rows) + (f"\n\nNote: {po['note']}" if po.get("note") else "") + "\n\nThanks!")
    return jsonify({"ok": True, "subject": f"{biz} — order {po['number']}", "body": body, "email": v.get("email") or "",
                    "phone": v.get("phone") or ""})


@app.get("/api/orders/<oid>.csv")
def orders_csv(oid: str):
    po = _get_po(load_store(), oid)
    if not po:
        return err("Order not found.", 404)
    return _csv_response(po["lines"], ["name", "qty", "unit", "cases", "case_size", "unit_cost"], f"{po['number']}.csv")


# ---------- Input log (OSBW inputs: POS / invoices / purchases / transfers) ----------

@app.get("/api/inputs/log")
def inputs_log():
    t = request.args.get("type") or "all"
    st = load_store()
    rows = []
    if t in ("all", "pos"):
        for i in st["sales_imports"]:
            rows.append({"type": "pos", "at": i["imported_at"], "title": i.get("filename"), "id": i["id"],
                         "detail": f"{len(i['lines'])} lines · ${i.get('total_sales', 0):,.2f}", "by": i.get("imported_by"),
                         "example": i.get("example", False)})
    if t in ("all", "invoice", "purchase"):
        batches: dict = {}
        for r in st["receives"]:
            batches.setdefault(r.get("batch_id") or r["id"], []).append(r)
        for bid, rs in batches.items():
            rows.append({"type": "invoice" if any(r.get("invoice_no") or r.get("photos") for r in rs) else "purchase",
                         "at": rs[0]["received_at"], "id": bid,
                         "title": rs[0].get("vendor") or "Receive", "by": rs[0].get("by"),
                         "detail": ", ".join(f"{r['qty']:g} {r['unit']} {r['item_name']}" for r in rs[:4])
                         + ("…" if len(rs) > 4 else ""), "example": rs[0].get("example", False)})
        if t == "invoice":
            rows = [r for r in rows if r["type"] == "invoice"]
        if t == "purchase":
            rows = [r for r in rows if r["type"] == "purchase"]
    if t in ("all", "po"):
        for p in st.get("purchase_orders", []):
            rows.append({"type": "po", "at": p["created_at"], "id": p["id"], "title": f"{p['number']} · {p['vendor']}",
                         "detail": f"{p['status']} · {len(p['lines'])} lines", "by": p.get("created_by"),
                         "example": p.get("example", False)})
    if t in ("all", "transfer"):
        for x in st.get("transfers", []):
            rows.append({"type": "transfer", "at": x["at"], "id": x["id"],
                         "title": f"{'→ ' + (x.get('to_name') or '') if x.get('direction') == 'out' else '← ' + (x.get('from_name') or '')}",
                         "detail": ", ".join(f"{l['qty']:g} {l['unit']} {l['name']}" for l in x["lines"][:4]),
                         "by": x.get("by")})
    rows.sort(key=lambda r: r.get("at") or "", reverse=True)
    return jsonify({"ok": True, "rows": rows})


# ---------- Reports (OSBW reports: stock, history, money) ----------

def build_report(st: dict) -> dict:
    cfg = load_config()
    cats = {c["name"]: c for c in _ensure_categories(cfg, st)}
    items = active_items(st)
    by_cat: dict = {}
    by_zone: dict = {}
    for i in items:
        val = float(i.get("on_hand") or 0) * float(i.get("cost") or 0)
        c = by_cat.setdefault(i.get("category") or "Other", {"category": i.get("category") or "Other", "items": 0,
                                                              "value": 0.0, "no_cost": 0})
        c["items"] += 1
        c["value"] = round(c["value"] + val, 2)
        c["no_cost"] += 0 if i.get("cost") not in (None, "") else 1
        z = by_zone.setdefault(i["zone"], {"zone": i["zone"], "items": 0, "value": 0.0})
        z["items"] += 1
        z["value"] = round(z["value"] + val, 2)
    for c in by_cat.values():
        meta = cats.get(c["category"]) or {}
        c["gl_code"] = meta.get("gl_code") or ""
        c["kind"] = meta.get("kind") or ""
    history = [_history_row(s) for s in reversed(completed_sessions(st))]
    money = {"ready": False}
    sv = compute_sales_variance(st)
    if sv.get("ready"):
        items_by = {i["id"]: i for i in items}
        cogs, ideal, cat_cogs = 0.0, 0.0, {}
        for r in sv["rows"]:
            it = items_by.get(r["item_id"]) or {}
            cost = it.get("cost")
            if cost in (None, "") or r.get("counted_usage") is None:
                continue
            used = float(r["counted_usage"]) * float(cost)
            cogs += used
            ideal += float(r.get("theoretical") or 0) * float(cost)
            k = it.get("category") or "Other"
            cat_cogs[k] = round(cat_cogs.get(k, 0) + used, 2)
        sales = float(sv.get("sales") or 0)   # same window as the usage math (v1.3: timing-aware)
        money = {"ready": True, "period": sv["period"], "cogs": round(cogs, 2), "ideal_cogs": round(ideal, 2),
                 "sales": round(sales, 2),
                 "food_cost_pct": round(cogs / sales * 100, 1) if sales else None,
                 "ideal_pct": round(ideal / sales * 100, 1) if sales else None,
                 "variance_cost": sv.get("total_variance_cost"),
                 "by_category": [{"category": k, "cogs": v, "gl_code": (cats.get(k) or {}).get("gl_code") or "",
                                  "target_pct": (cats.get(k) or {}).get("target_pct"),
                                  "pct_of_sales": round(v / sales * 100, 1) if sales else None}
                                 for k, v in sorted(cat_cogs.items(), key=lambda kv: -kv[1])]}
    return {"stock": {"total_value": round(sum(c["value"] for c in by_cat.values()), 2),
                      "by_category": sorted(by_cat.values(), key=lambda c: -c["value"]),
                      "by_zone": [by_zone[z] for z in store_zones(st) if z in by_zone],
                      "item_count": len(items),
                      "missing_cost": sum(1 for i in items if i.get("cost") in (None, ""))},
            "history": history, "money": money}


@app.get("/api/reports/summary")
def reports_summary():
    return jsonify({"ok": True, **build_report(load_store())})


@app.get("/api/export/report.csv")
def export_report():
    rep = build_report(load_store())
    return _csv_response(rep["stock"]["by_category"], ["category", "gl_code", "kind", "items", "value", "no_cost"],
                         "osft-stock-by-category.csv")


@app.get("/api/export/count.csv")
def export_count():
    st = load_store()
    rows = [{"zone": i["zone"], "name": i["name"], "unit": i["unit"], "par": i.get("par"), "on_hand": i.get("on_hand"),
             "count": ""} for i in sorted(active_items(st), key=lambda x: (store_zones(st).index(x["zone"])
                                                                           if x["zone"] in store_zones(st) else 9,
                                                                           x["name"].lower()))]
    return _csv_response(rows, ["zone", "name", "unit", "par", "on_hand", "count"], "osft-count-sheet.csv")


@app.get("/api/export/variance.csv")
def export_variance():
    sv = compute_sales_variance(load_store())
    return _csv_response(sv.get("rows") or [], ["name", "unit", "start", "received", "end", "counted_usage",
                                                "theoretical", "variance", "variance_pct", "variance_cost"],
                         "osft-variance.csv")


@app.get("/api/export/reorder.csv")
def export_reorder():
    rep = build_reorder(load_store())
    rows = [{**l, "vendor": g["vendor"]} for g in rep["groups"] for l in g["lines"]]
    return _csv_response(rows, ["vendor", "name", "unit", "on_hand", "par", "order_qty", "case_size", "order_cases",
                                "cost", "ext_cost"], "osft-order-list.csv")


# ---------- Backups / restore / reset everything ----------

def backups_dir() -> Path:
    return DATA_DIR / "backups"


def write_backup(reason: str = "manual"):
    try:
        if not DATA_DIR.exists():
            return None
        bd = backups_dir()
        bd.mkdir(parents=True, exist_ok=True)
        name = f"osft-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{_re.sub(r'[^a-z0-9-]', '', reason.lower())[:20]}-{uuid.uuid4().hex[:4]}.zip"
        path = bd / name
        with _zipfile.ZipFile(path, "w", _zipfile.ZIP_DEFLATED) as z:
            for p in DATA_DIR.rglob("*.json"):
                if bd in p.parents:
                    continue
                if p == config_path():
                    c = _read_json(p) or {}
                    if isinstance(c.get("ai"), dict):
                        c["ai"] = {k: v for k, v in c["ai"].items() if k != "api_key"}  # never put the AI key in a backup
                    z.writestr(p.relative_to(DATA_DIR).as_posix(), json.dumps(c, indent=2))
                    continue
                z.write(p, p.relative_to(DATA_DIR).as_posix())
        olds = sorted(bd.glob("osft-*.zip"))
        for o in olds[:-30]:
            o.unlink(missing_ok=True)
        return path
    except OSError:
        return None


@app.get("/api/backups")
def backups_list():
    bd = backups_dir()
    rows = [{"name": p.name, "size": p.stat().st_size,
             "at": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat()}
            for p in sorted(bd.glob("osft-*.zip"), reverse=True)] if bd.exists() else []
    return jsonify({"ok": True, "backups": rows})


@app.post("/api/backups")
def backups_create():
    p = write_backup("manual")
    if not p:
        return err("Couldn't write a backup.", 500)
    return jsonify({"ok": True, "name": p.name}), 201


@app.get("/api/backup")
def backup_download():
    p = write_backup("download")
    if not p:
        return err("Couldn't write a backup.", 500)
    return send_from_directory(backups_dir(), p.name, as_attachment=True)


def _safe_member(name: str) -> bool:
    return (name.endswith(".json") and not name.startswith("/") and ".." not in Path(name).parts
            and _re.match(r"^[A-Za-z0-9_./-]+$", name) is not None)


@app.post("/api/restore")
def restore():
    f = request.files.get("file")
    if f is None or not f.filename:
        return err("Choose a backup file (.zip or store.json).")
    raw = f.read()
    write_backup("before-restore")
    if raw[:2] == b"PK":
        try:
            z = _zipfile.ZipFile(_io.BytesIO(raw))
        except _zipfile.BadZipFile:
            return err("That zip is damaged.")
        names = [n for n in z.namelist() if not n.endswith("/")]
        if not names or any(not _safe_member(n) for n in names):
            return err("That doesn't look like an OSFT backup.")
        for n in names:
            try:
                json.loads(z.read(n).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return err(f"{n} in the backup is not valid JSON.")
        keep_key = get_ai_cfg().get("api_key")
        for n in names:
            dest = DATA_DIR / n
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(z.read(n))
        if keep_key:
            c = load_config()
            if isinstance(c.get("ai"), dict) and not c["ai"].get("api_key"):
                c["ai"]["api_key"] = keep_key
                save_config(c)
        return jsonify({"ok": True, "restored": names})
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError):
        return err("That file isn't a backup (.zip) or a store.json.")
    if not isinstance(data, dict) or "items" not in data:
        return err("That JSON isn't an OSFT store.")
    save_store(data)
    return jsonify({"ok": True, "restored": ["store.json"]})


@app.post("/api/reset/all")
def reset_all():
    if str(_body().get("confirm") or "") != "RESET":
        return err("Type RESET to confirm.")
    p = write_backup("reset-all")
    cfg = load_config()
    for t in cfg["trucks"]:
        tp = truck_store_path(t["id"])
        if tp.exists():
            tp.unlink()
    cp = config_path()
    if cp.exists():
        cp.unlink()
    _write_json(config_path(), default_config())
    _write_json(STORE_PATH, empty_store())
    session.clear()
    return jsonify({"ok": True, "backup": p.name if p else None})


# ---------- Onboarding (OSBW setup phases) ----------

# Same order as OSBW setup.html: Welcome (incl. optional AI) → Step 1 Your operation → Pass 1 map
# (sections ≈ OSBW bars/stations, walk, review & confirm) → Pass 2 first live count → done.
# OSBW has no login step in setup; OSFT offers the optional PIN lock last, just before home base.
ONBOARDING_PHASES = ["welcome", "business", "sections", "walk", "reconcile", "review", "first_count", "account", "done"]


def _onboarding_payload(cfg: dict) -> dict:
    st = load_store()
    ob = cfg["onboarding"]
    return {"onboarding": ob, "phases": ONBOARDING_PHASES, "business": cfg["business"],
            "has_admin": acct.auth_enabled(cfg.get("people", [])), "item_count": len(active_items(st)),
            "zones": store_zones(st), "auth": _auth_status(cfg)}


@app.get("/api/onboarding")
def onboarding_get():
    return jsonify({"ok": True, **_onboarding_payload(load_config())})


@app.put("/api/onboarding")
def onboarding_put():
    cfg = load_config()
    if cfg["onboarding"].get("completed") and acct.auth_enabled(cfg.get("people", [])) and not current_user(cfg):
        return err("Log in first.", 401)
    d = _body()
    ph = d.get("phase")
    if ph not in ONBOARDING_PHASES:
        return err("Unknown setup step.")
    ob = cfg["onboarding"]
    ob["phase"] = ph
    if ph == "done":
        ob["completed"] = True
        ob["completed_at"] = utc_now()
        st = load_store()
        st["settings"]["setup_complete"] = True
        if cfg["business"].get("name") and not st["settings"].get("truck_name"):
            st["settings"]["truck_name"] = cfg["business"]["name"]
        save_store(st)
    if d.get("skipped"):
        ob.setdefault("skipped", []).append(d["skipped"])
    save_config(cfg)
    return jsonify({"ok": True, **_onboarding_payload(cfg)})



# ---------- v1.2: product invoices during setup + reconcile ----------
SETUP_INV_EXT = PHOTO_EXT | {".csv", ".txt"}


def _setup_invoices(st: dict) -> list:
    return st["settings"].setdefault("setup_invoices", [])


def _read_setup_file(path: Path, ai_on: bool) -> dict:
    """One uploaded invoice file -> {lines, source, note}. AI reads photos/PDFs; without AI we read text only."""
    mime, ext = _mime_of(path), path.suffix.lower()
    if ai_on and ext not in (".csv", ".txt"):
        try:
            res = ai_mod.extract_invoice(get_ai_cfg(), [(path.read_bytes(), mime)])
            return {"lines": res["lines"], "vendor": res.get("vendor"), "invoice_no": res.get("invoice_no"),
                    "date": res.get("date"), "source": "ai", "note": None}
        except ai_mod.AIError as e:
            if ext != ".pdf":
                return {"lines": [], "source": "ai", "note": str(e)}
    if ext in (".csv", ".txt"):
        text = path.read_bytes().decode("utf-8", "ignore")
        src = "csv" if ext == ".csv" else "text"
    elif ext == ".pdf":
        text, src = ai_mod.pdf_text(path.read_bytes()), "pdf-text"
        if not text.strip():
            return {"lines": [], "source": src, "note": "This PDF is a scan (no text layer). Reading scans and photos needs AI — turn it on in Settings → AI, or type the lines below."}
    else:
        return {"lines": [], "source": "photo", "note": "Reading invoice photos needs AI. Turn it on in Settings → AI, or type the lines below."}
    lines, unread = recon.parse_text(text)
    note = None
    if unread:
        note = f"Read {len(lines)} line(s); {unread} line(s) couldn't be read without AI — check the list or type them in."
    if not lines:
        note = "Couldn't find product lines in this file without AI. Type the lines below (e.g. “2 cs Ground beef 4.89”)."
    return {"lines": lines, "source": src, "note": note}


@app.get("/api/setup/invoices")
def setup_invoices_list():
    st = load_store()
    return jsonify({"ok": True, "invoices": _setup_invoices(st), "ai_enabled": bool(get_ai_cfg().get("enabled"))})


@app.post("/api/setup/invoices")
def setup_invoices_upload():
    """Upload product invoices in the walk (same spot as the spoken products). Lines are a draft — no products change."""
    files = [f for f in (request.files.getlist("files") or request.files.getlist("file")) if f and f.filename]
    if not files:
        return err("Choose invoice files (PDF, photo, or CSV).")
    if len(files) > 12:
        return err("Up to 12 files at a time.")
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in SETUP_INV_EXT:
            return err(f"File type {ext or '?'} not allowed. Use: {', '.join(sorted(SETUP_INV_EXT))}.")
    ai_on = bool(get_ai_cfg().get("enabled"))
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    added = []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        name = f"inv-{uuid.uuid4().hex[:12]}{ext}"
        f.save(PHOTOS_DIR / name)
        r = _read_setup_file(PHOTOS_DIR / name, ai_on)
        added.append({"id": uuid.uuid4().hex[:10], "file": name, "filename": Path(f.filename).name[:120],
                      "vendor": r.get("vendor"), "invoice_no": r.get("invoice_no"), "date": r.get("date"),
                      "source": r["source"], "note": r.get("note"), "lines": r["lines"], "added_at": utc_now()})
    st = load_store()
    _setup_invoices(st).extend(added)
    save_store(st)
    return jsonify({"ok": True, "added": added, "invoices": _setup_invoices(st), "ai_enabled": ai_on}), 201


@app.post("/api/setup/invoices/text")
def setup_invoices_text():
    d = _body()
    text = str(d.get("text") or "")
    if not text.strip():
        return err("Type or paste the invoice lines first (one product per line).")
    lines, unread = recon.parse_text(text)
    if not lines:
        return err("Couldn't read any product lines. Try “2 cs Ground beef 4.89” — qty, unit, product, price.")
    inv = {"id": uuid.uuid4().hex[:10], "file": None, "filename": None, "vendor": str(d.get("vendor") or "").strip()[:80] or None,
           "invoice_no": None, "date": None, "source": "typed",
           "note": f"{unread} line(s) couldn't be read." if unread else None, "lines": lines, "added_at": utc_now()}
    st = load_store()
    _setup_invoices(st).append(inv)
    save_store(st)
    return jsonify({"ok": True, "added": [inv], "invoices": _setup_invoices(st)}), 201


@app.delete("/api/setup/invoices/<iid>")
def setup_invoices_delete(iid: str):
    st = load_store()
    inv = _setup_invoices(st)
    keep = [i for i in inv if i["id"] != iid]
    if len(keep) == len(inv):
        return err("Invoice not found.", 404)
    st["settings"]["setup_invoices"] = keep
    save_store(st)
    return jsonify({"ok": True, "invoices": keep})


EDIT_FIELDS = ("name", "zone", "on_hand", "unit", "pack", "cost", "vendor")


def _pending(st: dict) -> dict:
    p = st["settings"].setdefault("setup_pending", {})
    for k, v in (("edits", {}), ("deleted", []), ("merges", {}), ("links", {}), ("added", [])):
        p.setdefault(k, v)
    return p


def _apply_edit(it: dict, e: dict) -> None:
    for k, v in e.items():
        if k == "vendor":
            it["vendor_name"] = v
        else:
            it[k] = v
        it.setdefault("_edited", [])
        if k not in it["_edited"]:
            it["_edited"].append(k)


def _virtual_items(st: dict) -> list:
    """Products as they WILL be after Confirm: real ones with pending edits/deletes/merges, plus pending adds."""
    p = _pending(st)
    gone = set(p["deleted"]) | set(p["merges"])
    out = []
    for i in active_items(st):
        if i["id"] in gone:
            continue
        it = dict(i)
        _apply_edit(it, p["edits"].get(i["id"], {}))
        out.append(it)
    for a in p["added"]:
        it = {"id": a["id"], "name": a["name"], "zone": a["zone"], "unit": a.get("unit") or "ea", "on_hand": a.get("on_hand"),
              "cost": None, "pack": "", "aliases": [], "_new": True}
        _apply_edit(it, p["edits"].get(a["id"], {}))
        out.append(it)
    by = {i["id"]: i for i in out}
    real = {i["id"]: i for i in active_items(st)}
    for src, dst in p["merges"].items():
        a, b = real.get(src), by.get(dst)
        if a and b:
            e = {**a, **{k: v for k, v in p["edits"].get(src, {}).items() if k != "vendor"}}
            if e.get("on_hand") is not None:
                b["on_hand"] = float(b.get("on_hand") or 0) + float(e["on_hand"])
            b["merged_from"] = b.get("merged_from", []) + [e["name"]]
    return out


def _reconcile_report(st: dict) -> dict:
    p = _pending(st)
    rep = recon.reconcile(_virtual_items(st), store_sections(st), _setup_invoices(st),
                          st["settings"].get("setup_not_stocked") or [], starter_catalog.CATALOG, links=p["links"])
    rep["pending"] = {"edits": len(p["edits"]), "deleted": len(p["deleted"]), "merges": len(p["merges"]),
                      "links": len(p["links"]), "added": len(p["added"])}
    rep["pending"]["total"] = sum(rep["pending"].values())
    rep["deleted"] = [{"id": i["id"], "name": i["name"]} for i in active_items(st) if i["id"] in p["deleted"]]
    return rep


def _num_or_none(v, label):
    if v in (None, ""):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if f < 0:
        raise ValueError(f"{label} can't be negative.")
    return f


@app.post("/api/setup/reconcile/pending")
def setup_reconcile_pending():
    """Edit the Reconcile screen without saving products: edit / delete / restore / merge / link / unlink / add / reset."""
    d = _body()
    op = d.get("op")
    st = load_store()
    p = _pending(st)
    virt = {i["id"]: i for i in _virtual_items(st)}
    real = {i["id"] for i in active_items(st)}
    keys = {x["key"] for x in store_sections(st)}
    iid = str(d.get("id") or "")
    try:
        if op == "edit":
            if iid not in virt:
                return err("That product isn't on the map anymore — re-run reconciliation.", 404)
            ch = d.get("changes") or {}
            e = {}
            for k, v in ch.items():
                if k not in EDIT_FIELDS:
                    continue
                if k == "name":
                    v = str(v or "").strip()[:120]
                    if not v:
                        return err("Name can't be empty.")
                elif k == "zone":
                    if v not in keys:
                        return err("Pick a section.")
                elif k == "on_hand":
                    v = _num_or_none(v, "Count")
                elif k == "cost":
                    v = _num_or_none(v, "Cost")
                else:
                    v = str(v or "").strip()[:80]
                    if k == "unit" and not v:
                        return err("Unit can't be empty.")
                e[k] = v
            p["edits"].setdefault(iid, {}).update(e)
        elif op == "delete":
            if iid not in virt:
                return err("That product isn't on the map anymore.", 404)
            if iid in real:
                p["deleted"].append(iid)
            else:
                p["added"] = [a for a in p["added"] if a["id"] != iid]
                p["edits"].pop(iid, None)
            for k, v in list(p["links"].items()):
                if v == iid:
                    p["links"][k] = ""
        elif op == "restore":
            p["deleted"] = [x for x in p["deleted"] if x != iid]
            p["merges"].pop(iid, None)
        elif op == "merge":
            into = str(d.get("into") or "")
            if iid == into or iid not in virt or into not in virt:
                return err("Pick two different products to merge.")
            if iid not in real:
                return err("Merge a new product by deleting it instead.")
            p["merges"][iid] = into
            for k, v in list(p["links"].items()):
                if v == iid:
                    p["links"][k] = into
        elif op == "link":
            key, into = str(d.get("key") or ""), str(d.get("item_id") or "")
            if into not in virt:
                return err("Pick the product this invoice line belongs to.")
            p["links"][key] = into
        elif op == "unlink":
            ks = d.get("keys") or ([d["key"]] if d.get("key") else [])
            if not ks:
                return err("Nothing to unlink.")
            for k in ks:
                p["links"][str(k)] = ""
        elif op == "add":
            name = str(d.get("name") or "").strip()[:120]
            if not name:
                return err("Name the product.")
            if d.get("zone") not in keys:
                return err("Pick a section.")
            p["added"].append({"id": "new-" + uuid.uuid4().hex[:10], "name": name, "zone": d["zone"],
                               "unit": str(d.get("unit") or "ea").strip()[:20] or "ea",
                               "on_hand": _num_or_none(d.get("on_hand"), "Count")})
        elif op == "reset":
            st["settings"]["setup_pending"] = {}
            p = _pending(st)
        else:
            return err("Unknown edit.")
    except ValueError as e:
        return err(str(e))
    save_store(st)
    return jsonify({"ok": True, "saved": False, **_reconcile_report(st)})


def _materialize_pending(st: dict, cfg: dict) -> dict:
    """On Confirm: write pending edits into real products. Returns {pending_id: real_id} for added ones."""
    p = _pending(st)
    real = {i["id"]: i for i in active_items(st)}
    idmap = {}
    for a in p["added"]:
        it = _new_item({"name": a["name"], "zone": a["zone"], "unit": a.get("unit"), "on_hand": a.get("on_hand"),
                        "category": "Other"})
        it["source"] = "setup-reconcile"
        st["items"].append(it)
        real[it["id"]] = it
        idmap[a["id"]] = it["id"]
    for src, dst in p["merges"].items():
        a, b = real.get(src), real.get(idmap.get(dst, dst))
        if a and b:
            ea = p["edits"].get(src, {})
            oh = ea.get("on_hand", a.get("on_hand"))
            if oh is not None:
                b["on_hand"] = float(b.get("on_hand") or 0) + float(oh)
            for al in [ea.get("name", a["name"])] + list(a.get("aliases") or []):
                if al.lower() != b["name"].lower() and al not in b.setdefault("aliases", []):
                    b["aliases"].append(al)
            a["archived"] = True
            a["merged_into"] = b["id"]
    for iid in p["deleted"]:
        if iid in real:
            real[iid]["archived"] = True
    for iid, e in p["edits"].items():
        it = real.get(idmap.get(iid, iid))
        if not it or it.get("archived"):
            continue
        for k, v in e.items():
            if k == "vendor":
                v = (v or "").strip()
                if v:
                    vs = cfg.setdefault("vendors", [])
                    ven = next((x for x in vs if x.get("name", "").lower() == v.lower()), None)
                    if not ven:
                        ven = {"id": str(uuid.uuid4()), **{f: "" for f in VENDOR_FIELDS}, "name": v[:80], "created_at": utc_now()}
                        vs.append(ven)
                    it["vendor_id"] = ven["id"]
                else:
                    it["vendor_id"] = None
            elif k == "on_hand":
                it["on_hand"] = float(v or 0)
            else:
                it[k] = v
        it["_locked"] = list(e.keys())
        it["updated_at"] = utc_now()
    p["links"] = {k: idmap.get(v, v) for k, v in p["links"].items()}
    return idmap


@app.get("/api/setup/reconcile")
def setup_reconcile():
    """Proposal only: what was spoken per section, merged with invoice lines. Nothing is saved."""
    return jsonify({"ok": True, "saved": False, **_reconcile_report(load_store())})


@app.post("/api/setup/reconcile/apply")
def setup_reconcile_apply():
    """Owner confirmed: carry invoice details onto matched products and act on each unplaced invoice product."""
    d = _body()
    st = load_store()
    rep = _reconcile_report(st)
    unplaced = {g["key"]: g for g in rep["unplaced"]}
    carry = d.get("carry", True)  # True = all matched, or list of item ids
    acts = d.get("instructions") or []
    if not isinstance(acts, list):
        return err("Instructions must be a list.")
    secs = store_sections(st)
    keys = {x["key"] for x in secs}
    for a in acts:
        k = a.get("key")
        if k not in unplaced:
            return err("That invoice product isn't waiting to be placed anymore — re-run reconciliation.", 409)
        act = a.get("action")
        if act not in ("section", "new_section", "same_as", "commissary", "not_stocked", "skip"):
            return err(f"Pick what to do with “{unplaced[k]['name']}”.")
        if act == "section" and a.get("section") not in keys:
            return err(f"Pick a section for “{unplaced[k]['name']}”.")
        if act == "new_section" and not str(a.get("section_name") or "").strip():
            return err(f"Name the new section for “{unplaced[k]['name']}”.")
        if act == "same_as" and str(a.get("item_id") or "") not in {i["id"] for i in _virtual_items(st)}:
            return err(f"Pick the product “{unplaced[k]['name']}” is the same as.")
    cfg = load_config()
    vendors = cfg.setdefault("vendors", [])
    made_vendor = []
    idmap = _materialize_pending(st, cfg)
    links = _pending(st)["links"]
    st["settings"]["setup_pending"] = {}
    rep = recon.reconcile(active_items(st), store_sections(st), _setup_invoices(st),
                          st["settings"].get("setup_not_stocked") or [], starter_catalog.CATALOG, links=links)
    secs = store_sections(st)

    def vendor_id(names):
        if not names:
            return None
        n = names[0]
        v = next((x for x in vendors if x.get("name", "").lower() == n.lower()), None)
        if not v:
            v = {"id": str(uuid.uuid4()), **{f: "" for f in VENDOR_FIELDS}, "name": n[:80], "created_at": utc_now()}
            vendors.append(v)
            made_vendor.append(n)
        return v["id"]

    def carry_onto(it, g):
        lk = it.get("_locked") or []
        if g.get("unit_cost") is not None and "cost" not in lk:
            it["cost"] = g["unit_cost"]
        if g.get("pack") and not it.get("pack") and "pack" not in lk:
            it["pack"] = g["pack"]
        if g.get("unit") and "unit" not in lk and (it.get("unit") in (None, "", "ea")) and voice.canon_unit(g["unit"]) != "case":
            it["unit"] = voice.canon_unit(g["unit"]) or g["unit"]
        vid = vendor_id(g.get("vendors"))
        if vid and not it.get("vendor_id") and "vendor" not in lk:
            it["vendor_id"] = vid
        for sp in g.get("spellings") or []:
            if sp.lower() != it["name"].lower() and sp not in it.setdefault("aliases", []):
                it["aliases"].append(sp)
        it["updated_at"] = utc_now()

    groups = {g["key"]: g for g in recon.dedupe(_setup_invoices(st))}
    updated = 0
    for s in rep["sections"]:
        for row in s["items"]:
            if not row["from_invoice"] or (carry is not True and row["id"] not in (carry or [])):
                continue
            it = find_item(st, row["id"])
            for gk in row["invoice_keys"]:
                g = groups.get(gk)
                if it and g:
                    carry_onto(it, g)
            updated += bool(it)
    created, ns, skipped = [], st["settings"].setdefault("setup_not_stocked", []), 0
    for a in acts:
        g, act = unplaced[a["key"]], a["action"]
        if act == "skip":
            skipped += 1
            continue
        if act == "not_stocked":
            if g["key"] not in ns:
                ns.append(g["key"])
            continue
        if act == "same_as":
            it = find_item(st, idmap.get(a["item_id"], a["item_id"]))
            carry_onto(it, g)
            updated += 1
            continue
        if act == "commissary":
            sec = next((x for x in secs if x["key"] == "commissary"), None)
            if not sec:
                sec = {"key": "commissary", "name": "Commissary (not on truck)"}
                secs.append(sec)
            zone = sec["key"]
        elif act == "new_section":
            nm = str(a["section_name"]).strip()[:40]
            sec = next((x for x in secs if x["name"].lower() == nm.lower()), None)
            if not sec:
                key = sections_mod.slug(nm) or "section"
                base, n = key, 2
                while key in {x["key"] for x in secs}:
                    key, n = f"{base}-{n}", n + 1
                sec = {"key": key, "name": nm}
                secs.append(sec)
            zone = sec["key"]
        else:
            zone = a["section"]
        name = str(a.get("name") or g["name"]).strip()[:120] or g["name"]
        it = _new_item({"name": name, "zone": zone, "category": "Other"})
        it["source"] = "setup-invoice"
        if act == "commissary":
            it["notes"] = "Commissary only — not stocked on the truck."
        carry_onto(it, g)
        for k in ("unit", "pack", "cost", "on_hand"):
            if a.get(k) not in (None, ""):
                try:
                    it[k] = float(a[k]) if k in ("cost", "on_hand") else str(a[k])[:40]
                except (TypeError, ValueError):
                    pass
        if str(a.get("vendor") or "").strip():
            it["vendor_id"] = vendor_id([str(a["vendor"]).strip()])
        st["items"].append(it)
        created.append({"id": it["id"], "name": it["name"], "zone": zone})
    for it in st["items"]:
        it.pop("_locked", None)
    st["settings"]["sections"] = secs
    st["settings"]["setup_reconciled_at"] = utc_now()
    save_store(st)
    if made_vendor:
        save_config(cfg)
    return jsonify({"ok": True, "saved": True, "updated": updated, "created": created, "skipped": skipped,
                    "not_stocked": len(ns), "vendors_created": made_vendor, "sections": secs,
                    **_reconcile_report(load_store())})


@app.post("/api/onboarding/first-count")
def onboarding_first_count():
    """Use on-hand quantities captured during setup as the first completed count (OSBW first_count)."""
    st = load_store()
    items = active_items(st)
    if not items:
        return err("Add some products first.")
    sess = {"id": str(uuid.uuid4()), "status": "completed", "started_at": utc_now(), "completed_at": utc_now(),
            "counts": {i["id"]: float(i.get("on_hand") or 0) for i in items}, "source": "setup",
            "counted_by": current_user_name()}
    st["count_sessions"].append(sess)
    save_store(st)
    return jsonify({"ok": True, "session": sess})


# ---------- Sample taco truck ----------

DEMO_VENDORS = [
    {"name": "Example Meat Co.", "rep": "Sam (EXAMPLE)", "phone": "555-0101", "email": "orders@example.com",
     "account_no": "EX-1042", "cutoff": "2 pm day before", "delivery_days": "Tue, Fri", "lead_days": "1",
     "terms": "Net 14", "order_method": "email", "notes": "EXAMPLE vendor — replace with yours"},
    {"name": "Example Produce", "rep": "Lupe (EXAMPLE)", "phone": "555-0102", "email": "produce@example.com",
     "account_no": "EX-2201", "cutoff": "6 pm", "delivery_days": "Mon–Sat", "lead_days": "1", "terms": "COD",
     "order_method": "text", "notes": "EXAMPLE vendor"},
    {"name": "Example Restaurant Supply", "rep": "", "phone": "555-0103", "email": "", "account_no": "",
     "cutoff": "", "delivery_days": "Pickup", "lead_days": "0", "terms": "Card", "order_method": "pickup",
     "notes": "EXAMPLE — cash & carry"},
]
DEMO_ITEM_EXTRA = {
    "Ground beef": ("Example Meat Co.", 10, "10 lb chub", "Carne molida"),
    "Chicken thigh": ("Example Meat Co.", 40, "40 lb case", "Muslo de pollo"),
    "Frozen carnitas": ("Example Meat Co.", 10, "2 × 5 lb", "Carnitas congeladas"),
    "Shredded cheese": ("Example Restaurant Supply", 20, "4 × 5 lb", "Queso rallado"),
    "Flour tortillas": ("Example Restaurant Supply", 12, "12 packs", "Tortillas de harina"),
    "Corn tortillas": ("Example Restaurant Supply", 12, "12 packs", "Tortillas de maíz"),
    "Pico de gallo": ("Example Produce", None, "", "Pico de gallo"),
    "Lime wedges": ("Example Produce", None, "", "Limones"),
    "Salsa verde": ("Example Produce", None, "", "Salsa verde"),
    "Black beans (can)": ("Example Restaurant Supply", 6, "6 × #10 can", "Frijoles negros"),
    "Hot sauce bottles": ("Example Restaurant Supply", 12, "12 bottles", "Salsa picante"),
    "Ice": ("Example Restaurant Supply", None, "", "Hielo"),
}


def seed_demo_v1(store: dict, items: list) -> None:
    cfg = load_config()
    vend = {v["name"]: v for v in cfg["vendors"]}
    for dv in DEMO_VENDORS:
        if dv["name"] not in vend:
            v = {"id": str(uuid.uuid4()), **dv, "example": True, "created_at": utc_now()}
            cfg["vendors"].append(v)
            vend[dv["name"]] = v
    for it in items:
        ex = DEMO_ITEM_EXTRA.get(it["name"])
        if ex:
            it["vendor_id"] = vend[ex[0]]["id"]
            it["case_size"] = ex[1]
            it["pack"] = ex[2]
            it["name_es"] = ex[3]
            it["aliases"] = [ex[3].lower()]
    if not cfg["pos_accounts"]:
        cfg["pos_accounts"].append({"id": str(uuid.uuid4()), "label": "Main register (EXAMPLE)",
                                    "provider": "generic_csv", "location": "Truck window", "account_ref": "",
                                    "notes": "EXAMPLE", "mapping": {}, "default": True, "truck_id": "main",
                                    "example": True})
    if not cfg["staff_board"]:
        cfg["staff_board"].append({"id": str(uuid.uuid4()), "text": "EXAMPLE note: count the cooler before service, "
                                   "and log anything tossed.", "author": "Sample", "truck_id": None, "pinned": True,
                                   "created_at": utc_now()})
    _ensure_categories(cfg, store)
    if not cfg["business"].get("name"):
        cfg["business"]["name"] = "Taco Libre (Sample)"
    cfg["onboarding"].update(phase="done", completed=True, completed_at=utc_now())
    save_config(cfg)
    beef = next((i for i in items if i["name"] == "Ground beef"), None)
    if beef:
        po = {"id": str(uuid.uuid4()), "number": "PO-1001", "vendor_id": vend["Example Meat Co."]["id"],
              "vendor": "Example Meat Co.", "status": "sent",
              "lines": [{"item_id": beef["id"], "name": beef["name"], "qty": 20.0, "unit": "lb", "cases": 2,
                         "case_size": 10, "unit_cost": beef.get("cost")}], "note": "EXAMPLE order",
              "created_at": utc_now(), "sent_at": utc_now(), "received_at": None, "example": True,
              "created_by": "Sample"}
        _po_totals(po)
        store["purchase_orders"] = [po]
    else:
        store["purchase_orders"] = []
    store["transfers"] = []


@app.post("/api/onboarding/sample")
def onboarding_sample():
    """“Load sample taco truck” from the welcome screen: seed example data and finish setup."""
    resp = seed_demo()
    cfg = load_config()
    cfg["onboarding"].update(phase="done", completed=True, completed_at=utc_now(), sample=True)
    save_config(cfg)
    return resp




# ================= v1.1: sections, AI connection, invoice upload, shelf building =================

def get_ai_cfg() -> dict:
    cfg = load_config()
    if "ai" not in cfg:
        old = (_read_json(STORE_PATH) or {}).get("settings", {}).get("ai_reader") if STORE_PATH.exists() else None
        ai = {}
        if isinstance(old, dict) and old.get("api_key"):
            ep = str(old.get("endpoint") or "https://api.openai.com/v1").replace("/chat/completions", "")
            ai = {"provider": "custom", "base_url": ep, "model": old.get("model") or "gpt-4o-mini",
                  "api_key": old["api_key"], "enabled": bool(old.get("enabled"))}
        return ai
    return dict(cfg.get("ai") or {})


def _ai_save(data: dict):
    new, e = ai_mod.update(get_ai_cfg(), data)
    if e:
        return err(e)
    cfg = load_config()
    cfg["ai"] = new
    save_config(cfg)
    c = ai_mod.public(new)
    return jsonify({"ok": True, "ai": c, "ai_reader": {"enabled": c["enabled"], "endpoint": c["base_url"],
                                                        "model": c["model"], "has_key": c["has_key"]}})


def _mime_of(p: Path) -> str:
    ext = p.suffix.lower()
    return {".pdf": "application/pdf", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
            ".heic": "image/heic", ".heif": "image/heif"}.get(ext, "image/jpeg")


def _ai_call(fn):
    try:
        return fn()
    except ai_mod.AIOff as e:
        return err(str(e), 409)
    except ai_mod.AIError as e:
        return err(str(e), 502)


# ---------- Library + Help tutor (Settings › Library) ----------

LIBRARY_DIR = BASE_DIR / "library"


def _ai_on() -> tuple[bool, str, str]:
    c = get_ai_cfg()
    ok = bool(c.get("enabled") and c.get("base_url") and c.get("model"))
    label = ai_mod.PRESETS.get(c.get("provider") or "", {}).get("label", "") if ok else ""
    return ok, label, (c.get("provider") or "") if ok else ""


def library_snapshot() -> dict:
    """A short, read-only summary of the active truck for the Help tutor. No PINs, keys or contact details."""
    st = load_store()
    cfg = load_config()
    items = active_items(st)
    below = sorted((i for i in items if float(i.get("on_hand") or 0) < float(i.get("par") or 0)),
                   key=lambda i: float(i.get("on_hand") or 0) - float(i.get("par") or 0))
    done = completed_sessions(st)
    last = _history_row(done[-1]) if done else None
    full = [s for s in done if _is_full(s)]
    sales = st.get("sales_imports", []) or []
    return {
        "truck": st["settings"].get("truck_name") or "", "version": VERSION,
        "language": st["settings"].get("locale") or "en",
        "sections": [s["name"] for s in store_sections(st)],
        "products": len(items), "products_without_cost": sum(1 for i in items if not i.get("cost")),
        "products_without_par": sum(1 for i in items if not i.get("par")),
        "below_par": len(below), "below_par_examples": [i["name"] for i in below[:8]],
        "completed_counts": len(done), "full_counts": len(full),
        "count_in_progress": any(s.get("status") == "in_progress" for s in st["count_sessions"]),
        "last_count": {k: last[k] for k in ("business_date", "type_name", "full", "lines", "by")} if last else None,
        "receives": len(st.get("receives", [])), "menu_items": len(st.get("menu_items", []) or []),
        "sales_imports": len(sales), "last_sales_import": max((s.get("created_at") or "" for s in sales), default="")[:10],
        "stop_types": [s.get("name") for s in st.get("stop_types", []) or []][:10],
        "open_orders": sum(1 for p in st.get("purchase_orders", []) or [] if p.get("status") != "received"),
        "vendors": len(cfg.get("vendors", [])), "trucks": len(cfg.get("trucks", [])),
        "logins_on": acct.auth_enabled(cfg.get("people", [])),
        "people": sum(1 for p in cfg.get("people", []) if p.get("active", True)),
        "ai_on": _ai_on()[0],
    }


@app.get("/api/library/<lang>")
def library_get(lang: str):
    on, label, provider = _ai_on()
    return jsonify({"ok": True, "manual": library_mod.load(LIBRARY_DIR, lang),
                    "ai": {"on": on, "label": label, "provider": provider}})


@app.post("/api/library/ask")
def library_ask():
    d = _body()
    q = str(d.get("question") or "").strip()
    if not q:
        return err("Type a question first.")
    lang = d.get("lang") if d.get("lang") in library_mod.LANGS else "en"
    if not _ai_on()[0]:
        return jsonify({"ok": True, "mode": "off"})
    manual = library_mod.load(LIBRARY_DIR, lang)
    refs = [r for r in (d.get("refs") or []) if isinstance(r, str)][:6] or ["welcome"]
    pages = library_mod.topics_for(manual, refs)
    prompt = library_mod.build_prompt(lang, q, pages, library_snapshot(), d.get("history") or [],
                                      str(d.get("view") or "")[:40])
    try:
        answer = ai_mod.chat(get_ai_cfg(), prompt, want_json=False, max_tokens=900, timeout=60)
    except ai_mod.AIOff:
        return jsonify({"ok": True, "mode": "off"})
    except ai_mod.AIError as e:
        return err(str(e), 502)
    sources = [{k: p[k] for k in ("chapter", "chapter_title", "topic", "title")} for p in pages]
    return jsonify({"ok": True, "mode": "ai", "answer": answer.strip(), "sources": sources})


@app.get("/api/ai")
def ai_status():
    presets = [{"key": k, **v} for k, v in ai_mod.PRESETS.items()]
    return jsonify({"ok": True, "ai": ai_mod.public(get_ai_cfg()), "presets": presets})


@app.put("/api/ai/settings")
def ai_settings_v11():
    return _ai_save(_body())


@app.post("/api/ai/test")
def ai_test():
    d = _body()
    cfg, e = ai_mod.update(get_ai_cfg(), {k: v for k, v in d.items() if k != "enabled"})
    if e:
        return err(e)

    def run():
        reply = ai_mod.test(cfg)
        full = load_config()
        stamp = {"at": utc_now(), "ok": True}
        full.setdefault("ai", get_ai_cfg())["last_test"] = stamp
        save_config(full)
        return jsonify({"ok": True, "reply": reply, "last_test": stamp})
    return _ai_call(run)


def _match_name(name: str, items: list):
    m = voice.match_entry(name, items, None)
    if m["item"] is not None and m["status"] == "matched":
        return {"status": "matched", "item_id": m["item"]["id"], "item_name": m["item"]["name"]}
    if m["item"] is not None and m["status"] == "ambiguous":
        return {"status": "ambiguous", "item_id": m["item"]["id"], "item_name": m["item"]["name"]}
    return {"status": "new", "item_id": None, "item_name": None}


@app.post("/api/invoice/upload")
def invoice_upload():
    files = request.files.getlist("files") or request.files.getlist("file")
    files = [f for f in files if f and f.filename]
    if not files:
        return err("Choose an invoice photo or PDF.")
    if len(files) > 6:
        return err("Up to 6 files per invoice.")
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in PHOTO_EXT:
            return err(f"File type {ext or '?'} not allowed. Use: {', '.join(sorted(PHOTO_EXT))}.")
        name = f"inv-{uuid.uuid4().hex[:12]}{ext}"
        f.save(PHOTOS_DIR / name)
        out.append({"name": name, "url": f"/photos/{name}", "type": _mime_of(Path(name))})
    return jsonify({"ok": True, "files": out, "ai_enabled": bool(get_ai_cfg().get("enabled"))}), 201


@app.post("/api/ai/invoice")
def ai_invoice():
    names = _body().get("files") or []
    if not isinstance(names, list) or not names:
        return err("Upload the invoice first.")
    paths = []
    for n in names:
        n = str(n)
        if "/" in n or "\\" in n or n.startswith(".") or not (PHOTOS_DIR / n).is_file():
            return err("Invoice file not found — upload it again.")
        paths.append(PHOTOS_DIR / n)

    def run():
        res = ai_mod.extract_invoice(get_ai_cfg(), [(p.read_bytes(), _mime_of(p)) for p in paths])
        items = active_items(load_store())
        for ln in res["lines"]:
            ln.update(_match_name(ln["description"], items))
        vendors = load_store().get("vendors") or []
        v = next((x for x in vendors if res["vendor"] and x.get("name", "").lower() in res["vendor"].lower()), None)
        res["vendor_id"] = v["id"] if v else None
        return jsonify({"ok": True, "invoice": res, "saved": False})
    return _ai_call(run)


def _shelf_result(items_in: list, section: str, st: dict) -> list:
    have = active_items(st)
    out = []
    for it in items_in:
        it.update(_match_name(it["name"], have))
        it["zone"] = section
        out.append(it)
    return out


@app.post("/api/ai/shelf")
def ai_shelf():
    st = load_store()
    if request.files:
        section = request.form.get("section") or ""
        text = request.form.get("text") or ""
        f = request.files.get("photo")
        image = None
        if f and f.filename:
            ext = Path(f.filename).suffix.lower()
            if ext not in PHOTO_EXT or ext == ".pdf":
                return err("Use a photo (jpg, png, webp, heic).")
            image = (f.read(), _mime_of(Path(f.filename)))
    else:
        d = _body()
        section, text, image = d.get("section") or "", str(d.get("text") or ""), None
    secs = {x["key"]: x["name"] for x in store_sections(st)}
    if section not in secs:
        return err("Pick a section first.")

    def run():
        known = [i["name"] for i in active_items(st)] + [c["name"] for c in starter_catalog.CATALOG[:120]]
        items = ai_mod.propose_shelf(get_ai_cfg(), secs[section], known, image=image, text=text)
        return jsonify({"ok": True, "section": section, "items": _shelf_result(items, section, st), "saved": False})
    return _ai_call(run)


@app.post("/api/ai/tidy")
def ai_tidy():
    d = _body()
    st = load_store()
    secs = {x["key"]: x["name"] for x in store_sections(st)}
    section = d.get("section") or ""
    if section not in secs:
        return err("Pick a section first.")
    text = str(d.get("text") or "")
    if not text.strip():
        return err("Say or type what's in this section first.")

    def run():
        items = ai_mod.propose_shelf(get_ai_cfg(), secs[section], [i["name"] for i in active_items(st)], text=text)
        return jsonify({"ok": True, "section": section, "items": _shelf_result(items, section, st), "saved": False})
    return _ai_call(run)


@app.get("/api/sections")
def sections_get():
    st = load_store()
    counts = {}
    for i in active_items(st):
        counts[i["zone"]] = counts.get(i["zone"], 0) + 1
    secs = [{**x, "count": counts.get(x["key"], 0)} for x in store_sections(st)]
    return jsonify({"ok": True, "sections": secs, "suggestions": sections_mod.SUGGESTIONS,
                    "custom": bool(st["settings"].get("sections"))})


@app.put("/api/sections")
def sections_put():
    d = _body()
    st = load_store()
    cur = store_sections(st)
    new, e = sections_mod.normalize(d.get("sections"), cur)
    if e:
        return err(e)
    keys = [x["key"] for x in new]
    gone = {x["key"]: x["name"] for x in cur if x["key"] not in keys}
    stuck = [i for i in active_items(st) if i["zone"] in gone]
    if stuck:
        move_to = d.get("move_to")
        if move_to not in keys:
            names = sorted({gone[i["zone"]] for i in stuck})
            return jsonify({"ok": False, "error": f"{len(stuck)} product(s) still live in {', '.join(names)}. Pick where they go.",
                            "needs_move": True, "count": len(stuck)}), 409
        for i in stuck:
            i["zone"] = move_to
    for i in st["items"]:
        if i.get("archived") and i.get("zone") not in keys:
            i["zone"] = keys[0]
    st["settings"]["sections"] = new
    st["settings"]["zones"] = keys
    save_store(st)
    return jsonify({"ok": True, "sections": new})


@app.post("/api/sections/<key>/count")
def section_count(key: str):
    """Pass 2 per-section count from the review table: {counts: {item_id: qty}} — only after the user confirms."""
    st = load_store()
    if key not in store_zones(st):
        return err("Unknown section.", 404)
    counts = _body().get("counts") or {}
    if not isinstance(counts, dict):
        return err("Counts must be an object.")
    n = 0
    for iid, q in counts.items():
        it = find_item(st, iid)
        if not it or it.get("zone") != key:
            continue
        try:
            q = float(q)
        except (TypeError, ValueError):
            return err(f"Count for {it['name']} must be a number.")
        if q < 0:
            return err(f"Count for {it['name']} can't be negative.")
        it["on_hand"] = q
        n += 1
    save_store(st)
    return jsonify({"ok": True, "updated": n})


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        save_store(empty_store())
    import socket
    import sys

    lan = "--lan" in sys.argv or os.environ.get("OSFT_LAN") == "1"
    host = os.environ.get("OSFT_HOST", "0.0.0.0" if lan else "127.0.0.1")
    port = int(os.environ.get("OSFT_PORT", "5053"))
    # ASCII only: on Windows the installer redirects output to a log file in the local code page
    print(f"OSFT {VERSION} -> http://127.0.0.1:{port}/")
    if host == "0.0.0.0":
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
            s.close()
            print(f"Phone on the same Wi-Fi -> http://{ip}:{port}/  (no login - trusted networks only)")
        except OSError:
            pass
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
