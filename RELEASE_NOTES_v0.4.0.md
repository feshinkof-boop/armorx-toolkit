# ArmorX Toolkit v0.4.0 — Linux BLE configuration

v0.4.0 adds guarded live configuration from Linux while preserving the offline
protocol, capture, diagnostics and exchange tooling introduced in v0.3.0.

The Windows configurator remains a separate **v0.2.1** release.

## Highlights

- `armorx live scan`, `info`, `read-config`, `backup`, and `plan`.
- `armorx live apply TARGET --address ADDRESS` with:
  - two agreeing D6 reads before a write;
  - automatic pre-write `.json/.bin/.sha256` backup;
  - backup reopen + SHA-256 verification;
  - exact byte-level and decoded field diff;
  - default refusal when undecoded bytes would change;
  - KDE/terminal confirmation;
  - one ten-fragment D7 full-image write;
  - one `A5 05 0E 00 B8` persistence command;
  - two exact D6 read-backs.
- `armorx live rollback PREFIX --address ADDRESS` restores the exact saved
  `.bin` bytes and refuses unrelated live states by default.
- Bounded BLE connection retries are allowed only before the first mutating
  frame; the toolkit never blindly replays a partially started write.
- `armorx.diff` and `armorx.confirm` provide reusable diff/confirmation
  layers.
- Conservative scan classification records why a device is or is not considered
  an ARMOR-X candidate instead of guessing anonymous advertisements.

## Real-hardware validation

The public apply/rollback path was validated end-to-end on 2026-09-29:

- baseline: 144 bytes, valid CRC, stable across repeated D6 reads;
- target: M1 B→A, exactly three changed offsets (two CRC bytes + mapKeys[23]);
- public dry-run: backup/diff only, zero mutating frames;
- public apply: ten D7 fragments, acknowledgement observed, one persistence
  frame, two target-matching D6 verifications;
- physical check: pressing M1 produced the A bit on the controller's USB GIP
  report stream;
- target survived a power cycle;
- public rollback restored the exact saved baseline;
- final power cycle still matched the original baseline byte-for-byte;
- after fixing the apply session record, the corrected apply→rollback pair was
  revalidated on hardware without an override.

## Safety defaults

- Unknown/reserved changed bytes are refused unless
  `--allow-unknown-diff` is explicitly provided.
- Interactive confirmation is required by default.
- Non-interactive automation requires both `--yes` and
  `--acknowledge-backup`.
- No raw opcode, arbitrary payload, firmware, or OTA command is exposed.
- Public reports/backups omit BLE addresses, usernames, hostnames, home paths,
  serial numbers and tokens.
- Experimental `validate-write-gate` and `validate-reversible-m1` commands
  remain clearly labelled as validation tools.

## Installation

Python 3.10+ is required. The BLE backend is optional:

```bash
python -m pip install "armorx-toolkit[live] @ git+https://github.com/feshinkof-boop/armorx-toolkit.git@v0.4.0"
```

From a source checkout:

```bash
python -m pip install -e ".[live]"
```

## Validation

- **324 tests passed, 0 failed, 0 skipped** before release-prep-only version and
  documentation changes.
- GitHub Actions passes Python **3.10, 3.11, 3.12 and 3.13**.
- Release CI builds wheel/sdist, installs the wheel into a clean environment,
  checks `armorx --version`, and smoke-tests the live command surface.
