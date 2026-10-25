# Open Source Food Truckin (OSFT)

Local-first food-truck inventory for operators. GPLv3. Flask + static UI. Port **5053**.
Free, runs on your own computer, no account, no subscription. English / Español.

**Version:** 1.3.0-beta (see `VERSION.txt`, `CHANGELOG.md`)

## Features

v1.0-beta — full Open Source Barware parity (see `PARITY.md`)
- **Speak your inventory** — Voice count in English or Spanish (Chrome, Edge or Safari; typing always works)
- Guided setup that builds your product list from a voice walk of the truck; "Load sample taco truck" for demos
- People & PIN logins (admin / manager / crew, per-permission, truck lock) — open until you create the first admin
- Accounts: categories with GL codes + target %, POS accounts · Vendors · Purchase orders by vendor with receiving
- 380-product starter list (no prices — enter your own) · CSV import/export · barcode scan (Chrome)
- Invoice entry · Input log · Money report (food cost %) · Multiple trucks + transfers · Crew board
- Backups, restore, reset


v0.1
- Setup (truck name, units, language) · Catalog with PAR/min, category, zone, cost per unit
- Storage map: cooler, freezer, dry, prep · Count walk by zone · Variance vs PAR and prior count
- Receive log → on-hand up · Low-PAR alerts on Home · Taco-truck demo data

v0.3
- Open Source Barware layout (sidebar, Home base, Inventory sheets tabs, Reports, All inputs) in the Food Truckin' comic look
- Order list grouped by vendor · big −/+ count steppers on phones

v0.2
- **Sales import from any POS** (Sales tab) — upload a CSV; Square, Toast, Clover formats are auto-detected,
  anything else works through column mapping. Preview first, then import.
- **Menu & recipe costing** (Menu tab) — cost per plate, food-cost %, margin.
- **Variance from sales** (Sales tab) — what you *should* have used vs. what the counts say you used.
- **Stop types & load list** (Stops tab) — PAR per stop type, printable load list for tomorrow.
- **Invoice photos** on receives, plus an optional AI reader (off by default, your own key).

## Count types (v1.3)

Settings › Count types has three kinds of count:
- **Daily end-of-shift:** a partial count of a watch list (sections, categories or picked products).
- **Weekly:** the full truck.
- **Monthly in-depth:** the full truck plus an extras checklist.

You pick the type and business date when you start a count. Crew logins can be limited to daily counts (People). A partial count only updates what it covers; everything else keeps its last count and is never zeroed or flagged missing. Count history shows type, scope and who counted.

## Reconcile edits (v1.3)

On setup step 4 you can tap any row to edit it: name, section, count, unit, pack, cost, vendor, delete, merge, link or unlink an invoice line. You can also add a missing product. Nothing saves until **Confirm & continue**.

## First run (v1.2)

The walk also takes your product invoices (PDF, photos, CSV, or typed lines). Step 4 **Reconcile** merges them with what you said, shows "Here's what I registered" per section, and asks what to do with invoice products that aren't in a section yet. Nothing saves until you confirm.

### v1.1 notes
Setup unfolds like Open Source Barware: Welcome (optional AI) → Your truck → Sections → Walk each section by voice → Approve map → First count by section → optional PIN.

## Library and Help (2026-10-25)
**Settings › Library** is the full manual, in English and Spanish, with search, learning paths and **Take me there** buttons. **Help** (bottom-right on every screen) answers questions from the Library for free. If you connect your own AI in Settings › AI, Help becomes a step-by-step tutor that also reads a short summary of your truck's numbers. It never changes anything. It can read answers aloud and take questions by voice. To edit the manual, change the Markdown in `library/en` and `library/es`, keeping the `{#topic-id}` anchors in the Spanish headings, then run `python -m pytest -q tests/test_library.py`.

## Optional AI
Settings › AI: pick ChatGPT, Claude, Grok, local Ollama or any OpenAI-compatible endpoint, paste your key, Test, turn on. AI reads invoice photos/PDFs and suggests shelf contents. It never saves anything on its own, and it is never called while switched off. The key stays in data/config.json and is left out of backups.

## Run

See `README-INSTALL.txt`, or:

```bash
cd program
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py          # this computer only → http://127.0.0.1:5053/
python server.py --lan    # also reachable from a phone on the same Wi-Fi (prints the URL)
```

`--lan` has no login: use it only on a trusted network (the truck's own hotspot / home Wi-Fi).

## POS adapters

| Adapter | Kind | Status |
|---|---|---|
| Generic CSV + column mapping | CSV | Works with any POS export that has item + qty columns |
| Square — Item Sales / Item Details | CSV | Columns from Square help docs — **unverified against a live export** |
| Toast — ItemSelectionDetails / Product Mix | CSV | Columns from Toast data-export docs — **unverified against a live export**; voids skipped |
| Clover — Item Sales report | CSV | **Unverified** (inferred); export has no dates → pick the sales date on import |
| Square / Toast / Clover live API | API | Documented stubs only (`fetch_sales` raises NotImplementedError) |

Add a POS: subclass `POSAdapter` in `osft/pos_adapters.py`, list header aliases in `columns`, add it to `ADAPTERS`.
Every adapter returns `[{date: "YYYY-MM-DD", menu_item, qty, price}]` (`price` = line total).
Sample files: `samples/*-EXAMPLE.csv` (hand-made, not real exports).

## How the sales variance works

For the period between the two latest **full** counts (daily partial counts in between are skipped; a product
counted only on a daily list uses its own last count):
`counted usage = start count + received − end count`, `theoretical = Σ (qty sold × recipe qty)`.
POS exports carry dates, not times. A "before service" count comes before that day's sales; an "end of shift"
count comes after them. Pick the timing per count type. Recipe qty is in the catalog item's own unit
(e.g. 0.04 *pack* of tortillas per taco) — no unit conversion yet.

## Week simulation

`python tests/sim_week.py http://127.0.0.1:PORT 40 short out.json` runs against a **fresh throwaway copy** (it creates logins and products). It opens with 10 of each product, imports POS sales that use 5 of each, has a crew login do two daily partial counts, then does a weekly full count, and checks on-hand, variance, food cost and the order list. See `../SIMULATION-REPORT.md`.

## Data

Everything is in `data/store.json` and `data/photos/`. Back up that folder. The AI key (if you add one) is stored
there in plain text and never sent to the browser.

## Tests

- `python -m pytest -q` (89 tests, AI mocked) · `python scripts/smoke.py http://127.0.0.1:5053` · browser walk-throughs on a **fresh copy**: `python tests/e2e_v11.py http://127.0.0.1:5053 ./shots m390 390 844` (new first run + AI against a local mock) and `python tests/e2e_v1.py http://127.0.0.1:5053 ./shots` (it creates an admin with PIN 123456 and loads sample data).

```bash
.venv/bin/python -m pytest -q tests        # unit + API tests (no server needed)
.venv/bin/python scripts/smoke.py          # v0.1 API smoke — WARNING: resets data/store.json
.venv/bin/python scripts/ui_smoke.py       # optional browser smoke (pip install playwright)
```

## License

GNU General Public License v3.0 or later (GPL-3.0-or-later), the same license as Open Source Barware.
Full text in `LICENSE.txt`; copyright and bundled font licenses in `NOTICE.md`.
