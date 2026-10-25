"""Plug-and-play POS adapters for Open Source Food Truckin (OSFT).

Every adapter turns a POS export into *normalized sales lines*:

    {"date": "YYYY-MM-DD", "menu_item": str, "qty": float, "price": float}

``price`` is the line's total net sales (not unit price) when the export has it,
else unit price * qty, else 0.

Adding a POS = subclass ``POSAdapter`` and add it to ``ADAPTERS``.

Column names for Square / Toast / Clover come from their public help pages and
sample exports as of 2026. Columns marked ``verified=False`` have NOT been
checked against a real export file — confirm with a real file from the truck
before trusting them. All adapters match header names case-insensitively and
accept several aliases, and any file can still be imported with the generic
CSV adapter + column mapping UI.

GPLv3 — see LICENSE.txt.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime


class AdapterError(ValueError):
    pass


def _norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (h or "").strip().lower()).strip()


def parse_number(v) -> float:
    if v is None:
        return 0.0
    s = str(v).strip()
    if not s:
        return 0.0
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^0-9.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return 0.0
    try:
        n = float(s)
    except ValueError:
        return 0.0
    return -n if neg else n


DATE_FORMATS = (
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%b-%Y", "%b %d, %Y",
    "%m/%d/%Y %I:%M %p", "%m/%d/%Y %H:%M", "%m/%d/%y %I:%M %p", "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y %I:%M:%S %p", "%d-%b-%Y %I:%M %p",
)


def parse_date(v, default: str | None = None) -> str | None:
    s = str(v or "").strip()
    if not s:
        return default
    s2 = re.sub(r"(Z|[+-]\d{2}:?\d{2})$", "", s).strip()
    m = re.search(r"\s([A-Z]{2,5})$", s2)
    if m and m.group(1) not in ("AM", "PM"):
        s2 = s2[: m.start()].strip()  # drop "EDT", "UTC"…
    candidates = [s2, s2.split(" ")[0].split("T")[0]]
    for c in candidates:
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(c, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    if m:
        return m.group(1)
    return default


def read_csv(text: str) -> tuple[list[str], list[dict]]:
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.splitlines()
    # Some exports put a title/blank rows before the header: skip rows with <2 cells.
    start = 0
    for i, line in enumerate(lines[:15]):
        if line.count(",") >= 1:
            start = i
            break
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    headers = [h for h in (reader.fieldnames or []) if h is not None]
    rows = [r for r in reader if any((v or "").strip() for v in r.values() if isinstance(v, str))]
    return headers, rows


class POSAdapter:
    key = "base"
    label = "Base"
    kind = "csv"           # "csv" or "api"
    verified = False
    doc_url = ""
    notes = ""
    # field -> list of accepted header aliases (normalized form)
    columns: dict[str, list[str]] = {}
    required = ("menu_item", "qty")

    def describe(self) -> dict:
        return {
            "key": self.key, "label": self.label, "kind": self.kind,
            "verified": self.verified, "doc_url": self.doc_url, "notes": self.notes,
            "columns": self.columns, "available": self.kind == "csv",
        }

    def detect(self, headers: list[str]) -> dict[str, str]:
        """Return field -> actual header for this adapter's aliases."""
        normmap = {_norm(h): h for h in headers}
        found = {}
        for field, aliases in self.columns.items():
            for a in aliases:
                if _norm(a) in normmap:
                    found[field] = normmap[_norm(a)]
                    break
        return found

    def score(self, headers: list[str]) -> int:
        return len(self.detect(headers))

    def parse(self, text: str, mapping: dict | None = None, default_date: str | None = None) -> list[dict]:
        headers, rows = read_csv(text)
        if not headers:
            raise AdapterError("File has no header row.")
        m = dict(self.detect(headers))
        if mapping:
            m.update({k: v for k, v in mapping.items() if v})
        for f in self.required:
            if f not in m or m[f] not in headers:
                raise AdapterError(f"Could not find a column for '{f}'. Use the column mapping.")
        return self._rows_to_lines(rows, m, default_date)

    def skip_row(self, row: dict, m: dict) -> bool:
        return False

    def line_name(self, row: dict, m: dict, name: str) -> str:
        return name

    def _rows_to_lines(self, rows, m, default_date):
        out = []
        for r in rows:
            if self.skip_row(r, m):
                continue
            name = str(r.get(m["menu_item"]) or "").strip()
            if not name or _norm(name) in ("total", "totals", "grand total", "subtotal"):
                continue
            name = self.line_name(r, m, name)
            qty = parse_number(r.get(m["qty"]))
            if qty == 0:
                continue
            price = 0.0
            if m.get("net_sales"):
                price = parse_number(r.get(m["net_sales"]))
            elif m.get("price"):
                price = parse_number(r.get(m["price"])) * qty
            date = parse_date(r.get(m["date"]) if m.get("date") else None, default_date)
            out.append({"date": date, "menu_item": name, "qty": qty, "price": round(price, 2)})
        return out


class GenericCSVAdapter(POSAdapter):
    key = "generic_csv"
    label = "Any POS — spreadsheet (CSV) with column mapping"
    verified = True
    notes = "Works with any export that has one row per item (or per item per day). Map the columns once."
    columns = {
        "date": ["date", "sale date", "order date", "day", "business date"],
        "menu_item": ["menu item", "item", "item name", "name", "product", "description"],
        "qty": ["qty", "quantity", "qty sold", "quantity sold", "count", "units sold", "items sold", "sold", "units"],
        "price": ["price", "unit price", "item price"],
        "net_sales": ["net sales", "total", "amount", "sales", "revenue", "gross sales"],
    }


class SquareItemSalesAdapter(POSAdapter):
    key = "square"
    label = "Square — Item Sales / Item Details export"
    verified = False
    doc_url = "https://squareup.com/help/us/en/article/5072-summaries-and-trends"
    notes = ("Square Dashboard → Reports → Item Sales (or Transactions → Item Details) → Export. "
             "Column names from Square help docs/sample exports; NOT yet verified against a live file.")
    columns = {
        "date": ["Date"],
        "menu_item": ["Item", "Item Name"],
        "qty": ["Qty", "Items Sold", "Units Sold", "Quantity"],
        "price": ["Price"],
        "net_sales": ["Net Sales", "Gross Sales"],
        "variation": ["Price Point Name", "Variation"],
    }

    def line_name(self, row, m, name):
        # Square splits items by variation ("Price Point Name"): "Taco (Large)".
        var = str(row.get(m["variation"]) or "").strip() if m.get("variation") else ""
        if var and _norm(var) != "regular":
            return f"{name} ({var})"
        return name


class ToastItemSelectionAdapter(POSAdapter):
    key = "toast"
    label = "Toast — Item Selection Details / Product Mix export"
    verified = False
    doc_url = "https://doc.toasttab.com/doc/platformguide/adminItemSelectionDetailsCSV.html"
    notes = ("Toast Web → Reports → Data exports → ItemSelectionDetails.csv (one row per item sold), "
             "or Sales → Product mix export. Voided rows are skipped. NOT yet verified against a live file.")
    columns = {
        "date": ["Order Date", "Sent Date", "Business Date", "Date"],
        "menu_item": ["Menu Item", "Item", "Item Name"],
        "qty": ["Qty", "Quantity", "Item Qty", "Qty Sold"],
        "net_sales": ["Net Price", "Net Amount", "Net Sales"],
        "price": ["Gross Price", "Avg Price"],
        "void": ["Void?", "Voided", "Void"],
    }

    def skip_row(self, row, m):
        if m.get("void"):
            return str(row.get(m["void"]) or "").strip().lower() in ("true", "yes", "1", "y")
        return False


class CloverItemSalesAdapter(POSAdapter):
    key = "clover"
    label = "Clover — Item Sales report export"
    verified = False
    doc_url = "https://www.clover.com/help/view-item-sales-reports"
    notes = ("Clover Dashboard → Reports → Items → Export. Clover exports summary rows for the "
             "report's date range (no per-row date) — pick the sales date on import. "
             "UNVERIFIED: column names inferred from help pages; confirm with a real file.")
    columns = {
        "date": ["Date", "Order Date"],
        "menu_item": ["Name", "Item Name", "Item"],
        "qty": ["Quantity Sold", "# Sold", "Items Sold", "Quantity", "Qty"],
        "net_sales": ["Net Sales", "Amount", "Gross Sales", "Item Revenue"],
        "price": ["Price", "Item Price"],
    }


class LiveAPIStub(POSAdapter):
    """Documented placeholder for a future live API connection.

    A live adapter would implement ``fetch_sales(start_date, end_date, credentials)``
    and return normalized lines exactly like ``parse``. Credentials (OAuth token /
    API key) would be stored only in the local data/store.json, never sent anywhere
    but the POS vendor.
    """

    kind = "api"
    verified = False

    def parse(self, *a, **k):
        raise AdapterError(f"{self.label} is not built yet — export a CSV and use the CSV adapter.")

    def fetch_sales(self, start_date: str, end_date: str, credentials: dict) -> list[dict]:
        raise NotImplementedError(self.notes)


class SquareAPIStub(LiveAPIStub):
    key = "square_api"
    label = "Square — live API (planned)"
    doc_url = "https://developer.squareup.com/reference/square/orders-api/search-orders"
    notes = ("Plan: OAuth or personal access token → Orders API SearchOrders (location_ids, "
             "date_time_filter.closed_at) → each order.line_items[] gives name, variation_name, "
             "quantity, total_money → normalized lines.")


class ToastAPIStub(LiveAPIStub):
    key = "toast_api"
    label = "Toast — live API (planned)"
    doc_url = "https://doc.toasttab.com/openapi/orders/operation/ordersBulkGet/"
    notes = ("Plan: Toast partner/integration credentials (requires Toast approval) → "
             "Orders API /ordersBulk?businessDate= → checks[].selections[] (displayName, quantity, price).")


class CloverAPIStub(LiveAPIStub):
    key = "clover_api"
    label = "Clover — live API (planned)"
    doc_url = "https://docs.clover.com/dev/reference/ordergetorders"
    notes = ("Plan: merchant API token → GET /v3/merchants/{mId}/orders?expand=lineItems&filter=createdTime>= "
             "→ lineItems (name, price in cents, unitQty) → normalized lines.")


ADAPTERS: dict[str, POSAdapter] = {
    a.key: a for a in (
        GenericCSVAdapter(), SquareItemSalesAdapter(), ToastItemSelectionAdapter(),
        CloverItemSalesAdapter(), SquareAPIStub(), ToastAPIStub(), CloverAPIStub(),
    )
}


def get_adapter(key: str) -> POSAdapter:
    if key not in ADAPTERS:
        raise AdapterError(f"Unknown POS adapter '{key}'.")
    return ADAPTERS[key]


def guess_adapter(headers: list[str]) -> str:
    """Best CSV adapter for a header row (POS-specific wins ties over generic)."""
    best, best_score = "generic_csv", -1
    for key in ("square", "toast", "clover", "generic_csv"):
        a = ADAPTERS[key]
        d = a.detect(headers)
        if not all(f in d for f in a.required):
            continue
        s = len(d) + (1 if key == "toast" and "void" in d else 0)
        if s > best_score:
            best, best_score = key, s
    return best
