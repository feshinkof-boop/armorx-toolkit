#!/usr/bin/env bash
# Start frida-server 16.7.19 detached in the emulator guest and verify.
set -uo pipefail
ADB=/usr/bin/adb
DEV="${1:-emulator-5554}"
FRIDA_PY=/home/salamanka/armorx-lab/.venv-frida/bin/python

$ADB -s "$DEV" root >/dev/null 2>&1
sleep 3
$ADB -s "$DEV" wait-for-device
$ADB -s "$DEV" shell "pkill -f frida-server" >/dev/null 2>&1
sleep 1
# detach with setsid so it survives the adb shell exit
$ADB -s "$DEV" shell "setsid /data/local/tmp/frida-server </dev/null >/data/local/tmp/frida-server.log 2>&1 &"
sleep 4
echo "--- ps ---"
$ADB -s "$DEV" shell "ps -A -o PID,ARGS | grep frida-server | grep -v grep"
echo "--- log ---"
$ADB -s "$DEV" shell "cat /data/local/tmp/frida-server.log 2>/dev/null | head"
echo "--- client enumerate ---"
$FRIDA_PY -c "
import frida
d=frida.get_device('$DEV')
print('device', d.id, 'procs', len(d.enumerate_processes()))
"
