# BIGBIG WON 2.22.0901 — dynamic run against the virtual ARMOR-X peripheral

Autonomous dynamic pass, 2026-09-27. Everything below is from commands executed in
this session; raw output tails are quoted. Labels: **PROVEN LIVE** (observed this
session), **PROVEN STATIC** (from the APK), **INFERRED**, **UNKNOWN**.

## 1. Artifacts under test

| item | value |
|---|---|
| APK | `/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk` |
| SHA-256 | `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c` (re-verified) |
| size | 27,608,134 bytes |
| package / version | `com.moojiang.bigbigwon`, versionCode **3**, versionName **2.22.0901** (PROVEN STATIC + PROVEN LIVE via `dumpsys`) |
| launcher | `com.moojiang.bigbigwon.MainActivity` |
| ABI | ships `x86_64` → runs natively, no ARM translation |
| BLE stack | `flutter_reactive_ble` (`com.signify.hue.flutterreactiveble.*`), PROVEN LIVE by the plugin probe (44 classes / 35 methods hooked) |

The APK was never modified, re-signed, or patched.

## 2. Commands and their real output

### 2.1 AVD boot (final, working configuration)

```
emulator -avd armorx_res_api33 -no-window -gpu swiftshader_indirect -no-audio \
         -no-boot-anim -no-snapshot -port 5554 -packet-streamer-endpoint default -writable-system
```
(via `avd/research/launch-research.sh armorx_res_api33 5554`; emulator **37.1.11.0**)

Boot log: `logs/emulator-res-5554.log`
```
INFO | Successfully initialized netsim WiFi
INFO | Activated packet streamer for bluetooth emulation          <-- Bluetooth IS on the virtual radio
```
Guest state (`dumpsys bluetooth_manager`): `enabled: true  state: ON  address: BB:BB:BB:00:00:01`
(the netsim address from `armorx_res_api33.avd/netsim.ini`).

netsim gRPC port for this boot: `45561` (`$TMPDIR/netsim.ini`).

### 2.2 Install (original APK, unmodified)

The AVD still carried 2.23.0609 (versionCode 12) from earlier work, so a downgrade
install was correctly refused first:

```
$ adb -s emulator-5554 install apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk
adb: failed to install ...: Failure [INSTALL_FAILED_VERSION_DOWNGRADE: Downgrade detected: Update version code 3 is older than current 12]

$ adb -s emulator-5554 uninstall com.moojiang.bigbigwon     -> Success
$ adb -s emulator-5554 install apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk
Performing Streamed Install
Success

$ adb -s emulator-5554 shell dumpsys package com.moojiang.bigbigwon | grep -E "versionCode|versionName"
    versionCode=3 minSdk=21 targetSdk=32
    versionName=2.22.0901
```

### 2.3 Launch + Flutter engine boot

```
$ adb -s emulator-5554 shell am start -n com.moojiang.bigbigwon/.MainActivity
Starting: Intent { cmp=com.moojiang.bigbigwon/.MainActivity }
```
logcat (`logs/2.22-logcat-launch.txt`):
```
I/ActivityManager: Start proc 4674:com.moojiang.bigbigwon/u0a175 for next-top-activity {...MainActivity}
W/FlutterActivityAndFragmentDelegate( 4674): A splash screen was provided to Flutter, but this is deprecated. ...
```
`topResumedActivity=ActivityRecord{... com.moojiang.bigbigwon/.MainActivity}` — Flutter engine
booted, first frame drawn (`Fully drawn ...MainActivity: +1s430ms`). **PROVEN LIVE**

### 2.4 frida-server 16.7.19 (x86_64)

The binary already on the AVD was a leftover **17.19.0** build (version mismatch →
`unable to communicate with remote frida-server`). The lab's pinned binary was pushed:

```
$ adb -s emulator-5554 push frida/tools/frida-server-16.7.19-x86_64 /data/local/tmp/frida-server-16.7.19
$ adb -s emulator-5554 shell chmod 755 /data/local/tmp/frida-server-16.7.19
$ adb -s emulator-5554 shell /data/local/tmp/frida-server-16.7.19 --version
16.7.19
$ adb -s emulator-5554 shell "setsid /data/local/tmp/frida-server-16.7.19 </dev/null >/tmp/frida-server.log 2>&1 &"
$ frida.get_device('emulator-5554').enumerate_processes()   -> 146 processes
```

### 2.5 Capture driver

```
.venv-frida/bin/python frida/run-hooks.py --version 2.22 --device emulator-5554 \
    --seconds 420 --with-net \
    --extra frida/hooks/2.22/permgate2.js \
    --out frida/traces/2.22.0901/trace-2.22.0901-api33-fw2741.jsonl
```
Installed: `network-http-hooks.js`, `bt-platform-hooks.js`, `flutter-plugin-probe.js`,
`frida/hooks/2.22/entry-2.22.js`, plus the permission-gate instrument (below).

## 3. The permission gate that blocks the app on API 33 — and its fix

**PROVEN LIVE.** On API 33 the ARMOR-X Pro card tap is a **no-op**. Tapping it calls the
bundled `permission_handler` plugin, which logs

```
D permissions_handler: No permissions found in manifest for: []3
```

and returns denied, so the Dart side never starts a BLE scan. Cause (PROVEN STATIC):
this build declares

```
uses-permission: android.permission.ACCESS_FINE_LOCATION   maxSdkVersion='32'
uses-permission: android.permission.ACCESS_COARSE_LOCATION maxSdkVersion='32'
```

so on an API 33 device those entries are dropped from the app's effective manifest.
On API 30 the same tap *does* raise the system dialog
"Allow BIGBIG WON to access this device's location?" — confirming the gate is location.

Instrumentation used (`frida/hooks/2.22/permgate2.js`, observation-only, APK untouched):
the obfuscated status method `f.a.a.n.f(int group, android.content.Context)` — found by
trapping the plugin's own log line and reading its Java stack — was observed returning
`0` (denied) for **group 3 = location**; forcing it to `1` (granted) lets the app continue:

```
[PERMGATE2] f(group=3) real=0 -> 1 (GRANTED, forced)
```

With that single override the app scans, connects and completes the whole sequence.
**All live BLE results below depend on this instrumentation**; without it 2.22.0901
cannot reach BLE on API 33 at all. This is a claim about *this* build on *this* AVD.

## 4. Observed startup sequence (PROVEN LIVE)

Peripheral session `ble/virtual-armorx/logs/2220901-fw2741/` (raw `.bin`/`.hex` + `.jsonl`).
Times are local (UTC-4).

| # | time | direction | event | raw bytes |
|---|---|---|---|---|
| 1 | 15:30:35.974 | — | `connect` (app → peripheral), peer `4C:60:DB:07:90:1C` | — |
| 2 | 15:30:36.451 | app→dev | CCCD subscribe on **FFE2** (notify enabled); CCCD value `01 00` | — |
| 3 | 15:30:36.466 | app→dev | **`0x0B` getZKMVer** | `A5 04 0B B4` |
| 4 | 15:30:36.466 | dev→app | version reply | `A5 05 0B 30 E5` |
| 5 | 15:30:36.481 | dev→app | GATT read **2A24** model = `5A 4A 2D 58 54` (`ZJ-XT`) | — |
| 6 | 15:30:36.491 | dev→app | GATT read **2A26** firmware = `32 37 34 31` (`2741`) | — |
| 7 | 15:30:36.512 | dev→app | GATT read **2A19** battery = `64` (100 %) | — |
| 8 | 15:30:36.539 | app→dev | **`0xEF` getDeviceUUID** | `A5 0C EF 00 00 00 00 00 00 00 00 A0` |
| 9 | 15:30:36.539 | dev→app | device-UUID reply | `A5 0C EF 00 01 02 03 04 05 06 07 BC` |
| 10 | 15:30:36.571 | app→dev | unsubscribe FFE2 | — |
| 11 | 15:30:38.297 | app→dev | re-subscribe FFE2 (2nd registration) | — |
| 12 | 15:30:38.316 | app→dev | **`0xD4` getInputModel** — **NOT implemented by the peripheral** | `A5 04 D4 7D` |
| 13 | 15:30:38.316 | — | peripheral logs `command_unknown` `D4`, `reply_bytes_sent: 0` | — |
| 14 | 15:30:38.331 | app→dev | **`0xD6` getDeviceConfig** | `A5 04 D6 7F` |
| 15 | 15:30:38.331 | dev→app | 10 fragments `A4 14 D6 01 …09` + tail `A4 0E D6 0A` = **144-byte config** | see raw below |
| 16 | 15:30:38.433 | app→dev | **`0xD6` again** (the app requests the config a second time) | `A5 04 D6 7F` |
| 17 | 15:30:38.433 | dev→app | same 10 fragments repeated | — |

Raw config read (peripheral `.hex`, verbatim):
```
< 0000  A5 04 D6 7F
> 0000  A4 14 D6 01 84 8A 00 90 33 FF 00 00 00 00 0A 05
> 0010  0A 05 00 7D
> 0000  A4 14 D6 02 00 0F 00 0F 00 01 00 1E 1E 46 46 00
> 0010  00 01 00 78
> 0000  A4 14 D6 03 1E 1E 46 46 00 00 00 00 02 02 00 00
> 0010  00 00 00 5D
> 0000  A4 14 D6 04 0A 3C 3C 2A 00 00 00 00 0A 3C 3C 2A
> 0010  00 00 00 EA
> 0000  A4 14 D6 05 00 0A 3C 3C 2A 00 00 00 00 00 00 00
> 0010  00 00 00 3F
> 0000  A4 14 D6 06 00 00 00 00 00 00 00 00 00 00 00 00
> 0010  00 00 00 94
> 0000  A4 14 D6 07 00 00 00 00 00 00 00 00 00 00 00 00
> 0010  00 00 00 95
> 0000  A4 14 D6 08 00 00 00 00 00 00 00 00 01 02 03 04
> 0010  05 06 07 B2
> 0000  A4 14 D6 09 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13
> 0010  14 15 16 78
> 0000  A4 0E D6 0A 17 18 19 1A 1B 1C 1D 1E 1F 85
```

App-side ordering (Frida trace `trace-2.22.0901-api33-fw2741.jsonl`, verbatim tail):
```
15:29:25.631 BluetoothLeScanner.startScan  {"filters": null, "callback": "f.e.a.n0.u.r$a"}
15:29:27.268 BluetoothLeScanner.stopScan
15:29:27.318..27.327 BluetoothDevice.connectGatt   x4
15:29:28.269 GattCallback.onConnectionStateChange {"status":0,"new_state":2}
15:29:28.313 BluetoothGatt.discoverServices
15:29:28.708 GattCallback.onServicesDiscovered {"status":0}
15:29:28.711 BluetoothGattDescriptor.setValue {"value_hex":"0100"}   <- CCCD
15:29:28.717 BluetoothGatt.writeDescriptor
15:29:28.734 BluetoothGatt.setCharacteristicNotification
15:29:28.735 BluetoothGattCharacteristic.setValue {"value_hex":"a5040bb4"}
15:29:28.738 BluetoothGatt.writeCharacteristic
...
```

### 4.1 Scan parameters — no filters, no name/ServiceUUID filter at the platform layer

```
{"api":"BluetoothLeScanner.startScan","arg_count":3,
 "settings":{"scan_mode":1,"report_delay_ms":"0","callback_type":1,
             "match_mode":1,"legacy":true},
 "filters":null,"callback":"f.e.a.n.u.r$a"}
```
`filters: null` → the app passes **no `ScanFilter`**; any name/ServiceUUID matching is
done in Dart on the delivered result. The obfuscated callback class `f.e.a.n0.u.r$a`
confirms the R8-shrunk release build (the plugin-class-name probe is what covers it).

### 4.2 Not observed (honest negatives)

* **No `requestMtu`** anywhere in the trace — this build never negotiated an MTU.
* **No disconnect/reconnect retry loop** inside a session. The only disconnect was the
  old link dropping when the app was force-stopped (`15:29:03.233 disconnect`).
* **`0xD7` (config write) and `0x0E` (writeDevice) were never sent** — nothing was written
  to the device in this pass.
* No `A4`-fragmented write from the app; the peripheral's `config_write` /
  `macro_terminator` handlers never fired.

## 5. Protocol finding: 2.22's parser needs a ≥4-byte 2A26 (PROVEN LIVE)

The first live run served 2A26 = `41` (2 bytes, the value captured from real hardware
in the earlier research). The app then threw an uncaught Dart exception immediately
after that read:

```
E/flutter ( 5035): [ERROR:flutter/lib/ui/ui_dart_state.cc(198)] Unhandled Exception: RangeError (end): Invalid value: Only valid value is 2: 4
E/flutter ( 5035): #0      RangeError.checkValidRange (dart:core/errors.dart:356)
E/flutter ( 5035): #1      _IntListMixin.getRange (dart:typed_data-patch/typed_data_patch.dart:198)
E/flutter ( 5035): #2      _ArmorXProWidgetState.onNewReceivedData (package:moojiang/widgets/armor-x_pro/armorx_pro_root.dart:129)
E/flutter ( 5035): #3      _ArmorXProWidgetState._readCharacteristic (package:moojiang/widgets/armor-x_pro/armorx_pro_root.dart:147)
E/flutter ( 5035): <asynchronous suspension>
```
(full logcat: `logs/2.22-logcat-full.txt`)

`RangeError (end): Invalid value: Only valid value is 2: 4` = a slice `getRange(_, 4)` on a
list of length **2**. Correlating with the Frida ordering
(`readCharacteristic` at .756/.773/.787 → `onCharacteristicRead` at .770 `ZJ-XT`,
.785 `41`, .795 `64`), the exception lands right after the **2A26 read** — i.e. the
in-flight characteristic was `00002a26` (firmware revision), 2 bytes long.

**Hypothesis test:** re-ran the whole flow with the peripheral serving **2A26 = `2741`**
(4 bytes). Result: **the exception disappeared** (0 `RangeError`/`getRange` lines in
logcat) **and the app advanced past it** to `0xEF`, `0xD4` and `0xD6` (§4). This confirms
the length hypothesis and is the first hard evidence of the payload length 2.22 expects
for 2A26. The experiment changed exactly one variable (the model value was already a
conventional `ZJ-XT`); it does not prove the *semantic* value, only the length.

## 6. UI exploration (PROVEN LIVE)

All screens reached by `adb shell input tap` on the running app. Screenshots in
`results/static/2.22.0901/screenshots/`.

| screen | reached | controls found |
|---|---|---|
| Device List (home) | yes | title "Device List", "Language" button, two family cards: **RAINBOW / "Multiplatform Aim Motion Gamepad"** and **ARMOR-X Pro / "Xbox Series Controller Motion Back Button Attachment"**, hint "Choose your device" |
| Privacy policy dialog | yes (first launch) | "Agree" / "Refuse" |
| Language page | yes | English / 简体中文 / 日本語 / 한국어 |
| Scanning overlay | yes (after tapping ARMOR-X Pro) | dark "Scanning…" card on the Device List |
| ARMOR-X Pro device page | yes (connected) | back arrow, title, "MORE »", controller image, battery icon, device name "ARMOR-X Pro_0001", tabs **Configs / Macros** |
| — Configs tab | yes | "Current config [Untitled ]" row with **Edit** and **Save** buttons, "All Configs", a **+** row |
| — Macros tab | yes | a row "**NIL**", "All Macros", a **+** row |
| MORE menu | yes | **Button Test**, **Instructions**, **Information** (each with a chevron) |
| Button Test | yes | live gamepad diagram: LT/RT (show `0`/`0`), LB/RB, D-pad, X/Y/A/B, L/R sticks, L3/R3, M3/M1/M4/M2 |
| Information | yes | Phone Model `sdk_gphone64_x86_64`, System Version `sdk_gphone64_x86_64-userdebug 13 TE1A.240213.009 12342917 dev-keys`, **App Version `2.22.0901`**, **Device Model `ARMOR-X Pro_0001`**, **Firmware Version (blank)**, footer "Support: ShenZhen Qianyu Co.,Ltd." |
| Instructions | yes but **blank/grey** — its content (server-hosted) did not load |
| Config editor (sliders / lighting / key mapping) | **NOT REACHED** | tapping **Edit**, the config row, or the **+** row produces no navigation (verified repeatedly, incl. after the 144-byte config had been served and parsed). Save was not exercised. |
| Macro editor | **NOT REACHED** | the Macros **+** / "NIL" row taps produced no navigation |

Note: "Firmware Version" displays blank on the Information page even though 2A26 was
read successfully — the app does not surface that value there (UNKNOWN which field feeds it).

## 7. Proven live vs not reached

**PROVEN LIVE**
* Original APK installs and launches; Flutter engine boots (logcat above); `versionCode=3`.
* App scans (`startScan`, `filters=null`, `scan_mode=1`, legacy) after the ARMOR-X Pro card
  tap — **but only with the permission-gate override on API 33**.
* App connects to `ARMOR-X Pro_0001`, discovers services, writes CCCD `01 00` on FFE2,
  writes `A5 04 0B B4`, reads 2A24/2A26/2A19, sends `A5 0C EF …`, sends `A5 04 D4 7D`
  (unknown), sends `A5 04 D6 7F` twice and consumes the 144-byte config.
* Reconnect after a forced app restart re-runs the same sequence from scratch.
* On the Button-Test page the app sends test-mode **`0xD2`** (`A5 05 D2 01 7D` on entry,
  `A5 05 D2 00 7C` on exit) — captured in the earlier run
  (`ble/virtual-armorx/logs/2220901-api33e`).

**NOT REACHED / NOT OBSERVED**
* Any config/lighting/macro **editor** UI (Edit / + / Save / Macros).
* `0xD7` (config write), `0x0E` (writeDevice), any `A4` write, any macro write.
* MTU negotiation; in-session disconnect/reconnect retry.
* Firmware/revision values on the Information page.

## 8. Limitations & crashes

1. **API 33 permission gate (blocking, worked around).** 2.22.0901 cannot start BLE on an
   API 33 device because its location permissions are capped at `maxSdkVersion=32`
   (§3, logcat `No permissions found in manifest for: []3`). Without instrumentation the
   app **never issues `startScan`** on this AVD. That is itself the answer to the
   "does it scan on its own" question: **no — nothing is scanned until the user taps the
   ARMOR-X Pro card, and on API 33 even that is refused by the plugin.**
2. **2A26 length crash (§5).** With a 2-byte 2A26 the Dart parser throws `RangeError`
   from `armorx_pro_root.dart:129`; the app survived but the flow stalled before `0xEF`.
3. **The peripheral's original netsim wiring did not work.** Running
   `virtual_armorx.py --transport android-netsim:…` in its default two-Controller
   ("bridge") mode produced `advertising_started` in the log while **zero HCI reached the
   netsim controller** (netsim's RootCanal showed no commands for that chip and no packets
   crossed for 60 s+). Fixed by attaching the peripheral Host directly to the netsim HCI
   (`--mode direct`, added this session). Additionally the original advertising payload
   (name + 128-bit vendor ServiceUUID + flags = 38 bytes) exceeds the 31-byte legacy limit
   and the real controller rejects it with
   `bumble.hci.HCI_Error: HCI_Error(hci/INVALID_COMMAND_PARAMETERS_ERROR [0x12])`; the
   vendor UUID was moved to the scan response. After both fixes the app connected within
   ~2 s. Evidence: `logs/2.22-periph-direct.log`, `2.22-periph-direct2.log`, and
   `…/netsimd/netsim_stderr.log` (`ChipAdded … device_name: armorxperiph`).
4. API 30 (`armorx_res_api30`) was tried first: there the app **does** scan, but that
   image's Bluetooth is **not** netsim-backed (`address: 3C:5A:B4:01:02:03`,
   no "Activated packet streamer for bluetooth emulation"), so a Bumble peripheral can
   never appear on its radio. API 33 is the only AVD on this host that is both
   netsim-backed and (with the gate override) drivable.

## 9. Instrumentation side effects (explicit)

* Files added to the guest: `/data/local/tmp/frida-server-16.7.19` (lab binary),
  `/data/local/tmp/frida-server.log`.
* Files added on the host: this report, `virtual-armorx-compat.md`, screenshots,
  Frida traces, peripheral session logs, and helper scripts
  (`scripts/start-frida-server-222.sh`, `frida/hooks/2.22/{entry-2.22.js,permgate-api33.js,
  permgate2.js,perm-stack-probe.js,plugin-trace.js,perm-probe.js}`).
* `frida/run-hooks.py` gained `2.22` in `VERSION_PKG` and a repeatable `--extra` flag.
* `ble/virtual-armorx/virtual_armorx.py` gained `--mode {bridge,direct}` (default
  `bridge`, unchanged behaviour) and now puts the 128-bit vendor UUID in the scan response.
* No APK was re-signed or modified; no device permission database entry was changed
  (the location status is faked only inside the instrumented process).

## 10. Trace / log / screenshot inventory

Frida traces (`frida/traces/2.22.0901/`):
* `trace-2.22.0901-api33-fw2741.jsonl` — **primary**, complete connect→config sequence
* `trace-2.22.0901-api33-coldstart.jsonl` — cold start (2A26=41, aborted by the RangeError)
* `trace-2.22.0901-api33-20260927-111700.jsonl` — first API 33 connect + D2 test-mode
* `trace-2.22.0901-20260927-111055.jsonl` — API 30 scan attempt (no netsim radio)
* `trace-2.22.0901-api33-20260927-111600.jsonl` — API 33 pre-override (gate blocked)

Peripheral sessions (`ble/virtual-armorx/logs/`):
`2220901-fw2741/` (primary), `2220901-api33e/` (D2), `2220901-api33b|c|d/` (netsim
iteration), `2220901-api30/`, `2220901-live/`.

Logs: `logs/2.22-install.log`, `logs/2.22-launch.log`, `logs/2.22-logcat-launch.txt`,
`logs/2.22-logcat-full.txt`, `logs/2.22-frida-driver-*.log`, `logs/2.22-periph-*.log`,
`logs/emulator-res-5554.log`, `logs/emulator-res-5556.log`.

Screenshots (`results/static/2.22.0901/screenshots/`): `01-launch`, `03-after-agree`,
`api30-01..05` (API 30 gate), `api33-06..24` (gate override, scan, connected, MORE,
Information, Button Test, Configs, Macros, cold start, config load, Instructions).
