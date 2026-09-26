# Config format family map — 2026-09-25

Maps device families to configuration formats, from Blutter static analysis of
com.moojiang.bigbigwon 2.23.0609 (Dart 2.19.6/Flutter 3.7) and 2.24.0919
(Dart 3.2.3/Flutter 3.16), cross-correlated with the live ARMOR-X Pro capture.

## Android device enum (PROVEN_STATIC, keep separate from Windows legacy IDs)

2.23 `deviceName` (define.dart @0x7fee88, field `curDevice.field_7`):
1=Rainbow, 2=Rainbow S, 3=Rainbow2 PRO, 4=BLITZ ULT, 5=BLITZ LITE, 6=ARMOR-X Pro.

2.24 `deviceName` (define.dart @0x830cc8, field `curDevice.field_7`):
1=Rainbow, 2=Rainbow S, 3=Rainbow2 PRO, 4=Rainbow2 Lite, 5=Blitz2, 6=BLITZ ULT,
7=CHOCO, 8=ARMOR-X Pro (Smi 0x10). Enum renumbered; ARMOR-X Pro moved 6 → 8.

Windows legacy factory types (separate namespace, DevMgr.dll): 2=ArmorX,
3=ArmorX Pro, 4=ArmorX Dongle. Never merge with Android enum numbers.

## Config sizes and selection

Effective config length is NOT hard-coded per device. It is derived at runtime:
D6 reply reassembly → `parsingData` → `checkConfigLength` → static field
(2.23: 0xfd8; 2.24: 0x1030) → UI routing + serializer choice.

checkConfigLength (2.23 @0x810a34, PROVEN_STATIC):
```
if (list.length < 240) return list.length
if (list.contains(-2) && list.length == 240) return 240
return list.indexOf(-2)      // -2 = wire byte 0xFE padding terminator
```

2.24 router (rainbow_tab_config_1s.dart @0x8aa014, PROVEN_STATIC): config-length
static == 0x58(88) / 0x90(144) / 0xF0(240) → legacy pages; == 0x118(280) →
ConfigsMain280Widget (gamepadset280); else → ConfigsMain484Widget (gamepadset484).

## Family → format table

| Config size | Serializer | Default template sha256[:16] | Device family (evidence) |
|---|---|---|---|
| 88 | GamepadSet (2.23) | 9eaea1d6a42c49a4 | Rainbow (type 1; defaultConfig selects 88 for type 1, 2.23) |
| 144 | GamepadSet30::toList @0x7a0530 | 1fa5afe2401d17c2 (Rainbow-family defaults), bc536085f138a2ed (**ARMOR-X Pro**) | ARMOR-X Pro proven live: captured device image == bc536085 template + recomputed CRC 0x7F67. Rainbow2/BLITZ-family defaults differ at offsets 10-13,16,18,36 |
| 240 | GamepadSet30 (else-branch) | 4baf590a1d3d48ad (CRC valid), +3 more variants in 2.24 | 240-byte devices (Rainbow2 PRO-era; exact model UNKNOWN — not ARMOR-X Pro live) |
| 280 | gamepadset280.dart (2.24 only) | 8f318f88caedb66b | C1 Pro-class devices (configV280 pages reference C1Pro widgets; router by length 0x118) |
| 484 | gamepadset484.dart (2.24 only) | a61757a34cbdc20f (CRC 0xD0A4 valid) | C1 Pro-class (configV484 pages; else-branch of length router) |

**ARMOR-X Pro remains 144 bytes** — unchanged in 2.24 (its armor-x_pro pages and
GamepadSet30 path persist; 280/484 pages never reference the ARMOR-X Pro widget tree).
Live capture (2.23): D6/D7 images exactly 144 bytes ×16/17.

## Read/write paths per family

All families share: FFE1 write-without-response, FFE2 notify, A5 short frames,
A4 fragmentation (15-byte chunks, 1-based index, len byte = total frame bytes),
per-frame sum-mod-256 checksum, and for 144/240/280/484 a CRC-16/MODBUS over
bytes 2..end stored big-endian at 0..1 (88-byte format: same envelope, CRC recomputed
at write). Read opcode D6 (A5 04 D6 7F), write opcode D7 (A4/D7 fragments), both
PROVEN_LIVE for 144.

| Size | Read | Write | ACK |
|---|---|---|---|
| 88 | D6 | D7 | A5 05 D7 00 81 (same) |
| 144 | D6 | D7 | A5 05 D7 00 81 (live) |
| 240 | D6 | D7 | same (static) |
| 280 | D6 | D7 | same (static) |
| 484 | D6 | D7 | same (static) |

(280/484 use the same base_gamepadset/ble_gamepad_set_provider machinery in 2.24;
their D6/D7 builders live in configs_mian/configs_config_only_c1.dart per the
frame-builder scan.)

## Macros / DPI / lighting (separate from config image)

- Macros: /dev/*Macro* server API + A4/D8 fragments (writeMacroConfig,
  gamepadset.dart 2.23 @0x797fa0 region).
- DPI: FC request (getDpi @0x8af8ec / writeDpiConfig @0x7fdee4).
- Lighting: A4/FF fragments (writeLightConfig @0x7f8158).
- Input model: D4 (getInputModel @0x8afa98).
