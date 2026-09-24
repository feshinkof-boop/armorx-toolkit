# Changelog

All notable project changes are documented here.

## Unreleased

### Fixed

- Match captured V41 macro wire serialization (`macroJson` is a JSON list of JSON-encoded row strings).
- Serialize `/dev/addMacro` `inUse` as integer `0`/`1`.
- Preserve captured `showAdd=true` behavior for every macro row.
- Correct the structured `res2` config region to raw bytes `74..111` instead of treating it as reserved-only data.

### Added

- Regression tests for the captured macro wire format and the `res2` overlap.
- USB/HID protocol research notes covering the shared ARMORX Pro/dongle USB identity and read/query command evidence.
- Deeper vtable/call-site reconstruction: `GetMode` and `GetMode2` share the same `A5 04 E2 8B` request and differ in 16-byte vs 19-byte response layouts. The separate `A5 05 19 PP CC` encoder is `CParserTestMode`.
- Corrected `CDeviceMgr::IdentifyDevice`: it is a bootloader/upgrade path for `4C4A:2342` / `4C4A:3442`, not normal `413D:2106` ARMORX discovery.
- Documented the normal `413D:2106` path through HID record-size discovery and `CDeviceMgr::IsDevice`.
- Documented that the current Assistant 1.0.6.1 `Skin=0` classifier does not assign legacy factory types `2=ArmorX`, `3=ArmorX Pro`, or `4=ArmorX Dongle`, even though those factory cases remain present.

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
