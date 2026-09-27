#!/usr/bin/env bash
# armorx-lab :: push and start frida-server on a research AVD
#
#   ./push-frida-server.sh emulator-5554
#
# Requires adb root (the google_apis images — NOT google_apis_playstore — allow it).
# The server binary must match the frida-tools version used by the client
# (.venv-frida). Frida 16.7.19 is used because Frida 17 dropped the bundled
# Java bridge that the platform-level hooks need.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../common-env.sh"

DEV="${1:-emulator-5554}"
ARCH="${ARCH:-x86_64}"                 # emulator guest arch
V="$( "$FRIDA_CLI" --version )"
BIN="$LAB_ROOT/frida/tools/frida-server-${V}-${ARCH}"

if [ ! -f "$BIN" ]; then
  echo "missing $BIN" >&2
  echo "download: https://github.com/frida/frida/releases/download/${V}/frida-server-${V}-android-${ARCH}.xz" >&2
  exit 1
fi

"$ADB" -s "$DEV" root
sleep 3
"$ADB" -s "$DEV" wait-for-device
"$ADB" -s "$DEV" shell "pkill -f frida-server || true"
"$ADB" -s "$DEV" push "$BIN" /data/local/tmp/frida-server
"$ADB" -s "$DEV" shell chmod 755 /data/local/tmp/frida-server
"$ADB" -s "$DEV" shell "nohup /data/local/tmp/frida-server >/dev/null 2>&1 & echo started"

sleep 3
"$FRIDA_PY" -c "
import frida
d=frida.get_device('$DEV')
print('processes visible:', len(d.enumerate_processes()))
"
