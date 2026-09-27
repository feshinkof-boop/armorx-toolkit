# armorx-lab

Research laboratory for the BIGBIG WON / ARMOR-X Pro BLE protocol work. Everything in here is
RESEARCH ONLY: nothing in this lab is meant to be wired into the public Windows application.

## Layout

| Path | Contents |
|---|---|
| `apk/original/{2.23,2.24,4.0.8}/` | untouched APK/APKM originals (hashes in `apk/manifests/`) |
| `apk/extracted/` | extracted copies for analysis (never the originals) |
| `apk/manifests/` | per-version identity manifests + `version-matrix.json` |
| `static/{jadx,blutter,ghidra}/` | decompiler output per version (Blutter trees are referenced from the existing research dirs rather than duplicated) |
| `ble/virtual-armorx/` | Bumble-based virtual ARMOR-X peripheral + session logs |
| `ble/bumble/venv` | Bumble install used by the lab |
| `automation/radio/` | combo-adapter identification, Wi-Fi isolation, BlueZ/Bumble mode switching |
| `automation/scripts/` | protocol helpers (`armorx_lab/`), real-device harness, selftest, emergency restore |
| `automation/experiment-matrix/` | machine-readable one-variable experiment plan |
| `baselines/{host,radio,device,imported-research}/` | frozen baselines and imported research |
| `results/{static,dynamic,version-diff,experiments,final}/` | findings, diffs and final reports |
| `logs/` | install logs, device sessions, harness state logs |

## Safety invariants (never violate)

* Primary Wi-Fi `wlp3s0` must keep its IP and the default route through `192.168.0.1`.
* Never run `rfkill block wifi` / `rfkill block all`.
* Never blacklist a Wi-Fi driver; never unbind a whole USB device (only a single USB interface).
* No experimental device write without a saved, CRC-verified, hashed baseline.
* Unknown protocol semantics stay UNKNOWN; they are never guessed into a reply.

## Quick start

```bash
/usr/bin/python3 automation/scripts/real_device_harness.py status
/usr/bin/python3 automation/scripts/harness_selftest.py          # logic self-test, no hardware
automation/radio/check-primary-network.sh                        # must PASS at all times
```

See `results/final/lab-status.md` for the current state of every subsystem.
