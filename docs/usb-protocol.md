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

It parses HID report size/count/main items and stores the resulting record size.
`CUsbRecvThread::ReadFromUsb` requests that record size from the IN endpoint
with a 5000 ms timeout. For `0xA5` short frames it uses byte 1 as the actual
short-frame length. Separate `0xA4` / `0xAB` receive/reassembly paths exist
but are not yet fully decoded.

The recovered short-packet send path passes the monitor's full HID record size
(`m_nBulkSize`) to `libusb_interrupt_transfer`, with the short command copied
at offset 0 of a zero-filled buffer. `m_nBulkSize` is derived by
`CUsbMonitor::GetHidRecordSize` from the HID report descriptor rather than
being hard-coded from the endpoint's 64-byte max-packet value.

On the tested hardware, the interrupt endpoints advertise 64-byte max packets,
while the Windows HID layer exposes a 65-byte output-report buffer (report ID
byte plus report data). The exact `m_nBulkSize` value selected by DevMgr for
this descriptor has not yet been observed dynamically, so the toolkit does not
collapse those two facts into a guessed transfer length.

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

`IsDevice` performs up to three identification attempts, with an approximately
500 ms delay around attempts and a 5000 ms command timeout.

The exact ARMORX Pro / Dongle marker responses remain pending direct USB
capture. A read-only reproduction should therefore calculate the official HID
record size first, start the IN reader before sending, and send only this proven
`E2` query when testing the identification path.

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
