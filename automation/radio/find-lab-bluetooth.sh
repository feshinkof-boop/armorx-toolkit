#!/usr/bin/env bash
# =============================================================================
# find-lab-bluetooth.sh
#
# Resolve the LAB adapter's Bluetooth controller from the saved USB identity
# (baselines/radio/combo-adapter.json).
#
# Resolution is by PHYSICAL USB PATH + BD ADDRESS, never by hci index:
#   1. every /sys/class/bluetooth/hciN is walked;
#   2. readlink -f /sys/class/bluetooth/hciN/device is used to recover the
#      physical USB path (e.g. .../usb1/1-8/1-8:1.0  ->  "1-8");
#   3. only the controller whose USB path equals the anchored one is accepted;
#   4. its bdaddr (hcitool dev / hciconfig) must equal the anchored bdaddr.
# This survives hci-index reshuffles after re-plug.
#
# USAGE
#   find-lab-bluetooth.sh [-h|--help]
#   find-lab-bluetooth.sh [--quiet | --json]
#
#   (no options)  human-readable block
#   --quiet       print only the resolved hci name (e.g. "hci1") -- for use as
#                 $(find-lab-bluetooth.sh --quiet) in other scripts
#   --json        print a JSON object
#
#   Environment: LAB_IDENTITY_JSON (default
#                /home/salamanka/armorx-lab/baselines/radio/combo-adapter.json)
#
# EXIT CODES
#   0  adapter found and resolved
#   3  adapter NOT present (clean, explicit failure)
#   2  usage / identity-file problem
#
# SAFETY: read-only.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
LIB="$LAB_ROOT/automation/radio/lib-radio-identity.sh"
[ -r "$LIB" ] || { printf '%s: ERROR: missing library %s\n' "$SELF" "$LIB" >&2; exit 2; }
# shellcheck source=/dev/null
. "$LIB"

usage() { sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

MODE=human
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --quiet) MODE=quiet ;;
    --json)  MODE=json ;;
    *) radio_die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

WANT_PATH="$(radio_anchor_usb_path)"
WANT_BD="$(radio_exp_bdaddr)"
WANT_VIDPID="$(radio_anchor_vidpid)"
[ -n "$WANT_PATH" ] || radio_die "identity file $LAB_IDENTITY_JSON has no physical_anchor.usb_port_path"

HCI="$(radio_resolve_lab_hci || true)"

if [ -z "$HCI" ]; then
  {
    printf '%s: adapter NOT PRESENT.\n' "$SELF"
    printf '  Looked for a Bluetooth controller whose physical USB path is "%s"\n' "$WANT_PATH"
    printf '  with bdaddr %s (VID:PID %s).\n' "${WANT_BD:-<any>}" "${WANT_VIDPID:-<any>}"
    if [ -n "$(radio_json live_capture.status)" ]; then
      printf '  Identity file records live_capture.status=%s\n' "$(radio_json live_capture.status)"
    fi
    printf '  Controllers currently visible:\n'
    if compgen -G '/sys/class/bluetooth/hci*' >/dev/null; then
      for h in /sys/class/bluetooth/hci*; do
        hn="$(basename "$h")"
        printf '    %-6s usb_path=%-8s bdaddr=%s\n' "$hn" \
          "$(radio_hci_usb_path "$hn" 2>/dev/null || echo '?')" \
          "$(radio_hci_bdaddr "$hn" 2>/dev/null || echo '?')"
      done
    else
      printf '    (none)\n'
    fi
    printf '  ACTION: plug the lab combo adapter (Realtek RTL8723B, %s) into the\n' "${WANT_VIDPID:-0bda:b720}"
    printf '  SAME physical USB port so it re-enumerates as "%s", then re-run:\n' "$WANT_PATH"
    printf '      %s\n' "$0"
  } >&2
  exit 3
fi

UPATH="$(radio_hci_usb_path "$HCI")"
UIFACE="$(radio_hci_usb_iface "$HCI")"
BDADDR="$(radio_hci_bdaddr "$HCI")"
REAL="$(radio_hci_realpath "$HCI")"
DRV="$(radio_usb_iface_driver "$UIFACE")"
RFDIR="$(readlink -f "/sys/class/bluetooth/$HCI/rfkill"* 2>/dev/null | head -n1)"
RFIDX=""
[ -n "$RFDIR" ] && RFIDX="$(basename "$RFDIR" | sed 's/rfkill//')"

case "$MODE" in
  quiet) printf '%s\n' "$HCI" ;;
  json)
    "$RADIO_PY" - "$HCI" "$BDADDR" "$UPATH" "$WANT_VIDPID" "$UIFACE" "$DRV" "$REAL" "$RFIDX" <<'PY'
import json, sys
hci, bd, upath, vidpid, iface, drv, real, rfidx = sys.argv[1:9]
print(json.dumps({
    "resolved": True,
    "lab_hci": hci,
    "bdaddr": bd,
    "usb_path": upath,
    "usb_vid_pid": vidpid,
    "usb_interface": iface,
    "kernel_driver": drv,
    "sysfs_path": real,
    "rfkill_index": rfidx,
    "resolved_by": "usb_path+bdaddr",
}, indent=2, sort_keys=False))
PY
    ;;
  human)
    printf 'lab_hci=%s\n'         "$HCI"
    printf 'bdaddr=%s\n'          "$BDADDR"
    printf 'usb_path=%s\n'        "$UPATH"
    printf 'usb_vid_pid=%s\n'     "$WANT_VIDPID"
    printf 'usb_interface=%s\n'   "$UIFACE"
    printf 'kernel_driver=%s\n'   "$DRV"
    printf 'rfkill_index=%s\n'    "${RFIDX:-unknown}"
    printf 'sysfs_path=%s\n'      "$REAL"
    printf 'resolved_by=usb_path+bdaddr\n'
    ;;
esac
exit 0
