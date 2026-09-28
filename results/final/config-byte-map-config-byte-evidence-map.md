# ARMOR-X Pro 144-byte configuration — full byte-by-byte evidence map

Device: REAL ARMOR-X Pro `ARMOR-X Pro_11` / `2D:37:35:6D:66:11`, model `ZJ-XT`, firmware `2741`.
Artifact: **`GamepadSet30` / `GamepadParam30`**, protocol `0x90` (144 bytes), Dart AOT (`MYGT 4.0.8`).

Baseline verified first-hand this pass:
- path `baselines/device/ZJ-XT_2741_2D-37-35-6D-66-11/20260927-170400-baseline-as-found.bin`
- `wc -c` = **144**; `sha256sum` = **`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`** (matches the stored `.sha256` and the manifest).
- durability status **DURABLE_OK** (`results/final/real-config-durability.md`): D7 write -> readback -> settle -> power cycle -> D6 == baseline. **STAGED_OK != DURABLE_OK** is respected throughout; nothing here is regraded from a readback alone.

## Container layout (how offsets were derived — not guessed)

`GamepadSet30::toList` (`blutter_out/asm/moojiang/units/gamepadset.dart`, addr `0x811bc0`, `mygt408` = MYGT 4.0.8) does exactly this:

1. `mov x2, #0x90` + `_GrowableList` -> allocates a **144**-element list (line `17669-17672`).
2. Writes `len>>8` into list index 2 and `len & 0xFF` into list index 3 (`0x811d8c-0x811dc8`).
3. Builds a **108**-element parameter list (`mov x2, #0x6c` `_GrowableList`, `0x811dd0`) and inserts it with
   `replaceRange(start=4, end=112, paramList)` (`mov x2,#4` / `mov x3,#0x70` @`0x813844`, call @`0x81384c`).
4. The ctor (`0x814268`) reads the header with `sublist(0,4)` (`0x8142a4`) and the map with `sublist(112,..)` into `KeyRemapT` (`0x814560-0x81457c`).

Therefore **byte = 4 + param_index**, and **144 = 4 header + 108 param + 32 mapKeys[112..143]**.

Independent corroboration: the app's hard-coded 144-byte default blob (`define.dart`, the
`"[0,0,0,144,51,255,...,31]"` literal) aligns **index-for-index with the live device buffer at 133 of 144
positions**; the 11 differences are all expected (`0,1` = the runtime CRC; the device's zeroed trigger/stick
deadzones; `sensorMode`; and the two real mapKeys remaps at 135/136). That triple-agreement (code offsets,
default blob, live bytes) is what lifts most of the table from INFERRED to PROVEN.

## CRC (bytes 0-1) — recomputed here

- Field: **CRC-16/MODBUS**, stored **big-endian at bytes 0-1**.
- Coverage: **bytes 2..143** (`sublist(2, len)` @`0x813a24`, len = 144). Initial value **0xFFFF**, polynomial **0xA001**.
- Arithmetic (reproduced this pass on the real files):

```
crc16_modbus(init=0xFFFF, poly=0xA001, data=baseline[2:144]) = 0x2c40  == stored baseline[0:2] = 0x2c40  OK
crc16_modbus(init=0xFFFF, poly=0xA001, data=mutant[2:144])   = 0xbfd4  == stored mutant[0:2]   = 0xbfd4  OK
```

- Code proof: `GamepadSet30::toList` runs the bitwise loop `x4 = crc ^ byte; for 8: x4 = (x4>>1) ^ 0xA001 | x4>>1`
  (`0x813a5c-0x813ac4`, `init 0xFFFF` @`0x813a40`, `poly 0xA001` @`0x813a98`), then stores
  `(crc & 0xFF00) >> 8` at index 0 and `crc & 0xFF` at index 1 (`0x813ad4-0x813b24`).
- Prior docs called bytes 0-1 an "unknown header"; that is now **resolved**: it is the config CRC.

## Length (bytes 2-3)

`u16` big-endian, value **0x0090 = 144**, read live and written by `toList` as `len>>8` / `len&0xFF`. PROVEN STATIC + PROVEN LIVE.

## Full byte table

| bytes | len | field | encoding | grade |
|---|---|---|---|---|
| 0-1 | 2 | config_checksum_crc | CRC-16/MODBUS big-endian (poly 0xA001, init 0xFFFF, over bytes 2..143) | **PROVEN STATIC** |
| 2-3 | 2 | config_length | u16 big-endian total length | **PROVEN STATIC** |
| 4 | 1 | field_static_0xb5c (toolkit: motorSpeedIdx) | byte, written from a Dart global static | **PROVEN STATIC** |
| 5 | 1 | motorMax | byte | **PROVEN STATIC** |
| 6-8 | 3 | UNKNOWN | 3 raw bytes | **UNKNOWN** |
| 9 | 1 | triggerMode | byte enum | **PROVEN STATIC** |
| 10-11 | 2 | triggerLeftDeadzone (center,side) | 2 bytes (Axis2) | **PROVEN STATIC** |
| 12-13 | 2 | triggerRightDeadzone (center,side) | 2 bytes (Axis2) | **PROVEN STATIC** |
| 14 | 1 | joystickCircleLimit | byte | **PROVEN STATIC** |
| 15 | 1 | stickTurn | byte | **PROVEN STATIC** |
| 16-17 | 2 | stickLeftDeadzone (center,side) | 2 bytes (Axis2) | **PROVEN STATIC** |
| 18-19 | 2 | stickRightDeadzone (center,side) | 2 bytes (Axis2) | **PROVEN STATIC** |
| 20-25 | 6 | stickLeftCurve | 3 x Axis2 (x,y) points | **PROVEN STATIC** |
| 26-27 | 2 | UNKNOWN | 2 bytes | **UNKNOWN** |
| 28-33 | 6 | stickRightCurve | 3 x Axis2 (x,y) points | **PROVEN STATIC** |
| 34-35 | 2 | UNKNOWN | 2 bytes | **UNKNOWN** |
| 36 | 1 | sensorMode | byte enum | **PROVEN STATIC** |
| 37 | 1 | sensorDir | byte enum | **PROVEN STATIC** |
| 38 | 1 | sensorRightKey0 | byte key code | **PROVEN STATIC** |
| 39 | 1 | sensorRightKey1 | byte key code | **PROVEN STATIC** |
| 40-43 | 4 | sensorRightKeyBit | u32 big-endian (from a hex String field) | **PROVEN STATIC** |
| 44-49 | 6 | sensorRightCurve0 | 3 x Axis2 | **PROVEN STATIC** |
| 50-51 | 2 | UNKNOWN | 2 bytes | **UNKNOWN** |
| 52-57 | 6 | sensorRightCurve1 | 3 x Axis2 | **PROVEN STATIC** |
| 58-59 | 2 | UNKNOWN | 2 bytes | **UNKNOWN** |
| 60-65 | 6 | sensorRightCurve2 | 3 x Axis2 | **PROVEN STATIC** |
| 66-67 | 2 | UNKNOWN | 2 bytes | **UNKNOWN** |
| 68 | 1 | sensorMin | byte | **PROVEN STATIC** |
| 69-72 | 4 | sensorSwitch | u32 big-endian (from a hex String field) | **PROVEN STATIC** |
| 73-75 | 3 | UNKNOWN | 3 bytes | **UNKNOWN** |
| 76-79 | 4 | UNKNOWN | 4 bytes | **UNKNOWN** |
| 80 | 1 | field_static_0xb60 (toolkit: turboSpeedIdx) | byte, written from a Dart global static | **PROVEN STATIC** |
| 81-84 | 4 | turboKey | u32 big-endian (from a hex String field) | **PROVEN STATIC** |
| 85-93 | 9 | UNKNOWN (0xF0-branch only) | 9 bytes | **UNKNOWN** |
| 94-111 | 18 | UNKNOWN | 18 bytes | **UNKNOWN** |
| 112-143 | 32 | mapKeys[32] | 1 byte per source slot: mapKeys[source_id] = target_id | **PROVEN LIVE** |

## Per-field detail

### bytes 0-1 — config_checksum_crc  (PROVEN STATIC)
- encoding: CRC-16/MODBUS big-endian (poly 0xA001, init 0xFFFF, over bytes 2..143)
- evidence: static/blutter 4.0.8 mygt408 units/gamepadset.dart:20137-20212 (GamepadSet30::toList CRC loop); baselines/device/.../20260927-170400-baseline-as-found.bin
- changed_by (any experiment): recomputed on any change to bytes>=2 (observed in id15 mutant: 0x2c40->0xbfd4)
- notes: Independently reproduced by arithmetic on BOTH real buffers (baseline 0x2c40==0x2c40; mutant 0xbfd4==0xbfd4). Prior docs labelled this 'header, semantics UNKNOWN' - now PROVEN. PROVEN LIVE corroboration.

### bytes 2-3 — config_length  (PROVEN STATIC)
- encoding: u16 big-endian total length
- evidence: gamepadset.dart:17796-17798 (toList writes len>>8@idx2, len&0xFF@idx3); ctor sublist(0,4) @0x8142a4; live D6 reads 0x0090
- changed_by (any experiment): -
- notes: toList writes len>>8 at list index 2 and len&0xFF at index 3. Live value 0x0090=144 matches the real 144-byte buffer.

### bytes 4 — field_static_0xb5c (toolkit: motorSpeedIdx)  (PROVEN STATIC)
- encoding: byte, written from a Dart global static
- evidence: gamepadset.dart:17928-17940 (toList param idx0 <- LoadStaticField(0xb5c) @0x811ef8); default blob define.dart idx4=51
- changed_by (any experiment): -
- notes: Byte (param index 0 -> config byte 4). Live value 0x33=51 equals the app default blob index 4. App field NAME not provable (no GamepadParam30 field); toolkit name INFERRED.

### bytes 5 — motorMax  (PROVEN STATIC)
- encoding: byte
- evidence: gamepadset.dart:17948-17978 (param idx1 <- pa.field_7); default blob idx5=255; live byte5=0xFF
- changed_by (any experiment): -
- notes: Live 0xFF=255 == default blob index 5. NAME from GamepadParam30.field_7 / toolkit.

### bytes 6-8 — UNKNOWN  (UNKNOWN)
- encoding: 3 raw bytes
- evidence: no writer in toList, no reader in ctor (params 2,3,4)
- changed_by (any experiment): -
- notes: Never written or read in the protocol-0x90 path. Zero in all observed buffers.

### bytes 9 — triggerMode  (PROVEN STATIC)
- encoding: byte enum
- evidence: gamepadset.dart:17996-18002 (param idx5 <- pa.field_f); default idx9=0
- changed_by (any experiment): -

### bytes 10-11 — triggerLeftDeadzone (center,side)  (PROVEN STATIC)
- encoding: 2 bytes (Axis2)
- evidence: gamepadset.dart:18012-18049 (param idx6,7 <- pa.field_13.field_7/.field_b)
- changed_by (any experiment): -
- notes: Device live 0,0 vs default 10,5 (device zeroed these). Offset proven by code, not by value.

### bytes 12-13 — triggerRightDeadzone (center,side)  (PROVEN STATIC)
- encoding: 2 bytes (Axis2)
- evidence: gamepadset.dart:18067-18112 (param idx8,9 <- pa.field_17)
- changed_by (any experiment): -
- notes: Same as left; device live 0,0.

### bytes 14 — joystickCircleLimit  (PROVEN STATIC)
- encoding: byte
- evidence: gamepadset.dart:18122 (param idx10 <- pa.field_1b)
- changed_by (any experiment): -

### bytes 15 — stickTurn  (PROVEN STATIC)
- encoding: byte
- evidence: gamepadset.dart:18146 (param idx11 <- pa.field_1f)
- changed_by (any experiment): -

### bytes 16-17 — stickLeftDeadzone (center,side)  (PROVEN STATIC)
- encoding: 2 bytes (Axis2)
- evidence: gamepadset.dart:18170-18215 (param idx12,13 <- pa.field_23)
- changed_by (any experiment): -
- notes: Default center 15; live 0 (device uses 0). Byte 16/18 mismatch vs default noted.

### bytes 18-19 — stickRightDeadzone (center,side)  (PROVEN STATIC)
- encoding: 2 bytes (Axis2)
- evidence: gamepadset.dart:18225-18270 (param idx14,15 <- pa.field_27)
- changed_by (any experiment): -

### bytes 20-25 — stickLeftCurve  (PROVEN STATIC)
- encoding: 3 x Axis2 (x,y) points
- evidence: gamepadset.dart:18280-18373 (param idx16-21 <- pa.field_2b)
- changed_by (any experiment): -
- notes: Live 01 00 1e 1e 46 46 = 1,0,30,30,70,70 == default blob idx20-25. STRONG live corroboration.

### bytes 26-27 — UNKNOWN  (UNKNOWN)
- encoding: 2 bytes
- evidence: params 22,23 unwritten/unread
- changed_by (any experiment): -

### bytes 28-33 — stickRightCurve  (PROVEN STATIC)
- encoding: 3 x Axis2 (x,y) points
- evidence: gamepadset.dart:18431-18524 (param idx24-29 <- pa.field_2f)
- changed_by (any experiment): -
- notes: Live 01 00 1e 1e 46 46 == default idx28-33.

### bytes 34-35 — UNKNOWN  (UNKNOWN)
- encoding: 2 bytes
- evidence: params 30,31 unwritten/unread
- changed_by (any experiment): -

### bytes 36 — sensorMode  (PROVEN STATIC)
- encoding: byte enum
- evidence: gamepadset.dart:18582 (param idx32 <- pa.field_33)
- changed_by (any experiment): -
- notes: Live byte36=0x02; default blob idx36=0 (device uses 2).

### bytes 37 — sensorDir  (PROVEN STATIC)
- encoding: byte enum
- evidence: gamepadset.dart:18606 (param idx33 <- pa.field_37)
- changed_by (any experiment): -

### bytes 38 — sensorRightKey0  (PROVEN STATIC)
- encoding: byte key code
- evidence: gamepadset.dart:18630 (param idx34 <- pa.field_3b); live=2 default=2
- changed_by (any experiment): -

### bytes 39 — sensorRightKey1  (PROVEN STATIC)
- encoding: byte key code
- evidence: gamepadset.dart:18654 (param idx35 <- pa.field_3f); live=2 default=2
- changed_by (any experiment): -

### bytes 40-43 — sensorRightKeyBit  (PROVEN STATIC)
- encoding: u32 big-endian (from a hex String field)
- evidence: gamepadset.dart:18678-18712 (param idx36-39 <- int.parse(pa.field_43,radix:16)>>24..&0xFF)
- changed_by (any experiment): -

### bytes 44-49 — sensorRightCurve0  (PROVEN STATIC)
- encoding: 3 x Axis2
- evidence: gamepadset.dart:18843-18936 (param idx40-45 <- pa.field_47)
- changed_by (any experiment): -
- notes: Live 00 0a 3c 3c 2a 00 == default idx44-49 (0,10,60,60,42,0).

### bytes 50-51 — UNKNOWN  (UNKNOWN)
- encoding: 2 bytes
- evidence: params 46,47 unwritten/unread
- changed_by (any experiment): -

### bytes 52-57 — sensorRightCurve1  (PROVEN STATIC)
- encoding: 3 x Axis2
- evidence: gamepadset.dart:18994-19087 (param idx48-53 <- pa.field_4b)
- changed_by (any experiment): -

### bytes 58-59 — UNKNOWN  (UNKNOWN)
- encoding: 2 bytes
- evidence: params 54,55 unwritten/unread
- changed_by (any experiment): -

### bytes 60-65 — sensorRightCurve2  (PROVEN STATIC)
- encoding: 3 x Axis2
- evidence: gamepadset.dart:19145-19238 (param idx56-61 <- pa.field_4f)
- changed_by (any experiment): -

### bytes 66-67 — UNKNOWN  (UNKNOWN)
- encoding: 2 bytes
- evidence: params 62,63 unwritten/unread
- changed_by (any experiment): -

### bytes 68 — sensorMin  (PROVEN STATIC)
- encoding: byte
- evidence: gamepadset.dart:19296 (param idx64 <- pa.field_53) @0x813044
- changed_by (any experiment): -

### bytes 69-72 — sensorSwitch  (PROVEN STATIC)
- encoding: u32 big-endian (from a hex String field)
- evidence: gamepadset.dart:19320-19476 (param idx65-68 <- int.parse(pa.field_57,radix:16)>>24..&0xFF)
- changed_by (any experiment): -

### bytes 73-75 — UNKNOWN  (UNKNOWN)
- encoding: 3 bytes
- evidence: params 69,70,71 unwritten/unread
- changed_by (any experiment): -

### bytes 76-79 — UNKNOWN  (UNKNOWN)
- encoding: 4 bytes
- evidence: params 72,73,74,75 unwritten/unread
- changed_by (any experiment): -
- notes: Prior doc mislabelled byte 76 as turboSpeedIdx; correct offset is byte 80 (param idx76). Bytes 76-79 have no writer.

### bytes 80 — field_static_0xb60 (toolkit: turboSpeedIdx)  (PROVEN STATIC)
- encoding: byte, written from a Dart global static
- evidence: gamepadset.dart:19490-19494 (param idx76 <- LoadStaticField(0xb60) @0x81325c); toolkit names it turboSpeedIdx
- changed_by (any experiment): -
- notes: Byte (param idx76 -> config byte 80). Name INFERRED (no GamepadParam30 field). Corrects the prior 'byte 76' label.

### bytes 81-84 — turboKey  (PROVEN STATIC)
- encoding: u32 big-endian (from a hex String field)
- evidence: gamepadset.dart:19490-19560 (param idx77,78,79,80 <- int.parse(pa.field_5b,radix:16)); live bytes 81-84 = 00 00 00 00
- changed_by (any experiment): -
- notes: param idx77-80 -> config bytes 81-84. Corrects the prior '77-80' label (off by 4). Confirmed by the parse loop.

### bytes 85-93 — UNKNOWN (0xF0-branch only)  (UNKNOWN)
- encoding: 9 bytes
- evidence: written only in the protocol==0xF0 (240-byte) branch, gamepadset.dart:0x813564-0x813774
- changed_by (any experiment): -
- notes: Not populated for the 144-byte protocol. Exact f0/0x90 split of this run is inferred from addresses; boundary +/- a byte not proven.

### bytes 94-111 — UNKNOWN  (UNKNOWN)
- encoding: 18 bytes
- evidence: no writer in toList nor reader in ctor (params 90-107)
- changed_by (any experiment): -
- notes: Likely reserved/padding. All zero in every observed buffer.

### bytes 112-143 — mapKeys[32]  (PROVEN LIVE)
- encoding: 1 byte per source slot: mapKeys[source_id] = target_id
- evidence: gamepadset.dart:20112-20128 (toList replaceRange(112,...,KeyRemapT::list)) + ctor sublist(112,..)->KeyRemapT @0x81468c; live D6 identity 0..31; real-config-semantic-map.md; id15 mutant readback
- changed_by (any experiment): byte 127 changed by the D7 id15 mutant write (source slot 15: 0x0F -> 0x02); live bytes 135,136 already remapped (0x01,0x0D) in the as-found baseline
- notes: Region structure PROVEN (code + live identity default at bytes 112-143 == 0..31). Individual slot semantics from the live D2 key-id map. Slot 15 behaviour under the controlled byte-127 write was INCONCLUSIVE (no operator verdict) -> slot-15 semantics INFERRED.

## Controlled differences actually available in the project

The task asked for *every* historical controlled difference. There is essentially **one** byte-level
controlled difference in the whole project, and it lands in the mapKeys region:

| experiment | bytes changed | meaning |
|---|---|---|
| baseline vs id15 mutant | `{0,1,127}` | byte 127 (mapKeys source slot 15) set to `0x02`; bytes 0,1 are the CRC consequence |
| no-op D7 write then readback | none | readback == baseline (staging check only) |
| id15 restore / D2 / official-vs-harness D6 readbacks | none | all equal baseline |
| as-found device vs app default blob | `{0,1,10,11,12,13,16,18,36,135,136}` | confirms the layout; not a write experiment |

Consequence for grading: **no experiment in the project changes any byte outside 0..1 and 112..143.** Every
other field's identity rests on the static code plus the default-blob alignment — which is why those are
graded PROVEN STATIC (code is decisive) rather than PROVEN LIVE (no live *differentiation* was ever recorded).
The single live-controlled data byte (127) is graded INFERRED for its *behavioural semantics* because the
operator verdict for that test was never collected (`results/final/real-key-id-map.md` §4).

## Corrections to prior documents

- bytes 0-1 are a CRC-16/MODBUS, not an "unknown header" (`config-144-reconstruction.md` / `config-field-map.json`).
- `turboSpeedIdx` is at **byte 80** (param idx76), not byte 76.
- `turboKey` is at **bytes 81-84** (param idx77-80), not bytes 77-80.
  Both were 4 too low in the prior table (the `+4` header shift was applied everywhere except these two rows);
  the prior cross-check line ("80 turboSpeedIdx, 81-84 turboKey") was already correct.

## Every byte still UNKNOWN

47 of 144 bytes have no located writer or reader for the 144-byte (0x90) protocol. All are `0x00` in every
observed buffer, so they read as reserved/padding, but that is not proof of their meaning:

| bytes | len | reason |
|---|---|---|
| 6-8 | 3 | param indices 2,3,4 neither written by `toList` nor read by the ctor |
| 26-27 | 2 | param 22,23 unwritten/unread (gap inside the stick-curve area) |
| 34-35 | 2 | param 30,31 unwritten/unread |
| 50-51 | 2 | param 46,47 unwritten/unread |
| 58-59 | 2 | param 54,55 unwritten/unread |
| 66-67 | 2 | param 62,63 unwritten/unread |
| 73-75 | 3 | param 69,70,71 unwritten/unread |
| 76-79 | 4 | param 72,73,74,75 unwritten/unread |
| 85-93 | 9 | written only in the `protocol==0xF0` (240-byte) branch (`0x813564+`), not in the 0x90 path |
| 94-111 | 18 | no writer in `toList`, no reader in the ctor (params 90-107) |

No byte is graded CONTRADICTED. `motorMin` (a declared `GamepadParam30` field) is **never parsed** from this
block, so bytes 6-8 are **not** `motorMin` — that would be an inference from a declared-but-unused field.

## Totals

- PROVEN (LIVE + STATIC): **97 bytes** — 32 (mapKeys region, PROVEN LIVE structure) + 65 (header + param block, PROVEN STATIC).
- UNKNOWN: **47 bytes**.
- INFERRED-only names: byte 4 `motorSpeedIdx`, byte 80 `turboSpeedIdx`, and mapKeys slot-15 behaviour.
- CONTRADICTED: 0.
- Method: offline only — the baseline was hashed and measured, both real buffers were diffed, and the arithmetic re-run locally; no device write, no git state change, baseline files untouched.
