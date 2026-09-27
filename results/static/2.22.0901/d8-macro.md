# D8 macro protocol — BIGBIG WON **2.22.0901** (Dart 2.17.5 AOT) — static reconstruction

Scope: `lib/arm64-v8a/libapp.so` of `apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk`
(sha256 `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`), disassembled with
Blutter `blutter_dartvm2.17.5_android_arm64` into
`static/blutter/2.22.0901/blutter_out/` (`asm/`, `pp.txt`, `objs.txt`).

Evidence labels: **PROVEN STATIC** (instruction-level, cited file+addr) · **STRONG EVIDENCE**
(multiple corroborating sites / value tables) · **INFERRED** · **UNKNOWN** · **CONTRADICTED**.
Nothing in this document was taken from a later build. The APK was never modified or executed;
no radio traffic was generated.

---

## 0. Headline result

**2.22.0901 implements the same D8 macro wire family as 4.0.8 — same opcodes, same header
layout, same CRC — but with a different chunking model and a smaller macro frame.**

| Aspect | 2.22.0901 |
|---|---|
| D8 payload header | `[crc16][len][0][runKey][runKey\|5][isRepeat][repeatTime]` — **byte-identical semantics to 4.0.8** (PROVEN STATIC) |
| Macro step frame | **7 bytes** = `[type][time16 BE][key32 BE]` — not the 4.0.8 10-byte frame (PROVEN STATIC) |
| Fragmentation | `A4 <segLen+5> D8 <seg> <csum>`, **chunk hard-coded 15** (PROVEN STATIC) |
| Commit/terminator | `A4 05 D8 <nfrags+1> <csum>` — **no 0x0A byte anywhere** (PROVEN STATIC) |
| MTU / subpackageLength / device chunk table | **absent** — no such symbol exists in 2.22 (PROVEN STATIC, negative) |
| Device→app D8 macro readback | **absent** — no D8 macro parser exists (PROVEN STATIC, negative) |
| Macro persistence | server-side JSON CRUD (`addMacroResponse`, `changeMacroRunkeyResponse`, …); BLE is used only to *apply* (PROVEN STATIC) |

The 4.0.8 conclusion that the payload is a *TranscribeFrame* list with 12-bit time + separate
key/stick words **does not hold in 2.22** and must not be promoted backwards. The 4.0.8 chunk
candidate set {15, 43, 67} (`subpackageLength()-5`) **collapses to 15 only** here, and 15 is a
literal, not derived from MTU or from a device table.

---

## 1. Encode direction (macro UI → object → serializer → D8 payload → fragmentation → BLE write)

### Hop 1 — UI / event handlers
File `asm/moojiang/widgets/armor-x_pro/armorx_pro_config_macro.dart`,
class `_ArmorXProMacroWidgetState` (extends the generic rainbow macro state, see
`_ArmorXProMacroWidget.createState` → `_RainbowMacroConfigWidgetState()` @0x9b6ecc).

The macro *record* is a plain map with a fixed default template, built inline at **0x92aa14**
(`[closure] void <anonymous closure>(dynamic, BoxCode)`), lines 15206-15359:

```
"changed": false, "id": -2, "inUse": false,
"runKey": 46, "runKeyName": "M1", "isRepeat": false,
"repeatTime": 200, "macroName": "", "macroJson": ""
```
PROVEN STATIC — pool refs `[pp+0x45408] "inUse"`, `[pp+0x45410] "runKey"`, `[pp+0x45418]
"runKeyName"`, `[pp+0x45420] "isRepeat"`, `[pp+0x45428] "repeatTime"`, `[pp+0x45430]
"macroName"`, `[pp+0x45438] "macroJson"`; default `runKey = 46` (`mov x16,#0x2e`,
0x92aabc), `repeatTime = 200` (`mov x16,#0xc8`, 0x92ab20).

The BLE apply is triggered from the server-response / commit handlers, each of which calls
`applicationMacro` (PROVEN STATIC, `grep -n 'r0 = applicationMacro()'`):

| file:line | address | enclosing handler |
|---|---|---|
| 2434 | 0x8bed24 | `_ addMacroResponse` (body starts line 1806) |
| 4081 | 0x8ac3b0 | `_ changeMacroRunkeyResponse` (3599) |
| 4184 | 0x8ac4cc | `_ changeMacroRunkeyResponse` (3599) |
| 4722 | 0x8bfd18 | `_ changeMacroRepeatResponse` (4242) |
| 5224 | 0x8c18c8 | `_ changeMacroUseRepeatTimeResponse` (4778) |
| 5726 | 0x8be534 | `_ changeMacroInUseResponse` (5280) |
| 12909 | 0x8bdfc4 | `[closure] void <anonymous closure>(dynamic)` (12863) |

### Hop 2 — deserialize the macro JSON → `GamepadDef`
`applicationMacro` @**0x7a559c**, async body closure @**0x7a56c4**
(`asm/moojiang/units/gamepadset.dart` lines 4764-6295). It reads the envelope keys above,
`jsonDecode`s `macroJson` and builds `MacroRow` objects (`MacroRow.fromJson`).

Then it builds a **`GamepadDef`** with one `GamepadDefMap` per macro step. Buffer length is
computed as `10 + 7·n`:

```
0x7a6234: mul   x0, x1, #7      ; 7 bytes per step  (line 5780)
0x7a6238: add   x0, x0, #0xa    ; + 10-byte header
```
PROVEN STATIC. The Gamepad-family late-field symbols are in `pp.txt` lines 54008-54020:

```
[pp+0x456c8] Field <GamepadDef.gpatt>: late (offset: 0xc)
[pp+0x456e0] Field <GamepadDef.map>:   late (offset: 0x10)
[pp+0x456e8] Field <GamepadDef.len>:   late (offset: 0x8)
[pp+0x456f0] Field <GamepadAtt.type>:    late (offset: 0x8)
[pp+0x456f8] Field <GamepadAtt.setting>: late (offset: 0xc)
[pp+0x45700] Field <GamepadAtt.key>:     late (offset: 0x10)
[pp+0x45708] Field <GamepadAtt.att>:     late (offset: 0x14)
[pp+0x45710] Field <GamepadAtt.d>:       late (offset: 0x18)
[pp+0x45718] Field <GamepadDefMap.type>: late (offset: 0x8)
[pp+0x45720] Field <GamepadDefMap.time>: late (offset: 0xc)
[pp+0x45728] Field <GamepadDefMap.key>:  late (offset: 0x10)
```

**Key / stick accumulation (PROVEN STATIC, lines 5330-5790):** the step's changed-control list
`MacroRow.mapList` is folded into two 32-bit accumulators:

* `k <= 0x21` → key bitmask `keymask |= 1 << k` (0x7a5c38-0x7a5c48).
* `k in 0x22..0x31` → OR of a **stick-pattern table** (0x7a5ad0-0x7a5c14). Table values
  (read from the `mov` immediates): `0x22→0x80000000`, `0x23→0x7f000000`, `0x24→0x7f0000`,
  `0x25→0x800000`, `0x26→0x8000`, `0x27→0x7f00`, `0x28→0x7f`, `0x29→0x80`,
  `0x2a→0x80000000|0x7f0000`, `0x2b→0x7f000000|0x7f0000`, `0x2c→0x80000000|0x800000`,
  `0x2d→0x7f000000|0x800000`, `0x2e→0x8000|0x7f`, `0x2f→0x7f00|0x7f`,
  `0x30→0x8000|0x80`, `0x31→0x7f00|0x80`.

Each step becomes a `GamepadDefMap` array `[ type=0x80 , time=duration/8 , key=accumulator ]`
(`r17 = 256` → Smi 128 → byte `0x80` at 0x7a5c9c; `sdiv …,#8` at 0x7a5c80). The `runKey`,
`isRepeat` and `repeatTime` values are stored into the **`GamepadAtt`** sub-object of the
`GamepadDef` (fields `setting`, `key`, `att`, `d`).

Finally:
```
0x7a66c8/0x7a66dc/0x7a66f0: build args
0x7a66f4: r0 = writeMacroConfig()
```
with argument order (by stack slot) `writeMacroConfig(env.field_23, env.field_1f, GamepadDef, runKey)`.
PROVEN STATIC.

### Hop 3 — `writeMacroConfig` @**0x79dfc8** (async body closure @**0x79e158**)
`asm/moojiang/units/gamepadset.dart` lines 2312-3654. Wrapper stores the 4 args into context
slots `field_1b/=fp+0x28(int)`, `field_1f`, `field_23`, `field_27` (0x79e010-0x79e028).

**3a. payload** = the serializer result concatenated with one extra context integer element:
```
0x79e1ec: LoadField r3 = <ctx>->field_1b     ; the int arg (runKey at the call site)
0x79e1f8: new list [field_1b]
0x79e2a0: r0 = changeGamepadDef()            ; the ONLY call site of changeGamepadDef in 2.22
0x79e8ac/0x79e8b4: r0 = +()   ; _ListBase&Object&ListMixin::+
```
PROVEN STATIC that one integer element and the GamepadDef serialization are concatenated;
**prefix vs suffix order is UNKNOWN** (see §5 open item O-5).

**3b. fragment count**
```
0x79e2e0-0x79e2ec: N = payload.length  (sbfx / ldur)
0x79e300: fmov d1, #15.00000000
0x79e310: fcvtps x1, d1/d0   ; ceil(N/15)
0x79e3b0: r17 = 30           ; Smi 30 = Dart 15 (upper bound of the loop counter)
```
PROVEN STATIC → **chunk = 15, hard-coded**.

**3c. per-fragment loop** (lines 2646-2860)
```
0x79e50c: r16 = 15 ; mul  -> start = i*15
0x79e54c: r16 = 15 ; mul  -> end   = (i+1)*15   (clamped at 0x79e5b0)
0x79e658: sub  x4, x3, x1        ; segLen = end - start
0x79e65c: add  x1, x4, #5        ; len byte = segLen + 5
0x79e358: r17 = 328 (Smi 164)    ; 0xA4   -> frame[0]
0x79e428: r17 = 328              ; 0xA4   -> (second, alternate construction path)
0x79e778: r17 = 432 (Smi 216)    ; 0xD8   -> frame[2]
```
so each data fragment is `A4 (segLen+5) D8 <seg> <checksum>`; the checksum is computed by
`getCheckSum` @**0x79c368** = Σ bytes & 0xFF (mask `mov x11,#0xff` @0x79c438, `ubfx` 0x79c43c,
`and` 0x79c440). Inter-fragment delay is 4 ms (`r17 = 4` @0x79edf4 — INFERRED as ms, see O-4).

**3d. terminator / commit frame** (lines 3186-3340)
```
0x79eb7c: r17 = 10        ; raw 10 -> Smi 10 = Dart 5  = len byte for a zero-length segment
0x79ebf4: r17 = 432       ; 0xD8
0x79ec24: add x1, x3, #1  ; nfrags + 1   (field_23 = nfrags)
0x79eca8: ArrayStore      ; append
```
→ terminator = `A4 05 D8 <nfrags+1> <checksum>`. PROVEN STATIC.
**There is no 0x0A byte**: a full sweep of 2312-3654 for `#0x14` (Smi 20 → byte 0x0A) and for
any `0x0a` immediate that survives the halving rule returned nothing except the len-byte `10`
above. The 4.0.8 "commit byte 0x0A" is **CONTRADICTED** for 2.22.

**The write frame is `A4 | len | D8 | ordinal | seg | csum`, total = `5 + segLen` bytes, and
`len == total` (PROVEN for the terminator, see §10).** The `len +5` arithmetic (`r17 = 10` raw →
Dart 5, 0x79eb7c) is just the `segLen+5` formula evaluated at `segLen = 0`.

### Hop 4 — `getCheckSum` / serialization helpers
* `getCheckSum` @0x79c368 — Σ & 0xFF (PROVEN STATIC).
* `getCRC` / `intToHex` are present in the pool but have **no call sites** in `asm/moojiang`;
  the CRC is instead computed inline inside `changeGamepadDef` (below).

### Hop 5 — the serializer `changeGamepadDef` @**0x79c894** (lines 413-1249)
This is the *real* D8 payload builder. It allocates a `List<int>` of `10 + 7n` and fills it
element-by-element. Activation-frame symbols are named in the inline late-field error
handlers, which is unusually informative (see §6):

```
0x79d044: r9 = len     (Field <GamepadDef.len>)
0x79d06c: r9 = gpatt   (Field <GamepadDef.gpatt>)
0x79d078: r9 = type    (Field <GamepadAtt.type>)
0x79d088: r9 = setting (Field <GamepadAtt.setting>)
0x79d098: r9 = key     (Field <GamepadAtt.key>)
0x79d0a8: r9 = att     (Field <GamepadAtt.att>)
0x79d0b8: r9 = d       (Field <GamepadAtt.d>)
```

* **CRC-16/MODBUS** over elements `[2:]` of the payload:
  ```
  0x79cf10: r6 = 65535        ; init 0xFFFF
  0x79cf30: ArrayLoad r7 = r2[...]
  0x79cf48: eor x7, x6, x8    ; crc ^= byte
  0x79cf60: cmp x7, #8 / loop ; 8 rounds
  0x79cf84: r16 = 40961       ; 0xA001 polynomial
  0x79cf88: eor x9, x8, x16
  0x79d008: StoreField r4->field_f  = r8   ; elem0 <- (crc & 0xff00) >> 8
  0x79d028: StoreField r4->field_13 = r1   ; elem1 <-  crc & 0xff
  ```
  PROVEN STATIC. This is the same CRC as 4.0.8.
* **length**: elem2/elem3 = `len >> 8`, `len & 0xff` (0x79c960 `asr x9,x0,#8` … 0x79c994).
* **header bytes 4..9** = `GamepadAtt.type`, `.setting`, `.key` (with the **`0 → 5`
  substitution** `r9 = 5` @0x79ca70), `.att`, and a 16-bit BE field from `.d`
  (0x79cb18 `ArrayLoad r8[0]`; `&0xff00 >>8` 0x79cd80-0x79cd8c; `&0xff` 0x79cd2c).
* **records**, count = `(len - 10) / 7` (0x79cb80 `mul #7` / 0x79cbac `add #0xa`), 7 bytes each:
  ```
  0x79cc24: map.type -> byte 0
  0x79cca4: (map.time & 0xff00) >> 8 -> byte 1
  0x79cd2c: (map.time & 0xff)        -> byte 2
  0x79cd60: (map.key >> 24)          -> byte 3
  0x79cdbc: (map.key >> 16)          -> byte 4
  0x79ce18: (map.key >> 8)           -> byte 5
  0x79ce78: (map.key & 0xff)         -> byte 6
  ```
  PROVEN STATIC (offsets 0x79cc24 → `r0->field_7` = `GamepadDefMap.type`, 0x79cca4/0x79cd0c =
  `field_b` = `.time`, 0x79cd60/0x79cdbc/0x79ce18/0x79ce78 = `field_f` = `.key`; the three
  `GamepadDefMap` field names come from `pp.txt` 54018-54020).

**Therefore the 2.22 D8 macro payload is:**

```
off  size  field        endian  notes
 0    2    crc16        BE      CRC-16/MODBUS (init 0xFFFF, poly 0xA001) over bytes [2:]
 2    2    length       BE      = 10 + 7*nsteps  (GamepadDef.len)
 4    1    att.type     -       GamepadAtt.type
 5    1    runKey       -       GamepadAtt.setting
 6    1    runKey|5     -       GamepadAtt.key, 0 -> 5
 7    1    isRepeat     -       GamepadAtt.att
 8    2    repeatTime   BE      GamepadAtt.d
10    7×n  macro step   -       GamepadDefMap: [type=0x80][time=duration/8 16b BE][key 32b BE]
```

---

## 2. Decode direction (BLE notification → fragment assembly → parser → macro object → UI)

### Hop 1 — notification dispatch
The receive side is a *different* frame shape from the write side. Every A4-indexed reassembler
is the `[closure] void <anonymous closure>(dynamic, List<int>)` in the page widgets:

| file:line | address | first test | note |
|---|---|---|---|
| `widgets/general/configs_config.dart:3107` | 0x8a6a04 | `cmp x1, #0xa4` (0x8a6a58) | 0xA4 dispatcher |
| `widgets/armor-x_pro/armorx_pro_config_config.dart:7286` | 0x89b48c | `cmp x1, #0xa4` | 0xA4 dispatcher |
| `widgets/armor-x_pro/armorx_pro_root.dart:3179` | — | `cmp x1, #0xa4` | 0xA4 dispatcher |
| `widgets/rainbow/rainbow_root.dart:3163` | — | `cmp x1, #0xa4` | 0xA4 dispatcher |

Reassembly (from `configs_config.dart:3107-3266`, PROVEN STATIC):
```
0x8a6a58: cmp  x1, #0xa4            ; data[0] == 0xA4
0x8a6a80: r16 = 428                 ; data[4] == 0xD6  (device-config opcode)
0x8a6ab8: r16 = 2                   ; data[6] == 2
0x8a6ae8: sublist(4, 38)            ; 34-byte window
0x8a6b18..0x8a6b28: replaceRange(0, 15, <sublist>)     ; fragment ordinal 2 -> output offset 0
0x8a6bb4..0x8a6bac: replaceRange(15, 30, <sublist>)    ; fragment ordinal 4 -> output offset 15
```
So: **received frame = `A4 ? ? ? <opcode@4> ? <ordinal@6> <payload…>`; the reassembly step is
15 bytes and the output offset advances by 15 for each +2 in the ordinal.** (Ordinal-to-offset
mapping `ord 2 → 0`, `ord 4 → 15`; whether the ordinal counts in units of 2 or is an absolute
byte index is UNKNOWN — see O-6.) There is **no D8 (0xD8 / 216) ordinal dispatcher** on the
receive side (PROVEN STATIC negative).

### Hop 2 — config-blob parsers (the readback routines)
The assembled blob is decoded by the *param* classes, which read **fixed byte offsets**:

* `GamepadParam30` @ line 17217, `sublist(16, 48)`, `sublist(24, 64)`, `sublist(34, 72)`,
  **`sublist(70, 216)`** (0x79fb00 `r0 = 70`, 0x79fb04 `r16 = 216`), plus a 32-bit
  byte-swap and `.toRadixString(16)` hex conversion at 0x79fa74-0x79fad4.
* `GamepadParam` @ line 18539, `sublist(11, 32)`, `sublist(16, 40)`, `sublist(32, 68)`,
  `sublist(34, 72)`, `sublist(36, 76)`, `sublist(38, 80)`, **`sublist(43, 102)`**
  (0x79dbfc `r0 = 43`, 0x79dc00 `r16 = 102`).

PROVEN STATIC. These are per-field extractions from a fixed-layout config blob.

### Hop 3 — macro object → UI
There is **no device→app D8 macro deserializer**: the only macro deserializer in 2.22 is
`MacroRow.fromJson` (JSON out of the `macroJson` field), and the macro widget's notification
closure (0x8c290c, `armorx_pro_config_macro.dart:15162`) only calls `setState`. The macro list
itself comes from the **server** (`queryMacroListResponse` @531, `addMacroResponse` @1806,
`changeMacro*Response`). PROVEN STATIC negative.
The `#0xd8`/216 literal that exists in the tree is a **sublist bound** inside `GamepadParam30`
(`sublist(70,216)`, 0x79fb04), not an opcode test.

---

## 3. (c) Fragmentation constants — exact locations

`grep -rn 'mov  *x[0-9]*, #0x2b$\|mov  *x[0-9]*, #0x43$' asm/moojiang` and
`grep -rn 'fmov  *d[0-9]*, #<N>.0' asm/moojiang` were used for 20/43/48/64/67/72.

| const | where | what it governs | label |
|---|---|---|---|
| **15** | `gamepadset.dart:2464` `fmov d1,#15.0` (0x79e300) | `nfrags = ceil(payloadLen/15)` | PROVEN STATIC |
| **15** | `gamepadset.dart:2646` (0x79e50c), `:2665` (0x79e54c) | fragment `start=i*15`, `end=(i+1)*15` | PROVEN STATIC |
| **15** | `gamepadset.dart:2700` (0x79e5b0) | end clamp | PROVEN STATIC |
| **15** | `gamepadset.dart:3134` (0x79ea88) `sdiv x2,…,15` | tail bookkeeping `len/15` | PROVEN STATIC |
| **15** | `gamepadset.dart:2525` `r17 = 30` (Smi 30 → 15) | loop bound | PROVEN STATIC |
| **15** | `configs_config.dart:3210-3265` `replaceRange(0,15,…)` / `(15,30,…)` | **receive** reassembly step | PROVEN STATIC |
| 20 | only `fmov d,#20.0` in `units/component.dart` (UI) and `units/theme.dart` — none near fragmentation | not a chunk size | PROVEN STATIC (negative) |
| 43 | `gamepadset.dart:19246/19404` → `sublist(43, 102)` in **`GamepadParam`** | readback field start offset (59-byte field) | PROVEN STATIC (not fragmentation) |
| 48 | `gamepadset.dart:17577` → `sublist(16, 48)` in **`GamepadParam30`** | readback field (32 bytes) | PROVEN STATIC (not fragmentation) |
| 64 | `gamepadset.dart:17609` → `sublist(24, 64)` in **`GamepadParam30`** | readback field (40 bytes) | PROVEN STATIC (not fragmentation) |
| 67 | not present as a raw immediate anywhere in `asm/moojiang` | — | PROVEN STATIC (negative) |
| 72 | `gamepadset.dart:17609/19246` → `sublist(…, 72)` | readback field end bound | PROVEN STATIC (not fragmentation) |

**No MTU-derived logic and no `subpackageLength()` equivalent exist in 2.22:**
```
$ grep -rn 'subpackageLength\|mtu\|Mtu\|MTU' asm/moojiang/ | head -20
(no output)
```
PROVEN STATIC negative. 2.22's chunk size is a plain literal 15.

---

## 4. (d) Field-by-field comparison with 4.0.8 (`baselines/imported-research/d8-macro.md`)

| field | 4.0.8 (imported) | 2.22.0901 (this work) | verdict |
|---|---|---|---|
| header size | 10 | 10 | same — PROVEN STATIC |
| bytes 0-1 | CRC | CRC-16/MODBUS, init 0xFFFF poly 0xA001, over bytes [2:] | same — PROVEN STATIC |
| bytes 2-3 | length | length = 10 + 7·nsteps, BE | same shape, different step size — PROVEN STATIC |
| byte 4 | unknown/zero const | `GamepadAtt.type` (application sets it via the same object) | **differs** (4.0.8 const 0) — STRONG EVIDENCE |
| byte 5 | trigger key | `GamepadAtt.setting` = runKey | same — PROVEN STATIC |
| byte 6 | runKey (0→5 default) | `GamepadAtt.key`, 0→5 (`r9 = 5` @0x79ca70) | same, incl. the 0→5 default — PROVEN STATIC |
| byte 7 | isRepeat | `GamepadAtt.att` | same — STRONG EVIDENCE |
| bytes 8-9 | repeatTime | `GamepadAtt.d`, 16-bit BE | same width/order — PROVEN STATIC |
| frame size | 10 | **7** | **CONTRADICTED for 2.22** — PROVEN STATIC |
| frame contents | time(12b) + key u32 + stick u32 | `[type=0x80][time16 BE][key u32 BE]` | **differs** — PROVEN STATIC |
| frame time unit | 8 ms granularity (`time/8`) | `GamepadDefMap.time = duration/8` (`sdiv …,#8` @0x7a5c80) | same granularity — PROVEN STATIC |
| keys | u32 bitmask | u32 bitmask, `1<<k` for `k<=0x21` | same — PROVEN STATIC |
| stick | u32 pattern | u32 pattern from the 0x22..0x31 table (OR-accumulated) | same family — STRONG EVIDENCE |
| disable | all-zero frame | type `0x80` with `time=0,key=0` — **turn `0x80` is still present**, so 2.22 has no "all-zero frame" literal | **differs/UNKNOWN** — see O-7 |
| transport | A4 indexed fragmentation | A4 fragmentation | same — PROVEN STATIC |

---

## 5. (e) The four open questions, against 2.22 evidence

**O-1 — D8 chunk size → RESOLVED (for 2.22): 15 bytes, hard-coded.**
Evidence: `fmov d1,#15.0` (0x79e300) + `mul #15` twice (0x79e50c/0x79e54c) + `sdiv #15`
(0x79ea88) on the write side; `replaceRange(0,15)`/`replaceRange(15,30)` on the receive side.
Candidates 43 and 67 do **not** exist as fragmentation constants here (43 is a readback offset).
The 4.0.8 candidate `subpackageLength()-5` has no analogue: 2.22 has no `subpackageLength`.
*One experiment to confirm anywhere:* capture one real D8 macro apply and count bytes between the
`A4` and the following `D8` — must be 15 (+5 header arithmetic).

**O-2 — D8 readback format/offsets → STILL UNKNOWN as a D8 format; PARTIALLY RESOLVED as a family.**
The device→app path in 2.22 uses fixed-offset blob parsing (`GamepadParam`,
`GamepadParam30`), with a byte-swapped 32-bit read rendered as a hex string, but no D8-opcode
dispatcher and no macro parser exists. The `sublist(70,216)` bound in `GamepadParam30` is the
only place the number 216 (0xD8) occurs on the receive side and it is not an opcode test.
*One experiment:* apply a macro, then read the device notification stream and check whether any
notification has `data[4]==0xD8` at all — if none does, 2.22 genuinely has no D8 readback; if one
does, dump it and diff against the `GamepadParam*` offsets.

**O-3 — repeatTime unit → PARTIALLY RESOLVED: milliseconds, low confidence.**
The envelope default is `repeatTime = 200`; the macro editor's time dialog passes the macro
`interval`/`duration` fields through `ChangeTimeDialog("ms")` (0x8bf504, ref `pp+0x8178 "ms"`),
so at least the sibling macro timing fields are labelled ms in the UI. There is no scaling
constant applied to `repeatTime` anywhere on the path to the wire (it is copied byte-for-byte
into header bytes 8-9), so **the wire unit equals the UI unit** — but 2.22 never spells out that
the *repeatTime* field specifically is ms. *One experiment:* set repeatTime to 1000 and time the
observed repetition period on hardware; 1 s ⇒ ms, 1000 s/16.7 min ⇒ something else.

**O-4 — commit/terminator semantics (0x0A) → CONTRADICTED in 2.22; the terminator carries a count.**
There is no `0x0A` byte in the terminator. The terminator is
`A4 05 D8 <nfrags+1> <checksum>` — `05` is just the ordinary `segLen+5` arithmetic for an empty
segment (`r17 = 10` raw → Dart 5, 0x79eb7c) and byte 3 is `nfrags + 1` (`add x1, x3, #1`,
0x79ec24, appended at 0x79eca8). `nfrags` itself comes from the A-frame header word (0x79ec08).
So in 2.22 the "commit" byte means *total fragment count expressed as nfrags+1*.
If 4.0.8 really transmits `0x0A`, the encoding changed between 2.22 and 4.0.8 — the two must not
be merged. *One experiment:* capture a 2.22 macro apply and a 4.0.8 macro apply and compare the
final A4 frame byte-for-byte.

**O-5 (new, 2.22-only) — the extra payload byte.** `writeMacroConfig` concatenates one integer
context element with the `changeGamepadDef` output (0x79e1ec → 0x79e8b4). The element is almost
certainly `runKey` (the 4th argument at the call site, 0x7a66dc/0x7a66f0), but the *list `+`
operand order is not resolvable from the decompilation*, so whether the byte is a prefix or a
suffix of the D8 payload is UNKNOWN. This directly affects the CRC range and the len field, and
therefore any replay. *One experiment:* replay the two candidate payloads (prefix vs suffix) with
the device and see which one is accepted, or read back a stored macro and check the first/17th byte
against the runKey.

**O-6 (new, 2.22-only) — receive ordinal mapping.** `data[6]==2 → offset 0` and `data[6]==4 →
offset 15` (0x8a6a98-0x8a6bb4). Whether the ordinal is "index+2" and only ever even, or a
half-index, is UNKNOWN. *One experiment:* capture a multi-fragment notification burst and look at
`data[6]` for successive fragments.

**O-7 (new, 2.22-only) — "disable/all-zero frame".** 2.22 always emits a `GamepadDefMap` with
`type = 0x80` even for a zero-duration, zero-key step, so the 4.0.8 "disable = all-zero frame"
rule has no visible 2.22 counterpart. UNKNOWN whether a zeroed 7-byte record is a valid disable.

---

## 6. (f) Names / strings present in 2.22 that later builds lost

2.22 is **much more legible** than 4.0.8 on this code path:

1. **Semantic response-handler names** in the UI: `addMacroResponse`,
   `changeMacroRunkeyResponse`, `changeMacroRepeatResponse`,
   `changeMacroUseRepeatTimeResponse`, `changeMacroInUseResponse`. These map 1:1 onto the
   envelope fields `runKey / isRepeat / repeatTime / inUse`, i.e. the UI names the protocol
   fields. 4.0.8's tree has no equivalent handler set on the macro path.
2. **Pool field symbols survive**: `Field <GamepadDef.len|gpatt|map>`,
   `Field <GamepadAtt.type|setting|key|att|d>`, `Field <GamepadDefMap.type|time|key>`
   (`pp.txt` 54008-54020). These name the exact bytes of the D8 header and the 7-byte record,
   including `GamepadDefMap.time` — which is what pins the `/8` granularity.
3. **Inline late-field error handlers** (`r9 = len`, `r9 = gpatt`, `r9 = type`, `r9 = setting`,
   `r9 = key`, `r9 = att`, `r9 = d` at 0x79d044-0x79d0c0) act as a per-field name table inside
   the serializer. Reading them off is how the header byte semantics were assigned.
4. **`runKeyName`** (`[pp+0x45418]`, default `"M1"`) exists as a first-class envelope field in
   2.22; it is a UI-only label but confirms `runKey` is a *named trigger key*, not an opaque code.
5. No obfuscation of the macro widget class names: `_ArmorXProMacroWidget`,
   `_ArmorXProMacroWidgetState`, `navigatorToMacroSetting`, `_RainbowMacroConfigWidgetState`.

---

## 7. Raw command / output tails for the key claims

```
$ cd static/blutter/2.22.0901/blutter_out/asm/moojiang
$ grep -rn 'subpackageLength\|mtu\|Mtu\|MTU' . | head -20
(no output)
```
```
$ grep -n 'Field <GamepadAtt\.\|Field <GamepadDef\.\|Field <GamepadDefMap\.' ../pp.txt
54008:[pp+0x456c8] Field <GamepadDef.gpatt>: late (offset: 0xc)
54011:[pp+0x456e0] Field <GamepadDef.map>: late (offset: 0x10)
54012:[pp+0x456e8] Field <GamepadDef.len>: late (offset: 0x8)
54013:[pp+0x456f0] Field <GamepadAtt.type>: late (offset: 0x8)
54014:[pp+0x456f8] Field <GamepadAtt.setting>: late (offset: 0xc)
54015:[pp+0x45700] Field <GamepadAtt.key>: late (offset: 0x10)
54016:[pp+0x45708] Field <GamepadAtt.att>: late (offset: 0x14)
54017:[pp+0x45710] Field <GamepadAtt.d>: late (offset: 0x18)
54018:[pp+0x45718] Field <GamepadDefMap.type>: late (offset: 0x8)
54019:[pp+0x45720] Field <GamepadDefMap.time>: late (offset: 0xc)
54020:[pp+0x45728] Field <GamepadDefMap.key>: late (offset: 0x10)
```
```
$ grep -n '#0x1b0$\|#0x148$' units/gamepadset.dart      # value -> enclosing function
2492 | 0x79e358 mov x17,#0x148 | writeMacroConfig body (line 2312)
2571 | 0x79e428 mov x17,#0x148 | writeMacroConfig body
2857 | 0x79e778 mov x17,#0x1b0 | writeMacroConfig body
3266 | 0x79ebf4 mov x17,#0x1b0 | writeMacroConfig body (terminator)
3977 | 0x7a040c mov x17,#0x148 | writeDeviceConfig body (line 3655)
4067 | 0x7a04f4 mov x17,#0x148 | writeDeviceConfig body
6888 | 0x7a7b04 mov x17,#0x148 | writeLightConfig body (line 6303)
7625 | 0x7a82e0 mov x17,#0x148 | writeLightConfig body
8317 | 0x7a8aa0 mov x17,#0x1b0 | writeLightConfig body
```
```
$ grep -rn 'mov  *x[0-9]*, #0x2b$\|mov  *x[0-9]*, #0x43$' .
./units/gamepadset.dart:13340: 0x7a2d4c: mov x1, #0x2b     (not fragmentation)
./units/gamepadset.dart:13907: 0x7a3414: mov x1, #0x43
./units/gamepadset.dart:13916: 0x7a342c: mov x4, #0x43
./units/gamepadset.dart:19404: 0x79dbfc: mov x0, #0x2b     -> sublist(43,102) in GamepadParam
$ grep -rn 'fmov  *d[0-9]*, #20.0' .
./units/component.dart:8293,8437,8581 ; ./units/theme.dart:718,818,...   (UI floats only)
```
```
$ grep -n 'r0 = applicationMacro()' widgets/armor-x_pro/armorx_pro_config_macro.dart
2434: 0x8bed24   (encl. _addMacroResponse, 1806)
4081: 0x8ac3b0   (encl. _changeMacroRunkeyResponse, 3599)
4184: 0x8ac4cc   (encl. _changeMacroRunkeyResponse, 3599)
4722: 0x8bfd18   (encl. _changeMacroRepeatResponse, 4242)
5224: 0x8c18c8   (encl. _changeMacroUseRepeatTimeResponse, 4778)
5726: 0x8be534   (encl. _changeMacroInUseResponse, 5280)
12909: 0x8bdfc4  (encl. [closure] void <anonymous closure>(dynamic), 12863)
```

Reload-verification commands for every addr in this document: search the asm file for the
`// 0x<addr>:` comment; Blutter emits one per instruction. Value-immediate calibration used
throughout: `#0x148`=328 raw ⇒ Smi 164 ⇒ byte 0xA4 (PROVEN by the write path storing byte
values into a `List<int>`), `#0x1b0`=432 ⇒ 0xD8, raw `#0xa` ⇒ Dart 5, raw `#0xf` ⇒ 15.
The read path compares an *unboxed* `List<int>` element, so its literals are the raw byte values
(`#0xa4`, `#0xd8`, `#0x1ac`=428⇒0xD6).

---

## 8. Late finding — frame arithmetic, the ordinal byte, and `subpackageLength()`

**(1) The terminator settles the frame shape.** The commit frame is built with exactly five
elements: `0x79eb7c` (len = 5), `0x79ebf4` (0xD8), `0x79ec24` (`nfrags + 1`, appended at
0x79eca8) and the checksum. Five bytes total with `segLen = 0` means the frame is
`A4 | len | D8 | ordinal | seg | csum` with `len = 5 + segLen`, and in the terminator the
ordinal slot holds **`nfrags + 1`** — i.e. the "commit" is expressed as *one past the last
fragment index*, not as a magic byte. PROVEN STATIC for the terminator.

**(2) This resolves the lab's `payload+5` vs `payload+4` discrepancy for 2.22.** `len` is
`segLen + 5` (`0x79e658 sub` / `0x79e65c add #5`) and the transmitted frame really is `5 + segLen`
bytes — the extra byte that makes the arithmetic close is the **ordinal byte at frame offset 3**
(proven to exist by (1)). The `payload + 5` form implemented in
`automation/scripts/armorx_lab/frames.py build_frag()` is therefore the correct one for 2.22;
the `payload + 4` form is the one that omits the ordinal. PROVEN STATIC (both operands).

**(3) `chunk = subpackageLength() - 5`.** 2.22 has no `subpackageLength()`; it hard-codes 15.
2.24 (`define.dart:477`, fn @0x7b9064) and 4.0.8 (`define.dart:316`, fn @0x819190) implement it
as a `curDevice.field_7` switch returning **20 (`#0x14`), 72 (`#0x48`) or 48 (`#0x30`)**.
`20-5 = 15`, `48-5 = 43`, `72-5 = 67` — exactly the three candidate chunk sizes under
investigation, and 2.22's hard-coded 15 is the `subpackageLength() == 20` class.
STRONG EVIDENCE (2.22 side proven; the per-device mapping read only by body inspection).
See `results/version-diff/d8-history.md`.

**(4) Residual uncertainty for data fragments.** The per-fragment ordinal *value* for
non-terminator fragments was not attributable to a single store in the decompilation (the frame
head is materialised through a 2-element array literal `[0xA4, …]` at `AllocateArray(2)`
0x79e350/0x79e364 with the length patched to 2, then appended to). It is PROVEN that the
position exists and what it holds in the terminator; whether the data fragments carry 1..N or
`i+2` is UNKNOWN (see O-6/O-8).

**(5) `nfrags` origin.** The terminator's ordinal is `LoadField r2->field_23 + 1` (0x79ec08,
0x79ec24) — i.e. the same counter used for the `ceil(N/15)` loop. PROVEN STATIC.

---

## 9. What could not be resolved, and why

* **Order of the extra payload byte** (O-5): Blutter does not name the operands of
  `_ListBase&Object&ListMixin::+` (0x79e8b4), and the two pushes (0x79e8ac/0x79e8b0) are
  symmetric. Needs either a hardware replay or a dynamic trace — both out of scope here
  (dynamic execution is owned by another workstream; the APK must not be run from this task).
* **Whether 2.22 has any D8 readback at all** (O-2): absence is provable, presence is not.
  Needs a live notification capture.
* **repeatTime unit** (O-3): no scaling constant exists on the path, so it is propagated
  verbatim, but the UI label evidence covers only the sibling interval/duration fields.
* **Receive ordinal semantics** (O-6): the dispatcher compares `data[6]` against 2 and 4 only in
  the two branches that were preserved; deeper branches were not exhaustively enumerated.
* **The `GamepadDefMap` record's split between key mask and stick pattern**: `applicationMacro`
  keeps the key bitmask and the stick word in two separate accumulators (0x7a5c38-0x7a5c60), but
  `changeGamepadDef` emits exactly one 32-bit word per record. Whether the second accumulator is
  merged into `key`, or is carried in a separate record/field, is **UNKNOWN** — the constructor
  argument order at 0x7a5c68 is not recoverable from the decompilation.
* **Whether the 4.0.8 "all-zero disable frame" applies** (O-7).
* Constants 20 and 67 are provably absent from the fragmentation code; 43/48/64/72 are provably
  readback-field bounds rather than chunk sizes. 2.23 not re-derived here (see `d8-history.md`).

## 10. Test vectors (statically derived)

Derived from the reconstructed layout with the CRC recomputed independently (Python,
CRC-16/MODBUS init 0xFFFF poly 0xA001 over payload bytes `[2:]`), `runKey = 46`,
`repeatTime = 200`, `att.type = 0`. Machine-readable in `d8-macro.json` → `test_vectors`.
These are **derived**, not captured; they are valid only if O-5 resolves to "no extra byte"
(they model the payload as header+records only).

| case | payload (hex) | nfrags | frames (ordinal `i+1` convention) |
|---|---|---|---|
| T1 1 step, 100 ms, key bit 0 | `11 FB 00 11 00 2E 2E 00 00 C8 80 00 0C 00 00 00 01` | 2 | `A4 14 D8 01 …5E` / `A4 07 D8 02 00 01 86` / `A4 05 D8 03 84` |
| T2 2 steps, 200/400 ms | `29 24 00 18 00 2E 2E 00 00 C8 80 00 19 00 00 00 01 80 00 32 00 00 00 02` | 2 | `A4 14 D8 01 …` / `A4 0E D8 02 …` / `A4 05 D8 03 84` |
| T3 zero step (disable attempt) | `D0 2A 00 11 00 2E 2E 00 00 C8 80 00 00 00 00 00 00` | 2 | `A4 14 D8 01 …` / `A4 07 D8 02 00 00 85` / `A4 05 D8 03 84` |
| T4 stick pattern for `k=0x23` | `05 AB 00 11 00 2E 2E 00 00 C8 80 00 0A 7F 00 00 00` | 2 | `A4 14 D8 01 …` / `A4 07 D8 02 00 00 85` / `A4 05 D8 03 84` |

Every frame is `5 + segLen` bytes (T1 frag0: `len = 20 = 15+5`; T1 frag1: `len = 7 = 2+5`;
terminator `A4 05 D8 03 84`: `len = 5 = 0+5`, opcode `0xD8`, ordinal `nfrags+1 = 3`, csum `0x84`).
Frames are emitted in the `ordinal = i+1` convention **and** the `ordinal = i` convention in the
JSON, because the data-fragment ordinal *value* is UNKNOWN (§8(4)); the terminator's ordinal is
PROVEN. All vectors are DERIVED (no hardware), and assume the payload has no extra element (O-5).