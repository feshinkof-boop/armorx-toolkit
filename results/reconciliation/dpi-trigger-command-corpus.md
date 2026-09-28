# DPI / trigger-command corpus (F7, F6, FC)

Generated 2026-09-28 from the four Blutter Dart-AOT trees by `automation/scripts/frame-literal-scan.py`.
A frame literal is an `AllocateArray` + one `StoreField` per element; a stored element is a **tagged
Smi**, so the byte value is the printed immediate halved. `byte[0]` is the header, `byte[1]` the total
frame length, `byte[2]` the opcode and the trailer is `sum8` over the preceding bytes.

**The method is validated by live evidence:** the tool reproduces, byte for byte and checksum for
checksum, the frames real hardware has already answered — `A5 05 FC 80 26` (DPI query; live reply
`A5 05 FF FC A5`), `A5 05 D2 01 7D` / `A5 05 D2 00 7C` (D2 enable/disable, used in every live run) and
`A5 04 0B B4` (the `0B` sanity query).

**Reporting rule:** bytes are only reported as a frame when *every* byte is a static literal
(11 of 20 entries). The other 9
carry runtime-computed lengths or payloads, so only their layout / static prefix is claimed.

## Presence by version

| command | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|---|---|---|---|
| `F7` (step length) | **ABSENT** | **ABSENT** | present (`getStepLength`, `writeStepLengthConfig`) | present (`getStepLength` @0x8b4d30, `writeStepLengthConfig` @0x9445d4) |
| `F6` (legacy DPI) | **ABSENT** | **ABSENT** | present (FC/F6 gate) | present (FC/F6 gate) |
| `FC` (DPI + transcribe) | **ABSENT** | present (`getDpi`, `writeDpiConfig`) | present | present (`getDpi` @0x8b4e3c, `writeDpiConfig` @0x946750, transcribe pair) |

2.22.0901 contains **no** F7/F6/FC frame literal — an exhaustive scan of its `asm/moojiang` tree
returns zero, matching the earlier independent negative for FC in that build.

## Entries

| version | function | addr | dir | frame | len | cks | role | feature | grade |
|---|---|---|---|---|---|---|---|---|---|
| 2.23.0609 | `static _ writeDpiConfig() async` | 0x7fdee4 | TX (app->device) | `A5 05 FC <selector & 0x0F> <cks>` | 5 | - | WRITE | DPI selector | PROVEN STATIC (layout/prefix only) |
| 2.23.0609 | `_ getDpi() async` | 0x8af8ec | TX (app->device) | A5 05 FC 80 26 | 5 | 26 | READ request | DPI | PROVEN STATIC |
| 2.24.0919 | `static _ writeStepLengthConfig() async` | 0x892cf4 | TX (app->device) | `A5 07|08 F7 <flag> <lo> <hi> [<extra>] <cks>` | None | - | WRITE | stick step-length / 'step accuracy' | PROVEN STATIC (layout/prefix only) |
| 2.24.0919 | `static _ writeDpiConfig() async` | 0x894000 | TX (app->device) | `A5 05 FC|F6 <selector & 0x0F> <cks>` | 5 | - | WRITE | DPI selector | PROVEN STATIC (layout/prefix only) |
| 2.24.0919 | `_ stopTranscribe() async` | 0x8293ec | TX (app->device) | `A5 0B FC 00 <8 runtime payload bytes> <cks>` | 11 | - | WRITE (control) | macro transcription stop | PROVEN STATIC (layout/prefix only) |
| 2.24.0919 | `_ startTranscribe() async` | 0x82d038 | TX (app->device) | `A5 0B FC 01 <8 runtime payload bytes> <cks>` | 11 | - | WRITE (control) | macro transcription start | PROVEN STATIC (layout/prefix only) |
| 2.24.0919 | `_ getStepLength() async` | 0x91af58 | TX (app->device) | A5 04 F7 A0 | 4 | A0 | READ request | stick step-length / 'step accuracy' | PROVEN STATIC |
| 2.24.0919 | `_ getDpi() async` | 0x91b090 | TX (app->device) | A5 05 FC 80 26 | 5 | 26 | READ request | DPI | PROVEN STATIC |
| 2.24.0919 | `_ getDpi() async` | 0x91b090 | TX (app->device) | A5 05 F6 80 20 | 5 | 20 | READ request | DPI | PROVEN STATIC |
| 2.24.0919 | `_ getDpi() async` | 0x91b090 | TX (app->device) | A5 04 F6 9F | 4 | 9F | READ request | DPI | PROVEN STATIC |
| 4.0.8 | `_ getStepLength() async` | 0x8b4d30 | TX (app->device) | A5 04 F7 A0 | 4 | A0 | READ request | stick step-length / 'step accuracy' | PROVEN STATIC |
| 4.0.8 | `_ getDpi() async` | 0x8b4e3c | TX (app->device) | A5 05 FC 80 26 | 5 | 26 | READ request | DPI | PROVEN STATIC |
| 4.0.8 | `_ getDpi() async` | 0x8b4e3c | TX (app->device) | A5 05 F6 80 20 | 5 | 20 | READ request | DPI | PROVEN STATIC |
| 4.0.8 | `_ getDpi() async` | 0x8b4e3c | TX (app->device) | A5 04 F6 9F | 4 | 9F | READ request | DPI | PROVEN STATIC |
| 4.0.8 | `static _ writeStepLengthConfig() async` | 0x9445d4 | TX (app->device) | `A5 07|08 F7 <flag:00|01> <value_lo> <value_hi> [<extra>] <cks>` | None | - | WRITE | stick step-length / 'step accuracy' | PROVEN STATIC (layout/prefix only) |
| 4.0.8 | `static _ writeDpiConfig() async` | 0x946750 | TX (app->device) | `A5 05 FC|F6 <selector & 0x0F> <cks>` | 5 | - | WRITE | DPI selector | PROVEN STATIC (layout/prefix only) |
| 4.0.8 | `_ stopTranscribe() async` | 0x9ac304 | TX (app->device) | `A5 0B FC 00 <8 runtime payload bytes> <cks>` | 11 | - | WRITE (control) | macro transcription stop | PROVEN STATIC (layout/prefix only) |
| 4.0.8 | `_ startTranscribe() async` | 0x9afc1c | TX (app->device) | `A5 0B FC 01 <8 runtime payload bytes> <cks>` | 11 | - | WRITE (control) | macro transcription start | PROVEN STATIC (layout/prefix only) |
| 4.0.8 (live) | `BluetoothModel::getDpi` | 0x8b4e3c | TX (app->device) | A5 05 FC 80 26 | 5 | 26 | READ request | DPI | PROVEN LIVE |
| 4.0.8 (live) | `reply to the DPI query` | - | RX (device->app) | A5 05 FF FC A5 | 5 | A5 | REPLY | DPI | PROVEN LIVE |

## Frames whose bytes are not fully static

- `writeDpiConfig` — `A5 05 FC|F6 <selector & 0x0F> <cks>`: the selector is masked to four bits; `F6`
  replaces `FC` when the device is in the F6 model set and the firmware version is `>= 0x35`.
- `writeStepLengthConfig` — `A5 07|08 F7 <flag 00|01> <value_lo> <value_hi> [<extra>] <cks>`: the length
  byte itself is computed (`NN = ((arg & 2) + 14) / 2` → 7 or 8), byte[3] is a boolean flag, bytes[4..5]
  are a 16-bit little-endian value, and the call sites are gated on firmware version `>= 0x36`.
- `startTranscribe` / `stopTranscribe` — `A5 0B FC 01` / `A5 0B FC 00` are the **static prefixes** of
  **11-byte** frames whose remaining 8 bytes are a runtime payload (macro/keystroke data). This is the
  third, DPI-unrelated role of `FC`.

## What is deliberately NOT in this corpus

- **No entry claims F7 is trigger travel.** The strings attached to the step-length feature are
  `step_accuracy_setting` = 「步长精度设置」 with the tip 「步长精度影响**摇杆**的精确度」 ("affects the
  precision of the **stick**"). See `results/final/real-trigger-travel.md` for the refutation.
- No numeric DPI value is assigned to any selector (the preset table is server-side, not in the binary).
- No replay of any captured official-app traffic.
