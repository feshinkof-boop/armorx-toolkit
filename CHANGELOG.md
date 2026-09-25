# Changelog

All notable project changes are documented here.

## Unreleased

### Fixed

- Match captured V41 macro wire serialization (`macroJson` is a JSON list of JSON-encoded row strings).
- Serialize `/dev/addMacro` `inUse` as integer `0`/`1`.
- Preserve captured `showAdd=true` behavior for every macro row.
- Correct the structured `res2` config region to raw bytes `74..111` instead of treating it as reserved-only data.

### Added

- Captured the complete normal Android/BLE first-contact path from the current BIGBIG WON app on real hardware.
- Confirmed live runtime identity `ZJ-XT`, firmware revision `2741`, and standard battery characteristic `2A19`.
- Documented the live vendor GATT transport: all-zero vendor service UUID, `FFE1` write-without-response, `FFE2` read/notify, and CCCD `2902`.
- Proved that Android uses the same `A5` frame family and sum-mod-256 checksum as the recovered Windows protocol.
- Decoded indexed `A4` fragmentation for 144-byte payloads.
- Proved D6 as full 144-byte config read and D7 as full 144-byte config write with short D7 acknowledgement.
- Confirmed the config CRC live as CRC-16/MODBUS-style over bytes 2..143 with big-endian storage.
- Live-confirmed `offset 45 = sensorRightCurve0YDivx` during a profile change and `offset 135 = mapKeys[M1]` during M1 -> A remapping.
- Added Android/BLE protocol documentation and a Windows/Android bridge-status document.
- Replayed the Android-derived `0B -> EF -> D6` sequence over the proven Windows HID transport; all writes completed 65/65, but zero input reports were observed.
- Corrected that bridge result to **LINK-STATE-INCONCLUSIVE** because USB identity `413D:2106` does not itself prove the F20 radio link was established; future real runs must record the physical LED/link state.
- Recorded and corrected a Windows `SP_DEVICE_INTERFACE_DETAIL_DATA_W` path-offset bug that could falsely report the target as absent.


- Closed the GetMode transport-size blocker with a read-only live observation: both send and receive workers share an owner whose transfer-size field is `0x40`, so logical interrupt size is **N=64**.
- Recorded the retail hardware labels without serial data: ARMOR-X Pro plus BIGBIG WON Wireless Adapter model **F20**.
- Recorded the corrected physical-state split: ARMOR-X-Pro-alone stays at vendor HID `413D:2106` (solid white receiver), while attaching an Xbox controller can re-enumerate the same receiver through an Xbox-compatible `045E:0B12 -> 045E:02FF` chain.
- Added the first vendor-shaped live GetMode test with IN pre-posted before OUT: two bounded 65-byte writes completed successfully, both reads timed out with zero reply.
- Documented that `413D:2106` is accepted by normal Assistant matcher logic and is classless at VID/PID stage; later product classification depends on a device-derived ZJ-/C4-style mark string.
- Added live Windows Assistant observation: a fresh `413D:2106` arrival triggers native enumeration but no vendor HID session, wrapper call, ReadFile, or WriteFile.
- Established the current Assistant UI failure mode: its configured IE/ActiveX analysis URL now returns only a tiny analytics stub, leaving the native per-device session undriven; status recorded as `UI_TRIGGER_ROOT_CAUSE_PROVEN`.
- Updated the recommended next research branch to passive BIGBIG WON ELITE mobile/Bluetooth analysis, keeping firmware/DFU paths separate.

- Added a 2026-09-25 research handoff covering the current ArmorX/BIGBIG WON USB/HID reverse-engineering state and explicit next static-analysis gates.
- Corrected the GetMode transport record: the logical command is proven, but the vendor's final libusb OUT/IN transfer lengths remain unresolved below the backend operations-table dispatch.
- Documented the live HID metadata for the tested `413D:2106` collection: Usage Page `0xFF7A`, Usage `1`, unnumbered 64-byte input/output reports, and no feature report.
- Documented the corrected unmanaged `OVERLAPPED` implementation and withdrew earlier device-rejection conclusions caused by PowerShell by-ref marshalling.
- Recorded the first confirmed successful GetMode HID report transmission (`STATUS_SUCCESS`, 65 bytes) and the subsequent no-response result from a read posted after the write.
- Recovered the embedded HID backend operations table, the `CUsbCmd` ToPacket/FromPacket vtable, and the `CreateIoCompletionPort`-based completion architecture.
- Regression tests for the captured macro wire format and the `res2` overlap.
- USB/HID protocol research notes covering the shared ARMORX Pro/dongle USB identity and read/query command evidence.
- Deeper vtable/call-site reconstruction: `GetMode` and `GetMode2` share the same `A5 04 E2 8B` request and differ in 16-byte vs 19-byte response layouts. The separate `A5 05 19 PP CC` encoder is `CParserTestMode`.
- Corrected `CDeviceMgr::IdentifyDevice`: it is a bootloader/upgrade path for `4C4A:2342` / `4C4A:3442`, not normal `413D:2106` ARMORX discovery.
- Documented the normal `413D:2106` path through HID record-size discovery and `CDeviceMgr::IsDevice`.
- Documented that the current Assistant 1.0.6.1 `Skin=0` classifier does not assign legacy factory types `2=ArmorX`, `3=ArmorX Pro`, or `4=ArmorX Dongle`, even though those factory cases remain present.
- Reconstructed the byte-level `GetHidRecordSize` parser, including its non-standard descriptor start/stride rules, one-byte Report Count behavior, multi-byte overwrite quirk, `0xC0` state reset, and input-only `m_nBulkSize` calculation.
- Corrected `IsDevice` timing to the nested double-send structure: up to 3 outer attempts × 2 `A5 04 E2 8B` sends, with `Sleep(500)` before each send and a 5000 ms collection window.
- Recorded the required `libusb_claim_interface` step before the report-descriptor/interrupt path.

## 0.1.0 — 2026-09-23

First public release of **ArmorX Toolkit**, an open-source BIGBIG WON ARMORX Pro toolkit for Xbox controller configuration, key mapping, macros, and community/config research.

### Highlights

- Installable `src/armorx` Python package
- Unified `armorx` command with `config`, `macro`, and `community` namespaces
- 144-byte ARMORX Pro config decoder, validator, patcher, and builder
- CRC16 validation and regeneration
- Named Xbox / ARMORX Pro key mapping
- Convenient remapping syntax such as `armorx config map config.json M1=A`
- M1-M4 macro triggers, timed steps, chords, and execution modes
- Read-oriented community/config exchange client
- Evidence-based protocol documentation
- Pytest regression suite and GitHub Actions CI

### Key mapping coverage

Directly documented IDs include A, B, X, Y, LB, RB, LT, RT, View, Menu, L3, R3, D-pad directions, and M1-M4.

Unresolved IDs remain explicitly marked as unknown instead of being guessed.

### Compatibility

The original standalone scripts remain available under `tools/`:

```text
tools/armorx_config.py
tools/armorx_macro.py
tools/armorx_community.py
```

The preferred interface for new users is the unified `armorx` command.

### Research status

This release distinguishes protocol findings as **PROVEN**, **STRONG EVIDENCE**, or **UNKNOWN**. Unknown/reserved config bytes are preserved when patching known-good configurations.

### Known limitations

- Share / Screenshot numeric key ID is still unresolved.
- Firmware-internal raw macro frame encoding is not yet fully documented.
- BLE/device write support is not part of v0.1.0.
- Community commands intentionally stay narrow and do not enumerate identifiers or brute-force share codes.
