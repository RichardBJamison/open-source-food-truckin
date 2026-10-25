# Changelog — Open Source Food Truckin (OSFT)


## 1.3.0-beta update — 2026-10-25 (Settings thank-you popup + pitch box)

- Settings opens a thank-you popup (EN/ES): Open Source Barware is free to download and includes Reservation Relief and Nexus web design; IHS builds a custom site or migrates yours for $300, Nexus included. Reservation Relief logo links to https://www.reservationrelief.com/, IHS link to https://intelligenthospitalitysystems.com/.
- "Do not open again" checkbox (saved in this browser, localStorage `osft_promo_hide`); Close button, X, Esc, click-outside; focus trapped while open.
- Bottom of Settings: the Open Source Barware "More from the same house" pitch box, now with clickable Reservation Relief and IHS logos, a $300-websites card and a "Show the thank-you note" button. Replaces the old box (no duplicate).
- New: static/js/promo.js, static/img/reservation-relief-logo.png, static/img/ihs-logo.png, tests/test_settings_promo.py.

## 1.3.0-beta installers — 2026-10-25 (Mac + Windows downloads · full license)

### Added
- **Mac zip** (`osft-1.3.0-beta-mac.zip`): double-click `Install.command`. It copies the program to `~/osft-program`, sets up Python, starts it at every login, and opens it in the browser. `Start.command` / `Stop.command` live in that folder. `START-HERE-MAC.html` covers the one-time macOS "Open Anyway" step (macOS 15+ removed right-click → Open) and a Terminal route.
- **Windows zip** (`osft-1.3.0-beta-win.zip`): double-click `Install.bat` → `%USERPROFILE%\osft-program`, a Startup shortcut, and the browser opens. If Python is missing it opens python.org and says to tick "Add python.exe to PATH". If it's run from inside the zip it says to Extract All first.
- Re-running either installer updates the program and keeps `data/`.
- `scripts/package_release.py` builds both zips. It refuses to build if a required file is missing or a Windows script isn't ASCII, and writes `.ps1` with a BOM and CRLF.
- `NOTICE.md`, plus the font licenses (Roboto, OFL 1.1; Luckiest Guy, Apache 2.0) in `static/fonts/`.

### Changed
- `LICENSE.txt` is now the full GNU GPLv3 text (it was only the short notice). The license is GPL-3.0-or-later, the same as Open Source Barware.
- Python 3.9+ is supported, the version macOS ships with (all 118 tests pass on 3.9).
- The server's startup lines are ASCII only. On Windows the installer sends them to a log file, and non-ASCII crashed Open Source Barware there. These Barware lessons are built in: ASCII + BOM + CRLF PowerShell, separate stdout/stderr logs, a curl.exe health-check fallback, 127.0.0.1 instead of localhost, and the log tail shown on failure.

## 1.3.0-beta update — 2026-10-25 (Library + Help tutor)

### Added
- **Settings › Library.** The whole manual inside the program: 20 chapters and 101 topics, in English and Spanish, covering setup, sections, products, counting, voice counts, count types, receiving, ordering, POS sales, menu costing, reports, stops, trucks, people, business settings, AI, backups, troubleshooting and a glossary. It has a contents list, search, eight learning paths, and a **Take me there** button on every chapter that opens the screen it describes. The source is plain Markdown in `library/en` and `library/es`.
- **Help, bottom-right on every screen.** Ask in plain words, or tap 🎙️ to ask by voice. With AI off it answers straight from the Library in the browser: free, and nothing is sent anywhere. With your own AI connected (Settings › AI) it becomes a tutor. It sends your question, the Library pages it found, and a short read-only summary of the truck (product, count, PAR, order and sales numbers; no PINs, keys or contact details) to your AI, then teaches step by step in your language. Follow-up questions keep the pages from the question before.
- **🎓 Teach me this path.** Walks a learning path one step at a time inside Help, with **Take me there** and **Next step**.
- **🔊 Voice.** Help can read its answers aloud in English or Spanish (the browser's own speech). This is off by default and remembered on the device.
- API: `GET /api/library/<en|es>` returns the manual plus AI on/off. `POST /api/library/ask {question, lang, refs, history, view}` returns `{mode: "ai", answer, sources}`, or `{mode: "off"}` when AI is off. Any login can use both; neither writes data.
- The program page now tells browsers not to auto-translate it, because it has its own EN/ES switch. It also honours `?lang=es` (used by the website's live demo).
- Tests: `tests/test_library.py` (manual links, EN/ES topic parity, chapter screens exist, AI on/off, prompt contents, no secrets). 100 unit/API tests in total.

## 1.3.0-beta — 2026-10-24 (Edit on the Reconcile step · daily / weekly / monthly counts · week simulations)

### Added
- **Edit right on step 4 Reconcile.** You don't have to go back to the walk any more. Tap any row (✎) in "Here's what I registered", or any invoice product in "not in any section", and a drawer opens (a bottom sheet on phones). From there you can:
  - change the name, section (move it), spoken count, unit, pack, cost and vendor;
  - delete the product, or merge it into another one;
  - unlink an invoice line from a product, or link it to a different one;
  - add a missing product to any section ("＋ Add product").
  Edits stay pending: the stats and flags update live, a banner shows what's pending (with "Undo all edits"), and deleted products can be restored. Nothing saves until **Confirm & continue**.
- **Unit-mismatch flag.** "⚑ unit differs" now fires whenever your unit and the invoice unit differ (cases vs lb included), with a one-tap "use invoice unit". This fixes "cases saved as lb".
- **Count types (Settings › Count types):**
  - Daily end-of-shift: a partial count. Its scope can be any mix of sections, categories and a watch list of picked products. The default scope is protein categories.
  - Weekly: the full truck, and it can leave sections out (for example commissary).
  - Monthly in-depth: the full truck plus an extras checklist (default: commissary storage, paper & supplies, propane, waste review).
  - Each type has a timing (before service, or end of shift after that day's sales) and an "every N days" interval. This mirrors OSBW's weekly/monthly count cycle and its station-scoped counts.
- **Scoped count walk.** You pick a count type and a business date before starting. A crew member doing a daily count sees only the products in that scope. A banner explains what the count covers, and monthly counts show the extras checklist.
- **Partial counts never zero or flag what they skip.** Products outside the scope, or left blank in a partial count, keep their last known on-hand. "Missing" is only reported for blanks inside a full count's scope.
- **Count history** on the Count sheet, the Money report and `GET /api/counts/history`. Each entry shows business date, type, scope, who counted, and products counted against products in scope.
- **Per-login count types.** People › "Count types this person can start" lets you, for example, limit crew to Daily. This is enforced by the server (403).
- API additions:
  - `GET/PUT /api/count-types`.
  - `POST /api/counts/start` takes `{type, date, timing}`.
  - Sessions now carry `type`, `type_name`, `business_date`, `timing`, `scope{full,label,item_ids,checklist}`, `counted_by`, `checklist_done` and `summary`.
  - `PUT /api/counts/<id>` rejects products outside a partial count's scope.
  - Reconcile edits: `POST /api/setup/reconcile/pending` with ops edit, delete, restore, merge, link, unlink, add and reset.
- **Settings › Business: "More from the same house" panel** (always on, EN/ES). This mirrors the panel Open Source Barware added on 2026-10-24: it promotes Reservation Relief 2026 and the IHS tools and links to reservationrelief.com and intelligenthospitalitysystems.com. It is adapted to the truck program: it promotes Open Source Barware instead of food-truck inventory, and the Reservation Relief card talks about catering and event bookings. It uses the comic-panel style. Links open only when clicked; nothing loads from those sites in the background.
- **Week simulations against the real server:** `tests/sim_week.py` and `SIMULATION-REPORT.md`. Two scenarios (10 products, and 40 products across 5 sections with 13 menu items), each run exact and with 2 products short.
- Tests: `tests/test_v13.py` (Reconcile edits) and `tests/test_v13_counts.py` (count types, scope, roles, variance math), 89 unit/API tests in total. Browser tests: `tests/e2e_v13.py` and `tests/e2e_counts.py` (390px and 1440px).

### Fixed (found while building the count types and running the simulations)
- **Sales variance used "the last two counts".** A daily partial count between two weekly counts became the start of the weekly report, which dropped most products and mis-stated usage. Now the default report runs from the previous full count to the latest full count. Partials in between are skipped and listed, and a product counted only on a daily list uses its own last count.
- **Variance vs prior** compared against the last session, even when that session never counted the product. It now uses each product's last count that actually included it.
- **The food-cost % sales window** used a different date rule from the usage math. It now uses the same timing-aware window: before service, or end of shift including that day's sales.
- Counts are ordered by business date, so a count entered late for an earlier day lands in the right place.
- Generic POS CSV: a "Sold" or "Units" column is now recognized as quantity. The bundled `samples/generic-EXAMPLE.csv` uses "Sold" and failed without the column mapping.
- After finishing a count, a crew login without Reports access was sent to Variance and got a 403. It now stays on the count screen with a summary.
- Switching language as a crew login tried to save the shop-wide setting (403). The language is now kept on that device.

## 1.2.0-beta — 2026-10-24 (Invoices in the setup walk + Reconcile step)

### Added
- **Product invoices in the walk:** the walk intro now asks for recent product invoices, and the same spot where you speak each section takes uploads — one or many PDFs, photos (camera button on phones) or CSV files. With AI on, each invoice is read into lines (vendor, qty, unit, cost). With AI off, CSV files and PDFs with a text layer are read as best effort, and you can type or paste lines ("2 cs Ground beef 4.89"); the screen says plainly that photos and scanned PDFs need AI. Invoices are a draft: uploading never creates or changes products.
- **New step 4 "Reconcile your map"** (OSBW's Pass 1 reconcile position: Walk → Reconcile → Approve map). It merges spoken products with invoice lines (fuzzy match, the same product across invoices de-duplicated: quantities add up, latest cost wins) and shows:
  - a stat row (sections · products · invoices · on an invoice · to place · no cost yet) and the summary "N of N products matched an invoice · N invoice products to reconcile on the map";
  - **"Here's what I registered"** per section: product, count spoken, from invoice yes/no (vendor, pack), cost, status (✓ verified / ⚑ no cost yet / ⚑ unit differs);
  - **"On your invoices but not in any section"**: instruct each one — put in a section, new section, same as an existing product (when it's a close match), commissary only, not stocked on truck, or skip for now — with select-all and bulk actions;
  - **"Spoken but not on any invoice"**: flagged "no cost yet".
  Nothing is saved until **Confirm & continue**. Confirm carries cost, pack size, unit (when the walk left it as "ea"), vendor (created if new) and the invoice spelling (as another name) onto matched products, and creates the placed ones with 0 on hand. "Commissary only" products go in a "Commissary (not on truck)" section; "Not stocked" items aren't asked about again; skipped ones are.
- API: `GET/POST /api/setup/invoices`, `POST /api/setup/invoices/text`, `DELETE /api/setup/invoices/<id>`, `GET /api/setup/reconcile` (proposal, saved:false), `POST /api/setup/reconcile/apply`. Onboarding phases now: welcome, business, sections, walk, **reconcile**, review, first_count, account, done.
- Tests: tests/test_v12.py (6 tests: AI upload, merge/de-dupe, unplaced instructions, commissary/skip/same-as, AI-off CSV/photo/typed, PDF-text layouts) and tests/e2e_v12.py (browser, 390px + 1440px). 81 unit/API tests total.

## 1.1.0-beta — 2026-10-24 (First run like OSBW, truck sections, optional AI)

### Added
- **First run in the OSBW order:** Welcome (two passes + optional "Connect AI") → 1 Your truck (name, count cycle) → 2 Sections → 3 Walk, one section at a time → 4 Review & approve map → 5 First count, section by section → 6 Lock it (optional owner PIN) → done.
- **Truck sections you define:** add, rename, reorder, delete, with food-truck ideas to tap (Cooler, Lowboy, Line / make table, Dry shelf 1/2, Window, Cab, Propane rack, Paper & to-go, Drinks cooler, Commissary). Deleting a section that still holds products asks where to move them. Also in Settings › Sections. Section names show everywhere zones did.
- **Settings › AI (optional, off by default):** ChatGPT (OpenAI), Claude (Anthropic), Grok (xAI), local Ollama, or any OpenAI-compatible endpoint. Model, Test connection, on/off. The key stays on this computer, is never sent back to the browser, and is left out of backups.
- **Invoice upload:** choose PDF or image files (up to 6) or take a photo. With AI on, "Read with AI" fills in vendor, invoice #, date and lines (qty, unit, cost). You check every line, match it to a product or add a new one, then save to receiving and costs. With AI off, the file is still attached to the receive you type in.
- **AI shelf building:** in the walk, "Photo → AI" suggests products and amounts for that section from a picture, and "Tidy with AI" cleans up a messy spoken list. Nothing is saved until you press "Add to <section>".
- API: `/api/sections` (GET/PUT, per-section count), `/api/ai`, `/api/ai/settings`, `/api/ai/test`, `/api/ai/invoice`, `/api/ai/shelf`, `/api/ai/tidy`, `/api/invoice/upload`; `/api/receives/batch` accepts `photos` and `new_item` lines.
- Tests: tests/test_v11.py (13 tests, mocked AI server) and tests/e2e_v11.py (browser first run + AI with a local mock, 390px and 1440px). 75 unit/API tests total.

### Changed
- Owner PIN moved to the end of setup (OSBW has no login step in setup); it's still optional.
- The old "AI invoice reading" box in Settings › Business moved to Settings › AI; existing keys carry over.
- Voice matching: words in brackets now count, so "chicken thighs" no longer matches "Chicken (whole)".

### Security
- Backups (`/api/backup`) no longer contain the AI key; restoring a backup keeps your current key.

## 1.0.0-beta — 2026-10-24 (Full Barware parity)

### Added
- **Speak your inventory:** Voice count screen (browser speech in English or Spanish, or type), check what we heard, fix misheard lines, keep or zero items you didn't mention, save and jump to variance.
- **Guided setup:** welcome → your truck → your login → walk your truck by voice → review pars → first count. "Load sample taco truck" for demos.
- **People & access:** admin / manager / crew, 6-digit PIN login with on-screen keypad, per-permission switches, lock a person to one truck.
- **Accounts:** categories with GL code, kind and target %; POS accounts.
- **Products:** starter list of 380 food-truck products (no prices), CSV import/export, Spanish name, SKU, barcode (scan in Chrome), case size, pack, vendor, other names.
- **Orders:** build POs by vendor from the order list, copy / email draft / CSV, mark sent, receive with shorts.
- **Invoice entry, input log, money report** (food cost %, by category, stock value, count history, CSV exports).
- **Multiple trucks** with stock transfers, **crew board**, **vendors**, **business profile + logo**, extra zones.
- **Data:** backups, download, restore, reset truck, erase everything.
- PARITY.md, browser walk-through test (tests/e2e_v1.py), 46 new unit/API tests (62 total).

### Changed
- Fonts are bundled (no outside requests). Footer no longer shows a port.

## 0.3.0 — 2026-10-24 (Barware layout, Food Truckin' look)

### Changed
- **Layout now mirrors Open Source Barware's app:** left sidebar with icon + title + one-line hint
  (Home base · Inventory sheets · Reports · On the truck · All inputs · Menu & costing · Stops & load lists · Settings),
  a header on every screen (eyebrow, big title, one-line purpose), and workbook tabs inside groups
  (Inventory sheets: Count sheet / Variance / Order list / Product master; All inputs: POS sales / Invoices & receiving).
  On phones the sidebar becomes a slide-out drawer (hamburger, tap-outside or Esc to close).
- **Home base dashboard** like OSBW's: hero with the CRAZY EATS! truck art, clickable metric tiles
  (items, below PAR, stock value, receives, menu items, sales imports, stop types) and a "Jump to" grid of nav cards
  with a big "Count walk" card.
- **Count sheet** like OSBW's mobile count: big −/+ steppers per item and a sticky Start/Complete bar on phones.
- **Reports** screen now holds sales-vs-count variance (moved from the Sales screen).
- **Look:** night navy, neon orange/teal, string lights, Luckiest Guy + Roboto, art from the OSFT site;
  every box is a comic panel (ink border, hard offset shadow, halftone dots, caption tags, speech-bubble alerts).
- Remaining hard-coded English on Home, Count and Variance moved to the locale files; Spanish complete.

### Added
- **Order list** (`GET /api/reorder`, mirrors OSBW's Order Generator): everything under PAR with qty to order and cost,
  grouped by the last vendor it was received from; printable.
- `/api/dashboard` also returns `inventory_value`, `menu_count`, `stop_count`, `sales_import_count`.
- `scripts/ui_smoke.py` rewritten for the new navigation: every screen at 390px and 1440px, overflow check,
  sales import, photo receive, stepper, Spanish, print page.

## 0.2.0 — 2026-10-24 (demo build for a test truck)

### Added
- **Plug-and-play POS import** (`osft/pos_adapters.py`): one adapter interface that turns any export into
  normalized sales lines (`date, menu_item, qty, price`). Adapters: Generic CSV with a column-mapping UI,
  Square Item Sales, Toast Item Selection Details, Clover Item Sales. Format auto-detect, preview before import,
  delete an import. Live API adapters for Square / Toast / Clover are documented stubs (not functional).
- **Menu & recipe costing**: menu items built from catalog items with qty per plate; cost per plate,
  food-cost %, margin $ and %. Items now have an optional cost per unit (also updated from receives — last cost).
  Each menu item can list the names it uses in the POS, so imported sales link to it.
- **Variance from sales**: theoretical usage (sales × recipes) vs. counted usage
  (start count + received − end count) between the last two completed counts, with $ impact and a list of
  unmatched POS items.
- **Stop types + load list**: lunch / brewery / festival … each with its own PAR per item (blank = everyday PAR);
  on-screen load list for tomorrow's stop plus a printer-friendly page (`/print/loadlist/<id>`), EN/ES.
- **Receive photos**: attach an invoice/receipt photo (phone camera) to a receive; stored in `data/photos/`.
  Receives also record vendor and unit cost.
- **Optional AI invoice reading** (`osft/ai_reader.py`): OFF by default; uses the operator's own API key with an
  OpenAI-compatible endpoint; returns suggestions only — never auto-applies. Key is never sent to the browser.
- **Phone on Wi-Fi**: `python server.py --lan` (or `OSFT_LAN=1`) listens on the network and prints the phone URL.
- Demo seed extended (all marked EXAMPLE): item costs, 4 menu items, 3 stop types, 2 counts, a receive and a
  day of sales — so every new screen has data; beef is over-portioned 15% to show variance.
- Spanish strings for all new UI. Sample POS CSVs in `samples/`. pytest suite in `tests/`,
  optional browser smoke `scripts/ui_smoke.py`.

### Changed
- Version 0.1.0-draft → 0.2.0. `/api/settings` and `/api/dashboard` now hide the AI key.

## 0.1.0-draft — 2026-09-19
Setup, catalog with PAR, storage zones, count walk, variance vs PAR/prior, receive log, low-PAR alerts,
taco-truck demo, EN + ES scaffold.
