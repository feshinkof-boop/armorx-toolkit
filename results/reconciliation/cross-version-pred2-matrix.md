# Cross-version pre-D2 matrix — where the Button-Test pre-burst originates

Scope: static Dart AOT (Blutter) for BIGBIG WON builds **2.22.0901, 2.23.x, 2.24.0919, 4.0.8**.
Method: frame-exact reconstruction (`tools/2.22.0901/reconstruct_frames.py`) + opcode-tag scan
(`mov #(2*opcode)`) + caller/call-site extraction from the Blutter trees. No HCI timing is used as
evidence. Live facts are quoted only where the code cannot settle a cell, and are labelled LIVE.

Trees:
`armorx-lab/static/blutter/2.22.0901/blutter_out/asm`,
`armorx/re/blutter_out/asm` (2.23),
`armorx/re/v224/blutter_out/asm` (2.24),
`armorx-re/mygt408/blutter_out/asm` (4.0.8).

Grades: **PROVEN STATIC** > **STRONG EVIDENCE** > **INFERRED** > **UNKNOWN**.

## 1. The matrix

| Column | 2.22.0901 | 2.23 | 2.24 | 4.0.8 |
|---|---|---|---|---|
| **EF** (A5 0C EF …) present | YES | YES | YES | YES |
| EF emitter | root page `armorx_pro_root.dart` / `rainbow_root.dart` closure (addr **UNKNOWN**, opcode-tag present) | `_ArmorXProWidgetState::getDeviceUUID` **@0x791a30** / `_RainbowWidget::getDeviceUUID` **@0x7ff67c** | `_ArmorXProWidgetState::getDeviceUUID` **@0x7b4c48** / `_RainbowWidget::getDeviceUUID` **@0x8972a4** | `BluetoothModel::getDeviceUUID` **@0xacf618** |
| EF origin path | device/detail page | device/detail page | device/detail page | device/detail page (root `initState`: `@0xab9068` armorx / `@0xacf590` rainbow) |
| EF grade | STRONG EVIDENCE | STRONG EVIDENCE | STRONG EVIDENCE | PROVEN STATIC |
| **0B** (A5 04 0B …) present | YES | YES | YES | YES |
| 0B emitter | `getZKMVer` closure **@0x7ab7f8** (armorx) / **@0x7a9b8c** (rainbow) | `getZKMVer` **@0x7617f4** / **@0x800610** | `getZKMVer` **@0x78c208** / **@0x8975d4** | `BluetoothModel::getZKMVer` **@0x8b61fc** |
| 0B origin path | device/detail page (triggered by the EF response) | device/detail page (triggered by EF response) | device/detail page (triggered by EF response) | device/detail page: FFE2 dispatcher closure **@0x8b5994**, EF-response branch → `getZKMVer` **@0x8b6084** |
| 0B grade | STRONG EVIDENCE | PROVEN STATIC (frame-exact) | PROVEN STATIC (frame-exact) | PROVEN STATIC |
| **E2** (A5 04 E2 …) present | **ABSENT** | **ABSENT** | **ABSENT** | YES |
| E2 emitter | — | — | — | `BluetoothModel::readFirmware` **@0x8b6860** (verified: `field_13=8`→len 4, opcode tag `#0x1c4`→0xE2) |
| E2 origin path | — | — | — | device/detail page: FFE2 dispatcher, 0B-response branch (`>4,>=0xb`) → `readFirmware` **@0x8b5cdc** |
| E2 grade | PROVEN STATIC (absence: no `readFirmware`, no `#0x1c4` frame) | PROVEN STATIC (absence) | PROVEN STATIC (absence) | PROVEN STATIC |
| **D4** (A5 04 D4 …) present | YES | YES | YES | YES |
| D4 emitter | `_ArmorXProConfigWidgetState` closure **@0x89b16c** | `RainbowMoreWidget::getInputModel` **@0x8afa98** | `_RainbowTabConfig1sWidgetState::getOnBoardConfig` **@0x91b988** | `BluetoothModel::getInputModel` **@0xa84258** |
| D4 origin path | configuration initialisation | configuration initialisation | configuration initialisation | configuration initialisation (config tab) |
| D4 grade | STRONG EVIDENCE | PROVEN STATIC (frame-exact) | PROVEN STATIC (frame-exact) | PROVEN STATIC |
| **D6** (A5 04 D6 …; answers with eight A4 D6 fragments) present | YES | YES | YES | YES |
| D6 emitter | `_ArmorXProConfigWidgetState` closure **@0x89c3c8** / `_ConfigsConfigWidgetState` closure **@0x8a64b4** | `getDeviceConfig` **@0x810d2c** / **@0x8abc64** | `getDeviceConfig` **@0x8a8798** / **@0x91433c** | `BluetoothModel::getDeviceConfig` **@0x80dbfc** |
| D6 origin path | configuration initialisation / refresh | configuration initialisation / refresh | configuration initialisation / refresh | configuration initialisation / refresh (config tab; re-fired from `del/change/rename/addConfigResponse`) |
| D6 grade | STRONG EVIDENCE | PROVEN STATIC (frame-exact) | PROVEN STATIC (frame-exact) | PROVEN STATIC |
| **D2 pre-clear** (A5 05 D2 00 7C before Button Test?) | **NO** | **NO** | **NO** | **NO** |
| D2 pre-clear grade | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |
| **D2 enable** | A5 05 D2 01 7D — `_RainbowTestState::testModeSwitch` **@0x8e3a88** | A5 05 D2 01 7D — **@0x8b1d68** | A5 05 D2 01 7D — **@0x91e380** | A5 05 D2 01 7D — `BluetoothModel::testModeSwitch` **@0xabaef4** (frame `[0x14a,0xa,0x1a4,0x2,0xfa]`) |
| D2 enable grade | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |
| **D2 disable** | A5 05 D2 00 7C — `testModeSwitch1` **@0x8e1efc** (from `dispose` **@0x95a864**) | A5 05 D2 00 7C — **@0x881a78** (from `dispose` **@0x8819d0**) | A5 05 D2 00 7C — **@0x93371c** (from `dispose` **@0x93367c**) | A5 05 D2 00 7C — from `dispose` **@0xadd7e0** |
| D2 disable grade | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |
| **write type** (with evidence) | **write-without-response** — `BleDeviceInteractor::writeCharacterisiticWithoutResponse` **@0x9699b0** | **write-without-response** — `BleDeviceInteractor::writeCharacterisiticWithoutResponse` **@0x4d0eb4** | **write-without-response** (STRONG) — `BleCharacteristic::writeCharacterisiticWithoutResponse` **@0x89254c** | **UNKNOWN statically** — `BluetoothModel::write` **@0x80dd28** → flutter_blue_plus `BluetoothCharacteristic::write` (`withoutResponse` bool not resolvable). **LIVE (2026-09-27): ATT Write Command 0x52 on handle 0x0075 = write-without-response** |
| **notification owner** (FFE2) | Button Test **page** (`_RainbowTestState::subscribeCharacteristic` **@0x8e2190**) | Button Test **page** (`subscribeCharacteristic` **@0x8b0550**) | Button Test **page** (`subscribeCharacteristic` **@0x91cfdc**) | **connection handler** — `BluetoothModel::initGattServices` **@0xaca0a8** arms notify via `onCharacteristicChanged` **@0xaca7c4** (`setNotifyValue`) at connect; the page only adds a Dart listener (`@0xacf8fc`) |
| notification-owner grade | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |
| **parser gate** | `frame[1] == 0x12` (len 18) only; header/opcode/checksum unchecked (closure **@0x8e2408/0x8e2430**) | `frame[1] == 0x12` (len 18) only (**@0x8b0654**) | first comparison `0x24` (**@0x91d130**) — **UNKNOWN** (length 36 vs element compare) | `frame[2] == 0x02` (`cmp w0,#4` = Smi 2) **@0xacfaac**; parser `analysisData` **@0xacfa64** |
| parser-gate grade | PROVEN STATIC | PROVEN STATIC | UNKNOWN (one gate) | PROVEN STATIC |
| **connection gate** | disable gated on `DeviceConnectionState==connected` (dispose) | same | same | disable gated on Provider `BluetoothModel` connected; **and every write** (`BluetoothModel::write`) awaits the init-complete future (**"等待初始化完成"** @0x80dd80) |
| connection-gate grade | STRONG EVIDENCE | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |
| **configuration dependency** (Button Test requires prior config read?) | **NO** | **NO** | **NO** | **NO** |
| config-dep grade | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |
| **firmware gate** | none found | none found | none found | none found |
| firmware-gate grade | PROVEN STATIC (absence) | PROVEN STATIC (absence) | PROVEN STATIC (absence) | PROVEN STATIC (absence) |
| **timing behaviour** | enable issued unawaited, then page subscribes; no delay; 500 ms re-render timer for the disconnected state only | same | same | enable issued unawaited inside the `initState` closure **@0xacf874**, then `subscribeCharacteristic`; no delay. The **burst is response-chained** (each query is fired by the previous response), so it is serial and round-trip-gated |
| timing grade | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC | PROVEN STATIC |

## 2. The decisive structural finding

The pre-D2 burst — EF, 0B, E2, D4, D6 — is **NOT emitted by the Button Test page**.

`_RainbowTestState::initState` in **all four builds** calls exactly two things:

* `...::testModeSwitch` (the D2 enable), and
* `...::subscribeCharacteristic`.

Extracted initState call lists:
* 2.22 `@0x8e1e94`: `[_RainbowTestState::testModeSwitch, _RainbowTestState::subscribeCharacteristic]`
* 2.23 `@0x8b0504`: `[_RainbowTestState::testModeSwitch, _RainbowTestState::subscribeCharacteristic]`
* 2.24 `@0x91cf94`: `[_RainbowTestState::testModeSwitch, _RainbowTestState::subscribeCharacteristic]`
* 4.0.8 `@0xacf744` (closure `@0xacf874`): `BluetoothModel::testModeSwitch` + `_RainbowTestState::subscribeCharacteristic`

No `getDeviceUUID` / `getZKMVer` / `readFirmware` / `getDeviceConfig` / `getInputModel` call appears
anywhere in `rainbow_test.dart` in any build. **PROVEN STATIC.**

The emitters instead live in:

* the **device/detail root page** (`armorx_pro_root.dart`, `rainbow_root.dart`) — EF and 0B (and E2 in 4.0.8); and
* the **config tabs** (`armorx_pro_config_config.dart`, `configs_config*.dart`, `rainbow_tab_config_1s.dart`, `rainbow_more.dart`) — D4 and D6.

### The 4.0.8 burst is a response-chained bring-up (the reference case)

From the FFE2 dispatcher closure `rainbow_root.dart @0x8b5994` (opcode switch after
`cmp w0,#0x14a` header check):

* root `initState` → `BluetoothModel::getDeviceUUID` (**EF**) `@0xacf590`;
* EF response (`opcode 0xEF`, branch `>=0xEF` / `#0x1de` @0x8b5f90) → `onGetDeviceUUID` + `getZKMVer` (**0B**) `@0x8b6084`;
* 0B response (`>4 && >=0xb`, `print("zkm=")` @0x8b5c88) → `readFirmware` (**E2**) `@0x8b5cdc` + `getBattery` `@0x8b5d10`;
* `opcode 8` → `setBattery`; `0xE1..0xE4` → MTU. The config tab separately fires **D6**/**D4**.

The identical `"zkm="` dispatcher string is present in the 2.23 and 2.24 root files, so the same
response-chained structure is **STRONG EVIDENCE / INFERRED** there.

## 3. Generic application initialisation or D2-specific? — ANSWER

**GENERIC APPLICATION INITIALISATION.** The pre-D2 burst is what the app does on **any device-page
open**, unrelated to D2.

Code-structure reasons (no HCI timing used):

1. The Button Test page emits **none** of EF/0B/E2/D4/D6 — its initState emits only the D2 enable
   and its own subscription (PROVEN STATIC, all four builds).
2. The emitters are the device **root page** (EF/0B/E2) and the **config tabs** (D4/D6); these fire
   when the device page and its config data are brought up, whether or not Button Test is ever
   entered.
3. In 4.0.8 the queries are **chained to each other by their own responses** (EF→0B→E2), i.e. a
   self-contained device-identification handshake, not a step of the D2 toggle.
4. The D2 feature itself is a **single self-sufficient toggle**: one 5-byte frame on enable, one on
   dispose; no preceding query, no ack, no config read, no firmware/device gate (PROVEN STATIC).

Consequence: the observed EF/0B/E2/D4/D6 immediately before D2 are **incidental to reaching the
device page**, not a precondition the Button Test code issues. Any harness that reproduces the
*device-page bring-up* will emit this burst; a harness that only opens the Button Test feature will
not — because the app itself does not.

## 4. Unknown / open cells

| Cell | Status | Note |
|---|---|---|
| 2.22 EF / 0B exact emitter addresses | UNKNOWN | opcode tags present in the root page, but the frame-exact builder was not isolated (2.22 uses a different reactive_ble code shape) |
| 2.22 burst ordering / chain | INFERRED | same `getZKMVer`/`getDeviceUUID` pairing as 2.23/2.24, chain order not proven byte-for-byte |
| 2.24 parser gate meaning (`0x24`) | UNKNOWN | length 36 vs element compare not settled |
| 4.0.8 D2 write type (static) | UNKNOWN static / LIVE settled | `BluetoothCharacteristic::write` `withoutResponse` arg not resolvable; LIVE = write-without-response |
| Exact D4/D6 trigger (tab init vs response refresh) | PARTIAL | D6 is re-fired from `del/change/rename/addConfigResponse`; the first (page-open) fire was not fully ordered |
| EF/0B/D4/D6 emitter addresses for 2.22 in the config files | STRONG (file-level) | function-level addresses recovered only for D4 `@0x89b16c` and D6 `@0x89c3c8`/`@0x8a64b4` |

No address in this document is invented; every numeric address was read from a Blutter annotation.
