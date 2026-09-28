# Macro path — full static trace (2.22.0901 / 2.23 / 2.24 / 4.0.8)

STATIC ONLY. Addresses are Blutter asm comment addresses; reload by searching the `// 0x<addr>:`
comment in the cited file. Trees: see `d8-reconciliation.md` §"Trees read".

Notation: `#0x148` inside a `List<int>` write path is a **tagged Smi** (Dart value 164 = byte `0xA4`);
`#0xf` / `#5` used as an unboxed arithmetic operand is the true value.

The D8 opcode family is a runtime **WRITE** family. Nothing here was executed.

---

## 1. Encode path (UI → object → serializer → D8 payload → fragmentation → BLE)

### 1.1 Hop 0 — UI entry points

| build | macro page(s) | file |
|---|---|---|
| 2.22 | `_ArmorXProMacroWidgetState` (ArmorX) + `_RainbowMacroConfigWidget` | `widgets/armor-x_pro/armorx_pro_config_macro.dart`, `widgets/rainbow/rainbow_tab_macro.dart` |
| 2.23 | same families | `widgets/rainbow/rainbow_tab_macro.dart`, `widgets/general/config_macros.dart` |
| 2.24 | `widgets/general/config_macros.dart` + new `widgets/general/frame_config_macros.dart` | — |
| 4.0.8 | `widgets/general/config_macros.dart` (**ArmorX**, contains the devArmorX + `macrosItemLen()==7` special case @`0x997d90`) + `widgets/general/frame_config_macros.dart` (other devices, calls `applicationFrameMacro` directly @`0x9ad0c0`) |

All macro-apply handlers funnel into **`applicationMacro`** (2.22: 7 call sites in
`armorx_pro_config_macro.dart`, 8 in `rainbow_tab_macro.dart`; 2.23: `changeMacroResponse`,
`addMacroResponse`, `changeMacroRepeatResponse`, `changeMacroInUseResponse`,
`changeMacroRunkeyResponse`, `changeMacroUseRepeatTimeResponse`; 2.24/4.0.8: config-macro dialog
closures). `frame_config_macros.dart` additionally calls `applicationFrameMacro` directly.

### 1.2 Hop 1 — `applicationMacro` (dispatch + legacy payload build)

2.22 `units/gamepadset.dart` (body closure @`0x7a56c4`) and 2.23 (line 463) have **no dispatcher**:
they build a `GamepadDef` with one `GamepadDefMap` per step and call `writeMacroConfig`.

2.24 (line 171, `0x7feb68`) and 4.0.8 (line 5028, `0x858f2c`) dispatch:

```
macrosItemLen()                       ; 4.0.8 0x858f78 / 2.24 0x7febdc
cmp x0, #0xa ; b.ne <legacy>          ; 4.0.8 0x858f7c/0x858f80 ; 2.24 0x7febe0
  == 10 -> applicationFrameMacro()    ; 4.0.8 0x858f9c ; 2.24 0x7fec0c
  != 10 -> synchronized(_lock, closure (0x859144 / 0x803728))
              -> changeGamepadDef()   ; 4.0.8 line 6819 ; 2.24 line 4651
              -> writeMacroConfig()   ; 4.0.8 line 6834 ; 2.24 line 4669
```

`macrosItemLen()` (4.0.8 `define.dart:1087`, `0x859014`; 2.24 `define.dart:131`) returns the
per-item record stride: devArmorX fw<40 → 7, fw≥40 → 6; other devices fw≥0x35 → 10,
0x31≤fw<0x35 → 6, else 7.

Legacy payload construction (proven in 2.22; same shape in the modern `!=10` closure):
step's changed-control list folded into key/stick accumulators (`k<=0x21` → `1<<k`;
`k in 0x22..0x31` → stick table `0x22..0x31`), then `GamepadDefMap {type=0x80, time=duration/8, key=…}`
(`0x7a5c9c`, `sdiv …,x,#8` @`0x7a5c80`), buffer `N = 7n + 10` (`0x7a6234`/`0x7a6238`/`0x7a623c`).

### 1.3 Hop 2 — payload serialization

**OLD (`changeGamepadDef`)** — 2.22 `0x79c894`, 2.23 `0x798b04`, and the 2.24/4.0.8 legacy branch
(4.0.8 line 7563, 2.24 line 4748). Emits per 2.22 §1.1 of `results/static/2.22.0901/d8-macro.md`:

```
off 0..1  crc16        CRC-16/MODBUS init 0xFFFF poly 0xA001 over bytes[2:], BE   (0x79cf10/0x79cf84/0x79d008/0x79d028)
off 2..3  length       N = 10 + 7n, BE                                            (0x79c960/0x79c994)
off 4     GamepadAtt.type                                                         (0x79d078)
off 5     runKey                                                                  (0x79d088)
off 6     runKey|5  (0 -> 5 substitution)                                          (0x79d098, 0x79ca70)
off 7     isRepeat                                                                (0x79d0a8)
off 8..9  repeatTime u16 BE                                                       (0x79d0b8)
off 10+7i GamepadDefMap record: [type=0x80][time u16 BE][key u32 BE]
```

**MODERN (`applicationFrameMacro`)** — 2.24 `0x7fec9c`, 4.0.8 `0x85c8c0`/`0x85c908`:
`N = 10n + 10` (4.0.8 `0x85cf5c mul #0xa`, `0x85cf64 add #0xa`); header bytes 4..9 as above but
**byte 4 = constant `0x00`** (`0x85d238` `StoreField … = rZR`); each step serialized by
`TranscribeFrame.toFrameCmd` (4.0.8 `units/transcribe_frame.dart:10`; 2.24 `:161`) into 10 bytes
`[(t8&0x0F)<<4][(t8>>4)&0xFF][key u32 BE][stick u32 BE]`, `t8 = duration_ms // 8` (12-bit,
max 32760 ms), inserted with `replaceRange(10+10i, 20+10i, …)` (`0x85d480`).

### 1.4 Hop 3 — fragmentation: `writeMacroConfig`

| ver | fn | chunk | ordinal |
|---|---|---|---|
| 2.22 | `0x79dfc8` (body `0x79e158`) | literal **15** (`fmov d1,#15.0` @`0x79e300`; `mul #15` @`0x79e50c`/`0x79e54c`; `sdiv #15` @`0x79ea88`) | `i+1` (`0x79e7a8`) |
| 2.23 | `0x797fa0` | literal **15** (`fmov d1,#15.0` @`0x7980fc`) | `i+1` @`0x798310` (STRONG EVIDENCE) |
| 2.24 | `0x7ffb5c` | `subpackageLength()-5` (`bl 0x7b9064` @`0x7ffbfc`; `sub x1,x0,#5` @`0x7ffc00`) | `i+1` (`0x7ffcf4`) |
| 4.0.8 | `0x85a670` | `subpackageLength()-5` (`bl 0x819190` @`0x85a6f0`; `sub x1,x0,#5` @`0x85a6f4`/`0x85a730`) | `i+1` (`0x85a7e8`) |

Fragment assembly (4.0.8 addresses, identical shape in all four):
```
0x85a748 mov x16,#0x148    -> byte 0xA4
0x85a820 sub x1,x10,x8; 0x85a824 add x10,x1,#5    -> length byte = segLen+5
0x85a8f8 mov x16,#0x1b0    -> byte 0xD8
0x85a7e8 add x9,x6,#1      -> ordinal i+1
getCheckSum = sum(all preceding bytes) & 0xFF, appended last
```

Commit / terminator (identical in all four):
```
2.22  0x79eb7c (#0xa = Smi 5)  0x79ebf4 (0xD8)  0x79ec08 field_23  0x79ec24 add x1,x3,#1  0x79eca8 append
2.23  0x798744 (#0xa)          0x7987a0        0x7987a8 add x1,x4,#1
2.24  0x80012c (#0xa)          0x800188        0x800190 add x1,x4,#1
4.0.8 0x85aba8 (#0xa)          0x85abf0        0x85abf8 add x5,x2,#1   0x85ac3c BoxInt64
   -> A4 | 05 | D8 | nfrags+1 | sum8        (5 bytes total)
```

Inter-fragment delay 4 ms (2.22 `r17=4` @`0x79edf4`, INFERRED as ms). Then `writeDevice()` writes to
FFE1.

### 1.5 Ack

There is **no dedicated D8 ack parser**. The write is fire-and-forget on the write side; the device's
answer, when it comes, rides the notification path in §2. 4.0.8/2.24 print `"写入结果"` on a `0xD8`
notification; 2.22/2.23 have no such branch.

---

## 2. Decode / readback path

### 2.1 Generic A4 reassembler (present in all four)

| ver | site |
|---|---|
| 2.22 | `widgets/general/configs_config.dart` closure `0x8a6a04`: `cmp x1,#0xa4` `0x8a6a58`; opcode byte 2; **stride 15** (`replaceRange` offsets 0,15,30,45,60,75 @ `0x8a6b28`…, odd immediates ⇒ not Smis) |
| 2.23 | `widgets/general/configs_config.dart` (`cmp x1,#0xa4`); `parsingData` @`0x8098cc` |
| 2.24 | `widgets/general/configs_config.dart` @`0x912d30` (`cmp w0,#0x148`), @`0x912d58` (`cmp w0,#0x1ac`); stride `subpackageLength()-5` |
| 4.0.8 | `widgets/general/configs_config.dart` @`0xac1de8`, @`0xac1e10`; `subpackageLength(); sub #5` @`0xac1eec/0xac1ef0` |

Index convention (proven): the accessor immediates are tagged Smis — 4.0.8 `0xac1e4c mov x16,#12`
and `0xac1e80 mov x16,#14` build an adjacent BE pair ⇒ bytes 6 and 7. Therefore **opcode = byte 2,
ordinal/compare = byte 3**, matching the live `A4 14 D6 <ordinal> …` frames.

### 2.2 D8 macro readback

| ver | status | chain |
|---|---|---|
| 2.22 | **ABSENT** (no `0xD8`/216 comparison under `widgets/`) | macros come from server JSON only (`MacroRow.fromJson`) |
| 2.23 | **ABSENT** for D8 | generic `parsingData` only |
| 2.24 | **PRESENT/PARTIAL** | closure `0x915a2c`: `list[2]` vs `0xFC`(`0x915a68`) / `0xD8`(`0x915a90` → `"写入结果"` + `printHex`) / `0xD3`(`0x915ad8` → `list[7]`,`list[8]`) → `parsingData 0x915c38` → `TranscribeFrame.fromConfigData 0x80163c` |
| 4.0.8 | **PRESENT/PARTIAL** | closure `0xac33b4`: `0xFC`(`0xac33e0`) / `0xD8`(`0xac3408`) / `0xD3`(`0xac3448`) → `parsingData 0xac35ac` → `fromConfigData 0x85e32c` → `changeTranscribeFrameToDefMacro` |

`parsingData` reads (4.0.8): `list[3]` compared with `field_23 - 2` (step-limit check
`0xac3620-0xac3638`, then `stopTranscribe` + `"宏步数已经超出限制"`); a u16 **little-endian** at bytes
15–16 (`0xac369c`, `0xac36c4`, `0xac3744-0xac375c`) multiplied by 8 ms and stamped into the last
frame's `time` (`0xac377c`). The `"最大步数"` print is in the **caller** (`0xac3568`), not inside
`parsingData`.

No dedicated "read macro" command exists in any build — the readback rides the D6 config blob and/or
the D8/D3 notifications.

---

## 3. Storage slots

* Macro records are **server-side JSON objects** (`MacroRow.fromJson`), with envelope fields
  `changed / id / inUse / runKey / runKeyName / isRepeat / repeatTime / macroName / macroJson`
  (2.22 default template @`0x92aa14`, `runKey=46` @`0x92aabc`, `repeatTime=200` @`0x92ab20`).
* BLE D8 is used only to **apply** the macro to the device (`applicationMacro` is called from the
  server-response handlers `addMacroResponse` / `changeMacro*Response` in 2.22/2.23).
* **No device-side macro slot arithmetic exists in any build** — this contradicts the old
  "onboard config bank / slot" reading; the only slot-like arithmetic in the corpus is the
  `subpackageLength()-5` chunking and the `field_23` step-limit counter.
* No D8 read of a stored macro could be found in 2.22/2.23, and in 2.24/4.0.8 the readback is a
  notification (D8/D3) rather than a request — so **how a device-stored macro is enumerated is
  UNKNOWN** (would need a live apply + notification capture).

---

## 4. Safety note (unchanged)

D8 is a runtime **write** family. Nothing in this branch contacted hardware; the only permitted live
sequence for this project remains `0B`/`EF`/`D6`, and a D8 write must not be exercised until a target
macro slot is proven empty / operator-selected.
