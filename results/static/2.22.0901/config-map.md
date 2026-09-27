# 2.22.0901 — configuration map

Evidence base: `units/gamepadset.dart` in
`/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/`.
All byte values below are decoded from the 2.17.5 Smi-doubling dialect.

## 1. Which config families exist in 2.22

| length | family | status in 2.22 | evidence |
|---|---|---|---|
| **88** | `GamepadSet` | PRESENT | PROVEN STATIC — `replaceRange(56, 88, map)` + `sublist(2, 88)` in `GamepadSet::toList`, 2 length immediates (Smi `0xb0`) |
| **144** | `GamepadSet30` | PRESENT | PROVEN STATIC — `replaceRange(112, 144, map)` + `sublist(2, 144)`, 2 length immediates (Smi `0x120`) |
| 240 | (2.23 family) | **ABSENT** | `grep -rn '#0x1e0'` in `asm/moojiang/` → 0 `mov` immediates |
| 280 | (2.24 family) | **ABSENT** | `grep -rn '#0x230'` → 0 |
| 335 | — | **ABSENT** | not a Smi-representable byte; 0 hits |
| 456 | (4.0.8 family) | **ABSENT** | `grep -rn '#0x1c8'` → 0 |
| 484 | (4.0.8 family) | **ABSENT** | `grep -rn '#0x1e4'` → 0 |
| 508 | (4.0.8 family) | **ABSENT** | `grep -rn '#0x1fc'` → 0 |

So 2.22 has exactly **two** config serializers: 88 and 144.
Reproduce:
```
cd /home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out
for pair in "240:0x1e0" "280:0x230" "456:0x1c8" "484:0x1e4" "508:0x1fc" "144:0x120" "88:0xb0"; do
  n=${pair%%:*}; h=${pair##*:}; echo -n "$n: ";
  grep -rn "#$h\b" asm/moojiang/ | grep -v generated | grep -c mov; done
```

## 2. ARMOR-X Pro serializer

- Serializer class: **`GamepadSet30`** (declared `units/gamepadset.dart`, class header ~line 11816).
- Parameter class: **`GamepadParam30`** (declared `units/gamepadset.dart` ~line 17170).
- Exact config length: **144 bytes**. PROVEN STATIC — the length is written big-endian into
  bytes 2-3 and the CRC is taken over `sublist(2, 144)`.
- The class carries `len` (offset 0x8), `pa` = the `GamepadParam30` instance (offset 0xc) and
  `map` = the 32-element mapKeys list (offset 0x10).

## 3. Byte-position map of the 144-byte config

| bytes | content | writer | evidence |
|---|---|---|---|
| **0-1** | CRC-16/MODBUS, **big-endian** (`crc>>8` at byte 0, `crc&0xFF` at byte 1) | inline CRC loop in `GamepadSet30::toList` | PROVEN STATIC |
| **2-3** | configuration length, **big-endian** = `0x0090` (144) | `field_b` of the frame list | PROVEN STATIC |
| **4-111** | 108-byte parameter block | `replaceRange(4, 112, paramList)` | PROVEN STATIC |
| **112-143** | `mapKeys[32]` | `replaceRange(112, 144, map)` | PROVEN STATIC |

Raw reads:
```
sed -n '14230,14262p' units/gamepadset.dart   # replaceRange(112,144,map) @0x7a37a8 + sublist(2,144) @0x7a37d0
```

### 3.1 Verified parameter positions (`param[i]` → config byte `4+i`)

Extracted mechanically by `tools/2.22.0901/gp30_param_map.py` (all `ArrayStore` index literals in
`GamepadSet30::toList`) plus a hand read of the u32/hex region:

| config byte | param idx | field | label |
|---|---|---|---|
| 4 | 0 | `GamepadParam30.motorSpeedIdx` | STRONG EVIDENCE |
| 5 | 1 | `GamepadParam30.motorMax` | STRONG EVIDENCE |
| 9 | 5 | `GamepadParam30.triggerMode` | STRONG EVIDENCE |
| 10 | 6 | `GamepadParam30.triggerLeftDZ` (deadzone centre) | STRONG EVIDENCE |
| 69-72 | 65-68 | `GamepadParam30.sensorSwitch` u32 **BE** (MSB at 69) | STRONG EVIDENCE |
| 80 | 76 | `GamepadParam30.turboSpeedIdx` | STRONG EVIDENCE |
| 81-84 | 77-80 | `GamepadParam30.turboKey` u32 **BE** (MSB at 81) | STRONG EVIDENCE |

Literal-store param indices (i.e. positions written with a *constant* index): **0,1,5,6,7,8,9,11,
12,13,14,15,16,17,18,19,20,21,24,25,26,27,28,29,32,33,34,35,36,40,41,42,43,44,45,48,49,50,51,52,
53,56,57,58,59,60**. Indices **2,3,4,10,22,23,30,31,37,38,39,46,47,54,55** and everything from 61
up are written through *computed* indices (the u32-hex byte loops and reserved slots), so their
exact bytes are not readable from the static stores alone.

## 4. Position-by-position comparison with the later 144-byte structure

Reference: `/home/salamanka/armorx-lab/baselines/imported-research/config-144-reconstruction.md`.

| position | 4.0.8 reference | 2.22 evidence | verdict |
|---|---|---|---|
| bytes 0-1 | CRC-16/MODBUS, big-endian | identical (inline loop, poly 0xA001, init 0xFFFF) | **MATCH** |
| bytes 2-3 | length, big-endian | identical | **MATCH** |
| bytes 4-111 | 108-byte parameter block | `replaceRange(4,112,…)` | **MATCH** |
| bytes 112-143 | `mapKeys[32]` | `replaceRange(112,144,…)` | **MATCH** |
| byte 5 | motorMax | motorMax | **MATCH** |
| byte 9 | triggerMode | triggerMode | **MATCH** |
| byte 10 | triggerLeftDeadzone | triggerLeftDZ | **MATCH** |
| bytes 69-72 | sensorSwitch u32 BE | sensorSwitch u32 BE | **MATCH** |
| byte 80 | turboSpeedIdx | turboSpeedIdx | **MATCH** |
| bytes 81-84 | turboKey u32 BE | turboKey u32 BE | **MATCH** |

**Discrepancy note (about the reference document, not about 2.22).** The 4.0.8 document contradicts
itself: its section-2 cross-check list says *"80 turboSpeedIdx, 81-84 turboKey u32 BE"*, while its
section-3 field table lists byte 76 and bytes 77-80. The 2.22 evidence independently lands on
**byte 80 / bytes 81-84** — i.e. on the document's section-2 values. Treat the section-3 rows
`76` and `77-80` as an off-by-four transcription slip in that document rather than a real
2.22-vs-4.0.8 difference. Flagged rather than silently corrected.

**What is *not* proven equal:** the residue bytes that 2.22 writes through computed indices
(2,3,4,10,22,23,30,31,37,38,39,46,47,54,55 and 61-107) were not compared byte-for-byte against
4.0.8. Asserting full 144-byte equivalence would need either a live 2.22 capture or a selector-resolved
Blutter build. Status: **UNKNOWN** for those positions.

## 5. Embedded default images (independent CRC check)

Two default config images are embedded as literals in the 2.22 binary, both in
`widgets/general/configs_config.dart`, `_ConfigsConfigWidgetState::initState`:

| file | line | length | declared length (bytes 2-3) | stored CRC (bytes 0-1) | CRC-16/MODBUS over bytes[2:] | sha256 |
|---|---|---|---|---|---|---|
| `default-configs/default_000_len_144_configs_config_dart.json` | 880 | 144 | 144 ✓ | `0x0000` | `0xB811` | `b8f5735c…45e595` |
| `default-configs/default_001_len_88_configs_config_dart.json` | 884 | 88 | 88 ✓ | `0x0000` | `0xC800` | `9eaea1d6…a9afa6` |

Extractor: `tools/2.22.0901/extract_default_configs222.py` (adapted from
`mygt408/scripts/extract_default_configs.py`; the 2.22 tree has **no** `defaultConfig()`
switch in `define.dart` — the images are plain list literals inside the widget `initState`, so the
binary-search-switch resolver of 4.0.8 was unnecessary and was replaced by a tree-wide
list-literal scan). Full per-image metadata: `default-configs/index.json`.

Both 2.22 images ship with **CRC = 0x0000**, i.e. a placeholder that the client re-computes at
write time (`GamepadSet30::toList`). Consequence: the images **cannot** be used to validate the CRC
algorithm — they validate the *length* field only. See `crc.md` §3 for the full validation matrix.

## 6. Raw search commands

```
grep -rn '#0x120\b\|#0xb0\b' asm/moojiang/ | grep -v generated | grep mov
python3 tools/2.22.0901/gp30_param_map.py asm/moojiang/units/gamepadset.dart out/_gp30_param_map.json
sed -n '14230,14262p' asm/moojiang/units/gamepadset.dart
python3 tools/2.22.0901/extract_default_configs222.py asm/moojiang results/static/2.22.0901/default-configs
```