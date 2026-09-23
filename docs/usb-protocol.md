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
at offset 0 of a zero-filled buffer. For the tested ARMORX Pro/dongle descriptor,
the HID record size is 64 bytes. The application-side transfer buffer therefore
starts directly with `0xA5`; there is no extra report-ID byte in the buffer
passed by this code path. The transfer timeout in the recovered send routine is
5000 ms.

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

A critical distinction is now statically confirmed:

- `CParserGetMode` builds the 4-byte request `A5 04 E2 8B`.
- `CParserGetMode2` is **not** another `E2` request. Its encoder builds a
  5-byte `A5 05 19 PP CC` packet, where `PP` is a caller-supplied/state
  parameter and `CC` is the additive checksum. Its response decoder expects
  at least 19 bytes.

The exact meaning and value source of `PP` remains **UNKNOWN**, so the toolkit
does not send `GetMode2` yet.

## Current unresolved questions

- Exact first-query sequence for ARMORX Pro versus ARMORX Dongle.
- Whether a controller-attached or paired state is required before some read commands respond.
- Final mapping from protocol mode/device markers to ARMORX Pro and ARMORX Dongle.
- Long-packet framing for full profile and firmware operations.

No write-config, firmware-update, or destructive command is considered documented until independently validated.
