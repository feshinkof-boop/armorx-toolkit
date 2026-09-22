# Changelog

All notable project changes are documented here.

## 0.1.0 — Initial public research release

### Added

- installable `src/armorx` Python package
- unified `armorx` console command with `config`, `macro`, and `community` groups
- `armorx config map config.json M1=A` shorthand for named remapping
- unified CLI documentation and CLI regression tests

- 144-byte ARMORX Pro config decoder/builder
- CRC16 validation and regeneration
- named Xbox / ARMORX Pro key mapping
- M1-M4 remapping support
- macro builder and validator
- macro DSL example
- read-oriented community/config exchange client
- protocol documentation
- automated tests and GitHub Actions
- issue and pull-request templates

### Compatibility

The original standalone scripts under `tools/` are preserved and remain usable.

### Research status

The project intentionally leaves unresolved button IDs and unknown/reserved config bytes unassigned until they are independently verified.
