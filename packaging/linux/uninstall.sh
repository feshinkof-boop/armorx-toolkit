#!/bin/sh
set -eu

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV="${ARMORX_VENV:-$DATA_HOME/armorx-toolkit/venv}"

if [ -x "$VENV/bin/armorx-desktop" ]; then
  "$VENV/bin/armorx-desktop" uninstall || true
else
  rm -f "$DATA_HOME/applications/io.github.feshinkof_boop.armorx-toolkit.desktop"
fi

rm -rf "$VENV"

echo "ArmorX Toolkit application removed."
echo "Profiles/backups under $DATA_HOME/armorx-toolkit were preserved."
