# Connection-update attribution — official Android session (ARMOR-X Pro)

**Question:** for each of the four connection-interval transitions in the official Android HCI
capture, who initiated it — the phone (CENTRAL_REQUEST), the peripheral
(PERIPHERAL_REQUEST), the phone's stack automatically (STACK_AUTOMATIC), or UNKNOWN?

**Answer in one line:** the **11.25 ms** state is the only *requested* one and it was requested by the
**PERIPHERAL**; the other three are the phone's own stack. **The app requests no interval profile at all.**

---

## 1. Source and method

| | |
|---|---|
| Capture | `results/experiments/official-vs-harness-session-20260927-190741/official-session/transport-attempt-20260927-193109/official-session-live/raw/android-official-session.cfa` |
| SHA-256 | `bbaf10bd337a840ee0316291cd53f442859b55d8ce10c2414973d9c59248ba2f` — matches the sidecar `.sha256` exactly |
| Format | BTSnoop v1, HCI UART (`Bluetooth H4 with linux header`), 11 029 frames |
| Decoder | tshark 4.6.4 |
| Companion | `.../official-session-live/raw/logcat-official.txt` (same session) |
| Working copy | `/tmp/official.cfa` |

**Two method notes that cost time and are worth recording:**

1. tshark on this host is AppArmor-confined and **cannot read paths under `/home/salamanka`**. The file
   must be copied to `/tmp` first (`cp <file> /tmp/official.cfa`).
2. The field **`btatt.mtu` does not exist in tshark 4.6.4**. Requesting it makes tshark exit non-zero and
   emit *nothing at all* — a silent-looking failure. Field names that *do* exist in this build and were used:
   `bthci_evt.le_con_interval`, `bthci_evt.le_con_latency`, `bthci_evt.le_supv_timeout`,
   `bthci_evt.le_meta_subevent`, `bthci_cmd.opcode`, `btl2cap.cid`, `btl2cap.cmd_code`.
   Note also that there is **no `bthci_evt.le_con_timeout`** (it is `le_supv_timeout`) and no
   `bthci_cmd.ogf`/`ocf` (they are folded into `bthci_cmd.opcode` as `0x2013`).

### Exhaustiveness

The capture contains, in total:

- **2** frames on L2CAP LE-signalling CID `0x0005` (one request, one response);
- **3** HCI `LE Connection Update` commands (opcode `0x2013`);
- **3** `LE Connection Update Complete` meta-events (`0x03`), plus **1** `LE Enhanced Connection Complete` (`0x0a`).

That accounts for all four interval states and leaves nothing un-attributed. Everything below is the
complete set, not a sample.

---

## 2. The four intervals, with attribution

| # | Frame | t (s) | Event | Interval | Latency | Supv. timeout | **Initiated by** | Grade |
|---|---|---|---|---|---|---|---|---|
| 1 | 4274 | 629.795457 | LE Enhanced Connection Complete (`0x0a`) | 30 ms (raw 24) | 0 | 5000 ms | **STACK_AUTOMATIC** (creation-time choice) | PROVEN |
| 2 | 4320 | 630.196132 | LE Connection Update Complete (`0x03`) | 7.5 ms (raw 6) | 0 | 5000 ms | **STACK_AUTOMATIC** | STRONG EVIDENCE |
| 3 | 4407 | 630.706276 | LE Connection Update Complete (`0x03`) | 30 ms (raw 24) | 0 | 5000 ms | **STACK_AUTOMATIC** | STRONG EVIDENCE |
| 4 | 4426 | 631.493686 | LE Connection Update Complete (`0x03`) | **11.25 ms (raw 9)** | 0 | 2000 ms | **PERIPHERAL_REQUEST** | PROVEN |

Connection: handle `0x0002`, peer `2D:37:35:6D:66:11`, peer address type Public, local role **Central**,
unbonded, unencrypted, ATT MTU 64.

> `PERIPHERAL_REQUEST` means the *preference* came from the ARMOR-X Pro; the phone still had to accept
> it and issue the resulting HCI command. The phone's acceptance (L2CAP result `0x0000`) is part of the proof.

---

### #1 — 30 ms at connect (frame 4274) — STACK_AUTOMATIC

This is not an update but the connection itself. The phone's own command is visible:

```
Frame 4262 @ 629.751901   Sent (host -> controller)
  HCI Command: LE Extended Create Connection (0x08|0x0043)
    interval_min_raw = [24, 24, 24]    -> 30 ms
    interval_max_raw = [40, 40, 40]    -> 50 ms
    latency          = [0, 0, 0]
```

The connection comes up at raw `24` = 30 ms, i.e. the *minimum* of the phone's offered window — the
peripheral accepted the fastest value the phone offered. No L2CAP request, no app call.

**Grade: PROVEN** (command, direction and result all read off the stream).

### #2 — 7.5 ms (frame 4320) — STACK_AUTOMATIC

```
Frame 4297 @ 629.905698   Sent (host -> controller)
  HCI Command: LE Connection Update (0x08|0x0013)
    min = 6, max = 6 (7.5 ms), latency = 0, timeout = 500 (5 s)
Frame 4320 @ 630.196132   Rcvd LE Connection Update Complete (0x03)  -> 7.5 ms
    [Command in frame: 4297]
```

Preceded by **no** L2CAP `0x12`, and the logcat shows no connection-priority call. The command is
host-originated, so the phone's stack emitted it.

**Grade: STRONG EVIDENCE.** *Host-originated + no L2CAP request + no app API call* is PROVEN. The
*reason* for 7.5 ms at this instant is INFERRED: frame 4297 lands ~2 ms before the first GATT
discovery request (frame 4298, `Read By Group Type Request`), so this is the stack's discovery-time
boost. The precise framework decision path was not read out of AOSP in this session.

### #3 — 30 ms (frame 4407) — STACK_AUTOMATIC

```
Frame 4402 @ 630.627280   Sent (host -> controller)
  HCI Command: LE Connection Update (0x08|0x0013)
    min = 24, max = 24 (30 ms), latency = 0, timeout = 500 (5 s)
Frame 4407 @ 630.706276   Rcvd LE Connection Update Complete (0x03)  -> 30 ms
    [Command in frame: 4402]
```

No L2CAP request. In logcat this sits between `onConfigureMTU mtu=23` (02:44:36.284) and
`requestMtu(512)` (02:44:36.639) — again an app-API-free window. 30 ms is the creation-time value and
matches the Android GATT BALANCED default, i.e. the stack reverting to its default.

**Grade: STRONG EVIDENCE** (same reasoning as #2; the "revert to default" interpretation is INFERRED).

### #4 — 11.25 ms (frame 4426) — **PERIPHERAL_REQUEST** ✅

This is the decisive one. Four frames, in order, all on the same handle:

```
4420 @ 631.186767   RECEIVED by the phone   (=> SENT BY THE PERIPHERAL)
  L2CAP CID 0x0005 (LE Signalling), Command Code 0x12 = Connection Parameter Update Request
    ident 0x01, length 8
    Min. Interval:         6      (7.5 msec)
    Max. Interval:         6      (7.5 msec)
    Peripheral Latency:    0
    Timeout Multiplier:  200      (2 sec)

4421 @ 631.190316   SENT by the phone (host -> controller)
  HCI Command: LE Connection Update (0x08|0x0013)
    min = 9, max = 9 (11.25 ms), latency = 0, timeout = 200 (2 s)

4422 @ 631.191432   SENT by the phone
  L2CAP CID 0x0005, Command Code 0x13 = Connection Parameter Update Response
    ident 0x01, Move Result: Accepted (0x0000)

4426 @ 631.493686   RECEIVED by the phone
  LE Meta: LE Connection Update Complete (0x03) -> 11.25 ms
```

**Direction is the whole proof.** Frame 4420 is `Point-to-Point Direction: Received` / `[Direction: Rcvd]`
— it arrived from the controller toward the host, therefore it was **transmitted by the peripheral**. The
phone's reply (4422) is `Sent`. A central cannot "request" from the peripheral over this path; the
peripheral is structurally the requester here.

**Grade: PROVEN.**

#### Worth flagging: the peripheral asked for 7.5 ms and got 11.25 ms

The peripheral requested **6/6 (7.5 ms)**. The phone replied **"Accepted"** — but then programmed
**9/9 (11.25 ms)**. 11.25 ms ÷ 1.25 ms = **9**, which is the lowest interval value Android's GATT stack
permits for a peripheral-originated request (AOSP's `BTM_BLE_CONN_INT_MIN_LIMIT`; the spec's own floor is
`0x0006` = 7.5 ms). The peripheral's 2 s supervision timeout was carried through unchanged, so the only
substituted field is the interval.

- **Observation** (requested 6 → applied 9, response "Accepted"): **PROVEN**.
- **Explanation** (Android clamps to an 11.25 ms floor): **INFERRED**. The constant's existence is
  confirmed by AOSP commit titles (`Allow BTM_BLE_CONN_INT_MIN_LIMIT override by sysprop`); its value
  `0x0009` was **not** read verbatim from AOSP source during this session.

**This is the single most important number in the whole exercise: 11.25 ms is 9 × 1.25 ms, and it is a
clamped floor, not a requested preference.**

---

## 3. Does the app code request an interval profile?

**No.** Grade: **PROVEN**.

### What was searched

| Artifact | Result |
|---|---|
| `static/jadx/4.0.8/` | **Empty — 0 files.** (All four jadx trees, 4.0.8 / 2.24 / 2.23 / 2.22.0901, contain 0 files; there is no decompiled Java to review.) |
| `static/strings/*-libapp.strings` | Dart AOT string tables for libapp.so, builds 4.0.8 / 2.24 / 2.23 |
| `apk/extracted/4.0.8/base/classes.dex`, `classes2.dex`, `classes3.dex` | plugin + app Java/Kotlin |
| `.../logcat-official.txt` | runtime MethodChannel trace for the same session |

### The plugin *can* do it; the app *doesn't* call it

`classes.dex` shows the plugin registers these method names:

```
connect  connection_priority  disconnect  discoverServices  flutterRestart  getAdapterState
readCharacteristic  requestConnectionPriority  requestMtu  setNotifyValue  setPreferredPhy
stopScan  writeCharacteristic
```

…and contains the literals `gatt.requestConnectionPriority() returned false` and
`gatt.requestMtu() returned false`. So `requestConnectionPriority` and `setPreferredPhy` are fully
implemented — the capability is there.

But the **app's own Dart code never names them**. The app's `libapp.so` (4.0.8) contains these interface
strings:

```
connect  disconnect  discoverServices  flutterRestart  getAdapterState
readCharacteristic  requestMtu  setNotifyValue  startScan  stopScan  writeCharacteristic
```

and does **not** contain:

```
requestConnectionPriority      ✗ absent
setPreferredPhy                ✗ absent
connection_priority            ✗ absent   (the connect() option key would have to appear to pass a priority)
```

Same result in the 2.23 and 2.24 string tables (only `requestMtu`, and in 2.24 also `requestMtuSize`).

### Runtime agrees

The MethodChannel trace for the entire session:

```
02:44:24.646 flutterRestart      02:44:35.907 requestMtu        02:44:36.766 setNotifyValue
02:44:24.654 getAdapterState     02:44:36.639 requestMtu        02:45:34.379..02:46:44.953
02:44:33.546 startScan           02:44:36.707 discoverServices       writeCharacteristic x7, readCharacteristic
02:44:35.359 stopScan            02:44:36.722 setNotifyValue   02:47:20.034 disconnect
02:44:35.371 connect
```

No `requestConnectionPriority`. No `setPreferredPhy`. Ever.

The only GATT tuning the app performs is **MTU**: `requestMtu(23)` → `onConfigureMTU mtu=23`, then
`requestMtu(512)` → `onConfigureMTU mtu=64`. (`BluetoothGatt`/`BluetoothGattCallback` appear only as the
plugin's own internal machinery, i.e. `onConnectionUpdated`, `onConfigureMTU`, `onSearchComplete`.)

### Verdict

> **The app explicitly requests no connection-interval profile.** There is no evidence — in the Dart
> string table, in the dex, or in the runtime trace — that the app requested **11.25 ms**. The only
> 11.25 ms event was requested by the peripheral and clamped up by the framework. Asserting an
> app-requested 11.25 ms would be unsupported.

---

## 4. Independent corroboration of the peripheral's 7.50 ms preference

The ARMOR-X Pro publishes its own preference in the GAP service. In the **harness** session capture
(`harness-session/raw/btmon.txt`) the stack reads it:

```
ATT: Read Response (0x0b) len 8
  Handle: 0x0007 Type: Peripheral Preferred Connection Parameters (0x2a04)
  Value[8]: 0600 0600 0000 c800
             ^^^^ ^^^^ ^^^^ ^^^^
             min=6 max=6 latency=0 timeout=200     ->  7.5 ms … 7.5 ms, 0, 2000 ms
```

The peripheral's advertised preference is **7.5 ms**, matching exactly the L2CAP request it sent to the
Android phone (frame 4420: min 6 / max 6 / latency 0 / timeout 200). These are two independent
observations of the same peripheral intent.

---

## 5. Why this matters for the 11.25 ms question

The Android phone reached **11.25 ms** only because its framework *refused to go below* 11.25 ms when a
peripheral asked for 7.5 ms. That is an Android policy floor, not a target anyone chose.

Correspondingly, Linux/BlueZ has **no such floor** — it honours the request. In the harness session,
BlueZ accepted the same peripheral request outright:

```
harness btmon @ 24.911716   (RECEIVED)
  LE L2CAP: Connection Parameter Update Request (0x12) ident 1 len 8
    Min interval: 6   Max interval: 6   Peripheral latency: 0   Timeout multiplier: 200
@ MGMT Event: New Connection Para.. (0x001c)          (Store hint)
    Min connection interval: 6   Max connection interval: 6   Connection latency: 0   Supervision timeout: 200
harness btmon @ 24.912738   (SENT)
  LE L2CAP: Connection Parameter Update Response (0x13)  Result: Connection Parameters accepted (0x0000)
harness btmon @ 24.912750   (SENT by BlueZ)
  HCI Command: LE Connection Update (0x08|0x0013)   min 6, max 6, latency 0, timeout 2000 ms
harness btmon @ 24.915089   LE Connection Update Complete (0x03) -> 7.50 msec
```

Same peripheral, same request, opposite outcome: Android clamps to 11.25 ms, Linux gives it 7.50 ms.

**Consequence for any 11.25 ms experiment on Linux: the peripheral will actively pull the link back down
to 7.50 ms.** Any experiment must expect that, and must decide whether it is trying to (a) obtain
11.25 ms at all, or (b) hold 11.25 ms against a peripheral that keeps asking for 7.5 ms. See
`experiment-11.25ms.md`.

---

## 6. Grades

- **PROVEN** — read directly off the HCI/L2CAP stream or the app binary/trace in this session.
- **STRONG EVIDENCE** — observations agree; a small inferential step remains.
- **INFERRED** — consistent with all observations, not directly verified here.
- **UNKNOWN** — not determinable from available evidence.

| Claim | Grade |
|---|---|
| Handle/role/peer/MTU and all four interval values | PROVEN |
| 11.25 ms was requested by the peripheral (L2CAP `0x12` received on CID `0x0005`) | PROVEN |
| Phone accepted the peripheral's request (L2CAP `0x13`, result `0x0000`) | PROVEN |
| 7.5 ms and 30 ms updates were host-stack-issued (no L2CAP request, no app call) | STRONG EVIDENCE |
| The framework trigger for those two updates (discovery boost / revert) | INFERRED |
| Peripheral asked for 7.50 ms, got 11.25 ms (interval substituted, timeout unchanged) | PROVEN |
| Reason = Android's 11.25 ms floor (`BTM_BLE_CONN_INT_MIN_LIMIT` = 0x0009) | INFERRED |
| App requests no interval profile (no `requestConnectionPriority`/`setPreferredPhy`/`connection_priority`) | PROVEN |
| App requested 11.25 ms | **FALSE** |
