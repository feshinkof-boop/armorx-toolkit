# Opcode `0xD4` — four-build reconstruction (sender + receiver/parser)

Generated 2026-09-27 by the armorx-lab D4 reconciliation task.
Machine-readable companion: `d4-reconstruction.json` (same directory).

Evidence labels: **PROVEN STATIC** (byte-exact from the Blutter disassembly, checksum recomputed),
**STRONG EVIDENCE** (constant + frame context read by hand), **INFERRED**, **UNKNOWN**,
**CONTRADICTED**. Every claim cites file + function + address, and every constant states whether it
was halved from its Smi immediate.

## 0. The two decoding rules used here

1. **Smi halving (project convention).** A Dart integer used as a Dart *object* — a list element,
   an `==` operand, an `operator[]` index argument — appears in the disassembly as a tagged Smi
   `#0x(2V)`, so the Dart value is `immediate / 2`. A `cmp xN, #imm` that follows a
   `LoadInt32Instr` compares *untagged* values and is **never** halved. Every constant below records
   `halved → value` or `raw → value`.
2. **Index arguments are tagged too.** `mov x16, #4` before the `GDT[...] operator[]` call selects
   list index **2**, not 4. This is not an assumption: it is pinned against code that is already
   decoded — the `0xEF` parser (`_ArmorXProWidgetState::subscribeCharacteristic` @0x7ab44c, 2.22)
   reads whole-frame indices 3..10 with a *raw* loop counter (`add x5, x3, #3`, `cmp x3, #8`) to
   build the 8-byte UUID, and it reaches the opcode with arg `4`; the `0x0B` parser reads arg `6` →
   index 3, which is where the documented version byte lives (`A5 05 0B 30 E5`). The A4 branch of the
   2.22 dispatcher reads arg `6` → index 3, which is exactly where an A4 fragment index is.

Both rules matter: reading `r16 = 8` as "index 8" instead of "index 4" would move the D4 payload by
four bytes and invert the whole conclusion.

## 1. One-line answer

**0xD4 is a read whose reply is an `A5` short frame carrying a *gamepad/pad mode* byte at
whole-frame index 3 and an *onboard mode* (板载mode) byte at whole-frame index 4.** All four builds
send the identical request `A5 04 D4 7D`; the sender is renamed/relocated between builds
(`getOnBoardConfig` in 2.22.0901 and 2.24.0919, `getInputModel` in 2.23.0609 and 4.0.8) but the
reply layout and the field each parser updates are the same. The **frame structure is PROVEN**; the
**value domain of the two payload bytes is UNKNOWN**.

## 2. `InputModel` vs `getOnBoardConfig` — proven from the parser, not the name

The function names are misleading, so the verdict below is taken from the **receiver side only**:

| build | sender name | receiver proof that the reply carries an onboard mode |
|---|---|---|
| 2.22.0901 | `getOnBoardConfig` | 0x89bcac branch reads `data[4]` and stores it raw into `obj.field_1f` |
| 2.23.0609 | `getInputModel` | 0x8097cc branch reads `data[4]` and stores it raw into `obj.field_1f` |
| 2.24.0919 | `getOnBoardConfig` | 0x8a9824 branch **prints `"板载mode = "` + `data[4]`**, then stores raw into `field_1f` |
| 4.0.8 | `getInputModel` | 0x826ecc branch **prints `"板载mode = "` + `data[4]`**; 0x8b3d74 also reads it |

`板载mode` = **onboard mode**. The 2.24/4.0.8 string literal is the decisive evidence: it is inside a
branch that is entered only when the opcode field equals `0xD4`
(`2.24` : `0x8a9738 cmp x1,#0xd4;b.gt`, `0x8a9740 cmp x1,#0xe;b.gt`, `0x8a9824 cmp x1,#0xd4;b.lt`;
`4.0.8` : `0x826ecc cmp x1,#0xd4;b.lt`), so it cannot belong to another opcode.

The same frame additionally carries a `"手柄模式"` (**gamepad mode**) byte at index 3, printed and
compared in 2.23/2.24/4.0.8 (`== 6`). So `InputModel` and `getOnBoardConfig` name the **same thing**:
the device's current *onboard pad mode* (a mode selector that the firmware stores), read back for
display/state. Verdict on the candidate meanings:

| candidate | verdict | reason |
|---|---|---|
| active onboard **slot** | **CONTRADICTED** | the byte is stored raw or compared to a small constant; there is no bank/slot arithmetic, and 2.24/4.0.8 name it `板载mode`, not `板载配置槽` |
| **input mode** | **SUPPORTED** | that is literally what it is (板载mode / 手柄模式) |
| **config bank** | **CONTRADICTED** | no bank-selection arithmetic on the value anywhere in any of the four trees |
| **profile number** | **UNKNOWN** | no profile lookup on the value was found |
| **device mode** | **SUPPORTED** | the literal names it a mode; the "device" here is the controller's onboard/NVM mode |

## 3. Senders (per version)

Every builder is the *same four-element list literal* and the *same checksum*, so the exact frame is
identical in all four builds: **`A5 04 D4 7D`** (PROVEN STATIC; `0x7D = (0xA5+0x04+0xD4+0x00)&0xFF`).

### 2.22.0901 — `_ArmorXProConfigWidgetState::getOnBoardConfig` closure @0x89adac
`asm/moojiang/widgets/armor-x_pro/armorx_pro_config_config.dart` (outer method @0x89ac50):

```
0x89ae04 AllocateArray(size #8)        #8 = Dart 4 elements   → halved
0x89ae0c mov x17, #0x14a   → 330/2 = 0xA5   (halved, Smi)
0x89ae14 mov x17, #8       → 4              (halved, Smi)      = total length
0x89ae1c mov x17, #0x1a8   → 424/2 = 0xD4   (halved, Smi)
0x89ae24 mov x17, #0       → 0              (raw; the checksum placeholder)
0x89ae60 bl 0x79c368 getCheckSum(list)     # units/gamepadset.dart:87 — sum of elements & 0xFF
0x89aeac ArrayStore list[3] = 0x7D
```

* **Caller**: `_ArmorXProConfigWidgetState::queryConfigListResponse` @0x8a83f4 —
  `0x8a8adc subscribeCharacteristic()` → `0x8a8aec getOnBoardConfig()` → `setState`.
* **Device guard**: none observed. **Firmware guard**: none observed.
* **Startup path**: the ARMOR-X Pro config page data-load path (after the config-list response),
  immediately **before** the `0xD6` config read. Not app launch. (Matches the live capture that saw
  `A5 04 D4 7D` then `A5 04 D6 7F`.)
* **Note**: this build names it `getOnBoardConfig`, **not** `getInputModel`.

### 2.23.0609 — `_RainbowMoreWidget::getInputModel` @0x8afa98
`asm/moojiang/widgets/rainbow/rainbow_more.dart` — identical literal at 0x8afad4..0x8afaf4
(`#0x14a`→0xA5, `8`→4, `#0x1a8`→0xD4, `wzr`→0), `getCheckSum` @0x761954, checksum stored at 0x8afb68.

* **Caller**: `_RainbowMoreWidget::initState` @0x8af430 → `subscribeCharacteristic()` @0x8af464 →
  `Future.delayed(...).then(<closure @0x8afa4c>)` @0x8afa78 → `getInputModel()`.
* **Device guard / firmware guard**: none observed.

### 2.24.0919 — `_RainbowTabConfig1sWidgetState::getOnBoardConfig` @0x91b988
`asm/moojiang/widgets/rainbow/rainbow_tab_config_1s.dart` — identical literal at
0x91b9c4..0x91b9e4, `getCheckSum` @0x78c360 (`define.dart`), stored at 0x91ba54.

* **Callers**: `_RainbowTabConfig1sWidgetState` closure @0x91bfe4 → `0x91c030 getOnBoardConfig()`
  then `0x91c050 getDeviceConfig()` (**D4 then D6** — exactly the live ordering), and
  `_RainbowMoreWidget` closure @0x91b8e0 → 0x91b92c.
* **Device guard / firmware guard**: none observed in the immediate callers.

### 4.0.8 — `BluetoothModel::getInputModel` @0xa84258
`asm/moojiang/units/ble/bluetooth_mode.dart` — identical literal at 0xa84288..0xa842a8,
`BluetoothModel::getCheckSum` @0x80fbbc (loop accumulates, then `0x80fc80 and w1, w0, #0xff`),
checksum stored at 0xa84318, then `BluetoothModel::write()` @0xa84328.

* **Callers**: `_RainbowMoreWidget` closure @0xace4b0 → 0xace58c, and
  `_RainbowDeviceConfig1sState` closure @0xa84160 → 0xa841dc.
* **Device guard (PROVEN STATIC, rainbow_more path only)**: 0xace50c..0xace538 requires
  `curDevice` ∈ {`devRainbow2Pro` (Obj!Device@b2ee81), `devRainbow3` (Obj!Device@b2edc1),
  `devGale2` (Obj!Device@b2ede1)} — read from `Field <::.curDevice>` (static, offset 0xaf4,
  pp+0xa318). **`devArmorX` is NOT in that set**, so that particular poll path is not the ARMOR-X one;
  the ARMOR-X/1s path is the `_RainbowDeviceConfig1sState` closure, which has no device guard.
* **Firmware guard**: none observed. **Startup path**: page-init + `Future.delayed` polling loop.

## 4. Receivers / parsers (per version)

### 2.22.0901 — listener @0x89b438 (registered at 0x89b344)
```
0x89b48c cmp x1,#0xa4          (raw)  → A4 family gate → 0x89b4b4 == 428 (Smi→0xD6)
0x89bc00 cmp x1,#0xa5          (raw)  → A5 family gate; else end @0x89bd68
0x89bc08..0x89bc28  opcode = data[2]   (arg 4 → index 2, halved)
0x89bc2c == 28  (Smi→14 = 0x0E)
0x89bc94 == 424 (Smi→212 = 0xD4)  ← the D4 case
0x89bd00 == 430 (Smi→215 = 0xD7)
D4 branch 0x89bcac..0x89bcfc:
0x89bccc r16=#8 → index 4 ; GDT operator[] ; LoadInt32Instr → raw byte
0x89bcf8 StoreField obj.field_1f = value          (obj = (ctx[0]).field_b.field_1b)
```
* buffer extraction: whole-frame **index 4**; no sublist/index offset beyond that.
* length assumptions: **none** (no length byte read, no bounds check) — index 4 must simply exist.
* endianness: single byte. enum/bitfield: none, stored raw.
* follow-up command: none. Checksum verification of the inbound frame: none observed.

### 2.23.0609 — two receivers
**(a) `_RainbowMoreWidget` listener @0x8af5e8** (registered 0x8af558):
```
0x8af63c cmp x1,#0xa5 (raw) ; 0x8af650 arg 4 → index 2 = opcode
0x8af67c cmp w1,#0x76   (Smi class-id test: the element is an int, not a boxed/int64)
0x8af688 cmp x1,#0xd4   (raw) ; b.gt → other opcodes
0x8af690 cmp w0,#0x1a8  (Smi→0xD4)                      ← the D4 case
D4 branch 0x8af698..0x8af7a4:
  * allocates ["手柄模式->", data[3]] , _interpolate, print   (arg 6 → index 3)
  * reads data[3] again, cmp x1,#6 (raw) → boolean
  * 0x8af77c StoreField obj.field_1f = (data[3] == 6)
  * if true → 0x8af79c getDpi()  ← FOLLOW-UP COMMAND
```
**(b) `_RainbowTabConfig1sWidgetState` listener @0x808be4**:
```
0x80971c cmp x1,#0xa5 (raw) ; 0x809730 arg 4 → index 2 = opcode
0x809768 cmp x1,#0xd4 ; 0x809770 cmp x1,#0xe ; 0x8097cc cmp x1,#0xd4 ; b.lt → D4 branch
D4 branch 0x8097cc..0x809820:
  0x8097f0 r16=#8 → index 4 ; 0x80981c StoreField obj.field_1f = data[4] (raw)
```

### 2.24.0919 — two receivers
**(a) `_RainbowMoreWidget` listener @0x91a320**: D4 branch 0x91a520..0x91a618.
Prints `"手柄模式->" + data[3]` (0x91a544); `0x91a5e0 cmp w0,#0xc` (Smi→6) → boolean;
`0x91a5f4 StoreField obj.field_1b`; if true → `0x91a614 getDpi()`.

**(b) `_RainbowTabConfig1sWidgetState` listener @0x8a91d0**: D4 branch 0x8a9820..0x8a98f4.
```
0x8a9738 cmp x1,#0xd4 (raw); b.gt
0x8a9740 cmp x1,#0xe  (raw); b.gt → 0x8a9820
0x8a9824 cmp x1,#0xd4 (raw); b.lt → end          ⇒ exactly 0xD4
0x8a9844 r17 = "板载mode = "  ← decisive naming evidence
0x8a985c / 0x8a98c8  r16=#8 → index 4
0x8a98f0 StoreField obj.field_1f = data[4] (raw)
```

### 4.0.8 — two receivers
**(a) `_RainbowMoreWidget` listener @0x8b5724**: D4 branch 0x8b3c84..0x8b3dd8. Reads **both** bytes:
```
0x8b3cc0 r16=#6 → index 3 ; cmp w0,#0xc (Smi→6) ; 0x8b3d54 field_1b = (data[3]==6)
0x8b3d74 r16=#8 → index 4 ; cmp w0,#6   (Smi→3) ; 0x8b3d9c field_1f = (data[4]==3)
if field_1b → BluetoothModel::getDpi            ← FOLLOW-UP COMMAND
```
**(b) `_RainbowDeviceConfig1sState` listener @0x8266a4**: D4 branch 0x826ecc..0x826f74.
Prints `"板载mode = " + data[4]` (0x826ee8, arg 8 → index 4), then re-reads index 4 and branches
back to 0x827020 with **no observable store** (Blutter emitted no StoreField for the second read).

## 5. Four-version comparison table

See `d4-reconstruction.json → comparison_table` for the machine-readable form. Summary:
`UNCHANGED` 6 rows (frame bytes, checksum algorithm, index-4 read, firmware guard, …);
`RENAMED` 4 rows (function name, owner class, checksum host, transport call);
`EXTENDED` 7 rows (dispatch idiom, index-3 read, both debug prints, updated field, follow-up command,
device guard); `REMOVED` 0; `UNKNOWN` 3 (value domains, exact real length).

## 6. Smallest evidence-supported D4 reply, with test vectors

```
A5 | 06 | D4 | <gamepad_mode> | <onboard_mode> | <checksum>
 0      1     2          3                4            5
checksum = (0xA5 + 0x06 + 0xD4 + byte3 + byte4) & 0xFF
```

* **PROVEN STATIC**: the frame is an `A5` short frame (every D4 gate tests `data[0] == 0xA5`), the
  opcode sits at index 2, the payload bytes are read at whole-frame indices **3 and 4**, and the
  trailing byte is a checksum computed as `sum(all bytes except the last) & 0xFF`
  (2.22 `getCheckSum` @0x79c368; 4.0.8 `BluetoothModel::getCheckSum` @0x80fbbc `and w1,w0,#0xff`).
* **PROVEN STATIC**: the length byte equals the total frame length — cross-checked on three known
  replies: `A5 05 0B 30 E5` (5 B), `A5 0C EF <8 uuid> <sum>` (12 B), `A5 05 D7 00 81` (5 B).
* **INFERRED**: the total length is **6** — the minimum that lets both index 3 and index 4 exist
  *and* still leaves a checksum at index 5. The device may send more; nothing in any of the four
  branches reads index ≥ 5 or asserts a length.
* **UNKNOWN**: the value domain of byte 3 (`手柄模式`, only the value `6` is proven distinguished —
  it gates a `getDpi` follow-up) and of byte 4 (`板载mode`, never compared except against `3` in
  4.0.8's rainbow_more). No enum, no name table, and no write path that *sets* either byte was found.

Test vectors (byte-exact, checksums recomputed in Python — 4.0.8 dialect and project rule):

| gamepad_mode (idx 3) | onboard_mode (idx 4) | reply bytes | checksum |
|---|---|---|---|
| `0x00` | `0x00` | `A5 06 D4 00 00 7F` | `0x7F` |
| `0x06` | `0x03` | `A5 06 D4 06 03 88` | `0x88` |
| `0x06` | `0x00` | `A5 06 D4 06 00 85` | `0x85` |
| `0x01` | `0x01` | `A5 06 D4 01 01 81` | `0x81` |

Request vector (all four builds): `A5 04 D4 7D` (`0x7D = (0xA5+0x04+0xD4)&0xFF`).

## 7. What is still missing (and therefore NOT guessed)

1. The **value domain** of bytes 3 and 4 for ARMOR-X. The peripheral must therefore obtain them as
   *chosen device state* (CLI parameters), exactly like `--device-uuid` / `--zkm-version`, and the
   defaults carry no research authority.
2. The **exact real reply length** (≥ 6 proven, exact value unknown).
3. Whether byte 3 is genuine reply payload or a sub-code the device sends first.
4. Whether the app validates the inbound checksum of a D4 reply (no verification observed).

Nothing in the reply *structure* required a guess; nothing in the reply *content* is presented as
researched.

## 8. Reproduce

```bash
# opcode census (Dart 0xD4 = Smi 0x1a8) in the four trees
grep -rn '#0x1a8' --include=*.dart <tree>/asm/moojiang/ | grep -E '(cmp|mov)\s+[wx][0-9]+,\s*#0x1a8'
# 2.19+/3.x dispatcher idiom (raw opcode compare)
grep -rn 'cmp\s*x[0-9]*,\s*#0xd4' --include=*.dart <tree>/asm/moojiang/
# locate the D4 branches by their debug strings
grep -rn '板载\|手柄模式' --include=*.dart <tree>/asm/moojiang/
```

Trees: `static/blutter/2.22.0901/blutter_out`, `/home/salamanka/armorx/re/blutter_out` (2.23.0609),
`/home/salamanka/armorx/re/v224/blutter_out` (2.24.0919),
`/home/salamanka/armorx-re/mygt408/blutter_out` (4.0.8).
