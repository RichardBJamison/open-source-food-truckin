Open Source Food Truckin' (OSFT) — Install / Run
=================================================
Version: see VERSION.txt
Program address after install: http://127.0.0.1:5053/   (bookmark it — that bookmark is the software)

REQUIREMENTS
  - Mac (macOS 11+) or Windows 10/11
  - Python 3.9 or newer (Mac usually offers to install it; Windows: python.org)
  - Internet the first time only (to fetch Flask). After that it runs offline.

MAC
  1. Double-click Install.command.
     Blocked? Open START-HERE-MAC.html in this folder — it shows the one-time "Open Anyway" step.
  2. Your browser opens the program. Bookmark it.
  Installs to ~/osft-program and starts at login. Start.command / Stop.command live there.

WINDOWS
  1. Double-click Install.bat.
     "Windows protected your PC"? Click More info -> Run anyway.
     No Python? The installer opens python.org: install it with "Add python.exe to PATH" checked, then run Install.bat again.
  2. Your browser opens the program. Bookmark it.
  Installs to %USERPROFILE%\osft-program and starts at login. Start.bat / Stop.bat live there.

LINUX / BY HAND
  ./install.sh      (runs in this folder; Ctrl+C stops it)

UPDATING
  Download the new version and run its installer again. Your data (osft-program/data) is kept.

DATA
  Everything is in osft-program/data (store.json, photos, backups). Back up that folder; nothing leaves your computer.
  Demo seed: "Load taco-truck demo" on the Home screen.

USE FROM A PHONE (same Wi-Fi)
  Stop the program (Stop.command / Stop.bat), then in osft-program run:
    Mac:      .venv/bin/python3 server.py --lan
    Windows:  .venv\Scripts\python.exe server.py --lan
  It prints a line like: Phone on the same Wi-Fi -> http://192.168.1.23:5053/
  Open that on the phone. Only do this on a network you trust. Allow Python through the firewall if asked.

TESTS (developers)
  .venv/bin/python -m pip install pytest && .venv/bin/python -m pytest -q tests

LICENSE
  GPL-3.0-or-later — full text in LICENSE.txt; notices in NOTICE.md.
