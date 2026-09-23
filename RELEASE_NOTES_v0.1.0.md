# ArmorX Toolkit v0.1.0

The first public release of **ArmorX Toolkit** — an open-source toolkit for the **BIGBIG WON ARMORX Pro** and Xbox controller configuration research.

## Highlights

- Unified `armorx` CLI
- Installable Python package under `src/armorx`
- 144-byte ARMORX Pro config decoder / validator / builder
- CRC16 validation and regeneration
- Named Xbox / ARMORX Pro key mapping
- Simple remapping syntax such as:
  ```bash
  armorx config map config.json M1=A M2=B -o mapped.json
  ```
- Macro builder with M1-M4 triggers, timed steps, chords, and cycle modes
- Read-oriented community/config exchange client
- Evidence-based documentation using **PROVEN / STRONG EVIDENCE / UNKNOWN**
- Pytest coverage and GitHub Actions CI
- Original standalone scripts preserved under `tools/`

## Install

```bash
python -m pip install git+https://github.com/feshinkof-boop/armorx-toolkit.git@v0.1.0
armorx --version
```

## Known limitations

- Share / Screenshot numeric key ID is still unresolved.
- Raw firmware-side macro frame encoding is not fully documented yet.
- Direct BLE/device write support is not included in v0.1.0.
- Community commands are intentionally narrow and do not enumerate identifiers or brute-force share codes.

## Project scope

This release is focused on interoperability, reproducible controller research, configuration tooling, and community collaboration around **BIGBIG WON**, **ARMORX Pro**, **Xbox controllers**, macros, key mapping, and controller configuration.

See the README and documentation for usage details.
