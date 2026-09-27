#!/usr/bin/env bash
# shellcheck shell=bash
# =============================================================================
# lib-radio-identity.sh -- shared, READ-ONLY helpers for the armorx-lab radio
#                          tooling (phases 3+4).
#
# Source it, never execute it:
#     . "$(dirname "$0")/lib-radio-identity.sh"
#
# ---------------------------------------------------------------------------
# IDENTITY ANCHOR RULE (hard requirement of this lab)
# ---------------------------------------------------------------------------
# The lab combo adapter is identified ONLY by:
#     * its physical USB path          (e.g. "1-8")
#     * its USB VID:PID                (e.g. "0bda:b720")
#     * its Bluetooth controller bdaddr(e.g. "E8:4E:06:8A:F2:00")
#     * its Wi-Fi MAC                  (e.g. "e8:4e:06:8a:f1:ff")
# Device *names* -- wlan0/wlan1, hci0/hci1, wlxe84e068af1ff -- are NEVER used
# as identity. Names are only ever derived from the anchor at run time. An HCI
# index in particular is not stable across re-plugs (hci0/hci1 can swap), so
# every script resolves the controller fresh, on every run.
#
# ---------------------------------------------------------------------------
# SAFETY
# ---------------------------------------------------------------------------
# Nothing in this library changes radio state. It reads sysfs + hcitool only.
# =============================================================================

set -o pipefail

LAB_ROOT="${LAB_ROOT:-/home/salamanka/armorx-lab}"
LAB_IDENTITY_JSON="${LAB_IDENTITY_JSON:-$LAB_ROOT/baselines/radio/combo-adapter.json}"
RADIO_PY="${RADIO_PY:-/usr/bin/python3}"

# The machine's own radios -- these must NEVER be touched by lab tooling.
PRIMARY_IF="${PRIMARY_IF:-wlp3s0}"
BUILTIN_BT_USB_PATH="${BUILTIN_BT_USB_PATH:-1-6}"

radio_die()  { printf 'ERROR: %s\n' "$*" >&2; exit 2; }
radio_fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
radio_warn() { printf 'WARN: %s\n' "$*" >&2; }
radio_info() { printf '%s\n' "$*"; }

# -----------------------------------------------------------------------------
# radio_reexec_root "$@"
#   State-changing scripts must run as root (they write sysfs bind/unbind files
#   and change interfaces). Shell *functions* cannot be executed through
#   `sudo <function>`, so instead of wrapping individual commands we re-exec the
#   whole script under sudo, forwarding the environment that carries the lab
#   configuration. Idempotent: returns immediately when already root.
# -----------------------------------------------------------------------------
radio_reexec_root() {
  [ "$(id -u)" -eq 0 ] && return 0
  [ "${RADIO_REEXEC:-0}" = "1" ] && radio_die "still not root after re-exec (passwordless sudo failed?)"
  command -v sudo >/dev/null 2>&1 || radio_die "root is required for this operation but sudo is not installed"
  sudo -n true >/dev/null 2>&1 || radio_die "root is required for this operation and passwordless sudo is unavailable"
  local abs
  abs="$(readlink -f "$0")"
  exec sudo -n env \
    RADIO_REEXEC=1 \
    "LAB_ROOT=$LAB_ROOT" \
    "LAB_IDENTITY_JSON=$LAB_IDENTITY_JSON" \
    "PRIMARY_IF=$PRIMARY_IF" \
    "RADIO_PY=$RADIO_PY" \
    "BUMBLE_PY=${BUMBLE_PY:-}" \
    "BUMBLE_TOOL=${BUMBLE_TOOL:-}" \
    "$abs" "$@"
}

# radio_hci_state <hciN> -> "UP RUNNING" | "DOWN" | "" (hciconfig has no -quiet)
radio_hci_state() {
  hciconfig "$1" 2>/dev/null | grep -oE 'UP RUNNING|DOWN' | head -n1 || true
}

radio_require_file() { [ -r "$1" ] || radio_die "required file not readable: $1"; }
radio_require_cmd()  { command -v "$1" >/dev/null 2>&1 || radio_die "required command not found in PATH: $1"; }
radio_is_root()      { [ "$(id -u)" -eq 0 ]; }
radio_maybe_sudo()   { if radio_is_root; then "$@"; else sudo -n "$@"; fi; }

# -----------------------------------------------------------------------------
# radio_json <dotted.path>
#   Print a value out of the identity JSON. List indices are allowed:
#     radio_json physical_anchor.usb_port_path
#     radio_json live_capture.wifi.ifnames.0
#   Prints the empty string (exit 0) when the path is absent, so callers can
#   fall back to other fields. Booleans print as true/false.
# -----------------------------------------------------------------------------
radio_json() {
  local path="$1"
  radio_require_file "$LAB_IDENTITY_JSON"
  "$RADIO_PY" - "$LAB_IDENTITY_JSON" "$path" <<'PY'
import json, sys
fn, path = sys.argv[1], sys.argv[2]
try:
    cur = json.load(open(fn))
except Exception:
    print("", end=""); sys.exit(0)
for part in path.split("."):
    try:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    except Exception:
        print("", end=""); sys.exit(0)
if isinstance(cur, bool):
    print("true" if cur else "false", end="")
elif cur is None:
    print("", end="")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur), end="")
else:
    print(cur, end="")
PY
}

# live_capture.<rest> if non-empty, else expected_identity_until_insertion.<rest>
radio_identity_field() {
  local rest="$1" v
  v="$(radio_json "live_capture.$rest")"
  [ -n "$v" ] || v="$(radio_json "expected_identity_until_insertion.$rest")"
  printf '%s\n' "$v"
}

# radio_json_list <dotted.path>  -> array elements, one per line.
radio_json_list() {
  local path="$1"
  radio_require_file "$LAB_IDENTITY_JSON"
  "$RADIO_PY" - "$LAB_IDENTITY_JSON" "$path" <<'PY'
import json, sys
fn, path = sys.argv[1], sys.argv[2]
try:
    cur = json.load(open(fn))
except Exception:
    sys.exit(0)
for part in path.split("."):
    try:
        cur = cur[int(part)] if isinstance(cur, list) else cur[part]
    except Exception:
        sys.exit(0)
if isinstance(cur, list):
    for x in cur:
        print(x)
PY
}

# radio_bt_usb_interfaces
#   The USB *interfaces* that carry the adapter's Bluetooth function
#   (e.g. 1-8:1.0 and 1-8:1.1 on the RTL8723B, which exposes two BT interfaces).
#   Taken from the identity file when recorded, else derived from sysfs by
#   scanning interfaces of the anchored USB path for class e0/01/01 (Wireless /
#   RF Controller / Bluetooth).
radio_bt_usb_interfaces() {
  local want list ifc cls sub pro
  want="$(radio_anchor_usb_path)"
  list="$(radio_json_list live_capture.bluetooth.usb_interfaces)"
  if [ -z "$list" ]; then
    list="$(radio_json_list expected_identity_until_insertion.bluetooth.usb_interfaces)"
  fi
  if [ -z "$list" ] && [ -n "$want" ]; then
    for ifc in /sys/bus/usb/devices/"$want":*; do
      [ -e "$ifc" ] || continue
      cls=$(cat "$ifc/bInterfaceClass" 2>/dev/null)
      sub=$(cat "$ifc/bInterfaceSubClass" 2>/dev/null)
      pro=$(cat "$ifc/bInterfaceProtocol" 2>/dev/null)
      [ "$cls" = "e0" ] && [ "$sub" = "01" ] && [ "$pro" = "01" ] && list="$list$(basename "$ifc")
"
    done
  fi
  printf '%s' "$list"
}

# --- identity anchors --------------------------------------------------------
radio_anchor_usb_path() { radio_json physical_anchor.usb_port_path; }
radio_anchor_vid()      { radio_json physical_anchor.usb_vid; }
radio_anchor_pid()      { radio_json physical_anchor.usb_pid; }
radio_anchor_vidpid()   { radio_json physical_anchor.usb_vid_pid; }
radio_exp_bdaddr()      { radio_identity_field bluetooth.bdaddr; }
radio_exp_wifi_mac()    { radio_identity_field wifi.mac; }
radio_exp_wifi_driver() { radio_identity_field wifi.driver; }
radio_exp_bt_driver()   { radio_identity_field bluetooth.driver; }

radio_casefold() { printf '%s\n' "$1" | tr 'A-F' 'a-f'; }

# --- sysfs path helpers ------------------------------------------------------
# radio_usb_dev_dir <usb-path>   -> realpath of /sys/bus/usb/devices/<usb-path>
radio_usb_dev_dir() {
  local d
  d="$(readlink -f "/sys/bus/usb/devices/$1" 2>/dev/null)" || true
  [ -n "$d" ] && [ -d "$d" ] || return 1
  printf '%s\n' "$d"
}

# radio_usb_iface_realpath <iface>   e.g. 1-8:1.0 -> /sys/devices/.../1-8/1-8:1.0
radio_usb_iface_realpath() {
  readlink -f "/sys/bus/usb/devices/$1"
}

# radio_usb_iface_driver <iface> -> driver name or empty
#   NOTE: `readlink -f` alone is unsafe here -- it prints the (unresolved) path
#   even when nothing is bound, which would yield the bogus driver "driver".
#   The symlink is therefore tested first.
radio_usb_iface_driver() {
  local p="/sys/bus/usb/devices/$1/driver" r
  [ -L "$p" ] || return 0
  r="$(readlink -f "$p" 2>/dev/null)" || return 0
  [ -n "$r" ] && basename "$r"
  return 0
}

# radio_hci_usb_path <hciN>  -> physical USB device path (e.g. 1-8), or empty.
#   /sys/class/bluetooth/hciN/device  ->  .../usb1/1-8/1-8:1.0
radio_hci_usb_path() {
  local dev
  [ -e "/sys/class/bluetooth/$1" ] || return 1
  dev="$(readlink -f "/sys/class/bluetooth/$1/device" 2>/dev/null)" || return 1
  [ -n "$dev" ] && [ -e "$dev" ] || return 1
  basename "$(dirname "$dev")"
}

# radio_hci_usb_iface <hciN> -> USB interface of that HCI (e.g. 1-8:1.0)
radio_hci_usb_iface() {
  local dev
  [ -e "/sys/class/bluetooth/$1" ] || return 1
  dev="$(readlink -f "/sys/class/bluetooth/$1/device" 2>/dev/null)" || return 1
  [ -n "$dev" ] && [ -e "$dev" ] || return 1
  basename "$dev"
}

# radio_hci_realpath <hciN> -> canonical sysfs dir of the controller
radio_hci_realpath() { readlink -f "/sys/class/bluetooth/$1"; }

# radio_hci_bdaddr <hciN> -> uppercase BD address, or empty.
#   hcitool dev / hciconfig are used because /sys/class/bluetooth/hciN/address
#   is not present on this kernel (verified 2026-09-27).
radio_hci_bdaddr() {
  local hci="$1" a
  a="$(hcitool dev 2>/dev/null | awk -v h="$hci" '$1==h {print $2; exit}')"
  if [ -z "$a" ]; then
    a="$(hciconfig "$hci" 2>/dev/null | awk '/BD Address:/{print $3; exit}')"
  fi
  printf '%s\n' "${a:-}"
}

# --- resolution --------------------------------------------------------------
# radio_resolve_lab_hci
#   Print the lab controller's hci name, resolved by USB path (+ bdaddr
#   cross-check). Returns 1 (prints nothing) when the adapter is absent.
radio_resolve_lab_hci() {
  local want_path want_bd hci upath bd
  want_path="$(radio_anchor_usb_path)"
  want_bd="$(radio_exp_bdaddr)"
  [ -n "$want_path" ] || return 1
  for hci in /sys/class/bluetooth/hci*; do
    [ -e "$hci" ] || continue
    hci="$(basename "$hci")"
    upath="$(radio_hci_usb_path "$hci" 2>/dev/null)" || continue
    [ "$upath" = "$want_path" ] || continue
    if [ -n "$want_bd" ]; then
      bd="$(radio_hci_bdaddr "$hci")"
      [ "$(radio_casefold "$bd")" = "$(radio_casefold "$want_bd")" ] || continue
    fi
    printf '%s\n' "$hci"
    return 0
  done
  return 1
}

# radio_resolve_combo_wifi_iface
#   Print the combo adapter's Wi-Fi netdev, resolved by USB path + MAC.
#   Enforces uniqueness: fails if zero or more than one candidate matches.
radio_resolve_combo_wifi_iface() {
  local want_path want_mac n cand="" mac rp
  want_path="$(radio_anchor_usb_path)"
  want_mac="$(radio_exp_wifi_mac)"
  [ -n "$want_path" ] || return 1
  n=0
  for rp in /sys/class/net/*; do
    [ -e "$rp/device" ] || continue
    case "$(readlink -f "$rp/device")" in
      */"$want_path"/*) ;;      # parent USB device path must match
      *) continue ;;
    esac
    if [ -n "$want_mac" ]; then
      mac="$(radio_casefold "$(cat "$rp/address" 2>/dev/null)")"
      [ "$mac" = "$(radio_casefold "$want_mac")" ] || continue
    fi
    cand="$(basename "$rp")"
    n=$((n + 1))
  done
  [ "$n" -eq 1 ] || return 1
  printf '%s\n' "$cand"
}

# radio_combo_wifi_usb_iface <netdev> -> USB interface name (e.g. 1-8:1.2)
radio_combo_wifi_usb_iface() {
  local dev
  [ -e "/sys/class/net/$1/device" ] || return 1
  dev="$(readlink -f "/sys/class/net/$1/device" 2>/dev/null)" || return 1
  [ -n "$dev" ] && [ -e "$dev" ] || return 1
  basename "$dev"
}

# Root-required write: unbind/bind ONE usb interface, never the whole device.
#   radio_usb_iface_unbind 1-8:1.2  (driver auto-detected)
radio_usb_iface_unbind() {
  local iface="$1" drv rp
  rp="$(radio_usb_iface_realpath "$iface")"
  [ -e "$rp" ] || radio_die "no such USB interface: $iface"
  drv="$(radio_usb_iface_driver "$iface")"
  [ -n "$drv" ] || radio_die "USB interface $iface has no bound driver to unbind from"
  [ -w "/sys/bus/usb/drivers/$drv/unbind" ] || radio_die "not permitted: /sys/bus/usb/drivers/$drv/unbind (need root)"
  printf '%s\n' "$iface" > "/sys/bus/usb/drivers/$drv/unbind" \
    || radio_die "unbind of $iface from $drv failed"
  return 0
}

radio_usb_iface_bind() {
  local iface="$1" drv="$2"
  [ -n "$drv" ] || radio_die "radio_usb_iface_bind: driver name required"
  [ -w "/sys/bus/usb/drivers/$drv/bind" ] || radio_die "not permitted: /sys/bus/usb/drivers/$drv/bind (need root)"
  if [ -n "$(radio_usb_iface_driver "$iface")" ]; then
    return 0   # already bound -> idempotent
  fi
  printf '%s\n' "$iface" > "/sys/bus/usb/drivers/$drv/bind" \
    || radio_die "re-bind of $iface to $drv failed"
  return 0
}

# Guard used by every state-changing script.
radio_assert_not_primary() {
  local iface="$1" pmac imac
  [ "$iface" != "$PRIMARY_IF" ] || radio_die "refusing to act on the PRIMARY interface '$PRIMARY_IF'"
  pmac="$(radio_casefold "$(cat "/sys/class/net/$PRIMARY_IF/address" 2>/dev/null)")"
  imac="$(radio_casefold "$(cat "/sys/class/net/$iface/address" 2>/dev/null)")"
  [ -n "$pmac" ] && [ "$pmac" = "$imac" ] \
    && radio_die "refusing: '$iface' has the same MAC as the primary $PRIMARY_IF"
  return 0
}
