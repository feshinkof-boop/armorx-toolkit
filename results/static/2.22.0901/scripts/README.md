# Reproducible scripts — 2.22.0901 identity / inventory pass

Run from anywhere; all paths inside are absolute and read-only over the frozen APK.

| script | produces |
|---|---|
| `scan_certs.py` | signing-block v2/v3 cert extraction + openssl fingerprints (identity) |
| `strings_inventory.py` | per-artifact string dumps + classified subsets (`class-*.txt`) in `../` |
| `config_arch.py` | default-config image extraction + CRC-16/MODBUS (`configs.json`) |
| `removed_useful.py` | Dart-pool diff 2.22 \ (2.23 ∪ 2.24 ∪ 4.0.8) |
| `mark_search.sh` | per-artifact hit counts for ZJ-XT / device marks |

Key one-off commands (exact) are quoted inside the matching `../*.md` deliverable.
