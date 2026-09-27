#!/usr/bin/env bash
# =============================================================================
# restore-combo-wifi.sh
#
# Inverse of disable-combo-wifi.sh: put the LAB combo adapter's Wi-Fi function
# back the way it was -- re-bind the USB interface to its kernel driver, hand the
# netdev back to NetworkManager, bring it up -- and re-verify that the machine's
# PRIMARY network (wlp3s0) is untouched.
#
# USAGE
#   restore-combo-wifi.sh [-h|--help]
#   restore-combo-wifi.sh [--no-manage] [--dry-run]
#
#   --no-manage  re-bind and bring the netdev up, but leave it unmanaged in
#                NetworkManager (useful when the combo radio must stay quiet but
#                its interface must exist for inspection)
#   --dry-run    print the plan only
#
#   Environment: PRIMARY_IF (default wlp3s0)
#
# EXIT CODES
#   0 ok | 1 verification failed | 2 usage/prereq | 3 could not restore
#
# SAFETY: only ever acts on the adapter's OWN USB interface and netdev; never
#         unbinds anything, never runs rfkill block, never touches wlp3s0.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
LIB="$LAB_ROOT/automation/radio/lib-radio-identity.sh"
[ -r "$LIB" ] || { printf '%s: ERROR: missing library %s\n' "$SELF" "$LIB" >&2; exit 2; }
# shellcheck source=/dev/null
. "$LIB"

CHECK="$LAB_ROOT/automation/radio/check-primary-network.sh"
STATE_DIR="$LAB_ROOT/automation/radio/state"
STATE_JSON="$STATE_DIR/combo-wifi-state.json"
BEFORE_SNAP="$STATE_DIR/primary-before-combo-wifi-disable.txt"

usage() { sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

NO_MANAGE=0
DRY_RUN=0
ORIG_ARGS=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --no-manage) NO_MANAGE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) radio_die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

[ "$DRY_RUN" -eq 1 ] || radio_reexec_root "${ORIG_ARGS[@]}"

radio_require_cmd ip
WANT_PATH="$(radio_anchor_usb_path)"
WANT_MAC="$(radio_exp_wifi_mac)"
WANT_VIDPID="$(radio_anchor_vidpid)"
WANT_DRV="$(radio_exp_wifi_driver)"

USB_IF="$("$RADIO_PY" - "$STATE_JSON" 2>/dev/null <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("usb_interface", ""))
except Exception:
    print("")
PY
)"
DRV="$( "$RADIO_PY" - "$STATE_JSON" 2>/dev/null <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1])).get("usb_driver", ""))
except Exception:
    print("")
PY
)"
[ -n "$DRV" ] || DRV="$WANT_DRV"
[ -n "$DRV" ] || DRV="rtl8xxxu"

if [ -z "$USB_IF" ]; then
  USB_IF="$(radio_json_list expected_identity_until_insertion.wifi.usb_interfaces | head -n1)"
  radio_warn "no state file/entry found -- falling back to identity-derived USB interface '${USB_IF:-none}'"
fi

printf '%s: plan\n' "$SELF"
printf '  combo usb interface : %s (driver %s)\n' "${USB_IF:-<unknown>}" "$DRV"
printf '  action              : re-bind%s, link up\n' "$([ "$NO_MANAGE" -eq 0 ] && echo ' + NM managed yes' || echo '')"
[ "$DRY_RUN" -eq 1 ] && { printf '%s: dry-run, nothing changed.\n' "$SELF"; exit 0; }

# --- 1. re-bind the USB interface if it is currently unbound ----------------
if [ -n "$USB_IF" ] && [ -e "/sys/bus/usb/devices/$USB_IF" ]; then
  if [ -z "$(radio_usb_iface_driver "$USB_IF")" ]; then
    radio_info "re-binding $USB_IF to $DRV ..."
    radio_maybe_sudo radio_usb_iface_bind "$USB_IF" "$DRV" || radio_die "re-bind failed"
    sleep 1
  else
    radio_info "$USB_IF already bound to $(radio_usb_iface_driver "$USB_IF")"
  fi
elif [ -n "$USB_IF" ]; then
  printf '%s: USB interface %s is not present -- is the adapter plugged in (path %s)?\n' \
    "$SELF" "$USB_IF" "$WANT_PATH" >&2
fi

# --- 2. wait for the netdev to re-appear, resolved by identity ---------------
WIFI_IF=""
for _ in $(seq 1 15); do
  WIFI_IF="$(radio_resolve_combo_wifi_iface || true)"
  [ -n "$WIFI_IF" ] && break
  sleep 1
done

if [ -z "$WIFI_IF" ]; then
  printf '%s: combo Wi-Fi netdev did not appear under USB path %s (expected MAC %s, driver %s).\n' \
    "$SELF" "$WANT_PATH" "${WANT_MAC:-?}" "$DRV" >&2
  printf '  If the adapter was never unbound, this simply means it is not plugged in.\n' >&2
  exit 3
fi
radio_assert_not_primary "$WIFI_IF"

# --- 3. hand back to NetworkManager + bring up -------------------------------
if [ "$NO_MANAGE" -eq 0 ] && command -v nmcli >/dev/null 2>&1; then
  radio_maybe_sudo nmcli device set "$WIFI_IF" managed yes \
    && radio_info "NetworkManager now manages $WIFI_IF" \
    || radio_warn "nmcli device set $WIFI_IF managed yes failed"
elif [ "$NO_MANAGE" -eq 1 ]; then
  radio_info "--no-manage: leaving $WIFI_IF unmanaged in NetworkManager"
fi

ip link set "$WIFI_IF" up && radio_info "$WIFI_IF is UP" || radio_warn "ip link set $WIFI_IF up failed"

# --- 4. re-verify the primary network ---------------------------------------
rc=0
if [ -r "$BEFORE_SNAP" ]; then
  "$CHECK" --compare-with "$BEFORE_SNAP" --quiet || rc=1
else
  "$CHECK" --quiet || rc=1
fi

printf '%s: done%s\n' "$SELF" "$([ "$rc" -eq 0 ] && echo '' || echo ' (PRIMARY NETWORK CHECK FAILED)')"
exit "$rc"
