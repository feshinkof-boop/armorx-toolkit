# AVD + Frida readiness — phases 5 / 7 / 8 prep

Host: ASUS desktop, Kubuntu, kernel 7.0.0-34-generic, **x86_64**, i5-12400F
(VT-x, `/dev/kvm` present and usable by user `salamanka`).
Lab root: `/home/salamanka/armorx-lab`. Disk: `916G total / 775G free` after the
installs below. Date of these measurements: 2026-09-27.

---

## 1. Status summary

| Item | Status | Note |
|------|--------|------|
| adb / platform-tools | **WORKING** | 37.0.1 via Android cmdline-tools (`/usr/bin/adb` 34.0.5 also present from apt) |
| Android SDK (cmdline-tools) | **WORKING** | build 16111833 → `~/Android/Sdk/cmdline-tools/latest` |
| Java for sdkmanager | **WORKING** | openjdk 17 at `/usr/lib/jvm/java-17-openjdk-amd64` (system default is 25) |
| Android Emulator | **WORKING** | **37.1.11.0**; `emulator -accel-check` → `KVM (version 12) is installed and usable` |
| x86_64 system image (API 33) | **WORKING** | `system-images;android-33;google_apis;x86_64` |
| x86_64 system image (API 30) | **WORKING** | `system-images;android-30;google_apis;x86_64` (has ARM translation) |
| **2.23 dynamic run** | **WORKING** | installs + boots natively (ships an `x86_64` ABI) |
| **2.24 dynamic run** | **BLOCKED** (runtime) | arm64-only; installs on API 30 but **SIGILL** in `libndk_translation` at launch |
| **4.0.8 dynamic run** | **BLOCKED** (`DYNAMIC_AVD_4.0.8_BLOCKED_BY_ABI`) | arm64-only split APK; same SIGILL crash |
| Virtual Bluetooth (RootCanal/netsim) | **WORKING** | emulator auto-starts `netsimd`; guest BT ON |
| Bumble ↔ emulator virtual controller | **WORKING** | `controller_info` over `android-netsim` returned HCI 5.3, Google |
| Frida on host + guest | **WORKING** | frida-tools **16.7.19** (Frida 17 is NOT usable for the Java hooks) |
| Platform BLE hook scripts | **WORKING** | all hook groups attach; live interception verified |
| Network HTTP hook scripts | **WORKING** | captured the app's socket to `47.116.43.253:8080` |
| Plugin-layer hooks (2.23) | **WORKING** | 44 plugin classes discovered, 35 method overloads hooked by name |
| 2.24 / 4.0.8 hook scripts | **PARTIALLY WORKING** | scripts are written & load-clean, but the apps cannot run on this host to exercise them |
| Physical arm64 device / real dongle | **NOT ATTEMPTED** | out of scope for these phases (no radio operations) |

---

## 2. Toolchain: existence check and install, with real output

### 2.1 What existed before

```
$ command -v adb emulator sdkmanager avdmanager java qemu-system-x86_64 frida-tools
(no output — none of them were installed)
$ ls ~/Android ~/android-sdk /opt/android* /usr/lib/android-sdk
No such file or directory
```

`qemu-system-x86_64` is **not** on `$PATH`, but the Android emulator ships its own
QEMU (`$ANDROID_HOME/emulator/qemu/`). No standalone Android SDK, no AVD, no Java.

### 2.2 Install commands actually run

```bash
sudo apt-get install -y adb unzip wget
sudo apt-get install -y openjdk-17-jre-headless

export ANDROID_HOME=$HOME/Android/Sdk
mkdir -p $ANDROID_HOME/cmdline-tools && cd $ANDROID_HOME/cmdline-tools
wget -O cmdtools.zip \
  https://dl.google.com/android/repository/commandlinetools-linux-16111833_latest.zip
unzip -q cmdtools.zip && mv cmdline-tools latest

$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --sdk_root=$ANDROID_HOME \
  "platform-tools" "emulator" "platforms;android-33" \
  "system-images;android-33;google_apis;x86_64"
# and separately:
$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager --sdk_root=$ANDROID_HOME \
  "system-images;android-30;google_apis;x86_64"
```

Real (trimmed) output:

```
adb: Unpacking adb (1:34.0.5-12build1) ... Setting up adb (1:34.0.5-12build1) ...
Android Debug Bridge version 1.0.41  Version 34.0.5-debian

https://dl.google.com/android/repository/platform-tools_r37.0.1-linux.zip...
https://dl.google.com/android/repository/emulator-linux_x64-15917651.zip...
https://dl.google.com/android/repository/platform-33-ext3_r03.zip...
https://dl.google.com/android/repository/sys-img/google_apis/x86_64-33_r17.zip...
Unzipping emulator...... Unzipping system-images/android-33/google_apis/x86_64......
EXIT 0

https://dl.google.com/android/repository/sys-img/google_apis/x86_64-30_r16.zip...
EXIT 0
```

Verification:

```
$ emulator -version
Android emulator version 37.1.11.0 (build_id 15917651) (CL:N/A)
$ emulator -accel-check
accel:
0
KVM (version 12) is installed and usable.
accel
```

Disk after: `916G total, 95G used, 775G free` (the two system images + emulator
account for ~16 GB).

### 2.3 AVD boot proving the emulator runs

```bash
export ANDROID_AVD_HOME=/home/salamanka/armorx-lab/avd/research/avd-home
echo no | avdmanager create avd -n armorx_res_api33 \
    -k "system-images;android-33;google_apis;x86_64" -d medium_phone --force
emulator -avd armorx_res_api33 -no-window -no-audio -no-boot-anim -no-snapshot \
    -gpu swiftshader_indirect -port 5554
# -> sys.boot_completed=1 after ~36 s
```

---

## 3. ABI analysis and the per-version dynamic verdict

### 3.1 ABI sets, read from the APKs

| Build | `lib/` ABI directories in the APK | Result |
|-------|-----------------------------------|--------|
| 2.23 `base.apk` | `arm64-v8a`, `armeabi-v7a`, **`x86_64`** | native x86_64 available |
| 2.24 `BIGBIGWON-2.24.0919.apk` | `arm64-v8a` only | arm64-only |
| 4.0.8 `.apkm` | `config.arm64_v8a.apk` contains `lib/arm64-v8a/*`; `base.apk` has **no** `lib/` | arm64-only |

4.0.8 split contents:

```
config.arm64_v8a.apk: lib/arm64-v8a/libapp.so, lib/arm64-v8a/libflutter.so,
                      lib/arm64-v8a/libBugly_Native.so,
                      lib/arm64-v8a/libdatastore_shared_counter.so
base.apk / config.en.apk / config.ar.apk / config.xxhdpi.apk: (no lib/)
```

### 3.2 ABI capability of the emulator images

| Image | `ro.product.cpu.abilist` | native bridge |
|-------|--------------------------|---------------|
| `android-33;google_apis;x86_64` | `x86_64` | none |
| `android-30;google_apis;x86_64` | `x86_64,x86,arm64-v8a,armeabi-v7a,armeabi` | `libndk_translation.so`, `ro.enable.native.bridge.exec=1` |

A native arm64 **system image** cannot be used on this host at all — the emulator
refuses it:

```
PANIC: Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host.
```

So the only route to an arm64-only app is the Android 11 (API 30) image's
ARM→x86 binary translation.

### 3.3 Install + launch results (real output)

**On API 33 (no ARM translation)**

```
$ adb -s emulator-5554 install -r .../2.23/base.apk
Success

$ adb -s emulator-5554 install -r .../2.24/BIGBIGWON-2.24.0919.apk
Failure [INSTALL_FAILED_NO_MATCHING_ABIS: ... Failed to extract native libraries, res=-113]

$ adb -s emulator-5554 install -r .../4.0.8/base.apk
Failure [INSTALL_FAILED_MISSING_SPLIT: Missing split for com.moojiang.bigbigwon.mygt]

$ adb -s emulator-5554 install-multiple -r base.apk config.arm64_v8a.apk config.en.apk config.xxhdpi.apk
adb: failed to finalize session
Failure [INSTALL_FAILED_NO_MATCHING_ABIS: ... res=-113]
```

**On API 30 (ARM translation present)**

```
$ adb -s emulator-5556 install -r .../2.24/BIGBIGWON-2.24.0919.apk
Success
$ adb -s emulator-5556 install-multiple -r base.apk config.arm64_v8a.apk config.en.apk config.xxhdpi.apk config.ar.apk
Success
$ adb -s emulator-5556 shell pm list packages | grep moojiang
package:com.moojiang.bigbigwon
package:com.moojiang.bigbigwon.mygt
```

Launching either arm64-only build **crashes immediately**:

```
09-27 10:01:29.274  E ndk_translation: Undefined instruction 0x5ea1b801 at 0x00007d6593de0918
09-27 10:01:29.278  F libc    : Fatal signal 4 (SIGILL), code -6 (SI_TKILL) in tid 4813 (1.ui),
                              pid 4692 (jiang.bigbigwon)
09-27 10:01:29.486  F DEBUG   :       #01 pc ... /system/lib64/libndk_translation.so
                    (ndk_translation::Decoder<...>::DecodeSimdScalarTwoRegMisc()+642)
```

and for 4.0.8:

```
09-27 10:01:41.075  E ndk_translation: Undefined instruction 0x5ea1b800 at 0x00007d659332ad0c
09-27 10:01:41.075  F libc    : Fatal signal 4 (SIGILL) ... pid 5569 (.bigbigwon.mygt)
```

Flutter's arm64 `libflutter.so` executes an instruction the translator cannot
decode. Both apps die before drawing a frame; `pidof` returns empty and the
launcher is foreground again.

**2.23 on API 33 runs properly:**

```
$ adb -s emulator-5554 shell monkey -p com.moojiang.bigbigwon -c android.intent.category.LAUNCHER 1
$ adb -s emulator-5554 shell pidof com.moojiang.bigbigwon
6763
topResumedActivity=ActivityRecord{... com.moojiang.bigbigwon/.MainActivity t9}
I flutter : REACTIVE_BLE: Received BleStatus update: BleStatus.unauthorized
```

### 3.4 Verdict (honest)

| Build | Verdict | Reason |
|-------|---------|--------|
| 2.23 | **DYNAMIC: WORKING** | ships `x86_64` → runs natively on `android-33;google_apis;x86_64`. No translation involved. |
| 2.24 | **DYNAMIC: ARM64_IMPRACTICAL** | arm64-only. Installs on the API 30 image only via `libndk_translation`, then dies with SIGILL. Not usable as a test target on this host. |
| 4.0.8 | **DYNAMIC: `DYNAMIC_AVD_4.0.8_BLOCKED_BY_ABI`** | arm64-only split APK; `INSTALL_FAILED_NO_MATCHING_ABIS` on API 33 and SIGILL under translation on API 30. Equals `ARM64_IMPRACTICAL`. No re-signing / no APK modification was performed (the APKs are untouched). |

**Not `ARM64_RUNS`** for either arm64 build: translation exists but cannot execute
Flutter's arm64 code. A native arm64 host (or a physical arm64 device) would be
required to run 2.24 and 4.0.8 dynamically.

---

## 4. Virtual Bluetooth: RootCanal / netsim and Bumble — **WORKING**

On emulator 37.1.11 Bluetooth emulation is enabled automatically. Boot log:

```
INFO | Successfully initialized netsim WiFi
INFO | Activated packet streamer for bluetooth emulation
```

Guest state:

```
$ adb -s emulator-5554 shell dumpsys bluetooth_manager | head -5
Bluetooth Status
  enabled: true
  state: ON
  address: BB:BB:BB:00:00:01
  name: sdk_gphone64_x86_64
```

Host processes / ports:

```
$ ps -ef | grep netsimd
salaman+ 32640 ... /home/salamanka/Android/Sdk/emulator/netsimd --host-dns=127.0.0.53
$ ss -lntp | grep netsimd
LISTEN 0 128 127.0.0.1:6402   netsimd      # RootCanal HCI server (RootCanal default --hci_port)
LISTEN 0 4096 [::ffff:127.0.0.1]:35335  netsimd   # netsim gRPC control port
```

RootCanal default port set: `6401` test · `6402` HCI · `6403` link (BR/EDR) ·
`6404` link BLE.

Discovery file:

```
$ cat /home/salamanka/.hermes/cache/scratch/netsim.ini     # ($TMPDIR)
grpc.port=35335
$ cat avd/research/avd-home/armorx_res_api33.avd/netsim.ini
bluetooth.address = BB:BB:BB:00:00:01
```

Bumble auto-discovers via `netsim.ini`, but it looks in `XDG_RUNTIME_DIR` first on
Linux while the emulator wrote to `TMPDIR` — pass the port explicitly (or unset
`XDG_RUNTIME_DIR`). Bumble 0.0.235 was installed into `.venv-bumble` with the
`[android]` extra (grpcio + protobuf are required for the netsim transport).

**Verified end-to-end** (host Bumble stack → emulator's virtual controller):

```
$ .venv-bumble/bin/python -m bumble.apps.controller_info android-netsim:localhost:35335
<<< connecting to HCI...
<<< connected
Version:
  Manufacturer:   Google
  HCI Version:    BLUETOOTH_CORE_5_3
  LMP Version:    BLUETOOTH_CORE_5_3
Public Address: DA:4C:10:DE:00:00
LE Number Of Supported Advertising Sets: 16
LE Maximum Advertising Data Length: 512
```

### Emulator command lines / transport strings

```bash
emulator -avd armorx_res_api33 -packet-streamer-endpoint default          # use netsim
emulator -avd <name> -packet-streamer-endpoint localhost:8877             # external streamer
emulator -avd <name> -netsim-args <arg>...
```

| Bumble spec | Mode | Purpose |
|---|---|---|
| `android-netsim` | host | use port from `netsim.ini` |
| `android-netsim:localhost:35335` | host | explicit address |
| `android-netsim:localhost:8877,name=bumble1` | host | named instance (multiple clients) |
| `android-netsim:_:8877,mode=controller` | controller | act as netsim server (bridge a dongle in) |

A physical-dongle bridge (`bumble-hci-bridge android-netsim:_:8877,mode=controller
usb:0`) was **not** attempted — radio operations are out of scope.

---

## 5. Artifacts created

### AVD definitions / creation scripts

| Path | Purpose |
|------|---------|
| `avd/README.md` | REFERENCE vs RESEARCH split, ABI table, split-APK install rule |
| `avd/common-env.sh` | shared SDK/JAVA/emulator/adb/venv paths |
| `avd/reference/create-reference-avd.sh` | clean baseline AVD (API 33, no instrumentation) |
| `avd/reference/launch-reference.sh` | boot it (headless/window) |
| `avd/reference/README.md` | what the reference device is for + per-version results |
| `avd/research/create-research-avd.sh` | API 33 + API 30 research AVDs |
| `avd/research/launch-research.sh` | boot with `-packet-streamer-endpoint` + `-writable-system` |
| `avd/research/install-app.sh` | install a build, split-aware (`install-multiple`) |
| `avd/research/push-frida-server.sh` | push + start the version-matched frida-server |
| `avd/research/README.md` | netsim/RootCanal ports, Bumble specs, translation caveats |

AVDs actually created (lab-local homes, verified):

```
avd/reference/avd-home/armorx_ref_api33.{ini,avd}   # clean baseline, verified created
avd/research/avd-home/armorx_res_api33.{ini,avd}    # verified booted
avd/research/avd-home/armorx_res_api30.{ini,avd}    # verified booted (ARM translation image)
```

`create-reference-avd.sh` was executed end-to-end and produced
`armorx_ref_api33` with `abi.type=x86_64`, `hw.cpu.arch=x86_64`,
`image.sysdir.1=system-images/android-33/google_apis/x86_64/`.

### Frida hooks

| Path | Covers |
|------|--------|
| `frida/hooks/shared/bt-platform-hooks.js` | `BluetoothLeScanner.startScan/stopScan/flushPendingScanResults`; `BluetoothAdapter.startDiscovery/startLeScan/stopLeScan`; `ScanCallback.onScanResult/onBatchScanResults/onScanFailed`; `BluetoothGatt.connect/disconnect/close/discoverServices/getServices/readCharacteristic/writeCharacteristic/readDescriptor/writeDescriptor/setCharacteristicNotification/requestMtu/requestConnectionPriority/readRemoteRssi/beginReliableWrite/executeReliableWrite`; `BluetoothGattCallback.onConnectionStateChange/onServicesDiscovered/onCharacteristicRead/onCharacteristicChanged/onCharacteristicWrite/onDescriptorRead/onDescriptorWrite/onMtuChanged/onReadRemoteRssi/onReliableWriteCompleted`; `BluetoothDevice.connectGatt`; characteristic/descriptor `getValue/setValue` |
| `frida/hooks/shared/network-http-hooks.js` | libc `connect/close/send/sendto/sendmsg/write/recv/recvfrom/recvmsg/read` (fd→peer tracking, port 8080 filter); Java OkHttp + `HttpURLConnection` fallback |
| `frida/hooks/shared/flutter-plugin-probe.js` | runtime discovery of obfuscated plugin classes, hooks by method name |
| `frida/hooks/2.23/entry-2.23.js` | `flutter_reactive_ble` + RxAndroidBle2 |
| `frida/hooks/2.24/entry-2.24.js` | `flutter_reactive_ble` + RxAndroidBle2 |
| `frida/hooks/4.0.8/entry-4.0.8.js` | `flutter_blue_plus` (`FlutterBluePlusPlugin`, `flutter_blue_plus/methods`) |
| `frida/hooks/README.md` | exact run commands, btsnoop correlation, library mapping, constraints |
| `frida/run-hooks.py` | JSONL capture driver (spawn/attach, `--with-net`) |
| `frida/tools/frida-server-16.7.19-x86_64` | guest server binary |

Hex-before-encoding is enforced: records carry `value_hex` / `record_hex` /
`data_hex` as ground truth and only then a separate `*_ascii` rendering.

### Evidence

```
results/final/toolchain-evidence.txt
logs/phase5-7-8/emulator-boot-api33.log
logs/phase5-7-8/emulator-boot-api30.log
frida/traces/2.23/trace-2.23-*.jsonl
```

---

## 6. Blockers and caveats

1. **`DYNAMIC_AVD_4.0.8_BLOCKED_BY_ABI`** — the headline blocker. 4.0.8 (and 2.24)
   are arm64-only; the x86_64 host can install them via the API 30 translation
   layer but they SIGILL in `libndk_translation`. No APK was re-signed or modified.
   Dynamic work for these two needs a physical arm64 device or an arm64 host.
2. **Frida 17 is unusable for the Java hooks.** `Java` is undefined in Frida 17
   (the bridge left core). frida-tools **16.7.19** is installed in `.venv-frida`;
   the guest runs the matching `frida-server-16.7.19-x86_64`. The native-socket
   network hooks work under both.
3. **Release builds are R8-shrunk**; `io.flutter.plugin.common.MethodChannel` does
   not resolve by name at spawn. Harmless — the platform hooks and the method-name
   plugin probe cover it.
4. **API 33 image has no ARM translation** (verified: `abilist=x86_64`, no
   `libndk_translation.so`). Only the API 30 `google_apis` image has it. Do not
   assume newer images translate ARM.
5. **Arm64 system images are impossible on this host** — `PANIC: Avd's CPU
   Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host`.
6. No radio operations were performed; the emulator used only its default
   networking, and no `rfkill`/`hci attach`/interface changes were made.
   `/home/salamanka/armorx-re` was not touched.
