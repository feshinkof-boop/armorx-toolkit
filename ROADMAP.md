# Roadmap

ArmorX Toolkit is intentionally evidence-driven. Items move from research to stable support only after reproducible confirmation.

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
- [ ] Add a schema-aware config editor
- [ ] Add a macro visualizer
- [ ] Add a config diff command
- [ ] Add import/export helpers for community-shared configs
- [ ] Add an optional desktop GUI

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
