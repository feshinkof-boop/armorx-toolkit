#!/usr/bin/env bash
# =============================================================================
# radio-status.sh  -- read-only status of the whole radio picture
#
# Prints, in one place:
#   * the PRIMARY network (wlp3s0) state + whether it owns the default route
#   * the LAB combo adapter: is it present (by USB path), which Wi-Fi netdev,
#     which hciN, which drivers, which mode it is currently in
#   * rfkill list
#   * the saved isolation state (if disable-combo-wifi.sh has been run)
#
# USAGE
#   radio-status.sh [-h|--help] [--quiet]
#
# EXIT CODES
#   0  primary network healthy
#   1  primary network check failed (status is still printed)
#   3  combo adapter not present (status is still printed)
#
# SAFETY: strictly read-only.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
LIB="$LAB_ROOT/automation/radio/lib-radio-identity.sh"
[ -r "$LIB" ] || { printf '%s: ERROR: missing library %s\n' "$SELF" "$LIB" >&2; exit 2; }
# shellcheck source=/dev/null
. "$LIB"

CHECK="$LAB_ROOT/automation/radio/check-primary-network.sh"
FINDER="$LAB_ROOT/automation/radio/find-lab-bluetooth.sh"
STATE_JSON="$LAB_ROOT/automation/radio/state/combo-wifi-state.json"

usage() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }
QUIET=0
for a in "$@"; do case "$a" in -h|--help) usage ;; --quiet) QUIET=1 ;; *) radio_die "unknown argument: $a (try --help)" ;; esac; done

hr() { printf -- '--------------------------------------------------------------------------------\n'; }

hr
printf 'armorx-lab radio status  (%s)\n' "$(date -Is)"
hr

printf '\n[1] PRIMARY NETWORK (%s)\n' "$PRIMARY_IF"
if [ -x "$CHECK" ]; then
  if [ "$QUIET" -eq 1 ]; then
    "$CHECK" --quiet || PRIMARY_RC=$?
  else
    "$CHECK" || PRIMARY_RC=$?
  fi
else
  printf '  check-primary-network.sh missing\n'
  PRIMARY_RC=2
fi
PRIMARY_RC="${PRIMARY_RC:-0}"

printf '\n[2] LAB COMBO ADAPTER (identity: USB path %s, VID:PID %s)\n' \
  "$(radio_anchor_usb_path)" "$(radio_anchor_vidpid)"
DEV_DIR="$(radio_usb_dev_dir "$(radio_anchor_usb_path)" 2>/dev/null || true)"
if [ -z "$DEV_DIR" ]; then
  printf '  presence      : ABSENT (no /sys/bus/usb/devices/%s)\n' "$(radio_anchor_usb_path)"
  printf '  expected      : %s\n' "$(radio_json expected_identity_until_insertion.note)"
  COMBO_RC=3
else
  printf '  presence      : PRESENT  %s\n' "$DEV_DIR"
  printf '  vid:pid       : %s\n' "$(radio_anchor_vidpid)"
  printf '  bus/devnum    : %s/%s\n' "$(cat "$DEV_DIR/busnum")" "$(cat "$DEV_DIR/devnum")"
  printf '  usb product   : %s %s (serial %s)\n' \
    "$(cat "$DEV_DIR/manufacturer" 2>/dev/null)" "$(cat "$DEV_DIR/product" 2>/dev/null)" \
    "$(cat "$DEV_DIR/serial" 2>/dev/null)"
  printf '  usb interfaces:\n'
  for ifc in /sys/bus/usb/devices/"$(radio_anchor_usb_path)":*; do
    [ -e "$ifc" ] || continue
    printf '      %-10s class=%s/%s/%s driver=%s\n' "$(basename "$ifc")" \
      "$(cat "$ifc/bInterfaceClass")" "$(cat "$ifc/bInterfaceSubClass")" "$(cat "$ifc/bInterfaceProtocol")" \
      "$(radio_usb_iface_driver "$(basename "$ifc")" || echo '(none)')"
  done

  WIFI_IF="$(radio_resolve_combo_wifi_iface || true)"
  if [ -n "$WIFI_IF" ]; then
    printf '  wifi netdev   : %s  mac=%s driver=%s operstate=%s\n' "$WIFI_IF" \
      "$(cat "/sys/class/net/$WIFI_IF/address")" \
      "$(radio_usb_iface_driver "$(radio_combo_wifi_usb_iface "$WIFI_IF")" || echo '?')" \
      "$(cat "/sys/class/net/$WIFI_IF/operstate")"
    if command -v nmcli >/dev/null 2>&1; then
      printf '  nm managed    : %s\n' \
        "$(nmcli -t -g GENERAL.STATE device show "$WIFI_IF" >/dev/null 2>&1 && echo 'yes (NetworkManager knows it)' || echo 'no (unmanaged)')"
    fi
  else
    printf '  wifi netdev   : none matching the anchored MAC %s (unbound or absent)\n' "$(radio_exp_wifi_mac)"
  fi

  HCI="$(radio_resolve_lab_hci || true)"
  if [ -n "$HCI" ]; then
    printf '  bluetooth hci : %s  bdaddr=%s driver=%s state=%s\n' "$HCI" \
      "$(radio_hci_bdaddr "$HCI")" \
      "$(radio_usb_iface_driver "$(radio_hci_usb_iface "$HCI")" || echo '?')" \
      "$(radio_hci_state "$HCI")"
  else
    printf '  bluetooth hci : none (btusb may be detached -> Bumble mode?)\n'
  fi

  # Mode detection from live state (not from the state file).
  MODE="unknown"
  WIFI_FLAG="no combo wifi netdev"
  if [ -n "${WIFI_IF:-}" ]; then
    nmstate="$(nmcli -t -g GENERAL.STATE device show "$WIFI_IF" 2>/dev/null | head -n1)"
    if [ -n "$nmstate" ]; then
      WIFI_FLAG="managed by NetworkManager (state: $nmstate)"
    else
      WIFI_FLAG="UNMANAGED in NetworkManager (isolated)"
    fi
  fi
  if [ -n "${HCI:-}" ]; then MODE="BlueZ (btusb bound, $HCI present)"; fi
  if [ -z "${HCI:-}" ]; then MODE="Bumble or detached (no kernel HCI for this adapter)"; fi
  printf '  mode          : %s\n' "$MODE"
  printf '  combo wifi    : %s\n' "$WIFI_FLAG"
  [ -r "$STATE_JSON" ] && printf '  isolation log : %s holds the actions of the last disable-combo-wifi.sh run\n' "$STATE_JSON"
  COMBO_RC=0
fi

printf '\n[3] RFKILL\n'
rfkill list 2>&1 | sed 's/^/  /'

printf '\n[4] SAVED ISOLATION STATE\n'
if [ -r "$STATE_JSON" ]; then
  sed 's/^/  /' "$STATE_JSON"
  printf '\n'
else
  printf '  (none -- disable-combo-wifi.sh has not been run)\n'
fi

hr
printf 'summary: primary_rc=%s combo_rc=%s\n' "$PRIMARY_RC" "${COMBO_RC:-0}"
hr
[ "${PRIMARY_RC:-0}" -eq 0 ] || exit 1
[ "${COMBO_RC:-0}" -eq 0 ] || exit 3
exit 0
