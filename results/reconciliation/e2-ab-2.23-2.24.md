# E2 and AB-family verdicts for 2.23.0609 and 2.24.0919

Reconciliation pass, 2026-09-27. Scope: settle the two opcode families the four-way version
matrix (`results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.{md,json}`) recorded as `UNKNOWN`
for 2.23 and 2.24. `UNKNOWN` there meant "not checked", not "absent" — this file replaces it with
a verdict backed by an exhaustive search.

Trees searched (Blutter Dart-AOT disassembly + object pool):

| build | Dart | tree |
|---|---|---|
| 2.22.0901 | 2.17.5 | `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out` |
| 2.23.0609 | 2.19.6 | `/home/salamanka/armorx/re/blutter_out` |
| 2.24.0919 | 3.2.3 | `/home/salamanka/armorx/re/v224/blutter_out` |
| 4.0.8 | 3.12.2 | `/home/salamanka/armorx-re/mygt408/blutter_out` |

Evidence labels: **PROVEN STATIC** / **STRONG EVIDENCE** / **INFERRED** / **UNKNOWN** /
**CONTRADICTED**. `ABSENT` is used only after a genuinely complete negative search, and the
searches are listed verbatim.

### Dialect note (why the searches look doubled)

A wire byte `B` that is **stored into a frame array** is stored as a tagged Smi, so the `mov`
immediate that writes it is `2·B`: `0xE2`→`#0x1c4`, `0xAB`→`#0x156`, `0xFC`→`#0x1f8`,
`0xF6`→`#0x1ec`, `0xA5`→`#0x14a`. **But a value that has been explicitly untagged first is not.**
The compiler emits `r1 = LoadInt32Instr(r0)` (`sbfx x1, x0, #1, #0x1f`) before integer comparisons
on a static field, and the following `cmp` then carries the **plain** value. This distinction is
load-bearing for the F6 threshold and is worked through in `fc-f6-timeline.md`. Every immediate
below is reported as it literally appears in the asm, and the decoded wire byte is given next to it.

## Methodology caveat found during this pass (audit-relevant)

An early exploratory scan of the **2.24** tree used the relative path `v224/blutter_out` from
`/home/salamanka/armorx`, but the tree actually lives at `/home/salamanka/armorx/re/v224/blutter_out`.
`rg` therefore returned **0** for every pattern on that tree — a silent path miss that looks exactly
like a clean `ABSENT`. All numbers below were re-run with **absolute paths** and cross-checked.
This is a plausible root cause for earlier `UNKNOWN`/spurious-zero findings elsewhere in the
project: a wrong tree path reads as "no hits". Recommend every negative verdict record the
resolved absolute tree path it was run against.

---

## 1. 0xE2 (wire byte 226 = Smi 452 = `#0x1c4`)

### Verdict

| build | verdict | label |
|---|---|---|
| 2.22.0901 | **ABSENT** | PROVEN STATIC (prior pass, `results/static/2.22.0901/e2-verdict.md`) |
| 2.23.0609 | **ABSENT** | PROVEN STATIC (this pass) |
| 2.24.0919 | **ABSENT** | PROVEN STATIC (this pass) |
| 4.0.8 | **PRESENT_SEND** | PROVEN STATIC (`A5 04 E2 8B`, `BluetoothModel::readFirmware` @0x8b6860) |

E2 enters the protocol **only in 4.0.8**. It is not a 2.23 or 2.24 opcode in any form.

### Searches run (2.23 and 2.24)

All commands were run against the absolute tree roots shown above.

| # | question | command | 2.23 result | 2.24 result |
|---|---|---|---|---|
| E2-1 | tagged Smi of the byte, whole tree | `rg -n '#0x1c4\b' <tree>/asm/` | 28 hits | 29 hits |
| E2-1b | …of which inside `asm/moojiang/` | filter `'/moojiang/'` | 8 — **all** in `generated/intl/messages_*.dart` | 9 — **all** in `generated/intl/messages_*.dart` |
| E2-1c | …any `moojiang` hit **outside** `generated/intl/` | `rg … \| grep -v '/generated/intl/'` | **0** | **0** |
| E2-2 | raw immediate `mov reg, #0xe2`, whole tree | `rg -n 'mov +[xw][0-9]+, #0xe2\b' <tree>/asm/` | 31 hits | 31 hits |
| E2-2b | …of which in `asm/moojiang/` outside intl | filter | **0** | **0** |
| E2-3 | dispatcher compare against the byte | `rg -n 'cmp +[xw][0-9]+, #0xe2\b' <tree>/asm/moojiang/` | **0** | **0** |
| E2-4 | decimal 226 in the object pool | `rg -c '\b226\b' <tree>/pp.txt` | **0** | **0** |
| E2-5 | decimal 452 (untagged Smi value) in pool | `rg -c '\b452\b' <tree>/pp.txt` | **0** | **0** |
| E2-6 | a pool `List(n)[…]` literal containing 226 | `rg -oE 'List\([0-9]+\) \[[^]]*\b226\b[^]]*\]' <tree>/pp.txt` | **0** | **0** |
| E2-7 | literal byte sequence `A5 04 E2` in every native `libapp.so` (all ABIs) | Python `bytes.count(b"\xa5\x04\xe2")` | **0** | **0** |
| E2-8 | ditto in `classes.dex` | Python byte scan | **0** | **0** |
| E2-9 | `readFirmware` / `getFirmware` / firmware-named protocol fn | `rg -in 'firmware' <tree>/asm/moojiang/` | only l10n strings (`info_firmware`, `"Firmware Version:"`) and the UI label `"firmwareVer="` @`rainbow_root.dart:2150` — **no builder, no parser** | **no protocol hit** (only l10n strings in `pp.txt`, none in asm) |
| E2-10 | string dumps (`static/strings/2.23-libapp.strings`, `2.24-libapp.strings`) | `rg -in 'readfirmware\|0xe2'` | **0** | **0** |
| E2-11 | command tables / dispatch closures producing 0xE2 | builder census over `asm/moojiang` | **0 producing functions** | **0 producing functions** |

The `A5 04 E2` sequence cannot appear as a literal in `libapp.so` at all: frames are assembled at
runtime by `AllocateArray` + `ArrayStore`, never stored as byte strings. The binary scan (E2-7/E2-8)
is therefore a *supplementary* check; the load-bearing results are E2-1c, E2-2b, E2-3 and E2-11.

### Does E2 hide under a misleading function name?

**No.** The only firmware-version query in 2.23/2.24 is `getZKMVer`, and it emits **0x0B**
(`A5 04 0B B4`) — not E2:

* 2.23: `_RainbowWidget::getZKMVer` @0x800610 (call site @0x8005f0); `_ArmorXProWidgetState::getZKMVer`
  (@`armorx_pro_root.dart:101`, call @0x760ad0).
* 2.24: `_RainbowWidget::getZKMVer` @0x8975d4 (call @0x8975b8); `_ArmorXProWidgetState::getZKMVer`
  (call @0x78b5a0).

In 4.0.8 the E2 byte is emitted by a *differently named* function, `BluetoothModel::readFirmware`
@0x8b6860, while `getZKMVer` still emits 0x0B. So across the whole family E2 is never *renamed*
0x0B and 0x0B is never renamed E2 — there is no aliasing to trip over. The string
`"firmwareVer="` in 2.23 is a UI/telemetry label, not a frame builder.

### Where the byte 0xE2 *does* appear (noise, excluded)

2.23 and 2.24 both bundle third-party code whose small integers collide with 226/0xE2:
`syncfusion_flutter_pdf` (AES/bidi/font tables) and the Flutter `flutter_localizations`
date tables, plus the app's own `generated/intl/messages_*.dart` localisation tables (the same
noise that forces `opcode_census.py` to skip `generated/intl/`). None of it is protocol code.

### Cross-reference: the checksum 0x8B

The 4.0.8 frame is `A5 04 E2 8B`. That trailing byte is **derived**, not a constant to search for:
`sum(A5,04,E2) = 165+4+226 = 395`; `395 & 0xFF = 0x8B`. Searching for 0x8B as a discriminator is
therefore a red herring — it depends on the whole frame prefix.

---

## 2. AB family (wire byte 0xAB = Smi 342 = `#0x156`)

### Verdict

| build | verdict | label |
|---|---|---|
| 2.22.0901 | **ABSENT** | PROVEN STATIC (`results/static/2.22.0901/command-index.md` §1) |
| 2.23.0609 | **ABSENT** | PROVEN STATIC (this pass) |
| 2.24.0919 | **ABSENT** | PROVEN STATIC (this pass) |
| 4.0.8 | **PRESENT_SEND** | PROVEN STATIC (`AB 07 05 25 <lo> <hi> <cks>`, `writeMotionDpiConfig` @0x946158) |

Motion/gyro **data** exists in 2.23 and 2.24 — but it travels inside the 144/280/484-byte
**config image** (`writeDeviceConfig`, A4/D7), never as an AB frame. The AB *opcode* first appears
in 4.0.8.

### Searches run (2.23 and 2.24)

| # | question | command | 2.23 result | 2.24 result |
|---|---|---|---|---|
| AB-1 | tagged Smi of the byte, whole tree | `rg -n '#0x156\b' <tree>/asm/` | 38 hits | 35 hits |
| AB-1b | …inside `asm/moojiang/` | filter | 8 — **all** `generated/intl/messages_*.dart` | 9 — **all** `generated/intl/messages_*.dart` |
| AB-1c | …`moojiang` hit **outside** intl | `grep -v '/generated/intl/'` | **0** | **0** |
| AB-2 | raw immediate `mov reg, #0xab` | `rg -n 'mov +[xw][0-9]+, #0xab\b' <tree>/asm/` | **0** (whole tree) | 1 — `syncfusion…/color.dart:559` (third party) |
| AB-2b | …in `asm/moojiang/` | filter | **0** | **0** |
| AB-3 | dispatcher compare against the byte | `rg -n 'cmp +[xw][0-9]+, #(0xab\|0x156)\b' <tree>/asm/moojiang/` | **0** | **0** |
| AB-4 | decimal 171 in the object pool | `rg -c '\b171\b' <tree>/pp.txt` | 1 — `Map<int, LogicalKeyboardKey>(171)`, a **keyboard key code**, not protocol | 1 — same |
| AB-5 | decimal 342 (untagged Smi value) in pool | `rg -c '\b342\b' <tree>/pp.txt` | **0** | **0** |
| AB-6 | `AB 05` / `AB 07` / `05 25` / `05 26` builder shapes; `#0x25` immediate | `rg` for `#0x25`, `#0x156` in builder context | **0** | **0** |
| AB-7 | literal byte sequence `AB 07 05 25` in native libs / dex | Python scan | **0** | **0** |
| AB-8 | symbol/API naming: `getMotionList`, `getMotionDpi`, `writeMotionDpiConfig`, `MotionDpi` | `rg -in … <tree>/asm/moojiang/ <tree>/pp.txt <tree>/objs.txt` | **0** | **0** |
| AB-9 | naming: `motion` / `gyro` / `sensor` / `aim` / `mouse` / `transcribe` | `rg -il …` | present, but **config-resident only** (see below) | present, config-resident only |

### What the motion/gyro/sensor naming actually is in 2.23/2.24

The names exist, but every one of them resolves to *config-image* code, not an AB frame builder:

* **2.23** — `units/general_gamepadset.dart` declares `sensorMode`/`sensorDir`/`sensorRightKey0/1`/
  `sensorRightCurve*` (offsets 0x78…0xd8) and `widgets/general/config_motion.dart` (`_DeviceReversalState`,
  `_DeviceAxisState`, `_DeviceSwitchState`). Each write path calls **`::writeDeviceConfig`**
  (`config_motion.dart:1027` @0x7af060, and 7 more sites) — the A4/0xD7 config writer. **No AB builder.**
* **2.24** — the same family plus new `gamepadset280.dart` `SensorCurve` class and per-family
  `config_motion_v280/v484.dart`, `widgets/other/calibration/motion_calibration.dart`. Still
  config-image only; `config_motion*` writes go through the config serialiser.
* The `"Multiplatform Aim Motion Gamepad"`, `"Sensor Sensitivity"`, `"Sensor curve"` strings are
  **l10n / product-name** strings (2.24 `generated/l10n.dart`), not protocol.

So the word "motion" in 2.23/2.24 denotes the *config-resident* gyro block (the same one 2.22
carried inside its 144-byte image), not a wire opcode.

### 4.0.8 anchor (for contrast)

`AB 07 05 25 <lo> <hi> <cks>` is built at **`writeMotionDpiConfig` @0x946158** (`units/gamepadset.dart`):
`AllocateArray(7)`; elements `#0x156`(0xAB), `#0xe`(0x07), `#0xa`(0x05), `#0x4a`(0x25), then the LE
u16 and the checksum (`0x9461c8`…`0x946218`). The byte also appears a **second time as a response
filter**: `cmp w0, #0x156` @`rainbow_more.dart:0x8b482c` (a *tagged* compare, so raw 342 = byte 0xAB).
Readers: `getMotionList` @0xace94c and `getMotionDpi` @0xacea60 (both `mov x16, #0x156`).

---

## 3. What this changes in the version matrix

Rows `E2 readFirmware` and `AB motion DPI` for the 2.23 and 2.24 columns move from `UNKNOWN` to the
verdicts above. Machine-readable form: `results/reconciliation/e2-ab-summary.json`.
