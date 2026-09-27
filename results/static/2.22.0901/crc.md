# 2.22.0901 — CRC routine

## 1. Verdict

**YES — the CRC-16/MODBUS rule already existed in 2.22.0901 exactly as in the later builds:**
poly `0xA001` (reversed CRC-16/MODBUS), init `0xFFFF`, computed over `config.sublist(2, length)`
(i.e. bytes **2 … end**), output written **big-endian** into bytes **0-1**. PROVEN STATIC.

## 2. The routines

Three inlined copies of the same loop exist in `units/gamepadset.dart` (there is **no shared
callable** — see §4):

| # | enclosing function | address | init | polynomial instruction | byte range | output |
|---|---|---|---|---|---|---|
| 1 | `::changeGamepadDef` | **0x79c894** (loop init 0x79cf10, poly 0x79cf84) | `r6 = 65535` | `0x79cf84: mov x16, #0xa001` | UNKNOWN (not reconstructed) | UNKNOWN |
| 2 | `GamepadSet::toList` (88-byte family) | **0x7a0c50** (loop init 0x7a1a80, poly 0x7a1af0) | `r6 = 65535` | `0x7a1af0: mov x16, #0xa001` | `sublist(2, 88)` | bytes 0-1, big-endian |
| 3 | `GamepadSet30::toList` (144-byte family) | **0x7a1f60** (loop init 0x7a37e4, poly 0x7a3854) | `r6 = 65535` | `0x7a3854: mov x16, #0xa001` | `sublist(2, 144)` | bytes 0-1, big-endian |

Loop shape at site 3 (site 2 is identical):

```
0x7a37e4  r6 = 65535                      ; init
0x7a37f0  <per-byte loop>
0x7a3828  <bit loop, 8 iterations>
0x7a3854  mov x16, #0xa001                ; reversed polynomial
0x7a3858  eor x9, x8, x16                 ; shift-xor
0x7a386c  asr x8, x6, x4                  ; right shift (reflected algorithm)
0x7a3890  r5 = 8 ; r3 = 0xff00 ; r2 = 0xff
0x7a38b4  asr x3, x9, x5                  ; crc >> 8
0x7a38e0  StoreField: field_f = (crc>>8) & 0xFF   -> element 0 = config byte 0
0x7a38e4  and x3, x6, 0xff
0x7a3900  StoreField: field_13 = crc & 0xFF       -> element 1 = config byte 1
```

Raw reads:
```
sed -n '14273,14320p' units/gamepadset.dart     # init + poly, GamepadSet30::toList
sed -n '14310,14400p' units/gamepadset.dart     # loop + big-endian store
sed -n '10348,10395p' units/gamepadset.dart     # same for GamepadSet::toList
sed -n '977,1020p'    units/gamepadset.dart     # same for changeGamepadDef
grep -rn '65535\|0xa001' units/gamepadset.dart
```

The `0xa001` value is a **raw** (non-Smi) immediate in this build, so the Smi-doubling dialect rule
does not apply to it; `0xFFFF` likewise appears as raw `65535`.

## 3. Independent validation against extracted default images

Extractor: `tools/2.22.0901/extract_default_configs222.py` (adapted from
`mygt408/scripts/extract_default_configs.py`). The 4.0.8 `defaultConfig()` binary-search-switch
technique was **not applicable** here — 2.22 has **no** `defaultConfig()` in `define.dart`; the
default images are plain list literals inside `_ConfigsConfigWidgetState::initState`
(`widgets/general/configs_config.dart:880` and `:884`). Full metadata:
`default-configs/index.json`.

| image | len | declared len (bytes 2-3) | stored CRC (bytes 0-1) | computed CRC-16/MODBUS over bytes[2:] | match? |
|---|---|---|---|---|---|
| `default_000_len_144_…json` | 144 | 144 ✓ | `0x0000` | `0xB811` | **NO** |
| `default_001_len_88_…json` | 88 | 88 ✓ | `0x0000` | `0xC800` | **NO** |

**Result: the images do NOT validate the algorithm — both ship CRC = 0x0000, a placeholder that
the client recomputes at write time.** What the images *do* validate is:
- the length field (bytes 2-3) is big-endian and equals the total image length — 2/2 images ✓;
- the 144 image is a full-length ARMOR-X-style frame (params + 32 mapKeys), the 88 image is a
  full-length `GamepadSet` frame — consistent with §2 of `config-map.md`.

Algorithm confidence therefore rests on the disassembly (three independent code sites, identical
constants and shift direction), not on the images. Any claim that a *shipped* image carries a
pre-computed CRC is **CONTRADICTED** for 2.22.

## 4. Call sites / integration

- The CRC is **inlined** in `GamepadSet::toList` and `GamepadSet30::toList`; those two are the
  call sites that matter for the config write path (`0xD6`/`0xD7`).
- A standalone `getCRC` static is *declared* at `units/gamepadset.dart:180` (address `0x3d2664`)
  but its body is an **uncompiled trampoline** (`CompileFunction` stub, size 0x40) — it is never
  reached in the AOT image. Treat it as dead/unused in 2.22, NOT as the CRC implementation.
  Evidence: `sed -n '162,215p' units/gamepadset.dart`.
- The A5 frame checksum is a different mechanism: `::getCheckSum` @ **0x79c368**
  (`units/gamepadset.dart:87`) = `sum(bytes) & 0xFF` over the whole frame. Details in
  `command-index.md` §1.

## 5. Δ versus the later builds

| property | 2.22.0901 | later builds |
|---|---|---|
| algorithm | CRC-16/MODBUS, reflected, poly 0xA001, init 0xFFFF | same |
| range | bytes 2 … end | same |
| output | big-endian at bytes 0-1 | same |
| form | inlined ×2 (+1 in `changeGamepadDef`), 3 copies | (comparison only; not a 2.22 claim) |

No difference found in the CRC rule between 2.22 and the documented later builds — the rule is
**already present and unchanged** in 2.22.0901.