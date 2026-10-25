#!/usr/bin/env bash
# OSFT local install — creates venv, installs deps, starts server on :5053
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10+ and retry."
  exit 1
fi
if [ ! -d .venv ]; then
  echo "Creating virtualenv…"
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
echo ""
echo "OSFT ready. Starting server on http://127.0.0.1:5053/"
echo "Press Ctrl+C to stop."
exec python server.py
