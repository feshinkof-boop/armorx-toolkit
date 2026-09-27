# Real ARMOR-X Pro protocol contract (as proven on the physical unit)

Evidence labels: **PROVEN LIVE** (observed on the real unit in this project),
**PROVEN STATIC** (read out of the app's Dart AOT / vendor tooling), **STRONG EVIDENCE**,
**INFERRED**, **UNKNOWN**, **CONTRADICTED**.

## 1. Transport

- BLE GATT. Configuration channel: service `00000000-0000-1000-8000-00805f9b34fb`,
  **`FFE1` write**, **`FFE2` notify/read** — PROVEN LIVE (the entire conversation below ran there).
- A JieLi RCSP-compatible service `AE00`/`AE01`/`AE02` is also present (PROVEN LIVE) but is **not**
  the configuration path (app-negative, see `jieli-rcsp-verdict.md`).
- ATT MTU negotiated: 247 requested by the lab client.

## 2. Frame families

### 2.1 Short frames (`A5`)

```
A5 <len> <opcode> <payload...> <checksum>
```
- `<len>` = total frame length including header and checksum (e.g. `A5 05 0B 30 E5` → 5 bytes).
- checksum = sum8 of bytes `0..n-2` (verified on every captured frame in the regression vectors).

Proven opcodes on the real unit:

| opcode | direction | frame | meaning |
|---|---|---|---|
| `0x0B` | TX/RX | `A5 04 0B B4` → `A5 05 0B 30 E5` | version/link-health query |
| `0xD2` | TX | `A5 05 D2 01 7D` / `A5 05 D2 00 7C` | D2 raw-event test mode ON / OFF (acked by echo) |
| `0xD4` | TX/RX | `A5 04 D4 7D` → `A5 07 D4 11 01 00 92` | mode query (see `real-d4-e2.md` for the recorded conflict) |
| `0xD6` | TX | `A5 04 D6 7F` | read configuration (answered by `A4` fragments) |
| `0xE2` | TX/RX | `A5 04 E2 8B` → `A5 10 E2 27 41 02 "ZJ-XT" 00 00 00 00 7E` | firmware/model read (firmware is **BCD**) |
| `0xFC` | TX/RX | `A5 05 FC 80 26` → `A5 05 FF FC A5` | DPI query / reply |
| `_` | TX/RX | `A5 05 05 25 DA`, `A5 05 05 26 DB` | AB motion/gyro queries → **no reply** on this firmware |
| `0x02` | RX | `A5 12 02 …` | D2 status frame carrying the 32-bit key mask |

### 2.2 Fragment frames (`A4`)

```
A4 <total frame length> <opcode> <ordinal> <payload...> <checksum>
```
- `<total frame length>` includes header and checksum: `0x14` = 20 bytes.
- `<ordinal>` is **1-based**; reassembly must strip it (`emergency-restore.py` does).
- Configuration image is **144 bytes** (`0x0090` declared), split into 9×20-byte + 1×14-byte frames.
- Fragment payload class for this unit: **15 bytes** (`subpackageLength()` = 20), determined from
  both static code and live frames — see `real-d8.md`.
- Configuration commit/terminator: `A4 05 D8 <nfrags+1> <checksum>`. The old `A4 0A D8` is
  **CONTRADICTED** and must never be emitted. Serializers must not be mixed across generations.

## 3. Configuration image

- 144 bytes; stored big-endian CRC-16/MODBUS at bytes `0..1` (poly `0xA001`, init `0xFFFF`,
  computed over bytes `2..end`); declared length at bytes `2..3` (`0x0090`).
- `mapKeys[0..31]` occupies bytes `112..143`; `source` slot *N* is at absolute offset `112+N`.
- Key-mask rule: **bit == id** (verified: `1<<6 = 0x40`, `1<<15 = 0x8000`, `1<<16 = 0x10000`).
- The unit's as-found baseline maps 30 of 32 slots to themselves; **slot 23 (M1) → target 1 (B)**
  and **slot 24 (M2) → target 13 (L3)** are genuine non-identity mappings.
- Baseline (immutable): `sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`.

## 4. Write discipline (hard gates, both already exercised)

1. **D7 no-op gate** — write the byte-identical baseline, read back with `D6`, require byte
   equality: **PASSED** (`RESTORE_NOOP_VALIDATED = true`, ack `A5 05 D7 00 81`).
2. **Emergency restore** — identity-gated (live `2A24`/`2A26` vs manifest), restore + verified
   readback: **VERIFIED** on this unit.
3. Any mutation must differ from the baseline in the intended bytes **plus the CRC only** — the
   ID-15 experiment's diff was provably `{0, 1, 127}`.

## 5. Unknowns in the contract

- Field semantics of `EF`'s 8 payload bytes: **UNKNOWN** (raw preserved).
- `D4` payload byte 5 (`0x00` in the captured reply) purpose: **UNKNOWN**.
- `E2` payload byte `0x02` before the model string: **UNKNOWN** (not a length).
- Analog field roles `[7]`–`[14]` in the `0x02` status frame: **UNKNOWN** (they move with stick
  input; per-axis mapping not established).
- Whether the unit answers RCSP at all: **UNKNOWN** — deliberately untested.
