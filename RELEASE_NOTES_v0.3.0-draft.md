# v0.3.0 draft release notes

Status: draft for a development branch. Nothing here is released, tagged or
hardware-validated. No command in this release transmits to a device.

## Added

* `armorx.protocol`: A5/A4 framing, sum-mod-256 checksum, A4 fragment building and
  index-keyed reassembly, a recovered opcode table with evidence levels, and
  stream splitting.
* `armorx.gip`: an offline parser for the observed Xbox GIP input stream, covering
  the 32-byte startup and 48-byte steady-state forms and the proven control
  offsets, with unknown bytes retained.
* `armorx.device`: read-only discovery on Linux, classification of the two
  observed identities with explicit caveats, and a `doctor` diagnostic.
* `armorx.transport`: a transport seam with a scripted mock and an optional
  read-only hidraw transport. Writes are refused by default.
* CLI groups `device`, `protocol` and `gip`.
* Documentation: `docs/v0.3.0-release-plan.md`, `docs/linux-support.md`,
  `docs/offline-tools.md`.

## Notes for testers

* No ARMORX hardware is required for anything added in this release.
* `armorx device doctor` on a machine with no hardware is expected to succeed and
  report that nothing is present.
* Offsets and opcode meanings were established from live captures and recovered
  documentation; unresolved items are labelled unknown in the code and the docs.
