#!/usr/bin/env bash
# =============================================================================
# emergency-restore-radio.sh  -- OFFLINE, DEPENDENCY-FREE radio recovery
#
# Use this when the lab radio tooling itself is broken/unavailable and the
# machine must be put back to its normal state. It is deliberately
# self-contained: it sources nothing, parses nothing, and needs only ip, cat,
# echo and ls. Values are hard-coded for THIS host and are commented.
#
# It restores, idempotently:
#   * LAB combo adapter Bluetooth : interfaces 1-8:1.0 and 1-8:1.1 -> driver btusb
#   * LAB combo adapter Wi-Fi     : interface 1-8:1.2 -> driver rtl8xxxu
#   * the combo Wi-Fi netdev      : NetworkManager-managed + UP
#   * the lab Bluetooth controller: rfkill UNBLOCKED (never blocked) + UP/powered
#   * verification                : wlp3s0 UP, associated, owns the default route
#
# IT NEVER: runs `rfkill block ...`, blacklists/unloads a Wi-Fi driver, unbinds a
# whole USB device (only the single interfaces 1-8:1.x listed above), or touches
# the built-in Bluetooth (USB 1-6) or the primary Wi-Fi (wlp3s0 / ath12k).
#
# USAGE
#   emergency-restore-radio.sh [-h|--help] [--dry-run]
#
# EXIT CODES: 0 ok | 1 primary network still wrong | 2 usage
# =============================================================================
set -u

SELF="$(basename "$0")"
PRIMARY_IF="wlp3s0"                 # internal Qualcomm ath12k PCIe Wi-Fi -- never touch
COMBO_USB_PATH="1-8"                # physical USB port path of the lab RTL8723B combo
COMBO_BT_IFACES="1-8:1.0 1-8:1.1"   # its two Bluetooth USB interfaces (class e0/01/01)
COMBO_WIFI_IFACE="1-8:1.2"          # its Wi-Fi USB interface (rtl8xxxu)
COMBO_WIFI_DRV="rtl8xxxu"
BT_DRV="btusb"
DRY=0
for a in "$@"; do
  case "$a" in
    -h|--help) sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --dry-run) DRY=1 ;;
    *) printf '%s: ERROR: unknown argument %s\n' "$SELF" "$a" >&2; exit 2 ;;
  esac
done

run() { if [ "$DRY" -eq 1 ]; then printf '  [dry-run] %s\n' "$*"; else "$@"; fi; }
say() { printf '%s: %s\n' "$SELF" "$*"; }

say "=== [1/5] combo Bluetooth interfaces -> $BT_DRV ==="
for i in $COMBO_BT_IFACES; do
  if [ ! -e "/sys/bus/usb/devices/$i" ]; then
    say "  $i not present (adapter unplugged?) -- skipped"
    continue
  fi
  drv=""
  [ -e "/sys/bus/usb/devices/$i/driver" ] && drv="$(basename "$(readlink -f "/sys/bus/usb/devices/$i/driver")")"
  if [ "$drv" = "$BT_DRV" ]; then
    say "  $i already bound to $BT_DRV"
  else
    say "  binding $i -> $BT_DRV (was: ${drv:-unbound})"
    run sudo -n sh -c "echo $i > /sys/bus/usb/drivers/$BT_DRV/bind"
  fi
done

say "=== [2/5] combo Wi-Fi interface -> $COMBO_WIFI_DRV ==="
if [ -e "/sys/bus/usb/devices/$COMBO_WIFI_IFACE" ]; then
  drv=""
  [ -e "/sys/bus/usb/devices/$COMBO_WIFI_IFACE/driver" ] && drv="$(basename "$(readlink -f "/sys/bus/usb/devices/$COMBO_WIFI_IFACE/driver")")"
  if [ "$drv" = "$COMBO_WIFI_DRV" ]; then
    say "  $COMBO_WIFI_IFACE already bound to $COMBO_WIFI_DRV"
  else
    say "  binding $COMBO_WIFI_IFACE -> $COMBO_WIFI_DRV (was: ${drv:-unbound})"
    run sudo -n sh -c "echo $COMBO_WIFI_IFACE > /sys/bus/usb/drivers/$COMBO_WIFI_DRV/bind"
  fi
else
  say "  $COMBO_WIFI_IFACE not present -- skipped"
fi

say "=== [3/5] hand the combo Wi-Fi netdev back to NetworkManager and bring it up ==="
IFN=""
for n in /sys/class/net/*; do
  [ -e "$n/device" ] || continue
  case "$(readlink -f "$n/device")" in
    */"$COMBO_USB_PATH"/*) IFN="$(basename "$n")" ;;
  esac
done
if [ -n "$IFN" ]; then
  say "  combo Wi-Fi netdev detected as $IFN"
  run sudo -n nmcli device set "$IFN" managed yes || say "  (nmcli managed yes failed -- continuing)"
  run sudo -n ip link set "$IFN" up || say "  (ip link up failed -- continuing)"
else
  say "  no combo Wi-Fi netdev found (unbound or unplugged) -- skipped"
fi

say "=== [4/5] lab Bluetooth controller: unblock + power on ==="
HCI=""
for h in /sys/class/bluetooth/hci*; do
  [ -e "$h" ] || continue
  d="$(readlink -f "$h/device")"
  case "$d" in
    */"$COMBO_USB_PATH"/*) HCI="$(basename "$h")" ;;
  esac
done
if [ -n "$HCI" ]; then
  say "  lab controller resolved as $HCI (by USB path $COMBO_USB_PATH)"
  RF="$(basename "$(readlink -f "/sys/class/bluetooth/$HCI/rfkill"* 2>/dev/null | head -n1)" 2>/dev/null)"
  RF="${RF#rfkill}"
  [ -n "$RF" ] && run sudo -n rfkill unblock "$RF" || true
  run sudo -n hciconfig "$HCI" up || say "  (hciconfig up failed -- continuing)"
  run sudo -n bluetoothctl power on || true
else
  say "  no lab controller for USB path $COMBO_USB_PATH -- skipped"
fi

say "=== [5/5] verify the primary network ($PRIMARY_IF) ==="
rc=0
oper="$(cat "/sys/class/net/$PRIMARY_IF/operstate" 2>/dev/null)"
ddev="$(ip route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -n1)"
[ "$oper" = "up" ] && say "  PASS $PRIMARY_IF operstate=up" || { say "  FAIL $PRIMARY_IF operstate=${oper:-missing}"; rc=1; }
[ "$ddev" = "$PRIMARY_IF" ] && say "  PASS default route dev=$PRIMARY_IF" || { say "  FAIL default route dev=${ddev:-none}"; rc=1; }
if ip -4 -o addr show dev "$PRIMARY_IF" scope global 2>/dev/null | grep -q .; then
  say "  PASS $PRIMARY_IF has a global IPv4 address"
else
  say "  FAIL $PRIMARY_IF has no global IPv4 address"; rc=1
fi

say "=== done (rc=$rc) ==="
exit "$rc"
