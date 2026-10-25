#!/bin/bash
# Open Source Food Truckin' — stop the program (it starts again at next login; run Start.command to start now).
PORT="${OSFT_PORT:-5053}"
PLIST_LABEL="${OSFT_PLIST_LABEL:-com.osfoodtrucking.program}"
PLIST="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
lsof -ti tcp:"$PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
echo "  Open Source Food Truckin' stopped."
read -p "  Press Enter..."
