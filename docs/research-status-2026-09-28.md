# ARMOR-X Pro research status — 2026-09-28

This document is the public, evidence-oriented snapshot of the current ARMOR-X Pro / F20 reverse-engineering state. It intentionally separates reproducible protocol findings from internal capture/autopilot tooling.

The full research handoff archive is preserved on the GitHub branch:

`research/physical-armorx-live-2026-09-27`

The latest verified local research tip used for this snapshot is `8747846` (full SHA `87478461e662ede8f056cbcf8b35b44c10c8fbd5`). The local suite reported **495 passed + 12 subtests**; a fresh clone reported **489 passed + 6 skipped**.

## USB identity and power state

### F20 receiver

Two USB personalities are directly observed:

- **Vendor/idle personality:** `413D:2106`, manufacturer `Zikway`, product `HID zk`, vendor HID Usage Page `0xFF7A`, 64-byte interrupt IN/OUT endpoint maximums.
- **Xbox operating personality:** after ARMOR-X wireless association, the F20 disconnects/re-enumerates on the same physical port as `045E:0B12` and Linux `xpad` binds.

The vendor personality is therefore not the normal gameplay interface in the observed connected state.

### Direct ARMOR-X USB

Direct USB shows the same high-level split:

- USB cable attached, power button not pressed, red LED: `413D:2106` vendor HID.
- Pressing the ARMOR-X power button without moving the cable causes a USB disconnect/re-enumeration to `045E:0B12`, then Xbox GIP input streaming begins and `xpad` exposes the controller.

The red LED observation is recorded as a physical state, not assigned an undocumented semantic such as “charging” or “configuration mode”.

## Xbox GIP input map

For the PC-visible type-`0x20` input stream, the live map currently includes:

- A: byte 4 bit `0x10`
- M1: byte 4 bit `0x20`
- M2: byte 5 bit `0x40`
- LT: bytes 6-7, little-endian `u16`
- RT: bytes 8-9, little-endian `u16`
- left stick: bytes 10-13
- right stick: bytes 14-17

### Report length variants

The earlier 32-byte vs 48-byte discrepancy is resolved as two lengths of the same observed type-`0x20` stream:

- 32-byte startup form after enumeration;

> Correction, 2026-09-29: a capture begun before power-on produced only the 48-byte
> form from the first frame, 50 ms after enumeration, so the 32-byte form is no longer
> described as a startup form. See `docs/v0.3.0-interactive-hardware-validation.md`.
- 48-byte steady-state form;
- in the preserved power-state capture, the last 32-byte frame occurs at about 45.7805 s and the first 48-byte frame at about 45.8125 s.

What causes that switchover remains **UNKNOWN**.

## RT analogue → digital synthesis

The Xbox-facing RT representation has no separately observed digital RT bit. ARMOR-X creates its own D2 digital RT state internally.

Current proven static facts:

- D2 RT digital mask bit: `0x00000200` (bit 9).
- `r4` at the synthesis gate is the current candidate mask.
- `r5` is loaded from persistent `[r15+0x1d0]`.
- `r5 & r4` is an **intersection gate**, not a changed-bit set.
- The ARMOR-X code explicitly clears bit 9 with `0xfffffdff` or sets it with `0x200` based on the result of `0x1e0a426`.
- `0x1e0a426` is therefore at the key junction between the analogue RT byte and the predicate that controls RT digital bit 9.
- The exact internal behavior of `0x1e0a426` — threshold, scaling, pass-through, or another transform — remains **UNKNOWN**.

The later edge/synthesis block can also write `0xff` / `0x00` into the trigger candidate byte, while the analogue path supplies intermediate values. This reconciles earlier live observations containing intermediate RT values and `255`.

## Important correction: `0x1e094de`

`0x1e094de` is **not** the producer of the 28-byte normalized state record.

It is a compact deadzone/direction classifier that examines signed halfwords at offsets `+0x04`, `+0x06`, `+0x08`, and `+0x0a` against an approximately ±12000 threshold and returns direction-bit flags.

## Still open

The main unresolved items are:

- exact behavior of `0x1e0a426`;
- meaning and producers/consumers of persistent `[r15+0x1d0]`;
- exact ordering of trigger synthesis relative to the D2 comparison/emission gate;
- the internal USB-host receive callback and report buffer;
- the object behind `usbh_gamepadp`;
- exact store provenance into `state+0x1d4`;
- the RT live-ramp timing discrepancy;
- the precise reason RT-only motion does not independently produce the same D2 emission behavior observed when another event causes the current trigger state to be sampled.

## Next highest-value step

Reverse `0x1e0a426` completely. It is a small, bounded target at the junction where the analogue RT byte is normalized and where the predicate controlling bit `0x200` is produced.

## Public-release boundary

The public Windows configurator remains separate from the research/capture application. Raw capture automation, research autopilot, unknown-command probing, evidence-bundle collection, and other researcher-only workflows are not promoted into the end-user Windows build by this documentation release.
