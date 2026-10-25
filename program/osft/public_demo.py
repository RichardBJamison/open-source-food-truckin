"""Public demo mode — only when the server runs with OSFT_PUBLIC_DEMO=1 (a copy shared on the internet).

Visitors can play with the sample truck: count, edit products, cost the menu, import a POS CSV, read the
Library. They can't lock the program with PINs, store an AI key, upload photos or invoices, restore,
erase, change trucks or the business profile, or restart setup. The sample data is put back from
OSFT_DEMO_SNAPSHOT (a copy of a clean data/ folder) at start and every OSFT_DEMO_RESET_HOURS (default 6).
A normal install never sets these variables, so none of this runs.
"""
from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

ENABLED = os.environ.get("OSFT_PUBLIC_DEMO") == "1"
SNAPSHOT = os.environ.get("OSFT_DEMO_SNAPSHOT") or ""
RESET_SECONDS = float(os.environ.get("OSFT_DEMO_RESET_HOURS") or 6) * 3600
MESSAGE = "This is the public demo, so this part is switched off. Download the program to use it for real."
KEEP = {".session_secret"}

# (method regex, path regex) pairs that are blocked
BLOCKED = [
    (r".*", r"^/api/people(/.*)?$"),
    (r".*", r"^/api/ai/(settings|test|invoice|shelf|tidy)(/.*)?$"),
    (r"PUT|POST|DELETE", r"^/api/settings/ai$"),
    (r"POST|PUT|DELETE", r"^/api/trucks(/.*)?$"),
    (r"POST|PUT|DELETE", r"^/api/transfers$"),
    (r"PUT", r"^/api/business$"),
    (r"POST", r"^/api/(reset|reset/all|restore|backups)$"),
    (r"PUT|POST", r"^/api/onboarding(/.*)?$"),
    (r"POST", r"^/api/setup/invoices$"),
    (r"POST", r"^/api/invoice/upload$"),
    (r"POST", r"^/api/receives/[^/]+/photos(/.*)?$"),
]


def blocked(method: str, path: str) -> bool:
    return ENABLED and any(re.fullmatch(m, method) and re.match(p, path) for m, p in BLOCKED)


_last = {"t": 0.0}


def restore(data_dir: Path, snapshot: str = "") -> bool:
    """Put the clean sample data back. Returns True when it copied anything."""
    src = Path(snapshot or SNAPSHOT)
    if not src.is_dir():
        return False
    data_dir.mkdir(parents=True, exist_ok=True)
    for p in data_dir.iterdir():
        if p.name in KEEP:
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    for p in src.iterdir():
        if p.name in KEEP:
            continue
        dest = data_dir / p.name
        shutil.copytree(p, dest) if p.is_dir() else shutil.copy2(p, dest)
    _last["t"] = time.time()
    return True


def maybe_restore(data_dir: Path) -> None:
    if ENABLED and SNAPSHOT and time.time() - _last["t"] >= RESET_SECONDS:
        restore(data_dir)
