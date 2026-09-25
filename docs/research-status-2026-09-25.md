# ArmorX / BIGBIG WON research status — 2026-09-25

This is the current handoff point for the USB/HID and Windows Assistant reverse-engineering work. It records only evidence suitable for the public repository and intentionally omits host-specific identifiers, serial numbers, account data, private paths, and machine/network details.

## Executive status

The low-level Windows HID transport gate is now **closed** for the tested BIGBIG WON wireless adapter:

- the logical interrupt transfer size is **N = 64**, recovered live from both the receive and send worker objects;
- the tested HID collection is unnumbered and exposes 65-byte Windows input/output reports (one report-ID slot plus 64 logical bytes);
- the vendor receive worker keeps an IN transfer outstanding before OUT traffic;
- a corrected unmanaged-overlapped standalone probe successfully completed 65/65-byte writes of the recovered GetMode request with a pre-posted 65-byte read.

However, **two cold standalone GetMode attempts produced no response**. The remaining problem is not Windows write acceptance or the N value.

The current Windows Assistant 1.0.6.1 path was then observed directly. A real fresh arrival of the normal 413D:2106 vendor HID caused native enumeration activity, but the Assistant opened no vendor HID session and issued no vendor ReadFile/WriteFile traffic. The hosted UI URL used by the application now returns only a tiny analytics stub rather than the historical application page. This provides the best code-supported explanation for the permanently idle/grey device UI in this build.

The next research branch should therefore treat the obsolete Windows web UI separately from the normal ARMOR-X Pro control path. Passive analysis of the BIGBIG WON ELITE mobile/Bluetooth workflow is the highest-value normal-device path; firmware/DFU flows remain separate.

## Physical hardware identification

Photographs of the tested hardware establish the retail labels directly:

- controller attachment: **BIGBIG WON ARMOR-X Pro**;
- wireless receiver: **BIGBIG WON Wireless Adapter, model F20**.

No serial number is recorded in this repository.

Observed physical states:

- ARMOR-X Pro off: receiver slowly flashes white;
- ARMOR-X Pro on, Xbox controller disconnected: receiver becomes solid white and the PC-side identity is the normal 413D:2106 vendor HID;
- ARMOR-X Pro on with an Xbox controller attached: the same physical receiver can re-enumerate into a Microsoft/Xbox-compatible identity chain (observed 045E:0B12 -> 045E:02FF).

The last state is controller-attached passthrough behavior and must not be confused with the ARMOR-X-Pro-alone vendor state.

## Tested normal vendor-HID identity

The normal ARMOR-X-Pro-alone receiver state resolves as:

```text
VID:                 0x413D
PID:                 0x2106
USB class:           HID
Usage Page:          0xFF7A
Usage:               0x0001
Manufacturer:        Zikway
Product string:      HID zkm
Input report bytes:  65
Output report bytes: 65
Feature report bytes:0
Report ID:           0 / unnumbered
```

The underlying HID data payload is 64 bytes in each direction. The Windows report buffer is 65 bytes because byte zero is the report-ID slot.

## BIGBIG WON handling of 413D:2106

Static analysis of Assistant 1.0.6.1 `DevMgr.dll` proves that the normal VID/PID matcher accepts:

```text
413D:2114
413D:2104
413D:2106
```

For these 413D devices the VID/PID stage stores the packed identifier and leaves the concrete product type at the default/classless value. Product classification happens later from a device-derived mark/model string.

The later classifier compares against mark strings including:

```text
C4_DONGLE
C4_SERVER
ZJ-MJC6
ZJ-C2SLD
ZJ-C1pro
ZJ-RANIBO
ZJ-Rainbo
ZJ-C2SL
ZJ-BLACK_
ZJ-C1ZJD
ZJ-C1ZJ
ZJ-GALE_L
ZJ-GALE
```

Which mark the tested F20/ARMOR-X Pro pair actually returns remains a runtime fact and is **UNKNOWN** until captured. Do not infer a specific mark from VID/PID or a human-readable retail label.

The same 413D family also appears in firmware-upgrade logic. In particular, 2104/2106 are referenced by a NearLink/BS25 DFU path using Usage Page 0xFFB1. That is distinct from the live normal collection at Usage Page 0xFF7A and does not make the normal 413D:2106 collection DFU-only.

## GetMode request and response parsing

The recovered GetMode request is exactly:

```text
A5 04 E2 8B
```

Checksum:

```text
checksum = sum(previous bytes) & 0xFF
A5 + 04 + E2 = 0x18B -> 0x8B
```

Recovered E2 decoders:

- normal form: minimum 16 logical bytes, `A5`, opcode `E2`, checksum at byte 15, 9-byte marker at bytes 6..14;
- longer/GetMode2 form: minimum 19 logical bytes, checksum at byte 18, 9-byte marker at bytes 9..17.

The separate `A5 05 19 PP CC` encoder is TestMode, not GetMode2.

## Runtime transfer-size closure

The long-standing `m_nBulkSize` blocker is closed.

The receive and send worker objects have different vtables but both point through `worker+0x1C` to the same owner record. The owner's first DWORD was read live as:

```text
owner+0x00 = 0x00000040
```

Therefore:

```text
logical interrupt transfer size N = 64
```

This is **RUNTIME-PROVEN**.

Static aliasing remains:

```text
request      = transfer_base + 0x58
request+0x10 = transfer_base + 0x68
```

so the wrapper length and backend transfer length are the same storage.

The HID backend config bytes `+0x6` and `+0x7` are still **STRONG EVIDENCE** for zero-initialized values based on the calloc-like allocation path and absence of later writers. The branch direction itself is proven: when `config+0x7 == 0`, the Windows-side HID write length is logical length + 1.

## Vendor receive choreography

The receive worker is persistent rather than request-local. Its loop:

- checks its stop event;
- posts one interrupt IN transfer;
- uses a 5000 ms timeout;
- dispatches the received packet;
- returns to the loop and re-arms.

This establishes that vendor traffic normally has an IN outstanding before OUT traffic.

Response dispatch uses the current `CUsbCmd` pointer and virtual slot 2 -> `CUsbCmd::FromPacket`. `FromPacket` stores the response and calls `SetEvent(CUsbCmd+0x88)`.

## Corrected live GetMode probe

Earlier PowerShell attempts used an invalid managed/by-ref `OVERLAPPED` pattern. A device-free named-pipe reproduction proved that pattern could report false incomplete results.

The corrected primitive uses:

- stable unmanaged `OVERLAPPED` storage;
- stable unmanaged buffers;
- fresh auto-reset events;
- `CancelIoEx` on timeout;
- `GetOverlappedResult` with the same exact `OVERLAPPED` pointer;
- pre-posted IN before OUT.

A one-shot standalone transaction then produced:

```text
OUT requested:   65
OUT transferred: 65
OUT completion:  success / error 0
IN requested:    65
IN result:       timeout / 0 bytes
```

A single permitted retry produced the same result.

The exact standalone OUT report was:

```text
00 A5 04 E2 8B 00 ... 00
```

65 bytes total: report-ID slot `00`, 4-byte GetMode command, then zero padding to the 64-byte logical transport size.

This proves the host-side transport can submit that report successfully. It does **not** prove that the device recognizes cold E2 in that state or that the vendor's own reusable logical buffer always contains zero tail bytes.

## Windows Assistant live observation

Architecture-correct WOW64 module enumeration confirmed that `DevMgr.dll` is loaded by the live Assistant process. Earlier 64-bit module enumeration was misleading because it exposed only the WOW64 loader view.

A read-only Frida observer was placed on the logical interrupt wrapper at `DevMgr.dll + 0x4C8B0` and also instrumented relevant Win32 I/O APIs.

With ARMOR-X Pro on, Xbox controller disconnected, and the F20 receiver present as 413D:2106:

- a real unplug/replug produced a fresh normal vendor-HID arrival;
- native enumeration began about one second later;
- the observer remained healthy and uncapped;
- no vendor HID handle was opened;
- wrapper calls remained zero;
- vendor `ReadFile` / `WriteFile` remained zero;
- no E2 or any other vendor frame was issued.

This retires the hypothesis that another physical cycle alone will make the current Assistant open the vendor session.

## Windows Assistant UI root cause

The Assistant hosts an IE/ActiveX page through `CWebBrowserEx` / WndMgr. Its configured analysis URL is:

```text
http://app.mojhon.cn/HTML/Analysis/BigBigWonAssistant.51la.html
```

The same value is present in the application's URL configuration.

Direct HTTP requests using multiple user-agent variants and the application's own query parameters returned HTTP 200 but only a tiny analytics/tracker stub, not the historical application markup/JavaScript. No usable cached copy was found.

The native bridge still exists:

```text
CWebBrowserEx::Invoke
window.external
```

and the native device-manager layer is created, but the page that historically drove the per-device session is no longer present server-side.

The current best-supported status is therefore:

```text
UI_TRIGGER_ROOT_CAUSE_PROVEN
```

with one explicit limit: a working historical page was not separately replayed, so it is not claimed that every valid page would necessarily open this exact device session. What is proven is that the current configured page contains no application UI logic capable of doing so.

## Important corrections

- `413D:2106` is accepted by normal device matcher logic; it is not upgrade-only.
- The 045E Xbox-compatible re-enumeration occurred with an Xbox controller physically attached to ARMOR-X Pro and is not the ARMOR-X-Pro-alone state.
- The live logical transfer size is 64, not an unresolved static guess.
- Vendor IN is persistent/pre-posted; the earlier post-write read did not reproduce vendor ordering.
- A fresh vendor-HID arrival does trigger native enumeration, but it does not open a vendor session in the current Assistant/UI state.
- The exact working standalone probe source used in the lab must be treated separately from older/stale copies; do not redeploy an older attachment over the reconciled working build.

## Current unresolved questions

- What mark/model string the tested F20 + ARMOR-X Pro returns through the device identification protocol.
- Why the device does not answer a cold standalone E2 despite correct N=64 framing and pre-posted IN.
- What benign initialization/handshake, if any, normally precedes E2 in a functioning control application.
- The exact normal Bluetooth/BLE protocol used by the BIGBIG WON ELITE mobile app with ARMOR-X Pro.
- Whether a recoverable historical Assistant web page would initiate the legacy Windows vendor session.
- Exact vendor ReadFile system-call length below the backend branch (the logical receive size is proven N=64 and the HID report metadata is 65 bytes, but the final Windows ReadFile call was not independently disassembled).
- Exact runtime value of backend config `+0x6/+0x7` (zero remains strongly supported, not live-read).

## Recommended next research branch

Do not spend more time power-cycling the receiver or trying to force the obsolete Windows UI.

The highest-value next phase is:

1. preserve the Windows Assistant findings as a legacy/reference implementation;
2. analyze the BIGBIG WON ELITE mobile application;
3. capture the normal Bluetooth/BLE conversation with ARMOR-X Pro passively first;
4. identify the normal runtime identity/version/configuration handshake;
5. keep firmware/DFU/update behavior separate from normal configuration research.

## Evidence discipline

Use the repository's evidence labels consistently:

- **PROVEN** — directly established by live observation or static dataflow.
- **STRONG EVIDENCE** — multiple independent signals agree but a final link remains unresolved.
- **UNKNOWN** — deliberately unresolved.

Do not infer device-side mark strings, firmware state, or destructive command semantics from human-readable product names alone.
