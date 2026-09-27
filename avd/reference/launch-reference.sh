#!/usr/bin/env bash
# armorx-lab :: boot the REFERENCE AVD (clean baseline)
#
# Deliberately NO -writable-system and NO instrumentation: this is the golden
# device for "what does the app do untouched".
#
#   ./launch-reference.sh              # headless
#   WINDOW=1 ./launch-reference.sh     # with a window
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../common-env.sh"

: "${REF_AVD_NAME:=armorx_ref_api33}"
: "${PORT:=5554}"
: "${WINDOW:=0}"

export ANDROID_AVD_HOME="$HERE/avd-home"
export ANDROID_EMULATOR_HOME="$HERE/avd-home"

LOG="$LAB_ROOT/logs/emulator-ref-$PORT.log"
mkdir -p "$(dirname "$LOG")"

GPU_ARGS=(-gpu swiftshader_indirect)
WINDOW_ARGS=(-no-window)
if [ "$WINDOW" = "1" ]; then WINDOW_ARGS=(); fi

echo "booting REFERENCE '$REF_AVD_NAME' on port $PORT (log: $LOG)"
echo "NOTE: no virtual-Bluetooth endpoint is passed -> emulator default (netsim) is used."

exec "$EMULATOR" -avd "$REF_AVD_NAME" \
    "${WINDOW_ARGS[@]}" "${GPU_ARGS[@]}" \
    -no-audio -no-boot-anim -no-snapshot \
    -port "$PORT" \
    > "$LOG" 2>&1
