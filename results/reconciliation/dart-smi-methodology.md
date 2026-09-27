# Dart Smi / tagged-integer methodology for the four Blutter AOT trees

Status: **CURRENT** (2026-09-27). Supersedes every ad-hoc "halve the immediate" note scattered
through the project. Companion files: `smi-audit.md`, `smi-audit.json`, `smi-audit-summary.md`,
and the executable regression guard `../../tests/test_smi_constants.py`.

Scope: the four trees only —

| version | Dart | tree |
|---|---|---|
| 2.22.0901 | 2.17.5 | `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out` |
| 2.23.0609 | 2.19.6 | `/home/salamanka/armorx/re/blutter_out` |
| 2.24.0919 | 3.2.3  | `/home/salamanka/armorx/re/v224/blutter_out` |
| 4.0.8     | 3.12.2 | `/home/salamanka/armorx-re/mygt408/blutter_out` |

Line numbers below are Blutter `asm/...` **file lines**; `0xADDR` is the instruction address in
the `// 0xADDR:` comment. APKs were never modified; nothing here came from a device.

---

## 1. The representation rule (identical in all four builds)

Dart's AOT snapshot on `arm64 android compressed-pointers null-safety` tags small integers:

```
Smi(n)  =  n << 1          low bit 0            range about ±2^62
Mint(n) =  heap object      low bit 1 (pointer)  for values outside Smi range
HeapObject tag = 1, Smi tag = 0
```

**Consequences that decide every case in this project:**

1. A `mov xN, #K` whose destination is a **Dart int slot** carries the *encoded* value, so the
   logical Dart integer is `K / 2`.
2. Blutter's own human annotation prints the **raw instruction operand in decimal**, never the
   decoded value: `mov x16, #0x14a` is annotated `r16 = 330` (= 0x14A), it does **not** print
   165. Use the annotation only to read the operand; do the halving yourself.
3. Because the encoding is `2n`, **an odd immediate can never be a valid Smi.** This is a
   cheap, mechanical negative test (§4, rule N1).
4. The four Dart versions do **not** differ in any of this. What differs is Blutter's register
   naming (`r17` in 2.24 vs `x16` in 4.0.8) and the *dispatch style*: 2.17.5/2.19.6 dispatchers
   often compare raw headers (`cmp x1, #0xa4`), 3.2.3/3.12.2 compare Smi forms
   (`cmp w0, #0x14a` = 0xA5). A constant scanner keyed on one form silently returns zero hits on
   the other; that is a *scanner* issue, not a tagging difference.
5. `Smi = 2n` is not an assumption here — it is visible in the code as the box/unbox idioms:
   * **box**  `sbfiz x0, x2, #1, #0x1f` + `cmp x2, x0, asr #1` + `b.eq` (`BoxInt64Instr`),
   * **unbox** `sbfx xN, xM, #1, #0x1f` followed by `tbz wM, #0,` + `ldur xN, [xM, #7]`
     (`LoadInt32Instr`, with the Mint branch).

---

## 2. Positive identification — the immediate IS a tagged Smi

Any one of these is sufficient; two of them is a proof.

| # | Signature in the asm | Why |
|---|---|---|
| P1 | store target is a `List<int>` element: `AllocateArray` + `AllocateGrowableArray` with `TypeArguments: <int>`, or a `_GrowableList` whose `field_b` is maintained as a Smi (`add x2,x1,#1; lsl x3,x2,#1; stur w3,[x0,#0xb]`), then `add x4,x3,x1,lsl #2; stur w16,[x4,#0xf]` | `List<int>` elements are Dart ints, i.e. tagged. Smi-encoded *length* proves the list is not typed-data. |
| P2 | store target is a Dart object/closure-context int field (`StoreField rX->field_f = r16`, `stur w16,[xX,#0xf]`) | object fields hold tagged values. |
| P3 | `mov xN, #K` immediately followed by `lsl xN, xN, #1` before the store | the code explicitly re-tags a raw value → the stored value is a Smi and the *source* was raw. |
| P4 | the same immediate appears in a context where a byte is required and `K > 0xFF` | e.g. `#0x1fe` (510) written into a byte list can only mean 255. This proves the whole list is tagged. |
| P5 | a `cmp wK, #V` comparison on a value that was just produced by `BoxInt64Instr` / `sbfiz #1` | the compare is against the **tagged** form ⇒ logical value `V/2`. |

## 3. Negative identification — the immediate is RAW (never halve)

| # | Signature | Why |
|---|---|---|
| N1 | **the immediate is odd** (e.g. `mov x1, #0xff`) | an odd number is not `2n`; it is not a Smi. (See §5/W6 for the live case.) |
| N2 | the operand feeds `and` / `orr` / `eor` / `lsl` / `lsr` / `asr` / `ubfx` / `sxtw` / shift-amounts / masks (`#0xff`, `#0x3f`, `#0xf`, `#0x1e`, `#0x1ff`) | Dart bitwise arithmetic runs on an **unboxed** register; the result is boxed only at the end (`BoxInt64Instr`). |
| N3 | a `cmp`/`cbz`/`tbz` on a register that was just produced by `LoadInt32Instr` (`sbfx xN,xM,#1,#0x1f`) | the code has *just un-tagged* it; the comparison is against the raw value. |
| N4 | `AllocateArray` / `AllocateGrowableArray` / `AllocateContext` **size** arguments, `ReplaceRange`/`sublist(start,end)` bounds, `add x4,x3,x1,lsl #2` element offsets | array lengths and indices are plain `int` scalars. |
| N5 | `_Int32List` / `Int8List` / `Uint8List` elements and any `strb`/`ldrb` | typed-data; raw by construction. `strb` ⇒ raw byte, `stur w` at 4-byte stride ⇒ `List<int>` (tagged). |
| N6 | the value in **`pp.txt`** | Blutter prints `List<int>(n)` literals **already decoded** (see §5/W5), and `Obj!Duration { off_8: int(0x…) }` already decoded to microseconds. Do **not** halve anything read out of `pp.txt`. `_Int32List(n) [...]` entries are native int32 and are raw. |
| N7 | an immediate stored with the **full 64-bit** form (`stur xN`) together with a non-even value | observed for genuinely untagged integer fields (Dart's unboxed-int field path); treat as raw (§5/W6). |
| N8 | `movk …, lsl #16` pairs building a value written to `Future.delayed` | the constructed value is the raw microsecond count (see the 500 ms anchor `mov x0,#0xa120; movk x0,#16`). |

## 4. Decision procedure (apply mechanically, top to bottom)

```
1. Locate the instruction and the immediate K.
2. If K is odd                     -> RAW.  stop.            (N1)
3. Read the *destination*:
   a. typed-data / strb / ldrb     -> RAW.  stop.            (N5)
   b. rt is a List<int> element    -> tagged -> value = K/2. (P1)
   c. rt is a Dart object field    -> if store is `stur xN` and K even but the field is
                                      used in raw bitwise code -> AMBIGUOUS; else tagged. (P2/N7)
   d. rt is an Allocate*/bound/off -> RAW.  stop.            (N4)
   e. rt is a register consumed by and/orr/lsl/asr/ubfx,
      or K itself is the shift count/mask -> RAW.  stop.     (N2)
4. Read the *source* of the compared/operated register:
   just after LoadInt32Instr(sbfx#1) -> RAW.                 (N3)
   just after BoxInt64Instr(sbfiz#1)-> tagged -> value = K/2.(P5)
5. Cross-check with a second, independent anchor before writing a conclusion:
   - a sibling store in the SAME list that only makes sense halved  (P4)
   - pp.txt (already decoded)                                        (N6)
   - a live-captured wire byte, or the app's own id→label map literal
   - objs.txt enum index / a list-length or device-id table
   Still ambiguous -> record AMBIGUOUS. Never guess.
```

**Two independent anchors per correction** is the project's standing rule; every correction in
`smi-audit.md` carries at least two.

---

## 5. Worked examples from the four trees

### W1 — `keyCapture` / the key bit masks (the original bug)

`4.0.8 asm/moojiang/define.dart:1583` @`0x94cb70`:

```
static int keyCapture() {
  // 0x94cb70: r0 = 65536
  //     0x94cb70: mov             x0, #0x10000
  // 0x94cb74: ret
}
```

`x0` is the return register; the function's declared return type is `int`, so the value leaving
the frame is a **tagged Smi** ⇒ logical value `0x10000 / 2 = 0x8000` = **bit 15**.

The same class holds 23 more such getters, and halving them yields a **gapless
one-key-one-bit table** (2.22 `units/gamepadset.dart`, 2.23 same file, 2.24/4.0.8
`define.dart`):

| getter | raw imm (4.0.8) | /2 | bit | config key id |
|---|---|---|---|---|
| `keyL1` | `#0x80` | 0x40 | 6 | 6 (LB) |
| `keyR1` | `#0x100` | 0x80 | 7 | 7 (RB) |
| `keyL2` | `#0x200` | 0x100 | 8 | 8 (LT) |
| `keyR2` | `#0x400` | 0x200 | 9 | 9 (RT) |
| `keySelect` | `#0x800` | 0x400 | 10 | 10 |
| `keyStart` | `#0x1000` | 0x800 | 11 | 11 |
| `keyRThumb` | `#0x8000` | 0x4000 | 14 | 14 (R3) |
| `keyCapture` | `#0x10000` | **0x8000** | **15** | **15 (Capture)** |
| `keyUp` | `#0x20000` | 0x10000 | 16 | 16 (D-pad up) |
| `keyDown` | `#0x40000` | 0x20000 | 17 | 17 |
| `keyLeft` | `#0x80000` | 0x40000 | 18 | 18 |
| `keyRight` | `#0x100000` | 0x80000 | 19 | 19 |
| `keyM1` | `#0x1000000` | 0x800000 | 23 | 23 (M1) |
| `keyM2` | `#0x2000000` | 0x1000000 | 24 | 24 (M2) |
| `keyM3` | `#0x4000000` | 0x2000000 | 25 | 25 (M3) |
| `keyM4` | `#0x8000000` | 0x4000000 | 26 | 26 (M4) |
| `keyM6` (2.22/2.23) | `#0x20000000` | 0x10000000 | 28 | 28 (M6) |
| `keyY` | `#0x20` | 0x10 | 4 | 4 (Y) |

Per-version raw immediates verified for all four trees (see `smi-audit.json` item K1/K3).
**Rule: `bit == config key id`. There is no `+1`.**

Anchors:
1. **Internal** — the 24-getter set only closes onto ids 0..26 + 28 if the immediates are halved;
   unhalved it collides (`keyL1 = #0x80` = "bit 7" would duplicate RB, and `keyY = #0x20` would
   be bit 5 which has no key).
2. **`pp.txt` powers-of-two table** —
   `2.22 pp.txt:27316  [pp+0x28950] List<int>(32) [0x1, 0x2, …, 0x80000000]`
   Blutter prints the *decoded* values; this is exactly `[1 << i for i in 0..31]`, i.e. the
   app's bit table is indexed by key id.
3. **The app's own id→label map literal** — `4.0.8 key_remap_t.dart:635` `gamePadKeyName`
   @`0x92d69c` inserts `raw 30 → "Capture"` and boxes the lookup key with `sbfiz x0,x2,#1`:
   raw 30 ⇔ id 15, and 15 is `keyCapture`'s bit (0x8000) after halving. A map and a mask meet on
   the same number 15.
4. **A second, independent switch** — `gamePadMapKeyWidget` @`0x92cfc8` switches on the *real*
   int id with `case 0xf` = 15 in the icon group {10,11,15,16,17,18,19}.

### W2 — the D8 commit / terminator byte (the `0x0A` question)

`4.0.8 asm/moojiang/units/gamepadset.dart:7226` (function `writeMacroConfig` @`0x85a670`):

```
// 0x85aaf0: r0 = AllocateArray()
// 0x85aaf8: r16 = 328
//     0x85aaf8: mov             x16, #0x148     ; List<int> element 0
// 0x85abac: stur            w16, [x4, #0xf]    ; -> 0xA4
// 0x85aba8: r16 = 10
//     0x85aba8: mov             x16, #0xa       ; List<int> element 1
// 0x85abac: StoreField: r4->field_f = r16      ; -> 5, NOT 0x0A
// 0x85abf0: r16 = 432
//     0x85abf0: mov             x16, #0x1b0     ; -> 0xD8
```

The list is a `List<int>` (allocated with `TypeArguments: <int>`; its sibling element stores are
tagged), the pipeline appends with a Smi-encoded length
(`add x2,x1,#1; lsl x3,x2,#1; stur w3,[x0,#0xb]`), and `#0x148`/`#0x1b0` are only meaningful
halved (`0xA4`, `0xD8`). Therefore `#0xa` is the Smi of **5**, and the commit frame is

```
A4 05 D8 <nfrags+1> <csum>          (5 bytes; length byte == total frame bytes)
```

not `A4 0A D8 …`. Identical instruction in 2.24: `units/gamepadset.dart:2108` @`0x80012c`
`mov x17, #0xa`.

Anchors: (i) the same-list siblings `#0x148→0xA4`, `#0x1b0→0xD8`; (ii) the **live/deduced wire
frame** `A4 05 D8 <nfrags+1> <csum>`; (iii) 2.22's independent terminator, where the immediate
`r17 = 10` at `0x79eb7c` was already read as Dart 5 in the lab's own 2.22 pass.

### W3 — `writeLightConfig` per-zone colour-mode indices are 1,2,3 — not 2,4,6

`4.0.8 units/gamepadset.dart` inside `writeLightConfig` @`0x84938c`:

```
// 0x849824: r16 = 2 ; mov x16,#2 ; StoreField r4->field_f = r16
// 0x849888: r16 = 4 ; mov x16,#4 ; StoreField r4->field_f = r16
// 0x8498ec: r16 = 6 ; mov x16,#6 ; StoreField r4->field_f = r16
```

Each store is preceded by the growable-append idiom
(`LoadField r3 = r0->field_f; add x4,x3,x1,lsl #2; stur w16,[x4,#0xf]`) and the list length is
kept as a Smi (`add x2,x1,#1; lsl x3,x2,#1; stur w3,[x0,#0xb]`) ⇒ `List<int>` ⇒ **tagged**.
Values are **1, 2, 3**.

Anchors: (i) the `sbfx #1` un-tag of `field_b` proving the list is a tagged `List<int>`; (ii) the
fully folded value range stays a small ordinal 1..3, matching the app's 4 named light modes
(2.22 l10n: `Normal`, `Breathing`, `Gradient`, `Flicker`).

### W4 — DPI `& 0x0F` is a RAW mask, not a halved value (counter-example)

`4.0.8 units/gamepadset.dart` @`0x946750` (`writeDpiConfig`):

```
// 0x94686c: ubfx    x1, x1, #0, #0x20     ; unbox the caller's int
// 0x946870: and     w2, w1, #0xf          ; RAW mask on the raw value
// 0x946874: lsl     w1, w2, #1            ; re-TAG the result
// 0x946878: stur    w1, [x0, #0x1b]       ; -> List<int> element
```

Because the mask is applied to an *unboxed* register and the result is re-tagged with `lsl #1`,
the frame byte is `dpi & 0x0F` (0..15). The fc-dpi document's "4-bit selector" reading is
**correct**; halving the mask (`#0xf` → 7) would be the error. Same file: header
`#0x14a → 0xA5`, length `#0xa → 5`, opcode `#0x1f8 → 0xFC`, legacy `#0x1ec → 0xF6`,
motion header `#0x156 → 0xAB`, sub-command `#0x4a → 0x25`.

### W5 — `pp.txt` is already decoded

```
2.22 pp.txt:27316  [pp+0x28950] List<int>(32) [0x1, 0x2, 0x4, …, 0x80000000]
2.22 pp.txt:57877  [pp+0x4bc80] List<int>(20) [0x17, 0x18, 0x19, 0x1a, 0, 0x1, …]
4.0.8 pp.txt:62489 [pp+0x56188] Obj!Duration@b34461 : { off_8: int(0xfa0) }
4.0.8 pp.txt:4181  [pp+…] Obj!Duration : { off_8: int(0x7a120) }
```

`0x80000000` cannot be a tagged immediate (`2n` overflows 32 bits), and `int(0x7a120)` =
500000 µs = the **live-proven 500 ms** `Future.delayed`. So Blutter prints decoded values in
`pp.txt`: the 32-entry table is literally `1<<i`, the 20-entry turbo list is
`{23,24,25,26, 0,1,3,4, 16,17,18,19, 6,8,7,9, 13,14,10,11}`, and `int(0xfa0)` is **4000 µs = 4 ms**
(the D8 inter-fragment delay). **Do not halve `pp.txt`.** (`_Int32List` entries, by contrast, are
native and raw.)

### W6 — when the *store*, not the value, is untagged (parity test)

`2.22 widgets/rainbow/rainbow_config_light.dart:2356` @`0x9419f8` (Slider literal):

```
// 0x9419f8: r1 = 255
//     0x9419f8: mov             x1, #0xff
// 0x9419fc: StoreField: r0->field_2f = r1
//     0x9419fc: stur            x1, [x0, #0x2f]
```

`0xff` is **odd** ⇒ not a Smi (rule N1), and the store uses the full 64-bit form (`stur x1`,
rule N7) while the neighbouring double fields use `stur d0`. The field therefore holds the
untagged value **255**; the documented slider range `min 50, max 255, divisions 255`
(`fmov` of the pool doubles `0x4049000000000000` = 50.0 and `0x406FE00000000000` = 255.0) stands.
The same raw signature appears for `LightColorRainBow3` colour/speed fields
(`mov x1, #-1` at 4.0.8 `0x9ebddc` and `#0xff` at `0x9ebde4` → `field_1f`, `field_2f`) — read
those raw. **Odd immediates and `stur x` stores are the discriminator.**

### W7 — do NOT halve raw bit-table immediates

`4.0.8 units/transcribe_frame.dart` `_stickByte` @`0x85dad4`:

```
// 0x85db78: cmp x2, #0x22        ; after r2 = LoadInt32Instr(r0) / sbfx #1
// 0x85db88: cmp x2, #0x31
// 0x85dbc8: orr x2, x1, #0x80000000
// 0x85dc28: r16 = 2774138880 ; mov x16, #0xa55a0000
```

The id is compared raw (`0x22..0x31` = 34..49) and the patterns are `orr`ed into an unboxed
accumulator; `#0xa55a0000` = 2774138880 as a raw 32-bit word. Halving any of these would be
wrong. Same in 2.22 (`0x7a5ad0-0x7a5c14`) and 2.24 (`0x80091c`).

---

## 6. Version-specific notes

* **2.17.5 (2.22.0901)** — key getters live in `units/gamepadset.dart` (not `define.dart`);
  light/macro builders are in `gamepadset.dart`. Dispatchers compare raw headers. `pp.txt`
  `List<int>` printing style is the same as the newer builds.
* **2.19.6 (2.23.0609)** — same split; device-id comparisons double the load
  (`lsl x2,x1,#1; cmp w2,#0xc` ⇒ id 6) — that *is* the tagged form; do not "fix" it.
* **3.2.3 (2.24.0919)** — getters moved to `define.dart`; `keyCapture` present
  (`define.dart:619` @`0x7c42ac` `mov x0,#0x10000` → 0x8000). Blutter uses `r17`/`x16`
  interchangeably; a grep for `#0x1b0` alone misses 2.24 only because of register naming, not
  tagging.
* **3.12.2 (4.0.8)** — same as 2.24; Smi-tagged dispatch compares
  (`cmp w0, #0x14a`, `cmp w0, #0x1ac` for 0xD6, `cmp w0, #0x1b0` for 0xD8) are all
  **tag-doubled**; the logical byte is the halved immediate.

## 7. Anti-patterns to never repeat

1. Reading a `mov x0, #imm` in an `int`-returning getter as the literal value
   (this is what produced `keyCapture = 0x10000, bit = id+1`).
2. Assuming a doc that already divides by two is wrong "because 0x14a is not 0xA5"
   — some tables *are* correctly halved; audit, don't blanket-halve.
3. Halving `pp.txt` values (already decoded) or `_Int32List` entries.
4. Halving comparison operands that follow `LoadInt32Instr` (already un-tagged).
5. Halving `AllocateArray`/`AllocateContext` sizes, indices, offsets, shift counts, masks,
   `orr`/`and` immediates on unboxed accumulators, or `movk`-built microsecond counts.
6. Treating a `stur x` (64-bit) untagged store of an odd immediate as a Smi.
7. Carrying one build's constant table to another without re-reading the instruction there.
