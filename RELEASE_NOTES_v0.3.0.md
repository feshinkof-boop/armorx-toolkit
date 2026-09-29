# ArmorX Toolkit v0.3.0

Python/Linux/offline toolkit release — 2026-09-29.

This release turns the project's proven protocol and USB research into a
read-only public toolkit. It does **not** replace the Windows configurator;
the latest Windows application remains **v0.2.1**.

## Highlights

- Read-only Linux USB discovery for the observed `413D:2106` vendor-HID and
  `045E:0B12` Xbox personalities.
- `armorx device doctor` with privacy-sanitized diagnostics bundles.
- Offline A5/A4 framing, checksum, fragmentation and reassembly tooling.
- Offline Xbox type-`0x20` GIP parsing with proven A, M1, M2, LT and RT fields.
- Classic usbmon PCAP, raw-byte and hex-dump capture inspection.
- Versioned config/macro exchange envelopes with canonical JSON validation and
  deterministic SHA-256 content IDs.
- New CLI groups: `device`, `protocol`, `gip`, `capture`, and `exchange`.

## Validated on real hardware

The release candidate was exercised against an ARMOR-X Pro on Linux:

- The live power transition `045e:0b12` <-> `413d:2106` was observed on the
  same physical USB port.
- LT and RT matched Linux `ABS_Z` / `ABS_RZ` sample-for-sample by timestamp.
- A, M1 and M2 matched their documented wire bits and evdev key events.
- Capture inspection matched an independent parser on real usbmon captures.
- The real-host diagnostics bundle passed privacy checks.

## Fixes discovered by hardware validation

- Corrected multi-interface USB numbering.
- Decoded printable sysfs serial values instead of presenting a hex dump.
- Stopped restricted unrelated hidraw nodes from incorrectly making
  `device doctor` fail.
- Prevented GIP reports containing incidental `0xA5` bytes from being
  misclassified as phantom A5 protocol frames.
- GIP stick fields now expose raw and two's-complement readings without claiming
  signedness/scaling that has not yet been live-proven.
- Removed the unsupported claim that the previously observed 32-byte report is
  a universal "startup form."

## Validation

- **187 tests passed, 0 failed, 0 skipped.**
- GitHub Actions passes Python **3.10, 3.11, 3.12 and 3.13**.
- Wheel and sdist were built, the wheel was installed into a clean environment,
  and the CLI was smoke-tested.
- No public v0.3.0 command transmits configuration or firmware data to a device.

## Known non-blocking unknowns

- A controlled release-validation capture begun before power-on saw only
  48-byte type-`0x20` reports (76,382 reports total). The previously observed
  32-byte form remains supported for compatibility, but its existence/role and
  the earlier 45.8-second observation are not treated as general behavior.
- Stick signedness/scaling still needs a dedicated live stick sweep.
- The cause of trigger quantisation remains unknown.
- Several additional buttons have not yet been live-confirmed.
- Vendor-personality payload behavior remains an open research question.

## Downloads

The v0.3.0 release publishes:

- `armorx_toolkit-0.3.0-py3-none-any.whl`
- `armorx_toolkit-0.3.0.tar.gz`
- `ArmorX-Toolkit-v0.3.0-source.zip`
- `ArmorX-Toolkit-v0.3.0-SHA256SUMS.txt`

Windows users who want the GUI should continue using the validated
**ArmorX Windows v0.2.1** release.
