# ARMORX Pro USB/HID protocol research

This document records currently verified low-level findings for the BIGBIG WON ARMORX Pro family. It intentionally separates hardware observations, static-analysis evidence, and unresolved questions.

## Evidence levels

- **PROVEN** — directly observed on hardware or confirmed by captured traffic/static code.
- **STRONG EVIDENCE** — multiple independent observations agree, but final hardware confirmation is still pending.
- **UNKNOWN** — deliberately unresolved.

## USB identity

### PROVEN

Both an ARMORX Pro connected directly over USB and the ARMORX dongle enumerate with the same public USB/HID identity:

```text
VID:          0x413D
PID:          0x2106
Manufacturer: Zikway
Product:      HID zkm
bcdDevice:    0x0100
Interface:    0
Usage Page:   0xFF7A
Usage:        0x0001
```

The HID interface exposes:

```text
Endpoint 0x03 OUT  interrupt  max packet 64  interval 8 ms
Endpoint 0x83 IN   interrupt  max packet 64  interval 8 ms
```

There are no feature reports exposed by the tested HID descriptor.

VID/PID and descriptor strings alone therefore do **not** distinguish ARMORX Pro from the dongle.

## PC assistant transport

### PROVEN from static analysis

The Windows device library contains:

```text
CUsbMonitor::GetHidRecordSize
CUsbMonitor::SendCmd
CUsbSendThread::WriteToUsb
CUsbRecvThread::ReadFromUsb
```

and uses `libusb_interrupt_transfer` for device I/O.

`CUsbMonitor::GetHidRecordSize` obtains the HID report descriptor with a
standard control transfer:

```text
bmRequestType = 0x81
bRequest      = 0x06
wValue        = 0x2200
wIndex        = 0
timeout       = 1000 ms
```

The routine first claims the interface through `libusb_claim_interface`;
a negative claim result aborts this path. Its report-descriptor parser is not a
standards HID parser. The recovered byte-level behavior is:

- parsing begins at the 8-bit offset `(descriptor[0] + 1) & 0xFF`;
- item stride is `(prefix & 3) + 1`, except size-code 3 is forced from 4 to 5;
- `0x74..0x77` updates Report Size from the single byte at `idx+1`;
- `0x94..0x97` clears EDX/Report Count, then each encoded data byte overwrites
  EDX before being shifted by 0/8/16/24 bits. A normal one-byte `0x95`
  Report Count therefore works as expected, while multi-byte counts do **not**
  combine as a normal little-endian integer: only the final encoded byte,
  shifted to its position, survives;
- `0x80..0x83`, `0x90..0x93`, and `0xB0..0xB3` accumulate
  `ReportSize * ReportCount` into separate Input, Output, and Feature totals;
- `0xC0..0xC3` clears both Report Count (EDX) and Report Size;
- other relevant HID globals such as Report ID / Push / Pop are ignored by this
  custom parser;
- the final monitor record size is `(input_bits + 7) / 8`: **Input total
  only**. Output and Feature totals do not contribute.

That result becomes `m_nBulkSize`, the length used for both interrupt OUT
sends and interrupt IN reads.

`CUsbRecvThread::ReadFromUsb` requests that record size from the IN endpoint
with a 5000 ms timeout. For `0xA5` short frames it uses byte 1 as the actual
short-frame length. Separate `0xA4` / `0xAB` receive/reassembly paths exist
but are not yet fully decoded.

The short-command path is proven to carry the command's own logical length
through `CUsbCmd` (for GetMode, 4 bytes) and then enters the embedded libusb
backend through a runtime operations table. A later closure pass found that the
final assignment into the libusb transfer object's length field (`+0x68`) is
below that dispatch boundary and has **not** yet been recovered. Therefore the
repository no longer treats the exact Windows `WriteFile` length used by the
vendor as proven.

On the tested hardware, live HID metadata shows an unnumbered 64-byte input
report and unnumbered 64-byte output report, exposed to Windows as 65-byte
buffers including report ID `0x00`. A corrected live probe proved Windows
accepts a 65-byte padded GetMode report, but that does **not** establish that
the vendor application itself submits 65 bytes. The exact vendor transfer
length remains pending static closure through libusb's submission layer.

The application-side short-command buffer itself starts with `0xA5`; no
additional protocol wrapper is added before the command. The recovered
`libusb_interrupt_transfer` send call uses a 5000 ms timeout.

The library also contains explicit device-family strings for:

```text
ArmorX
ArmorX Pro
ArmorX Dongle
```

so device-type discrimination happens above the common USB identity.

## Packet families

### PROVEN from static analysis

Short commands use the `0xA5` packet family.

Longer transfer paths also contain separate framing/reassembly logic; those formats are not yet considered fully documented here.

A simple checksum helper used by decoded short commands is:

```text
checksum = sum(previous packet bytes) & 0xFF
```

## Read/query commands

The following request encodings are recovered from the Windows device library and old client implementation. Their presence/decoder logic is proven; hardware response behavior is still being validated.

| Operation | Request | Response evidence |
|---|---|---|
| GetMode | `A5 04 E2 8B` | parser requires at least 16 bytes, checks `A5`, command `E2`, and checksum |
| GetZkmVersion | `A5 04 0B B4` | parser accepts `A5 05 0B VV CC` |
| GetProfileSize | `A5 04 D3 7C` | parser checks `A5`, command `D3`, and checksum |
| GetMacroList | `A5 04 D5 7E` | dedicated parser exists |

Captured legacy application traffic identifies an ARMOR-X Pro with:

```text
firmwareVersion = 41
zkmVersion      = 48 decimal (0x30)
```

Therefore a `GetZkmVersion` response carrying version byte `0x30` is **STRONG EVIDENCE** for that tested firmware lineage, but remains pending direct USB capture.

## Device identification flow

### PROVEN from static analysis

A deeper call-site reconstruction corrects an earlier interpretation:
`CDeviceMgr::IdentifyDevice` is **not** the normal classifier for the shared
`413D:2106` ARMORX identity.

`CDeviceMgr::IdentifyDevice` at `0x10035750` is reached from
`GetDeviceVidPid` for bootloader/upgrade VID/PID pairs:

```text
4C4A:2342
4C4A:3442
```

That path dynamically references `BTUpgrade_HX.dll`. The normal
`413D:2106` discovery path does not invoke this routine.

For a recognized normal USB candidate such as `413D:2106`, the recovered path
is:

```text
GetDeviceVidPid
  -> recognized VID/PID record
  -> open libusb handle
  -> interrupt endpoint discovery
  -> bulk endpoint fallback if interrupt discovery fails
  -> HID report-descriptor parse / record-size calculation
  -> IsDevice when no pre-identified concrete type exists
  -> factory construction if IsDevice returns a supported device type
```

For `413D:2106`, `GetDeviceVidPid` stores the packed VID/PID and leaves the
type/identify field at `0`, so a later classifier is required before a
concrete device object can be constructed.

### Current Assistant 1.0.6.1 / Skin=0 classifier

The shipped `Skin.ini` contains:

```ini
[General]
Skin=0
```

The downstream factory still contains legacy cases:

```text
type 2 -> ArmorX
type 3 -> ArmorX Pro
type 4 -> ArmorX Dongle
```

However, the analyzed `Skin=0` path in `CDeviceMgr::IsDevice`
(`0x1002E8F0`) contains no assignment of legacy result types `2`, `3`, or
`4`.

This is **PROVEN static evidence** for the analyzed build. It means the current
Assistant retains the legacy ARMORX classes and factory cases, but its normal
`Skin=0` discovery mapping does not expose a route from the shared
`413D:2106` identity to those legacy factory types. This is consistent with a
legacy ARMORX device leaving the current UI's **Connect Device** state
unavailable, but it does not by itself prove how every older Assistant build
behaved.

### E2 / GetMode identification query

The recovered `CParserGetMode` and `CParserGetMode2` paths share the same
encoder at `0x1003E320` and both issue:

```text
A5 04 E2 8B
```

The response layouts differ:

- `CParserGetMode::Decode`: minimum 16 bytes; checks `A5`, command `E2`,
  validates the checksum at byte 15, and extracts a 9-byte marker from bytes
  6..14.
- `CParserGetMode2::Decode`: minimum 19 bytes; checks the same `A5` / `E2`
  fields, validates the checksum at byte 18, and extracts a 9-byte marker from
  bytes 9..17.

The separate `A5 05 19 PP CC` encoder belongs to `CParserTestMode`, not
`CParserGetMode2`.

The recovered `IsDevice` timing is more specific than a simple three-attempt
loop. There are up to three **outer** attempts, and each outer attempt can send
the same E2 query twice:

```text
repeat up to 3 outer attempts:
    Sleep(500 ms)
    send A5 04 E2 8B
    collect/parse for up to 5000 ms
    if no valid identification:
        Sleep(500 ms)
        send A5 04 E2 8B again
        collect/parse for up to 5000 ms
```

So the failure path can issue up to six E2 queries. The send thread has special
pre-send delays for other opcodes (notably `0x0E` and `0x70` variants), but
the E2 query has no additional send-thread delay beyond the `IsDevice`
`Sleep(500)` calls above.

The exact ARMORX Pro / Dongle marker responses remain pending direct USB
capture. A read-only reproduction should claim the interface, calculate the
DevMgr record size with the custom parser above, start the IN reader before
sending, and send only this proven `E2` query using the nested timing above.

Do not infer the legacy ARMORX Dongle marker from newer/current classifier
strings merely because one contains the word `DONGLE`; raw capture is still
required to establish the legacy marker.

## Current live/static GetMode status — 2026-09-25

### PROVEN

- The live `413D:2106` HID collection is unique on the tested system and uses
  Usage Page `0xFF7A`, Usage `0x0001`.
- Input and output report IDs are both `0`; each carries 64 bytes of data,
  exposed as 65-byte Windows HID report buffers. No feature report is exposed.
- GetMode logical request is exactly `A5 04 E2 8B`; the checksum is the
  additive byte sum modulo 256.
- The runtime model marker is device-derived through the GetMode path; it is
  not supplied by the vendor server.
- A corrected unmanaged-overlapped probe completed a 65-byte HID output report
  with `STATUS_SUCCESS` and 65 bytes transferred.
- A fresh input read posted **after** that write received no report within the
  recovered 5000 ms collection window.
- The embedded HID backend is installed through a static operation table at
  `0x101F8678`; its transport slot points to `0x10055BE0`.
- `CUsbCmd::ToPacket` and `CUsbCmd::FromPacket` are virtual methods in the
  same vtable at `0x102425FC`.
- Device-open code attaches the HID handle to an I/O completion port with
  `CreateIoCompletionPort`. Receive completion is therefore handled by an
  independent IOCP actor rather than by the command caller directly.

### Important correction

Two early live attempts used a managed by-ref `OVERLAPPED` PowerShell P/Invoke
pattern. A device-free named-pipe reproduction proved that pattern could report
`ERROR_IO_INCOMPLETE` / zero bytes after a successful asynchronous transfer.
Those two completion results are therefore not valid evidence of device
rejection.

The corrected primitive uses unmanaged `OVERLAPPED` storage, stable unmanaged
buffers, fresh auto-reset events, and `CancelIoEx` for bounded cancellation.

### Static trace update: direct application-side transfer wrapper

A subsequent narrowing pass found that `CUsbSendThread::WriteToUsb` does not jump directly from the command object into the HID backend. Three send sites call an inner wrapper at `0x1004CC50`:

```text
0x10049CF8  short packet -> 0x1004CC50
0x10049F8D  long packet  -> 0x1004CC50
0x1004A146  short packet -> 0x1004CC50
```

Each site supplies the 5000 ms timeout. The matching receive-side wrapper is localized to approximately `0x1004A500-0x1004AA00`.

This corrects the previous tracing model: the exact transfer-length assignment is now reachable through a bounded direct call chain. The remaining work is to read `0x1004CC50` through the libusb transfer fill/submission code and identify the exact store into transfer `+0x68`, then recover the IN submission/re-arm edge from the receive block.

The IOCP core is localized to `0x10050xxx-0x10052xxx`; relevant calls include `GetQueuedCompletionStatus` at `0x10051D76`, `PostQueuedCompletionStatus` at `0x10050CDF`, `CancelIoEx` at `0x100510F8`, and `GetOverlappedResult` at `0x10051191`. The HID handle is attached to the completion port at the already recovered open path.

These addresses narrow the gate but do not yet prove the numeric OUT/IN transfer lengths or ordering.

### Current gate

Do **not** treat another live GetMode probe as justified until both are
statically closed:

1. the exact GetMode OUT/IN value written into the libusb transfer length field
   `+0x68`;
2. the exact receive submission ordering / re-arm lifecycle relative to OUT.

The current static handoff is documented in
[research-status-2026-09-25.md](research-status-2026-09-25.md).

## Current unresolved questions

- Actual `E2` / GetMode response, if any, from ARMORX Pro and ARMORX Dongle in the controlled physical states.
- Legacy ARMORX Pro and Dongle marker strings, if their firmware responds to `E2`.
- How older Windows Assistant versions reached factory types `2` / `3` / `4`, or whether a different detector path/version supplied those types.
- Exact runtime HID record size selected by `CUsbMonitor` for the tested descriptor.
- Why the earlier direct PyUSB test reported a 65-byte write against a 64-byte interrupt max packet while receiving no reply.
- Full `0xA4` / `0xAB` long-packet framing and profile/macro device-write behavior.
- Meaning/source of the eight caller-provided bytes in the recovered `GetUUID` request shape `A5 0C EF <8 bytes> CC`.

Earlier direct HID/PyUSB timeouts are not treated as evidence that the
statically recovered commands are invalid because those probes did not yet
reproduce the complete official monitor/thread initialization sequence.

No write-config, firmware-update, or destructive command is considered documented until independently validated.
