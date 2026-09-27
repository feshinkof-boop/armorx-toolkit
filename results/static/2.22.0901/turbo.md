# Turbo in BIGBIG WON **2.22.0901** — ARMOR-X Pro

APK sha256 `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`.
Source: Blutter AOT tree `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out`.
Smi rule for this dialect: `List<int>` element immediates are tagged (printed `2×value`); list
lengths / array indices / `AllocateContext` sizes are **plain**.

Evidence labels: PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN / NOT PRESENT.

---

## 1. Verdict

**2.22 ARMOR-X Pro turbo is CONFIG-RESIDENT** (not command-based). There is **no**
`sendAllTurboKeySpeed` and **no** `writeTurboClick` anywhere in the build (0 grep hits) — turbo is a
field pair inside the 144-byte config buffer:

| model field | owner | Dart object offset | type |
|---|---|---|---|
| `turboSpeedIdx` | `GamepadParam30` | **0x58** | `int` |
| `turboKey` | `GamepadParam30` | **0x5c** | `String` (hex, parsed as radix-16 u32) |

(`units/gamepadset.dart:17192/17193`; also referenced at `config_mapkey.dart:1013/1040/1340/1367`.)

## 2. Serialisation — `GamepadSet30.map` (PROVEN STATIC)

`GamepadSet30.map` @ `units/gamepadset.dart:11825` (`0x7a6d38` region; body `0x7a33xx-0x7a3fxx`)
builds the parameter list. The turbo fields are written at fixed parameter-list indices:

```
@0x7a34bc  LoadField r8 = pa->field_57          // turboSpeedIdx  (offset 0x58)
@0x7a34d4  r1 = 76  (#0x4c) ; cmp/bounds check
@0x7a34e8  r5 = 76  (#0x4c) ; ArrayStore list[76] = turboSpeedIdx        // plain index 76

@0x7a3514  LoadField r0 = pa->field_5b          // turboKey (offset 0x5c)
@0x7a3528  r16 = 32 ; int.parse(turboKey, radix: 16) -> u32
@0x7a3540  r1 = 0xFF000000 ; and ; lsr #24  -> list[77]                 // index 77 (plain)
@0x7a35e8  r16 = 32 ; parse again
@0x7a3600  r1 = 0x00FF0000 ; and ; asr #16  -> list[78]                 // index 78
@0x7a3674  r16 = 32 ; parse again
@0x7a368c  r2 = 0x0000FF00 ; and ; asr #8   -> list[79]                 // index 79
@0x7a3700  r16 = 32 ; parse again
@0x7a3718  r2 = 0x000000FF ; and            -> list[80]                 // index 80
```

⇒ **`turboKey` is a hex string parsed to a u32 and split MSB-first into parameter-list indices
77, 78, 79, 80**; **`turboSpeedIdx` is a raw int at index 76**. (The `#0x18`, `#0x10`, `#8` shift
amounts and the `#0xff_00_00_00`-style masks are **plain** ints — they are shift counts/masks, not
Smi values — so they read as 24/16/8/0xFF000000 directly. PROVEN STATIC.)

### Byte offsets in the 144-byte config
The 2.22 parameter list is the config body after a **4-byte header** (144 bytes total ⇒ 140
parameters), so **`config_byte = list_index + 4`**. This base offset is the one *proven* on the
later build (4.0.8: "indices 77..80 → config bytes 81..84"), and it is consistent here with a
144-byte `GamepadSet30` config. Carrying it over (historical evidence, **STRONG EVIDENCE**, not
independently re-derived for 2.22):

| config byte(s) | size | endianness | field |
|---|---|---|---|
| **80** | 1 | byte | turbo speed index (`turboSpeedIdx`) |
| **81–84** | 4 | **big-endian u32** | `turboKey` per-key turbo bitmask |

⇒ **2.22's turbo byte layout is identical to 4.0.8's** (byte 80 = speed, bytes 81-84 = turboKey u32 BE).

## 3. `turboKey` semantics — bit = key id (PROVEN STATIC)

`turboClick` @ `widgets/general/config_mapkey.dart:273` (`0x8c96b0`) shows the exact bit maths:

```
r3 = List<int>(20) [0x17,0x18,0x19,0x1a, 0,1,3,4, 0x10,0x11,0x12,0x13, 6,8,7,9, 0xd,0xe,0xa,0xb]
                       (pp.txt:57877)   // real ids: 23,24,25,26,0,1,3,4,16,17,18,19,6,8,7,9,13,14,10,11
r2 = 1
r1 = LoadInt32Instr( list[ keyIndex ] )     // untag
cmp x1, #0x3f ; b.hi <out-of-range>
lsl x0, x2, x1                              // x0 = 1 << keyId
orr x1, x5, x0                              // mask |= (1 << keyId)
StoreField pa->field_1f = x1                // turbo mask accumulated
```

⇒ **turbo bit index == key id** (same convention as the hardware key constants, §`key-id-table.md`).
The **turbo-eligible key set in 2.22 is exactly the 20 ids**
`{23,24,25,26} M1–M4, {0,1,3,4} A/B/X/Y, {16,17,18,19} D-pad, {6,8,7,9} LB/LT/RB/RT, {13,14} L3/R3,
{10,11} Select/Start`. (PROVEN STATIC for the list and the shift.)

**`turboSpeedIdx` range:** single config byte 0..255, interpreted as an index into an app-side speed
table. Real-world range/step and the preset table are **UNKNOWN** (the table is not in the bundle —
same gap as 4.0.8).

## 4. UI paths (controller turbo only)

| role | symbol | file:line | addr |
|---|---|---|---|
| per-key turbo toggle implementation | `_ConfigMapkeyWidgetState.turboClick` | `widgets/general/config_mapkey.dart:273` | `0x8c96b0` |
| toggle closure registered | `[closure] void turboClick(dynamic,int,bool)` | `widgets/general/config_mapkey.dart:4113` | `0x8c9a1c` call |
| label | `S::rainbow_newconfig_key_turbo` = **"Turbo"** | `generated/l10n.dart:4836` | `0x5a8c6c` (`pp+0x2bb28`) |

Turbo changes accumulate in `GamepadParam30.turboKey` (hex string) / `turboSpeedIdx` and are flushed
by writing the config block (`GamepadSet30.map` → `writeDeviceConfig`).

## 5. Controller-turbo vs keyboard-subsystem-turbo

**2.22 has no keyboard subsystem at all.** There is no `kb_doujiang` / keyboard package directory in
`asm/` (compare 4.0.8, which has `widgets/kb_doujiang/kb_dou_jiang_tab_*`), and no
`sendAllTurboKeySpeed`. ⇒ **all 2.22 turbo code is controller/gamepad turbo**; the
keyboard-subsystem turbo functions that exist in 4.0.8 are **NOT PRESENT** here. No separation is
needed for 2.22.

## 6. Comparison with 2.23 / 2.24 / 4.0.8

| aspect | 2.22.0901 | 2.23.0609 *(hist.)* | 2.24.0919 *(hist.)* | 4.0.8 *(hist.)* |
|---|---|---|---|---|
| storage model | **config-resident** | config-resident (`GamepadParam30.turboKey` @ **0x54**) | config-resident (`@0x5c`) | config-resident |
| `turboKey` object offset | **0x5c** | 0x54 | 0x5c | 0x5c |
| `turboSpeedIdx` object offset | **0x58** (a real field) | — (not named) | — (not named) | not a `GamepadParam30` field (global static) |
| config byte 80 = speed | **yes** (STRONG EVIDENCE via idx76, byte=idx+4) | byte offsets *UNKNOWN* | byte offsets *UNKNOWN* | **yes** (PROVEN, idx 76 → byte 80) |
| config bytes 81–84 = turboKey u32 BE | **yes** (STRONG EVIDENCE via idx 77–80) | *UNKNOWN* | *UNKNOWN* | **yes** (PROVEN) |
| bit convention | **bit == key id** | — | — | **bit == key id** (re-verified this pass) |
| `sendAllTurboKeySpeed` / `writeTurboClick` | **NOT PRESENT** | not present *(hist.)* | not present *(hist.)* | not present; only in the **keyboard** subsystem |
| turbo speed preset table | **UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |

**2.22 is the earliest build in which the ARMOR-X Pro turbo byte layout is directly visible, and it
matches 4.0.8 exactly** (byte 80 speed, bytes 81–84 u32-BE turboKey). This resolves the
"byte offsets UNKNOWN for 2.23/2.24" gap *for 2.22* and corroborates the 4.0.8 layout, but it does
**not** retro-actively prove 2.23/2.24 offsets (different object offset 0x54 in 2.23; no independent
2.23/2.24 evidence available here).

## 7. UNKNOWN / open

* the **turbo-speed preset table** behind `turboSpeedIdx` (values, UI label, slider range);
* device-side limits (max simultaneous turbo keys);
* whether bit *i* refers to the **physical** key index or the mapped function code (inferred from the
  20-id list that it is the config key id, since the list is the key-id space);
* 2.23/2.24 byte offsets (not derivable from 2.22 alone).