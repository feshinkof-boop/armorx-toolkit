# Real ARMOR-X Pro identity (REAL device, this unit)

Evidence level: **PROVEN LIVE** unless stated otherwise. This document concerns the
**physical** unit; anything derived from the virtual peripheral is marked VIRTUAL.

| field | value | source |
|---|---|---|
| advertised name | `ARMOR-X Pro_11` | live BLE scan |
| BLE address | `2D:37:35:6D:66:11` (static/random per session — re-resolve each session) | live BLE scan |
| manufacturer data | `fe ff` + ASCII `ZJ-XT` (`5a 4a 2d 58 54`) | advertisement |
| advertisement service UUIDs | **none** (`service_uuids: []`) | advertisement |
| `2A24` Model Number String | `ZJ-XT` (raw `5a4a2d5854`) | live GATT read |
| `2A26` Firmware Revision String | `2741` (raw `32373431`) | live GATT read |
| `2A19` Battery Level | `0x44` = 68 % earlier in the day, `0x41` = 65 % later | live GATT reads |
| device id used for baselines | `ZJ-XT_2741_2D-37-35-6D-66-11` | manifest |

Baseline manifest: `baselines/device/ZJ-XT_2741_2D-37-35-6D-66-11/20260927-170400-baseline-as-found.json`.

## Important identity detail

The **advertisement carries no service UUIDs**, only manufacturer data and the local name.
Service discovery reveals 6 services (including the JieLi `AE00` and the vendor `00000000…`
service with `FFE1`/`FFE2`). Any conclusion drawn from advertisement data alone is invalid —
this mistake was made once, corrected, and is recorded in `jieli-rcsp-verdict.md` §7.

## What identity is NOT

- Central MCU: **UNKNOWN**
- IMU: **UNKNOWN**
- Bluetooth-side silicon evidence (AC6321A/AC632N/BD19 family): **STRONG EVIDENCE / INFERRED**
  from board markings (PCB `XBOX_X V1.4 / 220627`, 24.000 MHz crystal, S9450 charger) plus the
  live `AE00/AE01/AE02` RCSP-compatible service — still not a firmware dump.
