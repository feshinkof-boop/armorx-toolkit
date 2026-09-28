# Origin of the five pre-D2 ARMOR-X Pro requests (BIGBIG WON 4.0.8)

Git state at start: branch `research/physical-armorx-live-2026-09-27`, HEAD `9f57cc7edfc1d4a97a35a88b18d7b5fe3c22444f` (recorded once; no further git).

Static inputs used:
- 4.0.8 blutter: `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/...` (the `static/blutter/4.0.8/` dir is empty).
- Line numbers below are 1-indexed into those `*.dart` disassembly files.

## TL;DR — one-vs-many

**MULTIPLE INDEPENDENT REQUESTS**, split into two paths. It is *not* one single ordered
initialization state machine:

1. **EF → 0B → E2 is a reply-gated chain (a real 3-step state machine).** Each request is
   emitted from inside the *reply parser branch of the previous opcode*:
   - EF reply handler → calls `getZKMVer()` (emits `0B`)
   - 0B reply handler → calls `getDeviceParam()` → `readFirmware()` (emits `E2`)
   - E2 reply handler → only stores firmwareVer, emits nothing.
2. **D4 → D6 is a separate programmatic sequence**, fired from a *different page state*
   (`_RainbowDeviceConfig1sState`, the config tab), by one listener callback that runs
   `await getInputModel()` → `await Future.delayed()` → `await getDeviceConfig()`.
   Neither is gated on the E2 (or any) reply; D6 follows D4 only by fixed program order +
   a delay, not by a reply.

The wire order `EF→0B→E2→D4→D6` is therefore the interleaving of one gated init chain and
one independent config-tab init. (D6 also has other, post-config-write call sites — not the
pre-Button-Test one.)

## The Button-Test entry

`_ArmorXProMoreWidgetState::build` @ `0x940554` (`moojiang/widgets/armor-x-pro/armorx_pro_more.dart`
line 44) contains the "按键测试" (Button Test) tile @ `0x940684` (line 156) and the route
closure @ `0x94773c` (line 562). The Button-Test page itself is
`_RainbowTestState` in `moojiang/widgets/rainbow/rainbow_test.dart`.

D2 enable is emitted by `_RainbowTestState::initState` (see below), i.e. **when the Button
Test page opens** — confirming the five requests precede Button Test entry because they are
fired by the device page / config tab that host it, not because of an ordered machine.

## Evidence table

All emitters are methods of `BluetoothModel` (`package:moojiang/units/ble/bluetooth_mode.dart`).
Every emitter builds a Smi-tagged int array (blutter prints value×2), calls
`BluetoothModel::getCheckSum` @ `0x80fbbc`, writes the checksum into the last slot, then calls
`BluetoothModel::write` @ `0x80dd28` **and awaits it** (`AwaitStub` @ `0x4ecf8c`). `write()`
forwards to `flutter_blue_plus BluetoothCharacteristic::write` (find the `bl #0x80dd28` /
`bl #0x80de14` pairs).

| Request | Bytes | Emitter fn | Emitter addr | Emitter src | Array consts (raw / ÷2) | Awaited? |
|---|---|---|---|---|---|---|
| EF | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | `BluetoothModel::getDeviceUUID` | `0xacf618` | bluetooth_mode.dart:3973 | 330,24,478,0×8 → A5,0C,EF,0×8 | internal `AwaitStub` (0xacf72c) |
| 0B | `A5 04 0B B4` | `BluetoothModel::getZKMVer` | `0x8b61fc` | bluetooth_mode.dart:1042 | 330,8,22 → A5,04,0B | internal `AwaitStub` |
| E2 | `A5 04 E2 8B` | `BluetoothModel::readFirmware` | `0x8b6860` | bluetooth_mode.dart:1263 | 330,8,452 → A5,04,E2 | internal `AwaitStub` (0x8b6954) |
| D4 | `A5 04 D4 7D` | `BluetoothModel::getInputModel` | `0xa84258` | bluetooth_mode.dart:1850 | 330,8,424 → A5,04,D4 | internal `AwaitStub` (0xa8434c) |
| D6 | `A5 04 D6 7F` | `BluetoothModel::getDeviceConfig` | `0x80dbfc` | bluetooth_mode.dart:12 | 330,8,428 → A5,04,D6 | internal `AwaitStub` (0x80dcf0) |
| D2 on | `A5 05 D2 01 7D` | `BluetoothModel::testModeSwitch(true)` | `0xabaef4` | bluetooth_mode.dart:1954 | 330,10,420,2,250 → A5,05,D2,01,7D | internal `AwaitStub` (0xabb028) |
| D2 off | `A5 05 D2 00 7C` | `BluetoothModel::testModeSwitch(false)` | `0xabaef4` | bluetooth_mode.dart:1982-2041 | 330,10,420,0,248 → A5,05,D2,00,7C | internal `AwaitStub` |

Checksum proof (last byte = sum of preceding bytes & 0xFF):
`A5+0C+EF = 0x1A0 → A0`; `A5+04+0B = 0xB4`; `A5+04+E2 = 0x18B → 8B`; `A5+04+D4 = 0x17D → 7D`;
`A5+04+D6 = 0x17F → 7F`; `A5+05+D2+01 = 0x17D → 7D`.

| Request | Caller chain | Caller addr | Caller src | Awaited at caller? | Reply parser (opcode branch) | State written |
|---|---|---|---|---|---|---|
| EF | `_ArmorXProWidgetState::initState` closure(0xab903c) | call @ `0xab9068` | armorx_pro_root.dart:2817 | fire-and-forget | parser 0x8b6a18, branch opcode `0xEF` @0x8b6be8 (armorx_pro) / parser 0x8b5994 @0x8b5f88 (rainbow) | static `0xb68` = deviceUUID; then `devRegister()` |
| 0B | reply handler of EF: parser closure @ `0x8b6cc0` (armorx_pro) / @ `0x8b6084` (rainbow) | — | armorx_pro_root.dart:296; rainbow_root.dart:819 | fire-and-forget | parser 0x8b6a18 branch `0x0B` @0x8b6aa0 / parser 0x8b5994 @0x8b5c34 | static `0xb6c` = zkm version |
| E2 | from 0B reply branch → `getDeviceParam` @0x8b73a4 (armorx_pro) / parser @0x8b5cdc (rainbow) | call @ `0x8b73e0` | armorx_pro_root.dart:887; rainbow_root.dart:488 | fire-and-forget | parser 0x8b6a18 branch `0xE2` @0x8b6b30 / parser 0x8b5994 @0x8b5d34 | static `0xaf0` = firmwareVer |
| D4 | `_RainbowDeviceConfig1sState::initState` closure(0xa84160) | call @ `0xa841dc` | rainbow_tab_config_1s.dart:14616 | **AWAITED** (`AwaitStub` 0xa841e8) | parser 0x82684c branch `0xD4` @0x826ec8 | prints "板载mode = "+frame[4]; setState |
| D6 | same closure, after `Future.delayed` | call @ `0xa84238` | rainbow_tab_config_1s.dart:14653 | **AWAITED** (`AwaitStub` 0xa84244) | parser 0x82684c `frame[0]==0xA4` branch @0x82699c | static `0xb70` = protocolLength; `state.field_13` config buffer |
| D2 on | `_RainbowTestState::initState` closure(0xacf874) | call @ `0xacf8cc` | rainbow_test.dart:1754 | fire-and-forget | `analysisData` 0xacfa64 (gate frame[2]==0x02) | Button-Test UI state |
| D2 off | `_RainbowTestState::dispose` | call @ `0xadd844` | rainbow_test.dart:3660 | fire-and-forget | — | — |

### Caller-chain detail (quoted anchors)

- EF (armorx_pro): `armorx_pro_root.dart:2817` — `// 0xab9068: r0 = getDeviceUUID()` →
  `bl #0xab9084` (the page's own `_ArmorXProWidgetState::getDeviceUUID`, which then calls
  `BluetoothModel::getDeviceUUID`). Fired from initState 0xab8dec via a Future.delayed(500 ms)
  after `subscribeCharacteristic()` (closure 0xab8fb4 @ `armorx_pro_root.dart:2742`, its
  `Future.delayed(500000µs)` at line 2767).
- EF (rainbow_root): `rainbow_root.dart:4049` inside initState closure 0xacf53c, after
  `subscribeCharacteristic()`.
- 0B: the parser closures are `[closure](dynamic, List<int>)` and are **sync void** → the
  `bl getZKMVer` has no following `AwaitStub` (fire-and-forget).
- E2: `getDeviceParam` @0x8b73a4 is a sync (`/* No info */`, non-async) method; its last
  statement is `bl #0x8b6860` then `LeaveFrame` → fire-and-forget.
- D4/D6: closure 0xa84160 is `async`; each call is followed by `AwaitStub` → awaited, and D6
  is preceded by `Future.delayed` (`rainbow_tab_config_1s.dart:14628`).
- D2: closure 0xacf874 (sync void) does `bl #0xabaef4` then immediately `bl subscribeCharacteristic`
  → fire-and-forget.

### Reply-parser addresses / dispatch

- `BluetoothModel::notifyCharacteristicStream` @ `0x826814` (getter, returns `field_43`
  wrapped as `<List<int>>` `_BroadcastStream`). `BluetoothModel::onCharacteristicChanged` @
  `0xaca7c4` subscribes `lastValueStream` and re-broadcasts raw bytes via `field_43`; it does
  **not** parse.
- `_ArmorXProWidgetState::subscribeCharacteristic` @0x8b7400 listens on
  `notifyCharacteristicStream()` with closure **0x8b6a18** (`armorx_pro_root.dart:67`).
  Opcode = frame[2] (Smi-tagged read: `r16=4`). Branches: `0x0B`→zkm+getDeviceParam+getBatteryParam,
  `0xE2`→firmwareVer, `0xEF`→onGetDeviceUUID+getZKMVer+getMTU.
- `_RainbowWidget::subscribeCharacteristic` @0x8b5898 listens with closure **0x8b5994**
  (`rainbow_root.dart:193`). Same opcodes: `0x04`→setBattery, `0x0B`→zkm+readFirmware+getBattery,
  `0xE1..0xE4`→firmware/mtu, `0xEF`→onGetDeviceUUID+getZKMVer+getMTU.
- `_RainbowDeviceConfig1sState::subscribeCharacteristic` @0x8266a4 listens with closure
  **0x82684c** (`rainbow_tab_config_1s.dart:8880`). Branches: `frame[2]==0xD6` → print
  "首页监听D6："; `frame[0]==0xA4` → accumulate config fragments → `parsingData` @0x8270b0;
  `frame[0]==0xA5 && opcode==0xD4` @0x826d84/0x826ec8 → "板载mode"; `0x0E` @0x826d8c →
  "保存指令结果" → Timer→0x827f30; `0xD7` @0x826f78.

## State fields

- Static (index / annotation) written by replies:
  - `0xb68` = deviceUUID (EF reply; `onGetDeviceUUID` @0x8b6e18 line 447 `StoreStaticField(0xb68, r2)`).
  - `0xb6c` = zkm version (0B reply; armorx_pro 0x8b6ad4, rainbow 0x8b5c74).
  - `0xaf0` = firmwareVer (E2 reply; armorx_pro 0x8b6bdc/0x8b5e40).
  - `0xb70` = protocolLength (D6 A4-fragment parsing; 0x826aa4 `StoreStaticField(0xb70, r2)`).
  - `0xaf4` = `curDevice` (read in many init/tips branches).
- `BluetoothModel.field_43` = notify broadcast stream (source for every page parser).
- `_RainbowDeviceConfig1sState`: `field_13` = config byte buffer (append via `replaceRange`);
  `field_2b` = "collecting started" flag (set `true` in closure 0xa84160 @ line 14606);
  `field_27` = "saving" flag (set `false` on the `0x0E` reply, 0x826e44).
- `_ArmorXProWidgetState`/`_RainbowWidget`: `field_13`/`field_1b` = notify `StreamSubscription`.

### State fields Button Test (`_RainbowTestState`, rainbow_test.dart) reads
- `BluetoothModel.field_43` via `notifyCharacteristicStream` — `rainbow_test.dart:1816`
  (`LoadField: r2 = r0->field_43` inside `subscribeCharacteristic` @0xacf8fc).
- static `curDevice` (`0xaf4`) — `rainbow_test.dart:970` (`LoadStaticField(0xaf4)` in `build`).
- shared-singleton listener list — `rainbow_test.dart:1624` (`LoadStaticField(0x678)` in
  `initState`, to register the Delay-stream callback 0xacf874).
- its own state fields `field_1b` (subscription), `field_23/27/2b/2f` (UI/appbar state).
- `analysisData` @0xacfa64 gates on `frame[2]==0x02` (`cmp w0,#4` = tagged 2, line 1914),
  `sublist(3,7)` (`r16=14` tagged 7 line 1913-region), `Uint8List.fromList` + big-endian u32
  mask — matching the established Button-Test RX contract.

The shared singleton at static index `0x678` (listened to in initState by the device page,
the config tab, and Button Test; callback takes a `Duration`) is used app-wide. Its exact
class could not be resolved from the 4.0.8 dump (no `StoreStaticField(0x678)` and no
`InitLateFinalStaticField` annotation for it exists in the moojiang disassembly). See unknowns.md.

## Encode/write plumbing (shared by all six)

- `BluetoothModel::getCheckSum` @ `0x80fbbc` — computes the trailing checksum byte
  (`maxBy`/`& 0xFF`; emitters store its result at the last array slot).
- `BluetoothModel::write` @ `0x80dd28` — debug-prints `"写入"` + `printHex`, then calls
  `flutter_blue_plus BluetoothCharacteristic::write` @ `0x80de14` (fire `AwaitStub`).
- `printHex` @ `0x80f9c0` (gamepadset.dart).
