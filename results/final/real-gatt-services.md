# Real ARMOR-X Pro GATT service table (canonical)

Source: live Bumble GATT discovery + reads, 2026-09-27 (`results/experiments/physical-20260927-174445-buttons/session.jsonl`).
Machine-readable companion: `real-gatt-services.json`. Evidence level: **PROVEN LIVE** (REAL ARMOR-X).

Device: advertised `ARMOR-X Pro_11`, BLE address `2D:37:35:6D:66:11`, model mark `ZJ-XT`, firmware `2741`.

| service | name | member characteristics |
|---|---|---|
| `00001800-0000-1000-8000-00805f9b34fb` | 1800 Generic Access | `2A00` Device Name, `2A01` Appearance, `2A04` Preferred Connection Parameters |
| `00001801-0000-1000-8000-00805f9b34fb` | 1801 Generic Attribute | `2A05` Service Changed |
| `0000180a-0000-1000-8000-00805f9b34fb` | 180A Device Information | `2A23` System ID, `2A24` Model Number, `2A25` Serial Number, `2A26` Firmware Revision, `2A27` Hardware Revision, `2A28` Software Revision, `2A29` Manufacturer Name, `2A2A` IEEE 11073-20601, `2A50` PnP ID |
| `0000180f-0000-1000-8000-00805f9b34fb` | 180F Battery Service | `2A19` Battery Level |
| `00000000-0000-1000-8000-00805f9b34fb` | vendor/config service | **`FFE1` write**, **`FFE2` notify/read** |
| `0000ae00-0000-1000-8000-00805f9b34fb` | **AE00 JieLi RCSP-compatible service** | **`AE01` write**, **`AE02` notify/indicate** |

Totals: 6 services, 18 characteristics.

## Live values read (REAL device)

| characteristic | raw | decoded |
|---|---|---|
| `2A24` Model Number String | `5a 4a 2d 58 54` | `ZJ-XT` |
| `2A26` Firmware Revision String | `32 37 34 31` | `2741` |
| `2A19` Battery Level | `41` | 65 % (earlier in the day: `44` = 68 %) |

Note on the **E2** reply: it carries the firmware as **BCD** (`0x27 0x41`), not ASCII — see
`tests/test_real_device_vectors.py::test_live_e2_reply_carries_firmware_and_model_strings`.

## AE00/AE01/AE02 — JieLi RCSP-compatible service

- Presence on the **real** device: **PROVEN LIVE** (enumerated above; the same table appears
  across independent connections).
- Use of RCSP by the official apps in the four analysed builds: **NOT PROVEN / app-negative**.
- No RCSP or OTA command has been sent to the device, and none will be without byte-level
  evidence from an independent implementation.

## Caveat / open item

Characteristic **properties** were not captured by the Bumble session log (it recorded UUID
lists). The independent BlueZ/bleak path (`real-gatt-services-bleak.json`) is the intended
source for properties, descriptors and handles; its first run found no advertisement because
the unit had auto-powered-off. That file will be filled on the next run with the unit awake.
