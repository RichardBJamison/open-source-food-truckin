"""Voice-count parser tests (speak-your-inventory, OSBW parity)."""
import pytest

from osft import voice

ITEMS = [
    {"id": "beef", "name": "Ground beef", "name_es": "Carne molida", "unit": "lb", "zone": "cooler"},
    {"id": "corn", "name": "Corn tortillas", "name_es": "Tortillas de maíz", "unit": "pack", "zone": "dry", "case_size": 12},
    {"id": "flour", "name": "Flour tortillas", "unit": "pack", "zone": "dry"},
    {"id": "hh", "name": "Half and half", "unit": "qt", "zone": "cooler"},
    {"id": "ice", "name": "Ice", "name_es": "Hielo", "unit": "bag", "zone": "freezer"},
    {"id": "cheese", "name": "Shredded cheese", "unit": "lb", "zone": "cooler", "aliases": ["queso rallado"]},
    {"id": "eggs", "name": "Eggs", "unit": "ea", "zone": "cooler"},
    {"id": "old", "name": "Old thing", "unit": "ea", "zone": "dry", "archived": True},
]


def lines(text, **kw):
    return voice.reconcile(text, ITEMS, **kw)["lines"]


def one(text):
    ls = lines(text)
    assert len(ls) == 1, ls
    return ls[0]


@pytest.mark.parametrize("text,item,qty", [
    ("ground beef 14", "beef", 14),
    ("ground beef fourteen", "beef", 14),
    ("14 pounds of ground beef", "beef", 14),
    ("ground beef 14 pounds", "beef", 14),
    ("ground beef two and a half", "beef", 2.5),
    ("ground beef 1/2", "beef", 0.5),
    ("ground beef twenty five point five", "beef", 25.5),
    ("ground beef 3.25", "beef", 3.25),
    ("ice six bags", "ice", 6),
    ("ice none", "ice", 0),
    ("eggs two dozen", "eggs", 24),
    ("shredded cheese 32 ounces", "cheese", 2),
    ("corn tortillas 2 cases", "corn", 24),
    ("ground beef too", "beef", 2),
])
def test_english_quantities(text, item, qty):
    ln = one(text)
    assert ln["status"] == "matched" and ln["item_id"] == item
    assert ln["qty"] == pytest.approx(qty)


@pytest.mark.parametrize("text,item,qty", [
    ("carne molida doce libras", "beef", 12),
    ("hielo veinte", "ice", 20),
    ("tenemos queso rallado cinco libras", "cheese", 5),
])
def test_spanish(text, item, qty):
    ln = one(text)
    assert ln["status"] == "matched" and ln["item_id"] == item and ln["qty"] == pytest.approx(qty)


def test_names_with_number_words_are_protected():
    ln = one("half and half two quarts")
    assert ln["item_id"] == "hh" and ln["qty"] == 2


def test_multi_clause_and_zones():
    r = voice.reconcile("freezer: ice 4. cooler: eggs 30", ITEMS)
    assert [(l["item_id"], l["zone"], l["qty"]) for l in r["lines"]] == [("ice", "freezer", 4), ("eggs", "cooler", 30)]
    assert set(r["zones_walked"]) == {"freezer", "cooler"}
    # missing only counts products in the areas you walked (OSBW behaviour), never archived ones
    missing = {m["item_id"] for m in r["missing"]}
    assert missing == {"beef", "hh", "cheese"}


def test_missing_scope_all():
    r = voice.reconcile("freezer: ice 4", ITEMS, scope="all")
    assert "corn" in {m["item_id"] for m in r["missing"]}
    assert "old" not in {m["item_id"] for m in r["missing"]}


def test_duplicates_are_summed():
    r = voice.reconcile("ground beef 3, then ice 4; ground beef 2", ITEMS)
    assert r["totals"]["beef"] == 5 and r["duplicates"] == {"beef": 2}


def test_ambiguous_and_unmatched_and_no_qty():
    assert one("tortillas 5")["status"] == "ambiguous"
    assert one("xyz widgets 4")["status"] == "unmatched"
    assert one("ground beef")["status"] == "no_qty"


def test_gap_tolerance_controls_apply():
    ok = voice.reconcile("ground beef 3, xyz 2, abc 1", ITEMS)
    assert ok["summary"]["unresolved"] == 2 and ok["can_apply"]
    bad = voice.reconcile("ground beef 3, xyz 2, abc 1, qqq 4", ITEMS)
    assert bad["summary"]["unresolved"] == 3 and not bad["can_apply"]


def test_unit_mismatch_flags_check():
    ln = one("ice 3 gallons")
    assert ln["status"] == "unit_check"


def test_empty_text():
    assert voice.reconcile("", ITEMS)["lines"] == []


def test_walk_build_uses_starter_catalog():
    from osft import starter_catalog
    r = voice.walk_build("cooler: ground beef 10 pounds, sour cream. freezer: ice", [], starter_catalog.CATALOG)
    names = {p["name"].lower(): p for p in r["proposals"]}
    assert any("beef" in n for n in names)
    assert all(p["action"] == "new" for p in r["proposals"])
    assert {"cooler", "freezer"} <= set(r["zones"])


def test_starter_catalog_has_no_prices_and_unique_ids():
    from osft import starter_catalog
    cat = starter_catalog.CATALOG
    assert len(cat) >= 300
    assert len({c["id"] for c in cat}) == len(cat)
    assert all(c.get("cost") is None for c in cat)
    assert all(c["category"] in starter_catalog.CATEGORIES for c in cat)
