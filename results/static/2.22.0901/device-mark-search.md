# Device-mark search — 'ZJ-XT' and related patterns, 2.22.0901

Frozen APK: `/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk`
(sha256 `785684ec…c0361c`). Read-only pass.

## Verdict

> **The literal device-mark string `ZJ-XT` is ABSENT from 2.22.0901.** It is also absent, in every
> form searched, from the whole decompressed APK: `resources*`, `classes.dex`, all three
> `libapp.so`, all three `libflutter.so`, `AndroidManifest.xml`, `bledata.proto`, `assets/**`,
> `res/**`, `DebugProbesKt.bin`, the Dart AOT string pool (`pp.txt`), the object dump (`objs.txt`)
> and the full Blutter asm tree. **No `ZJ-` token of any kind is present either** (0 hits in every
> decompressed artifact).
>
> The ARMOR-X device identity in 2.22 is carried by the strings **`ARMOR-X Pro`**, **`ArmorX Pro`**,
> **`devArmorX`** and the package path **`…/widgets/armor-x_pro/…`** — not by any `ZJ-` mark.

## Exact command

```bash
EX=/home/salamanka/armorx-lab/apk/extracted/2.22.0901
BT=/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out
PATTERNS=( 'ZJ-XT' 'ZJ-' 'ARMOR-X' 'ARMORX' 'ArmorX' 'armorx_pro' 'devArmorX' 'F20' )
# per decompressed member:
grep -a -o "$p" "$member" | wc -l
# whole trees:
grep -a -r -o "$p" "$EX/assets" "$EX/res" | wc -l
grep -a -r -o "$p" "$BT/asm" | wc -l
```
The reusable script is `mark_search.sh` in the working scratch dir; the table below is its output
(`grep -a -o <pat> <file> | wc -l`).

## Hit counts per artifact

| artifact | ZJ-XT | ZJ- | ARMOR-X | ARMORX | ArmorX | armorx_pro | devArmorX | F20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `classes.dex` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `resources.arsc` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `AndroidManifest.xml` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `bledata.proto` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `DebugProbesKt.bin` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `lib/arm64-v8a/libapp.so` | 0 | 0 | 2 | 0 | 17 | 4 | 1 | 2 |
| `lib/armeabi-v7a/libapp.so` | 0 | 0 | 2 | 0 | 17 | 4 | 1 | 2 |
| `lib/x86_64/libapp.so` | 0 | 0 | 2 | 0 | 17 | 4 | 1 | 2 |
| `lib/arm64-v8a/libflutter.so` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `lib/armeabi-v7a/libflutter.so` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `lib/x86_64/libflutter.so` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Dart pool `pp.txt` | 0 | 0 | 2 | 0 | 109 | 102 | 1 | 3 |
| object dump `objs.txt` | 0 | 0 | 0 | 0 | 1 | 0 | 1 | 0 |
| Blutter `asm/**` (recursive) | 0 | 0 | 12 | 0 | 250 | 173 | 0 | 2 |
| `assets/**` + `res/**` (recursive) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **APK container (raw bytes)** | **0** | **3*** | 0 | 0 | 0 | 0 | 0 | 0 |

\* The 3 `ZJ-` hits in the raw APK are **not** real: 89/123 zip members are DEFLATE-compressed, so
matching raw container bytes produces coincidental byte sequences (`ZJ-Pj` etc.) inside compressed
streams. Container greps are invalid for this purpose and are shown only to document the trap; the
authoritative counts are the decompressed rows above.

## What the non-zero marks actually are

* `ARMOR-X` → **only** the device label `"ARMOR-X Pro"` (`pp.txt` lines 28758, 39739:
  `[pp+0x2b000] String: "ARMOR-X Pro"`, `[pp+0x39aa0] String: "ARMOR-X Pro_"`). This is the ARMOR-X
  device name; it is a *label*, not a `ZJ-` mark.
* `ArmorX` (109 in pool) → Dart identifiers: `devArmorX`, `ArmorXProScreen`, `ArmorXProConfigWidget`,
  `ArmorXProMacro*`, `ArmorXProMoreWidget`, and the label `"ArmorX Pro"`.
* `armorx_pro` → the app source package path `package:moojiang/widgets/armor-x_pro/armorx_pro_*.dart`.
* `devArmorX` → 1 hit: the `Device` enum member (`objs.txt` `Obj!Device@8fce91`).
* `F20` → **not a device mark**: it is Flutter's keyboard-key map entry
  (`"F20": Obj!LogicalKeyboardKey@8ed1d1`, `"F20": Obj!PhysicalKeyboardKey@8eb791`) plus the opaque
  literal `"SF200000"`. Library artifact only.

## Consistency with the neighbours

Later builds likewise carry `ARMOR-X Pro` (2.23/2.24/4.0.8 all have 1 pool hit at the device-label
slot). The `ZJ-XT` / `ZJ-` mark family is not present in this build; if such a mark exists in the
vendor ecosystem it is not in 2.22.0901's static assets.
