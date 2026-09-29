# ArmorX Toolkit v0.5.0 — Linux desktop configurator

v0.5.0 turns the guarded Linux BLE backend from v0.4.0 into a normal desktop
configuration workflow while keeping the protocol/write implementation in one
place.

The public Windows configurator remains the separate **v0.2.1** release.

## Linux GUI

- PySide6 desktop application via `armorx-gui`.
- BLE scan and live 144-byte D6 configuration read.
- M1-M4 remapping, known trigger/stick/sensor/turbo byte controls and exact
  pending-change diff.
- Native Apply & Verify confirmation using the released v0.4 write backend.
- Automatic pre-write backup and exact-byte rollback.
- Privacy-safe local profiles stored under the XDG application data directory.
- Visual stick/trigger deadzone controls and recovered stick curve-byte
  control-point previews.
- Offline 1..16-step macro timeline with chords, timing, execution mode,
  validation and JSON import/export.

## Hardware validation

The actual GUI path was supervised on ARMOR-X Pro model ZJ-XT / firmware 2741.
A controlled M1 B→A edit changed only the CRC bytes plus `mapKeys[23]`, was
applied through the native Qt confirmation and released backend, produced A on
the passive USB GIP wire, and survived a power cycle. GUI rollback then wrote
the exact saved baseline; two D6 reads and a final power cycle matched the
original baseline byte-for-byte.

Final restored baseline SHA-256:

`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`

## Safety boundaries

- The GUI contains no second D6/D7/0E implementation.
- Apply keeps the v0.4 safety contract: two agreeing reads, verified automatic
  backup, exact decoded/unknown diff, default unknown-byte refusal, explicit
  confirmation, one D7 write, one persistence command and two read-backs.
- The GUI does not expose the CLI advanced unknown-byte write override or
  unrelated-state rollback override.
- The macro timeline is **offline only** in v0.5.0; device macro installation
  remains outside this release.
- Visual curve/deadzone graphics are raw-byte previews and do not claim
  unproven firmware scaling.

## Linux installation

Release assets include:

- `armorx_toolkit-0.5.0-py3-none-any.whl`
- `armorx_toolkit-0.5.0.tar.gz`
- `ArmorX-Toolkit-Linux-v0.5.0.tar.gz`
- `ArmorX-Toolkit-Linux-v0.5.0-SHA256SUMS.txt`

Desktop bundle:

```bash
tar -xzf ArmorX-Toolkit-Linux-v0.5.0.tar.gz
cd ArmorX-Toolkit-Linux-v0.5.0
./install.sh
```

The installer creates a private per-user virtual environment and a KDE/
freedesktop launcher. It needs Internet access to obtain PySide6 and Bleak.

Direct Python install:

```bash
python -m pip install "armorx-toolkit[gui] @ git+https://github.com/feshinkof-boop/armorx-toolkit.git@v0.5.0"
armorx-desktop install
armorx-gui
```

## Validation

- Development baseline: **374 passed, 0 failed, 0 skipped** before
  release-prep-only version/documentation changes.
- CI covers Python 3.10, 3.11, 3.12 and 3.13.
- Package CI builds wheel, sdist and Linux desktop tarball, verifies SHA-256
  checksums, clean-installs the wheel, exercises the desktop launcher installer,
  and uploads release-candidate artifacts.
