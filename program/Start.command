#!/bin/bash
# Open Source Food Truckin' — start the program and open it (after Install.command).
INSTALL_DIR="${OSFT_INSTALL_DIR:-$HOME/osft-program}"
PORT="${OSFT_PORT:-5053}"
PLIST_LABEL="${OSFT_PLIST_LABEL:-com.osfoodtrucking.program}"
PLIST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
URL="http://127.0.0.1:${PORT}/"

if [ ! -f "$PLIST" ] || [ ! -f "$INSTALL_DIR/server.py" ]; then
  echo "  Run Install.command first."
  read -p "  Press Enter..."; exit 1
fi
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null || true
launchctl kickstart "gui/$(id -u)/${PLIST_LABEL}" 2>/dev/null || true
for i in $(seq 1 20); do
  curl -fs "${URL}api/health" >/dev/null 2>&1 && break
  sleep 1
done
open "$URL"
