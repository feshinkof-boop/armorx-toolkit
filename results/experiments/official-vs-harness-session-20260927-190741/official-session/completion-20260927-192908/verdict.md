# Completion pass 20260927-192908 — verdict

## Status: BLOCKED (official capture); the experiment as a whole stays PARTIAL

`OFFICIAL VS HARNESS = BLOCKED` for the official half: the ADB transport could not be established,
so no official-app session could be captured. The Linux half from the earlier pass is **COMPLETE
and untouched** (`../harness-session/`, `../../official-vs-harness-diff.*`).

## ADB transport: UNAVAILABLE

- Phase 1 (before asking): `adb devices` empty, no Android device in `lsusb` -> **USB_DEVICE_NOT_PRESENT**
- Phase 2A: exactly one modal popup, one sound, acknowledged 19:27:05
- Detection window: 12 polls over ~90 s -> still `USB_DEVICE_NOT_PRESENT`; popup **not** re-raised
- Late recheck: still no USB device; phone reachable on the network (tailscale pong 53 ms) but
  `adb connect ...:5555` -> `Connection refused`
- Classification: **USB_DEVICE_NOT_PRESENT**
- No wireless-debug pairing detour (not permitted while the phone has never been detected over USB),
  no random ports, no `adb tcpip`, no root bypass, nothing installed or removed

## Consequence for the comparison

Every official-side value is still **NOT_CAPTURED / UNKNOWN**:

| item | state |
|---|---|
| Android physical-device identity | NOT AVAILABLE |
| installed app package / version / APK sha256 | NOT INSPECTED |
| runtime classification (4.0.8 match / different / instrumented) | UNKNOWN |
| bond state, encryption before D2 | UNKNOWN (unreadable, explicitly not guessed) |
| official connection interval / latency / timeout / PHY / MTU | NOT_CAPTURED |
| official CCCD timing, pre-D2 writes, D2 ATT opcode, D2 timestamp | NOT_CAPTURED |
| official idle `A5 12 02` count | NOT_CAPTURED |
| physical A-twice | not performed (nothing to measure against) |
| official D2 disable behaviour | NOT_CAPTURED |

Neither `OFFICIAL_WORKS_HARNESS_SILENT` nor `OFFICIAL_AND_HARNESS_BOTH_SILENT` can be asserted: the
official app was never observed. **Earliest proven material difference: UNKNOWN — not computable.**

## Hypothesis states (unchanged, no inference applied)

- **D2-U-008** (bonding/encryption prerequisite): **UNKNOWN** — harness side measured
  unbonded/unencrypted; official side unobservable.
- **D2-U-009** (parameters/MTU/PHY/timing): **UNKNOWN** — harness numbers measured
  (7.50 ms / latency 0 / 2000 ms / MTU 64 / CCCD 0x0078=0100); official side unobservable.
- **D2-U-007** (why D2 stays silent): **UNKNOWN**, unchanged.

## Configuration integrity

No Bluetooth traffic was sent by this host during this pass (no harness session was run, per the
brief's instruction not to recapture Linux), so no write could have altered the device
configuration. The previously verified readback stands:

`D6 sha256 = bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` -> **CONFIG_BASELINE_MATCH** (earlier pass).

That remains a **readback integrity confirmation**, not a new durability proof. The baseline is
still **DURABLE_OK** from the earlier `write -> readback -> idle/settle -> power cycle -> D6 exact
match` procedure; immediate readback alone would only be **STAGED_OK**.

## Unblock

A working ADB transport to the phone: plug it in with a USB **data** cable, enable **USB debugging**,
and accept the *Allow USB debugging* prompt (or enable wireless debugging and pair). Then the brief's
Phases 3-19 run unchanged; nothing else is missing.
