#!/usr/bin/env bash
# armorx-lab :: create the RESEARCH (instrumented) AVDs
#
# Two research devices are created, because the two candidate system images have
# materially different ABI capabilities:
#
#   armorx_res_api33  (android-33 google_apis x86_64)  -> abilist = x86_64 only
#   armorx_res_api30  (android-30 google_apis x86_64)  -> abilist = x86_64,x86,
#                                                         arm64-v8a,armeabi-v7a
#                                                         (+ libndk_translation.so)
#
# Only the API 30 image can *install* the arm64-only builds (2.24 / 4.0.8); it
# still cannot RUN them without crashing (SIGILL in libndk_translation) — see
# results/final/avd-frida-readiness.md.
#
# Verified working on this host.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../common-env.sh"

export ANDROID_AVD_HOME="$HERE/avd-home"
mkdir -p "$ANDROID_AVD_HOME"

IMAGES=(
  "system-images;android-33;google_apis;x86_64"
  "system-images;android-30;google_apis;x86_64"
)
NAMES=("armorx_res_api33" "armorx_res_api30")

for i in "${!IMAGES[@]}"; do
  img="${IMAGES[$i]}"
  name="${NAMES[$i]}"
  echo "== RESEARCH AVD: $name ($img) =="
  IMG_PATH="$ANDROID_HOME/${img//;/\/}"
  if [ ! -d "$IMG_PATH" ]; then
    echo "-- installing system image (large download) --"
    yes | "$SDKMANAGER" --sdk_root="$ANDROID_HOME" "$img" || true
  fi
  echo no | "$AVDMANAGER" create avd \
      -n "$name" -k "$img" -d medium_phone --force
done

echo
echo "RESEARCH AVDs ready. Boot with ./launch-research.sh <name> <port>"
