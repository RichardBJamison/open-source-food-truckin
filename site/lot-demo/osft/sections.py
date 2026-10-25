"""Truck sections ("placements") — the OSFT version of OSBW bars/stations.

Owners name their own sections (cooler, freezer, dry shelf 1, line, cab, under-counter, propane rack…).
Each section has a stable ``key`` (what products point at) and a display ``name`` that can change.
Order of the list = walk / count order.
"""
from __future__ import annotations

import re

LEGACY_NAMES = {
    "cooler": ("Cooler", "Refrigerador"), "freezer": ("Freezer", "Congelador"), "dry": ("Dry storage", "Almacén seco"),
    "prep": ("Prep", "Preparación"), "outside": ("Outside", "Afuera"), "window": ("Window", "Ventanilla"),
    "commissary": ("Commissary", "Comisariato"),
}
SUGGESTIONS = [
    {"name": "Cooler", "name_es": "Refrigerador"}, {"name": "Freezer", "name_es": "Congelador"},
    {"name": "Lowboy (under-counter)", "name_es": "Refri bajo mostrador"}, {"name": "Line / make table", "name_es": "Línea / mesa de preparación"},
    {"name": "Dry shelf 1", "name_es": "Repisa seca 1"}, {"name": "Dry shelf 2", "name_es": "Repisa seca 2"},
    {"name": "Window / pass", "name_es": "Ventanilla"}, {"name": "Cab", "name_es": "Cabina"},
    {"name": "Propane rack", "name_es": "Rack de gas"}, {"name": "Paper & to-go", "name_es": "Desechables"},
    {"name": "Drinks cooler", "name_es": "Refri de bebidas"}, {"name": "Commissary", "name_es": "Comisariato"},
]
MAX_SECTIONS = 40
MAX_NAME = 40


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:32] or "section"


def from_zones(zones: list[str]) -> list[dict]:
    return [{"key": z, "name": LEGACY_NAMES.get(z, (z.replace("-", " ").title(),))[0]} for z in zones]


def normalize(raw, existing: list[dict]) -> tuple[list[dict] | None, str | None]:
    """Validate a full ordered replacement list. Keeps keys of rows that carry one; new rows get a unique slug."""
    if not isinstance(raw, list) or not raw:
        return None, "Add at least one section."
    if len(raw) > MAX_SECTIONS:
        return None, f"Up to {MAX_SECTIONS} sections."
    known = {s["key"] for s in existing}
    rows = [{"name": r} if isinstance(r, str) else r for r in raw]
    if any(not isinstance(r, dict) for r in rows):
        return None, "Each section needs a name."
    claimed, explicit = set(), []
    for r in rows:
        k = str(r.get("key") or "")
        if k in known and k not in claimed:
            claimed.add(k)
            explicit.append(k)
        else:
            explicit.append(None)
    by_name = {x["name"].lower(): x["key"] for x in existing}
    for idx, r in enumerate(rows):  # a plain name that matches an unclaimed existing section keeps its key
        if explicit[idx] is None:
            nm = str(r.get("name") or "").strip()
            k = by_name.get(nm.lower()) or (slug(nm) if slug(nm) in known else None)
            if k and k not in claimed:
                claimed.add(k)
                explicit[idx] = k
    out, names, used = [], set(), set(claimed)
    for r, key in zip(rows, explicit):
        name = re.sub(r"\s+", " ", str(r.get("name") or "")).strip()
        if not name:
            return None, "Each section needs a name."
        if len(name) > MAX_NAME:
            return None, f"Section names must be {MAX_NAME} characters or less."
        if name.lower() in names:
            return None, f"“{name}” is listed twice."
        names.add(name.lower())
        if not key:
            base = slug(name)
            key, n = base, 2
            while key in used or key in known:
                key, n = f"{base}-{n}", n + 1
            used.add(key)
        out.append({"key": key, "name": name})
    return out, None
