# ARMOR-X Pro live BLE autonomous research — 2026-09-26

This document records the public, sanitized findings from one controlled Windows BLE autonomous research run against a user-owned BIGBIG WON ARMOR-X Pro on firmware `2741`.

No BLE address, controller UUID, account identifier, serial number, or host-specific path is published here.

## Run integrity

- Research app: Windows BLE Research Autopilot v0.2.9
- Run status: completed
- Duration: about 8m39s
- Automatic BLE recoveries: 4
- No application warning/error/fatal entries were present in the run log.
- Final cleanup restored the exact 144-byte configuration captured at suite start.

### Baseline caveat

The suite-start configuration was **not** treated as a factory/default reference.

It was a previously persisted M1 -> B state:

```text
CRC:            0x1F81
mapKeys[23]:    0x01 (B)
```

An earlier known-good M1 -> A state used during the controlled persistence toggle was:

```text
CRC:            0x8F8C
mapKeys[23]:    0x00 (A)
```

The autonomous suite correctly restored what it found at startup. The test-start image must not be described as a factory default.

## GATT inventory

The tested normal vendor path remained:

```text
service 00000000-0000-1000-8000-00805f9b34fb
FFE1    WriteWithoutResponse, Write
FFE2    Read, Notify
FFE2    CCCD 2902
```

The second vendor-looking family was:

```text
service AE00
AE01    WriteWithoutResponse
AE02    Notify
AE02    CCCD 2902
```

Passive AE02 subscription succeeded. No guessed AE01 writes were sent.

Standalone and controller-attached GATT inventories were identical in this run.

## Clean idle observations

A clean standalone idle window and a controller-attached idle window produced:

- no unsolicited vendor traffic;
- no AB frames;
- no AE receive events;
- no disconnects during the measured windows.

This is evidence for those tested idle states only; it does not prove those transports can never be used.

## D7 and 0E persistence semantics

A one-byte logical config change (M1 target B -> A, plus CRC) was used as a reversible probe.

### D7 without 0E

1. D7 wrote the complete 144-byte target image.
2. D6 immediately read the target image back exactly.
3. The device was power-cycled.
4. D6 after reconnect returned the previously persisted image instead.

Result:

```text
D7-only persistence across power cycle = false
```

### D7 followed by 0E

The same D7 target was written again, followed by:

```text
A5 05 0E 00 B8
```

After power-cycle and reconnect, D6 still returned the target image exactly.

Result:

```text
D7 + 0E persistence across power cycle = true
```

Supported conclusion for the tested ARMOR-X Pro configuration path:

```text
D7 applies the complete config to live/volatile state.
0E persists that written config across power loss.
```

This conclusion is intentionally limited to the observed config-write path and does not claim the firmware's broader internal implementation.

In this Windows BLE run, each 0E transmit was followed by two identical FFE2 notifications of `A5 05 0E 00 B8`.

## D2 raw-input test mode

Commands:

```text
enable   A5 05 D2 01 7D
disable  A5 05 D2 00 7C
```

While enabled, the controller streamed 4,812 valid 18-byte reports over 75.20 seconds, approximately 63.98 reports/s. All captured report checksums validated.

Observed report layout:

```text
byte 0      A5
byte 1      12
byte 2      02
byte 3      rear buttons: bit0=M2, bit1=M3, bit2=M4
byte 4      bit0=D-pad Up, bit1=Down, bit2=Left, bit3=Right, bit7=M1
byte 5      bit0=LT digital, bit1=RT digital, bit5=L3, bit6=R3
byte 6      bit0=A, bit1=B, bit3=X, bit4=Y, bit6=LB, bit7=RB
bytes 7..8  left-stick X, signed 16-bit big-endian
bytes 9..10 left-stick Y, signed 16-bit big-endian
bytes 11..12 right-stick X, signed 16-bit big-endian
bytes 13..14 right-stick Y, signed 16-bit big-endian
byte 15     LT analog 0..255
byte 16     RT analog 0..255
byte 17     additive checksum modulo 256
```

Observed stick extrema were -32768 and +32767.

This closes the main ARMOR-X Pro D2 semantic gap: it is a controller-test/raw-input streaming mode.

## mapKeys sweep through M1

Each target below was written into `mapKeys[23]`, read back byte-for-byte, physically exercised through M1, and then restored to the captured test baseline.

| ID | Result | Public status |
|---:|---|---|
| 12 | Guide / Xbox / Mode action observed | PROVEN LIVE |
| 15 | operator note says `screenshot`, but structured chooser recorded Guide/Mode | PROVISIONAL Share/Capture/Screenshot candidate |
| 5 | no visible action in this test | UNRESOLVED |
| 20 | no visible action in this test | UNRESOLVED |
| 21 | no visible action in this test | UNRESOLVED |
| 22 | no visible action in this test | UNRESOLVED |
| 27 | no visible action in this test | UNRESOLVED |
| 28 | no visible action in this test | UNRESOLVED |
| 29 | no visible action in this test | UNRESOLVED |
| 30 | no visible action in this test | UNRESOLVED |
| 31 | no visible action in this test | UNRESOLVED |

The no-visible-action result does not establish that an ID is reserved or globally unused.

## Standalone vs controller-attached state

Within this controlled run:

- the 144-byte D6 config was byte-for-byte identical before and after physically attaching ARMOR-X Pro to the Xbox controller;
- the GATT inventory was identical;
- no unsolicited AB or AE traffic appeared in the attached idle window.

## Remaining gaps

The following remain deliberately unresolved:

- exact FC/DPI command semantics;
- exact FF lighting payload structure;
- D8 macro device encoding;
- AE01 application write semantics;
- Android UI value-scaling/transform rules not yet covered by controlled diffs;
- clean confirmation of ID 15 as Share/Capture/Screenshot;
- purpose-specific testing for IDs that produced no visible action.

