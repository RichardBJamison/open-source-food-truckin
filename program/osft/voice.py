"""Spoken-count parser for OSFT ("speak your inventory").

Port of the Open Source Barware count-dictation logic (parseCountText /
countLevelAt / scoreCountBottleMatch / reconcile) re-tuned for food-truck
stock: pounds, cases, bags, quarts, partials ("half a case", "two and a half",
"point five"), English + Spanish, fuzzy product matching and a
matched / ambiguous / unmatched / missing reconcile report that the UI shows
for confirmation before anything is written.

Pure functions, no Flask — unit-tested in tests/test_voice.py.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

MATCH_MIN_SCORE = 85          # same threshold as OSBW COUNT_MATCH_MIN_SCORE
AMBIGUOUS_MARGIN = 6          # top two this close → ask the user
GAP_TOLERANCE = 2             # OSBW COUNT_GAP_TOLERANCE: finish unlocks at ≤ 2 unresolved
MAX_QTY = 9999

# ---------------------------------------------------------------- text prep

def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


ONES = {
    "zero": 0, "oh": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    # Spanish
    "cero": 0, "uno": 1, "un": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6,
    "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiuno": 21, "veintiun": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23, "veinticuatro": 24,
    "veinticinco": 25, "veintiseis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80, "noventa": 90,
}
HUNDREDS = {"hundred": 100, "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200,
            "trescientos": 300, "trescientas": 300, "cuatrocientos": 400, "quinientos": 500}
# Speech engines mishear these; only treated as numbers right before a unit or at clause end (OSBW did too/to/for).
SOUNDALIKE = {"to": 2, "too": 2, "for": 4, "fore": 4, "won": 1, "ate": 8}
FRACTION_WORDS = {"half": 0.5, "medio": 0.5, "media": 0.5, "mitad": 0.5, "quarter": 0.25, "cuarto": 0.25,
                  "third": 1 / 3, "tercio": 1 / 3}
ZERO_WORDS = {"none", "empty", "out", "nothing", "zero", "nada", "vacio", "vacia", "agotado", "agotada",
              "ninguno", "ninguna", "cero"}
FULL_WORDS = {"full", "lleno", "llena"}

# canonical unit → spoken forms
UNIT_WORDS = {
    "lb": ["lb", "lbs", "pound", "pounds", "libra", "libras"],
    "oz": ["oz", "ounce", "ounces", "onza", "onzas"],
    "kg": ["kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "kilogramo", "kilogramos"],
    "g": ["g", "gram", "grams", "gramo", "gramos"],
    "gal": ["gal", "gallon", "gallons", "galon", "galones"],
    "qt": ["qt", "quart", "quarts"],
    "pt": ["pt", "pint", "pints", "pinta", "pintas"],
    "l": ["liter", "liters", "litre", "litres", "litro", "litros"],
    "case": ["case", "cases", "cs", "caja", "cajas"],
    "pack": ["pack", "packs", "pk", "package", "packages", "paquete", "paquetes"],
    "bag": ["bag", "bags", "bolsa", "bolsas"],
    "box": ["box", "boxes", "carton", "cartons"],
    "can": ["can", "cans", "lata", "latas"],
    "bottle": ["bottle", "bottles", "botella", "botellas"],
    "jar": ["jar", "jars", "frasco", "frascos"],
    "tub": ["tub", "tubs", "bote", "botes"],
    "pan": ["pan", "pans", "hotel", "bandeja", "bandejas"],
    "tray": ["tray", "trays", "charola", "charolas"],
    "roll": ["roll", "rolls", "rollo", "rollos"],
    "sleeve": ["sleeve", "sleeves", "manga", "mangas"],
    "bunch": ["bunch", "bunches", "manojo", "manojos"],
    "head": ["head", "heads", "cabeza", "cabezas"],
    "loaf": ["loaf", "loaves"],
    "tank": ["tank", "tanks", "tanque", "tanques", "cylinder", "cylinders", "cilindro", "cilindros"],
    "bucket": ["bucket", "buckets", "pail", "pails", "cubeta", "cubetas", "cubo", "cubos"],
    "jug": ["jug", "jugs", "garrafa", "garrafas", "galonera"],
    "dozen": ["dozen", "dozens", "doz", "docena", "docenas"],
    "ea": ["each", "ea", "piece", "pieces", "pc", "pcs", "pieza", "piezas", "unidad", "unidades", "count", "ct"],
    "flat": ["flat", "flats"],
    "sack": ["sack", "sacks", "costal", "costales"],
}
UNIT_LOOKUP = {w: u for u, ws in UNIT_WORDS.items() for w in ws}

# Item-unit aliases (what people type in the Unit column) → canonical
ITEM_UNIT_ALIASES = dict(UNIT_LOOKUP)
ITEM_UNIT_ALIASES.update({"each": "ea", "ea.": "ea", "unit": "ea", "units": "ea", "pc": "ea", "dz": "dozen",
                          "lb.": "lb", "#": "lb", "gallon": "gal", "quart": "qt", "pint": "pt", "cyl": "tank",
                          "half pan": "pan", "1/2 pan": "pan", "1/3 pan": "pan", "1/6 pan": "pan", "ltr": "l"})

WEIGHT_TO_LB = {"lb": 1.0, "oz": 1 / 16, "kg": 2.20462, "g": 0.00220462}
VOLUME_TO_QT = {"qt": 1.0, "pt": 0.5, "gal": 4.0, "l": 1.05669}

# Zone (station) words. OSBW: "Well one", "Back bar" create stations. OSFT: storage areas on the truck.
ZONE_WORDS = {
    "cooler": ["cooler", "fridge", "refrigerator", "reach in", "reach-in", "walk in", "walk-in", "lowboy",
               "refri", "refrigerador", "nevera", "hielera", "frigorifico", "enfriador"],
    "freezer": ["freezer", "deep freeze", "congelador", "congeladora", "freezer chest"],
    "dry": ["dry storage", "dry goods", "dry", "pantry", "shelf", "shelves", "cabinet", "almacen", "despensa",
            "estante", "seco", "secos", "bodega"],
    "prep": ["prep", "make line", "line", "rail", "prep table", "steam table", "preparacion", "linea", "barra fria"],
    "outside": ["outside", "exterior", "afuera", "tongue", "hitch", "propane rack", "roof"],
    "commissary": ["commissary", "comisariato", "commisary", "storage unit", "warehouse"],
    "window": ["window", "service window", "front", "ventana", "ventanilla", "counter"],
}
ZONE_SPOKEN = sorted(((w, z) for z, ws in ZONE_WORDS.items() for w in ws), key=lambda p: -len(p[0]))

FILLER = {"we", "have", "got", "there", "is", "are", "about", "around", "like", "uh", "um", "umm", "erm",
          "maybe", "roughly", "approximately", "approx", "the", "of", "and", "plus", "left", "on", "hand",
          "in", "at", "its", "it's", "theres", "there's", "i", "count", "counted", "see", "so", "okay", "ok",
          "tenemos", "hay", "como", "unos", "unas", "el", "la", "los", "las", "de", "del", "y", "en", "quedan",
          "queda", "mas", "o", "menos", "a", "an", "some", "with", "just", "also", "then", "next", "now"}
CLAUSE_SPLIT = re.compile(r"(?:\r?\n|;|,(?!\d)|(?<!\d)\.(?!\d)|\.(?=\s|$)|\bthen\b|\bnext\b|\bnext up\b|\by luego\b|\bdespues\b|\bsiguiente\b)")


def normalize(text: str) -> str:
    s = strip_accents(str(text or "")).lower()
    s = s.replace("’", "'").replace("–", "-").replace("—", " ")
    s = re.sub(r"(\d),(\d{3})\b", r"\1\2", s)          # 1,000 → 1000
    s = re.sub(r"(\d)\s*(lbs?|oz|kg|g|qt|pt|gal|cs|pk|ct|ea)\b", r"\1 \2", s)  # 10lb → 10 lb
    s = re.sub(r"(\d)\s*#", r"\1 lb", s)                  # 10# → 10 lb
    s = re.sub(r"\bx\s*(\d)", r"\1", s)                    # x4 → 4
    s = s.replace("&", " and ")
    s = re.sub(r"[\"!?()\[\]{}:]", " ", s)
    # Spanish structure synonyms (OSBW applySpanishStructureSynonyms analogue)
    s = re.sub(r"\by (medio|media)\b", "and a half", s)
    s = re.sub(r"\by (un|una) cuarto\b", "and a quarter", s)
    s = re.sub(r"\by tres cuartos\b", "and three quarters", s)
    s = re.sub(r"\btres cuartos\b", "three quarters", s)
    s = re.sub(r"\bun cuarto\b", "a quarter", s)
    s = re.sub(r"\bmedia caja\b", "half case", s)
    s = re.sub(r"\bmedio (\w+)", r"half \1", s)
    s = re.sub(r"\bpunto\b", "point", s)
    s = re.sub(r"\bno (hay|queda|quedan|more|tenemos)\b", "none", s)
    s = re.sub(r"\b(ran out( of)?|all out( of)?|out of)\b", "none", s)
    s = re.sub(r"\bse acabo( el| la| los| las)?\b", "none", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def singular(w: str) -> str:
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith(("oes", "ches", "shes", "xes", "ses")):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def name_tokens(s: str) -> list[str]:
    s = normalize(s)
    s = re.sub(r"[^a-z0-9/ ]+", " ", s)
    return [singular(w) for w in s.split() if w and w not in {"the", "of", "de", "del", "la", "el", "los", "las", "a"}]


# ---------------------------------------------------------------- quantities

def _word_number(words: list[str], i: int) -> tuple[float | None, int]:
    """Parse a spoken cardinal starting at i. Returns (value, consumed)."""
    n = len(words)
    total = 0
    consumed = 0
    w = words[i] if i < n else ""
    if w in HUNDREDS:
        total = HUNDREDS[w]
        consumed = 1
        if i + 1 < n and words[i + 1] == "and" and i + 2 < n and (words[i + 2] in ONES or words[i + 2] in TENS):
            consumed += 1
    elif w in ONES and i + 1 < n and words[i + 1] == "hundred":
        total = ONES[w] * 100
        consumed = 2
        if i + 2 < n and words[i + 2] == "and" and i + 3 < n and (words[i + 3] in ONES or words[i + 3] in TENS):
            consumed += 1
    j = i + consumed
    if j < n and words[j] in TENS:
        total += TENS[words[j]]
        consumed += 1
        j += 1
        # "twenty three", "twenty-three" (split earlier), "treinta y dos"
        if j < n and words[j] in ONES and 0 < ONES[words[j]] < 10 and words[j] not in ("un", "una"):
            total += ONES[words[j]]
            consumed += 1
        elif j + 1 < n and words[j] == "y" and words[j + 1] in ONES and 0 < ONES[words[j + 1]] < 10:
            total += ONES[words[j + 1]]
            consumed += 2
        return float(total), consumed
    if j < n and words[j] in ONES and (consumed == 0 or ONES[words[j]] < 100):
        if consumed and ONES[words[j]] >= 20:
            pass
        total += ONES[words[j]]
        consumed += 1
        return float(total), consumed
    if consumed:
        return float(total), consumed
    return None, 0


NUM_RE = re.compile(r"^(\d+(?:\.\d+)?|\.\d+)$")
FRAC_RE = re.compile(r"^(\d+)/(\d+)$")


def _base_number(words: list[str], i: int) -> tuple[float | None, int]:
    n = len(words)
    w = words[i]
    m = NUM_RE.match(w)
    if m:
        v = float(w)
        if i + 1 < n and FRAC_RE.match(words[i + 1]):          # "2 1/2"
            a, b = FRAC_RE.match(words[i + 1]).groups()
            if int(b):
                return v + int(a) / int(b), 2
        return v, 1
    m = FRAC_RE.match(w)
    if m:
        a, b = m.groups()
        return (int(a) / int(b), 1) if int(b) else (None, 0)
    if w == "point" and i + 1 < n:                           # "point five" → 0.5
        d, c = _decimal_digits(words, i + 1)
        if c:
            return d, 1 + c
    v, c = _word_number(words, i)
    if c:
        # "two point five"
        if i + c < n and words[i + c] == "point":
            d, c2 = _decimal_digits(words, i + c + 1)
            if c2:
                return v + d, c + 1 + c2
        return v, c
    return None, 0


def _decimal_digits(words: list[str], i: int) -> tuple[float, int]:
    digits = ""
    j = i
    while j < len(words) and j - i < 3:
        w = words[j]
        if w.isdigit():
            digits += w
        elif w in ONES and ONES[w] < 10 and w not in ("un", "una"):
            digits += str(ONES[w])
        else:
            break
        j += 1
    if not digits:
        return 0.0, 0
    return float("0." + digits), j - i


def _unit_at(words: list[str], i: int) -> tuple[str | None, int]:
    if i >= len(words):
        return None, 0
    j = i
    if words[j] in ("of", "de", "del") and j + 1 < len(words) and words[j + 1] in UNIT_LOOKUP:
        j += 1
    # two-word units
    if j + 1 < len(words) and f"{words[j]} {words[j + 1]}" in ("hotel pan", "half pan", "full pan", "third pan", "sixth pan"):
        return "pan", j - i + 2
    if words[j] in UNIT_LOOKUP:
        return UNIT_LOOKUP[words[j]], j - i + 1
    return None, 0


def quantity_at(words: list[str], i: int) -> dict | None:
    """Parse a quantity phrase at words[i]. Returns {qty, unit, consumed} or None.

    Handles: 14 · fourteen · twenty three · 2.5 · two point five · point five · .5 · 1/2 · 2 1/2 ·
    two and a half · half · a half · half a case · a case · three quarters · a dozen · none/out/empty
    · full · Spanish equivalents.
    """
    n = len(words)
    if i >= n:
        return None
    w = words[i]
    if w in ZERO_WORDS:
        return {"qty": 0.0, "unit": None, "consumed": 1}
    if w in FULL_WORDS and (i + 1 >= n or _unit_at(words, i + 1)[0]):
        u, uc = _unit_at(words, i + 1)
        return {"qty": 1.0, "unit": u, "consumed": 1 + uc}

    j = i
    value = None
    # a / an / un / una + (unit | fraction | dozen)
    if w in ("a", "an", "un", "una", "one") and i + 1 < n:
        nxt = words[i + 1]
        if nxt in FRACTION_WORDS:
            value, j = FRACTION_WORDS[nxt], i + 2
        elif _unit_at(words, i + 1)[0]:
            value, j = 1.0, i + 1
    if value is None and w in FRACTION_WORDS:
        value, j = FRACTION_WORDS[w], i + 1
    if value is None and w in ("three", "tres") and i + 1 < n and words[i + 1] in ("quarters", "quarter", "cuartos"):
        value, j = 0.75, i + 2
    if value is None:
        v, c = _base_number(words, i)
        if c:
            value, j = v, i + c
            # "three quarters" after a number word handled above; "and a half", "and three quarters"
            if j + 2 < n + 1 and j < n and words[j] == "and":
                if j + 2 <= n - 1 and words[j + 1] in ("a", "an", "one") and words[j + 2] in ("half", "quarter"):
                    value += FRACTION_WORDS[words[j + 2]]
                    j += 3
                elif j + 2 <= n - 1 and words[j + 1] == "three" and words[j + 2] in ("quarters", "quarter"):
                    value += 0.75
                    j += 3
                elif j + 1 < n and words[j + 1] in ("half",):
                    value += 0.5
                    j += 2
    if value is None and w in SOUNDALIKE:
        u, _ = _unit_at(words, i + 1)
        if u or i + 1 >= n:
            value, j = float(SOUNDALIKE[w]), i + 1
    if value is None:
        return None

    # "half a case", "half of a case"
    k = j
    if k < n and words[k] in ("a", "an", "of", "un", "una", "de"):
        u, uc = _unit_at(words, k + 1)
        if u:
            k += 1
    unit, uc = _unit_at(words, k)
    if unit:
        j = k + uc
    if unit == "dozen":
        value *= 12
        unit = "ea"
        nu, nuc = _unit_at(words, j)      # "a dozen eggs" stays ea; "dozen cases" unusual
    value = round(min(max(value, 0.0), MAX_QTY), 4)
    return {"qty": value, "unit": unit, "consumed": j - i}


# ---------------------------------------------------------------- clause → entries

def _detect_zone(words: list[str], i: int) -> tuple[str | None, int]:
    rest = " ".join(words[i:i + 3])
    for spoken, z in ZONE_SPOKEN:
        if rest == spoken or rest.startswith(spoken + " "):
            return z, len(spoken.split())
    return None, 0


def _clean_name(words: list[str]) -> str:
    ws = list(words)
    while ws and ws[0] in FILLER:
        ws.pop(0)
    while ws and ws[-1] in FILLER:
        ws.pop()
    return " ".join(ws).strip(" -'.")


def _protect(text: str, protected: list[str]) -> tuple[str, dict]:
    """Replace product names containing number/fraction words ("half and half", "7up") with placeholders."""
    mapping = {}
    for idx, name in enumerate(sorted(protected, key=len, reverse=True)):
        nn = normalize(name)
        if not nn:
            continue
        toks = nn.split()
        if not any(t in ONES or t in TENS or t in FRACTION_WORDS or t in ZERO_WORDS or t in FULL_WORDS
                   or t in SOUNDALIKE or NUM_RE.match(t) or t in UNIT_LOOKUP for t in toks) and not any(
                       nn == sp or nn.startswith(sp + " ") for sp, _z in ZONE_SPOKEN):
            continue
        key = f"zzprot{idx}zz"
        pat = r"(?<![a-z0-9])" + re.escape(nn) + r"(?![a-z0-9])"
        if re.search(pat, text):
            text = re.sub(pat, key, text)
            mapping[key] = nn
    return text, mapping


def parse_text(text: str, protected_names: list[str] | None = None, zones: list[str] | None = None) -> list[dict]:
    """Turn dictation into raw entries: [{name, qty, unit, zone, raw}] (qty None → needs a number)."""
    allowed_zones = set(zones) if zones else None
    norm = normalize(text)
    norm, prot = _protect(norm, protected_names or [])
    entries: list[dict] = []
    current_zone = None
    for ci, clause in enumerate(CLAUSE_SPLIT.split(norm)):
        if clause is None:
            continue
        clause = clause.strip(" .-")
        if not clause:
            continue
        words = [w for w in re.split(r"[\s\-]+", clause) if w]
        # leading zone ("cooler ground beef 14 lb", "in the freezer:")
        lead = 0
        while lead < len(words) and words[lead] in ("in", "the", "en", "el", "la", "now", "ahora", "zone", "zona", "area"):
            lead += 1
        z, zc = _detect_zone(words, lead)
        if z and (allowed_zones is None or z in allowed_zones or True):
            rest = words[lead + zc:]
            # a zone word immediately followed by a quantity is a product name ("prep 2" is odd) — accept zone
            current_zone = z
            words = rest
            if not words:
                continue
        i = 0
        buf: list[str] = []
        pending: dict | None = None          # quantity spoken before the name
        raw_start = 0
        while i < len(words):
            q = quantity_at(words, i)
            if q and q["consumed"]:
                name = _clean_name(buf)
                if name:
                    entries.append({"name": name, "qty": q["qty"], "unit": q["unit"], "zone": current_zone,
                                    "raw": " ".join(words[raw_start:i + q["consumed"]]),
                                    "_clause": ci, "_end": i + q["consumed"]})
                    buf = []
                    pending = None
                    raw_start = i + q["consumed"]
                elif (pending is None and entries and entries[-1].get("_clause") == ci
                      and entries[-1].get("_end") == i and q["unit"] and entries[-1]["unit"]
                      and q["unit"] != entries[-1]["unit"]):
                    # "3 cases 6 packs" → compound quantity on the same product
                    entries[-1].setdefault("extra", []).append({"qty": q["qty"], "unit": q["unit"]})
                    entries[-1]["raw"] += " " + " ".join(words[i:i + q["consumed"]])
                    entries[-1]["_end"] = i + q["consumed"]
                    raw_start = i + q["consumed"]
                elif pending is None:
                    pending = q
                else:
                    # two quantities in a row with no name: keep the latter
                    pending = q
                i += q["consumed"]
                continue
            # zone switch mid-clause ("... freezer carnitas 12")
            z2, zc2 = _detect_zone(words, i)
            if z2 and not buf and pending is None:
                current_zone = z2
                i += zc2
                raw_start = i
                continue
            buf.append(words[i])
            i += 1
            # qty-first: "14 pounds ground beef" → name runs until next quantity or clause end
            if pending is not None:
                nxt = quantity_at(words, i) if i < len(words) else None
                if i >= len(words) or (nxt and nxt["consumed"]):
                    name = _clean_name(buf)
                    if name:
                        entries.append({"name": name, "qty": pending["qty"], "unit": pending["unit"],
                                        "zone": current_zone, "raw": " ".join(words[raw_start:i])})
                        buf = []
                        pending = None
                        raw_start = i
        tail = _clean_name(buf)
        if tail:
            entries.append({"name": tail, "qty": pending["qty"] if pending else None,
                            "unit": pending["unit"] if pending else None, "zone": current_zone,
                            "raw": " ".join(words[raw_start:])})
    for e in entries:
        e.pop("_clause", None)
        e.pop("_end", None)
        for key, nn in prot.items():
            e["name"] = e["name"].replace(key, nn)
            e["raw"] = e["raw"].replace(key, nn)
    return entries


# ---------------------------------------------------------------- matching

def score_match(spoken: str, item: dict) -> int:
    """0–200 like OSBW scoreCountBottleMatch: exact 200, alias 195, all-item-words 150,
    all-spoken-words 130, overlap 70–120, fuzzy ratio."""
    st = name_tokens(spoken)
    if not st:
        return 0
    best = 0
    names = [item.get("name") or ""] + list(item.get("aliases") or [])
    if item.get("name_es"):
        names.append(item["name_es"])
    for idx, nm in enumerate(names):
        base = re.sub(r"\(.*?\)", " ", nm)
        it = name_tokens(base)
        full = name_tokens(nm)
        if not it:
            continue
        if st == it or st == full:
            best = max(best, 200 if idx == 0 else 195)
            continue
        sset, iset = set(st), set(it) | set(full)
        if set(it) <= sset and (set(full) <= sset or len(sset - set(it)) == 0):
            # parenthetical words count too: "chicken thigh" is not "Chicken (whole)"
            best = max(best, 150 - 5 * max(0, len(sset - set(it)) - 1))
        elif sset <= iset:
            cover = len(sset) / max(1, len(set(it)))
            best = max(best, int(100 + 30 * cover))
        else:
            inter = len(sset & iset)
            if inter:
                jac = inter / len(sset | iset)
                best = max(best, int(60 + 60 * jac))
        ratio = difflib.SequenceMatcher(None, " ".join(st), " ".join(it)).ratio()
        best = max(best, int(ratio * 100))
        # case/spare guard (OSBW rejects case↔spare mismatches): spoken "case X" vs item "X" fine
    return best


def match_entry(spoken: str, items: list[dict], zone: str | None = None) -> dict:
    scored = []
    for it in items:
        s = score_match(spoken, it)
        if s <= 0:
            continue
        if zone and it.get("zone") == zone:
            s += 8
        scored.append((s, it))
    scored.sort(key=lambda p: (-p[0], p[1].get("name", "")))
    if not scored or scored[0][0] < MATCH_MIN_SCORE:
        return {"status": "unmatched", "item": None, "score": scored[0][0] if scored else 0,
                "candidates": [{"id": it["id"], "name": it["name"], "score": s} for s, it in scored[:3]]}
    top_s, top = scored[0]
    cands = [{"id": it["id"], "name": it["name"], "score": s} for s, it in scored[:3]]
    if len(scored) > 1 and scored[1][0] >= MATCH_MIN_SCORE and top_s - scored[1][0] < AMBIGUOUS_MARGIN and top_s < 200:
        return {"status": "ambiguous", "item": top, "score": top_s, "candidates": cands}
    return {"status": "matched", "item": top, "score": top_s, "candidates": cands}


def canon_unit(u: str | None) -> str | None:
    if not u:
        return None
    u = strip_accents(str(u)).strip().lower()
    if u in ITEM_UNIT_ALIASES:
        return ITEM_UNIT_ALIASES[u]
    s = singular(u)
    return ITEM_UNIT_ALIASES.get(s, s)


def convert_qty(qty: float, spoken_unit: str | None, item: dict) -> tuple[float, str | None]:
    """Convert a spoken quantity into the item's counting unit. Returns (qty, note)."""
    iu = canon_unit(item.get("unit"))
    su = spoken_unit
    if not su or su == iu:
        return qty, None
    case_size = item.get("case_size")
    try:
        case_size = float(case_size) if case_size not in (None, "") else None
    except (TypeError, ValueError):
        case_size = None
    if su == "case" and case_size:
        return round(qty * case_size, 4), f"{qty:g} case × {case_size:g} = {qty * case_size:g} {item.get('unit')}"
    if su in WEIGHT_TO_LB and iu in WEIGHT_TO_LB:
        v = qty * WEIGHT_TO_LB[su] / WEIGHT_TO_LB[iu]
        return round(v, 3), f"{qty:g} {su} → {v:.3g} {iu}"
    if su in VOLUME_TO_QT and iu in VOLUME_TO_QT:
        v = qty * VOLUME_TO_QT[su] / VOLUME_TO_QT[iu]
        return round(v, 3), f"{qty:g} {su} → {v:.3g} {iu}"
    if su == "ea" and iu in (None, "ea"):
        return qty, None
    return qty, f"unit_mismatch:{su}->{item.get('unit')}"


def reconcile(text: str, items: list[dict], zones: list[str] | None = None, scope: str = "mentioned_zones") -> dict:
    """Parse dictation and reconcile against the product list.

    scope: "mentioned_zones" (OSBW: only flag missing items in areas you walked) or "all".
    """
    live = [i for i in items if not i.get("archived")]
    protected = []
    for it in live:
        protected.append(it.get("name") or "")
        protected.extend(it.get("aliases") or [])
    entries = parse_text(text, protected_names=protected, zones=zones)
    lines = []
    totals: dict[str, float] = {}
    for idx, e in enumerate(entries):
        m = match_entry(e["name"], live, e.get("zone"))
        line = {"n": idx, "spoken": e["name"], "raw": e["raw"], "zone": e.get("zone"), "qty_spoken": e["qty"],
                "unit_spoken": e["unit"], "status": m["status"], "score": m["score"], "candidates": m["candidates"],
                "item_id": None, "item_name": None, "item_unit": None, "qty": None, "note": None}
        if e["qty"] is None:
            line["status"] = "no_qty" if m["item"] is not None and m["status"] != "unmatched" else "unmatched"
        if m["item"] is not None and m["status"] != "unmatched":
            it = m["item"]
            line.update(item_id=it["id"], item_name=it["name"], item_unit=it.get("unit"))
            if e["qty"] is not None:
                q, note = convert_qty(e["qty"], e["unit"], it)
                for ex in e.get("extra") or []:
                    q2, note2 = convert_qty(ex["qty"], ex["unit"], it)
                    q = round(q + q2, 4)
                    note = "; ".join(x for x in (note, note2) if x)
                line["qty"] = q
                line["note"] = note
                if note and note.startswith("unit_mismatch") and line["status"] == "matched":
                    line["status"] = "unit_check"
        lines.append(line)
    # sum duplicates (beef in cooler + beef in freezer)
    dup_count: dict[str, int] = {}
    for ln in lines:
        if ln["status"] in ("matched", "unit_check") and ln["item_id"]:
            totals[ln["item_id"]] = round(totals.get(ln["item_id"], 0.0) + float(ln["qty"] or 0), 4)
            dup_count[ln["item_id"]] = dup_count.get(ln["item_id"], 0) + 1
    mentioned_ids = {ln["item_id"] for ln in lines if ln["item_id"]}
    zones_walked = {ln["zone"] for ln in lines if ln["zone"]}
    missing = []
    for it in live:
        if it["id"] in mentioned_ids:
            continue
        if scope == "all" or not zones_walked or it.get("zone") in zones_walked:
            missing.append({"item_id": it["id"], "name": it["name"], "zone": it.get("zone"), "unit": it.get("unit"),
                            "on_hand": it.get("on_hand")})
    unresolved = sum(1 for ln in lines if ln["status"] in ("unmatched", "ambiguous", "no_qty"))
    return {
        "lines": lines,
        "totals": totals,
        "duplicates": {k: v for k, v in dup_count.items() if v > 1},
        "missing": missing,
        "zones_walked": sorted(zones_walked),
        "summary": {
            "heard": len(lines),
            "matched": sum(1 for ln in lines if ln["status"] == "matched"),
            "unit_check": sum(1 for ln in lines if ln["status"] == "unit_check"),
            "ambiguous": sum(1 for ln in lines if ln["status"] == "ambiguous"),
            "unmatched": sum(1 for ln in lines if ln["status"] == "unmatched"),
            "no_qty": sum(1 for ln in lines if ln["status"] == "no_qty"),
            "missing": len(missing),
            "unresolved": unresolved,
        },
        "gap_tolerance": GAP_TOLERANCE,
        "can_apply": unresolved <= GAP_TOLERANCE,
        "min_score": MATCH_MIN_SCORE,
    }


def walk_build(text: str, existing: list[dict], starter: list[dict]) -> dict:
    """Setup "walk": dictate areas + products to BUILD the list (OSBW voice_walk → build_bar).
    Unknown names get unit/category from the closest starter-catalog product."""
    entries = parse_text(text, protected_names=[s["name"] for s in starter] + [e.get("name", "") for e in existing])
    out = []
    seen = set()
    for e in entries:
        m = match_entry(e["name"], existing, e.get("zone"))
        if m["status"] == "matched":
            out.append({"spoken": e["name"], "action": "existing", "item_id": m["item"]["id"],
                        "name": m["item"]["name"], "zone": e.get("zone") or m["item"].get("zone"),
                        "unit": m["item"].get("unit"), "category": m["item"].get("category"),
                        "on_hand": e["qty"], "unit_spoken": e["unit"]})
            continue
        sm = match_entry(e["name"], starter, None)
        tmpl = sm["item"] if sm["status"] in ("matched", "ambiguous") else None
        name = tmpl["name"] if tmpl and sm["score"] >= 130 else e["name"].strip().capitalize()
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        unit = (tmpl or {}).get("unit") or (e["unit"] if e["unit"] and e["unit"] != "case" else "ea")
        out.append({"spoken": e["name"], "action": "new", "starter_id": (tmpl or {}).get("id"), "name": name,
                    "zone": e.get("zone") or (tmpl or {}).get("zone") or "dry", "unit": unit,
                    "category": (tmpl or {}).get("category") or "Other", "case_size": (tmpl or {}).get("case_size"),
                    "on_hand": e["qty"], "unit_spoken": e["unit"]})
    zones = sorted({o["zone"] for o in out if o.get("zone")})
    return {"proposals": out, "zones": zones}
