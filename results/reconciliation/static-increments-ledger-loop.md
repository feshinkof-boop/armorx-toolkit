# Static increments from the ledger continuation loop (2026-09-27/28)

The master ledger lists, for each unknown, the next *offline* step. This document records the ones that
were actually worked during the shift, with byte-level evidence, and the ones that turned out to be
exhausted by this approach.

## 1. `E2` / `readFirmware` was introduced in 4.0.8 (closes the APK-cross-version gap)

| build | `readFirmware` files | `#0x1c4` (the Smi encoding of `0xE2`) |
|---|---|---|
| 2.22.0901 | **0** | 4 files |
| 2.23.0609 | **0** | 8 files |
| 2.24.0919 | **0** | 9 files |
| 4.0.8 | **3** | 3 files |

The `#0x1c4` hits in the 2.2x builds are **localization table indices**, not frame bytes: the inspected
occurrences are inside `generated/intl/messages_*.dart` as `r0 = 452` used as a string-table offset
(`add x2, x1, w0, sxtw #1` immediately followed by a string load). So the constant appearing is the
known false-positive pattern, and **`readFirmware`/`E2` is present only in 4.0.8** - PROVEN STATIC.

## 2. New: the app's write-result dispatcher enumerates write-capable opcodes

`moojiang/widgets/general/frame_config_macros.dart` (4.0.8) contains an opcode dispatch chain whose
branches build "写入结果" ("write result") messages:

| comparison | Smi | real byte | nearby label |
|---|---|---|---|
| `cmp w0, #0x1fa` | 506 | `0xFD` | - |
| `cmp w0, #0x1f8` | 504 | **`0xFC` (DPI)** | 写入结果 |
| `cmp w0, #0x1b0` | 432 | **`0xD8` (macro)** | 写入结果 |
| `cmp w0, #0x1a6` | 422 | `0xD3` | - |

This is the app's own list of opcodes it expects to produce a **write result** for: `{0xFD, 0xFC, 0xD8,
0xD3}`. It is useful for reading and writing design (it tells us which writes the app itself treats as
acknowledged), and it surfaces two opcodes that were **not** in our catalogue.

## 3. Corroboration: the D6 reply is consumed by the config pages

`cmp w0, #0x1ac` (= Smi of `0xD6`) occurs in `moojiang/widgets/configV484/configs_mian.dart` and
`widgets/configV280/configs_mian.dart`. That is exactly where the D6-application-state branch said the
configuration read lands, and it is **not** the Button Test page - independently consistent with
`D6_APP_STATE_DEPENDENCY_NOT_FOUND` for the D2 path.

## 4. `DPI-U-002` (the DPI *reply* parser): searched, not found by this approach

Both `cmp ... #0x1f8` occurrences reachable from BLE code were inspected:

- `widgets/rainbow/rainbow_more.dart` - inside a UI function; the branch builds the label
  "回报率等级：" ("report-rate level") and calls `setState`. It is a **menu/alert branch**, not a reply parser.
- `widgets/general/frame_config_macros.dart` - the write-result dispatcher in §2.

No reply-side dispatch on `0xFC` (nor on `0xF6`, `#0x1ec`) was found in the notify path. **Recording
this as a performed search with a negative result**, so the next pass does not repeat it: the DPI reply
parser is either reached by a different idiom (opcode-byte extraction rather than Smi compares) or lives
in the generic notification consumers. The remaining productive route is therefore a **live** capture
that varies the DPI selector and watches which byte moves.

## 5. Honest summary of the loop

Worked statically this pass: §1, §2, §3, §4. Result: one gap closed, one new opcode set discovered, one
corroboration, and one route marked as tried-and-cold. Nothing here is claimed beyond what the
disassembly shows, and no hardware was touched.
