# Remaining real-hardware unknowns — ARMOR-X Pro pass (`research/physical-armorx-live-2026-09-27`)

**Date:** 2026-09-27 · **Device state at the time of writing: ARMOR-X Pro is POWERED OFF** (operator).
Physical work resumes the moment the unit is powered on; the non-physical branches are finished.

---

## 1. Operator-interaction contract (now enforced)

The operator is not watching the chat continuously, so a chat-only request is no longer sufficient.
Every physical request runs through `automation/physical-action-alert.sh`, which raises:

- a **CRITICAL-urgency KDE desktop notification** (`notify-send`, persistent `-t 0`), and
- an **audible alarm** played on **every** PipeWire sink (default sink here is HDMI, so all sinks
  are played to avoid a silent monitor swallowing the alert),
- repeated every 30 s until acknowledged, and
- a chat instruction with the same wording.

**Validation record:** `results/experiments/physical-action-alert-test.json` — test alert
`test_alert` requested 16:38:29, acknowledged 16:38:38 by the operator with "test ok", loop stopped,
**0 leftover notifier processes** verified (`notify-send` id 46/47 fired; `paplay` on both sinks).
The alert log/state machine lives in `logs/physical-action-alert/{state.json,loop.pid,alert.log,alert.jsonl}`.

`physical-action-alert.sh start "<ACTION_ID>" "<MESSAGE>"` · `stop` · `status` · `selftest`.

---

## 2. Newly resolved on real hardware this pass

| Item | Result | Level |
|---|---|---|
| Unit identity | `ZJ-XT` via GATT 2A24; adv name `ARMOR-X Pro_11`; adv mfr data `fe ff 5a 4a 2d 58 54` = company `0xFEFF` + ASCII **`ZJ-XT`** | PROVEN LIVE |
| As-found config baseline | 144 bytes, sha256 `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` | PROVEN LIVE |
| No-op D7 → D6 round-trip | **PASS, byte-for-byte equal** (`restore_verified: true` for this unit+hash) | PROVEN LIVE |
| Emergency-restore path | physically validated against that same baseline | PROVEN LIVE |
| Real D4 reply | `A5 06 D4 00 00 7F` (gamepad_mode 0, onboard_mode 0) | PROVEN LIVE |
| DPI read | `A5 05 FC 80 26` → `A5 05 FF FC A5` (valid checksum, opcode `0xFF`, value `0xFC`) | PROVEN LIVE |
| Motion/gyro DPI query (`AB 05 05 25 DA`, `AB 05 05 26 DB`) | **no reply** while the link was demonstrably healthy (a follow-up `0B` answered) | PROVEN LIVE (no-reply) |
| **JieLi RCSP service** | **PRESENT on the device**: `0000ae00` (service) + `0000ae01` (write) + `0000ae02` (notify), found by live service discovery in **7** connections; never used by the app | **PROVEN LIVE** |
| Vendor PC toolchain | JieLi AC632N `.ufw` upgrade library (`JL_*`, `AC632N_TRANS/update`, `isd_config.ini`, `uboot.boot`) | PROVEN STATIC |
| Android app RCSP client | absent in all four builds (control-verified negative search) | PROVEN STATIC |

Detail: `results/final/jieli-rcsp-verdict.{md,json}`, `results/final/real-firmware-mode.md`,
`results/final/firmware-inventory.json`, `baselines/device/ZJ-XT_2741_2D-37-35-6D-66-11/`.

---

## 3. Blocked on device power (one concise action per item)

| # | Unknown | What it needs | Why it is still open |
|---|---|---|---|
| 1 | **Physical key-ID map** (ids 5, 12, 15, 20–22, 27–33) | power unit on → D2 test mode → operator presses buttons one at a time | capture windows died with the link when the unit powered off; 4 attempts recorded only the D2 echo |
| 2 | ID 15 = Capture live confirmation | D2 capture, then a single mapKey byte-127 test (gated by `restore_verified`) | needs live input first |
| 3 | Real D8 fragment class (15 / 43 / 67) and wire format | live read-back attempt + smallest legal macro | macro-state preservation must be established first; unit off |
| 4 | Real lighting state / RGB byte order | read-or-reconstruct original state before any write | damped by priority; unit off |
| 5 | Real LED state recording at state transitions | operator observation | device off |
| 6 | GATT **service-enumeration dump as a permanent artifact** | one read-only connection | done implicitly (7 sessions) but no single canonical dump file exists yet |
| 7 | Normal USB enumeration of the body | operator connects USB | not started (device off) |
| 8 | Firmware-upgrade USB mode (JieLi/BD19/UBOOT) | operator: power off, hold center button, insert USB | not started (device off) |
| 9 | Read-only firmware dump → AC6321A from STRONG EVIDENCE to PROVEN | USB bootloader mode + documented READ path only | no erase/flash ever; requires #8 |
| 10 | IMU identity (I2C addr / WHO_AM_I / driver strings) | firmware dump (#9) | stays **UNKNOWN** — do not assume QMI8658A |
| 11 | Does the firmware answer RCSP `FE DC BA` frames? | speaking a vendor upgrade/auth protocol to the unit | deliberately NOT attempted: out of scope for a configuration research pass and not safely reversible |

---

## 4. Blocked on something other than the device

- **GitHub push: AUTH_BLOCKED** — no SSH key / `gh` auth on this host. Work continues locally on
  `research/physical-armorx-live-2026-09-27`; bundles + patch series are produced instead.
- **4.0.8 / 2.24 dynamic emulation: BLOCKED_BY_ABI** (arm64-only APK vs x86_64 AVD host). Static
  evidence for those builds stands; no dynamic gap is claimed to be closed by emulation.
- **No ARMOR-X/F20 firmware image exists on this workstation** (Phase T, exhaustively swept) — the
  vendor updater downloads images at runtime, so firmware analysis cannot proceed offline.

---

## 5. Highest-value next experiment

**Physical key-ID capture (item 1).** It needs no configuration write at all, is fully reversible
(D2 stop frame), and it simultaneously resolves the ID-15 Capture question, most of ids 20–33, and
the real D8/lighting questions *without* any mutation — the strongest evidence-per-risk ratio
available. It requires exactly one physical action: **power the ARMOR-X Pro on**
(and it will be requested through the desktop alert system).
