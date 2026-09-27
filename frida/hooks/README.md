# armorx-lab :: Frida hook set

Platform-level Android Bluetooth/BLE tracing plus native-socket network capture
for the three BIGBIG WON builds.

```
frida/hooks/
├── shared/
│   ├── bt-platform-hooks.js      # android.bluetooth.* hooks (library-agnostic)
│   ├── network-http-hooks.js     # libc socket + Java HTTP capture
│   └── flutter-plugin-probe.js   # R8-proof plugin-class discovery
├── 2.23/entry-2.23.js            # flutter_reactive_ble (+ RxAndroidBle2)
├── 2.24/entry-2.24.js            # flutter_reactive_ble (+ RxAndroidBle2)
├── 4.0.8/entry-4.0.8.js          # flutter_blue_plus
└── README.md
```

`../run-hooks.py` is an optional capture driver that spawns the app, loads the
right files, and writes a JSONL trace to `frida/traces/<version>/`.

---

## 0. Which BLE stack each build uses (verified from the DEX)

| Build | Flutter BLE plugin | dex evidence | Underlying Java | Method channel(s) |
|-------|--------------------|--------------|-----------------|-------------------|
| 2.23  | `flutter_reactive_ble` | `com.signify.hue.flutterreactiveble.*` | `com.polidea.rxandroidble2` (RxAndroidBle 2) | `flutter_reactive_ble_method`, `_scan`, `_status` |
| 2.24  | `flutter_reactive_ble` | `com.signify.hue.flutterreactiveble.*` | `com.polidea.rxandroidble2` | same as 2.23 |
| 4.0.8 | `flutter_blue_plus`    | `com.lib.flutter_blue_plus.FlutterBluePlusPlugin` | — | `flutter_blue_plus/methods` |

Runtime confirmation for 2.23 (logcat while running):

```
I flutter : REACTIVE_BLE: Received BleStatus update: BleStatus.unauthorized
```

2.24's dex also contains the literal string `flutter_blue_plus/methods` but **no**
`com.lib.flutter_blue_plus.*` classes — it is a leftover string; 2.24 still runs
`flutter_reactive_ble`.

> The release builds are R8-shrunk. The Flutter *embedding* classes are renamed
> (`io/flutter/embedding/android/a … x`), which is why
> `Java.use('io.flutter.plugin.common.MethodChannel')` fails at spawn on these
> builds. The **plugin** classes keep their names, and `flutter-plugin-probe.js`
> additionally discovers hook targets by *method name* so obfuscation does not
> matter.

---

## 1. What `bt-platform-hooks.js` covers

Everything is hooked on the **Android platform** API, so it captures traffic
regardless of the Flutter plugin — including a future plugin swap.

| Area | Hooks |
|------|-------|
| Scanning | `BluetoothLeScanner.startScan` (all 4 overloads) / `stopScan` / `flushPendingScanResults`; `BluetoothAdapter.startDiscovery` / `startLeScan` / `stopLeScan`; `ScanCallback.onScanResult` / `onBatchScanResults` / `onScanFailed` |
| GATT (client) | `BluetoothGatt.connect` / `disconnect` / `close` / `discoverServices` / `getServices` / `readCharacteristic` / `writeCharacteristic` / `readDescriptor` / `writeDescriptor` / `setCharacteristicNotification` / `requestMtu` / `requestConnectionPriority` / `readRemoteRssi` / `beginReliableWrite` / `executeReliableWrite` |
| GATT callbacks | `BluetoothGattCallback.onConnectionStateChange` / `onServicesDiscovered` / `onCharacteristicRead` / `onCharacteristicChanged` / `onCharacteristicWrite` / `onDescriptorRead` / `onDescriptorWrite` / `onMtuChanged` / `onReadRemoteRssi` / `onReliableWriteCompleted` |
| Device | `BluetoothDevice.connectGatt` (all 5 overloads) |
| Value accessors | `BluetoothGattCharacteristic.getValue/setValue`, `BluetoothGattDescriptor.getValue/setValue` |
| Adapter | `BluetoothManager.getAdapter`, `BluetoothAdapter.startDiscovery` etc. |
| Plugin bridge | `MethodChannel.invokeMethod` (best-effort; see note above) |

**Raw bytes are logged as hex first.** Each record carries `value_hex` (ground
truth) and, separately, `value_ascii` (a convenience rendering emitted *after*
the hex). Scan records expose the full advertisement payload via
`record_hex` (from `ScanRecord.getBytes()`).

Verified on an API 33 emulator against 2.23 — every group installed, e.g.:

```
### HOOKED android.bluetooth.le.BluetoothLeScanner.startScan (4 overload(s))
### HOOKED android.bluetooth.BluetoothDevice.connectGatt (5 overload(s))
### HOOKED android.bluetooth.BluetoothGattCallback.onCharacteristicChanged (2 overload(s))
```

and a live interception:

```
{"api":"BluetoothAdapter.startDiscovery","self":{"address":"02:00:00:00:00:00",
 "name":"sdk_gphone64_x86_64","state":12,"enabled":true}}
```

## 2. What `network-http-hooks.js` covers

The apps are Flutter; their HTTP goes through Dart's `dart:io`, which does **not**
use Java's `HttpURLConnection`/OkHttp. A Java-only hook therefore misses the real
traffic, so this script hooks the **libc socket primitives**:

* `connect` / `close` — learns the peer address of every fd
* `send` / `sendto` / `sendmsg` / `write` — outbound payloads
* `recv` / `recvfrom` / `recvmsg` / `read` — inbound payloads

Only descriptors whose peer is on a watched port (`8080`) are dumped, keeping the
trace readable. Bursts are emitted as `data_hex` (+ `data_ascii`).

Verified: a live 2.23 capture recorded the app opening the backend socket —

```
{"api":"connect","fd":127,"peer":{"family":"AF_INET","ip":"47.116.43.253","port":8080},"ret":-1}
```

`47.116.43.253:8080` is `m.bigbigwon.com:8080`. Endpoints recovered from
`libapp.so`: `/dev/register`, `/dev/userLogin`, `/dev/addConfig`, `/dev/setConfig`,
`/dev/changeConfig`, `/dev/delConfig`, `/dev/renameConfig`, `/dev/queryConfigList`,
`/dev/addMacro`, `/dev/delMacro`, `/dev/changeMacro`, `/dev/queryMacroList`,
`/dev/shareConfig`, `/dev/importShareConfig`.

Java-level hooks for OkHttp / `HttpURLConnection` are included as a secondary net
for any platform-stack traffic.

> Complementary approach: **mitmproxy** (see `network/mitmproxy/`). The endpoint
> is plaintext `http://`, so no certificate pinning is involved — just point the
> emulator at the proxy (`emulator -http-proxy http://127.0.0.1:8080` or the
> guest's Wi-Fi proxy setting).

---

## 3. Exact run commands

### 3.1 Toolchain (already installed in the lab)

```bash
cd /home/salamanka/armorx-lab
# frida 16.7.19 — REQUIRED: Frida 17 removed the bundled Java bridge that the
# platform hooks depend on.
.venv-frida/bin/frida --version      # 16.7.19
```

Start the matching frida-server in the guest (see `avd/research/push-frida-server.sh`):

```bash
avd/research/push-frida-server.sh emulator-5554
```

### 3.2 Interactive (the canonical form)

```bash
cd /home/salamanka/armorx-lab

# --- 2.23 : flutter_reactive_ble ---
.venv-frida/bin/frida -U -f com.moojiang.bigbigwon \
    -l frida/hooks/shared/bt-platform-hooks.js \
    -l frida/hooks/shared/flutter-plugin-probe.js \
    -l frida/hooks/2.23/entry-2.23.js

# --- 2.24 : flutter_reactive_ble ---
.venv-frida/bin/frida -U -f com.moojiang.bigbigwon \
    -l frida/hooks/shared/bt-platform-hooks.js \
    -l frida/hooks/shared/flutter-plugin-probe.js \
    -l frida/hooks/2.24/entry-2.24.js

# --- 4.0.8 : flutter_blue_plus (add the network hooks) ---
.venv-frida/bin/frida -U -f com.moojiang.bigbigwon.mygt \
    -l frida/hooks/shared/network-http-hooks.js \
    -l frida/hooks/shared/bt-platform-hooks.js \
    -l frida/hooks/shared/flutter-plugin-probe.js \
    -l frida/hooks/4.0.8/entry-4.0.8.js
```

Add `-l frida/hooks/shared/network-http-hooks.js` to any of the above to also
capture the `/dev/*` HTTP traffic. Use `-U -p <pid>` to attach to an app that is
already running instead of spawning it.

To select a specific emulator when more than one is up:

```bash
.venv-frida/bin/frida -D emulator-5556 -f com.moojiang.bigbigwon -l ...
```

### 3.3 Non-interactive capture (JSONL traces)

```bash
.venv-frida/bin/python frida/run-hooks.py \
    --version 2.23 --device emulator-5554 \
    --seconds 45 --with-net
# -> frida/traces/2.23/trace-2.23-<ts>.jsonl
```

---

## 4. Correlating with btsnoop and the virtual ARMOR-X peripheral

Three independent views of the same session; line them up on the **timestamp**
and the **GATT handle/UUID**.

### 4.1 Frida (application semantics)
* What the app *asked for*: scan start/stop, `connectGatt`, `discoverServices`,
  `readCharacteristic`, `writeCharacteristic`, notifications, MTU.
* Hex payloads before any text encoding.

### 4.2 btsnoop (over-the-air truth)

The emulator guest already logs HCI. Two ways to enable it:

1. Developer options → *Enable Bluetooth HCI snoop log* (UI), or
2. Via adb (no UI needed):

```bash
adb -s emulator-5554 shell setprop persist.bluetooth.btsnooplogmode full
adb -s emulator-5554 shell svc bluetooth disable
adb -s emulator-5554 shell svc bluetooth enable
```

Retrieve the log:

```bash
adb -s emulator-5554 shell ls -l /data/misc/bluetooth/logs/
adb -s emulator-5554 pull /data/misc/bluetooth/logs/btsnoop_hci.log \
    /home/salamanka/armorx-lab/ble/btsnoop/
```

(Newer builds may also expose `/data/misc/bluetooth/logs/btsnoop_hci.log.last`
and `/data/misc/bluedroid/btsnoop_hci.log`.)

Observed on the API 33 image *before* enabling: `/data/misc/bluetooth/logs/`
exists and contains only `btsnooz_hci.log` (the reduced "snooz" log,
`persist.bluetooth.btsnooplogmode` unset). The full `btsnoop_hci.log` appears
only after enabling the snoop log as above.

Open it in Wireshark (Bluetooth HCI H4 dissector) or `btmon --btsnoop file:...`.

### 4.3 Virtual ARMOR-X peripheral logs

When a Bumble virtual peripheral is the peer, its app logs show the other side of
every ATT operation. Run the peripheral against netsim and tee its output:

```bash
.venv-bumble/bin/python -m bumble.apps.<peripheral_app> android-netsim:localhost:<grpc_port> \
    2>&1 | tee /home/salamanka/armorx-lab/ble/virtual-armorx/run-$(date +%F-%H%M%S).log
```

Correlation recipe:

| Frida record | btsnoop | virtual peripheral |
|--------------|---------|--------------------|
| `BluetoothGatt.writeCharacteristic` `value_hex=01a2…` | `ATT Write Command/Request` with identical UUID + value | `on_characteristic_write` for that handle |
| `GattCallback.onCharacteristicChanged` `value_hex=…` | `ATT Handle Value Notification` | what the peripheral sent |
| `BluetoothGatt.requestMtu(517)` | `HCI LE Set Data Length` / `ATT Exchange MTU` | `mtu` reported by the peer |
| `ScanCallback.onScanResult` `record_hex=…` | `HCI LE Advertising Report` | advertisement payload the peripheral broadcast |

Match on **UUID + raw hex** first; application timestamps differ between the
three sources.

---

## 5. Known constraints

* **Frida 17 will not run the Java hooks.** `Java` is undefined (the bridge moved
  out of core). Use Frida ≤ 16.x, or compile the agent with `frida-compile` +
  `frida-java-bridge`. The native-socket network hooks work on both.
* **Only 2.23 is currently runnable dynamically** on this host; 2.24 and 4.0.8 are
  arm64-only and crash under the emulator's binary translation. See
  `results/final/avd-frida-readiness.md`.
* Hooking at spawn means app-class hooks can race the classloader; the plugin
  probe therefore retries after 2 s.
