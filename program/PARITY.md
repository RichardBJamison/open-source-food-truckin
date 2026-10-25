# OSFT v1.1.0-beta — parity with Open Source Barware (OSBW)

Same backend behaviour as OSBW, food-truck words, comic look. Status: **Done** = built and tested,
**Partial** = works with a stated limit, **Not done** = not in this build.

| OSBW feature | OSFT equivalent | Status | Notes |
|---|---|---|---|
| Guided first-run setup | Onboarding wizard: welcome → truck → login → walk your truck → review → first count → done | Done | Can re-run from Settings › Business |
| Sample venue | "Load sample taco truck" (welcome screen and Settings › Data) | Done | Everything it adds is marked EXAMPLE |
| Speak your inventory (voice count) | Inventory sheets › Voice count | Done | Browser Web Speech (Chrome/Edge/Safari), EN + ES; typing box always works too. Parser has 27 unit tests |
| Voice "walk the bar" to build the list | Walk your truck: say zone + items, we propose products | Done | Matches existing items or the starter list |
| Reconcile map before approve (Pass 1 wrap-up, flags, "not on your map" → add / ignore) | Setup step 4 Reconcile: spoken × invoices, "Here's what I registered", place / new section / same as / commissary only / not stocked / skip, bulk, no cost yet flags | Done (v1.2) | OSBW reconciles bottles at count time; OSFT also brings invoices into setup |
| Review heard lines / fix misheard | Check what we heard: matched / which one? / not found, pick item, ignore, not-said → keep or zero | Done | |
| Count sheet (big +/- steppers) | Inventory sheets › Count sheet | Done | From v0.3 |
| Count cycle (weekly / monthly) + station-scoped counts ("missing" only inside the stations counted) | Settings › Count types: daily end-of-shift (partial: sections / categories / watch list), weekly full, monthly in-depth (+ extras checklist); scoped walk; count history with type · scope · who; crew can be limited to daily | Done (v1.3) | OSFT adds the daily partial count; partials never zero what they skip and the weekly sales variance skips them |
| Settings sister-product promo (IHS + Reservation Relief, always on) | Settings › Business: "More from the same house" panel | Done (v1.3) | Mirrors OSBW 2026-10-24; points at Barware instead of food-truck inventory |
| Edit while reconciling | Reconcile step: edit / move / delete / merge / link / unlink / add, pending until Confirm | Done (v1.3) | |
| Variance | Inventory sheets › Variance + Reports | Done | |
| Order list (below PAR) | Order list + CSV | Done | |
| Purchase orders by vendor | Orders: make POs per vendor, copy text, email draft, CSV, mark sent, receive (with shorts) | Partial | "Email draft" opens your mail app; nothing is sent by OSFT |
| Product master | Product master: add / edit / archive, search, Spanish name, SKU, barcode, case size, pack, vendor, other names | Done | |
| Starter catalog | Starter list: 380 common food-truck products | Done | **No prices, no pars** — you fill those in |
| Import / export products | CSV import (upload or paste, template), CSV export | Done | Matching names update |
| Barcode lookup | Scan button on product form | Partial | Needs Chrome (BarcodeDetector); otherwise type the code |
| Invoices / receiving | All inputs › Invoice (typed lines, matched to products, updates cost) + receives | Done | Photo AI reader from v0.2 still untested with a live key |
| POS sales import | All inputs › POS sales (Square / Toast / Clover / generic CSV) | Partial | Column maps from public docs; not verified on real exports |
| Input log | All inputs › Input log (sales, invoices, purchases, POs, transfers) | Done | |
| Money / COGS | Reports › Money: food cost %, ideal %, by category vs target, stock value, count history, exports | Done | Needs sales + 2 counts to show food cost |
| Accounts: categories + GL codes | Settings › Accounts: categories with GL code, kind, target % | Done | GL codes ship blank |
| POS accounts | Settings › Accounts: POS accounts, default | Done | Labels only, no live API |
| Zones / storage areas | Cooler, freezer, dry, prep + optional outside, window, commissary | Done | |
| Multiple venues | Trucks: add / rename / switch / delete, copy products, transfer stock | Done | Each truck has its own data file |
| Staff board | On the truck › Board: notes, pin, per-truck | Done | |
| People & PIN logins | Settings › People: admin / manager / crew, 6-digit PIN, per-permission toggles, truck lock, reset PIN | Done | Open until the first admin with a PIN exists |
| Business profile + logo | Settings › Business: name, legal name, address, phone, email, site, time zone, count cycle, logo | Done | |
| Backups / restore / reset | Settings › Data: backup now, download, restore, reset truck, erase all (type RESET) | Done | Auto-backup before every reset/restore |
| Bilingual | English / Spanish everywhere (locale files) | Done | Spanish is mine — have a native speaker skim it |
| Phone-friendly | Checked at 390 px and 1440 px, no sideways scroll | Done | |
| Bottle weigh mode | — | N/A | Bar-only (partial bottles). Food uses units/cases |
| Menu / plate costing | Menu (from v0.2) | Done | |
| Stops & load lists | Stops (from v0.2) | Done | Food-truck extra, not in OSBW |
| Hosted cloud accounts / sync | — | Not done | OSFT is local-first: runs on your own computer |
| Update notices | Opt-in checkbox | Partial | Saved on this device only; nothing is sent |

## v1.1 — first run matches OSBW setup.html

| OSBW setup | OSFT v1.1 first run |
|---|---|
| Welcome: "let's map your bar", two passes, optional AI connection (Claude/ChatGPT/Grok/Other, key on this computer), Skip | Welcome: "let's map your truck", Pass 1 / Pass 2 cards, optional "Connect AI" (ChatGPT/Claude/Grok/Ollama/Other, key on this computer), Begin setup / sample truck |
| Step 1 · Get started — Your operation (name, cycle) | Step 1 · Your truck (name, weekly / every 2 weeks / monthly) |
| Step 2 · Pass 1 — Walk the bar (voice / paste, how to speak, examples) | Step 2 · Sections (define the truck), then Step 3 · Walk one section at a time (mic or typed, how to speak, examples, optional AI photo / tidy) |
| Step 3 · Reconcile, Step 4 · Review layout (stations: reorder, rename, remove, add) | Sections editor (add / rename / reorder / delete) plus the per-section check table |
| Step 5 · Approve map | Step 4 · Review & approve map (rename, move, PAR) |
| Step 6 · Pass 2 — First live count, station by station | Step 5 · First count, section by section (voice fills the numbers, you save) |
| (no login in setup) | Step 6 · Lock it — optional owner PIN |
