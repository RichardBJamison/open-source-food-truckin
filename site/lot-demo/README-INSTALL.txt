Open Source Food Truckin (OSFT) — Install / Run
================================================
Version: see VERSION.txt
Default URL: http://127.0.0.1:5053/

REQUIREMENTS
  - Python 3.10+ (python3 on Mac/Linux, python on Windows)
  - No internet needed after first pip install of Flask

QUICK START (any OS)
  cd program
  python3 -m venv .venv
  # Mac/Linux:
  source .venv/bin/activate
  # Windows:
  .venv\Scripts\activate
  pip install -r requirements.txt
  python server.py

ONE-CLICK / SCRIPT
  Mac:     double-click Install.command  (or run ./Install.command)
  Windows: double-click Install.bat
  Linux:   ./install.sh

Then open a browser to:
  http://127.0.0.1:5053/
  Health check: http://127.0.0.1:5053/api/health

DATA
  Inventory JSON lives in program/data/store.json (created on first run).
  Demo seed: use “Load taco-truck demo” on the Home screen.

USE FROM A PHONE (same Wi-Fi)
  python server.py --lan
  The terminal prints a line like: Phone on the same Wi-Fi -> http://192.168.1.23:5053/
  Open that on the phone. No password: only do this on a network you trust.
  (If it doesn't load, allow Python through the computer's firewall.)

STOP
  Ctrl+C in the terminal running the server.

TESTS
  .venv/bin/python -m pip install pytest && .venv/bin/python -m pytest -q tests

SMOKE TEST (WARNING: wipes data/store.json)
  With the server running:
    .venv/bin/python scripts/smoke.py
