# OSFT — Known gaps

## v0.2.0 (2026-10-24)

- Square/Toast/Clover CSV column names are from public docs and NOT verified with real exports — test with the friend's real file first; generic mapping is the fallback.
- Live POS API adapters are stubs only.
- AI invoice reader is untested against a live provider (no key used in dev); suggestions are display-only, not one-tap into receives.
- No unit conversion (case → each, lb → oz); recipe qty must be in the item's own unit.
- Costing = last received cost, not weighted average.
- Load list assumes one location (on hand = what's on the truck); no commissary-to-truck transfer yet.
- Sales variance uses date-only matching (see README).
- `--lan` mode has no login/PIN.
- HEIC photos are stored but most desktop browsers can't show the thumbnail (link still opens/downloads).

## v0.1.0-draft — gaps vs T-001–T-016

Updated: 2026-09-19 (local build at `/workspace/osft/program/`)

## Implemented enough for Tester matrix

| ID | Area | Status | Notes |
|----|------|--------|-------|
| T-001 | Server boots | Done | `GET /`, `GET /api/health` |
| T-002 | Empty inventory | Done | Empty state on home + catalog |
| T-003 | Create item | Done | Catalog form + `POST /api/items` |
| T-004 | Edit item | Done | Persists in `data/store.json` |
| T-005 | Delete item | Done | Soft-delete (archive); not hard wipe |
| T-006 | Validation | Done | 400 + clear `error` string; no 500 |
| T-007 | Install path | Done | `Install.command`, `Install.bat`, `install.sh`, `README-INSTALL.txt` |
| T-008 | Mobile layout | Done | Responsive CSS; viewport meta; no device lab yet |
| T-009 | Zones | Done | cooler/freezer/dry/prep + storage map UI |
| T-010 | Count walk | Done | Start → qty by zone → complete; latest on reload |
| T-011 | Variance | Done | vs PAR; vs prior when 2nd+ completed count exists |
| T-012 | Purchase/receive | Done | Log receive → on-hand up; home stats |
| T-013 | Low-PAR dashboard | Done | Alerts on home |
| T-014 | Demo seed | Done | 12 taco-truck items, all 4 zones |
| T-015 | i18n scaffold | Done | `en` + `es` stubs; locale switch |
| T-016 | Setup | Done | Truck name + units (+ locale); persists |

## Gaps / polish (not blockers for smoke)

1. **Hard delete** — T-005 is archive-only (intentional for count history). No purge UI.
2. **In-progress count resume** — Abandoned sessions marked abandoned; only one active in_progress. Fine for v0.
3. **i18n coverage** — ES stubs cover chrome strings; some dynamic English phrases remain (e.g. confirm dialogs, “Setup incomplete”).
4. **Units preference** — Stored and shown in Setup; does not auto-convert item unit labels (operators enter free-text units).
5. **Auth / multi-user** — Out of scope (no PIN).
6. **Automated browser E2E** — Smoke is API-level (`scripts/smoke.py`); Chrome/mobile matrix is Tester-owned.
7. **No git remote / no deploy** — Local path only, per Floor.

## Not in scope (deferred)

Barcode, smart PO, multi-venue/commissary, PIN, PWA/offline, public marketing site. (POS import + recipes shipped in v0.2.)

## v1.0.0-beta (2026-10-24)
- Voice needs Chrome / Edge / Safari (Firefox has no speech recognition) — typing works everywhere.
- Barcode scan needs Chrome (BarcodeDetector).
- Starter list pack sizes are typical, not checked against a real vendor catalog.
- GL codes ship blank; POS accounts are labels only.
- PO "email draft" opens the user's mail app; OSFT never sends mail.
- Update opt-in is stored on the device only.
- Spanish strings not yet reviewed by a native speaker.

## v1.1.0-beta (2026-10-24)
- **Real AI calls are unverified.** Every AI path was tested against a local mock that speaks the OpenAI-compatible `/chat/completions` format. Nothing was sent to OpenAI, Anthropic, xAI or Ollama. Anthropic is reached through its OpenAI-compatible endpoint (`/v1/chat/completions` with `x-api-key`); if your account or model rejects that, use "Other" with a proxy.
- Reading quality depends on the model you pick. It must accept images (for example gpt-4o-mini, claude-sonnet, grok-4, llama3.2-vision). Scanned PDFs with no text layer can't be read: take a photo of each page instead.
- The microphone uses the browser's speech recognition (Chrome, Edge, Safari). Firefox shows the typed box only. The browser tests use typed text, not a real mic.
- AI shelf photos are not stored. Invoice files are kept in data/photos.

## v1.2.0-beta (2026-10-24)
- **Real AI invoice reading is unverified** (tested with a local mock only). Reading quality depends on the model.
- **AI-off invoice reading is best effort.** CSV needs a header with a description/item/product column. PDF text is read line by line: lines like "CHICKEN THIGH 4x10LB 2 cs 58.20 116.40" or "2 cs Ground beef 4.89" work; multi-line descriptions, odd column orders and scans don't. Photos always need AI.
- Matching invoice names to spoken names is fuzzy. Very different names (e.g. "Crema" vs "Sour cream MX 1gal") show up as "not in any section" — use "Same as…" only when it's offered, or place it and merge later in Products.
- If you said a product in cases but the walk saved it in another unit, Reconcile doesn't flag that; check units on Approve map. *(Fixed in 1.3: unit-mismatch flag + edit on Reconcile.)*
- Invoice quantities in setup are not added to stock (the walk count is what's on the truck). Receiving still happens in Invoices/Receive.

## v1.3.0-beta (2026-10-24)
- **Recipe units aren't converted.** Recipe qty must be in the product's own unit, e.g. 0.25 lb per taco. A product bought by the case but used by the pound will show false variance until the units match.
- **A partial count is a snapshot of its scope only.** There is no running "perpetual" on-hand between counts, so sales don't lower on-hand until the next count.
- **Daily reports:** to see a daily count's usage, call `/api/variance/sales?end=<daily count id>`. There is no picker in the UI yet. The weekly report skips partial counts by design.
- The count-type "every N days" interval is a label and reminder hint only; nothing is scheduled.
- **Simulations ran through the HTTP API on throwaway copies.** The browser screenshots are read-backs, not clicks through the whole week. The count-type UI flow itself (settings, crew login limited to daily, scoped walk, history, ES) is clicked through in `tests/e2e_counts.py`.
- Real AI and a real microphone are still unverified (mocked or typed in tests).
- `tests/sim_week.py` needs `requests`, which is a dev-only dependency and not in requirements.txt.
- Spanish strings have not been reviewed by a native speaker.

## 1.3.0-beta update — Library + Help (2026-10-25)
- **The AI tutor was tested against a local mock** of the OpenAI-compatible API, not a real provider. Answer quality depends on the model you connect.
- Without AI, Help answers by search: it shows the best-matching Library topic. It can't combine several topics or answer a question the Library doesn't cover.
- Voice questions and read-aloud use the browser's speech features: Chrome, Edge and Safari listen; read-aloud voices depend on the device.
- The Spanish manual hasn't been reviewed by a native speaker yet.
