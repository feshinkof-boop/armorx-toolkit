# E2 verdict for 2.22.0901

## Verdict: **ABSENT** (PROVEN STATIC)

0xE2 does **not** exist anywhere in the 2.22.0901 Dart AOT protocol code. There is no builder, no
dispatcher comparison, no switch-table entry and no pool constant for it. This dates the entry of
E2 into the protocol to a later build than 2.22.0901.

## Searches run (verbatim, against `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/`)

| # | question | command | result |
|---|---|---|---|
| 1 | Smi form of 0xE2 (`#0x1c4`, since Smi = 2×byte) anywhere in the whole asm tree | `grep -rn '#0x1c4' asm/` | 31 hits, of which **4 in `asm/moojiang/`** and 8 in `syncfusion_flutter_pdf`, 1 in `intl` |
| 2 | where are the 4 moojiang hits | `grep -rn '#0x1c4' asm/moojiang/` | **all four are `generated/intl/messages_{en,ja_JP,ko_KR,zh_CN}.dart:4252`** — localization message-index immediates, not protocol code |
| 3 | raw byte 226 / `0xe2` as a register immediate | `grep -rnE '(mov +x[0-9]+, #0xe2\|r[0-9]+ = 226)' asm/moojiang/` | 8 hits — **all in `generated/intl/messages_*.dart:2109-2110`**, i.e. the same localisation tables |
| 4 | raw 0xE2 compared against a frame byte | `grep -rnE 'cmp +x[0-9]+, #0xe2\|cmp +w[0-9]+, #0xe2' asm/moojiang/` | **0 hits** |
| 5 | pool constant list containing 226 / preceded by 0xE2 | `grep -oE 'List\([0-9]+\) \[[^]]*\b226\b[^]]*\]' pp.txt` | **0 hits** |
| 6 | decimal literal 226 in the object pool | `grep -cE '\b226\b' pp.txt` | **0** |
| 7 | full oppcode census incl. 0xE2 | `python3 tools/2.22.0901/opcode_census.py <tree> out/_opcode_census.json` | 0xE2 = 0 hits |

## Interpretation

- The **only** occurrences of the value 452/0x1c4 or 226/0xe2 in the whole tree are inside
  localisation string tables (`generated/intl/messages_*.dart`) and the third-party
  `syncfusion_flutter_pdf` library, both of which are noise for protocol purposes
  (the same noise that forced `opcode_census.py` to exclude `generated/intl/`).
- No A5 builder in 2.22 emits 0xE2 (the complete set of A5 builders is enumerated and
  byte-reconstructed in `command-index.md` §2 — 0x0B, 0x0E, 0x70, 0xD2, 0xD4, 0xD6, 0xEF).
- No A4 fragment builder appends 0xE2 (the only A4 opcodes in 2.22 are 0xD7 and 0xD8).
- No reply handler compares against 0xE2: the ARMOR-X Pro inbound handler @0x7ab44c compares the
  frame header against 0xA5, the opcode against 0x0B (11) and 0xEF (239) only; the config handlers
  @0x89b438 / @0x8a6a04 accept only 0xA4/0xA5 frames carrying 0xD4 (424), 0xD6 (428) or 0xD7 (430).

## Dating

E2 is therefore **not present in 2.22.0901**. It must have been introduced between 2.22.0901 and
the build in which it first appears; the four-way comparison in the sibling research trees is the
place to pin that down (`~/armorx/re/blutter_out/` = 2.23, `~/armorx/re/v224/` = 2.24,
`/home/salamanka/armorx-re/mygt408/blutter_out/` = 4.0.8). This file deliberately does **not**
carry those builds' conclusions into a 2.22 claim.

## What would settle it definitively

1. `grep -rn '#0x1c4'` and `grep -rnE 'mov +x[0-9]+, #0xe2'` in each sibling tree, excluding
   `generated/intl/` — the first build with a hit outside the localisation tables dates E2's entry.
2. A live capture of the 2.22 app during a firmware/version refresh: if the trace contains no
   `A5 .. E2` frame, the static result is confirmed end-to-end.