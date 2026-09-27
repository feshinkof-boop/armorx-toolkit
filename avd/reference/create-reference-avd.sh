#!/usr/bin/env bash
# armorx-lab :: create the REFERENCE (clean baseline) AVD
#
# The reference device is deliberately minimal: the stock android-33 google_apis
# x86_64 image, no writable system, no frida, no extra props. Anything observed
# on it is the app's un-instrumented behaviour.
#
# Verified working on this host (see results/final/avd-frida-readiness.md).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../common-env.sh"

: "${REF_AVD_NAME:=armorx_ref_api33}"
: "${REF_SYSIMG:=system-images;android-33;google_apis;x86_64}"
: "${REF_DEVICE:=medium_phone}"

export ANDROID_AVD_HOME="$HERE/avd-home"
mkdir -p "$ANDROID_AVD_HOME"

echo "== REFERENCE AVD =="
echo "  name      : $REF_AVD_NAME"
echo "  system img: $REF_SYSIMG"
echo "  avd home  : $ANDROID_AVD_HOME"

IMG_PATH="$ANDROID_HOME/${REF_SYSIMG//;/\/}"
if [ ! -d "$IMG_PATH" ]; then
  echo "-- installing system image (large download) --"
  yes | "$SDKMANAGER" --sdk_root="$ANDROID_HOME" "$REF_SYSIMG" || true
fi

echo no | "$AVDMANAGER" create avd \
    -n "$REF_AVD_NAME" \
    -k "$REF_SYSIMG" \
    -d "$REF_DEVICE" \
    --force

cat <<'EOF'

REFERENCE AVD created (clean, no instrumentation).
Boot it with:  ./launch-reference.sh
EOF
