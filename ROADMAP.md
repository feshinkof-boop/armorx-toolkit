# Roadmap

ArmorX Toolkit is intentionally evidence-driven. Items move from research to stable support only after reproducible confirmation.

## Research snapshot — 2026-09-28

- [x] Publish a dedicated public research handoff branch and archived patch series
- [x] Document F20 vendor-HID → Xbox-GIP dual USB identity
- [x] Document direct ARMOR-X USB power-state identity switching
- [x] Map live GIP A/M1/M2/LT/RT/stick fields
- [x] Resolve 32-byte startup vs 48-byte steady-state GIP input forms
- [x] Prove internally synthesized RT digital bit 9 (`0x00000200`)
- [x] Trace `r4` and `r5` into the RT synthesis gate and correct `r5 & r4` to an intersection gate
- [ ] Reverse `0x1e0a426` and characterize the RT threshold/scaling rule
- [ ] Resolve the exact D2 trigger-only scheduling/emission gate
- [ ] Recover the internal USB-host receive callback, report buffer, and `usbh_gamepadp` object
- [ ] Close exact `state+0x1d4` producer/store provenance

## Near term

- [x] Document the 144-byte ARMORX Pro configuration envelope
- [x] Implement CRC16 validation and regeneration
- [x] Document proven Xbox / ARMORX Pro key IDs
- [x] Implement named M1-M4 remapping
- [x] Implement macro JSON generation and validation
- [ ] Verify the remaining unresolved `mapKeys` IDs (ID 12 Guide/Mode is now live-proven; IDs 5, 20-22, 27-31 still unresolved)
- [ ] Cleanly confirm provisional ID 15 as Share / Capture / Screenshot
- [ ] Add more controlled config-diff fixtures
- [ ] Add hardware validation notes for multiple firmware versions

## Tooling

- [x] Turn the current scripts into a single installable CLI
- [x] Add a schema-aware config editor
- [x] Add a macro visualizer
- [ ] Add a config diff command
- [ ] Add import/export helpers for community-shared configs
- [x] Add a public Windows desktop GUI
- [x] Add a guarded Linux desktop GUI with visual config editor, local profiles and offline macro timeline
- [x] Add per-user Linux desktop launcher/package

## Public Windows v0.2.1

- [x] Automatic pre-write backup of the current device image
- [x] Review exact byte-level config changes before writing
- [x] One-click restore of the latest backup with write/read-back verification
- [x] Clear dirty/pending-changes state
- [x] Profile rename, duplicate, delete, import, and export
- [x] Exportable end-user diagnostic log without research/capture controls
- [x] About/compatibility page with app, model, firmware, and project information
- [x] Windows installer/package after portable-build validation

## Protocol research

- [ ] Capture the proven `A5 04 E2 8B` identification response with a read-only DevMgr-matched probe across the controlled ARMORX Pro/dongle physical states
- [ ] Recover how older Windows Assistant builds mapped normal `413D:2106` devices to legacy factory types `2` / `3` / `4`
- [x] Decode the `0xA4` long-packet framing and the Windows `0xAB` stream-reassembly path
- [x] Complete the core BLE config read/write/persistence path (D6, D7, 0E)
- [x] Decode ARMOR-X Pro D2 raw-input test mode
- [ ] Identify the live producer/payload semantics of `0xAB`
- [ ] Decode FC/DPI, FF lighting, and D8 macro device payloads
- [ ] Document additional controller parameter fields
- [ ] Validate joystick directional macro pseudo-keys
- [ ] Expand firmware compatibility matrix
- [ ] Document newer community/config listing behavior where reproducible

## Community

- [ ] Collect anonymized test vectors
- [ ] Add contributor hardware/firmware matrix
- [ ] Publish verified config recipes for common games
- [ ] Build a searchable mapping/macro example library
