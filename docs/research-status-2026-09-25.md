# ArmorX / BIGBIG WON research status — 2026-09-25

This document is the current handoff point for the USB/HID reverse-engineering work. It records only evidence suitable for the public repository and intentionally omits host-specific identifiers, private paths, account data, and machine/network details.

## Executive status

The current blocker is **not** command checksum, Windows HID framing, or basic device access. Those pieces are now substantially understood.

The remaining gate is the vendor application's exact libusb submission choreography:

1. the final value assigned to the libusb transfer object's length field for GetMode OUT/IN;
2. the exact ordering/lifecycle of the receive transfer relative to the OUT command.

Until both are closed statically, further live GetMode probing is **not justified**.

## Tested live HID identity

A present device matching the historical BIGBIG WON candidate was resolved uniquely as:

```text
VID:                0x413D
PID:                0x2106
USB class:          HID (03/00/00), non-composite
Usage Page:         0xFF7A
Usage:              0x0001
Manufacturer:       Zikway
Product string:     HID zkm
Input report ID:    0
Output report ID:   0
Input report bytes: 65
Output report bytes:65
Feature report bytes:0
```

The value caps show one unnumbered 64-byte input report and one unnumbered 64-byte output report. The extra byte in the Windows buffers is the report-ID slot, which is `0x00`.

This identity alone still does **not** prove an exact retail product name.

## BIGBIG WON ownership of 413D:2106

Static analysis of Assistant 1.0.6.1 `DevMgr.dll` shows that BIGBIG WON explicitly recognizes:

```text
413D:2104
413D:2106
413D:2114
```

For `413D:2106`, the matcher stores the packed VID/PID but leaves the BIGBIG device type as the unresolved/default value. Product classification happens later from a device-supplied model string rather than from VID/PID alone.

The only firmware-upgrade code path naming `413D:2106` directly is the Rainbow3-dongle NearLink/BS25 DFU path. That proves a Rainbow3-dongle relationship in the updater, but does **not** prove that every normal-mode `413D:2106` device is a Rainbow3 dongle.

## ArmorX strings and product types

The binary contains:

```text
ARMOR-X
ARMOR-X Pro
ARMOR-X Dongle
```

but there is no `CDeviceArmorX` RTTI class and no direct static VID/PID -> ArmorX mapping.

Those names live in a separate product-type/display-name table. Therefore the repository must not infer "ArmorX Pro" or "ArmorX Dongle" from `413D:2106` alone.

## Runtime model-string source

The runtime classifier `CDeviceMgr::IsDevice` does not receive the model string as a function argument. It obtains it from a device query and then compares it against known model codes such as:

```text
ZJ-C2SLD
ZJ-C2SL
ZJ-GALE_L
ZJ-GALE
ZJ-Rainbo
ZJ-RANIBO
ZJ-C1pro
ZJ-C1ZJ
ZJ-C1ZJD
C4_SERVER
C4_DONGLE
```

The missing value is therefore **device-derived**, not server-derived.

## GetMode protocol

The recovered GetMode request builder produces exactly:

```text
A5 04 E2 8B
```

Checksum:

```text
checksum = sum(previous bytes) & 0xFF
A5 + 04 + E2 = 0x18B -> 0x8B
```

The checksum algorithm was independently confirmed against another frame stored precomputed in the binary.

The normal decoder expects an `A5 10 E2 ...` response and extracts the model marker from logical response bytes `[6..13]`. A second decoder variant expects a longer E2 layout.

## Windows HID report metadata

Live metadata proved:

- Output `ReportID = 0`
- Input `ReportID = 0`
- 64 data bytes each direction
- 65-byte Windows report buffers
- no feature report

That rules out treating `0xA5` as a HID report ID for this collection.

## Corrected overlapped-I/O finding

Two early PowerShell probe attempts used a managed by-ref `OVERLAPPED` structure. That implementation was invalid for pending I/O because P/Invoke marshalled temporary copies between calls.

A device-free named-pipe reproduction proved the defect: a successful 1 MiB overlapped write was incorrectly observed as `ERROR_IO_INCOMPLETE` with zero transferred.

The corrected primitive uses:

- unmanaged 32-byte `OVERLAPPED` storage;
- the same stable pointer for submit/completion/cancellation;
- unmanaged or pinned I/O buffers;
- a fresh auto-reset event per operation;
- bounded cancellation with `CancelIoEx`.

The corrected primitive was validated locally and then on the HID handle.

## Confirmed live transaction result

With the corrected primitive, a 65-byte unnumbered output report:

```text
00 A5 04 E2 8B 00 00 ... 00
```

completed successfully through Windows:

```text
STATUS_SUCCESS
65 bytes transferred
```

A fresh 65-byte input read posted **after** that write received no report within the recovered 5000 ms window and was cancelled cleanly.

This proves Windows accepted and transmitted that 65-byte HID report. It does **not** prove:

- that the firmware recognized E2 in that padded form;
- that the vendor application itself submits 65 bytes;
- that the firmware replies to a read posted after the OUT report;
- the exact retail product identity.

## libusb backend closure

The embedded Windows HID backend is dispatched through a static operations table.

Recovered:

```text
backend ops table: 0x101F8678
transport slot:    0x101F86B8 -> 0x10055BE0
table installer:   0x10058054
```

`CUsbCmd::ToPacket` and `CUsbCmd::FromPacket` are adjacent virtual methods in the same vtable:

```text
vtable:        0x102425FC
slot 1:        0x10049390  ToPacket
slot 2:        0x10049430  FromPacket
COL:           0x1025053C
```

The HID handle is attached to an I/O completion port with `CreateIoCompletionPort`. The backend uses overlapped I/O and an IOCP-style completion architecture. This confirms that receive completion is handled by an independent actor rather than by the command caller directly.

## New application-side transfer-wrapper trace

A later static narrowing pass corrected the previous assumption that the final transfer-length trace was blocked entirely behind the backend operations table.

`CUsbSendThread::WriteToUsb` contains direct calls into an inner transfer wrapper at `0x1004CC50`:

```text
0x10049CF8  short-packet send -> call 0x1004CC50
0x10049F8D  long-packet send  -> call 0x1004CC50
0x1004A146  short-packet send -> call 0x1004CC50
```

All three sites supply a `0x1388` (5000 ms) timeout. The surrounding send-thread region is approximately `0x10049Bxx-0x1004A1xx`; the receive-side counterpart and the remaining monitor-field references lie approximately in `0x1004A500-0x1004AA00`.

This materially narrows the unresolved transfer-length gate: the next static step is now a bounded direct trace through `0x1004CC50` to the libusb transfer constructor/fill path and the store into transfer `+0x68`, rather than another search for a caller of `0x10055BE0`.

The IOCP core is likewise localized to `0x10050xxx-0x10052xxx`, including `GetQueuedCompletionStatus` at `0x10051D76`, `PostQueuedCompletionStatus` at `0x10050CDF`, `CancelIoEx` at `0x100510F8`, and `GetOverlappedResult` at `0x10051191`. The HID-open path's `CreateIoCompletionPort` call remains at `0x1005B2F6`.

**Correction:** `CancelIoEx` and `GetOverlappedResult` are present and called inside the image's IOCP core. Earlier wording that described them as merely imported was too broad; the narrower statement is only that they were not observed on the already-traced GetMode caller path.

The backend operations table remains live and is compared by pointer identity in several backend routines (including references to `0x101F86C8`, `0x101F86D8`, `0x101F86CC`, and `0x101F86C4`).

**Gate status remains unchanged:** the exact numeric OUT/IN values assigned to transfer `+0x68`, the receive re-arm edge, and the exact IN-vs-OUT submission ordering are still deliberately **UNKNOWN** until those bounded blocks are read instruction-by-instruction.

## Still unknown

The following are deliberately unresolved:

- exact GetMode OUT value assigned to libusb transfer `+0x68`;
- exact GetMode IN transfer length;
- exact Windows WriteFile/ReadFile lengths used by the vendor for E2;
- exact IN-vs-OUT submission ordering;
- whether the IN request is permanent/re-armed;
- the concrete completion callback that invokes `CUsbCmd::FromPacket`;
- the runtime value/source of the HID backend `config+0x7` report-ID-placement flag;
- the exact device model marker returned by the tested `413D:2106` unit;
- exact retail product mapping for that unit.

## Next static work

Before another live transaction:

1. resolve COL `0x1025053C` to the concrete class;
2. trace consumers of the backend ops table installed at object `+0x68`;
3. locate the libusb transfer creator/submission wrapper and close the assignment into transfer `+0x68`;
4. locate the IOCP service thread / `GetQueuedCompletionStatus` callback chain;
5. recover the receive re-arm edge and exact IN/OUT ordering;
6. resolve the completion key and the writer of `config+0x7`.

Only when the transfer length and ordering are proven should a new live GetMode attempt be designed.

## Evidence discipline

Use the repository's evidence labels consistently:

- **PROVEN** — directly established by live observation or static dataflow.
- **STRONG EVIDENCE** — multiple independent signals agree but a final link remains unresolved.
- **UNKNOWN** — deliberately unresolved.

Do not upgrade `413D:2106` to an ArmorX, ArmorX Pro, ArmorX Dongle, Rainbow3 Dongle, or other retail product name until the runtime model marker is captured and mapped through the recovered factory.
