# BIGBIG WON / MOJHON — 2.22.0901 command & opcode inventory

Scope: Dart 2.17.5 AOT `lib/arm64-v8a/libapp.so` from APK sha256
`785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`.
Evidence base: Blutter disassembly `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/`
(`asm/moojiang/**`, `pp.txt`, `objs.txt`). BLE stack in this build is
`flutter_reactive_ble` + `reactive_ble_platform_interface` (confirmed from the class inventory;
4.0.8 uses `flutter_blue_plus` — do not carry 4.0.8 API conclusions over).

Evidence labels used: **PROVEN STATIC** (byte-exact from the disassembly, checksum recomputed),
**STRONG EVIDENCE** (constant + frame context read by hand, one link unproven),
**INFERRED**, **UNKNOWN**, **CONTRADICTED**.

## 0. Dialect rule applied

Smi immediates are doubled. A byte `B` appears as `#0x(2B)`. Everything below is already
decoded back to the wire byte. Methods and the scanners are in
`/home/salamanka/armorx-lab/tools/2.22.0901/`.

## 1. Frame families

| family | status in 2.22 | evidence |
|---|---|---|
| **A5** short frame `A5 \| total_len \| opcode \| payload… \| checksum` | PRESENT, 10 byte-exact builders reconstructed | PROVEN STATIC — `tools/2.22.0901/reconstruct_frames222.py` (`out/_frames222.md`) |
| **A4** indexed fragmentation, base list `[0xA4]` | PRESENT (builder + two reply handlers) | STRONG EVIDENCE — see §3 |
| **AB** motion/other | **ABSENT** | PROVEN STATIC — no `#0x156` (Smi 342) immediate anywhere; the motion/gyro block travels inside the 144-byte config |

### Checksum rule (applies to A5 and A4 alike)

`::getCheckSum` lives in `units/gamepadset.dart` line 87, address **0x79c368** (PROVEN STATIC):
it iterates the list, accumulates `sum += element`, and returns `sum & 0xFF`.
For every one of the 10 reconstructed A5 builders the last array element was `0` in the static
array and the recomputed value `(sum of all preceding bytes) & 0xFF` matched the value the code
patches in — 10/10 `checksum_ok: true` (`out/_frames222.json`).

```
0x79c368  getCheckSum(list) : r = 0 ; for e in list : r += e ; return r & 0xFF
```
Search that produced it:
`grep -rn 'r0 = getCheckSum()' asm/moojiang/` and `sed -n '87,150p' asm/moojiang/units/gamepadset.dart`.

## 2. Complete A5 opcode inventory (byte-exact)

| opcode | status | role | builder (function @ address) | frame bytes | checksum | reply parser | UI feature | guard |
|---|---|---|---|---|---|---|---|---|
| **0x0B** | PRESENT (send+reply) | read — MCU/firmware version query (`getZKMVer`) | `_ArmorXProWidgetState::getZKMVer` closure @ **0x7ab7f8**; `_RainbowWidget::getZKMVer` closure @ **0x7a9b8c** | `A5 04 0B B4` | 0xB4 | yes — inbound handler `_ArmorXProWidgetState::subscribeCharacteristic` @ **0x7ab44c** (compare of 22 ≙ 0x0B) and `_RainbowWidget` handler @ **0x7a97f8** | ARMOR-X Pro / Rainbow first-contact | none observed |
| **0x0E** | PRESENT (send-only) | write — post-write command (`writeDevice`) | `::` closure in `units/gamepadset.dart` @ **0x79c5d4** | `A5 05 0E 00 B8` | 0xB8 | no parser found | emitted after config/macro writes | none observed |
| **0xD2** | PRESENT (send-only) | diagnostic — controller test-mode switch | `_RainbowTestState::testModeSwitch1` @ **0x8e1efc** (off) and `_RainbowTestState::testModeSwitch` closure @ **0x8e3be4** (on) | `A5 05 D2 00 7C` / `A5 05 D2 01 7D` | 0x7C / 0x7D | no parser found | Rainbow test page `widgets/rainbow/rainbow_test.dart` | none observed |
| **0xD4** | PRESENT (send+reply) | read — on-board config / input-model (`getOnBoardConfig`) | `_ArmorXProConfigWidgetState::getOnBoardConfig` closure @ **0x89adac** | `A5 04 D4 7D` | 0x7D | yes — handler @ **0x89b438** compares 424 ≙ 0xD4 (0x89bc94) | ARMOR-X Pro config page | none observed |
| **0xD6** | PRESENT (send+reply) | read — device configuration (`getDeviceConfig`) | `_ArmorXProConfigWidgetState::getDeviceConfig` closure @ **0x89bff8**; `_ConfigsConfigWidgetState::getDeviceConfig` closure @ **0x8a60f4** | `A5 04 D6 7F` | 0x7F | yes — A4 reply handlers @ **0x8a6a04** (0x8a6a80) and @ **0x89b438** (0x89b4b4) compare 428 ≙ 0xD6 | ARMOR-X Pro config page / generic config page | none observed |
| **0xEF** | PRESENT (send+reply) | read — device UUID (`getDeviceUUID`) | `_ArmorXProWidgetState::getDeviceUUID` closure @ **0x7aadd0**; `_RainbowWidget::getDeviceUUID` closure @ **0x79c074** | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 0xA0 | yes — @ **0x7ab44c** (compare 478 ≙ 0xEF, 0x7ab4cc); reply bytes 3..10 hex-encoded into `devUuid` (armorx_pro_root.dart:3213-3261) → `onGetDeviceUUID` → `devRegisterResponse` | first-contact; `POST /dev/register` | none observed |
| **0x70** | PRESENT (send-only) | lighting configuration (`writeLightConfig`) | `GamepadDef::writeLightConfig` closure @ **0x7a74c4** (opcode immediate at 0x7a7ba0) | `A5 ?? 70 00 00 00` — 6-element frame; element0 = 0xA5, element1 = 0x00 placeholder, element2 = 0x70, remaining = 0, length + checksum patched later | UNKNOWN (frame is patch-filled) | none found | Rainbow light-config page | UNKNOWN |

Non-opcode constant in the same builder: **0xFF** (immediate 510 ≙ Smi) at **0x7a7a3c** inside
`writeLightConfig` — a *payload* marker inside the `A5 70` body, not an opcode. STRONG EVIDENCE.

## 3. A4 family (indexed fragmentation)

| opcode | status | role | builder (function @ address) | reply parser | UI |
|---|---|---|---|---|---|
| **0xD7** | PRESENT (send+reply) | write — device configuration (`writeDeviceConfig`) | `GamepadDef::writeDeviceConfig` closure @ **0x7a005c**; the fragment list is `AllocateArray(2) → [0xA4]` at 0x7a040c and the opcode 430 ≙ 0xD7 is appended at **0x7a07d0** | yes — @ **0x89b438** (0x89bd00, 430 ≙ 0xD7) and @ **0x8a6a04** | ARMOR-X Pro config page (`armorx_pro_config_config.dart:6701`), generic config page (`configs_config.dart:2755`) |
| **0xD8** | PRESENT (send-only) | write — macro / macro-protocol (`writeMacroConfig`) | `GamepadDef::writeMacroConfig` closure @ **0x79e158** (opcode 432 ≙ 0xD8 at **0x79e778** and 0x79ebf4); also emitted by `writeLightConfig` @ 0x7a8aa0 | no 0xD8 comparison found in any frame handler → send-only | ARMOR-X Pro macro page, Rainbow macro page |

**A4 field order — UNKNOWN.** The `/`-indexed-reply handler @0x89b438 resolves the receiver's
frames through a dynamic dispatch stub (`GDT[cid_x0 - 0xfcb]`, an *unresolved selector id*), so
the observed list indices (0 → header, 4 → opcode, 6 → fragment index, payload ≥6) could not be
mapped onto wire byte positions statically. Exactly this mapping needs a live capture or a
Blutter build with resolved selectors. Recorded as observed, not interpreted:
`grep -n 'GDT\[cid_x0' asm/moojiang/widgets/armor-x_pro/armorx_pro_config_config.dart` around 0x89b438.

Known raw commands:
```
python3 tools/2.22.0901/ctx.py <tree> 0x89b438 --before 6 --after 6   # A4 handler constants
python3 tools/2.22.0901/dispatch_census.py                           # full dispatcher census
```

## 4. Every other candidate opcode — present or absent in 2.22

Result of a whole-tree Smi-immediate census (`tools/2.22.0901/opcode_census.py`, which skips the
`intl` string tables that otherwise make every small integer look like a hit) plus a manual
context read of every surviving hit:

| opcode | verdict in 2.22 | why |
|---|---|---|
| 0x04 | **ABSENT** | no `A5 04 04` builder and no dispatch compare. Battery is standard GATT: `uuidBatteryService() → "180F"` (define.dart:100, @0x791d28). |
| 0x05 | **ABSENT** (as protocol opcode) | 70 raw hits, all in UI files (`units/component.dart`, `units/configbutton.dart`, `theme.dart`) or as `AllocateArray` length immediates. No frame context. |
| 0x06 | **ABSENT** | all 46 hits are UI/array-size immediates (e.g. 0x7a7be0 `r17 = 12` is a growable-list length). |
| 0x07 | **ABSENT** | 33 hits, all colour tables / UI. |
| 0x1A | **ABSENT** | `#0x34` hits are data literals (`[.. 24,25,26 ..]` lists in macro/mapkey widgets) and `GamepadSet::toList` payload values. No frame context. |
| 0x1B | **ABSENT** | single hit 0x8dca14 — a `LightColor` field value. |
| 0x25, 0x26 | **ABSENT** | hits are config payload bytes and a raw `cmp #37` in `::applicationMacro`; and `GamepadSet30`/`GamepadParam30` payload values. |
| 0x34 | **ABSENT** | zero immediate hits. |
| 0x73 | **ABSENT** | zero immediate hits. |
| 0xA9 | **ABSENT** | zero hits; the DouJiang keyboard module is not in 2.22. |
| 0xD3 | **ABSENT** | zero immediate hits. |
| 0xDA | **ABSENT** | zero immediate hits. |
| 0xDD | **ABSENT** | zero immediate hits (4.0.8's charging-light-effect did not exist yet). |
| 0xE1 | **ABSENT** | zero immediate hits (4.0.8's connect-mode). |
| 0xE2 | **ABSENT** | see `e2-verdict.md` — Smi 452 ≙ 0x1c4 appears *only* in the bundled `syncfusion_flutter_pdf` library, never in `moojiang/`; raw 226 ≙ 0xe2 never appears as an immediate; no pool constant carries it. |
| 0xE3 | **ABSENT** | zero immediate hits. |
| 0xE4 | **ABSENT** | zero immediate hits; 2.22 has no MTU command — MTU is handled by `flutter_reactive_ble`. |
| 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8 | **ABSENT** | zero immediate hits each. |
| 0xFC, 0xFD | **ABSENT** | zero immediate hits (`0x1f8` occurrences are `ldr` offsets, not `mov` immediates). |
| 0xAB | **ABSENT** | see §1. |

The `0xC8` constants in `units/server.dart` are **HTTP**, not BLE, and are out of scope here.

## 5. Implemented-but-unused / send-only summary

- **Send-only (no reply parser found):** `0x0E`, `0x70`, `0xD2`, `0xD8`.
- **Implemented-but-unused:** none found. Every present opcode is reachable from a live UI call
  site (each builder was reached by walking call sites of the enclosing widget state).
- **Request/response pairs:** `0x0B`, `0xD4`, `0xD6`, `0xD7`, `0xEF`.

## 6. Method

- `reconstruct_frames222.py` — `AllocateArray` → array-literal → `getCheckSum` window walk, A5
  only; produced the 10 byte-exact frames. Adapted from `mygt408/scripts/reconstruct_frames.py`
  (2.17.5 dialect: the address comment sits between the pseudo-op and the real instruction, so the
  `AllocateArray` regex had to accept an optional leading `// 0xADDR:`).
- `opcode_census.py` — Smi-immediate census, excludes `generated/intl/`, `messages_*.dart`, `l10n.dart`.
- `dispatch_census.py` — dispatcher census over the two 2.17.5 idioms (integer equality via
  `_IntegerImplementation`, and `cmp` on raw ints).
- `ctx.py` — address → asm context dumper.
- `gp30_param_map.py` — config parameter-block index extractor (see `config-map.md`).

Raw command that reproduces the census:
```
python3 tools/2.22.0901/opcode_census.py <tree> out/_opcode_census.json
python3 tools/2.22.0901/reconstruct_frames222.py <tree> out/_frames222.json --md out/_frames222.md
```