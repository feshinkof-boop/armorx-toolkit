# D8 macro protocol — version history 2.22.0901 / 2.23 / 2.24 / 4.0.8

All cells are labelled. `UNKNOWN` = not re-derived in this pass (the version was only
grep-probed, not disassembly-read). Nothing here promotes a later build's reading into an
earlier one.

Trees used:
* 2.22.0901 → `armorx-lab/static/blutter/2.22.0901/blutter_out/` (full read, this pass; see
  `results/static/2.22.0901/d8-macro.md`)
* 2.23 → `~/armorx/re/blutter_out/` (grep-probed this pass)
* 2.24 → `~/armorx/re/v224/blutter_out/` (grep-probed + `subpackageLength` body read)
* 4.0.8 → `armorx-re/mygt408/blutter_out/` (grep-probed + `subpackageLength` body read; prior
  reconstruction in `baselines/imported-research/d8-macro.md`)

---

## Headline: the macro wire format was **replaced between 2.23 and 2.24**

```
$ grep -rln 'TranscribeFrame|transcribeFrame|frame_config_macros' <tree>/asm/moojiang/
2.22 : (no output)
2.23 : (no output)
2.24 : asm/moojiang/units/transcribe_frame.dart
       asm/moojiang/widgets/general/frame_config_macros.dart
4.0.8: asm/moojiang/units/transcribe_frame.dart
       asm/moojiang/widgets/general/frame_config_macros.dart
       asm/moojiang/widgets/shared_widgets/macro_edit_item.dart

$ grep -rn 'subpackageLength' <tree>/asm/moojiang/ | head -3
2.22 : (no output)
2.23 : (no output)
2.24 : define.dart:477  int subpackageLength()  { 0x7b9064 }
       base_gamepadset.dart:299 0x7b84cc -> 0x7b9064
4.0.8: define.dart:316  int subpackageLength()  { 0x819190 }
       base_gamepadset.dart:642 0x81d710 -> 0x819190

$ grep -n 'fmov  *d[0-9]*, #15.0' <tree>/asm/moojiang/units/gamepadset.dart
2.22 : 2406/0x79e300 (writeMacroConfig), 4879/0x79e970, 6209/0x7f8704     [this pass: 2464 etc. in 2.22]
2.23 : 2406/0x7980fc, 4879/0x79e970, 6209/0x7f8704
2.24 : (no output)
4.0.8: (no output)
```

**So 2.22.0901 and 2.23 share one implementation (hard-coded 15, GamepadDef-style payload);
2.24 and 4.0.8 share a different one (per-device `subpackageLength()`, `TranscribeFrame`).**
The 4.0.8 reconstruction in `baselines/` describes the *new* format and must not be applied to
2.22/2.23.

---

## `subpackageLength()` is a **per-device chunk table** — and it explains the 15/43/67 candidates

`subpackageLength()` switch on `curDevice.field_7` (device id) returns one of three constants:

| tree | fn addr | return sites | values |
|---|---|---|---|
| 2.24 | 0x7b9064 | 0x7b9124, 0x7b90ec, 0x7b9134 | `mov x0,#0x14`=20, `#0x48`=72, `#0x30`=48 |
| 4.0.8 | 0x819190 | 0x819238, 0x819264, 0x819274 | `mov x0,#0x14`=20, `#0x48`=72, `#0x30`=48 |

PROVEN STATIC (bodies read directly).
2.22 and 2.23 have **no** such function (grep empty) — PROVEN STATIC negative.

**Arithmetic:** `20-5 = 15`, `48-5 = 43`, `72-5 = 67` — exactly the three candidate chunk sizes in
the open-question list. 2.22's hard-coded chunk of **15** therefore corresponds to the
`subpackageLength()==20` device class, and the frame-length arithmetic is confirmed independently
in 2.22 (§below): the `len` byte equals `segLen + 5` and the 5-byte terminator frame
`A4 05 D8 <nfrags+1> <csum>` has `segLen = 0`. So **`chunk = subpackageLength() - 5`** where the
5 is the A4 frame overhead (A4, len, cmd, ordinal, checksum).
Label: STRONG EVIDENCE in 2.22 (both operands proven independently) / INFERRED for the
per-device mapping into 2.24+ (the device-id→value branches were read but not exhaustively).

This also **settles the lab's "+5 vs +4" documentation discrepancy for 2.22**: the `len` byte is
`segLen + 5` and the frame really is `5 + segLen` bytes long *provided the fragment ordinal byte
at frame offset 3 exists*. The terminator frame proves that byte exists (PROVEN: 5 bytes total
with a 1-byte ordinal carrier). `/home/salamanka/armorx-lab/automation/scripts/armorx_lab/frames.py
build_frag()`'s `payload + 5` form is the correct one for 2.22; the `payload + 4` form is the
one without an ordinal byte.

---

## Side-by-side

| property | 2.22.0901 | 2.23 | 2.24 | 4.0.8 |
|---|---|---|---|---|
| A4 fragmentation present | YES (`#0x148` @0x79e358/0x79e428) — PROVEN | UNKNOWN (not re-derived) | UNKNOWN (not re-derived) | YES (imported d8-macro.md) |
| D8 command byte | `0xD8` (`#0x1b0` @0x79e778, 0x79ebf4) — PROVEN | UNKNOWN | UNKNOWN | YES |
| chunk source | hard-coded literal **15** — PROVEN | hard-coded literal **15** (0x7980fc, 0x79e970, 0x7f8704) — PROVEN (grep) | `subpackageLength()` → {20,48,72} — PROVEN | `subpackageLength()` → {20,72,48} — PROVEN |
| MTU-derived logic | ABSENT — PROVEN (negative) | ABSENT (no subpackageLength) — PROVEN (grep) | present via subpackageLength | present via subpackageLength |
| device chunk table | ABSENT — PROVEN (negative) | ABSENT — PROVEN (grep) | YES (`curDevice.field_7` switch) | YES (`curDevice.field_7` switch) |
| `len` byte | `segLen + 5` — PROVEN (0x79e658/0x79e65c) | UNKNOWN | UNKNOWN | UNKNOWN (imported doc says payload+5) |
| fragment ordinal byte at frame[3] | YES, proven by the 5-byte terminator — PROVEN | UNKNOWN | UNKNOWN | UNKNOWN |
| terminator / commit | `A4 05 D8 <nfrags+1> <csum>`; **no 0x0A** — PROVEN | UNKNOWN | UNKNOWN | "commit byte 0x0A" (imported note) |
| D8 payload header | 10 B: `crc16 BE, len BE, att.type, runKey, runKey\|5, isRepeat, repeatTime BE` — PROVEN | UNKNOWN | UNKNOWN | same 10-byte shape per imported doc (byte 4 = const 0) |
| CRC | CRC-16/MODBUS init 0xFFFF poly 0xA001 over payload[2:] — PROVEN (0x79cf10/0x79cf84) | UNKNOWN | UNKNOWN | CRC-16 per imported doc |
| macro step frame | **7 B** `[type=0x80][time=duration/8 16b BE][key 32b BE]` (GamepadDefMap) — PROVEN | UNKNOWN | `TranscribeFrame` (10 B family) — evidence: file exists; format UNKNOWN here | 10 B frame (imported doc) |
| step time granularity | duration/8 (`sdiv …,#8` @0x7a5c80) — PROVEN | UNKNOWN | UNKNOWN | 8 ms (imported doc) |
| key bitmask | `1<<k`, `k<=0x21` (0x7a5c38) — PROVEN | UNKNOWN | UNKNOWN | u32 bitmask (imported doc) |
| stick pattern | table `k=0x22..0x31` OR-accumulated (0x7a5ad0-0x7a5c14) — PROVEN | UNKNOWN | UNKNOWN | u32 pattern (imported doc) |
| runKey default | 46 (`0x2e`) with name "M1" — PROVEN (0x92aabc) | UNKNOWN | UNKNOWN | 5 (`0x2e` in older doc; 0→5 substitution) |
| repeatTime default | 200 (`0xc8`) — PROVEN (0x92ab20) | UNKNOWN | UNKNOWN | UNKNOWN |
| repeatTime unit | ms (low confidence, UI dialog) — PARTIAL | UNKNOWN | UNKNOWN | UNKNOWN |
| macro UI file | `widgets/armor-x_pro/armorx_pro_config_macro.dart` — PROVEN | UNKNOWN | `widgets/general/frame_config_macros.dart` — PROVEN (file exists) | `widgets/general/frame_config_macros.dart` + `shared_widgets/macro_edit_item.dart` — PROVEN (files exist) |
| macro apply handler names | `addMacroResponse`, `changeMacroRunkeyResponse`, `changeMacroRepeatResponse`, `changeMacroUseRepeatTimeResponse`, `changeMacroInUseResponse` — PROVEN | UNKNOWN | UNKNOWN | UNKNOWN |
| device→app D8 macro readback | ABSENT; generic fixed-offset blob parsers `GamepadParam`/`GamepadParam30` instead — PROVEN | UNKNOWN | UNKNOWN | `parsingData` per imported doc |
| readback field offsets | `GamepadParam`: 11/16/32/34/36/38/**43**(→102); `GamepadParam30`: 16/24/34/**70**(→216) — PROVEN | UNKNOWN | UNKNOWN | UNKNOWN |
| receive reassembly step | 15 (`replaceRange(0,15)` / `(15,30)`, 0xA4 dispatcher) — PROVEN | UNKNOWN | UNKNOWN | 15 per 4.0.8 skill note |
| receive frame layout | `data[0]=0xA4`, `data[4]=opcode (0xD6)`, `data[6]=ordinal` — PROVEN for the 0xD6 config path | UNKNOWN | UNKNOWN | UNKNOWN |

---

## What this means for the open questions

1. **Chunk size** — 2.22 answers it for the *old* format: 15, literal, no MTU, no device table.
   2.24/4.0.8 answer it for the *new* format: a per-device table {20, 48, 72} minus 5.
   The three historical candidates {15, 43, 67} are now explained as
   `subpackageLength() - 5` for the three device classes, and **2.22/2.23 are the class that
   maps to 15**. The questions are still not interchangeable across the 2.23→2.24 boundary.
2. **Commit / terminator** — 2.22 has no `0x0A`. If the 4.0.8 tree really emits `0x0A`, the
   terminator semantics changed with the format rewrite; the 2.22 terminator is
   `A4 05 D8 <nfrags+1> <csum>`.
3. **Readback** — absent from 2.22's macro path; the 4.0.8 `parsingData` has no 2.22 counterpart.
   Whether a 2.24-style readback exists needs a 2.24 disassembly pass (not done here).
4. **repeatTime unit** — unchanged (undetermined) in every column; only 2.22 gives a UI hint (ms).

## Exact commands used for the cross-version cells

```
$ R23=~/armorx/re/blutter_out; R24=~/armorx/re/v224/blutter_out; R408=~/armorx-re/mygt408/blutter_out
$ for R in "$R23" "$R24" "$R408"; do
    grep -rln 'TranscribeFrame\|transcribeFrame\|frame_config_macros' "$R"/asm/moojiang/ | head -5
    grep -n 'fmov  *d[0-9]*, #15.0' "$R"/asm/moojiang/units/gamepadset.dart | head -5
    grep -rn 'subpackageLength' "$R"/asm/moojiang/ | head -3
  done
```
(2.23 output: only the three `#15.0` sites, no TranscribeFrame, no subpackageLength.
2.24 / 4.0.8 output: transcribe_frame.dart + frame_config_macros.dart + subpackageLength in
define.dart, and no `#15.0` chunk site.)

```
$ awk 'NR>=316 && NR<=420 && (/mov  *x0, #0x/ || /cmp  *x2, #/ || /b\./ || /ret/)' \
      /home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart
  -> 0x819238 mov x0,#0x14 ; 0x819264 mov x0,#0x48 ; 0x819274 mov x0,#0x30
$ awk 'NR>=477 && NR<=580 && (/mov  *x0, #0x/ || /cmp  *x2, #/ || /b\./ || /ret/)' \
      /home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/define.dart
  -> 0x7b90ec mov x0,#0x48 ; 0x7b9124 mov x0,#0x14 ; 0x7b9134 mov x0,#0x30
```

## Not done (would be required to fill the UNKNOWN cells)

* A full disassembly read of the 2.23 `writeMacroConfig` body (only greps were run).
* A full disassembly read of 2.24 / 4.0.8 `TranscribeFrame` + `writeMacroConfig` to re-derive the
  new-format payload (the imported note was used as-is and is *not* re-verified here).
* The device-id → `subpackageLength()` value mapping (branch ranges were read for 4.0.8's shape but
  not translated into a device-name table).
---

## 2026-09-27 correction (Parts C4–C6 pass) — commit byte, ordinal byte, dispatcher offsets

This pass re-read all four trees at instruction level (`writeMacroConfig` bodies, `subpackageLength`
bodies, the A4 reassemblers). Four statements above are now contradicted. Full evidence in
`results/reconciliation/d8-taxonomy.md`; machine-readable in `d8-taxonomy.json`; regression-tested
by `tests/test_d8_versions.py` (21 tests, all passing). Nothing here was hardware-verified.

### C-1 — the D8 commit/terminator length byte is `0x05`, not `0x0A` (ALL versions)
* **Old claim:** row 92 "terminator / commit … 4.0.8 'commit byte 0x0A' (imported note)"; §"Not
  done" implied the 4.0.8 note was used as-is.
* **New evidence:** 4.0.8 `0x85aba8: mov x16, #0xa` (Blutter annotation `r16 = 10`) stores into the
  *same* `List<int>` (TypeArguments `<int>` @0x85a750) that stores the literal bytes `0xA4` as
  `0x85a748: mov x16, #0x148` and `0xD8` as `0x85a8f8: mov x16, #0x1b0`. Both of those immediates are
  exactly `2 × byte`, so this list holds **tagged Smis** and `#0xa` = `2 × 5` → Dart int **5** →
  wire byte **`0x05`**. Same at 2.24 `0x80012c: mov x17, #0xa` (siblings `0x800060 #0x148`,
  `0x800188 #0x1b0`) and at 2.22 `0x79eb7c: mov x17, #0xa` (already correctly read as 5 in this doc).
  The commit frame carries an empty segment, so the length byte is `segLen + 5` at `segLen = 0` = 5 —
  the compiler constant-folded it; 2.22 emits the computed form. Sibling-immediate evidence +
  arithmetic form the two required anchors.
* **Corrected interpretation:** commit frame is `A4 05 D8 <nfrags+1> <csum>` in **every** version.
  The "0x0A" was a raw-immediate misread (the very failure mode flagged by the project-wide audit).
  It lives in `baselines/imported-research/d8-macro.md` §3.3 → `d8-test-vectors.json`
  (`"A4 0A D8 03 89"`) → this doc's line 92. The toolkit helper
  `automation/scripts/armorx_lab/frames.py::build_d8_terminator()` also encodes `A4 0A D8 …` and is
  wrong (left uncommitted per task rules).
  A **genuine** on-wire `0x0A` exists only as the *ordinal of the 10th fragment* of a 144-byte `D6`
  readback (`A4 0E D6 0A …`, live anchor) — different field, direction and opcode family.
* **Affected versions:** 2.22, 2.23, 2.24, 4.0.8.

### C-2 — the fragment ordinal byte at frame offset 3 exists in the modern format too
* **Old claim:** `baselines/imported-research/d8-macro.md` §3.3 — "data fragments themselves carry
  **no** index/ordinal byte"; this doc's row 91 (ordinal "UNKNOWN" for 2.24/4.0.8).
* **New evidence:** 4.0.8 `writeMacroConfig` appends, in order, `0xA4` (@0x85a748),
  `payload+5` (@0x85a820 `sub` → @0x85a824 `add #5` → BoxInt64 @0x85a87c), `0xD8` (@0x85a8f8) and
  **`i+1`** (@0x85a7e8 `add x9,x6,#1` → `[fp,-0x50]` → BoxInt64 @0x85a938). 2.24 is identical
  (@0x7ffc54 / @0x7ffd34 / @0x7ffe34 / @0x7ffcf4+0x7ffe88). The `len == payload + 5` arithmetic only
  closes with the ordinal present (3 header + 1 ordinal + payload + 1 csum). Same in 2.22
  (@0x79e658/0x79e65c, @0x79e778, @0x79e7a8+0x79e814) and 2.23 (@0x79823c, @0x79833c, @0x798310+0x798394).
* **Corrected interpretation:** the A4 fragmentation framing is **identical across all four
  versions** — `A4 | (segLen+5) | D8 | (i+1) | seg | csum`, length byte == total frame length, plus
  `A4 05 D8 <nfrags+1> <csum>`. Old (2.22/2.23) and modern (2.24/4.0.8) differ **only inside the D8
  payload** (7-byte `GamepadDefMap` records vs 10-byte `TranscribeFrame` frames), in header byte 4
  (`GamepadAtt.type` vs the constant `0x00`), and in the chunk source (literal 15 vs
  `subpackageLength()-5`). The imported 19-byte "no-ordinal" 4.0.8 wire frames are wrong; correct
  frames are 20 bytes for a full chunk.
* **Affected versions:** 2.24, 4.0.8 (and confirms 2.22/2.23).

### C-3 — the 2.22/2.24/4.0.8 A4 reassembler indices are tagged: opcode at byte 2, ordinal at byte 3
* **Old claim:** `results/static/2.22.0901/d8-macro.md` §2 — "`data[4] == 0xD6`", "`data[6] == 2`",
  `sublist(4, 38)`; this doc's row 107 ("`data[4]=opcode`, `data[6]=ordinal`").
* **New evidence:** in 4.0.8 `widgets/general/configs_config.dart` the accessor immediates
  `0xac1e4c mov x16,#12` and `0xac1e80 mov x16,#14` feed `lsl x2,x1,#8` / `orr` to build an adjacent
  big-endian 16-bit value → they address **bytes 6 and 7**, i.e. Dart indices 6 and 7 (12/2, 14/2).
  Likewise `frame_config_macros.dart::parsingData` uses `#30`/`#32` for the adjacent **bytes 15/16**.
  So the index argument is a tagged Smi and the opcode access `#4` is **byte 2**, the dispatch/ordinal
  access `#6` is **byte 3** — exactly the live-anchor layout `A4 14 D6 <ordinal> …`.
  Note the `replaceRange` offset ladder in 2.22 (`#0xf`, `#0x2d` …) contains **odd** immediates,
  which cannot be tagged, so the reassembly **stride stays 15 bytes** (`0,15,30,45,60,75`) — the
  stride claim above is unaffected.
* **Corrected interpretation:** opcode byte 2, ordinal/dispatch byte 3, 15-byte output strides in
  2.22/2.23 and `subpackageLength()-5` strides in 2.24/4.0.8 (4.0.8 `0xac1eec`/`0xac1ef0`).
* **Affected versions:** 2.22 (`d8-macro.md` §2), 2.24, 4.0.8; 2.23 unread on this point.

### C-4 — `"最大步数"` is printed by the caller, not inside `parsingData`
* **Old claim:** `baselines/imported-research/d8-macro.md` §5.2 — the `parsingData` routine "prints
  `最大步数$steps`".
* **New evidence:** the print is at 4.0.8 `0xac3568` / 2.24 `0x915bf4`, in the notification closure
  that **calls** `parsingData` (4.0.8 `0xac35ac`). Inside `parsingData` the reads are
  `list[3]` vs `field_23 - 2` (limit check @0xac3620-0xac3638) and a **little-endian u16 at bytes
  15–16 × 8 ms** (`0xac3744-0xac375c`) stamped into the last frame's `time` (`0xac377c`), then
  `changeTranscribeFrameToDefMacro` (@0xac37a4). The `/10 → steps ≤ 256` formula in the old doc was
  not reproduced here (CONTRADICTED as a description of this routine; the offsets 15/16 are PROVEN,
  their meaning PARTIAL).
* **Affected versions:** 2.24, 4.0.8.

### C-5 — D8 receive/readback status, per version (new, replaces the UNKNOWN cells)
* 2.22.0901 / 2.23.0609: generic A4/D6 reassembler PRESENT (2.22 `configs_config.dart:3108` closure
  @0x8a6a04; 2.23 `parsingData` @0x8098cc) but **D8 macro readback ABSENT** — no `0xD8`/`216`
  comparison exists anywhere under `widgets/` (recursive grep empty in both trees). Macro state comes
  from the server JSON (`MacroRow.fromJson`). The literal `216` in 2.22 is a `GamepadParam30`
  `sublist(70,216)` bound, not an opcode test.
* 2.24.0919 / 4.0.8: **PRESENT / PARTIAL**. Notification closure tests `list[2]` against
  `0xFC` (2.24 `0x915a68` / 4.0.8 `0xac33e0`, → exit), `0xD8` (2.24 `0x915a90` / 4.0.8 `0xac3408` →
  `"写入结果"` + `printHex`) and a third opcode `0xD3` (2.24 `0x915ad8` / 4.0.8 `0xac3448` → reads
  `list[7]`, `list[8]`). Chain: notification → `parsingData` (2.24 0x915c38 / 4.0.8 0xac35ac) →
  `TranscribeFrame.fromConfigData` (2.24 0x80163c / 4.0.8 0x85e32c) →
  `changeTranscribeFrameToDefMacro`. Readback offsets read: byte 2 (opcode), byte 3 (compare vs
  `field_23-2`), bytes **15–16** (u16 LE ×8 ms). No dedicated "read macro" command exists in any
  version — the macro readback rides the D6 config blob (2.22/2.23: no macro fields, so effectively
  none) or the D8/D3 notification.

### Still open after this pass
* 2.23's fragment ordinal value is STRONG EVIDENCE only (2.22/2.24/4.0.8 PROVEN).
* 2.24 vs 4.0.8 `subpackageLength()` device-id branches are **not** identical (2.24 has no `9/10`
  arms); the ARMOR-X Pro's `field_7` id is still UNKNOWN statically — the chunk in use is observable
  at runtime from the app's `包数->N` log line.
* `repeatTime` unit (ms assumed): UNKNOWN in all four.
