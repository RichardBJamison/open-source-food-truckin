#!/bin/bash
# Open Source Food Truckin' — Mac install (double-click).
# Copies the program to ~/osft-program, sets it up, starts it at login, opens it in the browser.
# Re-run any time to update: your data in ~/osft-program/data is kept.
set -e

INSTALL_DIR="${OSFT_INSTALL_DIR:-$HOME/osft-program}"
PORT="${OSFT_PORT:-5053}"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_LABEL="${OSFT_PLIST_LABEL:-com.osfoodtrucking.program}"
PLIST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
URL="http://127.0.0.1:${PORT}/"

fail() {
  echo ""
  echo "  ✗ $1"
  [ -z "$OSFT_SILENT" ] && read -p "  Press Enter to close..."
  exit 1
}

clear 2>/dev/null || true
echo ""
echo "  Open Source Food Truckin' — Mac Install"
echo "  ---------------------------------------"
echo ""

echo "  [1/6] Checking Python 3.9+..."
PYTHON=""
for candidate in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [ -x "$candidate" ] && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "  Python 3 isn't ready on this Mac yet."
  echo "  If a box popped up asking to install \"command line developer tools\", click Install,"
  echo "  wait for it to finish, then double-click Install.command again."
  echo "  Or install Python from https://www.python.org/downloads/ and run this again."
  fail "Python 3.9 or newer not found."
fi
echo "  ✓ $("$PYTHON" --version 2>&1)"

echo "  [2/6] Copying the program to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/data"
if [ "$SOURCE_DIR" != "$INSTALL_DIR" ]; then
  rsync -a --exclude /data --exclude /.venv --exclude __pycache__ --exclude .pytest_cache --exclude .DS_Store \
    "$SOURCE_DIR/" "$INSTALL_DIR/"
fi
chmod +x "$INSTALL_DIR"/*.command "$INSTALL_DIR/install.sh" 2>/dev/null || true
echo "  ✓ Program files in place (your data folder is untouched)"

echo "  [3/6] Setting up Python..."
VENV_PY="$INSTALL_DIR/.venv/bin/python3"
if ! "$VENV_PY" -c 'import sys' >/dev/null 2>&1; then
  rm -rf "$INSTALL_DIR/.venv"
  "$PYTHON" -m venv "$INSTALL_DIR/.venv" || fail "Could not create the Python environment."
fi
echo "  ✓ Python environment ready"

echo "  [4/6] Installing Flask (first time needs internet)..."
"$VENV_PY" -m pip install --upgrade pip --quiet --disable-pip-version-check >/dev/null 2>&1 || true
"$VENV_PY" -m pip install -r "$INSTALL_DIR/requirements.txt" --quiet --disable-pip-version-check \
  || fail "Could not install Flask. Check the internet connection and run Install.command again."
"$VENV_PY" -c "import flask" 2>/dev/null || fail "Flask did not install."
echo "  ✓ Ready"

echo "  [5/6] Starting the program (and at every login)..."
mkdir -p "$HOME/Library/LaunchAgents"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
lsof -ti tcp:"$PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${PLIST_LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${VENV_PY}</string>
    <string>${INSTALL_DIR}/server.py</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>OSFT_PORT</key><string>${PORT}</string></dict>
  <key>WorkingDirectory</key><string>${INSTALL_DIR}</string>
  <key>KeepAlive</key><true/>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>${INSTALL_DIR}/data/osft_server.log</string>
  <key>StandardErrorPath</key><string>${INSTALL_DIR}/data/osft_server.log</string>
</dict>
</plist>
EOF
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null || true
ok=""
for i in $(seq 1 30); do
  if curl -fs "${URL}api/health" >/dev/null 2>&1; then ok=1; break; fi
  sleep 1
done
[ -n "$ok" ] || fail "The program didn't start. Log: $INSTALL_DIR/data/osft_server.log"
echo "  ✓ Running at $URL"

echo "  [6/6] Opening your browser..."
[ -z "$OSFT_SILENT" ] && open "$URL" 2>/dev/null || true

echo ""
echo "  All set!"
echo "  Program:  $URL   ← bookmark this. That bookmark is the software."
echo "  It starts by itself when you log in. Stop it with Stop.command in $INSTALL_DIR."
echo "  Your data: $INSTALL_DIR/data"
echo ""
[ -z "$OSFT_SILENT" ] && read -p "  Press Enter to close this window..."
exit 0
