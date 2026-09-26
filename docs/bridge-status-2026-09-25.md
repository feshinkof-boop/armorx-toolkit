# Windows / Android protocol bridge status — 2026-09-25

This document tracks the attempt to replay the now-proven normal Android read sequence over the Windows F20 vendor-HID path.

## Goal

Test whether the normal Android initialization sequence:

```text
A5 04 0B B4
A5 0C EF 00 00 00 00 00 00 00 00 A0
A5 04 D6 7F
```

causes the Windows `413D:2106` vendor-HID path to reply, and only if D6 replies, test one E2/GetMode request in the same live session.

D7/config writes, 0E, firmware and DFU are deliberately excluded.

## Live Windows identity

### PROVEN

A fresh live F20 instance was observed as:

```text
VID/PID:             413D:2106
USB/HID status:      healthy/present
Usage Page:          0xFF7A
Usage:               0x0001
Input report bytes:  65
Output report bytes: 65
Feature report bytes:0
Report ID:           0
Manufacturer:        Zikway
Product:             HID zkm
```

No present USB `045E` composite node was observed during the run.

Historical instance IDs and host-specific paths are intentionally omitted.

## Probe-enumeration bug found before the run

A Windows `SP_DEVICE_INTERFACE_DETAIL_DATA_W` parsing bug initially read the interface path four bytes too far into the detail buffer.

Symptom:

```text
?\hid#...
```

instead of:

```text
\\?\hid#...
```

That caused every `CreateFileW` call to fail with Win32 error 123 and produced a false `TARGET NOT PRESENT` result.

The correction was to read the device path at the proper offset and then re-verify VID/PID from the opened interface. The corrected probe found exactly one matching live target.

This tooling failure is explicitly separated from device behavior.

## Transport-valid run

Using the corrected enumeration path:

- one handle remained open for the bounded session;
- a 65-byte IN was pre-posted before traffic;
- after each completion the receive was re-armed;
- all three 65-byte writes completed 65/65 with Win32 error 0;
- Report ID 0 was independently confirmed from HID value caps;
- no input report was observed during any phase or the final idle window;
- E2 was not sent because the probe gates it on a D6 reply.

The transmitted application frames were exactly:

```text
A5 04 0B B4
A5 0C EF 00 00 00 00 00 00 00 00 A0
A5 04 D6 7F
```

wrapped as Windows HID reports:

```text
00 | logical command | zero padding to 65 bytes total
```

## Critical correction: USB state is not RF-link state

The run above is **TRANSPORT-VALID / LINK-STATE-INCONCLUSIVE**.

A live healthy `413D:2106` node does not prove that the F20 receiver is currently wirelessly linked to the ARMOR-X Pro. Previous physical observation established:

```text
receiver flashing white
  -> 413D:2106 can still be present
  -> RF/controller link not established

receiver solid white
  -> ARMOR-X Pro powered/linked with Xbox controller disconnected
  -> 413D:2106 vendor-HID state

Xbox controller attached through ARMOR-X Pro
  -> receiver may move to an Xbox-compatible USB 045E chain
```

Because the physical LED/link state was not recorded for the transport-valid 0B/EF/D6 run, its zero-reply result must not be interpreted as proof that the linked F20/ARMOR-X Pro session ignores those commands.

## Probe hardening

The next probe revision requires an explicit physical link-state annotation for any real send.

Accepted state vocabulary includes at least:

```text
flashing_white
solid_white
solid_orange
```

The capture records the physical state and whether the result is link-state-inconclusive. The command constants and 65-byte wire frames remain unchanged from the transport-valid run.

The real-send path still requires an explicit send-enable gate. Dry-run opens no target and prints the exact wire frames.

## Next bounded experiment

Required physical state:

```text
F20 receiver:       plugged into Windows
ARMOR-X Pro:        powered ON
Xbox controller:    physically disconnected
F20 LED:            confirmed solid white
USB state:          413D:2106
present USB 045E:   none
```

Then rerun exactly once:

```text
1. pre-post/persist IN
2. A5 04 0B B4
3. collect
4. A5 0C EF 00 00 00 00 00 00 00 00 A0
5. collect
6. A5 04 D6 7F
7. collect + idle watch
8. only if D6 replies: one A5 04 E2 8B
```

Do not send D7, 0E, firmware, DFU or guessed commands.

## Timing review against verified Android init (2026-09-25)

The probe sequence was compared with the verified Android vendor-command
subsequence (`research/windows/probe-timing-review.md`): the probe's order
(persistent IN, 0B, collect, EF, collect, D6) is faithful; the only
Android-observed protocol delay is 500 ms before D6. No command bytes change.
The 2A26-read gate before EF is standard GATT and is not emulated over HID.

## Current conclusion

The Windows host-side transport is proven capable of submitting correctly addressed 65-byte reports, but the Android-derived read sequence has not yet been tested under a positively recorded `solid_white` RF-linked state.

Therefore:

```text
WINDOWS_BRIDGE_TRANSPORT = PROVEN
RUN1_LINK_STATE          = UNKNOWN
RUN1_D6_RESULT           = INCONCLUSIVE FOR LINKED DEVICE
NEXT_GATE                = SOLID_WHITE_REPLAY
```
