# D6 configuration read — does it change APPLICATION state the Button Test / D2 path depends on?

Build: **BIGBIGWON official Android app 4.0.8** (Dart AOT, Blutter asm tree
`/home/salamanka/armorx-re/mygt408/blutter_out/asm/`).
Lab branch at start: `research/physical-armorx-live-2026-09-27`, HEAD `9f57cc7`
(single `git status`/`git log` taken before any analysis; no further git commands).
Scope: **STATIC / LOCAL ONLY** — no hardware, no BLE, no network writes.

## Classification

```
D6_APP_STATE_DEPENDENCY_NOT_FOUND
```

Within the analysed 4.0.8 static surface, the Full-D6 config read does **not** write
any application state that the Button Test page or the D2 enable (`testModeSwitch`)
reads, checks, or is gated on.

**Critical framing (do not restate):** this is an *app-side* statement. It says the app's
Button-Test / D2 code has no app-state dependency on a prior D6 read. It says **nothing**
about whether the *device* requires a D6 read before it answers the D2 enable — that is a
device-side question and is out of scope of this analysis.

## End-to-end trace

### 1. D6 request encoder — `BluetoothModel::getDeviceConfig` @ `0x80dbfc`
`moojiang/units/ble/bluetooth_mode.dart:12`
```
AllocateArray(8); field_f = #0x14a (Smi -> 0xA5)
                  field_13 = #8   (Smi -> 0x04)
                  ArrayStore[0] = #0x1ac (Smi -> 0xD6)
                  field_1b = rZR  (checksum placeholder)
AllocateGrowableArray; length = #0xa/2 = 4  ->  frame [ A5 04 D6 <ck> ]
getCheckSum() @0x80fbbc  (sum mod 256) -> 0xA5+0x04+0xD6 = 0x17F -> 0x7F
store checksum at index 3 ; write() @0x80dd28
=> wire "A5 04 D6 7F"  (matches the established pre-D2 sequence)
```
`getDeviceConfig` has **no side effect on app state**: it builds the frame and calls
`write()`. It does not store a config, set a flag, or notify a listener. Called from six
sites, all in `widgets/rainbow/rainbow_tab_config_1s.dart` (lines 3592, 7672, 7976, 8501,
10746, 14654).

### 2. Reception / reassembly / config-object construction
The eight `A4 14 D6 NN` fragments are consumed **only by the config pages**, each of which
has its own `subscribeCharacteristic` closure + `parsingData`:
* `_RainbowDeviceConfig1sState::subscribeCharacteristic` closure @ `0x82684c`
  (`rainbow_tab_config_1s.dart`) — gate `frame[2]==0xD6` (`cmp w0,#0x1ac` @0x826894),
  prints `"首页监听D6："` @0x8268b4, computes `protocolLength = frame[12]<<8 | frame[14]`
  and stores it (`StoreStaticField(0xb70)` @0x826aa4, literal `"protocolLength===="` @0x826abc).
* `_ConfigsMainWidget484State::parsingData` @0xaad760, `_ConfigsMainWidget280State::parsingData`
  @0xaac980, `_ConfigsConfigWidgetState::parsingData` @0xac2200,
  `_FrameMacrosConfigWidgetState::parsingData` @0xac35ac.
Reassembly uses `_GrowableList::replaceRange` / `sublist` over the accumulated buffer,
and the parsed result is written via `_RainbowDeviceConfig1sState::setUserConfig` +
`::writeDevice` (`gamepadset.dart`), plus the app-global statics
`0xb5c`/`0xb60` (D6-written) and `0xb70` = `::protocolLength`.

**So D6-populated app state demonstrably exists** (e.g. `::protocolLength`, offset `0xb70`,
read by 18 app files — `define.dart`, `units/gamepadset*.dart`, `widgets/general/configs_config.dart`,
`widgets/rainbow/rainbow_tab_config_1s.dart`, …; positive control the scan works).

### 3. Button Test entry path
* More page built by `_ArmorXProMoreWidgetState::build` @ `0x940554`
  (`moojiang/widgets/armor-x_pro/armorx_pro_more.dart`). The `按键测试 / ボタンテスト /
  Button Test` `ListTile` @0x940684 is built **unconditionally**; the only branch in
  `build` is locale dispatch (`cmp x1,#0x3fc` / `#0x3fd`). **No state/field read at all.**
* `onTap` = AnonymousClosure **@ `0x94773c`** → `Navigator.push(MaterialPageRoute(
  builder: () => RainbowTest()))`; builder closure @0x947674 (`rainbow_more.dart`,
  resolved to `AllocateRainbowTestStub`). No state read.
* The gate that *does* guard opening the More page is in
  `_ArmorXProWidgetState` onTap closure **@ `0x948660`** (`armorx_pro_root.dart`): reads
  `BluetoothModel.field_3b` and compares against a `BluetoothConnectionState` instance
  (`cmp w1,w16; b.ne #0x948760`). That is the **BLE connection state**, not D6.

### 4. Button Test page state — `_RainbowTestState`
* `initState` **@ `0xacf744`**: loads framework static `0x678` (the same load appears in
  `flutter/src/widgets/heroes.dart`, `flutter/src/material/{ink_well,dropdown,scaffold}.dart`
  — a framework binding singleton) and registers closure **@ `0xacf874`**.
* Closure `0xacf874`: `ReadContext.read<BluetoothModel>()` → `testModeSwitch(true)`
  (`bl #0xabaef4` @0xacf8cc) → `subscribeCharacteristic()` (`bl #0xacf8fc` @0xacf8dc).
  No D6 read.
* `subscribeCharacteristic` **@ `0xacf8fc`**: `ReadContext.read<BluetoothModel>()` →
  `model.field_43` → wraps in `_BroadcastStream<List<int>>` → `.listen()`; stores the
  subscription in `state.field_1b`. `field_43` is `BluetoothModel`'s raw-notification
  broadcast controller, filled by `onCharacteristicChanged` @ `0xaca7c4` closure
  `0xacb7f8` (`model.field_43.add(data)` @0xacb870). **It carries raw BLE notify bytes,
  not a D6 config object.**
* `analysisData` **@ `0xacfa64`**, parser gate **@ `0xacfaac`** (`cmp w0,#4` → Smi 2, i.e.
  `frame[2]==2`): parses the incoming frame (`int.parse`, `Uint8List`/`Int8List.fromList`)
  and calls `State::setState` twice (@0xad0b30, @0xad0c7c). **Reads no config.**
* `build` **@ `0x9f6264`**: constructs `Key*Component` widgets + `ListView`/`Scaffold`; the
  only external read is static `0xaf4` = `::curDevice` (device-identity enum, used to pick
  the device `Image.asset`).
* `dispose` **@ `0xadd7e0`**: cancels `field_1b`, calls `testModeSwitch(false)` @0xadd844.
* `_RainbowTestState` ctor @ `0xb08fe0`: ~50 button-status fields, all `null`/`0`.
* Controller widgets `moojiang/units/keybutton.dart` (KeyABXY/DPad/Thumb/Linear/Button):
  **zero static-field accesses, zero calls into `bluetooth_mode` / config functions.**

**Every LoadStaticField/StoreStaticField in `rainbow_test.dart` is only:**
`rainbow_test.dart:970` (`0x9f6b98`, static `0xaf4` = curDevice) and
`rainbow_test.dart:1624` (`0xacf774`, static `0x678` = framework binding). None is a D6 field.
`armorx_pro_more.dart` has **no static-field access at all**.

### 5. D2 enable sender — `BluetoothModel::testModeSwitch` @ `0xabaef4`
Builds `[A5,05,D2,01,7D]` (or `[A5,05,D2,00,7C]`) from immediates, prints `"cmd: …"`, and
calls `write()`. **Reads no field of `this` beyond the receiver used for `write()`** — there
is no config field, null check, length check, or firmware/model value on this path.
`write()` @ `0x80dd28` touches only `model.field_3f` / `model.field_23` (the BLE
characteristic) and calls `BluetoothCharacteristic::write`.
The only branch in `testModeSwitch` is on its own bool argument; all five callers pass a
literal (`true` at 0xacf8cc; `false` in `dispose` at 0xadd844). Other call sites
(`config_stick_view.dart:585` / `:2380`, `gale_tab_keymap.dart:2950`) guard only on a
non-null captured context — **no D6 read at any of the five sites** (`gale_tab_keymap.dart`
even wraps the argument in `IsType_bool_Stub`).

## Why D6_APP_STATE_DEPENDENCY_NOT_FOUND and not UNKNOWN

The Button-Test / D2 path's *entire* external-state surface is finite and enumerated:
* static `0xaf4` = `curDevice` — set only by device-selection UI
  (`device_card.dart:1324`, `device_bottom_sheet.dart:2392/3659/3681/3702/3724`,
  `kb_dou_jiang_main_vm.dart:523`), never by D6;
* static `0x678` = framework binding;
* `BluetoothModel.field_43` = raw notify stream (from `onCharacteristicChanged`);
* `BluetoothModel.field_3b` = BLE connection state (the real entry gate);
* `_RainbowTestState`'s own button-status fields (written from the incoming frame).

D6-populated state exists and was located (`::protocolLength` @0xb70, statics 0xb5c/0xb60,
the page config objects) — the search has a positive control — and none of it appears in
that surface. The D2 enable function reads nothing. Every claim above is PROVEN STATIC with
cited address; the two inferences (identity of framework static 0x678, and that
`field_43`'s only producer is `onCharacteristicChanged`) are labelled below.

## Evidence grades

| # | Claim | Grade |
|---|-------|-------|
| 1 | `getDeviceConfig` @0x80dbfc encodes `A5 04 D6 7F` and has no app-state side effect | PROVEN STATIC |
| 2 | D6 fragments are consumed by config pages' `parsingData`; `::protocolLength` (0xb70) is D6-written @0x826aa4 | PROVEN STATIC |
| 3 | `::protocolLength` (0xb70) is read by 18 app files, none of them in the Button-Test/D2 path | PROVEN STATIC |
| 4 | `按键测试` ListTile is built unconditionally in `_ArmorXProMoreWidgetState::build` @0x940554 | PROVEN STATIC |
| 5 | Button-Test route @0x94773c reads no state | PROVEN STATIC |
| 6 | More-page entry gate is `BluetoothModel.field_3b == BluetoothConnectionState` (connection), not D6 | PROVEN STATIC |
| 7 | `testModeSwitch` @0xabaef4 reads no state; `write` @0x80dd28 touches only the characteristic | PROVEN STATIC |
| 8 | `rainbow_test.dart` reads only statics 0xaf4 and 0x678; `armorx_pro_more.dart` reads none; `keybutton.dart` reads none | PROVEN STATIC |
| 9 | `analysisData` gate is `frame[2]==2` and it reads no config | PROVEN STATIC |
| 10 | `BluetoothModel.field_43` is a raw-notify broadcast stream (`onCharacteristicChanged` @0xaca7c4 closure 0xacb7f8) | STRONG EVIDENCE (single producer observed) |
| 11 | framework static `0x678` is `WidgetsBinding`-style binding (identical load pattern in flutter framework files) | INFERRED |
| 12 | `curDevice` (0xaf4) is never written by a D6 handler | PROVEN STATIC (only 3 non-D6 setting files) |
| 13 | the 145-byte / 144-byte device D6 payload's byte layout | UNKNOWN (out of scope; not needed here) |

## What would falsify this classification

Any one of these would overturn `D6_APP_STATE_DEPENDENCY_NOT_FOUND`:
1. A `LoadStaticField`/`LoadField` in `rainbow_test.dart`, `keybutton.dart`,
   `armorx_pro_more.dart`, or `testModeSwitch` @0xabaef4 that resolves to a field written by
   the D6 handler (statics 0xb5c/0xb60/0xb70, or a config object member).
2. A branch in `_ArmorXProMoreWidgetState::build` @0x940554 (or its route @0x94773c) that
   skips the `按键测试` tile / route on a D6-derived value — not present in the analysed body.
3. `StoreStaticField(0xaf4)` (curDevice) appearing in any D6 parse path rather than only in
   the three device-selection files.
4. `BluetoothModel.field_43` being fed by the D6 parser rather than by
   `onCharacteristicChanged`'s `add(data)`.
5. In a **newer** build, a D6-config read inserted before the D2 send or before
   `subscribeCharacteristic` in the Button-Test path.

## Residual unknowns (do not affect the classification)
* Exact identity of framework static `0x678` (framework binding; inferred).
* The D6 144-byte payload's internal field map — not required to answer this question.
* Whether the **device** gates its D2 response on a prior D6 read (device-side; out of scope).
