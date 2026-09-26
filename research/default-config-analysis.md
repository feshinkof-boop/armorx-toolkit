# Default configuration templates — extracted and verified — 2026-09-25

Source: Blutter `pp.txt` string pools for com.moojiang.bigbigwon 2.23.0609 and 2.24.0919
(arm64-v8a). Extracted by `scripts/extract_default_configs.py` (deterministic; envelope
rule: bytes 0..1 = CRC16 big-endian, bytes 2..3 = declared length big-endian equal to list
length). All CRCs recomputed independently with CRC-16/MODBUS (init 0xFFFF, poly 0xA001,
input bytes 2..end).

## Template inventory

### 2.23.0609 (4 templates)

| # | Length | Declared | Stored CRC | Recomputed | Valid | SHA256 (first 16) |
|---|---|---|---|---|---|---|
| 1 | 88 | 88 | 0x0000 | 0xC800 | recomputed at write | 9eaea1d6a42c49a4 |
| 2 | 144 | 144 | 0x0000 | 0x848A | recomputed at write | 1fa5afe2401d17c2 |
| 3 | 144 | 144 | 0x0000 | 0x7F67 | recomputed at write | bc536085f138a2ed |
| 4 | 240 | 240 | 0x1605 | 0x1605 | **VALID** | 4baf590a1d3d48ad |

### 2.24.0919 (8 templates)

| # | Length | Declared | Stored CRC | Recomputed | Valid | SHA256 (first 16) |
|---|---|---|---|---|---|---|
| 1 | 88 | 88 | 0x0000 | 0xC800 | recomputed at write | 9eaea1d6a42c49a4 |
| 2 | 144 | 144 | 0x0000 | 0x848A | recomputed at write | 1fa5afe2401d17c2 |
| 3 | 144 | 144 | 0x0000 | 0x7F67 | recomputed at write | bc536085f138a2ed |
| 4 | 240 | 240 | 0x0000 | 0x6AC7 | recomputed at write | a2dabf5bec6afe49 |
| 5 | 240 | 240 | 0x1605 | 0xBC3A | stale (mismatch) | 96dd901075496924 |
| 6 | 240 | 240 | 0x198B | 0x198B | **VALID** | 47c992112178bc82 |
| 7 | 280 | 280 | 0x0000 | 0x878D | recomputed at write | 8f318f88caedb66b |
| 8 | 484 | 484 | 0xD0A4 | 0xD0A4 | **VALID** | a61757a34cbdc20f |

The 88/144/144 templates are byte-identical across both app versions (same SHA256).
2.24 drops nothing and adds: a zero-CRC 240 variant, a 0x1605-stale-CRC 240 variant, a
valid 240 variant (0x198B), a 280 variant, and a 484 variant.

## Key findings

1. **CRC algorithm independently proven from static data alone**: templates 4 (2.23),
   6 and 8 (2.24) ship precomputed CRCs that self-validate under CRC-16/MODBUS over
   bytes 2..end with big-endian storage. No live capture needed.
2. **ARMOR-X Pro device family template identified by live cross-correlation**: the live
   ARMOR-X Pro (ZJ-XT, firmware 2741... captured as V41-era session) config image
   reassembled from captured D7 fragments equals template `bc536085f138a2ed`
   (144-byte, stored CRC 0x0000) except bytes 0..1: the app wrote CRC 0x7F67, exactly
   the recomputed CRC of the template body. The device's live config at capture time was
   byte-for-byte the factory default 144-byte image in template 3.
3. **Templates with stored CRC 0x0000 are recomputed at write time** by
   `GamepadSet30::toList` @0x7a0530 (2.23): the serializer writes the computed CRC into
   bytes 0..1 before fragmentation.
4. **Template selection** (2.23 `defaultConfig` @0x803ba0): branches on `curDevice.type`
   (1=Rainbow → 88; 2..5 → 144/240 per static config-length field; 6=ARMOR-X Pro →
   144/240 per config-length field) and on static field 0xfd8 (config length) for
   144-vs-240. `1fa5afe2` (144) differs from `bc536085` (144) at offsets 10-13, 16, 18, 36
   (trigger deadzones, stick deadzones, sensorMode) — Rainbow vs ArmorX-family parameter
   defaults. Live evidence pins `bc536085` to ARMOR-X Pro.
5. **Config-length static field is derived, not device-reported**: `parsingData`
   (rainbow_tab_config_1s.dart @0x8098cc) calls `checkConfigLength` @0x810a34 and stores
   the result into static 0xfd8. checkConfigLength: `if (list.length < 240) return
   list.length; if (list.contains(-2) && list.length == 240) return 240; return
   list.indexOf(-2)` — where -2 is the Dart signed representation of wire byte 0xFE
   (padding terminator). So the app derives the effective configuration length from the
   reassembled D6 payload; for ARMOR-X Pro live traffic the image is exactly 144 bytes,
   shorter than 240, so the static is 144.
