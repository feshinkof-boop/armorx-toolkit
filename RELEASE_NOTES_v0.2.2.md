# ArmorX Toolkit v0.2.2

**Public research and protocol-documentation snapshot — 2026-09-28**

v0.2.2 publishes the latest reproducible ARMOR-X Pro / F20 research findings and a current public research-status document.

## What changed

- Documented the F20 dual USB identity: vendor HID `413D:2106` while idle/disconnected and Xbox GIP `045E:0B12` after ARMOR-X association.
- Documented direct ARMOR-X USB power-state switching: red-LED USB-powered/off vendor HID → powered-on Xbox GIP without moving the cable.
- Published live GIP field mapping for A, M1, M2, LT, RT and the stick fields.
- Resolved the apparent 32-byte/48-byte report conflict as startup vs steady-state lengths of the same observed type-`0x20` GIP stream.
- Published the RT digital-synthesis result: ARMOR-X creates D2 RT bit 9 (`0x00000200`) from the analogue RT path.
- Corrected the RT gate interpretation: `r5 & r4` is an intersection gate, not a changed-bit set.
- Recorded `0x1e0a426` as the next bounded target at the analogue-RT/digital-bit junction.
- Corrected `0x1e094de` to a deadzone/direction classifier rather than a normalized-record producer.
- Linked the dedicated research handoff/archive branch and preserved explicit UNKNOWN items instead of filling gaps by inference.

## Downloads

This release publishes source/documentation only:

- `ArmorX-Toolkit-v0.2.2-source.zip`
- `ArmorX-Toolkit-v0.2.2-SHA256SUMS.txt`

## Windows app

The latest validated public Windows configurator remains **v0.2.1**. v0.2.2 does **not** introduce a new Windows binary and does not promote the internal research/capture application into the public app.

## Python toolkit

The installable Python toolkit remains at package version **0.2.0**. This release does not claim a new Python API version.

## Research boundary

Research Lab, Research Autopilot, raw USB/BLE capture, guided physical experiments, unknown-command probing and researcher-only evidence tooling remain separate from the public end-user application.

## Compatibility

Directly validated hardware remains ARMOR-X Pro / ZJ-XT with BIGBIG WON F20 receiver in the documented test environment. Other firmware/hardware combinations should be treated as not independently validated unless explicitly documented.

## Read next

- `docs/research-status-2026-09-28.md`
- `research/physical-armorx-live-2026-09-27` branch handoff archive
