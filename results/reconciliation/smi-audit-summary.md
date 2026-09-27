# Smi audit — summary

**Date:** 2026-09-27 · **Scope:** the four ARMOR-X Pro Blutter Dart-AOT trees + imported-research
baselines + `results/static/2.22.0901/*` + `results/final/*` + the toolkit docs.
Full ledger: `smi-audit.md` / `smi-audit.json`. Method: `dart-smi-methodology.md`.
Guard: `../../tests/test_smi_constants.py` (12 tests, all passing).

## Counts (46 items audited)

| classification | count |
|---|---:|
| **TAGGED SMI — CORRECTED** | **6** |
| CORRECT AS DOCUMENTED | 13 |
| RAW INTEGER — NO CHANGE | 26 |
| AMBIGUOUS | 1 |
| total | 46 |

Corrections: K1 (key bit masks), D1 (D8 commit byte), L3 + L4 (light mode ordinals),
D5 + D6 (2.22 macro envelope defaults). One secondary non-Smi decode error also found (D4).

## The single most important correction

> **`keyCapture = 0x8000`, and the rule is `bit == key id` — there is no `+1`.**
> The imported note `"keyCapture = 0x10000, bit index = key id + 1"` read the raw `mov`
> immediate of a Dart Smi getter without halving it. `Smi(n) == n << 1`, so
> `4.0.8 define.dart:1583 @0x94cb70  mov x0, #0x10000` is the integer **0x8000 = bit 15 =
> config key id 15 (Capture)**; `#0x20000 → 0x10000 = bit 16 (D-pad up)`;
> `#0x80 → 0x40 = bit 6 (LB)`. Four independent anchors (24-getter closure, the app's own
> id→label map literal with `sbfiz #1` boxing, the `List<int>(32)` powers-of-two table in
> pp.txt, and the 2.22 build's own tables) all agree, and the un-halved reading is
> *self-contradictory* (`0x80` would claim bit 7 = RB, but the app's map says LB = id 6).

## Corrections, in order of blast radius

1. **D1 — D8 commit/terminator byte `0x0A` → `0x05`.** `4.0.8 @0x85aba8` and `2.24 @0x80012c`
   both `mov x16, #0xa` into a `List<int>` whose siblings are `#0x148 → 0xA4` and
   `#0x1b0 → 0xD8`. The frame is **`A4 05 D8 <nfrags+1> <csum>`**, matching the live/deduced wire
   frame. Touches: `baselines/imported-research/d8-macro.md` §3.3/§7,
   `baselines/imported-research/executive-report.md` §8, `results/final/open-questions.md:12`,
   `results/final/virtual-armorx-status.md:65`,
   `ble/virtual-armorx/armorx_protocol.py:183,207`, and the toolkit harness
   `armorx_lab/frames.py:76`. With `0x05` the frame obeys the general rule
   *length byte == total frame bytes*, so the `0x0A` special case can be deleted.
2. **K1 — key bit masks `bit == key id` (no `+1`).** As above.
3. **L3 / L4 — lighting mode ordinals are 1,2,3, not 2,4,6.** `writeLightConfig` stores
   `#2/#4/#6` into `List<int>` elements whose length field is Smi-encoded; 2.22's call-site mode
   arguments `#2/#6` are stored into a tagged object field ⇒ **1 and 3**. The id→name mapping
   stays UNKNOWN.
4. **D5 / D6 — 2.22 macro envelope defaults `runKey 46 → 23` (= M1, name in the same literal)
   and `repeatTime 200 → 100` ms.** Both are `Map<String,dynamic>` values written from a tagged
   `mov`.
5. **D4 (secondary, not a Smi bug) — `subpackageLength()` device-id sets.** The switch operand
   and its case labels are **raw** (they include odd labels 1,3,7,9), so nothing is halved; but
   id **11 belongs to the `→72` group** (devGale2), not `→20` as `d8-macro.md` §3.3 prints.

## What did NOT change (the 26 raw items, highest-value ones)

* `pp.txt` is **already decoded** — the `List<int>(32)` powers-of-two table, the `List<int>(20)`
  turbo-id list, and `Obj!Duration { off_8: int(0xfa0) }` (= exactly **4 ms**, anchored by the
  live-proven `int(0x7a120)` = 500 ms). Never halve anything read from `pp.txt`; `_Int32List`
  entries are native and raw.
* Directives that operate on **unboxed** registers: D8 stick-pattern `orr` masks
  (`0x80000000`, `0xa55a0000`…), the DPI `& 0x0F` selector, the LED `1 << id` masks and the
  `0x3F` id-space bound, the turbo serializer's `>>24/>>16/>>8/&0xFF`, and the
  `sdiv #8` / `&0x0F` / `&0xFF0` D8 timing pack.
* Compare operands that follow `LoadInt32Instr` (`sbfx #1`): `_keyByte`'s `k ≤ 0x20`,
  `_stickByte`'s `0x22..0x31`, the smart build's raw `subpackageLength` switch.
* `AllocateArray`/`AllocateContext` sizes, `ReplaceRange`/`sublist` bounds, element offsets:
  the config families **88/144/240/280/335/456/484/508** and `144 = 4 + 108 + 32`.
* Device enum ids (`devArmorX` = 6 → 8 → **10**), the deviceName/F8/DD/F7/E1 opcodes and lengths,
  the CRC-16/MODBUS constants, the firmware thresholds, `sensorRightKeyBit`/`sensorSwitch`,
  and all live-captured wire bytes.
* **Odd immediates are never Smis** — verified on the 2.22 Slider `divisions = 255`
  (`mov x1, #0xff`, 64-bit `stur x`) and on `LightColorRainBow3` colour/speed fields (`-1`, `0xff`).
  Those fields hold **untagged** integers; do not halve them.

## Standing ambiguity

* **D11** — the D8 readback id table literals `0x4e/0x50/0x52/0x5e/0x62/0xfe`
  (`transcribe_frame.dart 0x85e5d4-0x85e5f8`). The 16-bit halves are compared against table
  constants whose encoding was not established in this pass; recorded **AMBIGUOUS** with both
  hypotheses (raw pattern vs Smi ids 39/40/41/47/49). Do not promote the old `78/80/82/94/98` reading.

## Required actions (owners of the affected files)

1. `baselines/imported-research/`: fix the two `bit = id + 1` statements (`executive-report.md:84`,
   `docs/mygt-4.0.8-reconciliation.md:30`), the `0x0A` terminator
   (`d8-macro.md`, `executive-report.md`), the `2,4,6` light modes, and the `subpackageLength`
   id-11 row. Append, do not rewrite unrelated history.
2. `results/final/open-questions.md:12` and `results/final/virtual-armorx-status.md:65`: the `0x0A`
   question is **closed** (byte is `0x05`).
3. `ble/virtual-armorx/armorx_protocol.py:183,207`: emit and accept `A4 05 D8 …`; drop the special
   case and apply the general *length byte == total frame bytes* rule.
4. Toolkit repo `armorx-re/repo/docs/mygt-4.0.8-reconciliation.md:30` and
   `tools/lab/harness/armorx_lab/frames.py:76`: **not committed from this session** (hard rule);
   recorded here for the toolkit owner.
5. Re-run `python3 armorx-lab/tests/test_smi_constants.py` after any constant table is edited;
   it fails loudly if the `+1` rule, the `0x0A` byte, the `2,4,6` modes or an over-eager halving
   of the raw items comes back.
