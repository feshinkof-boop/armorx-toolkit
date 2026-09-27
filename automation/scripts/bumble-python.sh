#!/usr/bin/env bash
# =============================================================================
# bumble-python.sh -- run Bumble-lab python code with a Bluetooth-capable
# interpreter.
#
# WHY: the lab venv `.venv-bumble` was created from Hermes' bundled CPython
# 3.14.7, which is *compiled without Bluetooth socket support*
# (`socket.AF_BLUETOOTH` is missing -> bumble's hci-socket transport raises
# "Bluetooth HCI sockets not supported on this platform").
# The distribution interpreter /usr/bin/python3.14 does expose
# AF_BLUETOOTH=31 / BTPROTO_HCI=1 and is ABI-compatible (same 3.14), so it can
# use the venv's site-packages directly via PYTHONPATH.
#
# Usage:  bumble-python.sh <script.py> [args...]
#         sudo -n bumble-python.sh --sudo <script.py> [args...]  (HCI_USER_CHANNEL needs CAP_NET_ADMIN)
# =============================================================================
set -uo pipefail
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
SITE="$LAB_ROOT/.venv-bumble/lib/python3.14/site-packages"
PY="${BUMBLE_PYTHON:-/usr/bin/python3.14}"

[ -d "$SITE" ] || { echo "bumble-python: missing $SITE" >&2; exit 2; }
[ -x "$PY" ]    || { echo "bumble-python: missing interpreter $PY" >&2; exit 2; }

if ! "$PY" -c 'import socket,sys; sys.exit(0 if hasattr(socket,"AF_BLUETOOTH") else 1)'; then
  echo "bumble-python: $PY has no AF_BLUETOOTH" >&2
  exit 2
fi

if [ "${1:-}" = "--sudo" ]; then
  shift
  exec sudo -n env "PYTHONPATH=$SITE" "PYTHONDONTWRITEBYTECODE=1" "$PY" "$@"
fi
exec env PYTHONPATH="$SITE" PYTHONDONTWRITEBYTECODE=1 "$PY" "$@"
