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

### STRONG EVIDENCE

Static analysis of `CDeviceMgr` shows a discovery path built around:

```text
FindDevice
GetMatchDevice
IsMatchDevice
IdentifyDevice
GetDeviceVidPid
CParserGetMode
CParserGetMode2
```

This is consistent with the observed shared VID/PID: the PC software enumerates a common USB candidate first, then uses protocol-level information to decide which concrete device class is present.

The recovered identification routine contains both `CParserGetMode` and
`CParserGetMode2` paths. Around synchronous command transactions it waits
approximately 500 ms and uses a 5000 ms command timeout.

A deeper vtable/call-site reconstruction corrects an earlier misidentification:

- `CParserGetMode` and `CParserGetMode2` share the same command encoder at
  `0x1003E320`.
- Both therefore issue the same 4-byte request: `A5 04 E2 8B`.
- `CParserGetMode::Decode` accepts the 16-byte response layout.
- `CParserGetMode2::Decode` accepts the 19-byte response layout.
- The separate `A5 05 19 PP CC` encoder belongs to `CParserTestMode`, not
  `CParserGetMode2`.

The device-matching routine sends the shared `E2` query and can interpret the
reply using either response layout. It retries the identification transaction
up to three times, with an approximately 500 ms delay between attempts and a
5000 ms command timeout.

For the 16-byte layout, the recovered code extracts a 9-byte device marker from
response bytes 6..14. For the 19-byte layout it extracts the corresponding
9-byte marker from response bytes 9..17. Those marker bytes are then used by
the higher-level device matcher.

## Current unresolved questions

- Whether a controller-attached or paired state is required before the shared `E2` identification query responds.
- Exact marker strings returned by ARMORX Pro and ARMORX Dongle on the tested hardware.
- Final mapping from all protocol marker variants to concrete product/firmware combinations.
- Long-packet framing for full profile and firmware operations.

No write-config, firmware-update, or destructive command is considered documented until independently validated.
