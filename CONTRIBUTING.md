# Contributing

Thanks for helping improve ArmorX Toolkit.

This project is focused on **BIGBIG WON ARMORX Pro**, **Xbox controller** interoperability, configuration tooling, key mapping, macros, and reproducible protocol research.

## What makes a good contribution?

Useful contributions include:

- controlled before/after config comparisons;
- verification of unknown key IDs;
- new firmware observations;
- fixes to the Python tools;
- tests;
- documentation;
- anonymized examples;
- UI/UX improvements;
- reproducible controller behavior notes.

## Evidence levels

When documenting a protocol claim, use one of these labels:

- **PROVEN** — directly reproduced or independently confirmed.
- **STRONG EVIDENCE** — multiple signals agree, but one final confirmation is missing.
- **UNKNOWN** — unresolved; do not guess.

Please include enough detail for another person to reproduce your result.

## Pull requests

1. Keep changes focused.
2. Add or update tests when changing code.
3. Update documentation when behavior changes.
4. Do not include personal device identifiers, account identifiers, access tokens, or private configuration data.
5. Do not include proprietary application binaries or copied proprietary source code.
6. Preserve unknown/reserved config bytes unless your change specifically proves their meaning.

## Reporting a newly decoded byte or key

Please include:

- firmware version;
- exact setting changed;
- old value;
- new value;
- byte offset or key ID;
- whether other bytes changed;
- how many times you reproduced the result.

A minimal controlled-diff report is much more useful than a guess.

## Development

```bash
python -m pip install pytest
python -m pytest
```

The current tools are directly runnable from `tools/`.
