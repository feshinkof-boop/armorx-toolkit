#!/usr/bin/env bash
# armorx-lab :: install a BIGBIG WON build onto a running research AVD
#
#   ./install-app.sh 2.23  emulator-5554
#   ./install-app.sh 2.24  emulator-5556
#   ./install-app.sh 4.0.8 emulator-5556
#
# Signatures are NEVER touched: we install the original APKs/splits as shipped.
# For the 4.0.8 split build, all splits go in ONE install-multiple session so
# Android can validate the split signature set.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/../common-env.sh"

VER="${1:?usage: install-app.sh <2.23|2.24|4.0.8> [device]}"
DEV="${2:-emulator-5554}"
APKROOT="$LAB_ROOT/apk/original"

case "$VER" in
  2.23)
    "$ADB" -s "$DEV" install -r "$APKROOT/2.23/base.apk"
    ;;
  2.24)
    "$ADB" -s "$DEV" install -r "$APKROOT/2.24/BIGBIGWON-2.24.0919.apk"
    ;;
  4.0.8)
    SPLITS="$LAB_ROOT/apk/extracted/4.0.8-apkm-splits"
    mkdir -p "$SPLITS"
    unzip -o "$APKROOT/4.0.8/BIGBIGWON-4.0.8.apkm" -d "$SPLITS"
    "$ADB" -s "$DEV" install-multiple -r \
        "$SPLITS/base.apk" \
        "$SPLITS/config.arm64_v8a.apk" \
        "$SPLITS/config.en.apk" \
        "$SPLITS/config.xxhdpi.apk" \
        "$SPLITS/config.ar.apk"
    ;;
  *)
    echo "unknown version: $VER" >&2; exit 2 ;;
esac
