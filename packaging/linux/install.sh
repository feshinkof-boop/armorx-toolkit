#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
VENV="${ARMORX_VENV:-$DATA_HOME/armorx-toolkit/venv}"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

WHEEL=$(find "$SCRIPT_DIR" -maxdepth 1 -type f -name 'armorx_toolkit-*.whl' | sort | tail -n 1)
if [ -z "$WHEEL" ]; then
  echo "ArmorX Toolkit wheel not found next to install.sh" >&2
  exit 1
fi

"$PYTHON" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "$WHEEL[gui]"
"$VENV/bin/armorx-desktop" install

echo
echo "ArmorX Toolkit installed."
echo "Launcher: ArmorX Toolkit"
echo "Command:  $VENV/bin/armorx-gui"
echo "Data:     $DATA_HOME/armorx-toolkit"
