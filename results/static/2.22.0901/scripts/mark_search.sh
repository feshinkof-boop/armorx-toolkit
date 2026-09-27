#!/bin/bash
# Device-mark search over DECOMPRESSED members + Dart pool + Blutter asm.
set -u
EX=/home/salamanka/armorx-lab/apk/extracted/2.22.0901
BT=/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out
APK=/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk
PATTERNS=( 'ZJ-XT' 'ZJ-' 'ARMOR-X' 'ARMORX' 'ArmorX' 'armorx_pro' 'devArmorX' 'F20' )
FILES=( "$EX/classes.dex" "$EX/resources.arsc" "$EX/AndroidManifest.xml" "$EX/bledata.proto" \
        "$EX/DebugProbesKt.bin" "$EX/lib/arm64-v8a/libapp.so" "$EX/lib/armeabi-v7a/libapp.so" \
        "$EX/lib/x86_64/libapp.so" "$EX/lib/arm64-v8a/libflutter.so" "$EX/lib/armeabi-v7a/libflutter.so" \
        "$EX/lib/x86_64/libflutter.so" "$BT/pp.txt" "$BT/objs.txt" "$APK" )
printf '%-46s' "artifact"; for p in "${PATTERNS[@]}"; do printf '%10s' "$p"; done; echo
for f in "${FILES[@]}"; do
  printf '%-46s' "${f#/home/salamanka/armorx-lab/}"
  for p in "${PATTERNS[@]}"; do printf '%10s' "$(grep -a -o "$p" "$f" 2>/dev/null | wc -l)"; done
  echo
done
# whole asm tree
printf '%-46s' "static/blutter/.../asm/** (recursive)"
for p in "${PATTERNS[@]}"; do printf '%10s' "$(grep -a -r -o "$p" "$BT/asm" 2>/dev/null | wc -l)"; done; echo
printf '%-46s' "extracted tree assets/** + res/**"
for p in "${PATTERNS[@]}"; do printf '%10s' "$(grep -a -r -o "$p" "$EX/assets" "$EX/res" 2>/dev/null | wc -l)"; done; echo
