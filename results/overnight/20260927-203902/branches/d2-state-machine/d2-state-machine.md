# D2 / Button-Test state machine — BIGBIG WON (`moojiang`) app

Static reconstruction from Dart AOT (blutter) disassembly. Four builds: **4.0.8**, **2.24**, **2.23**, **2.22.0901**.

Grades used on every claim: **PROVEN STATIC** · **STRONG EVIDENCE** · **INFERRED** · **UNKNOWN**.
Every address below was read out of the listed file in this session; raw lines are quoted in §7.
No symbol name or address in this document is invented.

> **Live correction (2026-09-27), applied throughout:** the button-status stream is **event-driven**.
> The official 4.0.8 app produced 155 valid `A5 12 02` frames while a key was held and **0 frames while idle**.
> **Zero idle frames is not a failure** and is not treated as one anywhere in this document — no state below
> is entered or exited *because* no frames arrived.

---

## 1. Source files (per-version disassembly roots)

| version | asm root | page file | connection file |
|---|---|---|---|
| 4.0.8 | `/home/salamanka/armorx-re/mygt408/blutter_out/asm/` | `moojiang/widgets/rainbow/rainbow_test.dart` | `moojiang/units/ble/bluetooth_mode.dart` |
| 2.24 | `/home/salamanka/armorx/re/v224/blutter_out/asm/` | `moojiang/widgets/rainbow/rainbow_test.dart` | `moojiang/units/ble/ble_characteristic.dart` |
| 2.23 | `/home/salamanka/armorx/re/blutter_out/asm/` | `moojiang/widgets/rainbow/rainbow_test.dart` | `moojiang/units/ble/ble_device_interactor.dart` |
| 2.22.0901 | `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/` | `moojiang/widgets/rainbow/rainbow_test.dart` | `moojiang/units/ble/ble_device_interactor.dart` |

Entry widget for all four is `_ArmorXProMoreWidgetState::build` in `moojiang/widgets/armor-x_pro/armorx_pro_more.dart`
(the "按键测试" / "Button Test" `ListTile`), which pushes `RainbowTest` as a `MaterialPageRoute`.

---

## 2. The 4.0.8 state machine (compact text)

```
S01 APP_DISCONNECTED
      | connect()  0xac9a88
      v
S02 APP_CONNECTED            initGattServices 0xaca0a8
                             FFE1 "0000ffe1-..." @0xaca208 -> BluetoothModel.field_23 @0xaca224
                             FFE2 "0000ffe2-..." @0xaca248 -> BluetoothModel.field_27 @0xaca268
      | gatt-ready continuation 0xaca690 -> onCharacteristicChanged 0xaca7c4
      v
S03 NOTIFY_ARMED   [4.0.8 ONLY at this point]          0xaca7c4
                             setNotifyValue() 0xaca818 ; lastValueStream().listen 0xaca850
                             forward closure 0xacb7f8 -> field_43 .add(frame) 0xacb870
                             (get notifyCharacteristicStream 0x826814)
      | Button Test tap: "按键测试" 0x940684 -> onTap closure 0x94773c -> MaterialPageRoute 0x9477a8
      v
S04 ROUTE_PUSHED             RainbowTest::createState 0xb08f98
      | createState -> _RainbowTestState ctor 0xb08fe0  (builds the key-mask table)
      | didChangeDependencies 0xa54b9c : Provider<BluetoothModel> -> state.field_1f  (store 0xa54bdc)
      v
S05 WIDGET_INIT
      | framework calls initState 0xacf744
      |   -> allocates closure 0xacf874 and appends it to a static callback list (post-frame callback)
      v
S06 INITSTATE_RAN            (initState itself sends NOTHING)
      | post-frame callback 0xacf874 fires
      |   ReadContext.read<BluetoothModel>() 0xacf8c0   (context = state.field_f)
      v
S07 D2_ENABLE_ISSUED         testModeSwitch(true) bl 0xabaef4 @0xacf8cc   ** not awaited **
      |   0xabaf24 tbnz w0,#4 not taken (arg true=0x20) -> enable branch
      |   literals 0x14a,0xa,0x1a4,2,0xfa  =  A5 05 D2 01 7D
      |   print "cmd: ..." 0xabaff0 -> BluetoothModel::write bl 0x80dd28 @0xabb01c -> Await 0xabb028
      v
S08 WRITE_FFE1               write() 0x80dd28
      |   init gate: field_3f -> field_b -> tst #0x1e 0x80dd78 (if clear: print "等待初始化完成", Await 0x80dda8)
      |   BluetoothCharacteristic::write on field_23 (FFE1)  bl 0x80ddfc @0x80ddfc
      v
S09 LISTENER_OWNED           subscribeCharacteristic() bl 0xacf8fc @0xacf8dc  ** not awaited **
      |   ReadContext.read<BluetoothModel> 0xacf95c -> field_43 0xacf960
      |   _BroadcastStream 0xacf974 -> .listen(closure 0xacf9dc) bl 0xc0c474 @0xacf9a4
      |   store subscription -> state.field_1b  0xacf9ac
      v
S10 PARSER_ACTIVE            listener closure 0xacf9dc
      |   type check  cmp w0,#0x172 @0xacfa28 (mismatch -> print)
      |   analysisData(frame) bl 0xacfa64 @0xacfa48
      v
S11 gate: analysisData 0xacfa64
      |   r16 = 4 (Smi 2) pushed as index arg @0xacfa98 -> frame[2]
      |   cmp w0,#4 (Smi 2) 0xacfaac ; b.ne 0xad0c80  -> FRAME_DROPPED (silent return)
      +---- pass ----> v
S12 FRAME_ACCEPTED
      |   range/sublist(3,7): r2=3 @0xacfad0, r16=14 @0xacfac4 -> bytes [3..6]
      |   Uint8List.fromList 0xacfaec ; _ByteBuffer 0xacfaf4 ; asByteData 0xacfb0c
      |   big-endian u32 via 0xff00ff00/0x00ff00ff/0xffff0000/0xffff swizzle 0xacfb48..0xacfb88
      v
S13 UI_UPDATED
      |   21 per-key booleans -> state.field_27/2f/37/3f/47/4f/57... (stores 0xacfc24..0xacfe1c)
      |   setState() bl 0x509900 @0xad0b30 (and @0xad0c7c) — only on change
      v
      (back to S10 on the next notification — event-driven)

S14 DISPOSE_ENTERED          dispose 0xadd7e0
      |   state.field_1b (subscription) 0xadd800 -> if non-null: cancel via classid dispatch 0xadd828
      |   state.field_1f (BluetoothModel) 0xadd830 -> if non-null (cmp NULL @0xadd838):
      v
S15 D2_DISABLE_ISSUED        testModeSwitch(false) bl 0xabaef4 @0xadd844  ** not awaited **
      |   0xabaf24 tbnz taken (arg false=0x30) -> disable branch 0xabaf88
      |   literals 0x14a,0xa,0x1a4,rZR(0),0xf8 = A5 05 D2 00 7C -> write() 0x80dd28
      v
S16 DISPOSED
```

Note the asymmetry that matters for anyone reproducing this: in 4.0.8 the **enable** is gated only by "the
post-frame callback ran"; the **disable** is gated by "a `BluetoothModel` was ever resolved".
Neither is gated on the connection state, and the enable is issued **before** the page's own listener exists.

---

## 3. Where the four builds differ (the per-version machine)

Identical in all four: the two frames (`A5 05 D2 01 7D` / `A5 05 D2 00 7C`), the enable before the subscribe,
the cancel-then-disable order in dispose, the 4-byte big-endian key mask from `frame[3..6]`, bit index == key id,
no acknowledgement awaited for either direction, no delay/timer on either path, and no firmware or device gate on D2.

| state | 4.0.8 | 2.24 | 2.23 | 2.22.0901 |
|---|---|---|---|---|
| notify armed at connect | **yes** — `onCharacteristicChanged` 0xaca7c4 from 0xaca690 | no | no | no |
| enable issued from | post-frame callback 0xacf874 (bl @0xacf8cc) | initState, inline (bl @0x91cfb4) | initState, inline (bl @0x8b0520) | initState, inline (bl @0x8e1eb0) |
| enable builder | `BluetoothModel::testModeSwitch` 0xabaef4 | `_RainbowTestState::testModeSwitch` 0x91e380 | `_RainbowTestState::testModeSwitch` 0x8b1d68 | `_RainbowTestState::testModeSwitch` 0x8e3a88 → async_op 0x8e3be4 |
| write path | `BluetoothModel::write` 0x80dd28 → FFE1 `field_23` | injected `BleCharacteristic` 0x91e424 → `writeCharacteristic` | injected `BleDeviceInteractor::writeCharacterisiticWithoutResponse` 0x4d0eb4 | injected interactor write closure via widget (ClosureCall 0x8e3cf8) |
| subscribe source | `BluetoothModel.field_43` broadcast stream (0xacf960) | `BleCharacteristic::notifyCharacteristicStream` 0x91d048 | widget-supplied notify closure (ClosureCall 0x8b05c8) | widget-supplied notify closure (ClosureCall 0x8e2308) |
| listener registered on | `_BroadcastStream.listen` 0xacf9a4 | `_AsBroadcastStream.listen` 0x91d06c | GDT listen inside 0x8b0550 | GDT `cid-0xf4a` listen 0x8e2344 |
| subscription stored at | `field_1b` 0xacf9ac | `field_1b` 0x91d074 | (page object, see §5) | `field_10f` 0x8e2358 |
| parser | `analysisData` 0xacfa64 | `analysisData` 0x91d130 | listener closure 0x8b0654 | listener closure 0x8e2408 |
| **inbound gate** | **`frame[2] == 2`** 0xacfaac | `frame[1] == 18` 0x91d168 (see §6 caveat) | `frame.length == 18` 0x8b06f4 | `frame.length == 18` 0x8e245c |
| D2 echo (5-byte `A5 05 D2 ...`) | dropped by the opcode gate | dropped by the length gate | dropped by the length gate | dropped by the length gate |
| dispose gate | `field_1f != null` 0xadd838 | `connectionState == connected` 0x9336e8 | `connectionState == connected` 0x881a40 | `connectionState == connected` 0x95a8d0 |
| disable builder | `testModeSwitch(false)` (same fn) | `testModeSwitch1` 0x93371c | `testModeSwitch1` 0x881a78 | `testModeSwitch1` 0x8e1efc |
| disconnected re-render (500 ms `Future.delayed`) | **absent** | present (build 0x8c3bc0) | present (build 0x829638) | present (build 0x945854, flag `field_113` 0x945828/0x945840) |

Confidence: every "absent" above is an exhaustive read of that function block, so absence is **PROVEN STATIC**
for the named function; the 2.24 gate operand is **STRONG EVIDENCE** (§6).

---

## 4. State variables touched immediately around the D2 enable / disable

Full per-version table with addresses: see **`state-deltas.md`**. Summary:

**Immediately BEFORE the D2 enable**

| version | variables read/written |
|---|---|
| 4.0.8 | `state.field_f` (BuildContext, 0xacf8a4) → `Provider.read<BluetoothModel>` (0xacf8c0); inside `write()`: `BluetoothModel.field_3f` → `field_b` bit `0x1e` (0x80dd78), `field_23` (FFE1, 0x80ddc8) |
| 2.24 | `state.field_b` → `field_b[0]` / `field_1b` closure (0x91e424); frame built 0x91e3c4..0x91e3e8 |
| 2.23 | `state.field_b` → `field_b[0]` / `field_1b` closure (0x8b05a0..0x8b05b8, ClosureCall 0x8b05c8); frame built 0x8b1dac..0x8b1dd0 |
| 2.22 | `state.field_1b.field_b` → element 0 + `field_1b` closure (0x8e22d0..0x8e22f4); frame built 0x8e3c44..0x8e3c68 |

**Immediately AFTER the D2 enable (entering the subscribe step)**

| version | variables written |
|---|---|
| 4.0.8 | `BluetoothModel.field_43` read (0xacf960); `state.field_1b` = subscription (0xacf9ac) |
| 2.24 | `BleCharacteristic::notifyCharacteristicStream` (0x91d048); `state.field_1b` = subscription (0x91d074) |
| 2.23 | page object's subscription slot (inside 0x8b0550); no `state.field_*` slot reached from the page closure |
| 2.22 | `state.field_10f` = subscription (0x8e2358) |

**At dispose (before the D2 disable)**

| version | variables read |
|---|---|
| 4.0.8 | `state.field_1b` (0xadd800, cancel), `state.field_1f` (0xadd830, gate) |
| 2.24 | `state.field_1b` (0x933698, cancel), `state.field_b.field_b` (0x9336e0, gate) |
| 2.23 | subscription slot cancel via GDT `cid-0x8de` (0x881a14), `state.field_b.field_b` → `DeviceConnectionState@90dea1` (0x881a38/0x881a40) |
| 2.22 | `state.field_10f` (0x95a87c, cancel `cid-0xfc1` 0x95a8a4), `state.field_b.field_b` → `DeviceConnectionState@8fcb51` (0x95a8cc/0x95a8d0) |

**Never touched around D2, in any build** (PROVEN STATIC by exhaustive read of the D2 call chain):
mode flags, device feature flags (`::curDevice` is only consulted inside the generic write helper —
4.0.8 0x8b4ecc, 2.23 0x4d0f30–0x4d0f5c — never by D2), firmware-generation checks
(`getZKMVer` 0x8b61fc / `readFirmware` 0x8b6860 exist in 4.0.8 but lie on other paths),
MTU, and the checksum (`testModeSwitch` hard-codes it; `getCheckSum` 0x80fbbc is not called from D2).

---

## 5. Gates present in one build and not in another

This is the direct answer to the "gate in one version but not another" question. Six differences exist; none of them
suppresses the first status event and none is a precondition that a correct controller must reproduce.

1. **Post-frame deferral of the enable — 4.0.8 only.** *(STRONG EVIDENCE)*
   `_RainbowTestState::initState` 0xacf744 contains **no call to `testModeSwitch`**; it only allocates closure
   0xacf874 and appends it to a static callback list. The enable lives in that callback (bl 0xabaef4 @0xacf8cc).
   In 2.22 / 2.23 / 2.24 the enable is issued **inline from initState** (0x8e1eb0 / 0x8b0520 / 0x91cfb4).
   Consequence: in 4.0.8 the D2 write is raced against the framework's frame scheduling; the other builds are not.

2. **Inbound-frame opcode gate `frame[2] == 2` — 4.0.8 only.** *(PROVEN STATIC)*
   0xacfaac. Every other build gates on the 18-byte length instead (2.24 0x91d168, 2.23 0x8b06f4, 2.22 0x8e245c).
   This is the hardening that makes 4.0.8 reject the 5-byte `A5 05 D2 …` echo *by opcode* rather than by length.

3. **Notification subscription owned by the connection, not the page — 4.0.8 only.** *(PROVEN STATIC)*
   4.0.8 arms the FFE2 CCCD at connect time (`onCharacteristicChanged` 0xaca7c4, `setNotifyValue` 0xaca818,
   called from the GATT-ready continuation 0xaca690) and the page merely listens to the already-live broadcast
   stream `field_43`. In the other three the page performs the subscription itself, **after** the enable.

4. **Disable gated on `connectionState == connected` — 2.22/2.23/2.24 only.** *(PROVEN STATIC)*
   0x95a8d0 / 0x881a40 / 0x9336e8 compare against a `DeviceConnectionState` instance and skip the disable on
   mismatch. 4.0.8 replaces this with a non-null check on the Provider-resolved `BluetoothModel` (0xadd838).

5. **500 ms "disconnected" re-render — 2.22/2.23/2.24 only.** *(PROVEN STATIC)*
   `Future.delayed(...).then(setState)` guarded by `connectionState == disconnected` and a `field_113` one-shot
   flag (2.22 0x94581c–0x945884; 2.23 build 0x829638; 2.24 build 0x8c3bc0). The 4.0.8 `build` block 0x9f6264
   contains **no `Future.delayed` call at all**.

6. **`write()` precondition bit `0x1e` — 4.0.8 only.** *(PROVEN STATIC)*
   0x80dd78 tests a bit on the init-state object and, when clear, prints `"等待初始化完成"` and awaits before writing.
   The other builds hand the frame straight to their injected closure.

Two gates that are **not** present in any build, despite being natural suspects: a "test mode already on" flag
(no field test exists before the enable in any of the four builders) and a firmware/device-model gate on D2.

---

## 6. Caveats and grades on the contested items

* **2.24 parser gate — STRONG EVIDENCE, not PROVEN.** `analysisData` 0x91d130 performs an indexed access
  (`mov x16,#2` argument at 0x91d154) and compares the result: `cmp w0,#0x24 ; b.ne 0x91e23c` (0x91d168/0x91d16c).
  Read with the same Smi tagging the dump uses for its own frame literals — `0x14a` = Smi 165 for byte `0xA5`
  (0x91e3c4) — this is `frame[1] == 18`, i.e. the same 18-byte gate as 2.22/2.23 expressed as an indexed byte
  compare. A raw reading (`frame[2] == 36`) is not fully excluded from the bytes alone. Both readings are recorded
  in `d2-state-machine.json` → `unknowns`.
* **Page-level write characteristic identity (2.22/2.23/2.24).** The page invokes a closure injected by
  `armorx_pro_more.dart`; the concrete GATT UUID bound to it cannot be recovered statically from the arguments
  propagated down the tree. FFE1 write / FFE2 notify is **STRONG EVIDENCE** (2.23 PRE-002 / 2.22 define.dart +
  app logcat) rather than proven for those closures.
* **`state.field_b` object identity (2.22/2.23/2.24).** INFERRED to be the `_RainbowTest` widget from its use
  sites; the field name is not recoverable from the AOT image.

---

## 7. Raw disassembly (quoted, with file paths)

**4.0.8 — enable, from the post-frame callback** (`/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart`)
```
    // 0xacf8b4: r16 = <BluetoothModel>
    // 0xacf8c0: bl              #0x80fcec  ; [package:provider/src/provider.dart] ::ReadContext.read
    // 0xacf8c8: r2 = true
    //     0xacf8c8: add             x2, NULL, #0x20  ; true
    // 0xacf8cc: r0 = testModeSwitch()
    //     0xacf8cc: bl              #0xabaef4  ; [package:moojiang/units/ble/bluetooth_mode.dart] BluetoothModel::testModeSwitch
    // 0xacf8dc: r0 = subscribeCharacteristic()
    //     0xacf8dc: bl              #0xacf8fc  ; [package:moojiang/widgets/rainbow/rainbow_test.dart] _RainbowTestState::subscribeCharacteristic
```
**4.0.8 — the gate** (same file)
```
    // 0xacfa98: r16 = 4
    //     0xacfa98: mov             x16, #4
    // 0xacfaa8: blr             lr
    // 0xacfaac: cmp             w0, #4
    // 0xacfab0: b.ne            #0xad0c80
```
**4.0.8 — dispose gate** (same file)
```
    // 0xadd800: LoadField: r1 = r2->field_1b
    // 0xadd828: blr             lr                     ; cancel subscription
    // 0xadd830: LoadField: r1 = r0->field_1f
    // 0xadd838: cmp             w1, NULL
    // 0xadd83c: b.eq            #0xadd848
    // 0xadd844: bl              #0xabaef4  ; BluetoothModel::testModeSwitch
```
**4.0.8 — both frames** (`/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/ble/bluetooth_mode.dart`)
```
    // 0xabaf24: tbnz            w0, #4, #0xabaf88     ; false -> disable branch
    // 0xabaf3c: mov             x16, #0x14a           ; A5
    // 0xabaf44: mov             x16, #0xa             ; 05
    // 0xabaf4c: mov             x16, #0x1a4           ; D2
    // 0xabaf54: mov             x16, #2               ; 01      => A5 05 D2 01 7D
    // 0xabaf5c: mov             x16, #0xfa            ; 7D
    ...
    // 0xabaf9c: mov             x16, #0x14a
    // 0xabafa4: mov             x16, #0xa
    // 0xabafac: mov             x16, #0x1a4
    // 0xabafb4: stur            wzr, [x0, #0x1b]      ; 00      => A5 05 D2 00 7C
    // 0xabafbc: mov             x16, #0xf8            ; 7C
    // 0xabb01c: bl              #0x80dd28  ; BluetoothModel::write
    // 0xabb028: bl              #0x4ecf8c  ; AwaitStub
```
**4.0.8 — write precondition + FFE1** (same file)
```
    // 0x80dd64: LoadField: r1 = r0->field_3f
    // 0x80dd78: tst             x1, #0x1e
    // 0x80dd80: add             x1, PP, #0x4f, lsl #12  ; [pp+0x4f068] "等待初始化完成"
    // 0x80ddd8: bl              #0x80f500  ; BluetoothCharacteristic::properties
    // 0x80ddfc: bl              #0x80de14  ; BluetoothCharacteristic::write
```
**4.0.8 — notify armed at connect** (same file)
```
    // 0xaca208: add             x16, PP, #0x4f, lsl #12  ; [pp+0x4f4e0] "0000ffe1-0000-1000-8000-00805f9b34fb"
    // 0xaca224: StoreField: r1->field_23 = r0
    // 0xaca248: add             x16, PP, #0x4f, lsl #12  ; [pp+0x4f4e8] "0000ffe2-0000-1000-8000-00805f9b34fb"
    // 0xaca268: StoreField: r1->field_27 = r0
    // 0xaca690: bl              #0xaca7c4  ; BluetoothModel::onCharacteristicChanged
    // 0xaca818: bl              #0xacabfc  ; BluetoothCharacteristic::setNotifyValue
    // 0xacb860: LoadField: r0 = r1->field_43
    // 0xacb870: bl              #0xbe95f0  ; [dart:async] _BroadcastStreamController::add
```
**2.22 — initState order and dispose gate** (`/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart`)
```
    // 0x8e1eb0: bl              #0x8e3a88  ; _RainbowTestState::testModeSwitch
    // 0x8e1ec0: bl              #0x8e2190  ; _RainbowTestState::subscribeCharacteristic
    // 0x95a87c: add             x17, x1, #0x10f          ; subscription field_10f
    // 0x95a8a4: GDT[cid_x0 + -0xfc1]()                   ; cancel
    // 0x95a8d0: add             x16, PP, #0x41, lsl #12  ; [pp+0x41ba0] Obj!DeviceConnectionState@8fcb51
    // 0x95a8e4: bl              #0x8e1efc  ; _RainbowTestState::testModeSwitch1
```
**2.23 — initState order, gate, dispose** (`/home/salamanka/armorx/re/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart`)
```
    // 0x8b0520: bl              #0x8b1d68  ; _RainbowTestState::testModeSwitch
    // 0x8b0530: bl              #0x8b0550  ; _RainbowTestState::subscribeCharacteristic
    // 0x8b06f4: cmp             x1, #0x12
    // 0x8b06f8: b.ne            #0x8b1bd0
    // 0x881a40: add             x16, PP, #0x47, lsl #12  ; [pp+0x47858] Obj!DeviceConnectionState@90dea1
    // 0x881a54: bl              #0x881a78  ; _RainbowTestState::testModeSwitch1
```
**2.24 — initState order, gate, dispose** (`/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart`)
```
    // 0x91cfb4: bl              #0x91e380  ; _RainbowTestState::testModeSwitch
    // 0x91cfc0: bl              #0x91cfdc  ; _RainbowTestState::subscribeCharacteristic
    // 0x91d048: bl              #0x78c55c  ; BleCharacteristic::notifyCharacteristicStream
    // 0x91d06c: bl              #0xa74914  ; [dart:async] _AsBroadcastStream::listen
    // 0x91d168: cmp             w0, #0x24
    // 0x91d16c: b.ne            #0x91e23c
    // 0x9336e8: add             x16, PP, #0x47, lsl #12  ; [pp+0x47708] Obj!DeviceConnectionState@9ef301
    // 0x9336fc: bl              #0x93371c  ; _RainbowTestState::testModeSwitch1
```
**Navigation entry (all four)** — `.../asm/moojiang/widgets/armor-x_pro/armorx_pro_more.dart`
```
4.0.8  // 0x940684: r0 = "按键测试"   ; 0x9477a8: bl #0x817990 ; AllocateMaterialPageRouteStub
2.24   // 0x78a7f4: r16 = "Button Test"  ; 0x78b324: bl #0x6f35e8 ; AllocateMaterialPageRouteStub
2.23   // 0x75fd24: r16 = "Button Test"  ; 0x760824: bl #0x6e37f0 ; AllocateMaterialPageRouteStub
2.22   // 0x92add8: r16 = "Button Test"  ; 0x92b584: bl #0x5c2028 ; AllocateMaterialPageRouteStub
```

---

## 8. Reproduction notes for a controller (derived, INFERRED)

Not a protocol claim — a consequence of the static picture above. In priority order:

1. Send `A5 05 D2 01 7D` on FFE1 **without waiting for anything**, then attach the listener (both builds before
   4.0.8 expect exactly that order; 4.0.8 relies on a stream that is already live).
2. Never treat the 5-byte `A5 05 D2 ...` echo as data — every build discards it (4.0.8 by opcode, the rest by length).
3. Expect frames **only while a control is actuated**; a silent idle window carries no information.
4. Parse `frame[2] == 0x02` if you want 4.0.8 semantics; parse `frame.length == 18` if you want the older builds'
   semantics. For valid frames both hold.
5. On teardown: cancel the listener first, then send `A5 05 D2 00 7C`.
