#!/usr/bin/env python3
"""Build the Mac and Windows download zips from this folder.

  python3 scripts/package_release.py [OUT_DIR]      (default: ../../packages)

Writes osft-<version>-mac.zip and osft-<version>-win.zip, each with one top folder osft-<version>/.
Windows scripts are written ASCII-only with CRLF and (.ps1) a UTF-8 BOM — Windows PowerShell 5.1 fails
on anything else (the Open Source Barware v1.5.1 lesson). Mac scripts keep LF and the executable bit.
Refuses to build if a required file is missing (Barware once shipped start.command vs Start.command).
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").split()[0]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT.parent.parent / "packages")
TOP = "open-source-food-truckin-program"  # same pattern as open-source-barware-program/

SKIP_DIRS = {"data", ".venv", "__pycache__", ".pytest_cache", ".git", "tests"}
SKIP_TOP = {"SIMULATION-REPORT.md", "PARITY.md", "KNOWN-GAPS.md", "scripts/smoke.py", "scripts/ui_smoke.py", "scripts/package_release.py"}
SKIP_FILES = {".DS_Store", ".gitignore", ".gitattributes"}
WIN_ONLY = {"Install.bat", "install.ps1", "Start.bat", "Stop.bat", "start-server.ps1"}
MAC_ONLY = {"Install.command", "Start.command", "Stop.command", "START-HERE-MAC.html", "install.sh"}
COMMON = {"server.py", "requirements.txt", "VERSION.txt", "LICENSE.txt", "NOTICE.md", "README.md",
          "README-INSTALL.txt", "osft/__init__.py", "static/index.html", "static/js/app.js",
          "static/js/library.js", "library/en", "library/es", "locales/en.json", "locales/es.json",
          "static/fonts/LICENSE-Roboto-OFL-1.1.txt", "static/fonts/LICENSE-LuckiestGuy-Apache-2.0.txt"}


def files():
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if p.is_dir() or rel.parts[0] in SKIP_DIRS or any(x in SKIP_DIRS for x in rel.parts) or p.name in SKIP_FILES or ".bak" in p.name or rel.as_posix() in SKIP_TOP:
            continue
        yield rel


def win_text(rel: Path) -> bytes:
    text = (ROOT / rel).read_text(encoding="utf-8-sig")
    bad = [i + 1 for i, line in enumerate(text.splitlines()) if not line.isascii()]
    if bad:
        sys.exit(f"{rel}: non-ASCII on lines {bad} (breaks Windows PowerShell 5.1)")
    body = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii")
    return (b"\xef\xbb\xbf" + body) if rel.suffix == ".ps1" else body


def build(kind: str) -> Path:
    drop = set()  # Barware ships Mac + Windows launchers in both zips
    need = COMMON | (WIN_ONLY if kind == "win" else MAC_ONLY)
    have = {str(r) for r in files()}
    missing = [n for n in need if n not in have and not any(h.startswith(n + "/") for h in have)]
    if missing:
        sys.exit(f"{kind}: missing {missing}")
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"osft-{VERSION}-{kind}.zip"
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files():
            if rel.name in drop and len(rel.parts) == 1:
                continue
            info = zipfile.ZipInfo(f"{TOP}/{rel.as_posix()}", date_time=(2026, 10, 25, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            executable = rel.suffix in (".command", ".sh")
            info.external_attr = ((0o100755 if executable else 0o100644) << 16)
            data = win_text(rel) if rel.suffix in (".bat", ".ps1") else (ROOT / rel).read_bytes()
            z.writestr(info, data)
    return dest


if __name__ == "__main__":
    for kind in ("mac", "win"):
        d = build(kind)
        print(f"{d}  {d.stat().st_size:,} bytes")
