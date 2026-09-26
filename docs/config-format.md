# ARMORX Pro 144-byte configuration format

## Envelope

A known ARMORX Pro configuration is **144 bytes**:

| Offset | Size | Meaning |
|---:|---:|---|
| 0 | 2 | CRC16, big-endian storage |
| 2 | 2 | declared length, big-endian (`0x0090`) |
| 4 | 108 | controller parameter block |
| 112 | 32 | `mapKeys[32]` |

## CRC

The CRC uses the MODBUS-style polynomial `0xA001` with initial value `0xFFFF`, calculated over bytes `2..143`.

The resulting 16-bit value is stored in bytes `0..1` in big-endian order.

## Known parameter offsets

The current builder exposes these named fields:

| Offset | Field |
|---:|---|
| 4 | `motorSpeedIdx` |
| 5 | `motorMax` |
| 9 | `triggerMode` |
| 10 | `triggerLeftDZCenter` |
| 11 | `triggerLeftDZSide` |
| 12 | `triggerRightDZCenter` |
| 13 | `triggerRightDZSide` |
| 14 | `joystickCircleLimit` |
| 15 | `stickTurn` |
| 16 | `stickLeftDZCenter` |
| 17 | `stickLeftDZSide` |
| 18 | `stickRightDZCenter` |
| 19 | `stickRightDZSide` |
| 20..25 | left-stick curve |
| 28..33 | right-stick curve |
| 36 | `sensorMode` |
| 37 | `sensorDir` |
| 38..39 | sensor right-key fields |
| 40..43 | `sensorRightKeyBit` (u32 BE) |
| 44..49 | sensor curve 0 |
| 52..57 | sensor curve 1 |
| 60..65 | sensor curve 2 |
| 68 | `sensorMin` |
| 69..72 | `sensorSwitch` (u32 BE) |
| 80 | `turboSpeedIdx` |
| 81..84 | `turboKey` (u32 BE) |
| 112..143 | `mapKeys[32]` |

Unknown and reserved bytes are preserved when patching a template.

## Why patching a known-good template is preferred

A freshly generated config can initialize unknown bytes to zero, but those bytes may have firmware-specific meaning. For practical use, prefer:

```bash
python tools/armorx_config.py patch known-good.json \
  --set 'mapKey[M1]=A' \
  -o modified.json
```

This preserves all unknown fields while recalculating the length and CRC.

## Validation

```bash
python tools/armorx_config.py validate config.json
```

## Decode

```bash
python tools/armorx_config.py decode config.json -o decoded.json
```

## Factory templates and other sizes (2026-09-25)

The 2.23 app embeds factory-default templates for 88/144/240-byte configs, and 2.24 adds 280/484-byte families (C1 Pro-class devices, not ARMOR-X Pro). The live ARMOR-X Pro device image matched the embedded 144-byte template `bc536085f138a2ed…` except that the app recomputed the CRC (0x7F67) before sending. Extracted reproducibly by `scripts/extract_default_configs.py` into `research/default-config-templates.json`; analysis in `research/default-config-analysis.md`. The app derives the effective configuration length from the reassembled D6 payload (checkConfigLength; 0xFE padding terminator), not from a dedicated device-reported length field. A4 frame length byte = total frame bytes (chunk+5). ARMOR-X Pro remains 144 bytes.

## Current confidence

The 144-byte envelope, CRC behavior, mapping region, and listed field offsets are implemented as current research findings. Unknown fields are explicitly left unresolved rather than assigned speculative names.


## Captured structured share serialization

Captured `/dev/shareConfig` traffic for the 144-byte ArmorX Pro format adds evidence about the app's structured serializer:

- `res2` is a 38-byte array that mirrors raw bytes **74..111** exactly.
- This region overlaps known fields such as `turboSpeedIdx` at byte 80 and `turboKey` at bytes 81..84, so `res2` is a backing/raw region, not a reserved-only range.
- `crc` in structured share JSON is serialized as a signed 16-bit integer, while the raw config stores the same bits as two big-endian bytes.
- u32 fields such as `sensorRightKeyBit`, `sensorSwitch`, and `turboKey` are serialized by the captured client as lowercase hexadecimal strings without a `0x` prefix.
- Server storage accepts raw 144-byte configs even when bytes 0..1 contain a stale or zero CRC; device-write code should still regenerate the CRC before sending a config to hardware.

The precise placement/meaning of the separate six-byte structured field named `res` remains **UNKNOWN**.


## Live BLE confirmation — 2026-09-25

A captured normal Android/BLE session independently confirmed the device-side 144-byte image and CRC behavior:

- D6 returns one complete 144-byte config image.
- D7 writes one complete 144-byte config image even for a one-byte logical edit.
- Every captured outbound D7 image carried a valid CRC-16/MODBUS-style value over bytes 2..143, stored big-endian in bytes 0..1.
- Controlled profile switching changed only the CRC plus byte 45, already named `sensorRightCurve0YDivx`, from `0x0A` to `0x28`.
- Controlled rear-button remapping M1 -> A changed only the CRC plus byte 135. Since `mapKeys` begins at 112 and M1 is source ID 23, `112 + 23 = 135`; the value changed `0x17 -> 0x00` (M1 -> A).

This live capture therefore confirms the serialized mapping direction:

```text
mapKeys[source_button_id] = target_button_id
```

The BLE transport details are documented in [android-protocol.md](android-protocol.md).


## Live persistence behavior — 2026-09-26

A controlled BLE power-cycle experiment on firmware 2741 distinguished live application from persistence:

- D7 wrote a complete valid 144-byte image.
- D6 immediately read the written image back exactly.
- When 0E was deliberately omitted, a power cycle restored the previously persisted configuration.
- Repeating the same D7 write followed by `A5 05 0E 00 B8` made the new image survive the power cycle.

For the tested configuration path:

```text
D7 = apply complete config image to live/volatile state
0E = persist the written config across power loss
D6 = read current live config image
```

The test changed only `mapKeys[23]` (M1 target) plus the derived CRC, so unrelated config bytes were held constant.

A separate standalone-vs-controller-attached comparison found the 144-byte D6 image byte-for-byte identical across those two physical states in the tested session.
