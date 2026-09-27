#!/usr/bin/env bash
# =============================================================================
# use-bluez.sh  -- put the LAB combo adapter into BLUEZ MODE
#
# BlueZ mode = the adapter's Bluetooth function is owned by the kernel: the
# btusb driver is bound to the adapter's Bluetooth USB interfaces, an hciN
# controller exists, and BlueZ (bluetoothd) may power/use it.
#
# This script:
#   1. resolves the adapter from the SAVED USB IDENTITY (USB path + bdaddr),
#      never from an hci index -- indices shuffle across re-plugs;
#   2. re-binds btusb to the adapter's OWN Bluetooth USB *interfaces*
#      (e.g. 1-8:1.0, 1-8:1.1) if a previous Bumble run detached them;
#   3. un-soft-blocks the adapter's rfkill entry if needed (NEVER blocks);
#   4. powers the controller on/off through bluetoothctl, selecting it BY ADDRESS;
#   5. prints the resolved identity and the resulting controller state.
#
# USAGE
#   use-bluez.sh [-h|--help]
#   use-bluez.sh [--power on|off|leave] [--timeout <sec>]
#
#   --power MODE   on (default) | off | leave
#   --timeout SEC  bluetoothctl timeout, default 15
#
#   Environment: LAB_IDENTITY_JSON, PRIMARY_IF
#
# EXIT CODES
#   0 ok | 1 verification failed | 2 usage/prereq | 3 adapter not present
#
# NOTE: `btmgmt` is unreliable on this RTL8723B controller on this host (it hangs
# indefinitely on `btmgmt info`, verified 2026-09-27), so every btmgmt call here
# is wrapped in `timeout` and bluetoothctl is preferred.
#
# SAFETY: touches only the resolved lab controller's USB interfaces. Never
#         unbinds a whole USB device, never blocks rfkill, never touches the
#         built-in controller or wlp3s0.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
LIB="$LAB_ROOT/automation/radio/lib-radio-identity.sh"
[ -r "$LIB" ] || { printf '%s: ERROR: missing library %s\n' "$SELF" "$LIB" >&2; exit 2; }
# shellcheck source=/dev/null
. "$LIB"

FINDER="$LAB_ROOT/automation/radio/find-lab-bluetooth.sh"
BT_DRIVER_EXPECTED="$(radio_exp_bt_driver)"; BT_DRIVER_EXPECTED="${BT_DRIVER_EXPECTED:-btusb}"

usage() { sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

POWER=on
BCTL_TIMEOUT=15
ORIG_ARGS=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --power) shift; [ -n "${1:-}" ] || radio_die "--power needs on|off|leave"; POWER="$1" ;;
    --power=*) POWER="${1#*=}" ;;
    --timeout) shift; BCTL_TIMEOUT="${1:-15}" ;;
    --timeout=*) BCTL_TIMEOUT="${1#*=}" ;;
    *) radio_die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done
case "$POWER" in on|off|leave) ;; *) radio_die "--power must be on, off or leave" ;; esac
case "$BCTL_TIMEOUT" in ''|*[!0-9]*) radio_die "--timeout must be an integer" ;; esac

radio_reexec_root "${ORIG_ARGS[@]}"

radio_require_cmd ip
WANT_PATH="$(radio_anchor_usb_path)"
[ -n "$WANT_PATH" ] || radio_die "identity file lacks physical_anchor.usb_port_path"

# --- 0. is the adapter physically here at all? -------------------------------
if ! radio_usb_dev_dir "$WANT_PATH" >/dev/null; then
  printf '%s: adapter NOT PRESENT on USB path %s.\n' "$SELF" "$WANT_PATH" >&2
  [ -x "$FINDER" ] && "$FINDER" >/dev/null 2>&1 || true
  [ -x "$FINDER" ] && "$FINDER" 2>&1 | sed 's/^/  /' >&2
  printf '  The controller cannot be put in BlueZ mode until the adapter is inserted.\n' >&2
  exit 3
fi

# --- 1. make sure btusb owns the adapter's Bluetooth USB interfaces ----------
while IFS= read -r uif; do
  [ -n "$uif" ] || continue
  [ -e "/sys/bus/usb/devices/$uif" ] || continue
  cur="$(radio_usb_iface_driver "$uif")"
  if [ -z "$cur" ]; then
    radio_info "re-binding $uif to $BT_DRIVER_EXPECTED (was detached, probably by a Bumble run)"
    radio_maybe_sudo radio_usb_iface_bind "$uif" "$BT_DRIVER_EXPECTED" || radio_die "failed to re-bind $uif"
  elif [ "$cur" != "$BT_DRIVER_EXPECTED" ]; then
    radio_warn "$uif is bound to '$cur', not '$BT_DRIVER_EXPECTED' -- leaving it alone"
  else
    radio_info "$uif already bound to $BT_DRIVER_EXPECTED"
  fi
done <<< "$(radio_bt_usb_interfaces)"

# --- 2. resolve the controller by identity (retry while udev settles) --------
HCI=""
for _ in $(seq 1 10); do
  HCI="$(radio_resolve_lab_hci || true)"
  [ -n "$HCI" ] && break
  sleep 1
done
if [ -z "$HCI" ]; then
  printf '%s: adapter is plugged in at USB path %s but no matching Bluetooth controller appeared.\n' \
    "$SELF" "$WANT_PATH" >&2
  [ -x "$FINDER" ] && "$FINDER" 2>&1 | sed 's/^/  /' >&2
  exit 3
fi

BDADDR="$(radio_hci_bdaddr "$HCI")"
UIFACE="$(radio_hci_usb_iface "$HCI")"
RFDIR="$(readlink -f "/sys/class/bluetooth/$HCI/rfkill"* 2>/dev/null | head -n1)"
RFIDX=""; [ -n "$RFDIR" ] && RFIDX="$(basename "$RFDIR" | sed 's/rfkill//')"

# --- 3. rfkill: UNBLOCK ONLY (never block) -----------------------------------
if [ -n "$RFIDX" ]; then
  if rfkill list "$RFIDX" 2>/dev/null | grep -q 'Soft blocked: yes'; then
    radio_info "rfkill $RFIDX ($HCI) is soft-blocked -> unblocking (never blocking)"
    radio_maybe_sudo rfkill unblock "$RFIDX" || radio_warn "rfkill unblock $RFIDX failed"
  fi
fi

# --- 4. power via bluetoothctl, selecting the controller BY ADDRESS ----------
if [ "$POWER" != "leave" ]; then
  if command -v bluetoothctl >/dev/null 2>&1; then
    radio_info "bluetoothctl: select $BDADDR ; power $POWER"
    timeout "$BCTL_TIMEOUT" bluetoothctl <<EOF >/dev/null 2>&1 || true
select $BDADDR
power $POWER
quit
EOF
  else
    radio_warn "bluetoothctl missing; trying btmgmt (timeout-wrapped, known to hang on this adapter)"
    IDX="${HCI#hci}"
    timeout "$BCTL_TIMEOUT" btmgmt --index "$IDX" power "$POWER" >/dev/null 2>&1 || \
      radio_warn "btmgmt power $POWER failed or timed out"
  fi
fi

# --- 5. report ---------------------------------------------------------------
STATE="$(radio_hci_state "$HCI")"
printf '%s: lab controller in BlueZ mode\n' "$SELF"
printf '  lab_hci=%s\n'      "$HCI"
printf '  bdaddr=%s\n'       "$BDADDR"
printf '  usb_path=%s\n'     "$(radio_hci_usb_path "$HCI")"
printf '  usb_interface=%s\n' "$UIFACE"
printf '  driver=%s\n'       "$(radio_usb_iface_driver "$UIFACE")"
printf '  rfkill_index=%s\n' "${RFIDX:-unknown}"
printf '  hci_state=%s\n'    "${STATE:-unknown}"

rc=0
if [ "$POWER" = "on" ]; then
  case "$STATE" in
    *RUNNING*|*UP*) radio_info "PASS: $HCI is UP" ;;
    *) printf '%s: FAIL: $HCI did not come UP (state: %s)\n' "$SELF" "${STATE:-unknown}" >&2; rc=1 ;;
  esac
fi
[ "$POWER" = "on" ] && radio_info "hint: switch the adapter to Bumble with: $LAB_ROOT/automation/radio/use-bumble.sh"
exit "$rc"
