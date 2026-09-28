# State deltas around D2 — per version, with addresses

Scope: every state variable **read or written immediately before and after** the D2 enable
(`A5 05 D2 01 7D`) and the D2 disable (`A5 05 D2 00 7C`), for builds **4.0.8**, **2.24**, **2.23**, **2.22.0901**.

Grades: **PROVEN STATIC** · **STRONG EVIDENCE** · **INFERRED** · **UNKNOWN**. Addresses are code addresses in the
build's libapp AOT snapshot; the file each line lives in is stated per block. Since Dart AOT field names are stripped,
fields are named by their recovered offset (`field_<hex>`) exactly as blutter prints them — no names are invented.

Legend for the timeline columns: **P** = step before the enable · **E** = the enable itself · **A** = step after the
enable (subscribe) · **D** = dispose / disable.

---

## 1. 4.0.8

Root: `/home/salamanka/armorx-re/mygt408/blutter_out/asm/`

| # | variable | offset | read/written | step | address | how | grade |
|---|---|---|---|---|---|---|---|
| 1 | `_RainbowTestState` this | – | read | P | 0xacf744 | `initState` registers closure 0xacf874; **no D2 call here** | PROVEN STATIC |
| 2 | callback context → state | `field_f` | write | P | 0xacf770 | `stur w0,[x1,#0xf]` (closure captures `this`) | PROVEN STATIC |
| 3 | static callback list | – | write (append) | P | 0xacf7a8–0xacf838 | `AllocateClosureStub` + growable-list append | STRONG EVIDENCE |
| 4 | `_RainbowTestState.field_f` (BuildContext) | `field_f` | read | E | 0xacf8a4 | used as the Provider lookup context | PROVEN STATIC |
| 5 | `BluetoothModel` (via Provider) | – | read | E | 0xacf8c0 | `ReadContext.read` (`<BluetoothModel>` pp+0x75e0) | PROVEN STATIC |
| 6 | **D2 enable arg** | – | write | E | 0xacf8c8 | `r2 = true` (0x20) then `bl 0xabaef4` @0xacf8cc | PROVEN STATIC |
| 7 | `BluetoothModel.field_3f` | `field_3f` | read | E | 0x80dd64 | `->field_b->field_b`, `tst x1,#0x1e` @0x80dd78 | PROVEN STATIC |
| 8 | `BluetoothModel.field_23` (FFE1) | `field_23` | read | E | 0x80ddc8 | null-checked, then `BluetoothCharacteristic::write` @0x80ddfc | PROVEN STATIC |
| 9 | `BluetoothModel.field_43` (notify stream) | `field_43` | read | A | 0xacf960 | wrapped in `_BroadcastStream` @0xacf974 | PROVEN STATIC |
| 10 | `_RainbowTestState.field_1b` | `field_1b` | **write** | A | 0xacf9ac | subscription from `listen` @0xacf9a4 | PROVEN STATIC |
| 11 | `_RainbowTestState.field_27/2f/37/3f/47/4f/57` | various | write | A (frame) | 0xacfc24, 0xacfc78, 0xacfccc, 0xacfd20, 0xacfd74, 0xacfdc8, 0xacfe1c | per-key booleans | PROVEN STATIC |
| 12 | `State::setState` | – | call | A (frame) | 0xad0b30, 0xad0c7c | only on change | PROVEN STATIC |
| 13 | `_RainbowTestState.field_1b` | `field_1b` | read | D | 0xadd800 | cancel via classid dispatch @0xadd828 | PROVEN STATIC |
| 14 | `_RainbowTestState.field_1f` (BluetoothModel) | `field_1f` | read | D | 0xadd830 | `cmp w1,NULL` @0xadd838 gates the disable | PROVEN STATIC |
| 15 | `_RainbowTestState.field_1f` | `field_1f` | **write** | pre-D | 0xa54bdc | `didChangeDependencies` 0xa54b9c, `ReadContext.read` @0xa54bd4 | PROVEN STATIC |
| 16 | `BluetoothModel.field_27` (FFE2) | `field_27` | read | connect | 0xaca67c | passed to `onCharacteristicChanged` 0xaca690 | PROVEN STATIC |
| 17 | `BluetoothModel.field_3b` (connectionState backing) | `field_3b` | write | connect | 0x8b56bc | setter notifies listeners | PROVEN STATIC |

**Net effect of D2 enable on object state (4.0.8): none inside `testModeSwitch`.** 0xabaef4 builds the frame,
prints `"cmd: …"` (0xabaff0) and awaits `write()` (0x80dd28). The only state written around the enable is
`state.field_1b`, and that is written by the *subscribe* step, not by D2.

---

## 2. 2.24

Root: `/home/salamanka/armorx/re/v224/blutter_out/asm/` — page file `moojiang/widgets/rainbow/rainbow_test.dart`

| # | variable | offset | read/written | step | address | how | grade |
|---|---|---|---|---|---|---|---|
| 1 | `testModeSwitch` call | – | call | P | 0x91cfb4 | `initState` 0x91cf94, inline, not awaited | PROVEN STATIC |
| 2 | `subscribeCharacteristic` call | – | call | P | 0x91cfc0 | immediately after the enable | PROVEN STATIC |
| 3 | frame list | – | write | E | 0x91e3c4, 0x91e3cc, 0x91e3d4, 0x91e3e0, 0x91e3e8 | 0x14a,0xa,0x1a4,2,0xfa = A5 05 D2 01 7D | PROVEN STATIC |
| 4 | widget write closure target | `field_13` | read | E | 0x91e424 | `LoadField r3 = r2->field_13` (write closure) | STRONG EVIDENCE |
| 5 | async await of the write | – | await | E | 0x91e44c | `AwaitStub` | PROVEN STATIC |
| 6 | `_RainbowTestState.field_b` (widget) | `field_b` | read | A | 0x91d02c | null-checked (`NullCastError` @0x91d0a0) | PROVEN STATIC |
| 7 | `BleCharacteristic::notifyCharacteristicStream` | – | call | A | 0x91d048 | source stream for the listener | PROVEN STATIC |
| 8 | `_RainbowTestState.field_1b` | `field_1b` | **write** | A | 0x91d074 | subscription from `_AsBroadcastStream::listen` 0x91d06c | PROVEN STATIC |
| 9 | `_RainbowTestState.field_1b` | `field_1b` | read | D | 0x933698 | cancel via GDT `cid-0x7ca` @0x9336c0 | PROVEN STATIC |
| 10 | `state.field_b.field_b` (connection state) | – | read | D | 0x9336e0 | vs `Obj!DeviceConnectionState@9ef301` @0x9336e8 | PROVEN STATIC |
| 11 | `testModeSwitch1` | – | call | D | 0x9336fc | disable, gated | PROVEN STATIC |
| 12 | disable frame | – | write | D | 0x933748..0x933768 | 0x14a,0xa,0x1a4,rZR,0xf8 = A5 05 D2 00 7C | PROVEN STATIC |
| 13 | `state.field_113`-equivalent one-shot | – | read/write | build only | 0x8c3bc0 block | `Future.delayed` present in 2.24 `build` | PROVEN STATIC |

---

## 3. 2.23

Root: `/home/salamanka/armorx/re/blutter_out/asm/` — page file `moojiang/widgets/rainbow/rainbow_test.dart`

| # | variable | offset | read/written | step | address | how | grade |
|---|---|---|---|---|---|---|---|
| 1 | `testModeSwitch` call | – | call | P | 0x8b0520 | `initState` 0x8b0504, inline, not awaited | PROVEN STATIC |
| 2 | `subscribeCharacteristic` call | – | call | P | 0x8b0530 | immediately after the enable | PROVEN STATIC |
| 3 | frame list | – | write | E | 0x8b1dac, 0x8b1db4, 0x8b1dbc, (0x8b1dc8), 0x8b1dd0 | 0x14a,0xa,0x1a4,2,0xfa = A5 05 D2 01 7D | PROVEN STATIC |
| 4 | `_RainbowTestState.field_b` (widget) | `field_b` | read | A | 0x8b05a0 | `List_4` element 0 @0x8b05b0 + `field_1b` closure @0x8b05b8 | STRONG EVIDENCE |
| 5 | injected notify closure | – | call | A | 0x8b05c8 | `ClosureCall` → returns the stream | INFERRED |
| 6 | page subscription slot | – | write | A | inside 0x8b0550 | not a `state.field_*` reachable from the page closure | UNKNOWN |
| 7 | `_RainbowTestState.field_b.field_b` | – | read | D | 0x881a38 | vs `Obj!DeviceConnectionState@90dea1` @0x881a40 | PROVEN STATIC |
| 8 | page subscription cancel | – | call | D | 0x881a14 | `GDT[cid_x0 + -0x8de]()` (dispatch at 0x881a0c–0x881a1c) | PROVEN STATIC |
| 9 | `testModeSwitch1` | – | call | D | 0x881a54 | disable, gated | PROVEN STATIC |
| 10 | disable frame | – | write | D | 0x881aa4..0x881ac4 | 0x14a,0xa,0x1a4,rZR,0xf8 = A5 05 D2 00 7C | PROVEN STATIC |
| 11 | `state.field_113` one-shot | – | read | build only | 0x829638 block | 500 ms disconnected re-render, not on the D2 path | STRONG EVIDENCE |

---

## 4. 2.22.0901

Root: `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/` — page file `moojiang/widgets/rainbow/rainbow_test.dart`

| # | variable | offset | read/written | step | address | how | grade |
|---|---|---|---|---|---|---|---|
| 1 | `testModeSwitch` call | – | call | P | 0x8e1eb0 | `initState` 0x8e1e94, inline, not awaited | PROVEN STATIC |
| 2 | `subscribeCharacteristic` call | – | call | P | 0x8e1ec0 | immediately after the enable | PROVEN STATIC |
| 3 | async-op context | `field_f/1b/2b/2f` | write | E | 0x8e3aa8–0x8e3b3c | `testModeSwitch` 0x8e3a88 builds the async context | PROVEN STATIC |
| 4 | frame list | – | write | E | 0x8e3c44, 0x8e3c4c, 0x8e3c54, 0x8e3c5c, 0x8e3c64 | 0x14a,0xa,0x1a4,2,0xfa = A5 05 D2 01 7D | PROVEN STATIC |
| 5 | `state.field_1b` (widget) | `field_1b` | read | E | 0x8e3cc0 | `->field_b` @0x8e3cc8 = the write closure pair | STRONG EVIDENCE |
| 6 | injected write closure | – | call | E | 0x8e3cf8 | `ClosureCall`; `_awaitHelper` @0x8e3d28 awaits it | PROVEN STATIC |
| 7 | `state.field_1b` (widget) | `field_1b` | read | A | 0x8e22d0 | async_op 0x8e22a8, `->field_b` @0x8e22dc | STRONG EVIDENCE |
| 8 | injected notify closure | `field_1b` | call | A | 0x8e2308 | `ClosureCall` → returns the notify stream | PROVEN STATIC |
| 9 | `_RainbowTestState.field_10f` | `field_10f` | **write** | A | 0x8e2358 | `add x16,x1,#0x10f; str w0,[x16]` = subscription | PROVEN STATIC |
| 10 | `_RainbowTestState.field_10f` | `field_10f` | read | D | 0x95a87c | `add x17,x1,#0x10f` | PROVEN STATIC |
| 11 | subscription cancel | – | call | D | 0x95a8a4 | `GDT[cid_x0 + -0xfc1]()` | PROVEN STATIC |
| 12 | `state.field_b.field_b` | – | read | D | 0x95a8cc | vs `Obj!DeviceConnectionState@8fcb51` @0x95a8d0 | PROVEN STATIC |
| 13 | `testModeSwitch1` | – | call | D | 0x95a8e4 | disable, gated | PROVEN STATIC |
| 14 | disable frame | – | write | D | 0x8e1f24..0x8e1f48 | 0x14a,0xa,0x1a4,0,0xf8 = A5 05 D2 00 7C | PROVEN STATIC |
| 15 | `state.field_113` one-shot | `field_113` | read/write | build only | 0x945828 (read), 0x945840 (clear) | 500 ms disconnected re-render, not on the D2 path | PROVEN STATIC |

---

## 5. Cross-version summary of variable slots

| slot | 4.0.8 | 2.24 | 2.23 | 2.22.0901 |
|---|---|---|---|---|
| page subscription | `_RainbowTestState.field_1b` (0xacf9ac) | `field_1b` (0x91d074) | not reached from the page (0x8b0550) | `field_10f` (0x8e2358) |
| Provider/connection object | `BluetoothModel` via Provider → `field_1f` (0xa54bdc) | widget `field_b` (0x91d02c) | widget `field_b` (0x8b05a0) | widget `field_1b.field_b` (0x8e22dc) |
| write closure | `BluetoothModel::write` 0x80dd28 | widget `field_13` (0x91e424) | widget `field_b` element 0 (0x8b05b8) | widget `field_1b.field_b` (0x8e3cc8) |
| notify source | `BluetoothModel.field_43` (0xacf960) | `BleCharacteristic::notifyCharacteristicStream` (0x91d048) | injected closure (0x8b05c8) | injected closure (0x8e2308) |
| connection-state gate for disable | none — uses `field_1f != null` (0xadd838) | `field_b.field_b == DeviceConnectionState@9ef301` (0x9336e8) | `field_b.field_b == DeviceConnectionState@90dea1` (0x881a40) | `field_b.field_b == DeviceConnectionState@8fcb51` (0x95a8d0) |
| re-render one-shot | absent | present in build 0x8c3bc0 | present in build 0x829638 | `field_113` @0x945828/0x945840 |

## 6. Variables that are NOT touched around D2 (any version)

Established by exhaustive read of each D2 call chain (builder → write helper → dispose), so the negative is
PROVEN STATIC *for those functions* and only there.

* **mode flags** — no such field is read or written in `testModeSwitch` / `testModeSwitch1` in any build.
* **device feature flags** — `::curDevice` (static, offset 0xaf4) is compared only inside the generic write helper:
  4.0.8 0x8b4ecc vs `Obj!Device@b2ee81/b2edc1/b2ee61/b2ede1`; 2.23 0x4d0f30–0x4d0f5c vs
  `Obj!Device@90e481/90e461/90e441`. It selects the platform write call; it never changes the D2 frame and is not
  read on the D2 path.
* **firmware generation** — `getZKMVer` 0x8b61fc and `readFirmware` 0x8b6860 exist in 4.0.8 but are on unrelated
  paths. No firmware value is consulted before or after D2 in any build.
* **MTU / packet length negotiation** — no MTU call appears in any D2 builder or write helper.
* **checksum** — the D2 checksum is a hard-coded literal in every build (0xfa / 0xf8). 4.0.8's
  `BluetoothModel::getCheckSum` 0x80fbbc is *not* called by `testModeSwitch` (it *is* called by the other
  commands, e.g. `getConnectModel` 0xabd35c at 0xabd3d8) — PROVEN STATIC by the call list of 0xabaef4.
* **cached configuration state** — none of the cached-config objects (`getDeviceConfig` 0x80dbfc,
  `getInputModel` 0x84258, `getDpi` …) are read or invalidated by D2 in any build.
