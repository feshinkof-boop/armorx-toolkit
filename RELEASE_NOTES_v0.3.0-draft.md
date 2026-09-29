# v0.3.0 draft release notes

Status: draft on a development branch. Nothing here is released or tagged, and
PR #8 stays a draft. Read-only paths were validated against real hardware on
2026-09-29; interactive controls were not (see the interactive checklist). No
command in this release transmits to a device.

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


## Hardware validation, 2026-09-29

* Device discovery and `device doctor` were validated against an attached unit in
  the `045E:0B12` personality. Two real defects were found and fixed: interface
  numbering on multi-interface devices, and the sysfs serial being presented as a
  hex dump.
* `device doctor` no longer treats a restricted hidraw node as a blocking
  condition, because none of the read-only paths need hidraw. It now reports
  findings separately from blocking checks.
* The diagnostics bundle was generated on the real host and scanned: no username,
  home path, hostname, serial number, MAC address or credential appears in it.
* A 120 s passive usbmon capture produced 62,702 records and 30,009 GIP reports,
  all 48-byte, with the full 255-value sequence rollover.
* The capture parser was checked against an independent extraction and matched
  exactly, and one real defect was found and fixed: a GIP report whose sequence
  byte is `0xA5` could produce a phantom checksum-valid frame.

## Interactive validation, 2026-09-29 (operator present)

* LT, RT, A, M1 and M2 were exercised with one popup per action and the wire was
  correlated to `evdev` by timestamp, never by nearest frame: both triggers
  matched `ABS_Z`/`ABS_RZ` sample for sample, and the three buttons matched their
  key events to within one report interval.
* The power-state transition `045e:0b12` <-> `413d:2106` was observed live on the
  same USB port, including the off-state report descriptor, which is byte-identical
  to the F20 receiver identity.
* One decoder defect was found and fixed: stick axes were reported as raw unsigned
  words with no caveat even though the project documents sticks as signed
  elsewhere. The decoder now reports both readings and states that neither the
  signedness nor the scaling to the host axis range is established.
* Regression tests were added from the real captured reports.

## Not validated

* Stick signedness and scaling: no stick sweep has been correlated to evdev.
* The 32-byte starting report form did not appear at all in a 340 s capture that
  began before power-on; the earlier 45.8 s switchover observation is unreproduced.
* The D-pad, View, Menu, Guide, L3/R3 and Capture buttons.
* Reading the vendor personality's hidraw node, which is root-only by default.
