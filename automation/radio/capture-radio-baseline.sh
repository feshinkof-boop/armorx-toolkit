#!/usr/bin/env bash
# =============================================================================
# capture-radio-baseline.sh
#
# (Re)generate the armorx-lab radio baselines:
#   baselines/radio/primary-network-baseline.txt   -- primary network observation
#   baselines/radio/combo-adapter.json            -- combo USB Wi-Fi+BT identity
#
# Run it (a) now, and (b) again after the combo adapter is inserted/moved, so the
# live fields become real instead of MISSING_ARTIFACT.
#
# USAGE
#   capture-radio-baseline.sh [-h|--help]
#   capture-radio-baseline.sh [--usb-path 1-8] [--primary-if wlp3s0] [--quiet]
#
# EXIT CODES: 0 ok | 2 usage/prereq error
# SAFETY: read-only apart from writing the two baseline files. Needs sudo only
#         for `dmesg`; if sudo is unavailable the dmesg section is skipped
#         (--no-dmesg forces the skip).
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB_ROOT="${LAB_ROOT:-$(cd "$HERE/../.." && pwd)}"
PY="${RADIO_PY:-/usr/bin/python3}"

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

EXTRA=()
for a in "$@"; do case "$a" in -h|--help) usage ;; *) EXTRA+=("$a") ;; esac; done

[ -x "$PY" ] || { printf '%s: ERROR: %s is not executable\n' "$SELF" "$PY" >&2; exit 2; }
[ -r "$HERE/capture-radio-baseline.py" ] || { printf '%s: ERROR: missing capture-radio-baseline.py\n' "$SELF" >&2; exit 2; }

exec "$PY" "$HERE/capture-radio-baseline.py" --baselines "$LAB_ROOT/baselines/radio" "${EXTRA[@]}"
