#!/usr/bin/env bash
# =============================================================================
# radio-restore.sh  -- put the whole radio picture back to the lab's default
#
# Default state of the lab (and of this host):
#   * PRIMARY network wlp3s0: associated, owning the default route (untouched)
#   * LAB combo adapter: BlueZ mode  (btusb bound, hciN present and powered)
#   * LAB combo adapter Wi-Fi: re-bound to its driver, managed by NM, UP
#
# It runs, in order:
#   1. restore-combo-wifi.sh         (Wi-Fi side)
#   2. use-bluez.sh --power on       (Bluetooth side)
#   3. check-primary-network.sh      (verification, must PASS)
#
# USAGE
#   radio-restore.sh [-h|--help]
#
# EXIT CODES: 0 all good | 1 something is still wrong | 2 usage/prereq
#
# SAFETY: never blocks rfkill, never unbinds a whole USB device, never touches
#         the built-in controller or the primary Wi-Fi driver.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
R="$LAB_ROOT/automation/radio"

usage() { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }
for a in "$@"; do case "$a" in -h|--help) usage ;; *) printf '%s: ERROR: unknown argument: %s\n' "$SELF" "$a" >&2; exit 2 ;; esac; done

for s in restore-combo-wifi.sh use-bluez.sh check-primary-network.sh; do
  [ -x "$R/$s" ] || { printf '%s: ERROR: missing helper %s\n' "$SELF" "$R/$s" >&2; exit 2; }
done

rc=0
printf '=== [1/3] restore combo Wi-Fi (re-bind + NM managed + link up) ===\n'
"$R/restore-combo-wifi.sh" || { printf '%s: combo Wi-Fi restore failed or adapter absent\n' "$SELF" >&2; rc=1; }

printf '\n=== [2/3] put the lab controller back in BlueZ mode ===\n'
"$R/use-bluez.sh" --power on || { printf '%s: BlueZ mode restore failed or adapter absent\n' "$SELF" >&2; rc=1; }

printf '\n=== [3/3] verify the primary network ===\n'
"$R/check-primary-network.sh" --quiet || rc=1

printf '\n%s: %s\n' "$SELF" "$([ "$rc" -eq 0 ] && echo 'PASS - default lab radio state restored' || echo 'FAIL - see the errors above')"
exit "$rc"
