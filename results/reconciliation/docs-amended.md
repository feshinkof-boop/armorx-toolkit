# Documents amended by the E2 / AB-family / FC-F6 reconciliation (2026-09-27)

Every statement below was **appended**; no historical text was deleted or reworded.
Blocks use the OLD CLAIM / NEW EVIDENCE / CORRECTED INTERPRETATION / AFFECTED VERSIONS shape.
Primary artifacts: `e2-ab-2.23-2.24.md`, `fc-f6-timeline.md`, `e2-ab-summary.json`.

## Summary of appended blocks

| # | document (lab path) | topics reconciled |
|---|---|---|
| 1 | `baselines/imported-research/README.md` | keyCapture 0x10000 / bit=id+1; FC/DPI two-paths scope |
| 2 | `baselines/imported-research/unresolved.md` | bit=id+1; D8 chunk 15/43/67; A4 0A D8; E2 per-build; AB byte meaning |
| 3 | `baselines/imported-research/executive-report.md` | keyCapture 0x10000; A4 0A D8; D8 chunk 15/43/67; E2; AB family; F6 guard direction |
| 4 | `baselines/imported-research/command-index.md` | row 0x05↔AB mislabel; D4 getInputModel naming; E2; F6 role mislabel |
| 5 | `baselines/imported-research/fc-dpi.md` | FC/F6 condition; AB frame upgraded to PROVEN |
| 6 | `baselines/imported-research/old-vs-mygt-4.0.8.md` | E2 absent scope; AB opcode-vs-filter (SETTLED); keyCapture 65536; D4 naming; Smi-rule caveat |
| 7 | `baselines/imported-research/live-test-plan.md` | A4 0A D8; D8 chunk; E2 test scope; AB vectors |
| 8 | `baselines/imported-research/d8-macro.md` | A4 0A D8 (commit 0x0A); D8 chunk |
| 9 | `baselines/imported-research/ble-architecture.md` | A5/A4/AB frame-list scope |
| 10 | `baselines/imported-research/docs/mygt-4.0.8-reconciliation.md` | [lab copy] A4 0A D8; keyCapture 0x10000; FC/DPI three writers |
| 11 | `baselines/imported-research/docs/usb-protocol.md` | [lab copy, new] E2 mnemonic GetMode vs readFirmware |
| 12 | `baselines/imported-research/docs/research-status-2026-09-25.md` | [lab copy, new] E2 absence scope; Windows AB marker vs Android AB opcode |

## Freeze-integrity note

`baselines/imported-research/` is a Phase-1 freeze covered by `SHA256SUMS`. The appends above **intentionally invalidate** that manifest for the 9 amended flat files (and for `docs/mygt-4.0.8-reconciliation.md`). The original `SHA256SUMS` is left untouched (history preserved). Post-append hashes:

```
043964e70427c39280fcdbeefb0727e6873fce97d6c267ac33df5db907126719  README.md   [was 027919fc24c44eef…]
28b8079634283bfc51bf25af7b7627d9db7d3064c69a506b1bc0417e8c0bb4f4  unresolved.md   [was 3ea3660cdaef8dc4…]
bc365cbc166490e4219bb8354e9274838258fcf6b193dbddf8ed5cf5df9dd1dd  executive-report.md   [was 69bf9f8141f6f2c5…]
0797502620da0ae1fdcd1daa19787e979aec0079c3cb6997eb97e387b260a172  command-index.md   [was 195f357443198d5c…]
d4296ce418eb348add9186812e996f24bf586db66b66e39692c8f0d16bb6e41c  fc-dpi.md   [was 6757d87b533f62ae…]
6149fc5ad3f91a2a7a3414276a6796d6833d1fc8a92310593cfd2d439972fe81  old-vs-mygt-4.0.8.md   [was ff64101957e70010…]
71ba3dd6f2b4475453a34637cc6f1e75949cf69afba2a2357cd27d5ab2cebb1e  live-test-plan.md   [was 78e992cd3ca86a53…]
2e57af9f578282d470ef167875706f3426a112739a44f2020098b0dea9f9fcce  d8-macro.md   [was 84db4fb1c1a78305…]
44e7044649da1d7b1d056ea1d97f892d578aabd8877e196fae0e7fddd1d10948  ble-architecture.md   [was 7f8659f973cfdc0d…]
d0b1cc00e9f8ec41e83e1768c889a847a3c789a4775d0a67e998e3b797fc193a  docs/mygt-4.0.8-reconciliation.md   [was 4f471b20b8de79a8…]
95d4638f5253e934ea642f7eb684d96d63cfe25b70a389599bf81f39abfd91a5  docs/usb-protocol.md   [was (not in original…]
90f4c8b60d11d3eab372fe9e612735c7f32660f3392458b4ed403935a0d169d7  docs/research-status-2026-09-25.md   [was (not in original…]

New files not in the original manifest: docs/usb-protocol.md, docs/research-status-2026-09-25.md.
```

## Exact appended text (verbatim)

### 1. baselines/imported-research/README.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — keyCapture "0x10000 / bit = id+1"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: "Key id 15 | **Capture** (PROVEN STATIC, two independent chains: `gamePadKeyName` map literal raw 30, and the `@0x10000` bit in the key-mask namespace where bit = id+1)"
* **NEW EVIDENCE (PROVEN STATIC)**: `define.dart` `static int keyCapture()` emits `mov x0, #0x8000`
  (@0x94cb70 in 4.0.8) ⇒ **keyCapture = 0x8000 = bit 15 = id 15**; `keyUp()` emits `mov x0, #0x20000`
  ⇒ 0x10000 = bit 16 = id 16. The convention is **bit == id, NO +1 offset** (re-derived in
  `results/static/2.22.0901/key-id-table.md` §2 and confirmed against 2.22's own `define.dart`).
* **CORRECTED INTERPRETATION**: id 15 = Capture still stands, but **only** on the other chain
  (`key_remap_t.dart` map literal raw-30 → "Capture" @0x92d983). The bit-mask chain is
  `keyCapture = 0x8000` (bit 15); `0x10000` is `keyUp` (id 16).
* **AFFECTED VERSIONS**: 2.22, 2.23, 2.24, 4.0.8 (rule is version-independent).

### R3 — FC / DPI "two paths"  [CONFIRMED, but must be version-scoped]
* **OLD CLAIM (this doc)**: "FC / DPI | two paths: `A5 05 FC n` (normal DPI) and `AB 07 05 25 lo hi` (motion DPI)".
* **NEW EVIDENCE (PROVEN STATIC)**: the **AB path is 4.0.8-only**. In 2.23 and 2.24 the AB byte is absent
  from all protocol code (0 `#0x156` outside `generated/intl/`; 0 `mov #0xab` in `asm/moojiang`;
  0 `AB 07 05 25` byte sequences in the native libs / dex). `FC` first appears in 2.23; `F6` in 2.24.
* **CORRECTED INTERPRETATION**: keep both paths but date them — FC (2.23+), F6 (2.24+, gated on
  device + `zkmVersion >= 0x35`), AB motion DPI (4.0.8 only).
* **AFFECTED VERSIONS**: 2.23/2.24 (no AB), 4.0.8 (both).
````

### 2. baselines/imported-research/unresolved.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — keyCapture "0x10000 / bit = id+1"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: "id 15 | **PROVEN STATIC** (Capture) ... key-mask bit 16 where bit = id+1"
* **NEW EVIDENCE (PROVEN STATIC)**: `define.dart` `static int keyCapture()` emits `mov x0, #0x8000`
  (@0x94cb70 in 4.0.8) ⇒ **keyCapture = 0x8000 = bit 15 = id 15**; `keyUp()` emits `mov x0, #0x20000`
  ⇒ 0x10000 = bit 16 = id 16. The convention is **bit == id, NO +1 offset** (re-derived in
  `results/static/2.22.0901/key-id-table.md` §2 and confirmed against 2.22's own `define.dart`).
* **CORRECTED INTERPRETATION**: id 15 = Capture still stands, but **only** on the other chain
  (`key_remap_t.dart` map literal raw-30 → "Capture" @0x92d983). The bit-mask chain is
  `keyCapture = 0x8000` (bit 15); `0x10000` is `keyUp` (id 16).
* **AFFECTED VERSIONS**: 2.22, 2.23, 2.24, 4.0.8 (rule is version-independent).

### R2 — D8 chunk-size candidates "15/43/67"  [REFINED — resolved per device]
* **OLD CLAIM (this doc)**: "(20 for 20, 43 for 48, 67 for 72 — which one ARMOR-X Pro uses should be confirmed live)".
* **NEW EVIDENCE (PROVEN STATIC)**: `chunk = subpackageLength() - 5`. `subpackageLength()` exists **only from
  2.24** (`define.dart` @0x7b9064; absent in 2.22 and 2.23). Its per-device values are
  devNone 48, devRainbow 20, devRainbowS 20, devRainbow2Pro 20, devRainbow2Lite 48, devC2SL 72,
  devBLITZ_ULT 48, devCHOCO 20, devArmorX 20 ⇒ chunks 15/43/67 are **per-device**, not candidates for one unit.
* **CORRECTED INTERPRETATION**: ARMOR-X Pro uses subpackageLength 20 ⇒ **chunk = 15** (hard-coded 15 in
  2.22 and 2.23; derived 15 in 2.24/4.0.8). 43 belongs to subpackageLength 48 devices, 67 to 72.
* **AFFECTED VERSIONS**: chunk 15 (all builds); 43/67 only from 2.24 (and only for 48/72 devices).

### R2 — commit/terminator frame "A4 0A D8 <nfrags+1> <sum8>"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: the D8 commit frame has second byte `0x0A`.
* **NEW EVIDENCE (PROVEN STATIC)**: the commit frame is `A4 05 D8 <nfrags+1> <csum>`; `0x05` is the
  ordinary `segLen+5` arithmetic for an empty (5-byte) commit frame. There is **no literal 0x0A byte**:
  a full sweep for `#0x14` (Smi 20 → byte 0x0A) in the terminator range returns nothing
  (`results/static/2.22.0901/d8-macro.md` §3d; `results/version-diff/d8-history.md`: "no 0x0A — PROVEN").
* **CORRECTED INTERPRETATION**: write the terminator as `A4 05 D8 <nfrags+1> <csum>`. The "0x0A" was a
  misread of the length byte / a doubling slip.
* **AFFECTED VERSIONS**: 2.22 (PROVEN STATIC); 2.23/2.24/4.0.8 same envelope.

### R4 — E2 `readFirmware` per build  [SETTLED]
* **OLD CLAIM (this doc)**: "E2 (`readFirmware`, `A5 04 E2 8B`) is now used in 4.0.8".
* **NEW EVIDENCE (PROVEN STATIC)**: E2 is **ABSENT** from every form of 2.23 and 2.24 protocol code
  (see `e2-ab-2.23-2.24.md` §1 — 0 hits for Smi `#0x1c4`, raw `#0xe2`, pool 226/452, dispatcher compares,
  byte sequences and API symbols, outside `generated/intl/`). It is **PRESENT_SEND** in 4.0.8
  (`BluetoothModel::readFirmware` @0x8b6860).
* **CORRECTED INTERPRETATION**: the 4.0.8-only E2 statement is confirmed; the previously-open 2.23/2.24
  columns are now closed as ABSENT.
* **AFFECTED VERSIONS**: 2.23, 2.24 ABSENT; 4.0.8 PRESENT.

### R5 — "The AB byte inside the rainbow_more light closure is UNKNOWN"  [SETTLED]
* **OLD CLAIM (this doc)**: AB inside `rainbow_more` is of unknown meaning.
* **NEW EVIDENCE (PROVEN STATIC)**: in 4.0.8 the AB byte is the **motion/gyro DPI** opcode —
  `writeMotionDpiConfig` @0x946158 builds `AB 07 05 25 <u16 LE> <cks>`; it also appears as a response
  filter `cmp w0, #0x156` @`rainbow_more.dart:0x8b482c`. In **2.23 and 2.24 the AB byte is absent from
  all protocol code** (0 `#0x156` outside `generated/intl/`).
* **CORRECTED INTERPRETATION**: AB = motion-DPI request opcode (4.0.8) + response-family filter; not
  present before 4.0.8.
* **AFFECTED VERSIONS**: 2.22/2.23/2.24 ABSENT; 4.0.8 PRESENT_SEND.
````

### 3. baselines/imported-research/executive-report.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — keyCapture "0x10000 / bit = id+1"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: "`Define::keyCapture = 0x10000` = bit 16 in the key-mask namespace where [bit = id+1]"
* **NEW EVIDENCE (PROVEN STATIC)**: `define.dart` `static int keyCapture()` emits `mov x0, #0x8000`
  (@0x94cb70 in 4.0.8) ⇒ **keyCapture = 0x8000 = bit 15 = id 15**; `keyUp()` emits `mov x0, #0x20000`
  ⇒ 0x10000 = bit 16 = id 16. The convention is **bit == id, NO +1 offset** (re-derived in
  `results/static/2.22.0901/key-id-table.md` §2 and confirmed against 2.22's own `define.dart`).
* **CORRECTED INTERPRETATION**: id 15 = Capture still stands, but **only** on the other chain
  (`key_remap_t.dart` map literal raw-30 → "Capture" @0x92d983). The bit-mask chain is
  `keyCapture = 0x8000` (bit 15); `0x10000` is `keyUp` (id 16).
* **AFFECTED VERSIONS**: 2.22, 2.23, 2.24, 4.0.8 (rule is version-independent).

### R2 — commit/terminator frame "A4 0A D8 <nfrags+1> <sum8>"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: the D8 commit frame has second byte `0x0A`.
* **NEW EVIDENCE (PROVEN STATIC)**: the commit frame is `A4 05 D8 <nfrags+1> <csum>`; `0x05` is the
  ordinary `segLen+5` arithmetic for an empty (5-byte) commit frame. There is **no literal 0x0A byte**:
  a full sweep for `#0x14` (Smi 20 → byte 0x0A) in the terminator range returns nothing
  (`results/static/2.22.0901/d8-macro.md` §3d; `results/version-diff/d8-history.md`: "no 0x0A — PROVEN").
* **CORRECTED INTERPRETATION**: write the terminator as `A4 05 D8 <nfrags+1> <csum>`. The "0x0A" was a
  misread of the length byte / a doubling slip.
* **AFFECTED VERSIONS**: 2.22 (PROVEN STATIC); 2.23/2.24/4.0.8 same envelope.

### R3 — D8 chunk-size "15/43/67 candidates"  [REFINED — resolved per device]
* **OLD CLAIM (this doc)**: "Open: the chunk size for this device id (15/43/67 candidates ...)"; table row
  "D8 chunk size / readback offsets | unknown | candidates 15/43/67".
* **NEW EVIDENCE (PROVEN STATIC)**: `chunk = subpackageLength() - 5`; per-device values give 15/43/67 as
  *different devices'* chunks, not candidates for ARMOR-X Pro.
* **CORRECTED INTERPRETATION**: ARMOR-X Pro ⇒ 15. 43 ⇒ subpackageLength 48 devices, 67 ⇒ 72 devices.
* **AFFECTED VERSIONS**: 2.22/2.23 hard-coded 15; 2.24/4.0.8 derived from `subpackageLength()`.

### R4 — E2 presence  [SETTLED]
* **OLD CLAIM (this doc)**: `E2 (A5 04 E2 8B, ...)` listed in the 4.0.8 set; note that `"E2 is absent" — false from 4.0.8`.
* **NEW EVIDENCE (PROVEN STATIC)**: E2 ABSENT in 2.22, 2.23 and 2.24; PRESENT_SEND in 4.0.8 only
  (`readFirmware` @0x8b6860). The four-way matrix's `UNKNOWN` for 2.23/2.24 is now closed.
* **CORRECTED INTERPRETATION**: E2 is a 4.0.8-era opcode; earlier builds (incl. 2.23/2.24) do not carry it.
* **AFFECTED VERSIONS**: 2.22/2.23/2.24 ABSENT; 4.0.8 PRESENT.

### R5 — AB-family frames  [SETTLED, scoped]
* **OLD CLAIM (this doc)**: 4.0.8 opcode set includes "the `AB`-family frames (`AB 05 05 25/26`, `AB 07 05 25 …`)"
  and "motion/gyro DPI `AB 07 05 25 <lo> <hi> <cks>`".
* **NEW EVIDENCE (PROVEN STATIC)**: the confirmed builder emits `AB 07 05 25 <u16 LE> <cks>`
  (`writeMotionDpiConfig` @0x946158: elements `#0x156, #0xe, #0xa, #0x4a, …`). The AB byte is absent from
  2.23 and 2.24 protocol code.
* **CORRECTED INTERPRETATION**: keep the `AB 07 05 25` shape; treat `AB 05 …` as not confirmed by a builder
  in this pass; AB is **4.0.8-only**.
* **AFFECTED VERSIONS**: 2.22/2.23/2.24 ABSENT; 4.0.8 PRESENT_SEND.

### R6 — "legacy `F6` guard"  [DIRECTION CORRECTED]
* **OLD CLAIM (this doc)**: "`A5 05 FC <sel>` (4-bit) + ... legacy `F6` guard".
* **NEW EVIDENCE (PROVEN STATIC)**: `writeDpiConfig` @0x894000 (2.24) / @0x946750 (4.0.8): default opcode is
  `0xFC`; the opcode slot is overwritten with `0xF6` **iff** `curDevice ∈ gate` **and** `zkmVersion >= 0x35`
  (`cmp x1, #0x35 ; b.lt <skip>` on an explicitly untagged value — so the immediate is the plain `0x35`,
  not the tagged `0x6a`). Gate = {devRainbow2Pro, devC2SL} in 2.24; {devRainbow2Pro, devRainbow3, devGale2, devC2SL} in 4.0.8.
* **CORRECTED INTERPRETATION**: F6 is the **older-firmware-compatible** path selected when the firmware is
  **newer** (>= 0x35). FC is the fallback. Any "fw < 0x35 → F6" phrasing is wrong.
* **AFFECTED VERSIONS**: 2.24, 4.0.8 (F6 present); 2.22/2.23 (no F6).
````

### 4. baselines/imported-research/command-index.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — row `0x05 | UNKNOWN | … writeMotionDpiConfig … AB 7 5 37`  [CONTRADICTED]
* **OLD CLAIM (this doc)**: the opcode is `0x05`, role `UNKNOWN`, frame `AB 7 5 37`.
* **NEW EVIDENCE (PROVEN STATIC)**: `writeMotionDpiConfig` @0x946158 (`units/gamepadset.dart`) builds a
  **7-byte** array whose element 0 is `mov x16, #0x156` = Smi(342) ⇒ wire byte **0xAB** — the header, not 0x05.
  Elements are `0xAB, 0x07, 0x05, 0x25`, then a u16 LE, then the checksum ⇒ `AB 07 05 25 <lo> <hi> <cks>`.
* **CORRECTED INTERPRETATION**: opcode/header **0xAB**; role **motion/gyro DPI write**; payload = u16 LE.
* **AFFECTED VERSIONS**: 4.0.8 only (AB absent in 2.22/2.23/2.24).

### R2 — row `0xD4 | getInputModel`  [REFINED — name is version-dependent]
* **OLD CLAIM (this doc)**: D4 builder = `getInputModel` @0xa84258.
* **NEW EVIDENCE (PROVEN STATIC)**: the D4 request is named differently per build —
  2.22 `_ArmorXProConfigWidgetState::getOnBoardConfig` (closure @0x89adac);
  2.23 `getInputModel`; 2.24 `getOnBoardConfig` (5 sites); 4.0.8 `getInputModel` (5 sites).
  Opcode and frame (`A5 04 D4 7D`) are unchanged throughout.
* **CORRECTED INTERPRETATION**: the name alternates; the *opcode* D4 and role (on-board config / input model read) do not.
* **AFFECTED VERSIONS**: 2.22 & 2.24 = getOnBoardConfig; 2.23 & 4.0.8 = getInputModel.

### R3 — row `0xE2 | readFirmware`  [CONFIRMED for 4.0.8; ABSENT earlier]
* **OLD CLAIM (this doc)**: 4.0.8 `readFirmware` @0x8b6860, `A5 04 E2 8B`.
* **NEW EVIDENCE (PROVEN STATIC)**: confirmed for 4.0.8. E2 is **ABSENT** from 2.22/2.23/2.24 protocol code
  (see `e2-ab-2.23-2.24.md` §1). Note the checksum 0x8B is derived, not a constant.
* **AFFECTED VERSIONS**: 4.0.8 PRESENT; 2.22/2.23/2.24 ABSENT.

### R4 — row `0xF6 | keyboard/doujiang light - charging mode / step length`  [CONTRADICTED]
* **OLD CLAIM (this doc)**: F6 is a keyboard/doujiang light opcode; builder `writeDpiConfig` @0x946750.
* **NEW EVIDENCE (PROVEN STATIC)**: the builder cited (`writeDpiConfig`) is a **DPI** writer; F6 is the
  **legacy DPI opcode** substituted into the FC frame when `curDevice ∈ {devRainbow2Pro, devRainbow3, devGale2, devC2SL}`
  and `zkmVersion >= 0x35` (`mov x16, #0x1ec` = Smi(492) ⇒ byte 0xF6 @0x946850). The role text and the builder
  column contradict each other; the builder wins.
* **CORRECTED INTERPRETATION**: 0xF6 = legacy DPI write (`A5 05 F6 <sel> <cks>`), not a lighting opcode.
* **AFFECTED VERSIONS**: 4.0.8 (and 2.24); absent in 2.22/2.23.
````

### 5. baselines/imported-research/fc-dpi.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — normal DPI "0xFC (legacy 0xF6)"  [CONFIRMED, condition now exact]
* **OLD CLAIM (this doc)**: normal DPI = `0xFC` with legacy `0xF6`; builder `::writeDpiConfig` @0x946750.
* **NEW EVIDENCE (PROVEN STATIC)**: the opcode slot is written `0xFC` first; `0xF6` replaces it only when
  `curDevice ∈ gate` **and** `zkmVersion >= 0x35` (`cmp x1, #0x35 ; b.lt <skip>`; the operand is untagged
  so the immediate is the plain `0x35`, not `0x6a`). 2.24 gate = {devRainbow2Pro, devC2SL},
  static `0x102c`; 4.0.8 gate = {devRainbow2Pro, devRainbow3, devGale2, devC2SL}, static `0xb6c`.
  2.23 `writeDpiConfig` @0x7fdee4 writes `0xFC` **unconditionally** (no `#0x1ec` anywhere in `asm/moojiang`).
* **CORRECTED INTERPRETATION**: FC = default/legacy-compatible normal DPI in 2.23+; F6 = the branch taken for
  listed devices on firmware ≥ 0x35 (2.24+).
* **AFFECTED VERSIONS**: FC 2.23/2.24/4.0.8; F6 2.24/4.0.8; neither in 2.22.

### R2 — `AB 07 05 25 <lo> <hi> <cks>` "STRONG EVIDENCE, not proven"  [UPGRADED]
* **OLD CLAIM (this doc)**: request shape lists `A5 05 FC …` / `A5 05 F6 …` / `AB 07 05 25 …`;
  §"STRONG EVIDENCE, not proven".
* **NEW EVIDENCE (PROVEN STATIC)**: `writeMotionDpiConfig` @0x946158 builds exactly `AB 07 05 25 <u16 LE> <cks>`
  (7-byte array: `#0x156`,`#0xe`,`#0xa`,`#0x4a`, lo, hi, cks; checksum via `::getCheckSum` @0x819078).
* **CORRECTED INTERPRETATION**: promote to PROVEN STATIC for 4.0.8. FC/F6 shapes are also byte-exact.
* **AFFECTED VERSIONS**: AB = 4.0.8 only; FC/F6 = 2.23+ / 2.24+.
````

### 6. baselines/imported-research/old-vs-mygt-4.0.8.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — E2 "absent from the Android builds"  [REFINED — version-scoped]
* **OLD CLAIM (this doc)**: E2 is reachable in 4.0.8 (`readFirmware` @0x8b6860, `A5 04 E2 8B`); the
  "E2 absent" note is "true for 2.23/2.24".
* **NEW EVIDENCE (PROVEN STATIC)**: the "true for 2.23/2.24" parenthetical is **confirmed** by an exhaustive
  negative search (see `e2-ab-2.23-2.24.md` §1): 0 hits for `#0x1c4`, raw `#0xe2`, pool 226/452, dispatcher
  compares, byte sequences and API symbols outside `generated/intl/`. The four-way matrix's earlier `UNKNOWN`
  for 2.23/2.24 is superseded by ABSENT.
* **AFFECTED VERSIONS**: 2.22/2.23/2.24 ABSENT; 4.0.8 PRESENT.

### R2 — "UNKNOWN whether AB is an opcode byte or a payload filter byte"  [SETTLED]
* **OLD CLAIM (this doc)**: AB in the `rainbow_more` closure (0x8b3b40) is of unknown kind; "no builder emits
  AB as a request".
* **NEW EVIDENCE (PROVEN STATIC)**: 4.0.8 **does** emit AB as a request — `writeMotionDpiConfig` @0x946158,
  frame `AB 07 05 25 <u16 LE> <cks>` (element 0 = `#0x156`). It is **also** used as a response filter
  (`cmp w0, #0x156` @`rainbow_more.dart:0x8b482c`). So it is an opcode/header byte both ways.
* **CORRECTED INTERPRETATION**: AB is a first-class request opcode (motion/gyro DPI), not merely a filter marker.
* **AFFECTED VERSIONS**: 4.0.8; absent in 2.22/2.23/2.24.

### R3 — "keyCapture | 65536"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: the key-mask table row `keyCapture | – | 65536 | 65536`.
* **NEW EVIDENCE (PROVEN STATIC)**: `define.dart` `static int keyCapture()` emits `mov x0, #0x8000`
  ⇒ keyCapture = **0x8000 = 32768 = bit 15 = id 15**; `0x10000` (65536) is `keyUp` (id 16). `bit == id`, no +1.
* **CORRECTED INTERPRETATION**: fix the row — keyCapture = 0x8000.
* **AFFECTED VERSIONS**: all four builds.

### R4 — D4 builder name `getInputModel`  [REFINED]
* **OLD CLAIM (this doc)**: 4.0.8 D4 = `getInputModel` @0xa84258.
* **NEW EVIDENCE (PROVEN STATIC)**: name alternates — 2.22 `getOnBoardConfig`, 2.23 `getInputModel`,
  2.24 `getOnBoardConfig`, 4.0.8 `getInputModel`; opcode/frame (`A5 04 D4 7D`) unchanged.
* **AFFECTED VERSIONS**: as listed.

### R5 — Smi-rule caveat  [AMENDMENT]
* **OLD CLAIM (this doc, reading rule)**: "Smi immediates are doubled, so wire byte B is found as #0x(2B)".
* **NEW EVIDENCE**: the rule holds for **values stored into frame arrays** (`#0x14a`=0xA5, `#0x1f8`=0xFC,
  `#0x1ec`=0xF6, `#0x156`=0xAB), but **not** for compares against an explicitly untagged operand:
  `writeDpiConfig` loads `LoadInt32Instr` (`sbfx x1,x0,#1,#0x1f`) then `cmp x1, #0x35` — the literal is the
  plain 53, not `#0x6a`.
* **CORRECTED INTERPRETATION**: apply the doubling only to tagged stores; check for `sbfx …#1` / `LoadInt32Instr`
  before halving a `cmp`.
* **AFFECTED VERSIONS**: all.
````

### 7. baselines/imported-research/live-test-plan.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — commit/terminator frame "A4 0A D8 <nfrags+1> <sum8>"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: the D8 commit frame has second byte `0x0A`.
* **NEW EVIDENCE (PROVEN STATIC)**: the commit frame is `A4 05 D8 <nfrags+1> <csum>`; `0x05` is the
  ordinary `segLen+5` arithmetic for an empty (5-byte) commit frame. There is **no literal 0x0A byte**:
  a full sweep for `#0x14` (Smi 20 → byte 0x0A) in the terminator range returns nothing
  (`results/static/2.22.0901/d8-macro.md` §3d; `results/version-diff/d8-history.md`: "no 0x0A — PROVEN").
* **CORRECTED INTERPRETATION**: write the terminator as `A4 05 D8 <nfrags+1> <csum>`. The "0x0A" was a
  misread of the length byte / a doubling slip.
* **AFFECTED VERSIONS**: 2.22 (PROVEN STATIC); 2.23/2.24/4.0.8 same envelope.

### R2 — D8 chunk fallback "try 43 for subpkg 48, 67 for 72"  [CONFIRMED, scoped]
* **OLD CLAIM (this doc)**: if a write is dropped, "chunk size differs (try 43 for subpkg 48, 67 for 72)".
* **NEW EVIDENCE (PROVEN STATIC)**: `chunk = subpackageLength() - 5`, and `subpackageLength()` exists only from
  2.24. ARMOR-X Pro (subpackageLength 20) ⇒ chunk 15; 43/67 belong to the 48/72 devices.
* **CORRECTED INTERPRETATION**: keep as a device-dependent table; for ARMOR-X Pro the chunk is 15 (not a candidate).
* **AFFECTED VERSIONS**: 2.22/2.23 hard-coded 15; 2.24+ derived.

### R3 — "T7 — E2 read" hypothesis  [STILL VALID, version-scoped]
* **OLD CLAIM (this doc)**: "`A5 04 E2 8B` (`readFirmware`, new in 4.0.8)"; test T7 sends it once.
* **NEW EVIDENCE (PROVEN STATIC)**: E2 exists **only** in 4.0.8; ABSENT in 2.22/2.23/2.24. The experiment is
  meaningful only against 4.0.8 (or 4.0.8-era firmware).
* **CORRECTED INTERPRETATION**: gate T7 on a 4.0.8 install; on 2.22/2.23/2.24 there is nothing to send.
* **AFFECTED VERSIONS**: 4.0.8 only.

### R4 — AB motion-DPI vectors  [CONFIRMED for 4.0.8]
* **OLD CLAIM (this doc)**: "`AB 07 05 25 20 03 <cks>` sets the motion DPI".
* **NEW EVIDENCE (PROVEN STATIC)**: `writeMotionDpiConfig` @0x946158 emits exactly `AB 07 05 25 <u16 LE> <cks>`.
  AB is absent from 2.23/2.24.
* **AFFECTED VERSIONS**: 4.0.8 only.
````

### 8. baselines/imported-research/d8-macro.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — commit/terminator frame "A4 0A D8 <nfrags+1> <sum8>"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: the D8 commit frame has second byte `0x0A`.
* **NEW EVIDENCE (PROVEN STATIC)**: the commit frame is `A4 05 D8 <nfrags+1> <csum>`; `0x05` is the
  ordinary `segLen+5` arithmetic for an empty (5-byte) commit frame. There is **no literal 0x0A byte**:
  a full sweep for `#0x14` (Smi 20 → byte 0x0A) in the terminator range returns nothing
  (`results/static/2.22.0901/d8-macro.md` §3d; `results/version-diff/d8-history.md`: "no 0x0A — PROVEN").
* **CORRECTED INTERPRETATION**: write the terminator as `A4 05 D8 <nfrags+1> <csum>`. The "0x0A" was a
  misread of the length byte / a doubling slip.
* **AFFECTED VERSIONS**: 2.22 (PROVEN STATIC); 2.23/2.24/4.0.8 same envelope.

### R2 — "int chunk = subpackageLength() - 5; // 15 / 43 / 67"  [REFINED]
* **OLD CLAIM (this doc)**: chunk candidates 15/43/67 (shown as one line comment).
* **NEW EVIDENCE (PROVEN STATIC)**: `subpackageLength()` is per-device (devArmorX 20 ⇒ 15; 48-devices ⇒ 43;
  72-devices ⇒ 67). It exists only from 2.24; 2.22/2.23 hard-code 15.
* **CORRECTED INTERPRETATION**: ARMOR-X Pro chunk = 15; 43/67 are other devices'.
* **AFFECTED VERSIONS**: 15 (all); 43/67 (2.24+ only).
````

### 9. baselines/imported-research/ble-architecture.md

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — "builder (A5/A4/AB frame list)"  [SCOPED]
* **OLD CLAIM (this doc)**: the BLE pipeline is "builder (A5/A4/AB frame list) -> getCheckSum() -> write() -> FFE1".
* **NEW EVIDENCE (PROVEN STATIC)**: frame-list builders emit **A5** and **A4** in every build, but **AB** only
  from 4.0.8 (`writeMotionDpiConfig` @0x946158). In 2.22/2.23/2.24 there is no AB builder.
* **CORRECTED INTERPRETATION**: read the third term as "(A5/A4, plus AB from 4.0.8)".
* **AFFECTED VERSIONS**: 2.22/2.23/2.24 = A5/A4 only; 4.0.8 = A5/A4/AB.
````

### 10. baselines/imported-research/docs/mygt-4.0.8-reconciliation.md  [lab copy of /home/salamanka/armorx-re/repo/docs/mygt-4.0.8-reconciliation.md]

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — commit/terminator frame "A4 0A D8 <nfrags+1> <sum8>"  [CONTRADICTED]
* **OLD CLAIM (this doc)** `A4 | len | D8 | payload | sum8`, terminator `A4 0A D8 …`: the D8 commit frame has second byte `0x0A`.
* **NEW EVIDENCE (PROVEN STATIC)**: the commit frame is `A4 05 D8 <nfrags+1> <csum>`; `0x05` is the
  ordinary `segLen+5` arithmetic for an empty (5-byte) commit frame. There is **no literal 0x0A byte**:
  a full sweep for `#0x14` (Smi 20 → byte 0x0A) in the terminator range returns nothing
  (`results/static/2.22.0901/d8-macro.md` §3d; `results/version-diff/d8-history.md`: "no 0x0A — PROVEN").
* **CORRECTED INTERPRETATION**: write the terminator as `A4 05 D8 <nfrags+1> <csum>`. The "0x0A" was a
  misread of the length byte / a doubling slip.
* **AFFECTED VERSIONS**: 2.22 (PROVEN STATIC); 2.23/2.24/4.0.8 same envelope.

### R2 — keyCapture "0x10000 / bit = id+1"  [CONTRADICTED]
* **OLD CLAIM (this doc)**: "the key-mask constant `keyCapture = 0x10000` (bit 16, where bit index = config id + 1)"
* **NEW EVIDENCE (PROVEN STATIC)**: `define.dart` `static int keyCapture()` emits `mov x0, #0x8000`
  (@0x94cb70 in 4.0.8) ⇒ **keyCapture = 0x8000 = bit 15 = id 15**; `keyUp()` emits `mov x0, #0x20000`
  ⇒ 0x10000 = bit 16 = id 16. The convention is **bit == id, NO +1 offset** (re-derived in
  `results/static/2.22.0901/key-id-table.md` §2 and confirmed against 2.22's own `define.dart`).
* **CORRECTED INTERPRETATION**: id 15 = Capture still stands, but **only** on the other chain
  (`key_remap_t.dart` map literal raw-30 → "Capture" @0x92d983). The bit-mask chain is
  `keyCapture = 0x8000` (bit 15); `0x10000` is `keyUp` (id 16).
* **AFFECTED VERSIONS**: 2.22, 2.23, 2.24, 4.0.8 (rule is version-independent).

### R3 — FC/DPI "split in two"  [CONFIRMED, scoped]
* **OLD CLAIM (this doc)**: 4.0.8 has `A5 05 FC <sel&0x0F> <cks>` and `AB 07 05 25 <lo> <hi> <cks>`.
* **NEW EVIDENCE (PROVEN STATIC)**: both confirmed byte-exact (`writeDpiConfig` @0x946750;
  `writeMotionDpiConfig` @0x946158, element 0 = `#0x156` ⇒ 0xAB). Additionally, 4.0.8 gates a legacy
  **F6** substitution on `{devRainbow2Pro, devRainbow3, devGale2, devC2SL}` when `zkmVersion >= 0x35`.
  The AB path is absent from 2.23/2.24.
* **CORRECTED INTERPRETATION**: three DPI writers exist in 4.0.8 — FC (default), F6 (legacy, gated), AB (motion).
* **AFFECTED VERSIONS**: 4.0.8 (all three); 2.24 (FC+F6); 2.23 (FC); 2.22 (none).
````

### 11. baselines/imported-research/docs/usb-protocol.md  [NEW lab copy of /home/salamanka/armorx-re/repo/docs/usb-protocol.md]

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — E2 mnemonic "GetMode" vs Android "readFirmware"  [RECONCILED — same opcode, two names]
* **OLD CLAIM (this doc)**: `GetMode | A5 04 E2 8B` (Windows device-library path).
* **NEW EVIDENCE (PROVEN STATIC, Android side)**: 4.0.8's E2 builder is `BluetoothModel::readFirmware`
  @0x8b6860, same frame `A5 04 E2 8B`, same checksum (derived: `(A5+04+E2)&FF = 0x8B`). E2 is ABSENT from
  2.22/2.23/2.24.
* **CORRECTED INTERPRETATION**: `E2` is one opcode with two mnemonics across transports — "GetMode"
  (F20 USB HID library) and "readFirmware" (Android 4.0.8 BLE). Do not treat them as different opcodes;
  do not assume the Android naming applies to the USB parser (or vice-versa).
* **AFFECTED VERSIONS**: Android 4.0.8 only (absent 2.22/2.23/2.24); transport-independent frame.
````

### 12. baselines/imported-research/docs/research-status-2026-09-25.md  [NEW lab copy of /home/salamanka/armorx-re/repo/docs/research-status-2026-09-25.md]

````markdown
--

## Reconciliation block — 2026-09-27 (E2 / AB-family / FC-F6 audit, C1–C3+E)

Appended by the E2/AB/DPI reconciliation pass. **Nothing above was deleted or reworded.**
Primary artifacts: `results/reconciliation/e2-ab-2.23-2.24.md`,
`results/reconciliation/fc-f6-timeline.md`, `results/reconciliation/e2-ab-summary.json`.
Trees re-read with **absolute** paths: 2.23 = `/home/salamanka/armorx/re/blutter_out`,
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`, 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.
(An early scan used the wrong relative path `v224/…` and read as a clean zero — a path miss that
looks like `ABSENT`. Every negative below cites the absolute tree it was run on.)

### R1 — "Rigorous E2 absence: no reachable E2 frame-construction or response-decoding path in either analyzed build"  [SCOPED]
* **OLD CLAIM (this doc)**: E2 is absent from "either analyzed build".
* **NEW EVIDENCE (PROVEN STATIC)**: E2 is ABSENT in 2.22, 2.23 and 2.24 (exhaustive negative search),
  but **PRESENT_SEND in 4.0.8** (`readFirmware` @0x8b6860). The statement is correct only when scoped to the
  2.23/2.24 pair that the note was written against.
* **CORRECTED INTERPRETATION**: name the builds — "E2 absent in 2.23 and 2.24; present in 4.0.8".
* **AFFECTED VERSIONS**: as stated.

### R2 — "Windows AB long-packet path … reassembly by AB markers"  [DISAMBIGUATED]
* **OLD CLAIM (this doc)**: the Windows AB long-packet path reassembles by "AB markers".
* **NEW EVIDENCE (PROVEN STATIC, Android side)**: the Android BLE opcode **0xAB** is a distinct, 4.0.8-only
  frame header (`writeMotionDpiConfig`, `AB 07 05 25 <u16 LE> <cks>`), absent from all earlier Android builds.
* **CORRECTED INTERPRETATION**: keep the two uses separate — Android BLE 0xAB = motion-DPI opcode;
  Windows USB "AB marker" = a transport framing marker. Same two hex digits, unrelated roles.
* **AFFECTED VERSIONS**: Android 4.0.8 (BLE opcode); Windows (USB marker).
````
