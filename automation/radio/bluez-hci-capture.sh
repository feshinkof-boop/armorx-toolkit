#!/usr/bin/env bash
# =============================================================================
# bluez-hci-capture.sh -- INDEPENDENT capture path (Part 16, path B).
#
# Path A is the Bumble harness (byte-exact TX/RX log + session.jsonl).
# Path B is this: the *BlueZ/kernel* stack drives the adapter while `btmon`
# records the raw HCI, so the advertisement + connection + GATT identity reads
# are captured at the HCI layer by a completely different software stack.
#
# Read-only: scans, connects, reads 2A24/2A26/2A19, and (if the attribute can be
# selected) writes the known read-only 0B query A5 04 0B B4 to FFE1 and records
# the notify reply. Nothing is configured or modified.
#
# Usage: bluez-hci-capture.sh <outdir>
# =============================================================================
set -uo pipefail
OUT="${1:?usage: bluez-hci-capture.sh <outdir>}"
mkdir -p "$OUT"
TXT="$OUT/bluez-pass.txt"
SNOOP="$OUT/bluez-pass.btsnoop"
CTL="$OUT/bluetoothctl-session.txt"
ADDR="${ARMORX_BLE_ADDR:-2D:37:35:6D:66:11}"

sudo -n pkill -f '[b]tmon' 2>/dev/null || true
sleep 1
sudo -n btmon -w "$SNOOP" >"$TXT" 2>&1 &
BTMON=$!
sleep 2

{
  echo "scan on";            sleep 8
  echo "scan off";           sleep 1
  echo "connect $ADDR";      sleep 6
  echo "info $ADDR";         sleep 2
  echo "menu gatt";          sleep 1
  echo "list-attributes";    sleep 3
  echo "select-attribute 00002a24-0000-1000-8000-00805f9b34fb"; sleep 1
  echo "read";               sleep 2
  echo "select-attribute 00002a26-0000-1000-8000-00805f9b34fb"; sleep 1
  echo "read";               sleep 2
  echo "select-attribute 00002a19-0000-1000-8000-00805f9b34fb"; sleep 1
  echo "read";               sleep 2
  echo "select-attribute 0000ffe1-0000-1000-8000-00805f9b34fb"; sleep 1
  echo "write 0xa5 0x04 0x0b 0xb4"; sleep 2
  echo "select-attribute 0000ffe2-0000-1000-8000-00805f9b34fb"; sleep 1
  echo "notify on";          sleep 5
  echo "back";               sleep 1
  echo "disconnect $ADDR";   sleep 3
  echo "quit";               sleep 1
} | timeout 90 bluetoothctl >"$CTL" 2>&1

sleep 1
sudo -n kill -TERM "$BTMON" 2>/dev/null || true
sleep 2
sudo -n pkill -f '[b]tmon' 2>/dev/null || true
chmod 0644 "$SNOOP" "$TXT" "$CTL" 2>/dev/null || true
echo "btmon text : $TXT ($(wc -l <"$TXT") lines)"
echo "btsnoop    : $SNOOP ($(stat -c %s "$SNOOP" 2>/dev/null) bytes)"
echo "bluetoothctl: $CTL ($(wc -l <"$CTL") lines)"
