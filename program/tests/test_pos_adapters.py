from osft import pos_adapters as pos
from conftest import SAMPLES


def _read(name):
    return (SAMPLES / name).read_text(encoding="utf-8")


def test_square_export():
    text = _read("square-item-sales-EXAMPLE.csv")
    headers, _ = pos.read_csv(text)
    assert pos.guess_adapter(headers) == "square"
    lines = pos.get_adapter("square").parse(text)
    assert lines[0] == {"date": "2026-10-23", "menu_item": "Beef Taco", "qty": 3.0, "price": 10.5}
    assert lines[2]["price"] == 6.5  # Net Sales after discount, ($1.00) parsed


def test_toast_skips_voids():
    text = _read("toast-item-selection-details-EXAMPLE.csv")
    headers, _ = pos.read_csv(text)
    assert pos.guess_adapter(headers) == "toast"
    lines = pos.get_adapter("toast").parse(text)
    assert len(lines) == 2
    assert lines[0]["date"] == "2026-10-23" and lines[0]["qty"] == 2


def test_clover_skips_total_and_uses_default_date():
    text = _read("clover-item-sales-EXAMPLE.csv")
    headers, _ = pos.read_csv(text)
    assert pos.guess_adapter(headers) == "clover"
    lines = pos.get_adapter("clover").parse(text, default_date="2026-10-20")
    assert [l["menu_item"] for l in lines] == ["Beef Taco", "Chicken Burrito"]
    assert all(l["date"] == "2026-10-20" for l in lines)


def test_generic_with_mapping():
    text = "When,What,How many,$\n10/22/2026,Taco,5,17.50\n"
    a = pos.get_adapter("generic_csv")
    try:
        a.parse(text)
        assert False, "should need mapping"
    except pos.AdapterError:
        pass
    lines = a.parse(text, {"date": "When", "menu_item": "What", "qty": "How many", "net_sales": "$"})
    assert lines == [{"date": "2026-10-22", "menu_item": "Taco", "qty": 5.0, "price": 17.5}]


def test_square_variation_name():
    text = "Date,Item,Qty,Price Point Name,Net Sales\n2026-10-23,Horchata,2,Large,$10.00\n"
    assert pos.get_adapter("square").parse(text)[0]["menu_item"] == "Horchata (Large)"


def test_api_stubs_not_available():
    for k in ("square_api", "toast_api", "clover_api"):
        d = pos.ADAPTERS[k].describe()
        assert d["kind"] == "api" and d["available"] is False and d["doc_url"]
