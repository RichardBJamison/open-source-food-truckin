"""v1.2 setup reconcile: merge what was spoken per section with lines from the owner's product invoices.

Mirrors OSBW: "Every input is a proposal. Reconciliation is the conversation until map and count agree."
Nothing here writes to the store — server.py applies a plan only after the owner confirms it.
"""
from __future__ import annotations

import csv
import io
import re

from . import voice

UNITS = r"cs|case|cases|lb|lbs|ea|each|bag|bags|box|bx|gal|qt|pk|pack|ct|tub|tubs|can|cans|btl|bottle|jar|dz|doz"
LEAD = re.compile(rf"^\s*(?P<qty>\d+(?:\.\d+)?)\s*(?:x\s*)?(?P<unit>{UNITS})?\.?\s+(?P<name>.+?)"
                  r"(?:\s+@?\s*\$?(?P<price>\d+(?:\.\d{1,2})))?(?:\s+\$?\d+(?:\.\d{1,2}))?\s*$", re.I)
TRAIL = re.compile(rf"^\s*(?:[\w-]*\d[\w-]*\s+)?(?P<name>[A-Za-zÀ-ÿ][^$]*?)\s{{1,}}(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>{UNITS})?\.?\s+"
                   r"\$?(?P<price>\d+(?:\.\d{1,2}))(?:\s+\$?(?P<ext>\d+(?:\.\d{1,2})))?\s*$", re.I)
SKIP = re.compile(r"^\s*(sub ?total|total|tax|balance|amount due|invoice|page|date|bill to|ship to|thank)", re.I)
PACK = re.compile(r"(\d+\s*(?:x|/)\s*\d+(?:\.\d+)?\s*(?:lb|oz|ct|gal|qt|kg|g)?|\d+(?:\.\d+)?\s*(?:lb|oz|ct|gal|qt|kg)\b)", re.I)
KEYS = {"name": ("description", "item", "product", "name", "desc", "item description"),
        "qty": ("qty", "quantity", "qty shipped", "shipped", "cases", "count"),
        "unit": ("unit", "uom", "u/m", "pack unit"),
        "unit_cost": ("unit cost", "price", "unit price", "cost", "each"),
        "pack": ("pack", "pack size", "size", "pack/size")}


def _num(v):
    try:
        return round(float(str(v).replace("$", "").replace(",", "").strip()), 4)
    except (TypeError, ValueError):
        return None


def _line(name, qty=None, unit=None, unit_cost=None, pack=None, total=None) -> dict:
    name = re.sub(r"\s{2,}", " ", str(name or "")).strip(" -–:*")[:120]
    pk = pack or (PACK.search(name).group(1) if PACK.search(name) else None)
    q, c = _num(qty), _num(unit_cost)
    if c is None and total is not None and q:
        c = round(_num(total) / q, 4) if _num(total) is not None else None
    return {"description": name, "qty": q, "unit": (str(unit).lower().rstrip(".") if unit else None),
            "unit_cost": c, "pack": pk}


def parse_csv(text: str) -> list[dict]:
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) < 2:
        return []
    head = [h.strip().lower() for h in rows[0]]
    col = {}
    for k, names in KEYS.items():
        for i, h in enumerate(head):
            if h in names and k not in col:
                col[k] = i
    if "name" not in col:
        return []
    out = []
    for r in rows[1:]:
        g = lambda k: r[col[k]] if k in col and col[k] < len(r) else None  # noqa: E731
        if g("name") and str(g("name")).strip():
            out.append(_line(g("name"), g("qty"), g("unit"), g("unit_cost"), g("pack")))
    return out


def parse_text(text: str) -> tuple[list[dict], int]:
    """Best-effort local read of invoice text (typed lines, CSV, or a PDF's text layer). Returns (lines, unread)."""
    if not text or not text.strip():
        return [], 0
    first = text.strip().splitlines()[0].lower()
    if text.count(",") >= 2 and any(n in first for n in KEYS["name"]):
        rows = parse_csv(text)
        if rows:
            return rows, 0
    out, unread = [], 0
    for raw in text.splitlines():
        s = raw.strip()
        if not s or SKIP.match(s) or not re.search(r"[A-Za-z]", s):
            continue
        m = TRAIL.match(s)
        if m:
            out.append(_line(m.group("name"), m.group("qty"), m.group("unit"), m.group("price")))
            continue
        m = LEAD.match(s)
        if m and not re.fullmatch(r"\d+", m.group("name")):
            out.append(_line(m.group("name"), m.group("qty"), m.group("unit"), m.group("price")))
            continue
        unread += 1
    return out, unread


SIZE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:x|/)\s*\d+(?:\.\d+)?\s*[a-z]*\b|\b\d+(?:\.\d+)?\s*(?:in|inch|oz|lb|lbs|ct|gal|qt|kg|g|#)\b|#\s*\d+", re.I)


def core(name: str) -> str:
    """Product name without pack/size noise: "Corn Tortillas 6in 12x80ct" -> "corn tortilla"."""
    return " ".join(voice.name_tokens(SIZE.sub(" ", name))) or " ".join(voice.name_tokens(name))


def _same(a: str, b: str) -> bool:
    if core(a) == core(b):
        return True
    a, b = core(a), core(b)
    return voice.score_match(a, {"name": b}) >= 130 or voice.score_match(b, {"name": a}) >= 130


def dedupe(invoices: list[dict]) -> list[dict]:
    """Merge the same product across invoices: qty adds up, latest cost wins, vendors are kept."""
    groups: list[dict] = []
    for inv in invoices:
        for ln in inv.get("lines") or []:
            name = (ln.get("description") or "").strip()
            if not name:
                continue
            g = next((x for x in groups if _same(name, x["name"])), None)
            if not g:
                g = {"key": voice.name_key(name) if hasattr(voice, "name_key") else " ".join(voice.name_tokens(name)),
                     "name": name, "qty": 0.0, "unit": None, "unit_cost": None, "pack": None, "vendors": [],
                     "seen": 0, "spellings": []}
                groups.append(g)
            if not ln.get("pack") and PACK.search(name):
                ln = {**ln, "pack": PACK.search(name).group(1)}
            g["seen"] += 1
            if name not in g["spellings"]:
                g["spellings"].append(name)
            if ln.get("qty") is not None:
                g["qty"] = round(g["qty"] + float(ln["qty"]), 4)
            for k in ("unit", "unit_cost", "pack"):
                if ln.get(k) not in (None, ""):
                    g[k] = ln[k]
            v = (inv.get("vendor") or "").strip()
            if v and v not in g["vendors"]:
                g["vendors"].append(v)
    for g in groups:
        if not g["qty"]:
            g["qty"] = None
    return groups


ZONE_WORDS = {"cooler": ("cool", "refri", "fridge", "lowboy", "reach", "walk-in"),
              "freezer": ("freez", "congel", "frozen"),
              "dry": ("dry", "seca", "shelf", "repisa", "pantry"),
              "prep": ("line", "make", "prep", "línea", "linea")}


def suggest_section(name: str, sections: list[dict], starter: list[dict]) -> str | None:
    m = voice.match_entry(name, starter, None)
    z = (m["item"] or {}).get("zone") if m["status"] in ("matched", "ambiguous") else None
    if not z:
        return None
    keys = [s["key"] for s in sections]
    if z in keys:
        return z
    for s in sections:
        if any(w in s["name"].lower() for w in ZONE_WORDS.get(z, ())):
            return s["key"]
    return None


def reconcile(items: list[dict], sections: list[dict], invoices: list[dict], not_stocked: list[str],
              starter: list[dict], links: dict | None = None) -> dict:
    """links: owner fixes from the Reconcile screen — {invoice_key: item_id} forces a match, {invoice_key: ""} unlinks."""
    groups = dedupe(invoices)
    links = links or {}
    by_id = {i["id"]: i for i in items}
    by_item: dict[str, dict] = {}
    unplaced, ignored = [], []
    ns = {k.lower() for k in not_stocked}
    for g in groups:
        if g["key"] in links:
            tgt = by_id.get(links[g["key"]])
            m = {"status": "matched", "item": tgt} if tgt else {"status": "unlinked", "item": None}
        else:
            m = voice.match_entry(g["name"], items, None)
        if m["status"] == "matched":
            prev = by_item.get(m["item"]["id"])
            if prev:  # two invoice spellings landed on one product: merge
                prev["qty"] = (prev["qty"] or 0) + (g["qty"] or 0) or None
                prev["spellings"] += [s for s in g["spellings"] if s not in prev["spellings"]]
                for k in ("unit_cost", "pack", "unit"):
                    prev[k] = g[k] or prev[k]
                prev["vendors"] += [v for v in g["vendors"] if v not in prev["vendors"]]
                prev["keys"].append(g["key"])
            else:
                by_item[m["item"]["id"]] = {**g, "keys": [g["key"]], "spellings": list(g["spellings"]),
                                            "vendors": list(g["vendors"])}
            continue
        if g["name"].lower() in ns or g["key"] in ns:
            ignored.append(g)
            continue
        g["unlinked"] = m["status"] == "unlinked"
        g["suggest"] = suggest_section(g["name"], sections, starter)
        g["maybe"] = ({"id": m["item"]["id"], "name": m["item"]["name"]}
                      if m["status"] == "ambiguous" and m["item"] is not None else None)
        unplaced.append(g)
    out_secs, n_items, n_inv, n_nocost = [], 0, 0, 0
    for s in sections:
        rows = []
        for it in items:
            if it.get("zone") != s["key"]:
                continue
            g = by_item.get(it["id"])
            flags = []
            if g and g.get("unit") and it.get("unit") and (voice.canon_unit(g["unit"]) or g["unit"]) != (voice.canon_unit(it["unit"]) or it["unit"]):
                flags.append("unit_differs")
            ed = it.get("_edited") or []
            cost = it.get("cost") if "cost" in ed or not (g and g.get("unit_cost") is not None) else g["unit_cost"]
            if cost in (None, "", 0):
                flags.append("no_cost")
            rows.append({"id": it["id"], "name": it["name"], "unit": it.get("unit"), "spoken_qty": it.get("on_hand"),
                         "from_invoice": bool(g), "invoice_name": g["spellings"][0] if g else None,
                         "invoice_qty": g["qty"] if g else None, "invoice_unit": g["unit"] if g else None,
                         "invoice_keys": g["keys"] if g else [],
                         "cost": cost, "cost_from_invoice": bool(g and g.get("unit_cost") is not None and "cost" not in ed),
                         "pack": (it.get("pack") if "pack" in ed else None) or (g or {}).get("pack") or it.get("pack") or None,
                         "vendor": it.get("vendor_name") if "vendor" in ed else (", ".join(g["vendors"]) if g else None),
                         "zone": it.get("zone"), "pending_new": bool(it.get("_new")), "edited": sorted(ed), "flags": flags})
            n_items += 1
            n_inv += bool(g)
            n_nocost += "no_cost" in flags
        out_secs.append({"key": s["key"], "name": s["name"], "items": rows})
    return {"sections": out_secs, "unplaced": unplaced, "not_stocked": ignored,
            "stats": {"sections": len(sections), "with_products": sum(1 for s in out_secs if s["items"]),
                      "products": n_items, "from_invoice": n_inv, "to_place": len(unplaced), "no_cost": n_nocost,
                      "invoice_lines": sum(len(i.get("lines") or []) for i in invoices), "invoice_products": len(groups),
                      "invoices": len(invoices)}}
