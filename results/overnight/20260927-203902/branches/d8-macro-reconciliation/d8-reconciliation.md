# D8 / MACRO reconciliation across 2.22.0901 · 2.23 · 2.24 · 4.0.8

Branch: `results/overnight/20260927-203902/branches/d8-macro-reconciliation/`
Date: 2026-09-27 · **STATIC ONLY** — no hardware, no radio, no APK execution, no emulator.
All trees were read only; nothing was written outside this output directory.

Grade keys: **PROVEN STATIC** · **STRONG EVIDENCE** · **INFERRED** · **UNKNOWN** · **CONTRADICTED**

Trees read (absolute paths; the `static/blutter/2.23|2.24|4.0.8` directories are **empty stubs** —
the real trees live elsewhere, so all claims below cite the real path):

| ver | Dart | asm root |
|---|---|---|
| 2.22.0901 | 2.17.5 | `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang` |
| 2.23.0609 | 2.19.6 | `/home/salamanka/armorx/re/blutter_out/asm/moojiang` |
| 2.24.0919 | 3.2.3  | `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang` |
| 4.0.8     | 3.12.2 | `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang` |

Deliverables in this directory: `d8-reconciliation.md` · `d8-reconciliation.json` · `macro-path.md` ·
`vectors/d8-vectors.json` (25 vectors) · `gen_vectors.py` (deterministic generator).

---

## 1. Requirement (1) — the A4 fragment layout, verified arithmetically

### 1.1 The rule (re-verified, not assumed)

```
data fragment : A4 | (payload+5) | D8 | (i+1) | payload | csum     total = payload+5 bytes
commit frame  : A4 |     05      | D8 | (nfrags+1)  | csum          total = 5 bytes
```

* byte 0 = `0xA4`
* **byte 1 = the TOTAL frame length** (never "0x0A for a commit")
* byte 2 = opcode (`0xD8`)
* byte 3 = ordinal (`i+1`; for the commit frame, `nfrags+1`)
* then payload, then `csum = sum(all preceding bytes) & 0xFF`

Because byte 3 exists, `len = payload + 5` closes (3 header + 1 ordinal + payload + 1 checksum).
That is why the older `payload + 4` arithmetic was wrong.

### 1.2 Arithmetic on concrete frames from the corpus — 10 real frames

Source (live BLE capture, byte-exact, transcribed by the capture harness, not by hand):
`/home/salamanka/armorx-lab/results/experiments/physical-20260927-165347/baseline-fragments.jsonl`
(also mirrored in `results/overnight/20260927-203902/fixtures/official-fixtures.json` and
`.../official-timeline-canonical.json`). Recomputed with `gen_vectors.py` (kind `framing_anchor`):

| # | raw hex (20 or 14 bytes) | byte1 | actual len | byte1==len | payload | byte1==payload+5 | ordinal (byte3) | csum calc==stored |
|---|---|---|---|---|---|---|---|---|
| 1 | `a414d6012c40009033ff000000000000000000bd` | 0x14=20 | 20 | ✔ | 15 | ✔ | 1 | ✔ (0xBD) |
| 2 | `a414d602000000000001001e1e4646000001005a` | 0x14=20 | 20 | ✔ | 15 | ✔ | 2 | ✔ (0x5A) |
| 3 | `a414d6031e1e464600000200020200000000005f` | 0x14=20 | 20 | ✔ | 15 | ✔ | 3 | ✔ (0x5F) |
| 4 | `a414d6040a3c3c2a000000000a3c3c2a000000ea` | 0x14=20 | 20 | ✔ | 15 | ✔ | 4 | ✔ (0xEA) |
| 5 | `a414d605000a3c3c2a000000000000000000003f` | 0x14=20 | 20 | ✔ | 15 | ✔ | 5 | ✔ (0x3F) |
| 6 | `a414d60600000000000000000000000000000094` | 0x14=20 | 20 | ✔ | 15 | ✔ | 6 | ✔ (0x94) |
| 7 | `a414d60700000000000000000000000000000095` | 0x14=20 | 20 | ✔ | 15 | ✔ | 7 | ✔ (0x95) |
| 8 | `a414d6080000000000010203040506070...b2` | 0x14=20 | 20 | ✔ | 15 | ✔ | 8 | ✔ (0xB2) |
| 9 | `a414d60908090a0b0c0d0e0f1011121314151678` | 0x14=20 | 20 | ✔ | 15 | ✔ | 9 | ✔ (0x78) |
| 10 | `a40ed60a010d191a1b1c1d1e1f64` | 0x0E=14 | 14 | ✔ | 9 | ✔ | 10 (0x0A) | ✔ (0x64) |

All 10 satisfy **byte1 == total length == payload+5** and the checksum, and the payloads concatenate
to exactly **9×15 + 9 = 144 bytes** (the ARMOR-X Pro config image). These are `D6` frames, but the
A4 framing they demonstrate is the same framing the D8 writer emits (`A4 | len | opcode | ordinal | …`);
the opcode differs, the arithmetic does not. **PROVEN STATIC + anchored live.**

Note the genuine `0x0A` in frame 10: it is the **ordinal of the 10th fragment**, in the byte-3
position — not a length byte. This is the likely second source of the historical `0x0A` confusion.

### 1.3 The commit frame arithmetic

`csum = (Σ all preceding bytes) & 0xFF`:

| nfrags | frame | sum | & 0xFF |
|---|---|---|---|
| 1 | `A4 05 D8 02 83` | 0xA4+0x05+0xD8+0x02 = 0x183 | 0x83 |
| 2 | `A4 05 D8 03 84` | 0xA4+0x05+0xD8+0x03 = 0x184 | 0x84 |
| 3 | `A4 05 D8 04 85` | 0xA4+0x05+0xD8+0x04 = 0x185 | 0x85 |

`0x05` is not a magic byte: it is the ordinary `payload+5` formula evaluated at `payload = 0`
(the commit carries an empty segment). 2.22 emits it as a **computed** value
(`0x79eb7c: mov x17, #0xa` after an `add …, #5`); 2.24/4.0.8 emit the **constant-folded** literal
(`0x80012c` / `0x85aba8: mov x16, #0xa`). Same byte, same source expression.

### 1.4 Why `A4 0A D8 …` cannot be the commit — the arithmetic that kills it

`0x0A` is not a *literal wire byte* anywhere; every `mov xN, #0xa` on this path is a **tagged Smi**.
Independent proof from the sibling immediates in the *same* `List<int>` in 4.0.8
(`units/gamepadset.dart`, the commit block):

```
6989: // 0x85a748: r16 = 328
6990: //     0x85a748: mov             x16, #0x148      ; 328 = 2 x 0xA4  -> Dart int 164
7135: // 0x85a8f8: r16 = 432
7137: //     0x85a8f8: mov             x16, #0x1b0      ; 432 = 2 x 0xD8  -> Dart int 216
7376: // 0x85aba8: r16 = 10
7377: //     0x85aba8: mov             x16, #0xa        ;  10 = 2 x 0x05  -> Dart int 5
7378: // 0x85abac: StoreField: r4->field_f = r16
7379: //     0x85abac: stur            w16, [x4, #0xf]   ; tagged store into the same List<int>
7406: // 0x85abf8: add             x5, x2, #1           ; nfrags+1
7429: // 0x85ac3c: r0 = BoxInt64Instr(r4)               ; the count byte
```

`0x148` and `0x1b0` are exactly `2 ×` the bytes they store (`0xA4`, `0xD8`), so this list holds
tagged Smis and `0xa` stores Dart **5** → wire byte **`0x05`**. The same situation holds at 2.24
`0x80012c: mov x17, #0xa` (sibling `0x800060 #0x148`, `0x800188 #0x1b0`) and at 2.22
`0x79eb7c: mov x17, #0xa`. **PROVEN STATIC in all four builds.**

The arithmetic consequence:

* A commit frame is **5 bytes total**. Therefore its byte 1 must be `0x05`.
* `A4 0A D8 03 89` declares byte1 = 10, i.e. a **10-byte** frame → under the proven layout that is a
  *data fragment carrying 5 payload bytes*, whose ordinal would then be `0x03`. It is internally
  contradictory as a commit and cannot be produced by any of the four writers.
* Corollary, and the source of the old confusion: `A4 0A …` **is** legal for a *data* fragment whose
  payload happens to be 5 bytes (e.g. a 20-byte payload's second fragment is `A4 0A D8 02 <5 B> <ck>`,
  10 bytes, byte1 = 0x0A = 10 = 5+5). `A4 0A` is not forbidden — it is just never the **commit**.
  The concrete counter-example vector is `REJECT-a40ad8-commit` in `vectors/d8-vectors.json`.

Full-body sweeps corroborate: the 4.0.8 `writeMacroConfig` body contains `#0xa` at `0x85aba8` only
inside the commit block (plus *unboxed* uses: `0x85cf5c mul #0xa` in `applicationFrameMacro` and loop
arithmetic); 2.22's body has exactly one (`0x79eb7c`); 2.24's has `0x80012c` in the commit block.
**No literal `0x0A` wire byte exists in any fragmentation body.**

> Status of the earlier correction: **CONFIRMED**. `baselines/imported-research/d8-test-vectors.json`
> still carries `"A4 0A D8 03 89"` (commit) and 19-byte fragments, and is **wrong on both counts**.
> `automation/scripts/armorx_lab/frames.py::build_d8_terminator()` has since been fixed in-tree and
> now emits `bytes([FRAG_HEADER, 0x05, 0xD8, nfrags+1])` — the stale claim that the toolkit still
> encodes `A4 0A` is **CONTRADICTED by the current file**.

Second, independent kill of the imported vectors: the imported fragment
`A4 14 D8 97 58 00 1E 00 17 17 00 00 00 E0 03 00 00 00 AE` is **19 bytes** long while declaring
byte1 = `0x14` = 20. It omits the ordinal byte (so byte 3 = `0x97` is really the payload's first byte,
and `len != total`). Inserting the ordinal `0x01` yields a self-consistent 20-byte frame
(`A4 14 D8 01 97 …`). Vector `REJECT-imported-19byte-ordinal-less`.

### 1.5 The `0x0A` question per version

| ver | literal `0x0A` wire byte in the fragmentation body? | label |
|---|---|---|
| 2.22.0901 | NO — the single `#0xa` (`0x79eb7c`) is Dart 5 | PROVEN STATIC |
| 2.23.0609 | NO — the single `#0xa` (`0x798744`) is Dart 5 | PROVEN STATIC |
| 2.24.0919 | NO — `0x80012c` is Dart 5; other `#0xa` sites are outside the fragment/commit builders | PROVEN STATIC |
| 4.0.8 | NO — `0x85aba8` is Dart 5 | PROVEN STATIC |

---

## 2. Requirement (2) — OLD model vs MODERN model: which the code supports

### 2.1 What the two models actually are

| | OLD | MODERN |
|---|---|---|
| step record class | `GamepadDefMap` | `TranscribeFrame` |
| record size | **7 B** `[type=0x80][time u16 BE][key u32 BE]` | **10 B** `[(t8&0xF)<<4][(t8>>4)&0xFF][key u32 BE][stick u32 BE]` |
| payload length | `N = 10 + 7n` | `N = 10 + 10n` |
| header byte 4 | `GamepadAtt.type` (settable) | constant `0x00` |
| serializer | `changeGamepadDef` | `TranscribeFrame.toFrameCmd` via `applicationFrameMacro` |
| chunk | literal **15** | `subpackageLength() - 5` ∈ {15,43,67} |

The two classes are **not** mutually exclusive per build — `GamepadDefMap` field names survive in
**all four** `pp.txt` (3 hits each), and `TranscribeFrame` exists in 2.24/4.0.8 only (7 hits each).

### 2.2 The dispatch — this is the key result, and it changes the picture

`applicationMacro` (the generic macro entry point) is a **dispatcher on `macrosItemLen()`**:

4.0.8 `units/gamepadset.dart` lines 5058-5092:

```
5058: // 0x858f78: r0 = macrosItemLen()    bl #0x859014  ; [package:moojiang/define.dart] ::macrosItemLen
5060: // 0x858f7c: cmp             x0, #0xa
5061: // 0x858f80: b.ne            #0x858fa8          ; != 10 -> synchronized(closure 0x859144)
5072: // 0x858f9c: r0 = applicationFrameMacro()  bl #0x85c908   ; == 10 -> MODERN
5091: // 0x858fd0: r1 = Function '<anonymous closure>': static (0x859144), in ... ::applicationMacro
```

and the `!= 10` closure builds the **OLD** class (within closure `0x859144`, lines 5205-5210):

```
5205: // 0x859228: r0 = GamepadDefMap()
5206: //     0x859228: bl #0x85c8fc  ; AllocateGamepadDefMapStub -> GamepadDefMap (size=0x14)
5209: // 0x859238: r0 = GamepadDefMap()
5210: //     0x859238: bl #0x85c80c  ; [package:moojiang/units/gamepadset.dart] GamepadDefMap::GamepadDefMap
```

then calls `changeGamepadDef()` (line 6819, `0x85a580`) and `writeMacroConfig()` (line 6834).
2.24 has the identical structure (`applicationMacro` line 212 `macrosItemLen` / 214 `cmp x0,#0xa` /
231 `applicationFrameMacro`; `!=10` closure line 367 → `changeGamepadDef` 4651 + `writeMacroConfig` 4669).

**PROVEN STATIC:**
* `macrosItemLen() == 10` → `applicationFrameMacro` (MODERN, 10-byte `TranscribeFrame`).
* `macrosItemLen() != 10` → `changeGamepadDef` (OLD, 7-byte `GamepadDefMap`).

### 2.3 `macrosItemLen()` is device-firmware dependent — and devArmorX never returns 10

`define.dart` 4.0.8 lines 1087-1196 (`0x859014`), decoded:

```
0x859084: curDevice
0x85908c: r16 = Obj!Device@b2eec1                 ; == Device.devArmorX  (off_10:"devArmorX")
0x859098: b.ne #0x8590f4                          ; not the ArmorX -> generic branch
  ; --- devArmorX branch ---
  ... int.parse(substring(..., len-2)) -> x0
  0x8590cc: cmp x0, #0x28      (40)
  0x8590d4: mov x0, #7         ; fw <  40  -> 7
  0x8590e4: mov x0, #6         ; fw >= 40  -> 6
0x8590f4: ; --- generic branch ---
  v = <static 0xb6c>
  0x859108: cmp x2, #0x35      (53) ; >=53 -> 10
  0x859118: cmp x2, #0x31      (49) ; >=49 -> 6    else -> 7
```

**devArmorX returns 6 or 7 — never 10.** (Both return sites are `mov x0,#7` / `mov x0,#6`; no `#0xa`
appears in the ArmorX branch.) The enum value is confirmed independently:
`objs.txt` → `Obj!Device@b2eec1 { off_8: int(0xa), off_10: "devArmorX" }` (4.0.8) and
`off_8: int(0x8)` (2.24).

Corroborating UI evidence (which page the ArmorX uses):
* `widgets/general/config_macros.dart` contains **1** reference to the devArmorX enum object and
  special-cases `curDevice == devArmorX && macrosItemLen() == 7` (line 2855, `0x997d90`).
* `widgets/general/frame_config_macros.dart` — the page that calls `applicationFrameMacro()`
  **directly**, bypassing the gate (line 5254, `0x9ad0c0`) — contains **0** references to devArmorX.

### 2.4 Verdict

Neither model "wins" globally, and the OLD model must **not** be deleted:

| ver | OLD `GamepadDefMap` (7B) | MODERN `TranscribeFrame` (10B) | verdict for the ARMOR-X Pro |
|---|---|---|---|
| 2.22.0901 | **only path** | absent | OLD |
| 2.23.0609 | **only serializer** | absent (but `macrosItemLen()` already exists, 19 hits) | OLD |
| 2.24.0919 | reachable (`macrosItemLen()!=10`) | reachable (`==10`) | **OLD** (`macrosItemLen()`=6/7) |
| 4.0.8 | reachable (`macrosItemLen()!=10`) | reachable (`==10`) | **OLD** (`macrosItemLen()`=6/7) |

* **Which model the code supports:** both, in 2.24/4.0.8, selected at runtime by `macrosItemLen()`;
  only OLD in 2.22/2.23. **STRONG EVIDENCE** (static branch + return-value analysis + UI-page
  attribution; no live confirmation, which is out of scope tonight).
* **The "MODERN 10-byte `TranscribeFrame` = the 4.0.8 ARMOR-X Pro D8 format" claim is
  CONTRADICTED for the ARMOR-X Pro.** `applicationFrameMacro` is the 10-byte serializer for devices
  whose `macrosItemLen() == 10`; the ArmorX never selects it.
* **Annotated, not deleted.** The OLD model is retained and is the *active* ARMOR-X Pro model in all
  four builds. `tests/test_d8_versions.py` currently asserts a per-build family mapping
  ("2.22/2.23 → OLD, 2.24/4.0.8 → MODERN"); that framing is **over-simplified** and should be
  re-expressed as a `macrosItemLen()` dispatch — the test's *framing* invariants (§1) remain correct
  and are unchanged.

> **Caveat I will not paper over:** this is a static reading. The single missing observation is one
> live 4.0.8 macro apply with a byte-count between the `A4` and the following `D8`. Until then the
> ArmorX-uses-OLD conclusion is STRONG EVIDENCE, not PROVEN.

---

## 3. Requirement (3) — the chunk-class selector (15 vs 43 vs 67)

**The selector is statically determinable.** It is `subpackageLength()`, a switch on
`curDevice.field_7` (the device enum value), minus the 5-byte A4 overhead.

`define.dart` `subpackageLength()` bodies (both read line-by-line, independently decoded here):

| tree | fn | return values (raw imm) | 
|---|---|---|
| 4.0.8 | `0x819190` (`define.dart:316`) | `#0x14`=20 @`0x819238`, `#0x48`=72 @`0x819264`, `#0x30`=48 @`0x819274` |
| 2.24 | `0x7b9064` (`define.dart:477`) | `#0x48`=72 @`0x7b90ec`, `#0x14`=20 @`0x7b9124`, `#0x30`=48 @`0x7b9134` |

Consumption, 4.0.8 `writeMacroConfig`:

```
6961: // 0x85a6f0: r0 = subpackageLength()   bl #0x819190
6963: // 0x85a6f4: sub x1, x0, #5            ; the -5 overhead, untagged immediate
6968: // 0x85a704: scvtf d1, x1             ; used DIRECTLY as a float divisor (no unboxing)
6979: // 0x85a72c: r0 = subpackageLength()   bl #0x819190
6980: // 0x85a730: sub x3, x0, #5
```

**The `-5` is untagged arithmetic:** the immediate is `#5`, not `#0xa`; and the numerator *is*
unboxed explicitly (`0x818940 sbfx x16, x0, #1, …` for a field) while `x0 = subpackageLength()` is
fed straight into `scvtf d1, x19` with **no** `sbfx`/`asr #1`. So `subpackageLength()` returns the
untagged values 20/48/72 and `chunk = subpackageLength() - 5` ∈ **{15, 43, 67}**. **PROVEN STATIC.**

Independent anchor: the 10 live fragments in §1.2 are all `A4 14 D6 <ord> <15 B>` → a 20-byte frame
/ 15-byte payload, i.e. `subpackageLength() == 20`. A tagged-Smi reading (20 → Dart 10, chunk 5)
would have produced `A4 0F` frames and could not reconstruct a 144-byte image from 9×15+9.

**Branch decode (this pass re-derived it; the prior reconciliation's mapping was partly wrong):**

`subpackageLength()` by `curDevice.field_7`:

| id | 4.0.8 | 2.24 |
|---|---|---|
| 0 | 48 | 48 |
| 1,2,3 | 20 | 20 |
| 4 | 72 | 48 |
| 5 | 48 | 72 |
| 6 | 48 | 48 |
| 7 | **72** | 20 |
| 8 | 48 | **20** |
| 9 | 20 | 48 |
| 10 | **20** | 48 |
| 11 | 72 | 48 |
| ≥12 | 48 | 48 |

> **Correction to `results/reconciliation/d8-taxonomy.{md,json}`**: the prior doc claimed
> "4.0.8: id 1,2,3 and 7..10 → 20; id 4..7 → 72". The independent decode above gives id 7 → **72**
> (not 20) and id 8 → **48** (not 20). This does **not** change the ARMOR-X Pro answer (see below),
> but it changes the mapping for those device ids. Grade: PROVEN STATIC (body re-read), correcting a
> prior INFERRED mapping.

**Resolution for the ARMOR-X Pro — all four builds → chunk 15:**

| ver | devArmorX enum id | subpackageLength(id) | chunk |
|---|---|---|---|
| 2.22.0901 | (no enum path) | n/a — literal 15 | **15** |
| 2.23.0609 | (no enum path) | n/a — literal 15 | **15** |
| 2.24.0919 | `0x8` = 8 (`objs.txt`) | 20 | **15** |
| 4.0.8 | `0xa` = 10 (`objs.txt`) | 20 | **15** |

So the ARMOR-X Pro is the `subpackageLength() == 20` / 15-byte-payload class in every build, matching
the live 20-byte frames. **PROVEN STATIC + anchored live.** MTU is not an input: 43 and 67 exist for
*other* device codes, so MTU could never have chosen among 15/43/67 (no MTU term exists on this path).

Nothing is missing for the ARMOR-X Pro. What remains **UNKNOWN** is only the reverse mapping
(which *other* device ids need 43/67 in a human-readable product name).

---

## 4. Requirement (4) — the full macro path (summary)

Full trace with addresses: **`macro-path.md`**. Headline:

```
[UI] config_macros.dart / armorx_pro_* / frame_config_macros.dart
  -> applicationMacro()                              (gamepadset.dart)
       macrosItemLen()==10 ? applicationFrameMacro()  (MODERN 10B)
                           : changeGamepadDef()       (OLD 7B)  [+ synchronized(_lock)]
  -> payload = CRC16 | len | hdr(byte4..byte9) | records
  -> writeMacroConfig():
        chunk  = subpackageLength() - 5
        nfrags = ceil(payloadLen / chunk)
        for i in 0..nfrags-1:  A4 | (segLen+5) | D8 | i+1 | seg | sum8
        commit:                A4 | 05        | D8 | nfrags+1 | sum8
  -> writeDevice()  (BLE write to FFE1)
[device -> app] notification closure
  2.24/4.0.8: list[2] tested vs 0xFC / 0xD8 (prints "写入结果") / 0xD3
              -> parsingData() -> TranscribeFrame.fromConfigData() -> changeTranscribeFrameToDefMacro()
  2.22/2.23 : generic A4/D6 reassembler only; NO 0xD8 comparison -> no D8 macro readback
storage slots: server-side JSON CRUD (MacroRow.fromJson / addMacroResponse / changeMacro*Response);
              no device-side macro slot arithmetic exists in any build (contradicts the old
              "onboard config bank" reading)
```

Vectors: **`vectors/d8-vectors.json` — 25 vectors** (10 live framing anchors, 4 derived encode,
3 chunk-class, 6 commit, 2 rejected), format described in that file's `format_description` block.
Regenerate deterministically with `python3 gen_vectors.py` (it self-verifies every invariant).

---

## 5. Corrections issued by this pass

| # | corrected claim | new evidence | grade |
|---|---|---|---|
| 1 | "MODERN 10-byte `TranscribeFrame` is the 4.0.8 ARMOR-X Pro D8 format" | `applicationMacro` dispatches on `macrosItemLen()==10`; devArmorX returns 6/7; ArmorX UI = `config_macros.dart` (frame page never references devArmorX) | CONTRADICTED for the ArmorX / STRONG EVIDENCE |
| 2 | prior `subpackageLength()` device-id mapping (id 7→20, id 8→20) | re-decoded branch bodies: 4.0.8 id 7→72, id 8→48 | PROVEN STATIC correction |
| 3 | "toolkit still encodes `A4 0A D8`" | `automation/scripts/armorx_lab/frames.py::build_d8_terminator` now emits `0x05` | CONTRADICTED (already fixed) |
| 4 | `tests/test_d8_versions.py` models families as per-build | it is a `macrosItemLen()` dispatch; framing invariants unaffected | over-simplified |
| 5 | commit byte `0x05` not `0x0A`; ordinal present in all builds; `A4 14`/`A4 0E` frames | §1, re-verified on 10 live frames + asm | CONFIRMED (prior pass) |

## 6. Open items (honest gaps)

1. No live 4.0.8 macro apply was captured → §2.4 is STRONG EVIDENCE, not PROVEN.
2. `repeatTime` unit: UNKNOWN in all four (no scaling constant on the wire path).
3. Meaning of `field_23` (`maxSteps`) and the u16 read at readback bytes 15-16: offsets proven,
   semantics PARTIAL.
4. 2.23's per-fragment ordinal value `i+1` remains STRONG EVIDENCE (not fully traced).
5. `macrosItemLen()`'s devArmorX branch reads a 2-char substring of a static string and compares it
   to 40; the string's identity was not resolved (the *return values* 6/7 are unambiguous).
