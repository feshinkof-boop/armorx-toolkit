# Obtaining an 11.25 ms LE connection interval from Linux — experiment preparation

**Goal:** obtain a connection interval of **11.25 ms = 9 × 1.25 ms** reproducibly on the Linux harness
adapter, using **mature APIs**, without hand-rolling HCI.

**Target value:** `11.25 ms` → raw HCI units **`9` (`0x0009`)**, latency `0`,
supervision timeout **2000 ms** → raw **`200` (`0x00C8`)**.

> This is preparation only. **No adapter was touched. Nothing in this document was executed against
> hardware.** Every claim is graded.

---

## 0. The one thing that decides this experiment

The ARMOR-X Pro **asks for 7.50 ms and will fight for it**:

| Evidence | Value |
|---|---|
| GAP *Peripheral Preferred Connection Parameters* (`0x2a04`) on the device | `0600 0600 0000 c800` → min 6 / max 6 / latency 0 / timeout 200 (**7.5 ms**) |
| L2CAP Connection Parameter Update Request it sent to the Android phone | min 6 / max 6 / latency 0 / timeout 200 (**7.5 ms**) |
| L2CAP Connection Parameter Update Request it sent to the Linux harness | min 6 / max 6 / latency 0 / timeout 200 (**7.5 ms**) |

(Grades: PROVEN — all three read directly from captures in this repo.)

So the experiment is **not** "can Linux request 11.25 ms" (trivially yes) — it is **"how long can
11.25 ms survive against a peripheral that keeps asking for 7.5 ms"**.

This distinction is the difference between a successful experiment and a misleading one, so the
recommendation below pins the interval **and** measures whether it holds.

---

## 1. Requirements

| Requirement | Detail | Grade |
|---|---|---|
| Adapter | Any BLE-capable controller. The lab's RTL8723BU (`hci1`) qualifies — it already sustained 7.50 ms. | PROVEN (repo measurement) |
| Adapter state | The 7.5 ms / 11.25 ms values are ordinary values; no special PHY or feature needed. | STRONG EVIDENCE |
| Kernel | Any kernel supporting `HCI_LE_Connection_Update` (BLE 4.0+). Host kernel here is `7.0.0-34-generic`. | PROVEN |
| **Kernel module params** | `le_conn_min_interval` / `le_conn_max_interval` **DO NOT EXIST** on this kernel. `/sys/module/bluetooth/parameters/` contains only `disable_ertm`, `disable_esco`, `enable_ecred`. | PROVEN (checked locally) |
| BlueZ | **5.85** installed. `main.conf` `[LE]` interval keys exist (see §2B). | PROVEN (checked locally + bluez source) |
| Python | Bumble **0.0.235** + Bleak 3.0.2 in `/home/salamanka/armorx-lab/.venv-bumble`. `bumble-python.sh` exists precisely because the Hermes bundled CPython lacks `AF_BLUETOOTH`. | PROVEN (checked locally) |
| Privileges | See per-mechanism. In practice: **root / `CAP_NET_ADMIN`** for everything that touches HCI or the mgmt socket. | PROVEN |
| Spec constraint | supervision timeout must be > (1+latency) × interval × 2 → 22.5 ms for 11.25 ms. 2000 ms is comfortably valid. | PROVEN (spec rule) |

---

## 2. The mechanisms, best first

### 2A. ⭐ Bumble — `Device.update_connection_parameters` (RECOMMENDED for a mid-session change)

This is the highest-level, most explicit route and it maps **1:1 onto exactly the HCI command the
Android phone emitted** in the official capture.

**Exact API (Bumble 0.0.235, verified in the installed package):**

```python
# bumble/device.py:4437
await device.update_connection_parameters(
    connection,
    connection_interval_min = 11.25,   # milliseconds
    connection_interval_max = 11.25,   # milliseconds
    max_latency             = 0,
    supervision_timeout     = 2000.0,  # milliseconds
    min_ce_length           = 0.0,
    max_ce_length           = 0.0,
    use_l2cap               = False,   # central role -> must be False
)
```

**Why this is the right call:**

- Bumble converts milliseconds to raw units internally as `int(ms / 1.25)`
  (`bumble/device.py:4469-4470`). `int(11.25 / 1.25) == 9` exactly — 11.25 and 1.25 are both exact
  binary fractions, so there is **no floating-point rounding risk**. → **PROVEN**
- It then sends `hci.HCI_LE_Connection_Update_Command` (`device.py:4507-4517`), i.e. opcode
  `0x2013` — bit-for-bit the same command the Android phone sent at frame 4421. → **PROVEN**
- It awaits the matching `EVENT_CONNECTION_PARAMETERS_UPDATE`, raising `HCI_Error` on
  `EVENT_CONNECTION_PARAMETERS_UPDATE_FAILURE`. So **success/failure is reported to you**, not
  inferred. → **PROVEN**

**Verification inside the same process** — Bumble maintains
`connection.parameters.connection_interval` (milliseconds), refreshed on every update
(`device.py:6758-6783`, `Connection.Parameters`, `device.py:1865-1882`). Subscribe to
`connection.EVENT_CONNECTION_PARAMETERS_UPDATE` and read it. → **PROVEN**

**Role constraint:** `use_l2cap=True` is only legal when **we are the peripheral**
(`device.py:4475-4479` raises `InvalidStateError` otherwise). As the Central we must send the HCI
command, which is the correct and expected asymmetry — the Central does not "ask", it **decides**.

**Privileges / transport:**
- `hci-socket:<index>` — the adapter must be **DOWN** so Bumble can open the kernel HCI socket, and
  it needs root (the repo's own `bumble-python.sh --sudo` notes *"HCI_USER_CHANNEL needs
  CAP_NET_ADMIN"*). → PROVEN (repo tooling)
- `usb:<bus>-<port>` — libusb, detaching the adapter's Bluetooth USB interfaces from `btusb`
  one at a time; also root. → PROVEN (repo tooling)
- Use `automation/radio/use-bumble.sh` — it handles adapter down/restore and the EXIT trap. → PROVEN

**Reversibility:** call the same function with the previous values, or simply disconnect.

---

### 2B. ⭐ BlueZ `main.conf` `[LE]` — set 11.25 ms for **connection establishment** (RECOMMENDED for a clean run)

This sets the interval at **connection creation**, so the link comes up at 11.25 ms instead of being
corrected afterwards. `/etc/bluetooth/main.conf` lines ~230-239 already contain these keys commented out.

**Exact edit:**

```ini
[LE]
MinConnectionInterval = 9      # 9 x 1.25 ms = 11.25 ms   (raw units)
MaxConnectionInterval = 9      # 9 x 1.25 ms = 11.25 ms   (raw units)
ConnectionLatency     = 0
ConnectionSupervisionTimeout = 200   # 200 x 10 ms = 2000 ms
```

**Units are the raw 1.25 ms / 10 ms units, NOT milliseconds.** Verified from BlueZ source
(`src/main.c`): the accepted range for `MinConnectionInterval` / `MaxConnectionInterval` is
**`0x0006`–`0x0C80`** — i.e. the HCI interval domain (0x0006 = 7.5 ms, 0x0C80 = 4000 ms), so
11.25 ms is **`9`**. → **PROVEN**

- The keys are real and recognised (`le_options[]` in `src/main.c` includes
  `MinConnectionInterval`, `MaxConnectionInterval`, `ConnectionLatency`,
  `ConnectionSupervisionTimeout`). → **PROVEN**
- The effect is applied via the **LE (Extended) Create Connection** command, i.e. the interval is
  baked into the connection at establishment. → **PROVEN** (BlueZ maintainer, bluez#717; and the
  harness capture shows exactly this pattern)
- **Privileges:** root to edit `/etc/bluetooth/main.conf`, then `systemctl restart bluetooth`
  (or `bluetoothd` reload). → STRONG EVIDENCE (standard BlueZ behaviour)
- **Documented caveat, quoted from main.conf itself:** *"LE default connection parameters. These
  values are superseded by any specific values provided via the Load Connection Parameters
  interface."* → **PROVEN** (text in BlueZ `src/main.conf`)

**Reversibility:** comment the keys back out and restart `bluetoothd`; the kernel/BlueZ defaults
return. Keep a copy of the original file before editing.

---

### 2C. BlueZ MGMT `Load Connection Parameters` (opcode `0x0035`) — what BlueZ itself does

This is the interface BlueZ **already uses automatically**: in the harness capture, after reading the
peripheral's `0x2a04`, BlueZ issued

```
@ MGMT Command: Load Connection P.. (0x0035) plen 17  {0x0001} [hci1] 24.822825
        Parameters: 1
        LE Address: 2D:37:35:6D:66:11 (OUI 2D-37-35)
        Min connection interval: 6
        Max connection interval: 6
        Connection latency: 0 (0x0000)
        Supervision timeout: 200
```

→ **PROVEN** (observed on the wire). The fields are exactly the four you need.

- **API:** the BlueZ MGMT socket (BTPROTO_HCI, `HCI_CHANNEL_CONTROL`), command `0x0035`. Reachable
  from Python via a `mgmt`/`pybluez`-style helper or a hand-packed struct.
- **Privileges:** `CAP_NET_ADMIN` (root). → STRONG EVIDENCE
- **Caveat:** this is a *store*, applied to that device's parameters. BlueZ then also emits
  `New Connection Parameters` (`0x001c`) which the **kernel stores**; a subsequent peripheral-requested
  update still wins (see §3). → STRONG EVIDENCE
- **Status:** available and mature, but **less convenient than 2A/2B** because it needs raw mgmt
  packing. Use it if you want to reproduce *exactly* what BlueZ does, or to pre-seed parameters.

---

### 2D. `hcitool lecup` — one-shot, mature-but-deprecated CLI

Present in the installed BlueZ **5.85** and its usage is embedded in the binary:

```
Usage:
    lecup <handle> <min> <max> <latency> <timeout>
        --handle=<0xXXXX>  LE connection handle
        --min=<interval>   Range: 0x0006 to 0x0C80
        --max=<interval>   Range: 0x0006 to 0x0C80
        --latency=<range>  Peripheral latency. Range: 0x0000 to 0x03E8
        --timeout=<time>   N * 10ms. Range: 0x000A to 0x0C80
 min/max range: 7.5ms to 4s. Multiply factor: 1.25ms
 timeout range: 100ms to 32.0s. Larger than max interval
```

**Exact invocation for 11.25 ms:**

```
hcitool -i hci1 lecup <handle> 0x0009 0x0009 0x0000 0x00C8
```

→ **PROVEN** (usage string read from the installed binary; units and ranges explicit).

- **Pros:** zero code, mature, available right now, trivially scriptable; the `1.25 ms` factor is
  even printed for you.
- **Cons:** needs the **connection handle**, which is only known after connecting (see §4);
  `hcitool` is deprecated upstream and may vanish in future BlueZ; it is a thin wrapper over the raw
  HCI command, so it offers no event confirmation (you must watch `btmon` to learn the outcome).
- **Privileges:** root (raw HCI socket). → STRONG EVIDENCE
- **Rollback:** re-issue with the previous values, or disconnect.

---

### 2E. Raw kernel HCI socket (`BTPROTO_HCI` / `HCI_CHANNEL_USER`) — **not recommended**

Send `HCI_LE_Connection_Update` (OGF `0x08`, OCF `0x13`) yourself on a raw HCI socket.

- **Privileges:** `CAP_NET_ADMIN`; `HCI_CHANNEL_USER` additionally requires the adapter to be down
  and the kernel/BlueZ to release it. → PROVEN (repo tooling comments)
- **Why avoid:** the task asks to prefer mature APIs; this re-implements what Bumble (§2A) already
  provides correctly, including rounding, event correlation and error reporting. It also risks
  colliding with `bluetoothd`/the kernel's own connection management.
- **Grade:** works in principle — STRONG EVIDENCE. Not recommended.

---

### 2F. NOT AVAILABLE on this platform

| Mechanism | Status | Grade |
|---|---|---|
| Kernel module params `bluetooth.le_conn_min_interval` / `le_conn_max_interval` / `le_conn_latency` / `le_conn_timeout` | **The parameters do not exist on kernel 7.0.0-34-generic.** `/sys/module/bluetooth/parameters/` lists only `disable_ertm`, `disable_esco`, `enable_ecred`. | PROVEN (checked locally) |
| debugfs `/sys/kernel/debug/bluetooth/hciX/conn_min_interval` / `conn_max_interval` | The files exist and are BlueZ-facing constraints, but **they are not enforced when Linux is the Central** — the kernel validation that would use them was added and then reverted. | STRONG EVIDENCE (bluez#717 report; not code-verified here) |
| `btmgmt` | **Has no connection-interval command.** Its `-r/--min-interval` and `-x/--max-interval` options belong to the **`add-adv`** (advertising) usage block, not to connections. | PROVEN (usage strings read from the installed binary) |
| `bluetoothctl` | No command exposing the LE connection interval. The `MinInterval`/`MaxInterval` strings in the binary relate to advertising/scanning. | STRONG EVIDENCE |
| `Bleak` | **Cannot do it at all.** Bleak 3.0.2 exposes no connection-interval, latency or priority API (searched the whole package). On Linux it sits on BlueZ D-Bus, which has no such property. | PROVEN (searched locally) |
| Bumble `update_connection_parameters_with_subrate` / `set_default_connection_parameters` | These use the BT 6.2 **subrate** commands (`HCI_LE_Connection_Rate_Request`), intended for intervals *below* 7.5 ms. Not needed for 11.25 ms and they need newer controller support. | PROVEN (source read) |

---

## 3. What the peripheral may do — and what that means

**It will likely reject or override 11.25 ms by asking for 7.50 ms again.**

The BlueZ maintainer states this directly in bluez#717: *"if the remote end attempts to update we
store its value then the value of main.conf are superseded"*, and *"this sort of interface [rejecting
peripheral interval updates] is not available right now"*.

→ **PROVEN** (maintainer statement) for the supersede behaviour; **PROVEN** in this lab's own captures
that the ARMOR-X does send such requests (to both Android and Linux).

The possible outcomes when you set 11.25 ms:

| Peripheral behaviour | Observable result |
|---|---|
| Sends a new L2CAP `0x12` for 7.5 ms | BlueZ accepts, answers `0x13` Accepted, then issues its own `LE Connection Update` → **you are pulled back to 7.50 ms**. The `btmon` stream shows *two* `LE Connection Update Complete` events, the second at 7.5 ms. |
| Sends `0x12` and BlueZ rejects (parameter outside the peripheral's own acceptable range) | L2CAP `0x13` with a rejection result; interval stays 11.25 ms. |
| Says nothing | 11.25 ms holds. |
| Refuses to use the interval at LL level | The controller still reports `LE Connection Update Complete`, but possibly with a **status error** (e.g. `0x3B` Unacceptable Connection Parameters) or a different negotiated value — check the *interval actually reported*, not the one you asked for. |
| Link parameters become incompatible | Possible supervision-timeout lapse and disconnect. Low risk here: 11.25 ms / 0 latency / 2000 ms timeout is a conservative, spec-valid combination, and 2000 ms is exactly what the peripheral itself requested. |

**Consequence for experimental design:** because a peripheral override can arrive at any time, the
reporting must be **per connection event**, over time — which is exactly what
`btmon_interval_report.py` (§4) does. A single end-of-run reading is not sufficient evidence.

**Honest expectation:** the most likely outcome on this specific device is 11.25 ms briefly, then
7.50 ms. If the experiment's success criterion is "the link **settles** at 11.25 ms", it will probably
**fail** — and that failure is itself the finding, because it is the mechanism that explains why
Android showed 11.25 ms and Linux showed 7.50 ms.

---

## 4. Verification — how to prove the *negotiated* interval

**Rule: never report the requested interval as the result. Report the negotiated one from the wire.**

### 4.1 `btmon` (the authoritative source) — with the helper script

```bash
# capture (do this alongside the experiment)
btmon -i hci1 -w /tmp/exp11.25.btsnoop

# decode to text, then summarise
btmon -r /tmp/exp11.25.btsnoop > /tmp/exp11.25.txt
python3 btmon_interval_report.py /tmp/exp11.25.txt
python3 btmon_interval_report.py /tmp/exp11.25.txt --json
```

`btmon_interval_report.py` (delivered alongside this document) prints one row per connection event:

```
  #    line          t(s)   handle    interval    raw   lat    timeout  initiator
  1     646     24.561105   0x0010      7.5 ms      6     0    2000 ms  CONNECTION_ESTABLISHMENT
  2     923     24.915089   0x0010      7.5 ms      6     0    2000 ms  PERIPHERAL_REQUEST
```

…and, for peripheral-requested changes, the round trip:

```
Peripheral-requested updates (requested vs negotiated):
  line 923: requested 6/6 -> applied 6 (7.5 ms -> 7.5 ms)   (handle 0x0010)
```

**What to look for in an 11.25 ms run:** a row with `interval = 11.25 ms`, `raw = 9`, `timeout = 2000 ms`,
`initiator = STACK_AUTOMATIC` (an HCI command with no L2CAP request on the wire). If a *later* row
shows `7.5 ms` / `PERIPHERAL_REQUEST`, the peripheral took it back — record both.

**Honest limits of the script:** it infers attribution from HCI alone. HCI shows whether **the peer**
asked; it cannot show whether **your app** asked. `STACK_AUTOMATIC` therefore means "host-initiated,
app intent unobservable from HCI". This is called out in the script's own output. Privileges: `btmon`
needs root. Grade of the whole approach: **PROVEN** (the script's interval extraction is exact; the
attribution is explicitly labelled as bounded).

### 4.2 Bumble in-process (if you drive the experiment from Bumble)

Subscribe to `connection.EVENT_CONNECTION_PARAMETERS_UPDATE` and read
`connection.parameters.connection_interval` (ms). → **PROVEN**. This is a fast check but **only sees
Bumble's own view**; a peer-initiated change is surfaced too, so it is usable — but `btmon` is still
the ground truth, because it also shows *who* asked.

### 4.3 `hcitool con` — ✗ **does NOT show the interval**

`hcitool con` prints `handle %d state %d lm %s` plus remote name/address. **There is no interval
field.** Do not use it to verify this experiment. → **PROVEN** (format string in the installed binary)

### 4.4 `bluetoothctl` — ✗ no interval output

`bluetoothctl info <addr>` does not report the connection interval. → STRONG EVIDENCE

### 4.5 `tshark` (if you prefer the Android-style analysis)

The repo's `automation/scripts/session-diff.py` already parses
`Connection interval: ([\d.]+)` from decoded output. For raw `.cfa`/`.btsnoop` directly, remember the
two host quirks: tshark **cannot read under `/home/salamanka`** (copy to `/tmp`), and **`btatt.mtu`
does not exist in 4.6.4**. Key fields: `bthci_evt.le_con_interval` (raw 1.25 ms units),
`bthci_evt.le_supv_timeout`, `bthci_evt.le_meta_subevent`, `btl2cap.cid`,
`btl2cap.cmd_code`. → PROVEN (established in this session)

---

## 5. Rollback and default behaviour

| Mechanism | Rollback |
|---|---|
| §2A Bumble `update_connection_parameters` | Call again with the previous values (e.g. `7.5, 7.5, 0, 2000`) or disconnect. Nothing persists. |
| §2B `main.conf` | Restore the saved original (all keys are commented out by default in BlueZ 5.85) and `systemctl restart bluetooth`. |
| §2C MGMT `Load Connection Parameters` | Re-issue with the old values; the kernel's stored `hci_conn_params` for that device is overwritten. Removing the device (`bluetoothctl remove <addr>`) drops the store entirely. |
| §2D `hcitool lecup` | Re-issue with the old values, or disconnect. |
| §2E raw HCI | Same as §2D. |
| Any | **Disconnect and reconnect** always returns to creation-time defaults. The Linux adapter has no persistent interval state; a reboot is never required. |

**Default behaviour if you do nothing:** the harness currently comes up at **7.50 ms / latency 0 /
2000 ms supervision timeout**, because (a) the harness's own `LE Create Connection` offered
min 6 / max 6 (7.50 ms), and (b) BlueZ independently accepted the peripheral's 7.5 ms request. Both
are visible in `harness-session/raw/btmon.txt`. → **PROVEN**

---

## 6. Recommended procedure

**Recommended primary mechanism:** **§2A — Bumble `Device.update_connection_parameters(conn, 11.25, 11.25, 0, 2000.0)`**,
because it is a first-class API of an installed, mature stack; it maps 1:1 onto the exact HCI command
the Android phone emitted; it handles unit conversion and event correlation; and it reports failure
instead of leaving you to guess.

**Recommended pairing:** use **§2B (main.conf `MinConnectionInterval = 9`, `MaxConnectionInterval = 9`,
`ConnectionSupervisionTimeout = 200`) *together with* §2A**, so the link starts at 11.25 ms and any
later correction also targets 11.25 ms.

**Sketch of the run (not executed here):**

1. Confirm the adapter and note the current interval baseline (7.50 ms).
2. Apply §2B in `/etc/bluetooth/main.conf` (backup first) and restart `bluetoothd`.
3. Start `btmon -i hci1 -w <file>` **before** connecting.
4. Connect, using the repo's harness path (`use-bumble.sh` for a Bumble-driven run, or Bleak+BlueZ
   with `use-bluez.sh`).
5. Issue §2A right after connection setup.
6. **Keep the link idle for at least 60 s** so any peripheral override has time to arrive. The Android
   session shows the peripheral's request landing ~1.4 s after connect; a 60 s observation window
   gives ample margin.
7. Stop `btmon`; decode; run `python3 btmon_interval_report.py <text>`.
8. Report the **full timeline of negotiated intervals**, not a single value, and state explicitly
   whether 11.25 ms held.
9. Roll back §2B.

**Success criterion (be explicit, because the naive one is wrong):**
*Success = the `btmon` timeline contains an interval of 11.25 ms / raw 9 / timeout 2000 ms, and the
report states whether and when it was superseded.* Claiming "the experiment produced 11.25 ms" without
the timeline would be misleading, because the peripheral is known to pull the link back to 7.50 ms.

**Do not:** use `btmgmt` (no such command), use `hcitool con` to verify (no interval field), rely on
`ble_conn_*` module parameters (absent on this kernel), or attempt this with Bleak alone (no API).

---

## 7. Grades summary

| Claim | Grade |
|---|---|
| 11.25 ms = raw `9`; 2000 ms timeout = raw `200`; latency `0` | PROVEN |
| Bumble `update_connection_parameters` sends HCI `LE Connection Update` (`0x2013`) with `int(ms/1.25)`; 11.25 → 9 exactly | PROVEN |
| Bumble reports success/failure via `EVENT_CONNECTION_PARAMETERS_UPDATE(_FAILURE)`; `connection.parameters.connection_interval` is readable | PROVEN |
| Bumble `use_l2cap=True` requires peripheral role | PROVEN |
| BlueZ `main.conf` `[LE]` has `MinConnectionInterval`/`MaxConnectionInterval`, range `0x0006`–`0x0C80`, i.e. **raw 1.25 ms units** | PROVEN |
| BlueZ `main.conf` values are superseded by a peer's `Load Connection Parameters` / L2CAP request | PROVEN |
| MGMT `Load Connection Parameters` (`0x0035`) carries min/max interval, latency, timeout; BlueZ issues it automatically | PROVEN |
| `hcitool lecup <handle> <min> <max> <latency> <timeout>`, factor 1.25 ms, timeout unit 10 ms | PROVEN |
| `btmgmt` has **no** connection-interval command (its `--min/max-interval` are for `add-adv`) | PROVEN |
| Bleak has no connection-interval API | PROVEN |
| `bluetooth` module params `le_conn_*` do not exist on kernel 7.0.0-34-generic | PROVEN |
| `hcitool con` shows no connection interval | PROVEN |
| debugfs `conn_min_interval`/`conn_max_interval` not enforced when Linux is Central | STRONG EVIDENCE |
| Raw HCI socket route works | STRONG EVIDENCE (not recommended) |
| The ARMOR-X will request 7.50 ms again and may override 11.25 ms | PROVEN it requests 7.5 ms; **INFERRED** that it will override (highly likely) |
| 11.25 ms can be *held* indefinitely against this peripheral | **UNKNOWN** — this is precisely what the experiment must measure |
| Restoring `main.conf` + restart returns defaults | STRONG EVIDENCE |

---

## 8. Delivered helper

`btmon_interval_report.py` — offline btmon text parser.

- Reports the **negotiated interval per connection event** (raw units + ms + latency + supervision
  timeout + handle + role), and attributes each change.
- `--json` for machine consumption; `--self-test` runs a synthetic fixture.
- **Self-test result: PASSED** (3 events; 30.00 ms establishment → 7.50 ms `STACK_AUTOMATIC` →
  11.25 ms `PERIPHERAL_REQUEST`, correctly reporting "requested 6/6 → applied 9").
- **Also validated against real archived data:** running it on
  `.../harness-session/raw/btmon.txt` reproduces the harness timeline exactly —
  `7.5 ms CONNECTION_ESTABLISHMENT` then `7.5 ms PERIPHERAL_REQUEST`, with
  *"requested 6/6 -> applied 6 (7.5 ms -> 7.5 ms)"* — which is the independent confirmation that
  **BlueZ honours 6/6 verbatim while Android clamped it to 9/9**.
- **Never touches an adapter.** It reads a text file only.
