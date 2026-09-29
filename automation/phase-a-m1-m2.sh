#!/usr/bin/env bash
# phase-a-m1-m2.sh -- three sequential single-action popups, each with its own
# passive usbmon capture and its own read-only evdev log. One button per popup.
set -uo pipefail
cd /home/salamanka/armorx-lab
D=results/hardware-validation/hw-interactive-20260929-0354
EVNODE=/dev/input/event18

run_phase () {
  local id="$1" title="$2" msg="$3"
  echo "=== phase $id start $(date -Is)"
  sudo -n timeout 150 tcpdump -i usbmon1 -w "$D/usbmon/$id.pcap" -s 0 >"$D/usbmon/$id.log" 2>&1 &
  local cap=$!
  rm -f "$D/toolkit/evdev-$id.jsonl"
  python3 "$D/tools/evdev-jsonl.py" "$EVNODE" 150 "$D/toolkit/evdev-$id.jsonl" >/dev/null 2>&1 &
  local ev=$!
  sleep 6
  echo "capture bytes before action: $(stat -c%s "$D/usbmon/$id.pcap" 2>/dev/null || echo 0)"
  timeout 200 automation/operator-dialog-kdialog.sh --id "$id" --title "$title" --message "$msg" --button DONE
  local rc=$?
  echo "popup rc=$rc at $(date -Is)"
  sleep 8
  sudo -n pkill -f "tcpdump -i usbmon1 -w $D/usbmon/$id.pcap" 2>/dev/null
  kill $ev 2>/dev/null
  sleep 1
  echo "capture bytes final: $(stat -c%s "$D/usbmon/$id.pcap" 2>/dev/null || echo 0)"
  echo "=== phase $id done $(date -Is)"
}

run_phase phase6-a  'ARMOR-X ACTION REQUIRED - BUTTON A' "$(printf 'PHYSICAL ACTION 5 of 6 - BUTTON A\n\nPress and release the A button exactly ONCE.\n\n- One quick press, nothing else.\n- Do NOT touch triggers or sticks.\n\nThen click DONE on this window.')"

run_phase phase7-m1 'ARMOR-X ACTION REQUIRED - BUTTON M1' "$(printf 'PHYSICAL ACTION 6 of 6 - BUTTON M1\n\nPress and release the M1 paddle/back button exactly ONCE.\n\n- One quick press, nothing else.\n- Do NOT touch triggers or sticks.\n\nThen click DONE on this window.')"

run_phase phase8-m2 'ARMOR-X ACTION REQUIRED - BUTTON M2' "$(printf 'FINAL PHYSICAL ACTION - BUTTON M2\n\nPress and release the M2 paddle/back button exactly ONCE.\n\n- One quick press, nothing else.\n- Do NOT touch triggers or sticks.\n\nThen click DONE on this window.')"

echo "ALL PHASES COMPLETE $(date -Is)"
