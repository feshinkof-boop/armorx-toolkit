#!/usr/bin/env bash
# armorx-lab :: boot a RESEARCH (instrumented) AVD
#
#   ./launch-research.sh                          # default: api33 on :5554
#   ./launch-research.sh armorx_res_api30 5556    # android 11 (ARM translation) on :5556
#   WINDOW=1 ./launch-research.sh                 # with a window
#
# Virtual Bluetooth:
#   The emulator >= 33.1.4.0 activates Bluetooth emulation automatically and
#   starts `netsimd` ("Activated packet streamer for bluetooth emulation").
#   -packet-streamer-endpoint default makes that explicit; point it at a
#   host:port to route the HCI stream through a Bumble bridge instead.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../common-env.sh"

AVD_NAME="${1:-armorx_res_api33}"
PORT="${2:-5554}"
: "${WINDOW:=0}"
: "${STREAMER_ENDPOINT:=default}"     # "default" | "host:port"
: "${WRITABLE_SYSTEM:=1}"

export ANDROID_AVD_HOME="$HERE/avd-home"

LOG="$LAB_ROOT/logs/emulator-res-$PORT.log"
mkdir -p "$(dirname "$LOG")"

GPU_ARGS=(-gpu swiftshader_indirect)
[ "$WINDOW" = "1" ] && GPU_ARGS=(-gpu auto)
WINDOW_ARGS=(-no-window); [ "$WINDOW" = "1" ] && WINDOW_ARGS=()
WS_ARGS=(); [ "$WRITABLE_SYSTEM" = "1" ] && WS_ARGS=(-writable-system)

echo "booting RESEARCH '$AVD_NAME' on :$PORT"
echo "  packet-streamer-endpoint = $STREAMER_ENDPOINT"
echo "  log                      = $LOG"

exec "$EMULATOR" -avd "$AVD_NAME" \
    "${WINDOW_ARGS[@]}" "${GPU_ARGS[@]}" \
    -no-audio -no-boot-anim -no-snapshot \
    -port "$PORT" \
    -packet-streamer-endpoint "$STREAMER_ENDPOINT" \
    "${WS_ARGS[@]}" \
    > "$LOG" 2>&1
