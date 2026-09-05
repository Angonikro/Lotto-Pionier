#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/Desktop"
DESKTOP_FILE="$DESKTOP_DIR/Lotto.desktop"
ICON_FILE="$SCRIPT_DIR/lotto-icon.svg"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Lotto
Comment=Lotto Simulator
Exec=python3 "$SCRIPT_DIR/Lotto.py"
Path=$SCRIPT_DIR
Icon=$ICON_FILE
Terminal=false
Categories=Utility;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"
command -v gio >/dev/null 2>&1 && gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
echo "Desktop-Verknüpfung erstellt."
