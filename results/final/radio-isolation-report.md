# armorx-lab — radio isolation & mode-switching report (phases 3+4)

**Host:** Kubuntu, ASUS desktop (DMI chassis_type 3), kernel `7.0.0-34-generic`
**Date of verification:** 2026-09-27 (EDT) · **Verified by:** autonomous run with live hardware
**Full command transcript:** `results/final/radio-verification-log.txt` (501 lines, every command and its real output)

---

## 0. Headline: the brief's hardware premise was stale — the adapter **is plugged in**

The task brief said the spare combo adapter is *not* currently attached. That is no longer true.
At verification time the machine had it attached and working:

| Evidence | Value |
|---|---|
| `lsusb` | `Bus 001 Device 005: ID 0bda:b720 Realtek Semiconductor Corp. RTL8723BU 802.11b/g/n WLAN Adapter` |
| USB path | `1-8` (device), interfaces `1-8:1.0`, `1-8:1.1` (BT, class `e0/01/01`), `1-8:1.2` (Wi-Fi, class `ff/ff/ff`) |
| Wi-Fi | netdev `wlxe84e068af1ff`, MAC `e8:4e:06:8a:f1:ff`, driver `rtl8xxxu` |
| Bluetooth | `hci1`, BD address `E8:4E:06:8A:F2:00`, driver `btusb`, HCI 4.0, Local Name `RTK_BT_4.0` |
| dmesg | insertion at ~6673 s uptime; first enumeration failed (`RTL: download fw command failed (-19)`) then **re-enumerated and loaded fw successfully** (`RTL: fw version 0x0e2f9f73`) |

So almost everything could be verified **live**, not merely simulated. The "adapter absent" behaviour was
still verified — by pointing the tooling at a synthetic identity whose USB path (`1-99`) does not exist.

Consequence for the deliverables: `combo-adapter.json` is **not** a MISSING_ARTIFACT file. Every live field is
populated from a real capture; `expected_identity_until_insertion` is retained but explicitly marked
`SUPERSEDED_BY_LIVE_CAPTURE`, so the file still does the right thing if the adapter is unplugged later.

---

## 1. Deliverables — status

| # | Artefact | Status | Evidence |
|---|---|---|---|
| 1 | `baselines/radio/primary-network-baseline.txt` | **PASS** | 175 lines, 13 captured command sections (log §1) |
| 2 | `baselines/radio/combo-adapter.json` | **PASS** (live identity, not MISSING_ARTIFACT) | `/usr/bin/python3 -m json.tool`, values quoted in §2 |
| 3 | `automation/radio/check-primary-network.sh` | **PASS** — live, incl. `--compare-with` positive **and** negative | log §1 |
| 4 | `automation/radio/find-lab-bluetooth.sh` | **PASS** — live + both failure modes | log §2, §3 |
| 5 | `automation/radio/disable-combo-wifi.sh` | **PASS** — live, incl. `--unbind`, idempotent | log §7, §10 |
| 6 | `automation/radio/restore-combo-wifi.sh` | **PASS** — live round-trip incl. unbound→re-bind | log §8 |
| 7 | `automation/radio/use-bluez.sh` | **PASS** — live power off/on, controller resolved by anchor | log §4 |
| 8 | `automation/radio/use-bumble.sh` | **PASS** — **both** transports verified live | log §5, §6 |
| 9 | `automation/radio/radio-status.sh` | **PASS** | log §9 |
| 10 | `automation/radio/radio-restore.sh` | **PASS** — end-to-end | log §9 |
| 11 | `automation/radio/lib-radio-identity.sh` | supporting library (identity resolution + re-exec-to-root) | — |
| 12 | `automation/radio/capture-radio-baseline.sh` / `.py` | supporting: regenerates (1) and (2) | — |
| 13 | `automation/scripts/emergency-restore/emergency-restore-radio.sh` | **PASS** — standalone, dependency-free recovery | log §9 |
| 14 | `results/final/hardware-request.md` | written | — |

Nothing in the entire radio tool-set was left as NOT ATTEMPTED except the two items in §6.

---

## 2. Captured identity (live) — `baselines/radio/combo-adapter.json`

Identity is bound to the **physical USB path + MAC/controller address**, never to names. The generated file
records that rule explicitly under `identity_binding`.

```
physical_anchor.usb_port_path      = 1-8
physical_anchor.usb_vid_pid        = 0bda:b720          (vid 0bda, pid b720, bcdDevice 0200, serial 00e04c000001)
physical_anchor.usb_device_sysfs   = /sys/bus/usb/devices/1-8
physical_anchor.usb_device_realpath= /sys/devices/pci0000:00/0000:00:14.0/usb1/1-8
physical_anchor.udev_id_path       = pci-0000:00:14.0-usb-0:8
usb_interfaces.1-8:1.0            = /sys/devices/.../usb1/1-8/1-8:1.0   driver btusb    (class e0/01/01)
usb_interfaces.1-8:1.1            = /sys/devices/.../usb1/1-8/1-8:1.1   driver btusb    (class e0/01/01)
usb_interfaces.1-8:1.2            = /sys/devices/.../usb1/1-8/1-8:1.2   driver rtl8xxxu (class ff/ff/ff)
live_capture.wifi.ifnames         = ["wlxe84e068af1ff"]        <-- DERIVED, not an anchor
live_capture.wifi.mac             = e8:4e:06:8a:f1:ff          <-- ANCHOR
live_capture.wifi.usb_interface   = 1-8:1.2
live_capture.bluetooth.hci_name   = hci1                       <-- DERIVED, not an anchor
live_capture.bluetooth.bdaddr     = E8:4E:06:8A:F2:00          <-- ANCHOR
live_capture.bluetooth.hci_version= 4.0 (HCI rev 0xe2f, LMP subver 0x9f73)
live_capture.bluetooth.kernel_driv= btusb
live_capture.bluetooth.sysfs      = /sys/devices/.../usb1/1-8/1-8:1.0/bluetooth/hci1
missing_artifact_fields           = []                          (no live field was unavailable)
attachment_history                = 80 filtered dmesg lines (RTL8723B insertion evidence)
builtin_bluetooth_reference       = 1-6, 0489:e10d, hci0, 4C:82:A9:93:53:0C  (do-not-touch reference)
```

Notes recorded in the file:

* `expected_identity_until_insertion` is preserved and marked `SUPERSEDED_BY_LIVE_CAPTURE`, so discovery still
  works if the adapter is later absent (the anchoring values are already correct).
* `/sys/class/bluetooth/hciN/address` **does not exist on this kernel** (`cat` → ENOENT); the bdaddr is
  therefore read from `hcitool dev` / `hciconfig -a`. This is why resolution uses those tools.
* rfkill indices are **volatile**: the combo controller moved `3 → 6 → 8` across unbind/rebind cycles during
  this session. They are recorded as observations only and never used for identity.

---

## 3. What was actually verified on this host, right now

### 3.1 Primary network — **PASS** (`check-primary-network.sh`)
```
$ ./automation/radio/check-primary-network.sh
check-primary-network.sh: PASS: wlp3s0 operstate up
check-primary-network.sh: PASS: wlp3s0 has IPv4 192.168.0.45/24
check-primary-network.sh: PASS: wlp3s0 is associated (K&M New)
check-primary-network.sh: PASS: default route via 192.168.0.1 dev wlp3s0
check-primary-network.sh: PASS: NetworkManager reports wlp3s0 connected
check-primary-network.sh: PASS: primary network healthy
[exit 0]
```
`--compare-with` was verified in both directions:
```
$ ./automation/radio/check-primary-network.sh --compare-with baselines/radio/primary-network-snapshot.txt --quiet
... PASS: no change versus baselines/radio/primary-network-snapshot.txt        [exit 0]

$ ./automation/radio/check-primary-network.sh --compare-with /tmp/tampered.txt --quiet   # route.dev changed to wlxe84e068af1ff
... FAIL: primary network changed versus /tmp/tampered.txt:
--- /tmp/tampered.txt
+++ .../primary-net.*
-route.default.dev=wlxe84e068af1ff
+route.default.dev=wlp3s0
[exit 1]
```
The canonical snapshot is deliberately free of volatile fields (no signal/bitrate/RX-TX counters), so it does
not flap while the link is healthy.

### 3.2 Discovery by USB path + bdaddr — **PASS** (`find-lab-bluetooth.sh`)
```
$ ./automation/radio/find-lab-bluetooth.sh
lab_hci=hci1
bdaddr=E8:4E:06:8A:F2:00
usb_path=1-8
usb_vid_pid=0bda:b720
usb_interface=1-8:1.0
kernel_driver=btusb
rfkill_index=8
sysfs_path=/sys/devices/pci0000:00/0000:00:14.0/usb1/1-8/1-8:1.0/bluetooth/hci1
resolved_by=usb_path+bdaddr
```
**Both** rejection paths were exercised — this is the proof that identity is not name/index based:

| Test | Setup | Result |
|---|---|---|
| Adapter "absent" | identity USB path `1-99` | `adapter NOT PRESENT.` + list of the controllers that *are* present + plug-in instruction → **exit 3** |
| Same path, wrong controller | USB path `1-8`, bdaddr `DE:AD:BE:EF:00:01` | rejected → **exit 3** |
| Same bdaddr, wrong path | identity path `1-99` while real hci1 has that very bdaddr | rejected → **exit 3** |

That last row is the important one: a controller whose bdaddr matched was still refused because the physical
USB path did not. No script in the set ever takes an `hciN` index or a `wlx*` name as truth.

Same clean-failure behaviour was confirmed for `disable-combo-wifi.sh` (**exit 3**), `use-bluez.sh` (**exit 3**),
`use-bumble.sh` (**exit 3**), and `radio-status.sh` (**exit 3**, full status still printed).

### 3.3 Combo Wi-Fi isolation — **PASS** (`disable-combo-wifi.sh` / `restore-combo-wifi.sh`)
```
$ ./automation/radio/disable-combo-wifi.sh
disable-combo-wifi.sh: plan
  primary (untouched) : wlp3s0
  combo wifi netdev   : wlxe84e068af1ff (e8:4e:06:8a:f1:ff)
  combo usb interface : 1-8:1.2 (driver rtl8xxxu)
  action              : NetworkManager unmanaged + ip link down
check-primary-network.sh: PASS: no change versus .../primary-before-combo-wifi-disable.txt
state written: /home/salamanka/armorx-lab/automation/radio/state/combo-wifi-state.json
```
Live result: `nmcli device status` → `wlxe84e068af1ff  wifi  unmanaged`, operstate `down`, wlp3s0 untouched.
`--unbind` additionally detached **only** `1-8:1.2` from `rtl8xxxu` (the netdev disappeared entirely; nothing
else changed). `restore-combo-wifi.sh` re-bound it (`re-binding 1-8:1.2 to rtl8xxxu ...`), returned it to
NetworkManager and brought it up. Both scripts are idempotent: running each twice produced identical results
and `[exit 0]`, and the primary network compared clean every time.

Refusal guards (all enforced in code, all live-tested indirectly):
`radio_assert_not_primary()` refuses if the resolved netdev is `wlp3s0` or shares its MAC; the script also
refuses when zero candidates match the anchor and refuses to unbind if the driver cannot be determined.

### 3.4 BlueZ mode — **PASS** (`use-bluez.sh`)
```
$ ./automation/radio/use-bluez.sh --power on
1-8:1.0 already bound to btusb
1-8:1.1 already bound to btusb
bluetoothctl: select E8:4E:06:8A:F2:00 ; power on
  lab_hci=hci1  bdaddr=E8:4E:06:8A:F2:00  usb_path=1-8  driver=btusb  rfkill_index=8  hci_state=UP RUNNING
PASS: hci1 is UP
```
`--power off` → `--power on` round-trip verified. rfkill is only ever **unblocked** (by numeric index), never
blocked. `btmgmt` is deliberately avoided for control because it hangs indefinitely on this RTL8723B (see §5).

### 3.5 Bumble mode — **PASS, both transports** (`use-bumble.sh`)

**Least-invasive first — Bumble over the kernel HCI socket (`hci-socket:1`), btusb stays bound:**
```
$ ./automation/radio/use-bumble.sh --transport hci-socket
bringing hci1 DOWN so Bumble can open the kernel HCI socket (btusb stays bound)
use-bumble.sh: running Bumble with transport hci-socket:1
<<< connecting to HCI...   <<< connected
  Manufacturer:   Realtek Semiconductor Corporation
  HCI Version:    HCI_VERSION_BLUETOOTH_CORE_4_0
Public Address: E8:4E:06:8A:F2:00
Local Name: RTK_BT_4.0
Bumble mode finished (rc=0)
kernel ownership restored on exit
[exit 0]
```
This is a genuine end-to-end proof: Bumble 0.0.218 drove the lab controller and read its version, public
address and command table. Nothing was unbound; `hci1` was restored on exit.

**Fallback — exclusive libusb ownership (`usb:1-8`):**
```
$ ./automation/radio/use-bumble.sh --transport usb
detaching the adapter's Bluetooth USB interfaces from btusb (per-interface, never the whole device)
  unbound 1-8:1.0
use-bumble.sh: running Bumble with transport usb:1-8
<<< connecting to HCI...   <<< connected
  Manufacturer: Realtek Semiconductor Corporation ... Public Address: E8:4E:06:8A:F2:00
kernel ownership restored on exit
[exit 0]

# afterwards:
  1-8:1.0 -> driver=btusb      1-8:1.1 -> driver=btusb      1-8:1.2 -> driver=rtl8xxxu
  hci1: BD Address E8:4E:06:8A:F2:00 ... UP RUNNING
```
The USB moniker is `usb:1-8` — the **physical port path**, i.e. exactly the identity anchor. (Bumble also
accepts `usb:0bda:b720`; the port-path form is preferred because it distinguishes two identical dongles.)
Detaching is per *interface*; the EXIT trap re-binds unconditionally on exit, including on error. Verified
restored to `btusb` after the run, with `hci1` present again.

### 3.6 Status / restore / emergency — **PASS**
`radio-status.sh` prints the primary check, the full combo identity (presence, per-interface class+driver,
netdev, NM-managed state, HCI + bdaddr + driver + state), rfkill, the saved isolation state, and a summary
line (`primary_rc=0 combo_rc=0`). `radio-restore.sh` ran all three stages end-to-end and finished
`PASS - default lab radio state restored`. `emergency-restore-radio.sh` (dependency-free, hard-coded paths,
`--dry-run` supported) ran clean and re-verified the primary network.

---

## 4. Safety compliance

Every script was written and exercised against the hard rules:

* **never** `rfkill block wifi` / `rfkill block all` — not present anywhere; `use-bluez.sh` only ever calls
  `rfkill unblock <numeric index>` for the lab controller's own entry.
* **never** blacklists or unloads a Wi-Fi driver (`modprobe -r` does not appear in any script).
* **never** unbinds a whole USB device — only single interfaces (`1-8:1.2` for Wi-Fi, `1-8:1.0`/`1-8:1.1` for
  Bluetooth). The built-in controller's device (`1-6`) is never referenced by any action.
* the primary network was snapshotted **before and after** every radio operation, and every operation refused
  to proceed (or raised `*** PRIMARY NETWORK CHANGED -- RESTORE NOW ***`) if it changed. In this session it
  never changed: all `--compare-with` checks against `baselines/radio/primary-network-snapshot.txt` returned
  `PASS: no change`.
* a restore path was written **before** any driver-level change: `restore-combo-wifi.sh` (state file driven)
  plus `emergency-restore-radio.sh` (standalone).
* scripts fail loudly with a specific message and a non-zero exit (2 usage/prereq, 3 adapter absent,
  4 Bumble missing, 1 verification failed).

Final state left on the machine: **combo Wi-Fi isolated** (NM-unmanaged + link down — the lab-safe default,
since NetworkManager was otherwise trying to associate this adapter with the neighbouring AP `K&M New 2.4`,
which is exactly the interference the brief forbids), **combo Bluetooth in BlueZ mode** (`hci1` UP, btusb
bound), and **wlp3s0 verified unchanged against the baseline**. Undo with
`automation/radio/radio-restore.sh`.

---

## 5. Findings, deviations and gotchas (worth knowing before phase 5)

1. **The adapter is present, not absent** (§0). The brief's "spare adapter is NOT currently plugged in" is
   outdated; the `-19` firmware failure in dmesg is from the *first* enumeration only and self-healed on
   re-enumeration.
2. **`btmgmt` hangs on this controller.** `btmgmt info` (and `btmgmt --index 1 info`) never returns on this
   RTL8723B; every invocation in the tooling is `timeout`-wrapped and `bluetoothctl` is preferred for control.
3. **Bumble's CLI takes the transport as a positional argument**, not `--transport`, and its `hci-socket`
   transport wants an **adapter index** (`hci-socket:1`), not `hci1`. Both were wrong in the first draft and
   are fixed; the index is re-derived from the anchor on every run.
4. **`readlink -f` lies about unbound interfaces** — it echoes the unresolved path, so a naive
   `basename "$(readlink -f .../driver)"` yields the bogus driver name `driver`. All driver lookups now test
   the symlink first. (This bug was found and fixed live; it affected the first baseline capture.)
5. **`/sys/class/bluetooth/hciN/address` does not exist** on kernel 7.0.0-34-generic; use
   `hcitool dev` / `hciconfig -a`.
6. **rfkill indices are volatile** (3 → 6 → 8 in one session). Never persist them as identity.
7. **Power-on can transiently report `DOWN INIT RUNNING`** for the RTL8723B while it re-initialises; a repeat
   check shows `UP RUNNING`. The scripts report what they see at the moment of checking.
8. **Bumble was installed into the lab venv** (`ble/bumble/venv`, `bumble 0.0.218`, plus Frida 17.19), by a
   parallel task, not by this one. `use-bumble.sh` resolves it at `$BUMBLE_PY` → `ble/bumble/venv/bin/python`
   → system `python3`, and exits **4** with install instructions when no interpreter can `import bumble`.
9. **`shellcheck` is not installed** on this host; correctness was established with `bash -n` plus live runs.
   **`usbmon`** is also missing (only needed if later phases want USB-level capture).
10. During unbind of `1-8:1.0`, the kernel also released `1-8:1.1` (the btusb driver treats the two Bluetooth
    interfaces as one unit). Harmless, still interface-scoped, and both were re-bound on restore.

---

## 6. Not attempted / waiting for hardware

Only two things in this deliverable set remain unproven, and neither is a code path that failed:

| Item | Status | Why | Exact command to run when the situation arises |
|---|---|---|---|
| Absence behaviour against a **physically removed** adapter | **NOT ATTEMPTED (simulated only)** | The adapter is attached; unplugging was not permissible in this session. The absence path was exercised with a synthetic identity (`USB path 1-99`) instead. | `LAB_IDENTITY_JSON=/tmp/fake-absent.json automation/radio/find-lab-bluetooth.sh` — or, after physically unplugging `1-8`: `automation/radio/find-lab-bluetooth.sh; echo $?` (expect exit 3) |
| `--keep` / long-running interactive Bumble sessions (scan, GATT work) | **NOT ATTEMPTED** | Out of phase 3+4 scope; only `bumble-controller-info` was driven to prove both transports. | `automation/radio/use-bumble.sh --transport hci-socket --keep -- --help` then `automation/radio/use-bluez.sh --power on` |

Everything else — including both Bumble transports, the Wi-Fi isolation round-trip with unbind, and the
ours-absent-is-not-theirs rejection logic — was executed against the real hardware and is recorded in
`results/final/radio-verification-log.txt`.
