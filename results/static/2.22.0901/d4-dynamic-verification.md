# Opcode `0xD4` — LIVE dynamic verification against unmodified 2.22.0901

Generated 2026-09-27 by the armorx-lab D4 live-verification task.
Companions: `results/reconciliation/d4-reconstruction.md` (static pass) and its
dated follow-up appended below that report.

Labels: **PROVEN LIVE** (observed this session in a log), **PROVEN STATIC** (from the APK),
**STRONG EVIDENCE**, **INFERRED**, **UNKNOWN**. Every byte below is quoted from a file that
exists on disk; nothing is reconstructed from memory.

## 0. One-line result

**PROVEN LIVE.** The unmodified 2.22.0901 app sends the exact D4 request `A5 04 D4 7D`, the
peripheral answers `A5 06 D4 00 00 7F`, the app consumes it **without any Dart exception**, and
**proceeds straight to `0xD6`** (twice), then to the 144-byte config. Robustness probes settle what
the static pass could not: the app **does not validate the inbound D4 checksum** (a corrupted
checksum is ignored), but it **reads whole-frame index 4 without a length guard** — a truncated
4-byte reply throws `RangeError (index): Index out of range: index should be less than 4: 4`
at `armorx_pro_config_config.dart:178`, and the app still carries on to `0xD6`. It never repeats
D4 and never disconnects in any of the three runs.

## 1. Artifacts under test

| item | value | evidence |
|---|---|---|
| APK | `apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk` | never modified / re-signed |
| SHA-256 | `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c` | `sha256sum`, re-verified this session **PROVEN LIVE** |
| package / version | `com.moojiang.bigbigwon`, `versionCode=3`, `versionName=2.22.0901` | `dumpsys package` before install and after install **PROVEN LIVE** |
| AVD | `armorx_res_api33` (x86_64, API 33, netsim-backed) on `:5554` | emulator 37.1.11.0, `logs/emulator-res-5554.log` |
| netsim BT address | `BB:BB:BB:00:00:01` | `dumpsys bluetooth_manager`; `avd/research/avd-home/armorx_res_api33.avd/netsim.ini` |
| netsim gRPC port (this boot) | `38395` | `$TMPDIR/netsim.ini` (`grpc.port=38395`) |
| frida-server | 16.7.19 x86_64 | `frida/tools/frida-server-16.7.19-x86_64`, pushed to `/data/local/tmp/frida-server-16.7.19` |
| Frida client | 16.7.19 (`.venv-frida`) | `.venv-frida/bin/python -c "import frida; print(frida.__version__)"` |
| peripheral | updated `ble/virtual-armorx/virtual_armorx.py`, D4 handler active | venv `ble/bumble/venv` |

## 2. Exact commands

```bash
# 0) baseline radio safety (PASS, exit 0)
automation/radio/check-primary-network.sh

# 1) boot the API-33 netsim AVD (foreground of the launcher; run in background)
cd avd/research && ./launch-research.sh armorx_res_api33 5554
# emulator log shows: "Activated packet streamer for bluetooth emulation"

# 2) install the ORIGINAL APK
adb -s emulator-5554 install apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk     # -> Success
adb -s emulator-5554 shell dumpsys package com.moojiang.bigbigwon | grep versionCode
#     versionCode=3 minSdk=21 targetSdk=32 ; versionName=2.22.0901

# 3) frida-server 16.7.19 (the pre-existing /data/local/tmp/frida-server was 17.19.0 -> wrong)
adb -s emulator-5554 root
adb -s emulator-5554 push frida/tools/frida-server-16.7.19-x86_64 /data/local/tmp/frida-server-16.7.19
adb -s emulator-5554 shell chmod 755 /data/local/tmp/frida-server-16.7.19
adb -s emulator-5554 shell "setsid /data/local/tmp/frida-server-16.7.19 </dev/null >/data/local/tmp/frida-server.log 2>&1 &"
# -> /data/local/tmp/frida-server-16.7.19 --version == 16.7.19 ; 146 processes visible

# 4) start the updated virtual peripheral (D4 handler active) on this boot's netsim port
ble/bumble/venv/bin/python ble/virtual-armorx/virtual_armorx.py \
  --transport android-netsim:localhost:38395,name=armorxperiph \
  --mode direct --firmware-revision 2741 \
  --session-id 2220901-d4-live --d4-gamepad-mode 0x00 --d4-onboard-mode 0x00

# 5) drive the app with the platform hook set + permission-gate override
.venv-frida/bin/python frida/run-hooks.py --version 2.22 --device emulator-5554 \
  --seconds 900 --with-net --extra frida/hooks/2.22/permgate2.js \
  --out frida/traces/2.22.0901/trace-d4-live.jsonl

# 6) tap the ARMOR-X Pro card (app is at the Device List on resume)
adb -s emulator-5554 shell input tap 540 740

# 7) pull logcat for the exception check
adb -s emulator-5554 logcat -d -v threadtime > logs/2.22-d4-logcat-full.txt
```

Negative experiments use the **same** recipe plus one flag on the peripheral; the app process is
force-stopped between runs so each is a clean cold start:

```bash
# (a) bad checksum
... virtual_armorx.py ... --session-id 2220901-d4-badcksum  --d4-reply-mode bad-checksum
# (b) truncated
... virtual_armorx.py ... --session-id 2220901-d4-truncated --d4-reply-mode truncated
```

The `--d4-reply-mode {normal,bad-checksum,truncated}` flag was **added this session** to
`virtual_armorx.py` + `armorx_protocol.py::build_d4_reply_variant` (virtual peripheral only;
no APK change). `pytest -q` -> **29 passed** after the change.

## 3. The permission gate (reused, unchanged)

`frida/hooks/2.22/permgate2.js` forced `f.a.a.n.f(int group, Context)` to `1` for the location
group. **PROVEN LIVE**, first trace lines of every run:

```
[PERMGATE2] hooked f.a.a.n.f(int,Context); location group 3 forced to 1
```

`adb shell pm grant ... BLUETOOTH_SCAN / BLUETOOTH_CONNECT` + `appops set ... fine_location allow`
were also attempted as a belt-and-braces step; the app still requires the Dart-side override on API 33
because its location `<uses-permission>` entries carry `maxSdkVersion=32` and are dropped from the
effective manifest (**PROVEN STATIC**, unchanged from the prior dynamic pass). All live D4 results
below depend on this instrumentation.

## 4. Positive run — Frida-vs-peripheral byte comparison (**PROVEN LIVE**)

Run `2220901-d4-live` (default `--d4-reply-mode normal`, payload 0x00 / 0x00).

| # | what | peripheral capture (`.hex`) | Frida platform hook (`.jsonl`) | match |
|---|---|---|---|---|
| 1 | D4 **request** (app→dev) | `< 0000  A5 04 D4 7D` @ `16:02:32.040` | `BluetoothGattCharacteristic.setValue` FF**E1** `value_hex="a504d47d"` @ `16:02:31.991` → `BluetoothGatt.writeCharacteristic` | ✅ byte-identical |
| 2 | D4 **reply** (dev→app) | `> 0000  A5 06 D4 00 00 7F` @ `16:02:32.040` | `setValue` FF**E2** `value_hex="a506d400007f"` @ `16:02:32.009` **and** `GattCallback.onCharacteristicChanged arg2=[-91,6,-44,0,0,127]` @ `16:02:32.010` | ✅ byte-identical |
| 3 | app's **next** frame | `< 0000  A5 04 D6 7F` @ `16:02:32.051` | `setValue` FFE1 `value_hex="a504d67f"` @ `16:02:31.997` | ✅ byte-identical |

`arg2` decodes to `[-91, 6, -44, 0, 0, 127]` = `0xA5 0x06 0xD4 0x00 0x00 0x7F` — the same six
bytes the peripheral logged as sent. The request `a504d47d` is byte-identical to the static
reconstruction `A5 04 D4 7D` (checksum `0x7D`), and the reply `a506d400007f` is the reconstructed
frame (checksum `0x7F`).

Frida trace lines, verbatim:

```json
{"api": "BluetoothGattCharacteristic.setValue", "char": "0000ffe1-0000-1000-8000-00805f9b34fb", "value_hex": "a504d47d", "ts": "2026-09-27T16:02:31.991Z", "kind": "armorx-bt"}
{"api": "BluetoothGattCharacteristic.setValue", "char": "0000ffe2-0000-1000-8000-00805f9b34fb", "value_hex": "a506d400007f", "ts": "2026-09-27T16:02:32.009Z", "kind": "armorx-bt"}
{"api": "GattCallback.onCharacteristicChanged", "char": {"char_uuid": null}, "arg2": [-91, 6, -44, 0, 0, 127], "ts": "2026-09-27T16:02:32.010Z", "kind": "armorx-bt"}
{"api": "BluetoothGattCharacteristic.setValue", "char": "0000ffe1-0000-1000-8000-00805f9b34fb", "value_hex": "a504d67f", "ts": "2026-09-27T16:02:31.997Z", "kind": "armorx-bt"}
```

Peripheral structured `d4_reply` event, verbatim:

```json
{"ts": "2026-09-27T16:02:32.040+00:00", "session": "2220901-d4-live", "event": "d4_reply",
 "request": "a504d47d", "reply": "a506d400007f", "reply_mode": "normal",
 "gamepad_mode": 0, "onboard_mode": 0, "checksum_ok": true}
```

### 4.1 What the app did next (**PROVEN LIVE**)

* **Proceeded to `0xD6` — YES.** Two `A5 04 D6 7F` requests were sent (`16:02:32.051`,
  `16:02:32.131`); the peripheral answered each with the ten `A4/D6` fragments (144-byte config).
* **Repeated D4 — NO.** Exactly one `A5 04 D4 7D` in the whole session.
* **Disconnected — NO.** No `disconnect` event in the session.
* **App-visible state change:** the app navigated from the Device List to the **connected ARMOR-X
  Pro page** (back arrow, name `ARMOR-X Pro_0001`, battery icon, tabs **Configs / Macros**,
  "Current config [Untitled ]" with Edit/Save). Screenshot
  `results/static/2.22.0901/screenshots-d4/02-after-d4-d6.png` (**PROVEN LIVE**).

## 5. logcat exception check (**PROVEN LIVE**)

Command: `adb -s emulator-5554 logcat -d -v threadtime > logs/2.22-d4-logcat-full.txt` (28,285 lines).

```
$ grep -cE "RangeError|getRange|armorx_pro_root\.dart" logs/2.22-d4-logcat-full.txt
0
$ grep -cE "RangeError|getRange|armorx_pro_root\.dart|Unhandled Exception|E/flutter" logs/2.22-d4-logcat-full.txt
0
```

**Zero occurrences** of `RangeError`, `getRange`, `armorx_pro_root.dart` (and zero `E/flutter`
lines at all) around the positive D4 exchange. The positive path is exception-free.

## 6. Negative / robustness experiments (virtual peripheral only) — **PROVEN LIVE**

These variants are deliberately malformed and are **not** evidence about real hardware; they probe
what the app validates.

### 6.1 `--d4-reply-mode bad-checksum` — reply `A5 06 D4 00 00 80` (last byte wrong)

Run `2220901-d4-badcksum`.

| path | bytes |
|---|---|
| D4 request (app→dev) | `A5 04 D4 7D` |
| D4 reply (dev→app) | `A5 06 D4 00 00 80`  (valid length 6, checksum `0x80` ≠ computed `0x7F`) |
| app's next frame | `A5 04 D6 7F` (7 ms after the D4 reply) |

Peripheral event: `"reply_mode": "bad-checksum", "checksum_ok": false,
"parser_errors": ["checksum mismatch: stored 0x80, computed 0x7F"]`.

* **App exception: NONE.** logcat `logs/2.22-d4-logcat-badcksum.txt`:
  `grep -cE 'RangeError|getRange|armorx_pro_root\.dart|Unhandled Exception|E/flutter'` → **0**.
* **App reaction: IGNORE.** It consumed the frame and continued to `D6` and the config.
* **Verdict: the app does NOT validate the inbound D4 checksum.** (Settles static open item §7.4.)

### 6.2 `--d4-reply-mode truncated` — reply `A5 04 D4 00` (4 bytes: index 4 + checksum absent)

Run `2220901-d4-truncated`.

| path | bytes |
|---|---|
| D4 request (app→dev) | `A5 04 D4 7D` |
| D4 reply (dev→app) | `A5 04 D4 00`  (declared length 4; whole-frame index 4 does not exist) |
| app's next frame | `A5 04 D6 7F` (still sent, after the exception) |

Peripheral event: `"reply_mode": "truncated", "checksum_ok": false,
"parser_errors": ["truncated: 4 bytes < 6 (indices 3 and 4 must exist)"]`.

* **App exception: YES — `RangeError`.** `logs/2.22-d4-logcat-truncated.txt`, verbatim:

```
09-27 12:05:38.079  4578  4613 E flutter : [ERROR:flutter/lib/ui/ui_dart_state.cc(198)] Unhandled Exception: RangeError (index): Index out of range: index should be less than 4: 4
09-27 12:05:38.079  4578  4613 E flutter : #0      _Uint8ArrayView.[] (dart:typed_data-patch/typed_data_patch.dart:4194)
09-27 12:05:38.079  4578  4613 E flutter : #1      _ArmorXProConfigWidgetState.subscribeCharacteristic.<anonymous closure> (package:moojiang/widgets/armor-x_pro/armorx_pro_config_config.dart:178)
09-27 12:05:38.079  4578  4613 E flutter : #2      _rootRunUnary (dart:async/zone.dart:1434)
09-27 12:05:38.079  4578  4613 E flutter : #3      _CustomZone.runUnary (dart:async/zone.dart:1335)
09-27 12:05:38.079  4578  4613 E flutter : #4      _CustomZone.runUnaryGuarded (dart:async/zone.dart:1244)
09-27 12:05:38.079  4578  4613 E flutter : #5      _BufferingStreamSubscription._sendData (dart:async/stream_impl.dart:341)
... (frames #6..#15 continue through `_StreamController._add` / `_StreamImplEvents`)
```

  exactly **1** `E/flutter` line-set for the run.
* **Location:** `_ArmorXProConfigWidgetState.subscribeCharacteristic.<anonymous closure>` at
  `package:moojiang/widgets/armor-x_pro/armorx_pro_config_config.dart:178` — i.e. the D4 listener
  in the **same class/file** the static pass decoded (`_ArmorXProConfigWidgetState` listener
  @0x89b438, D4 branch 0x89bcac, module comment `armorx_pro_config_config.dart`). It is **not**
  `armorx_pro_root.dart:129` (that was the earlier 2A26 length crash).
* **App reaction after the exception: it still proceeds to `D6`** and loads the config; the UI stays
  on the connected page (`screenshots-d4/04-truncated.png`). The `RangeError` is thrown inside the
  notify-stream callback and is not fatal.
* **Verdict: the app maps the reply without a length check.** A 4-byte frame with a valid opcode but
  no index-4 byte crashes the D4 callback with `RangeError` — which **PROVEN-LIVE-confirms** the
  static claim that the parser reads whole-frame index 4 raw (`data[4]` / `obj.field_1f`).

### 6.3 Negative-experiment summary

| experiment | reply bytes | app exception | repeats D4 | proceeds to D6 | disconnects |
|---|---|---|---|---|---|
| normal | `A5 06 D4 00 00 7F` | none | no | yes (×2) | no |
| bad-checksum | `A5 06 D4 00 00 80` | none | no | yes | no |
| truncated | `A5 04 D4 00` | **RangeError @ armorx_pro_config_config.dart:178** | no | yes | no |

## 7. PROVEN LIVE vs UNKNOWN

**PROVEN LIVE**
* The unmodified 2.22.0901 app (versionCode 3) sends D4 request `A5 04 D4 7D`, byte-identical to the
  static reconstruction, on **both** the Frida platform hook path and the peripheral raw capture.
* The peripheral's `A5 06 D4 00 00 7F` reaches the app's Dart layer (`onCharacteristicChanged`
  `arg2=[-91,6,-44,0,0,127]`).
* The app consumes the D4 reply **without a Dart exception** and **proceeds to `0xD6`** (twice) and
  the 144-byte config; it does **not** repeat D4 and does **not** disconnect.
* The app **does not validate the inbound D4 checksum** (wrong checksum ignored, no exception).
* The app **reads whole-frame index 4 without a length guard**: a truncated 4-byte D4 reply throws
  `RangeError (index): Index out of range: index should be less than 4: 4` at
  `armorx_pro_config_config.dart:178`, and the app still continues to `D6`.
* Emission ordering: the app writes `D4` then `D6` back-to-back (Frida: `.991` then `.997`), i.e. the
  D6 request is queued before the D4 reply is processed; the reply arrives at `.009`.

**UNKNOWN**
* The **value domain** of payload bytes 3 and 4 (0x00/0x00 here are chosen device state, not
  researched). No value-driven branch fired (the `==6 → getDpi()` gate in 2.23+ is not in 2.22's
  index-4-only branch, and no follow-up command was observed).
* The **exact real reply length** the hardware sends (≥6 proven by the parser's index-4 read; the
  app tolerates extra bytes — never exercised).
* Whether the app ever validates an inbound checksum anywhere else (only D4 was probed).

## 8. File inventory

Traces (`frida/traces/2.22.0901/`):
* `trace-d4-live.jsonl` — primary positive run (D4 `a504d47d` → reply `a506d400007f` → D6)
* `trace-d4-badcksum.jsonl` — bad-checksum probe
* `trace-d4-truncated.jsonl` — truncated probe

Peripheral sessions (`ble/virtual-armorx/logs/`), each `.bin` + `.hex` + `.jsonl`:
* `2220901-d4-live.{bin,hex,jsonl}` — primary positive run
* `2220901-d4-badcksum.{bin,hex,jsonl}`
* `2220901-d4-truncated.{bin,hex,jsonl}`

Logcat (`logs/`):
* `2.22-d4-logcat-full.txt` — positive run (0 exceptions)
* `2.22-d4-logcat-badcksum.txt` — 0 exceptions
* `2.22-d4-logcat-truncated.txt` — the `RangeError` block (§6.2)
* `emulator-res-5554.log` — boot + netsim activation

Screenshots (`results/static/2.22.0901/screenshots-d4/`):
`00-launch.png`, `02-after-d4-d6.png`, `03-badcksum.png`, `04-truncated.png`.

Code touched (virtual peripheral only, not the APK):
* `ble/virtual-armorx/armorx_protocol.py` — added `build_d4_reply_variant(mode, g, o)`
* `ble/virtual-armorx/virtual_armorx.py` — `--d4-reply-mode` flag, `d4_reply` event now carries
  `reply_mode` + `parser_errors`

## 9. Radio-safety and cleanup (PROVEN LIVE)

* `automation/radio/check-primary-network.sh` before the run: **PASS, exit 0** (wlp3s0
  192.168.0.45, gw 192.168.0.1 up).
* Emulator stopped with `adb -s emulator-5554 emu kill`; `adb devices` empty; no `qemu-system`,
  `virtual_armorx.py` or `run-hooks.py` process left (`pgrep` → none).
* `automation/radio/check-primary-network.sh` after cleanup: **PASS, exit 0**.
* No `rfkill`, no driver blacklist/unbind, no `/dev/hci*`, primary Wi-Fi untouched; the ONLY radio in
  the loop was the emulator's virtual netsim controller.
* No APK was modified or re-signed; the permission status was faked only inside the instrumented
  process.
