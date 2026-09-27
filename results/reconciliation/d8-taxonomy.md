# D8 macro taxonomy — definitive per-version reconciliation (Parts C4–C6)

Date: 2026-09-27 · Author: protocol-archaeology subagent (Parts C4–C6)
Trees read (never modified, APK never run/re-signed):

| ver | Dart | asm root |
|---|---|---|
| 2.22.0901 | 2.17.5 | `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out` |
| 2.23.0609 | 2.19.6 | `/home/salamanka/armorx/re/blutter_out` |
| 2.24.0919 | 3.2.3  | `/home/salamanka/armorx/re/v224/blutter_out` |
| 4.0.8     | 3.12.2 | `/home/salamanka/armorx-re/mygt408/blutter_out` |

Labels: **PROVEN STATIC** · **STRONG EVIDENCE** · **INFERRED** · **UNKNOWN** · **CONTRADICTED**.
Every numeric claim below has an instruction citation. Smi rule applied throughout: an immediate
`#imm` used as a **Dart-level int stored/passed as a value** is tagged, so the Dart value is
`imm/2`; an immediate used in **unboxed arithmetic** (`mul`, `cmp`, `sub`, `scvtf` operand) is the
true value. Odd immediates cannot be tagged Smis at all. Two independent anchors were required for
every load-bearing number.

---

## 0. Headline (definitive)

1. **The A4 fragmentation framing is IDENTICAL in all four versions** — this was not previously
   stated and partly contradicts the imported 4.0.8 note:

   ```
   data fragment : A4 | (segLen+5) | D8 | (i+1) | seg | csum      total = segLen+5 bytes
   commit frame  : A4 | 05        | D8 | (nfrags+1) | csum         total = 5 bytes
   ```

   The **fragment ordinal byte at frame offset 3 exists in every version** (old *and* modern). The
   imported doc's "data fragments carry no index/ordinal byte" is **CONTRADICTED**.
   The `len` byte always equals the total frame length.

2. **The commit/terminator length byte is `0x05`, never `0x0A`, in every version.**
   The historical "4.0.8 commit byte 0x0A" is the **tagged-Smi misread** of `mov x16, #0xa`
   (Dart value 5). See §4.

3. **Old format (2.22, 2.23) vs modern format (2.24, 4.0.8)** differ ONLY inside the D8 payload
   (and in how the chunk is chosen). Both the chunking framing and the commit frame are the same:

   | | 2.22 | 2.23 | 2.24 | 4.0.8 |
   |---|---|---|---|---|
   | D8 payload step record | **7 B** `[0x80][time16 BE][key32 BE]` | **7 B** (same) | **10 B** `TranscribeFrame` | **10 B** (same) |
   | payload length N | `10 + 7n` | `10 + 7n` | `10 + 10n` | `10 + 10n` |
   | chunk source | literal **15** | literal **15** | `subpackageLength()-5` | `subpackageLength()-5` |
   | `subpackageLength()` | absent | absent | `{20,72,48}` | `{20,72,48}` |
   | `TranscribeFrame` / `applicationFrameMacro` | absent | absent | present | present |

4. **0x0A does not appear as a byte anywhere in any D8 fragmentation body** (proven by full-body
   immediate sweeps in all four trees). The only genuine on-wire `0x0A` found is the **ordinal of
   the 10th fragment of a 144-byte D6 config readback** (`A4 0E D6 0A …`, live anchor) — a
   different field, direction and opcode family.

---

## 1. Per-version payload field layout

### 1.1 2.22.0901 — OLD format (PROVEN STATIC)

Built by `applicationMacro` (0x7a559c, body closure 0x7a56c4, `units/gamepadset.dart`), serialized
by `changeGamepadDef` (0x79c894), fragmented by `writeMacroConfig` (0x79dfc8, body 0x79e158).

- Buffer size `N = 7n + 10`: `0x7a6234 mov x16,#7` → `0x7a6238 mul x0,x1,x16` →
  `0x7a623c add x1,x0,#0xa` (`#7` and `#0xa` are unboxed operands → 7 and 10).
- Header (10 B), byte offsets from the payload start:

  | off | width | field | asm evidence |
  |---|---|---|---|
  | 0–1 | 2 | CRC-16/MODBUS (init 0xFFFF, poly 0xA001) over bytes [2:], **BE** | `0x79cf10 r6=65535`, `0x79cf84 r16=40961`, `0x79d008/0x79d028` stores |
  | 2–3 | 2 | length = N, **BE** | `0x79c960 asr x9,x0,#8`, `0x79c994` |
  | 4 | 1 | `GamepadAtt.type` | `0x79d078 LoadField <GamepadAtt.type>` |
  | 5 | 1 | `GamepadAtt.setting` = runKey | `0x79d088` |
  | 6 | 1 | `GamepadAtt.key`, 0→5 substitution | `0x79d098`, `0x79ca70 r9=5` |
  | 7 | 1 | `GamepadAtt.att` = isRepeat | `0x79d0a8` |
  | 8–9 | 2 | `GamepadAtt.d` = repeatTime, **BE** | `0x79d0b8`, `0x79cd2c` |
  | 10+7i | 7 | step record (§1.2) | — |

- Pool names PROVEN: `pp.txt:54008-54020` `Field <GamepadDefMap.type|time|key>`,
  `<GamepadAtt.type|setting|key|att|d>`, `<GamepadDef.len|gpatt|map>`.

### 1.2 2.22.0901 — the 7-byte step record (PROVEN STATIC)

`GamepadDefMap` emitted one field at a time (byte = index 0..6):

| rec off | content | asm |
|---|---|---|
| 0 | `0x80` (type; `r17=256`=Smi(128)=byte 0x80) | `0x79cc24`, imm `0x7a5c9c` |
| 1–2 | `time` u16 BE = `duration_ms / 8` | `0x79cca4` (hi), `0x79cd2c` (lo); `sdiv …,x,#8` at `0x7a5c80` |
| 3–6 | `key` u32 BE (key bitmask `1<<k` for `k<=0x21` OR stick-pattern word) | `0x79cd60` (>>24), `0x79cdbc`, `0x79ce18`, `0x79ce78` |

Key accumulation `k<=0x21 → mask|=1<<k` at `0x7a5c38`; stick table `0x22..0x31` at `0x7a5ad0-0x7a5c14`.

### 1.3 2.23.0609 — OLD format (PROVEN STATIC, structurally identical to 2.22)

- `changeGamepadDef` @0x798b04, body contains the CRC loop `r6=65535` @0x7995a8 and
  `r16=40961` (0xA001) @0x79961c, `mov x1,#7` @0x798d68, `add #0xa` @0x7f8240 / 0x7f8488 / 0x7f916c
  → same `N = 10 + 7n`, same 7-byte `GamepadDefMap` records.
- Pool names identical: `pp.txt:53715-53727` (`GamepadDefMap.type/time/key`, `GamepadAtt.*`, `GamepadDef.*`).
- `subpackageLength` and `TranscribeFrame`/`applicationFrameMacro`/`frame_config_macros` are
  **ABSENT** (recursive greps empty) — PROVEN STATIC negative.
- Serializer `writeMacroConfig` @**0x797fa0** (body from line 2288): chunk literal 15
  (`fmov d1,#15.0` @0x7980fc). Payload writer = the same `changeGamepadDef` family, so header
  layout = §1.1 (byte 4 = `GamepadAtt.type`, byte 5 = runKey, 6 = runKey|5, 7 = isRepeat,
  8–9 = repeatTime BE, then 7-byte records).

### 1.4 2.24.0919 — MODERN format (PROVEN STATIC)

`applicationFrameMacro` (0x7fec9c) builds `N = 10 + 10n`; `TranscribeFrame.toFrameCmd` (0x800524)
serializes each step; `changeTranscribeFrameToDefMacro` appends a gap frame.

### 1.5 4.0.8 — MODERN format (PROVEN STATIC)

`applicationFrameMacro` @0x85c8c0: `0x85cf5c mov x16,#0xa` → `0x85cf60 mul x0,x1,x16` →
`0x85cf64 add x4,x0,#0xa` ⇒ `N = 10n + 10`.

Header (10 B) — byte-for-byte the same shape as the old format, except byte 4 is a **constant 0**
on this path (it is inside the `inUse` branch; the header constant is stored as `rZR`):

| off | width | field | asm evidence |
|---|---|---|---|
| 0–1 | 2 | CRC-16/MODBUS over [2:], BE | `0x85d4bc` loop, byte0 @`0x85d594`, byte1 @`0x85d5b4` |
| 2–3 | 2 | N, BE | `0x85d200` / `0x85d224` |
| 4 | 1 | `0x00` (constant) | `0x85d238` `StoreField … = rZR` |
| 5 | 1 | trigger key = `int.parse(runKey)` | `0x85cfa0`, store `0x85d254` |
| 6 | 1 | runKey raw, `0 → 5` | `0x85d018-0x85d034`, `0x85d314 r3=5`, store `0x85d2d0` |
| 7 | 1 | isRepeat (0/1) | `0x85d3a4` |
| 8–9 | 2 | repeatTime, BE u16 | `0x85d3f4` (hi), `0x85d410` (lo) |
| 10+10i | 10 | `TranscribeFrame.toFrameCmd` frame | `replaceRange(10+10i, 20+10i, …)` @`0x85d480` |

10-byte step frame (`toFrameCmd`, 4.0.8 0x85e5xx; 2.24 0x800524) — byte identical between 2.24 and
4.0.8 (verified at 2.24 0x800598-0x800708 with explicit mask immediates):

| byte | value |
|---|---|
| 0 | `((t8 & 0x0F) << 4)` |
| 1 | `(t8 >> 4) & 0xFF` |
| 2–5 | key bitmask `1<<k` (k ≤ 0x20), **BE** u32 |
| 6–9 | stick-pattern word from the 16-entry `0x22..0x31` table, **BE** u32 |

`t8 = time_ms ~/ 8` (`sdiv …,x5,#8` @4.0.8 0x85d74c / 2.24 0x80058c); 12-bit ⇒ max 4095×8 = 32760 ms.

### 1.6 Defaults

| default | 2.22 | 2.23 | 2.24 | 4.0.8 |
|---|---|---|---|---|
| `runKey` | **46** (`mov x16,#0x2e` @0x92aabc), name `"M1"` — PROVEN | UNKNOWN (not re-derived) | UNKNOWN | STRONG EVIDENCE: `int.parse(runKey)` @0x85cfa0, byte6 `0→5` @0x85d314 (per-M1 id 23 per toolkit `macro-format.md`) |
| `repeatTime` | **200** (`mov x16,#0xc8` @0x92ab20) — PROVEN | UNKNOWN | UNKNOWN | UNKNOWN |
| macro template record | @0x92aa14 `{changed,id,inUse,runKey,runKeyName,isRepeat,repeatTime,macroName,macroJson}` | — | — | — |
| step time unit | ms, 8 ms granularity (`/8`) — PROVEN | ms (same 7-byte `GamepadDefMap.time`, `/8`) | ms | ms |

`repeatTime` unit remains UNKNOWN in every version (no scaling constant on the wire path; only UI
labels `"ms"` on the sibling duration/interval fields — PARTIAL).

---

## 2. Chunk size — hard-coded vs derived (per version)

| ver | chunk | provenance | label |
|---|---|---|---|
| 2.22 | **15** literal | `0x79e300 fmov d1,#15.0` (ceil N/15); `0x79e50c`/`0x79e54c mov x16,#0xf; mul` (start=(i·15), end=(i+1)·15); `0x79ea88 sdiv #15`; loop bound `0x79e3b0 r17=30`=Smi(15). No `subpackageLength` (recursive grep empty). | PROVEN STATIC |
| 2.23 | **15** literal | `0x7980fc fmov d1,#15.0`; same three `mov x16,#0xf` sites (`0x7980fc`, and the `#15.0` grep sites `0x79e970`, `0x7f8704` region). No `subpackageLength`. | PROVEN STATIC (grep + body) |
| 2.24 | `subpackageLength()-5` = **{15,43,67}** | `writeMacroConfig` @0x7ffb5c: `0x7ffbfc bl 0x7b9064` then `sub x1,x0,#5`. `subpackageLength()` @**0x7b9064** (`define.dart:477`) returns `#0x14`@0x7b9124, `#0x48`@0x7b90ec, `#0x30`@0x7b9134. | PROVEN STATIC for the switch values; the `-5` arithmetic is directly visible |
| 4.0.8 | `subpackageLength()-5` = **{15,43,67}** | `writeMacroConfig` @0x85a670: `0x85a6f0 bl 0x819190` → `0x85a6f4 sub x1,x0,#5` used directly as the float divisor (`0x85a704 scvtf d1,x1`); the loop re-derives chunk at `0x85a72c-0x85a730 sub x3,x0,#5`. `subpackageLength()` @**0x819190** (`define.dart:316`): `0x819238 mov x0,#0x14`, `0x819264 mov x0,#0x48`, `0x819274 mov x0,#0x30`. | PROVEN STATIC |

**Cross-anchor for 20/48/72 (independent of the Smi question):** the live 144-byte D6 readback came
back as `A4 14 D6 <ordinal> <15 bytes>` — length byte `0x14` = 20, payload 15 ⇒ `chunk = 20-5 = 15`.
The 4.0.8/2.24 read reassembler computes its output stride from the same
`subpackageLength(); sub x1,x0,#5` pair (4.0.8 `0xac1eec`/`0xac1ef0`), and the write path's
`sub x0,#5` operand-immediate is `0x14`/`0x48`/`0x30`. So the operands are 20/72/48 and the chunks
15/67/43 — **PROVEN STATIC + anchored live**.
*(If one instead read the `mov x0,#0x14` as a tagged Smi the Dart value would be 10; that reading is
refuted by the live 20-byte frames. Recorded for completeness.)*

Device-id → value mapping (public ids from the switch body; the ARMOR-X Pro's `field_7` id is not
resolvable statically here — the app prints `包数->N` before writing, so it is observable at runtime):

- 4.0.8 `0x8191b4-0x819234`: id `1,2,3` and `7..10` → 20; id `4`...`7` → 72; else (`0,5,6,11…`) → 48.
- 2.24 `0x7b9088-0x7b9120`: id `1,2,3` → 20; id `5,6` → 48; id `4,7` → 72; else → 48.
  → the two trees are **not** branch-identical (2.24 has no `9/10` arms); label **INFERRED** per device.
  Both agree that the three possible chunks are 15 / 43 / 67.

---

## 3. The commit / terminator frame — exact bytes, per version

All four: `A4 05 D8 <nfrags+1> <csum>` where `csum = (Σ all preceding bytes) & 0xFF`.

| ver | function | A4 | len byte | D8 | count | append | label |
|---|---|---|---|---|---|---|---|
| 2.22 | `writeMacroConfig` @0x79dfc8 | shared `[0xA4]` template @0x79e358, reused for the commit list @0x79eb0c | `0x79eb7c mov x17,#0xa` (Smi 10 = **5**) | `0x79ebf4` | `0x79ec08 field_23` → `0x79ec24 add x1,x3,#1` → append `0x79eca8` | `A4 05 D8 <nfrags+1> <csum>` | PROVEN STATIC |
| 2.23 | `writeMacroConfig` @0x797fa0 | shared `[0xA4]` template (same shape) | `0x798744 mov x17,#0xa` (=**5**) | `0x7987a0` | `0x7987a8 add x1,x4,#1` | same | PROVEN STATIC |
| 2.24 | `writeMacroConfig` @0x7ffb5c | `0x800060 mov x17,#0x148` (=0xA4) | `0x80012c mov x17,#0xa` (=**5**) | `0x800188` (=0xD8) | `0x800190 add x1,x4,#1` | same | PROVEN STATIC |
| 4.0.8 | `writeMacroConfig` @0x85a670 | `0x85aaf8 mov x16,#0x148` (=0xA4) | `0x85aba8 mov x16,#0xa` (=**5**) | `0x85abf0` (=0xD8) | `0x85abf8 add x5,x2,#1` (x2 = loop counter, ends at nfrags) → append `0x85ac3c` | same | PROVEN STATIC |

Worked example (identical in all versions), nfrags = 2:
`A4 05 D8 03 84` — `0x84 = (0xA4+0x05+0xD8+0x03) & 0xFF = 0x184 & 0xFF`.

### 3.1 Data-fragment ordinal byte (frame offset 3) — per version

**Present in every version, value `i+1` (1-based).**

| ver | ordinal store | label |
|---|---|---|
| 2.22 | `0x79e78c field_23`; `0x79e7a8 add x1,x3,#1`; `BoxInt64` @`0x79e814` (field_23 counts loop iterations 0-based inside the body, incremented on the back-edge at `0x79e494/0x79e4ac`, entry jumps past it at `0x79e3c8` → ordinals 1..nfrags) | PROVEN STATIC |
| 2.23 | `0x798310 add x4,x3,#1` … `0x798374`+`BoxInt64` @`0x798394` (same shape as 2.22) | STRONG EVIDENCE |
| 2.24 | `0x7ffcf4 add x9,x6,#1` stored `[fp,-0x58]`; `BoxInt64(x6=[fp,-0x58])` @`0x7ffe88` | PROVEN STATIC |
| 4.0.8 | `0x85a7e8 add x9,x6,#1` stored `[fp,-0x50]`; `BoxInt64(x6=[fp,-0x50])` @`0x85a938` | PROVEN STATIC |

Anchor: the live D6 readback frames carry ordinals 1..10 with the 10th frame's ordinal `0x0A`.

**CONTRADICTED:** `baselines/imported-research/d8-macro.md` §3.3 ("data fragments themselves carry
**no** index/ordinal byte") and `results/version-diff/d8-history.md` line 91 ("fragment ordinal byte
at frame[3] … UNKNOWN" for 2.24/4.0.8). The ordinal exists and the `len = payload+5` arithmetic only
closes because of it (3 header + 1 ordinal + payload + 1 csum = payload+5).

---

## 4. The `0x0A` question — origin, and whether 0x0A is valid anywhere

**Verdict: `0x0A` is NOT a valid D8 commit/terminator byte in ANY of the four versions.
It is `0x05`. The `0x0A` interpretation is a tagged-Smi misread; label CONTRADICTED everywhere.**

Origin of the interpretation (traced to the instruction):
1. The imported baseline reconstruction
   `/home/salamanka/armorx-re/mygt408/research/mygt-4.0.8/d8-macro.md` §3.3 (mirrored into
   `/home/salamanka/armorx-lab/baselines/imported-research/d8-macro.md` line 178) reads
   **4.0.8 `0x85aba8: mov x16, #0xa`** — Blutter's own annotation for it is `"r16 = 10"` — and
   reports it as *"the commit frame's second byte is the constant `0x0A`"*. The number was taken as
   the literal wire byte.
2. The same file derives the 4.0.8 vectors from that reading
   (`d8-test-vectors.json` → `"A4 0A D8 03 89"`).
3. `results/version-diff/d8-history.md` propagated it: *"commit second byte `10` at 0x80012c /
   0x85aba8"* (2.24 / 4.0.8).

Why it is wrong — two independent anchors:
- **Sibling immediates in the same list.** At `0x85a748 mov x16, #0x148` stores the *byte* `0xA4`
  into the packet `List<int>` (TypeArguments `<int>` at `0x85a750`), and `0x85a8f8/0x85abf0
  mov x16, #0x1b0` stores the byte `0xD8`. Both immediates are exactly `2 × byte`. Therefore at
  `0x85aba8` `#0xa` = `2 × 5` → the stored Dart int is **5** → wire byte **`0x05`**. (An odd
  immediate anywhere in this list, which would be an unboxable value, is absent.)
- **Semantics.** The commit frame carries an empty segment, so the length byte is the ordinary
  `segLen + 5` formula evaluated at `segLen = 0` → 5. In 2.22 the compiler emits the *computed*
  value `#0xa` @0x79eb7c after `add …,#5`; in 2.24/4.0.8 the compiler **constant-folded**
  `0 + 5` into the literal `#0xa`. Same value, same source expression. So the 2.22 doc's
  *"2.22 has no 0x0A"* and the 4.0.8 doc's *"4.0.8 emits 0x0A"* are the **same byte** read two ways.
- 2.24 `0x80012c mov x17, #0xa` in the same list alongside `0x800060 #0x148` (0xA4) and
  `0x800188 #0x1b0` (0xD8) — identical situation.

Full-body sweeps (no other candidate): the entire 2.22 `writeMacroConfig` body
(lines 2312-3654) contains exactly one `#0xa` (`0x79eb7c`); the 4.0.8 body (lines 6911-7562)
contains `#0xa` at `0x85aba8` only inside the commit block plus two *unboxed* uses
(`0x85cf5c mul #0xa` in `applicationFrameMacro`, and loop/index arithmetic at `0x85ad80`);
2.24: `#0xa` at `0x80012c` (commit) plus `0x8003f4/0x800408/0x800438` in the post-write/error block.
⇒ **no literal `0x0A` wire byte exists in any fragmentation body.**

### 4.1 Where a genuine `0x0A` *does* appear on the wire
The live 144-byte D6 config read: `A4 14 D6 <ordinal> <15 B> ×9` then `A4 0E D6 0A …`.
There `0x0A` is the **ordinal of the 10th fragment** (`0x0E = 9+5` for the 9-byte tail) — i.e. the
same "count/index" field, in the device→app direction and the D6 family. This is the most likely
second source of the `0x0A` confusion, but it is **not** a D8 commit byte.

### 4.2 Field layout the task asked for — "literal 0x0A in the fragmentation body"
| ver | literal 0x0A in fragmentation body? | label |
|---|---|---|
| 2.22 | **NO** (single `#0xa`, = Dart 5) | PROVEN STATIC |
| 2.23 | **NO** (single `#0xa` @0x798744, = Dart 5) | PROVEN STATIC |
| 2.24 | **NO** (`#0xa` @0x80012c = Dart 5; other `#0xa` outside the fragment/commit builders) | PROVEN STATIC |
| 4.0.8 | **NO** (`#0xa` @0x85aba8 = Dart 5) | PROVEN STATIC |

---

## 5. D8 RECEIVE / READBACK — traced per version

Method note (as instructed): absence of a function literally named `parser` proves nothing; every
tree was searched for the *A4 dispatcher*, for any comparison against `0xD8`/`216`, for
`replaceRange`/`sublist` reassembly, and for the macro row/step constructors.

### 5.1 Generic A4/D6 reassembly (present in all four)

| ver | site | opcode test | dispatch byte | stride | label |
|---|---|---|---|---|---|
| 2.22 | `widgets/general/configs_config.dart:3108` closure @**0x8a6a04** (in `_ConfigsConfigWidgetState::subscribeCharacteristic` @0x8a6620); also `widgets/armor-x_pro/armorx_pro_config_config.dart` @0x89b48c | `data[0]==0xA4` @0x8a6a58; `data[2]==0xD6` @0x8a6a68-0x8a6a88 | `data[3]` @0x8a6a9c; branches compare 1,2,3,… (tagged `#2,#4,#6,…` @0x8a6ab8/0x8a6bcc/0x8a6c58/0x8a6ce4/…) | payload window `sublist(2,19)` @0x8a6afc-0x8a6b08; `replaceRange` into a growing buffer at offsets **0,15,30,45,60,75** @0x8a6b28/0x8a6bb4/0x8a6c40/0x8a6ccc/0x8a6d58/0x8a6e00 | PROVEN STATIC (addresses); stride 15 PROVEN (odd immediates `#0xf`, `#0x2d` cannot be tagged) |
| 2.23 | `widgets/general/configs_config.dart` (A4 dispatcher, `cmp x1,#0xa4`) and `widgets/rainbow/rainbow_tab_config_1s.dart` (`parsingData` @**0x8098cc**, called @0x809198/0x8093ec/0x8096e4) | `cmp x1,#0xa4` present | same family | same 15-byte stride family | STRONG EVIDENCE (structure not exhaustively read) |
| 2.24 | `widgets/general/configs_config.dart` @**0x912d30** (`cmp w0,#0x148`), @**0x912d58** (`cmp w0,#0x1ac`); `replaceRange` @0x912f18/0x912ff8; `sublist` @0x9131f0/0x9134dc/…; also `configs_mian.dart`, `rainbow_tab_config_1s.dart` | `data[0]==0xA4` (tagged), `data[2]==0xD6` | `data[3]` | sublist + `replaceRange` | PROVEN STATIC |
| 4.0.8 | `widgets/general/configs_config.dart` @**0xac1de8** (`cmp w0,#0x148`), @**0xac1e10** (`cmp w0,#0x1ac`); then `cmp w0,#2` @0xac1e38; adjacent-byte read @0xac1e4c/0xac1e80 (`#12`/`#14` → bytes 6/7) → `StoreStaticField` @0xac1ec0; `subpackageLength(); sub #5` @**0xac1eec/0xac1ef0** | same | same | `replaceRange` @0xac1fc4/0xac208c | PROVEN STATIC |

**Index convention proven (important correction).** The accessor index immediates are *tagged
Smis*: at 4.0.8 `0xac1e4c mov x16,#12` and `0xac1e80 mov x16,#14` are followed by
`lsl x2, x1, #8` / `orr x2, x0, x1` producing an adjacent big-endian pair → they address **bytes 6
and 7**, i.e. Dart indices 6 and 7 (12/2, 14/2). Likewise `#30`→15 and `#32`→16 in `parsingData`
(adjacent little-endian pair, see §5.3). Therefore in the A4 dispatchers the opcode access `#4` is
**byte 2** and the ordinal access `#6` is **byte 3** — exactly matching the live anchor
`A4 14 D6 <ordinal> …`.
**CONTRADICTED:** earlier notes (`results/static/2.22.0901/d8-macro.md` §2 "data[4]==0xD6,
data[6]==2") labelled those indices literally as bytes 4 and 6; the halved reading is required by
the adjacent-byte proof and by the live frame layout.

### 5.2 D8-specific macro readback

| ver | D8 receive handling | call chain (addresses) | status |
|---|---|---|---|
| **2.22.0901** | **ABSENT** — no `0xD8`/`216` comparison exists anywhere in `widgets/` (recursive grep empty); the macro path never parses a device reply. The only receive parsers are the fixed-offset blobs `GamepadParam` (`sublist(11,32)(16,40)(32,68)(34,72)(36,76)(38,80)(43,102)`; `0x79dbfc r0=43`, `0x79dc00 r16=102`) and `GamepadParam30` (`sublist(16,48)(24,64)(34,72)(70,216)`; `0x79fb00 r0=70`, `0x79fb04 r16=216`). The literal `216` there is a **sublist bound**, not an opcode test. Macro state comes from the server JSON (`MacroRow.fromJson`; `addMacroResponse` @0x8bed24, `changeMacroRunkeyResponse` @0x8ac3b0/0x8ac4cc, `changeMacroRepeatResponse` @0x8bfd18, `changeMacroUseRepeatTimeResponse` @0x8c18c8, `changeMacroInUseResponse` @0x8be534 all call `applicationMacro`). | generic A4/D6 only | **D8 readback ABSENT** (PROVEN STATIC negative); generic A4 readback PRESENT |
| **2.23.0609** | **ABSENT** for D8 (no `0xD8`/`0x1b0` comparison in `widgets/`, grep empty); generic A4 + `parsingData` @0x8098cc present. | generic only | **D8 readback ABSENT**; generic PRESENT |
| **2.24.0919** | **PRESENT (PARTIAL).** `_FrameMacrosConfigWidgetState` notification closure @~0x915a2c-0x915c1c: `list[2]` tested `#0x1f8` (`0x915a68`, ==0xFC → exit), `#0x1b0` (`0x915a90`, ==0xD8 → prints `"写入结果"` @0x915a98 and `printHex` @0x915ab0), then `#0x1a6` (`0x915ad8`, ==0xD3) → reads `list[7]`, `list[8]` (`#14`/`#16`). `parsingData` @**0x915c38** invoked @0x915a3c; `TranscribeFrame.fromConfigData` @**0x80163c** invoked @0x916144. | `subscribeCharacteristic → closure(0x915a2c) → parsingData(0x915c38) → TranscribeFrame.fromConfigData(0x80163c) → changeTranscribeFrameToDefMacro` | **PRESENT/PARTIAL** (frame reconstruction PRESENT; step-count/limit logic PARTIAL) |
| **4.0.8** | **PRESENT (PARTIAL).** Same structure: closure @~0xac33b4-0xac3590: `list[2]` `#0x1f8` (0xac33e0, 0xFC → exit), `#0x1b0` (0xac3408, 0xD8 → `"写入结果"` @0xac3410 + `printHex` @0xac3420), `#0x1a6` (0xac3448, 0xD3 → `list[7]`/`list[8]`). `parsingData` @**0xac35ac** (called @0xac33b4); `fromConfigData` @**0x85e32c** (called @0xac3a8c). | as 2.24 | **PRESENT/PARTIAL** |

### 5.3 Readback byte offsets actually read (4.0.8 `parsingData` @0xac35ac — 2.24 twin is structurally identical)

| Dart index (asm imm) | wire byte offset | read as | use | label |
|---|---|---|---|---|
| 3 (`#6` @0xac3604) | offset 3 | int | compared with `field_23 - 2` @0xac3620-0xac3638; on `>=` → `stopTranscribe` @0xac3640 + `"宏步数已经超出限制"` @0xac365c | PROVEN STATIC |
| 15 (`#30` @0xac369c) | offset 15 | low byte | u16 **little-endian** with byte 16 (`ldrb [x0,#0x17]` @0xac374c) | PROVEN STATIC |
| 16 (`#32` @0xac36c4) | offset 16 | high byte | `lsl x2,x1,#8` @0xac3748 | PROVEN STATIC |
| 15–16 combined | offsets 15–16 | u16 LE | `val = b1<<8 + b0` @0xac3754, then `val <<= 3` (= ×8 ms) @0xac3754-0xac375c, stored to `last().field_1b` (the frame's `time` in ms) @0xac377c | PROVEN STATIC |

After the time is stamped, `parsingData` calls `changeTranscribeFrameToDefMacro` @0xac37a4 and writes
the rebuilt `MacroRow` list to `field_37`. `TranscribeFrame.fromConfigData` @0x85e32c is the other
readback entry (bit-walk of a 32-bit key word, MSB-first, plus a 16-entry stick table — see the
4.0.8 baseline §5.3).
The `"最大步数"` print lives in the *caller* (4.0.8 `0xac3568`, 2.24 `0x915bf4`), **not** inside
`parsingData` as the imported doc stated — a small but real correction.
**Residual UNKNOWN:** whether the u16 at bytes 15–16 is a per-frame time or a fragment counter, and
the exact meaning of `field_23` (`maxSteps`), need a capture; the *offsets* (15,16) are proven.

### 5.4 Readback command
The app's config read is the short frame `A5 04 D6 7F` (`get_device_config`, PROVEN LIVE + STATIC,
`automation/scripts/armorx_lab/frames.py::KNOWN_FRAMES`); the device answers with A4-fragmented
`D6` frames which the §5.1 reassembler stitches. There is **no dedicated "read macro" command** in
any version: the macro readback rides the same D6 blob (2.22/2.23: no macro fields in the blob, so
effectively no macro readback) or the D8/D3 notification (2.24/4.0.8).

---

## 6. Test vectors

Machine-readable: `results/reconciliation/d8-version-test-vectors.json` (one encode vector + one
commit-frame vector per version, each marked `derived_from`). Every vector is **DERIVED** from the
statically reconstructed layout with the CRC recomputed independently in Python
(CRC-16/MODBUS, init 0xFFFF, poly 0xA001, reflected) — **none is captured**.

Confirmed cross-checks: the 2.22 `11 FB 00 11 00 2E 2E 00 00 C8 80 00 0C 00 00 00 01` payload and
its `A4 14 D8 01 …5E` / `A4 07 D8 02 00 01 86` / `A4 05 D8 03 84` frames reproduce
`results/static/2.22.0901/d8-macro.md` T1 byte-for-byte (that doc's vectors already carried the
ordinal). The imported 4.0.8 vectors do **not** reproduce: they omit the ordinal byte and use the
wrong commit byte (`A4 0A D8 …`).

---

## 7. Corrections issued against earlier docs

See the dated block appended to `results/version-diff/d8-history.md` (§"2026-09-27 correction").
Summary: (a) commit byte is 0x05 not 0x0A (all versions); (b) the fragment ordinal byte exists in
2.24/4.0.8 as well; (c) 2.22's dispatcher indices are `data[2]`/`data[3]`, not `data[4]`/`data[6]`;
(d) the 4.0.8 header byte 4 is a constant 0 while 2.22's is `GamepadAtt.type` — the two are *not*
byte-identical header-wise even though the field widths match; (e) `"最大步数"` print site.

## 8. Open items (honest gaps)

1. 2.23's fragment ordinal value (`i+1`) is STRONG EVIDENCE only — the storer of `[fp,-0x40]` was
   not traced to its definition (2.22/2.24/4.0.8 are PROVEN).
2. 2.24 vs 4.0.8 `subpackageLength()` device-id branches are not identical (`9/10` arms present in
   4.0.8 only). The ARMOR-X Pro's `field_7` id remains UNKNOWN statically.
3. `repeatTime` unit (ms assumed) — UNKNOWN in all four.
4. Readback semantics of `field_23` / the u16 at bytes 15–16 — offsets proven, meaning PARTIAL.
5. 2.22/2.23 `parsingData`-equivalent offsets not exhaustively enumerated (2.22's dispatcher ladder
   is proven to step 15 and dispatch on `data[3]`; deeper branches unread).
