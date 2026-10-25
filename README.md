# Open Source Food Truckin' (OSFT)

Free, open source (GPLv3) inventory software for food trucks — spin-off of [Open Source Barware](https://github.com/RichardBJamison/open-source-barware).

Speak your inventory section by section, reconcile invoices (optionally read by your own AI key), run daily partial / weekly full / monthly in-depth counts, and plug in any POS through CSV adapters. Runs locally on your Mac or PC; your data never leaves your computer. English and Spanish.

## Layout

| Folder | What it is |
|---|---|
| `program/` | The downloadable program (Python/Flask, port 5053). Install with `Install.command` (Mac) or `Install.bat` (Windows); see `program/README-INSTALL.txt`. |
| `site/` | The website generator (`build_site.py`, `i18n.py`) and static site. `site/server/serve_site.py` serves it with the email-gated download and download counter. Signups are saved to `contacts.db` and emailed to the owner (see `site/server/README.md`). |

## Develop

```
cd program
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest -q tests
.venv/bin/python server.py      # http://127.0.0.1:5053/
python3 scripts/package_release.py   # builds the Mac/Windows zips
```

## License

GPL-3.0-or-later, the same license as Open Source Barware. Full text in `LICENSE`; copyright and bundled font licenses in `NOTICE.md`.

Made by Intelligent Hospitality Systems (https://intelligenthospitalitysystems.com/) · Reservation Relief (https://www.reservationrelief.com/)
