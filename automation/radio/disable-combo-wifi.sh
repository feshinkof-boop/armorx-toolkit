#!/usr/bin/env bash
# =============================================================================
# disable-combo-wifi.sh
#
# Isolate the LAB combo adapter's Wi-Fi function so it can never interfere with
# the machine's PRIMARY Wi-Fi (wlp3s0 / ath12k, which owns the default route).
#
# What it does, in order:
#   1. resolves the combo Wi-Fi netdev from the SAVED USB IDENTITY
#      (physical USB path + Wi-Fi MAC) -- never by name like wlan1/phy2;
#   2. refuses to run unless exactly ONE candidate matches, and refuses
#      categorically if the candidate is the primary interface or shares its MAC;
#   3. verifies the primary network is healthy BEFORE changing anything;
#   4. marks ONLY that netdev unmanaged in NetworkManager;
#   5. brings ONLY that netdev DOWN (ip link set <if> down);
#   6. optionally (--unbind) unbinds ONLY the adapter's Wi-Fi USB *interface*
#      (e.g. 1-8:1.2) via /sys/bus/usb/drivers/rtl8xxxu/unbind -- never the
#      whole USB device (1-8), and never a driver that serves wlp3s0;
#   7. re-verifies the primary network and FAILS LOUDLY if anything changed;
#   8. writes a state file so restore-combo-wifi.sh can undo exactly this.
#
# USAGE
#   disable-combo-wifi.sh [-h|--help]
#   disable-combo-wifi.sh [--unbind] [--dry-run] [--force]
#
#   --unbind    also detach the Wi-Fi USB interface from its kernel driver
#               (removes the netdev entirely; restorable with restore-combo-wifi.sh)
#   --dry-run   print the plan and exit without changing anything
#   --force     proceed even if the primary network check fails beforehand
#               (dangerous; the pre-change snapshot is still taken)
#
#   Environment: PRIMARY_IF (default wlp3s0)
#
# EXIT CODES
#   0 ok | 1 verification failed | 2 usage/prereq | 3 adapter Wi-Fi not present
#
# SAFETY (hard rules, enforced in code)
#   * never `rfkill block wifi` / `rfkill block all`
#   * never blacklist or unload a Wi-Fi driver
#   * never unbind a whole USB device -- only a single interface (1-8:x)
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

usage() { sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

DO_UNBIND=0
DRY_RUN=0
FORCE=0
ORIG_ARGS=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --unbind)  DO_UNBIND=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --force)   FORCE=1 ;;
    *) radio_die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

# Everything below writes sysfs/interfaces -> must be root.
[ "$DRY_RUN" -eq 1 ] || radio_reexec_root "${ORIG_ARGS[@]}"

radio_require_cmd ip
[ -x "$CHECK" ] || radio_die "missing helper: $CHECK"

WANT_PATH="$(radio_anchor_usb_path)"
WANT_MAC="$(radio_exp_wifi_mac)"
WANT_VIDPID="$(radio_anchor_vidpid)"
[ -n "$WANT_PATH" ] || radio_die "identity file lacks physical_anchor.usb_port_path"

# --- 1. resolve the combo Wi-Fi netdev, with explicit diagnostics ------------
CANDIDATES=()
for rp in /sys/class/net/*; do
  [ -e "$rp/device" ] || continue
  case "$(readlink -f "$rp/device")" in
    */"$WANT_PATH"/*) CANDIDATES+=("$(basename "$rp")") ;;
  esac
done

if [ "${#CANDIDATES[@]}" -eq 0 ]; then
  printf '%s: adapter Wi-Fi NOT PRESENT.\n' "$SELF" >&2
  printf '  No netdev found under physical USB path "%s" (expected MAC %s, VID:PID %s).\n' \
    "$WANT_PATH" "${WANT_MAC:-?}" "${WANT_VIDPID:-?}" >&2
  printf '  ACTION: insert the lab combo adapter into the same USB port, then re-run.\n' >&2
  printf '  Current netdevs: %s\n' "$(ls /sys/class/net/ | paste -sd' ' -)" >&2
  exit 3
fi

WIFI_IF=""
for c in "${CANDIDATES[@]}"; do
  cmac="$(radio_casefold "$(cat "/sys/class/net/$c/address" 2>/dev/null)")"
  if [ -z "$WANT_MAC" ] || [ "$cmac" = "$(radio_casefold "$WANT_MAC")" ]; then
    WIFI_IF="$c"
    break
  fi
done

if [ -z "$WIFI_IF" ]; then
  printf '%s: cannot uniquely identify the combo Wi-Fi netdev.\n' "$SELF" >&2
  printf '  Candidates under USB path %s: %s\n' "$WANT_PATH" "${CANDIDATES[*]}" >&2
  printf '  None matched anchored MAC %s -- refusing to touch anything.\n' "$WANT_MAC" >&2
  exit 3
fi

if [ "${#CANDIDATES[@]}" -gt 1 ]; then
  # More than one netdev on the same USB device: only proceed if exactly one
  # satisfied the MAC anchor (it did, above) and say so out loud.
  radio_warn "multiple netdevs on USB path $WANT_PATH (${CANDIDATES[*]}); selected $WIFI_IF by MAC anchor"
fi

# --- 2. hard guard rails -----------------------------------------------------
radio_assert_not_primary "$WIFI_IF"

USB_IF="$(radio_combo_wifi_usb_iface "$WIFI_IF")"
WIFI_DRV="$(radio_usb_iface_driver "$USB_IF")"
WIFI_MAC="$(cat "/sys/class/net/$WIFI_IF/address")"
OPERSTATE="$(cat "/sys/class/net/$WIFI_IF/operstate")"
NM_MANAGED="unknown"
if command -v nmcli >/dev/null 2>&1; then
  NM_MANAGED="$(nmcli -t -g GENERAL.STATE device show "$WIFI_IF" >/dev/null 2>&1 && echo yes || echo no)"
fi

[ -n "$WIFI_DRV" ] || radio_die "cannot determine the kernel driver for $USB_IF (refusing to unbind blindly)"
case "$WIFI_DRV" in
  ath12k|ath12k_wifi7|ath11k|iwlwifi|ath9k|mt76*|rtw88*|rtw89*|brcmfmac)
      # These are the drivers of built-in/primary-class Wi-Fi. The lab adapter is
      # expected to be on an rtl8xxxu/rtl8723bu-class USB driver.
      radio_warn "combo Wi-Fi driver is '$WIFI_DRV'; confirm this is really the lab adapter before continuing" ;;
esac

# --- 3. primary network healthy BEFORE any change ----------------------------
mkdir -p "$STATE_DIR"
if ! "$CHECK" --snapshot > "$BEFORE_SNAP"; then
  radio_die "cannot snapshot the primary network -- refusing to make changes"
fi
if ! "$CHECK" --quiet >/dev/null 2>&1; then
  if [ "$FORCE" -eq 1 ]; then
    radio_warn "primary network check FAILED but --force given; continuing"
  else
    radio_die "primary network ($PRIMARY_IF) is not healthy BEFORE the change -- fix it first or pass --force"
  fi
fi

printf '%s: plan\n' "$SELF"
printf '  primary (untouched) : %s\n' "$PRIMARY_IF"
printf '  combo wifi netdev   : %s (%s)\n' "$WIFI_IF" "$WIFI_MAC"
printf '  combo usb interface : %s (driver %s)\n' "$USB_IF" "$WIFI_DRV"
printf '  action              : NetworkManager unmanaged + ip link down%s\n' \
  "$([ "$DO_UNBIND" -eq 1 ] && printf ' + unbind %s from %s' "$USB_IF" "$WIFI_DRV")"

if [ "$DRY_RUN" -eq 1 ]; then
  printf '%s: dry-run, nothing changed.\n' "$SELF"
  exit 0
fi

# --- 4/5/6. apply ------------------------------------------------------------
ACTIONS=""
if command -v nmcli >/dev/null 2>&1; then
  if nmcli -t -g GENERAL.STATE device show "$WIFI_IF" >/dev/null 2>&1; then
    radio_maybe_sudo nmcli device set "$WIFI_IF" managed no \
      && ACTIONS="$ACTIONS nm-managed-no" \
      || radio_die "nmcli device set $WIFI_IF managed no failed"
  else
    radio_warn "NetworkManager does not know $WIFI_IF; skipping unmanage step"
  fi
else
  radio_warn "nmcli not available; skipping NetworkManager step"
fi

ip link set "$WIFI_IF" down && ACTIONS="$ACTIONS link-down" \
  || radio_die "ip link set $WIFI_IF down failed"

if [ "$DO_UNBIND" -eq 1 ]; then
  radio_maybe_sudo radio_usb_iface_unbind "$USB_IF" && ACTIONS="$ACTIONS usb-unbind:$USB_IF" \
    || radio_die "unbind of USB interface $USB_IF failed (netdev is already down; no further change made)"
fi

# --- 7. verify the primary network is untouched ------------------------------
rc=0
if ! "$CHECK" --compare-with "$BEFORE_SNAP" --quiet; then
  printf '\n%s: *** PRIMARY NETWORK CHANGED -- RESTORE NOW ***\n' "$SELF" >&2
  printf '  run: %s/automation/radio/restore-combo-wifi.sh\n' "$LAB_ROOT" >&2
  printf '  or : %s/automation/scripts/emergency-restore/emergency-restore-radio.sh\n' "$LAB_ROOT" >&2
  rc=1
fi

# --- 8. record state for the restore script ----------------------------------
"$RADIO_PY" - "$STATE_JSON" "$WIFI_IF" "$WIFI_MAC" "$USB_IF" "$WIFI_DRV" "$ACTIONS" "$OPERSTATE" "$BEFORE_SNAP" <<'PY'
import json, sys, datetime
state, if_, mac, usbif, drv, actions, operstate, snap = sys.argv[1:9]
json.dump({
    "schema_version": 1,
    "written_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    "purpose": "combo-adapter Wi-Fi isolation (phase 3) -- consumed by restore-combo-wifi.sh",
    "wifi_ifname": if_,
    "wifi_mac": mac,
    "usb_interface": usbif,
    "usb_driver": drv,
    "actions_applied": actions.split(),
    "previous_operstate": operstate,
    "primary_snapshot_before": snap,
}, open(state, "w", encoding="utf-8"), indent=2)
print("state written:", state)
PY

printf '%s: done%s\n' "$SELF" "$([ "$rc" -eq 0 ] && echo '' || echo ' (WITH PRIMARY-NETWORK ERROR)')"
exit "$rc"
