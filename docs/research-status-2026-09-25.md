# ArmorX / BIGBIG WON research status — 2026-09-25

This is the current handoff point for the USB/HID and Windows Assistant reverse-engineering work. It records only evidence suitable for the public repository and intentionally omits host-specific identifiers, serial numbers, account data, private paths, and machine/network details.

## Executive status

The normal Android/BLE control path is now **captured end-to-end** and the low-level Windows HID transport remains **closed/proven**.

Android live traffic establishes:

- runtime mark/model `ZJ-XT`, firmware revision `2741`, and standard battery characteristic `2A19`;
- vendor GATT transport on the all-zero Bluetooth-base service UUID with `FFE1` write-without-response and `FFE2` read/notify;
- the same `A5` frame/checksum family already recovered from Windows;
- indexed `A4` fragmentation for long payloads;
- D6 as a complete 144-byte configuration read;
- D7 as a complete 144-byte configuration write;
- live validation of the config CRC and two existing field mappings.

Windows remains:

- logical interrupt transfer size **N = 64**;
- 65-byte Windows HID input/output reports including report-ID slot 0;
- persistent/pre-posted IN behavior proven;
- vendor-shaped writes complete successfully.

A bounded Windows replay of Android's normal read sequence `0B -> EF -> D6` completed all writes but returned zero input reports. That result is now explicitly **TRANSPORT-VALID / LINK-STATE-INCONCLUSIVE** because the F20's physical LED/RF-link state was not recorded; `413D:2106` alone does not prove the receiver is linked to the ARMOR-X Pro.

The immediate next gate is one read-only replay with the F20 explicitly confirmed **solid white**, ARMOR-X Pro powered on, Xbox controller disconnected, and no present USB 045E composite node. Firmware/DFU remains separate.

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

The Android/BLE path captured the tested controller's runtime mark directly as `ZJ-XT` through the standard Model Number String and advertising/manufacturer data. This closes the controller-side runtime-mark question without inferring it from VID/PID or retail labeling. The exact content of a future E2 marker over the F20 HID path remains unresolved.

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

## Android/BLE milestone

The tested app is `com.moojiang.bigbigwon` v2.23.0609 (versionCode 12), implemented as Flutter/Dart AOT and using `flutter_reactive_ble` / RxAndroidBle2.

The complete normal first-contact sequence was captured on a real non-root Android device with passive Frida instrumentation. The live vendor service is:

```text
00000000-0000-1000-8000-00805f9b34fb
FFE1 = write without response
FFE2 = read + notify
2902 = CCCD
```

Identity reads:

```text
2A24 = ZJ-XT
2A26 = 2741
2A19 = 91% in the captured session
```

Initial app traffic:

```text
A5 04 0B B4
A5 0C EF 00 00 00 00 00 00 00 00 A0
A5 04 D6 7F
```

D6 is proven as a full 144-byte config read. D7 is proven as a full 144-byte config write. Long images use ten indexed A4 fragments, and the per-frame checksum is the same sum-mod-256 rule as Windows.

The 144-byte image's own CRC is independently confirmed live as CRC-16/MODBUS-style over bytes 2..143 with big-endian storage. Controlled UI changes also live-confirmed:

```text
offset 45  = sensorRightCurve0YDivx, 0x0A -> 0x28 on profile change
offset 135 = mapKeys[23] / M1,       0x17 -> 0x00 on M1 -> A
```

See [android-protocol.md](android-protocol.md).

## Windows/Android bridge milestone

A corrected standalone HID probe replayed the Android-derived read sequence over a live `413D:2106` F20 interface. A probe bug was first fixed: the Windows device-interface detail path had been read four bytes too far into `SP_DEVICE_INTERFACE_DETAIL_DATA_W`, producing invalid `?\\hid#...` paths and false target-absent results.

After correction:

- the target opened successfully and matched VID/PID;
- Report ID 0 and 65-byte input/output report sizes were independently confirmed;
- all three writes completed 65/65 with error 0;
- no input reports were observed;
- E2 remained unsent because it was gated on a D6 reply.

The run is **not** a protocol-negative result because the receiver's physical LED/RF-link state was not recorded. USB `413D:2106` can exist while the F20 is not linked to the ARMOR-X Pro.

Future real-send probes now require an explicit physical link-state annotation. The next bounded run must use a confirmed `solid_white` receiver with ARMOR-X Pro on and Xbox controller disconnected.

See [bridge-status-2026-09-25.md](bridge-status-2026-09-25.md).

## Important corrections

- `413D:2106` is accepted by normal device matcher logic; it is not upgrade-only.
- The 045E Xbox-compatible re-enumeration occurred with an Xbox controller physically attached to ARMOR-X Pro and is not the ARMOR-X-Pro-alone state.
- The live logical transfer size is 64, not an unresolved static guess.
- Vendor IN is persistent/pre-posted; the earlier post-write read did not reproduce vendor ordering.
- A fresh vendor-HID arrival does trigger native enumeration, but it does not open a vendor session in the current Assistant/UI state.
- The exact working standalone probe source used in the lab must be treated separately from older/stale copies; do not redeploy an older attachment over the reconciled working build.

## Android static-analysis closure (2026-09-25, second pass)

Full Blutter dumps of 2.23.0609 and 2.24.0919 (verified provenance: APK SHA256
7ed18b77…/0bae884b…; Dart 2.19.6 / 3.2.3) closed the Android static gaps:

- Frame-builder index: 13 functions (2.23) / 21 (2.24) — `research/android-frame-builders-*.json`;
- Response-dispatcher index: 5 (2.23) / 10 (2.24) — `research/android-response-dispatchers-*.json`;
- Internal-buffer vs wire-frame reconciliation (length byte = total frame bytes; A4 len = chunk+5;
  EF request carries eight compiled zero literals) — `research/android-frame-builder-reconciliation.md`;
- EF reply → devUuid → /dev/register dataflow — `research/apk-2.23.0609/ef-dataflow.md`;
- D6 A4 reassembly offsets, completion, and config-length derivation (checkConfigLength,
  0xFE terminator; static 0xfd8/0x1030) — `research/config-format-family-map.md`;
- Factory default templates 88/144/240 (+280/484 in 2.24) with independently recomputed CRCs
  (240-byte template CRC 0x1605 self-validates; live ARMOR-X Pro config equals the bc536085
  144-byte template with recomputed CRC 0x7F67) — `research/default-config-templates.json`;
- Rigorous E2 absence: no reachable E2 frame-construction or response-decoding path in either
  analyzed build;
- D2 corrected to the test-mode UI path (rainbow_test.dart);
- 0E characterized narrowly as a post-write command emitted by multiple workflows;
- Semantic 2.23↔2.24 differential incl. device-enum renumbering (ARMOR-X Pro 6→8) and the
  280/484 C1 Pro-class families — `research/apk-version-diff-2.23-vs-2.24.md`;
- Server API map cross-reconciled with the Windows Assistant (same host/endpoints) —
  `research/server-api-map.md`;
- Windows AB long-packet path decoded (send pacing + receive stream reassembly by AB markers) —
  `research/windows/ab-protocol.md`; web-bridge data-model inventory — `research/windows/web-bridge.md`;
- Probe timing reviewed against the verified Android init order — `research/windows/probe-timing-review.md`.

## 2026-09-26 live BLE addendum

A controlled Windows BLE autonomous suite on firmware 2741 closed several questions that were still open when this 2026-09-25 handoff was written. Full sanitized details are in [live-ble-research-2026-09-26.md](live-ble-research-2026-09-26.md).

New live conclusions:

- D7 applies a valid 144-byte configuration to the current/live state.
- A D7-only change reverted after power cycle in the controlled test.
- The same D7 change followed by `A5 05 0E 00 B8` survived power cycle; for the tested configuration path, 0E is therefore the persistence step.
- `D2 01` enables a continuous ~64 Hz raw-input stream and `D2 00` disables it; the 18-byte raw report layout is decoded in the live-BLE document.
- key ID 12 is live-proven as Guide / Xbox / Mode through a controlled M1 remap.
- ID 15 is only a provisional Share/Capture/Screenshot candidate because the structured chooser and operator note conflict.
- AE01 is WriteWithoutResponse and AE02 is Notify; passive AE02 subscription succeeded, but no AE traffic appeared during clean idle windows.
- standalone and controller-attached D6 images and GATT inventories matched in the tested session.

The autonomous run began from a previously persisted M1 -> B state. That image is a test-start baseline, **not** a factory/default reference.

## Current unresolved questions

- Actual E2/GetMode response, if any, from the tested F20 + ARMOR-X Pro pair in a positively recorded linked state.
- Why the F20 HID path produced no input during the transport-valid but link-state-inconclusive `0B -> EF -> D6` replay.
- Whether E2 requires a state transition not exercised by the Android app.
- Broader semantics of 0E outside the tested configuration-write persistence path.
- AE01 application-write semantics and whether AE02 is used by another feature/state.
- Whether a recoverable historical Assistant web page would initiate the legacy Windows vendor session.
- Exact final Windows ReadFile system-call length below the backend branch.
- Exact runtime value of backend config `+0x6/+0x7`.
- Exact FC/DPI command semantics, FF lighting payload structure, and D8 macro device encoding.
- Clean confirmation of key ID 15 and purpose-specific testing of IDs 5, 20, 21, 22, 27, 28, 29, 30, and 31.

## Recommended next research branch

The broad Android/BLE capture milestone is complete. Do not repeat broad reconnaissance; use targeted experiments for the remaining named gaps.

Next:

1. keep the Android capture and field-correlation results as the normal-protocol reference;
2. repeat the Windows `0B -> EF -> D6` bridge test once with the F20 physically confirmed `solid_white`, ARMOR-X Pro on, Xbox controller disconnected, and no present USB 045E composite node;
3. preserve raw 65-byte HID input reports before interpretation;
4. issue one E2 only if D6 replies in that same initialized session;
5. if the linked-state run remains silent, compare the standalone Windows HID open/claim/I/O behavior against the vendor backend instead of guessing new command permutations;
6. keep config writes, firmware and DFU outside this read-only bridge gate.

## Evidence discipline

Use the repository's evidence labels consistently:

- **PROVEN** — directly established by live observation or static dataflow.
- **STRONG EVIDENCE** — multiple independent signals agree but a final link remains unresolved.
- **UNKNOWN** — deliberately unresolved.

Do not infer device-side mark strings, firmware state, or destructive command semantics from human-readable product names alone.
