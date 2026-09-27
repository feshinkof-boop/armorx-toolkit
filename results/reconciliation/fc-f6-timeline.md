# FC / F6 DPI timeline — 2.22.0901 → 2.23.0609 → 2.24.0919 → 4.0.8

Definitive per-version DPI timeline, settled from raw Blutter disassembly (2026-09-27).
Supersedes the *(historical)* columns in `results/version-diff/dpi-history.md` for the 2.23/2.24
rows and resolves the self-contradictory `F6` wording (`< 0x35` vs `>= 0x35`).

Trees: 2.22 = `static/blutter/2.22.0901/blutter_out`; 2.23 = `/home/salamanka/armorx/re/blutter_out`;
2.24 = `/home/salamanka/armorx/re/v224/blutter_out`; 4.0.8 = `/home/salamanka/armorx-re/mygt408/blutter_out`.

Labels: **PROVEN STATIC** unless noted.

## 0. Summary matrix

| aspect | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|---|---|---|---|
| normal-DPI writer | **ABSENT** | `writeDpiConfig` @**0x7fdee4** | `writeDpiConfig` @**0x894000** | `writeDpiConfig` @**0x946750** |
| default opcode | — | **0xFC** unconditional | **0xFC** (opcode slot 2 of the frame array) | **0xFC** |
| legacy `F6` branch | ABSENT | **ABSENT** (no `#0x1ec` anywhere in `asm/moojiang`) | **PRESENT** | **PRESENT** |
| devices that enter the F6 branch | — | — | `{devRainbow2Pro(3), devC2SL(5)}` | `{devRainbow2Pro(3), devRainbow3(4), devGale2(0xb), devC2SL(7)}` |
| version threshold | — | — | `cmp x1,#0x35 ; b.lt` → **F6 when version ≥ 0x35** (= 53) | same, on static `0xb6c` |
| version source | — | — | static **0x102c** (= `zkmVersion`, set from the `0B` reply) | static **0xb6c** |
| frame shape | — | `A5 05 FC <sel&0x0F> <cks>` | `A5 05 FC/F6 <sel&0x0F> <cks>` | `A5 05 FC/F6 <sel&0x0F> <cks>` |
| DPI query | ABSENT | present (`A5 05 FC 80 …`) | `getDpi` @0x91b090 (FC/F6, u16 branch ≥ 0x36) | present |
| motion/gyro DPI (`AB` family) | ABSENT | ABSENT | ABSENT | `AB 07 05 25 <u16 LE> <cks>` @0x946158 |
| opcodes present | none (`FC`/`F6`/`AB` all absent) | `FC` | `FC`, `F6` | `FC`, `F6`, `AB` |

`0x35 = 53` decimal. Wiring byte `B` stored in a frame array appears as the tagged Smi `2·B`
(`0xFC`→`#0x1f8`, `0xF6`→`#0x1ec`, `0xA5`→`#0x14a`).

## 1. 2.23 — FC only, unconditional (PROVEN STATIC)

`writeDpiConfig` @ **0x7fdee4** (`units/gamepadset.dart`, lines 7663-7777). Literal pseudocode:

```
0x7fdf34  AllocateArray(#0xa)          ; #0xa = Smi(5)  -> 5-element array
0x7fdf50  loop i in 0..4: arr[i] = 0   ; placeholders, cmp x1,#5 (x1 is the plain index)
0x7fdf70  arr[0] = #0x14a              ; 0xA5  header
0x7fdf78  arr[1] = #0xa                ; 0x05  total length (5)
0x7fdf80  arr[2] = #0x1f8              ; 0xFC  opcode      <-- unconditional
0x7fdf90  arr[3] = (dpi & 0xF) <<1     ; tagged Smi of (dpi & 0x0F), the 4-bit selector
0x7fdfa0  call ::getCheckSum(arr)      ; arr[4] = sum & 0xFF
0x7fe028  call ::writeDevice(arr)
```

* **No** device comparison (`curDevice` is never loaded).
* **No** version comparison, **no** `#0x1ec` store. `rg -n 'mov +[xw][0-9]+, #0x1ec\b' 2.23/asm/moojiang/`
  → **0 hits**. So 2.23 has no F6 path at all. VERDICT: **FC only, no gate** (PROVEN STATIC).

## 2. 2.24 — FC default + F6 branch (PROVEN STATIC) — the exact condition

`writeDpiConfig` @ **0x894000** (`units/gamepadset.dart`, lines 9727-9885):

```
0x894050  AllocateArray(#0xa)          ; Smi(5) -> 5-element array
0x89406c  loop i in 0..4: arr[i] = 0
0x894088  arr[0] = #0x14a              ; 0xA5
0x894090  arr[1] = #0xa                ; 0x05
0x894098  arr[2] = #0x1f8              ; 0xFC  <-- DEFAULT opcode (always written first)
0x8940a0  r0 = InitLateStaticField(0xfa8)  ; ::curDevice  (define.dart)
0x8940c0  cmp  w0, Obj!Device@9ef941   ; devRainbow2Pro (off_8 = 0x3)
0x8940cc  b.eq  0x8940e0
0x8940d0  cmp  w0, Obj!Device@9ef981   ; devC2SL       (off_8 = 0x5)
0x8940dc  b.ne  0x894114               ; not one of the two -> keep FC
0x8940e0  r0 = LoadStaticField(0x102c) ; zkmVersion (set from the 0B reply)
0x8940e8  r1 = LoadInt32Instr(r0)      ; sbfx x1,x0,#1,#0x1f  -> UNTAG to plain int
0x8940ec  tbz  w0, #0, 0x8940f4        ; (Smi fast path)
0x8940f0  ldur x1, [x0, #7]            ; (Mint path)
0x8940f4  cmp  x1, #0x35               ; compare PLAIN int to 53
0x8940f8  b.lt 0x89410c                 ; if version <  0x35 -> skip, KEEP FC
0x8940fc  ldur x1, [fp, #-0x28]         ; else load the frame array
0x894100  arr[2] = #0x1ec               ; 0xF6  <-- OVERWRITE the opcode slot
0x894108  b    0x894118
0x89410c  ; (FC retained)
0x894114  ; (FC retained)
0x894118  arr[3] = (dpi & 0xF) <<1
0x894134  call ::getCheckSum(arr)
0x894190  ClosureCall -> writeDevice(arr)
```

**Literal pseudocode of the condition:**

```dart
var frame = [0xA5, 0x05, 0xFC, dpi & 0x0F, 0];        // opcode 0xFC by default
if (curDevice == Device.devRainbow2Pro ||            // off_8 == 0x3
    curDevice == Device.devC2SL) {                   // off_8 == 0x5
  if (zkmVersion >= 0x35) {                          // 53 ; note: >=, see below
    frame[2] = 0xF6;                                 // legacy opcode substitutes FC
  }
}
```

* **Comparison operator:** `cmp x1, #0x35 ; b.lt <skip>` → the F6 store executes when the branch is
  **not** taken, i.e. **version ≥ 0x35**. The fallback direction is therefore: version `< 0x35`
  ⇒ keep **FC**; version `≥ 0x35` ⇒ use **F6**. The earlier phrasing "fw < 0x35 → F6" is
  **CONTRADICTED** by the branch sense at `0x8940f8`.
* **Threshold value and the Smi trap:** the operand `x1` is produced by `LoadInt32Instr` /
  `sbfx x1, x0, #1, #0x1f` (`0x8940e8`) — an explicit **untag** — so the `cmp` immediate is the
  **plain** value `0x35` = 53, *not* half of it. If the compare had been done in tagged space the
  same constant would have appeared as `#0x6a` (= 2·53). Both encode 53; the literal in this build
  is `#0x35`. **The "halve the immediate" rule applies to Smis stored into frame arrays, not to
  compares against an untagged (`LoadInt32Instr`) operand.** This is rule **N3** of the sibling
  `results/reconciliation/dart-smi-methodology.md` ("a `cmp` on a register just produced by
  `LoadInt32Instr` (`sbfx xN,xM,#1,#0x1f`) is against the raw value") — independently derived, same
  conclusion. Two additional anchors agree:
  (a) the `sbfx`/`tbz`/`ldur` untag sequence immediately precedes the `cmp`; (b) the identical
  pattern and constant occur in 4.0.8 at `0x946844` (§3).
* **Device list that enters the branch:** exactly two — `Obj!Device@9ef941` = `devRainbow2Pro`
  (`off_8 = 0x3`) and `Obj!Device@9ef981` = `devC2SL` (`off_8 = 0x5`). Resolved from
  `/home/salamanka/armorx/re/v224/blutter_out/objs.txt` lines 21588 and 21602. (Note: the *addresses*
  in `objs.txt` are not ordered by id — id 3 sits at a higher address than id 4-5-6 — so only `off_8`
  is authoritative; the manifest's `{devRainbow2Pro(3), devC2SL(5)}` is **confirmed**.)
* **Version source:** static **0x102c**, written by `StoreStaticField(0x102c, r0)` @`rainbow_root.dart:0x8969e4`
  inside the `0B`-reply handler, right next to the literal `"zkm="` (`rainbow_root.dart:0x8969f8`).
  The same static is later read as the "derived config length" at other sites — `0xfd4`(2.22)→`0x102c`(2.24)
  →`0xb6c`(4.0.8) is **one field carrying the device's `zkmVersion`**, which other code also uses to
  derive config length. (Documentation that calls this slot only "config length" is incomplete; see
  the reconciliation blocks.)
* **Payload / framing unchanged by the switch:** only array slot 2 (the opcode) is overwritten; the
  length byte stays `0x05`. Zero-selector frames are therefore `A5 05 FC 00 7C` (FC) and
  `A5 05 F6 00 A0` (F6) — checksums recomputed: `(A5+05+FC+00)&FF = 0x7C`, `(A5+05+F6+00)&FF = 0xA0`.

### 2.24 query path (context)

`getDpi` @ **0x91b090** (`widgets/rainbow/rainbow_more.dart`) builds the read frame the same way
(`#0x14a`/`#0xa`/`#0x1f8`/`#0x100`→selector `0x80`) and gates an F6 variant at `0x91b160`/`0x91b18c`
with `cmp x2, #0x36` (≥ 0x36) and at `0x91b1fc`/`0x91b228` with `cmp x2, #0x36`. Not a write path;
recorded for completeness.

## 3. 4.0.8 — four-device gate, same threshold, plus AB motion DPI (PROVEN STATIC)

`writeDpiConfig` @ **0x946750** (`units/gamepadset.dart`, lines 11042-11171):

```
0x9467b8  arr[0] = #0x14a     ; 0xA5
0x9467c0  arr[1] = #0xa       ; 0x05
0x9467c8  arr[2] = #0x1f8     ; 0xFC  <-- default
0x9467f0  cmp w0, Obj!Device@b2ee81  ; devRainbow2Pro (0x3)
0x946800  cmp w0, Obj!Device@b2edc1  ; devRainbow3   (0x4)
0x946810  cmp w0, Obj!Device@b2ede1  ; devGale2      (0xb)
0x946820  cmp w0, Obj!Device@b2eee1  ; devC2SL       (0x7)
0x94682c  b.ne 0x946864              ; none of the four -> keep FC
0x946830  r0 = LoadStaticField(0xb6c)  ; zkmVersion
0x946838  r1 = LoadInt32Instr(r0)      ; sbfx -> untag
0x946844  cmp x1, #0x35
0x946848  b.lt 0x94685c                 ; version < 0x35 -> keep FC
0x946850  arr[2] = #0x1ec               ; 0xF6
```

Device ids resolved from `/home/salamanka/armorx-re/mygt408/blutter_out/objs.txt`
(b2ee81=devRainbow2Pro/0x3, b2edc1=devRainbow3/0x4, b2ede1=devGale2/0xb, b2eee1=devC2SL/0x7).
Note `devC2SL`'s id moved **5 (2.24) → 7 (4.0.8)**; the gate is by object identity, not id.

Motion DPI (`AB` family, new in 4.0.8): `writeMotionDpiConfig` @ **0x946158** →
`[#0x156, #0xe, #0xa, #0x4a, lo, hi, cks]` = `AB 07 05 25 <u16 LE> <cks>`; readers `getMotionList`
@0xace94c, `getMotionDpi` @0xacea60; response filter `cmp w0, #0x156` @`rainbow_more.dart:0x8b482c`.

## 4. Evolution summary (corrected)

1. **2.22.0901 — no DPI at all** (PROVEN STATIC). `FC`, `F6`, `AB` all absent.
2. **2.23.0609 — FC introduced, single unbranched opcode** (PROVEN STATIC; corrects the
   *(historical)* "no F6 branch" phrasing to a positive result: `writeDpiConfig` is unconditional FC).
3. **2.24.0919 — legacy F6 path added** for `{devRainbow2Pro, devC2SL}` when `zkmVersion >= 0x35`
   (PROVEN STATIC; **direction settled: ≥, not <**).
4. **4.0.8 — gate widened to four devices** (`+devRainbow3, +devGale2`) with the **same** `>= 0x35`
   threshold on static `0xb6c`, plus the separate `AB 07 05 25` 16-bit-LE motion-DPI write (PROVEN STATIC).

## 5. Still open (unchanged)

* The selector→real-DPI value mapping (payload is a 4-bit selector; values are app/server presets).
* The DPI **reply parser / notification handler** — not located in any build.
* Whether the `F6` opcode is honoured by older firmware (< 0x35) is *by construction* unknown
  statically; the app avoids sending it below 0x35.
