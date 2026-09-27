# Real-hardware readiness

## Ready now (verified in this pass)

| Component | State |
|---|---|
| Protocol helper library | `automation/scripts/armorx_lab/frames.py` — every builder re-derives its checksum and the module asserts the four live anchors (`A5 04 0B B4`, `A5 0C EF 00×8 A0`, `A5 04 D6 7F`, `A5 05 0E 00 B8`) at import time |
| Session state machine | `armorx_lab/device.py` — WAITING_FOR_DEVICE / DEVICE_AWAKE / CAPTURING_IDLE / RUNNING_EXPERIMENT / WAITING_FOR_REPLY / DEVICE_SLEEP_OR_LINK_LOSS / RESTORING / COMPLETE / FAILED, every transition JSONL-logged |
| Watchdog | device-presence watchdog (`--wait`, `device_watchdog`) classifies silence as DEVICE_SLEEP_OR_LINK_LOSS, never as "protocol rejected" |
| CLI | `automation/scripts/real_device_harness.py status|identify|baseline|verify-restore|experiment|prompt` |
| Self-test | `automation/scripts/harness_selftest.py` → **21/21 PASS** (baseline capture, CRC verify, sha256, unknown command → no fabricated reply, watchdog, JSONL audit) |
| Radio path | lab adapter hci1 identified and resolvable by USB path + bdaddr (`find-lab-bluetooth.sh` exit 0); Wi-Fi side already isolated |
| Radio modes | `use-bluez.sh` (btusb) and `use-bumble.sh` (hci-socket first, `usb:1-8` fallback) both verified live |
| Observer path | virtual ARMOR-X (WORKING) + Frida hooks (WORKING) + btsnoop plan (tooling ready) |

## Not attempted (needs a physical ARMOR-X Pro attached)

1. `identify` against real hardware (0B version, EF uuid, MTU).
2. **Baseline capture** — nothing exists in `baselines/device/` yet.
3. **Restore round-trip validation** — until this succeeds, `emergency-restore` refuses to write by
   design and must not be described as usable.
4. Live tests **L01–L08** (`automation/experiment-matrix/matrix.json`). Highest value first: L01
   (baseline + identity), L02 (E2 firmware read), **L03 (`mapKeys[15] = 2`, the Capture
   confirmation)**, then L04/L05 (DPI), L06 (lighting framing), L07 (D8 fragment form — the open
   `len = payload + 5` vs `+ 4` question), L08 (repeatTime unit, gated on L07).

## Operating discipline for the first real session

* Save the "as found" baseline before any write; it is the only trustworthy restore source.
* One variable per write; never combine two unknowns.
* At each physical-state transition record: Receiver LED, ARMOR-X LED, controller attached,
  ARMOR-X awake (`real_device_harness.py prompt` writes these into `logs/device/`).
* Treat the ARMOR-X auto power-off timer as a first-class failure mode; every wait is bounded and a
  vanished device is classified DEVICE_SLEEP_OR_LINK_LOSS until evidence says otherwise.
