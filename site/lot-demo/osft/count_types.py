"""v1.3 count types — daily end-of-shift (partial), weekly full, monthly in-depth.

Mirrors OSBW's count cycle (weekly / monthly, interval_days) and its station-scoped counts:
a count only answers for the stations (here: sections / categories / watch list) it covers.
"Missing" only means missing inside that scope; anything outside keeps its last known on-hand.
"""
from __future__ import annotations

TIMINGS = ("before_service", "end_of_shift")
DEFAULTS = [
    {"key": "daily", "name": "Daily end-of-shift", "name_es": "Diario al cierre", "enabled": True, "full": False,
     "sections": [], "categories": ["Protein", "Proteins", "Meat"], "items": [], "exclude_sections": [],
     "checklist": [], "timing": "end_of_shift", "interval_days": 1},
    {"key": "weekly", "name": "Weekly full count", "name_es": "Conteo completo semanal", "enabled": True, "full": True,
     "sections": [], "categories": [], "items": [], "exclude_sections": ["commissary"],
     "checklist": [], "timing": "before_service", "interval_days": 7},
    {"key": "monthly", "name": "Monthly in-depth", "name_es": "Mensual a fondo", "enabled": True, "full": True,
     "sections": [], "categories": [], "items": [], "exclude_sections": [],
     "checklist": ["Commissary storage", "Paper & supplies", "Propane", "Waste review"],
     "timing": "before_service", "interval_days": 30},
]
LEGACY = {"key": "weekly", "name": "Full count", "full": True}


def get_types(settings: dict) -> list[dict]:
    have = settings.get("count_types")
    if not isinstance(have, list) or not have:
        return [dict(d) for d in DEFAULTS]
    return [dict(t) for t in have]


def normalize(raw, sections: list[str], item_ids: set) -> tuple[list | None, str | None]:
    if not isinstance(raw, list) or not raw:
        return None, "Add at least one count type."
    out, keys = [], set()
    for t in raw:
        if not isinstance(t, dict):
            return None, "Each count type must be an object."
        key = str(t.get("key") or "").strip().lower().replace(" ", "-")[:24]
        name = str(t.get("name") or "").strip()[:60]
        if not key or not name:
            return None, "Every count type needs a key and a name."
        if key in keys:
            return None, f"Two count types use “{key}”."
        keys.add(key)
        full = bool(t.get("full"))
        secs = [s for s in (t.get("sections") or []) if s in sections]
        cats = [str(c).strip()[:40] for c in (t.get("categories") or []) if str(c).strip()]
        its = [i for i in (t.get("items") or []) if i in item_ids]
        if not full and not (secs or cats or its):
            return None, f"“{name}”: pick sections, categories or watch-list products (or make it a full count)."
        timing = t.get("timing") if t.get("timing") in TIMINGS else ("end_of_shift" if not full else "before_service")
        out.append({"key": key, "name": name, "name_es": str(t.get("name_es") or "").strip()[:60],
                    "enabled": bool(t.get("enabled", True)), "full": full, "sections": secs, "categories": cats,
                    "items": its, "exclude_sections": [s for s in (t.get("exclude_sections") or []) if s in sections],
                    "checklist": [str(c).strip()[:60] for c in (t.get("checklist") or []) if str(c).strip()][:12],
                    "timing": timing, "interval_days": max(1, min(int(t.get("interval_days") or 7), 92))})
    if not any(t["full"] and t["enabled"] for t in out):
        return None, "Keep at least one full count (weekly or monthly) switched on."
    return out, None


def scope_items(ctype: dict, items: list[dict]) -> list[dict]:
    if ctype.get("full"):
        ex = set(ctype.get("exclude_sections") or [])
        return [i for i in items if i.get("zone") not in ex]
    secs, cats, ids = set(ctype.get("sections") or []), {c.lower() for c in ctype.get("categories") or []}, set(ctype.get("items") or [])
    return [i for i in items if i.get("zone") in secs or (i.get("category") or "").lower() in cats or i["id"] in ids]


def scope_label(ctype: dict, section_names: dict) -> str:
    if ctype.get("full"):
        ex = [section_names[s] for s in ctype.get("exclude_sections") or [] if s in section_names]
        return "Full truck" + (f" (not {', '.join(ex)})" if ex else "") + (" + " + ", ".join(ctype["checklist"]) if ctype.get("checklist") else "")
    parts = [section_names[s] for s in ctype.get("sections") or [] if s in section_names] + list(ctype.get("categories") or [])
    if ctype.get("items"):
        parts.append(f"{len(ctype['items'])} watch-list product(s)")
    return ", ".join(parts)


def allowed(user: dict | None, key: str) -> bool:
    if not user or user.get("role") == "admin":
        return True
    lim = user.get("count_types")
    return not lim or key in lim
