# Changelog

All notable project changes are documented here.

## Unreleased

## 0.2.2 — 2026-09-28

Public research and protocol-documentation snapshot. This release updates the public repository with the latest reproducible ARMOR-X Pro / F20 findings while keeping research/capture tooling separate from the end-user Windows application.

### Public release scope

- Added a public 2026-09-28 research-status document and linked the dedicated research handoff branch.
- Published the latest protocol findings without promoting researcher-only capture/autopilot tooling into the public Windows app.
- Kept the latest public Windows binary release at **v0.2.1**; v0.2.2 is a source/documentation research snapshot.
- Kept the Python toolkit package version at **0.2.0**; no Python API compatibility claim is changed by this release.

### Research snapshot — 2026-09-28

- Confirmed the F20 receiver has two observed USB personalities: vendor HID `413D:2106` while idle/disconnected and Xbox GIP `045E:0B12` after ARMOR-X association.
- Confirmed direct ARMOR-X USB follows the same power-state split: USB-powered/off with a red LED exposes `413D:2106`; pressing the power button without moving the cable re-enumerates as `045E:0B12` and binds to Linux `xpad`.
- Mapped live PC-visible Xbox GIP fields for A, M1, M2, LT, RT and both sticks.
- Resolved the apparent 32-byte/48-byte report conflict: the same type-`0x20` GIP input stream uses a 32-byte startup form and a 48-byte steady-state form; the cause of the switchover remains unknown.
- Proved that ARMOR-X synthesizes RT digital bit 9 (`0x00000200`) from the analogue RT path rather than copying a separate digital RT bit from the Xbox report.
- Traced `r4` to the current candidate mask and `r5` to persistent `[r15+0x1d0]`; corrected `r5 & r4` from a “changed-bit set” interpretation to an **intersection gate**.
- Located `0x1e0a426` at the analogue-RT-to-digital-bit junction; its exact threshold/scaling behavior remains the highest-priority static target.
- Corrected `0x1e094de`: it is a deadzone/direction classifier over four signed axis halfwords, not the producer of the 28-byte normalized record.
- Kept unresolved items explicit: the internal USB-host receive callback/buffer, the object behind `usbh_gamepadp`, exact `state+0x1d4` store provenance, the meaning of `[r15+0x1d0]`, and the remaining RT timing/emission questions.

### Research documentation — 2026-09-27

- Added the real BIGBIG WON 4.0.8 official-app vs Linux-harness BLE session differential.
- Confirmed `OFFICIAL_WORKS_HARNESS_SILENT`: the official app produces valid `A5 12 02` Button Test reports while the preserved Linux harness session did not.
- Corrected the D2 success criterion: the official app produces zero Button Test frames while idle; reports are event-driven and repeat while a button is held.
- Refuted bonding/encryption as the D2 prerequisite: the working official session was unbonded and unencrypted.
- Confirmed official and harness D2 use the same `A5 05 D2 01 7D` payload, Write Command `0x52`, handle `0x0075`, MTU 64, and the same FFE1/FFE2/CCCD handles.
- Recorded the first protocol-sequence difference: official performs `EF -> 0B -> E2 -> D4 -> D6` before D2, while the harness performs `0B -> D2 OFF -> D2 ON`; causality remains unresolved.
- Recorded the connection-interval difference (official final 11.25 ms vs harness 7.50 ms) as evidence, not as a proven cause.


## 0.2.1 — 2026-09-27

Public Windows safety and reliability release.

### Windows public app

- Added automatic full 144-byte pre-write backups before configuration writes.
- Added exact pending-change review with byte offsets and before/after values.
- Added clear dirty/pending-change state in the public UI.
- Added one-click restore of the latest backup with full read-back verification.
- Restore now creates a pre-restore backup first, making restoration reversible.
- Before writing, the app re-reads the controller and merges only edited semantic bytes onto the fresh device image so unrelated/reserved bytes remain preserved.
- Kept D7 full-image write, persistence, and complete 144-byte read-back verification as the required successful write path.
- Added a tested per-user Windows installer alongside the portable single-file EXE and folder-build fallback.
- Kept Research Lab, Research Autopilot, raw BLE capture, D2/AE experiments, unknown-ID sweeps, and evidence-bundle tooling out of the public app.

### Validation

- Promoted directly from the validated Final RC artifact built from commit `5133de9612e83613dd8741f9f61f51910c2ee77f`.
- Public self-test passed.
- WPF/XAML UI smoke test passed.
- Silent installer test passed.
- Installed-app self-test passed.
- Silent uninstaller test passed.
- Published release tag `v0.2.1` points exactly to the frozen validated commit.

### Compatibility

- Directly validated hardware baseline remains ARMOR-X Pro / ZJ-XT, firmware 2741.
- Other firmware versions remain not yet independently validated.

## 0.2.0 — 2026-09-26

Second public release of **ArmorX Toolkit**.

This release remains the installable Python toolkit/CLI. The Windows research/capture application, Autopilot runner, raw BLE recorder, guided experiment UI, and researcher-only diagnostics are not included as public release features.

### Public toolkit highlights

- Live-proven Guide / Xbox / Mode mapping is available as key ID `12`.
- V41 macro serialization now matches captured client wire format.
- `/dev/addMacro` serializes `inUse` as integer `0`/`1`.
- Macro rows preserve captured `showAdd=true` behavior.
- Structured config `res2` correctly mirrors raw bytes `74..111`.
- Unknown and unresolved IDs remain unassigned rather than guessed.
- Python 3.10–3.13 remains covered by CI.

### Fixed

- Match captured V41 macro wire serialization (`macroJson` is a JSON list of JSON-encoded row strings).
- Serialize `/dev/addMacro` `inUse` as integer `0`/`1`.
- Preserve captured `showAdd=true` behavior for every macro row.
- Correct the structured `res2` config region to raw bytes `74..111` instead of treating it as reserved-only data.

### Research documentation updates

The following are published protocol/documentation findings, not public GUI/device-control features:

- Added sanitized results from the 2026-09-26 autonomous Windows BLE research suite on firmware 2741.
- Proved by controlled power-cycle testing that D7 applies the current 144-byte config to live/volatile state, while `A5 05 0E 00 B8` persists that written config across power loss.
- Decoded D2 on ARMOR-X Pro as a ~64 Hz raw-input test stream and documented the 18-byte report layout, including buttons, sticks, and analog triggers.
- Live-confirmed map key ID 12 as Guide / Xbox / Mode; ID 15 remains a provisional Share/Capture/Screenshot candidate because the recorded observations conflict.
- Documented AE01 as WriteWithoutResponse and AE02 as Notify with passive subscription; no AE traffic was observed during clean tested idle windows.
- Confirmed the 144-byte D6 image and GATT inventory were unchanged between standalone and controller-attached states in the tested session.
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
