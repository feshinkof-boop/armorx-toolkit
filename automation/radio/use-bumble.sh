#!/usr/bin/env bash
# =============================================================================
# use-bumble.sh  -- put the LAB combo adapter into BUMBLE MODE
#
# Bumble mode = the Bumble Python Bluetooth stack drives the adapter instead of
# the kernel/BlueZ. Two transports are possible, and this script tries the
# LEAST INVASIVE one first:
#
#   hci-socket:<hciN>   (preferred, default)
#       Bumble talks to the controller through the *kernel HCI socket*.
#       btusb stays bound; nothing is unbound; only the controller is put DOWN
#       so Bumble can open the socket, and it is brought back UP afterwards.
#
#   usb:<bus>-<port>    (fallback, --transport usb)
#       Bumble claims the USB device directly through libusb. This requires
#       detaching the adapter's Bluetooth USB *interfaces* (e.g. 1-8:1.0 and
#       1-8:1.1) from btusb -- ONE INTERFACE AT A TIME, never the whole USB
#       device -- and they are ALWAYS re-bound automatically on exit (EXIT trap).
#       The transport moniker `usb:1-8` is the physical port path, i.e. exactly
#       the identity anchor, so it never depends on hci indices or netdev names.
#
# USAGE
#   use-bumble.sh [-h|--help]
#   use-bumble.sh [--transport auto|hci-socket|usb] [--command '<cmd>'] [--keep]
#                 [-- <extra args passed to the command>]
#
#   --transport SPEC  auto (default; tries hci-socket, falls back to usb),
#                     hci-socket, or usb
#   --command  CMD    command to run inside Bumble mode
#                     (default: bumble-controller-info from the lab venv)
#   --keep            do NOT restore the kernel's ownership afterwards
#                     (leaves hci down / btusb detached -- for interactive work)
#
#   Environment: BUMBLE_PY (python with bumble importable),
#                BUMBLE_TOOL (path to bumble-controller-info et al.)
#
# EXIT CODES
#   0 ok | 1 runtime failure | 2 usage/prereq | 3 adapter not present
#   4 Bumble not installed
#
# SAFETY: never `rfkill block`, never unbinds a whole USB device, never blacklists
#         a driver, and always restores btusb/hciX state on exit unless --keep.
# =============================================================================
set -o pipefail

SELF="$(basename "$0")"
LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
LIB="$LAB_ROOT/automation/radio/lib-radio-identity.sh"
[ -r "$LIB" ] || { printf '%s: ERROR: missing library %s\n' "$SELF" "$LIB" >&2; exit 2; }
# shellcheck source=/dev/null
. "$LIB"

BUMBLE_VENV="$LAB_ROOT/ble/bumble/venv"
FINDER="$LAB_ROOT/automation/radio/find-lab-bluetooth.sh"

usage() { sed -n '2,44p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }

TRANSPORT=auto
BUMBLE_CMD=""
KEEP=0
EXTRA=()
ORIG_ARGS=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) usage ;;
    --transport) shift; [ -n "${1:-}" ] || radio_die "--transport needs a value"; TRANSPORT="$1" ;;
    --transport=*) TRANSPORT="${1#*=}" ;;
    --command) shift; [ -n "${1:-}" ] || radio_die "--command needs a value"; BUMBLE_CMD="$1" ;;
    --command=*) BUMBLE_CMD="${1#*=}" ;;
    --keep) KEEP=1 ;;
    --) shift; EXTRA=("$@"); break ;;
    *) radio_die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done
case "$TRANSPORT" in auto|hci-socket|usb) ;; *) radio_die "--transport must be auto, hci-socket or usb" ;; esac

# hciconfig/USB interface manipulation and libusb claiming need root.
radio_reexec_root "${ORIG_ARGS[@]}"

# --- 1. adapter present? (checked before anything else: an absent adapter is a
#        more fundamental problem than a missing Bumble install) --------------
WANT_PATH="$(radio_anchor_usb_path)"
if ! radio_usb_dev_dir "$WANT_PATH" >/dev/null; then
  printf '%s: adapter NOT PRESENT on USB path %s (VID:PID %s).\n' \
    "$SELF" "$WANT_PATH" "$(radio_anchor_vidpid)" >&2
  [ -x "$FINDER" ] && "$FINDER" 2>&1 | sed 's/^/  /' >&2
  exit 3
fi

# --- 2. locate a Python with Bumble ------------------------------------------
find_bumble_py() {
  local cand
  for cand in "${BUMBLE_PY:-}" "$BUMBLE_VENV/bin/python" "$(command -v python3 2>/dev/null)"; do
    [ -n "$cand" ] && [ -x "$cand" ] || continue
    if "$cand" -c 'import bumble' >/dev/null 2>&1; then
      printf '%s\n' "$cand"; return 0
    fi
  done
  return 1
}

BUMBLE_PY_FOUND="$(find_bumble_py || true)"
if [ -z "$BUMBLE_PY_FOUND" ]; then
  {
    printf '%s: Bumble is NOT installed -- cannot enter Bumble mode.\n' "$SELF"
    printf '  Looked for a python with `import bumble` at:\n'
    printf '    $BUMBLE_PY=%s\n' "${BUMBLE_PY:-<unset>}"
    printf '    %s/bin/python   (lab venv, currently empty)\n' "$BUMBLE_VENV"
    printf '    %s\n' "$(command -v python3 2>/dev/null || echo '<no python3>')"
    printf '  Install it (NOT done automatically -- nothing is installed by this lab tooling):\n'
    printf '    %s/bin/pip install bumble\n' "$BUMBLE_VENV"
    printf '  Then re-run: %s --transport hci-socket\n' "$0"
  } >&2
  exit 4
fi

# Tool binary (bumble-controller-info et al.) or a module fallback.
# NOTE: Bumble's CLI takes the transport as a POSITIONAL argument
#       (`bumble-controller-info hci-socket:hci1`), not via --transport.
if [ -z "$BUMBLE_CMD" ]; then
  for t in "${BUMBLE_TOOL:-}" "$BUMBLE_VENV/bin/bumble-controller-info" "$(command -v bumble-controller-info 2>/dev/null)"; do
    [ -n "$t" ] && [ -x "$t" ] && { BUMBLE_CMD="$t"; break; }
  done
fi
if [ -z "$BUMBLE_CMD" ]; then
  radio_die "no Bumble tool found; pass --command '<your bumble command>' (e.g. 'bumble-controller-info')"
fi

# --- 3. resolve the controller and build the transport moniker ---------------
WANT_PATH="$(radio_anchor_usb_path)"
HCI="$(radio_resolve_lab_hci || true)"
BDADDR="${HCI:+$(radio_hci_bdaddr "$HCI")}"
HCI_INDEX="${HCI#hci}"; [ -n "$HCI_INDEX" ] || HCI_INDEX=0
# Bumble's hci-socket transport takes an adapter INDEX (not "hci1"). The index
# is re-derived from the anchor-resolved controller on every run, so it is never
# trusted from a previous invocation; the usb transport below uses the physical
# port path instead, which is the stable anchor.
HCI_SPEC="hci-socket:${HCI_INDEX}"
USB_SPEC="usb:${WANT_PATH}"

RESTORE_NEEDED=0
restore_kernel_ownership() {
  [ "$KEEP" -eq 1 ] && { printf '%s: --keep: NOT restoring kernel ownership of the adapter.\n' "$SELF" >&2; return 0; }
  [ "$RESTORE_NEEDED" -eq 1 ] || return 0
  printf '%s: restoring kernel ownership ...\n' "$SELF" >&2
  # (a) BlueZ mode: re-bind btusb to the adapter's Bluetooth USB interfaces.
  while IFS= read -r uif; do
    [ -n "$uif" ] || continue
    [ -e "/sys/bus/usb/devices/$uif" ] || continue
    if [ -z "$(radio_usb_iface_driver "$uif")" ]; then
      radio_maybe_sudo radio_usb_iface_bind "$uif" btusb || radio_warn "re-bind of $uif failed"
    fi
  done <<< "$(radio_bt_usb_interfaces)"
  # (b) bring the controller back up / powered, using the identity anchor.
  sleep 1
  local h; h="$(radio_resolve_lab_hci || true)"
  if [ -n "$h" ]; then
    radio_maybe_sudo hciconfig "$h" up >/dev/null 2>&1 || true
    local bd; bd="$(radio_hci_bdaddr "$h")"
    timeout 15 bluetoothctl <<EOF >/dev/null 2>&1 || true
select $bd
power on
quit
EOF
  fi
}
trap restore_kernel_ownership EXIT INT TERM

run_bumble() { # $1 = transport spec
  local spec="$1"
  printf '%s: running Bumble with transport %s\n' "$SELF" "$spec" >&2
  printf '%s: command: %s %s %s\n' "$SELF" "$BUMBLE_CMD" "$spec" "${EXTRA[*]:-}" >&2
  if [ "${#EXTRA[@]}" -gt 0 ]; then
    # shellcheck disable=SC2086
    $BUMBLE_CMD "$spec" "${EXTRA[@]}"
  else
    # shellcheck disable=SC2086
    $BUMBLE_CMD "$spec"
  fi
}

# --- 3. least-invasive-first transport selection -----------------------------
case "$TRANSPORT" in
  hci-socket)
    [ -n "$HCI" ] || radio_die "no lab controller resolved -- cannot use the hci-socket transport"
    radio_info "bringing $HCI DOWN so Bumble can open the kernel HCI socket (btusb stays bound)"
    radio_maybe_sudo hciconfig "$HCI" down || radio_warn "hciconfig $HCI down failed (may already be down)"
    RESTORE_NEEDED=1
    run_bumble "$HCI_SPEC"
    rc=$?
    ;;
  usb)
    radio_info "detaching the adapter's Bluetooth USB interfaces from btusb (per-interface, never the whole device)"
    while IFS= read -r uif; do
      [ -n "$uif" ] || continue
      [ -e "/sys/bus/usb/devices/$uif" ] || continue
      if [ -n "$(radio_usb_iface_driver "$uif")" ]; then
        radio_maybe_sudo radio_usb_iface_unbind "$uif" || radio_die "unbind of $uif failed"
        radio_info "  unbound $uif"
      fi
    done <<< "$(radio_bt_usb_interfaces)"
    RESTORE_NEEDED=1
    run_bumble "$USB_SPEC"
    rc=$?
    ;;
  auto)
    if [ -n "$HCI" ]; then
      radio_info "auto: trying the least invasive transport first (hci-socket:$HCI)"
      radio_maybe_sudo hciconfig "$HCI" down || radio_warn "hciconfig $HCI down failed"
      RESTORE_NEEDED=1
      if run_bumble "$HCI_SPEC"; then
        rc=0
      else
        rc=$?
        radio_warn "hci-socket transport failed (rc=$rc); falling back to the usb transport"
        radio_maybe_sudo hciconfig "$HCI" up >/dev/null 2>&1 || true
        while IFS= read -r uif; do
          [ -n "$uif" ] || continue
          [ -e "/sys/bus/usb/devices/$uif" ] || continue
          [ -n "$(radio_usb_iface_driver "$uif")" ] && radio_maybe_sudo radio_usb_iface_unbind "$uif" || true
        done <<< "$(radio_bt_usb_interfaces)"
        run_bumble "$USB_SPEC"; rc=$?
      fi
    else
      radio_warn "auto: no kernel HCI controller resolved; going straight to the usb transport"
      while IFS= read -r uif; do
        [ -n "$uif" ] || continue
        [ -e "/sys/bus/usb/devices/$uif" ] || continue
        [ -n "$(radio_usb_iface_driver "$uif")" ] && radio_maybe_sudo radio_usb_iface_unbind "$uif" || true
      done <<< "$(radio_bt_usb_interfaces)"
      RESTORE_NEEDED=1
      run_bumble "$USB_SPEC"; rc=$?
    fi
    ;;
esac

radio_info "Bumble mode finished (rc=$rc)"
[ "$KEEP" -eq 1 ] || radio_info "kernel ownership restored on exit (use --keep to leave it detached)"
exit "${rc:-0}"
