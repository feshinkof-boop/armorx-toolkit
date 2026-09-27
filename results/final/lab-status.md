# ARMOR-X lab status (generated 2026-09-27, autonomous pass)

Subsystem verdicts use exactly WORKING / PARTIALLY WORKING / BLOCKED / NOT ATTEMPTED.
Everything marked WORKING below was verified by an executed command whose output is quoted in the
referenced report; nothing is claimed from intent.

| Subsystem | Status | Evidence / where |
|---|---|---|
| Spare Bluetooth radio | **WORKING** | Realtek **RTL8723BU `0bda:b720`** at USB port path **1-8**, BT controller **hci1 `E8:4E:06:8A:F2:00`** (HCI 4.0, `RTK_BT_4.0`), `UP RUNNING` — verified live by `lsusb`, `hciconfig`, `/sys/class/bluetooth/hci1`. `baselines/radio/combo-adapter.json` |
| Spare Wi-Fi disabled | **WORKING** | combo Wi-Fi `wlxe84e068af1ff` (`e8:4e:06:8a:f1:ff`, `rtl8xxxu`, USB iface `1-8:1.2`) is NetworkManager-unmanaged and DOWN; round-trip (incl. per-interface unbind of **only** `1-8:1.2`) verified twice, idempotent. `automation/radio/{disable,restore}-combo-wifi.sh`, `results/final/radio-isolation-report.md` |
| wlp3s0 protected | **WORKING** | `automation/radio/check-primary-network.sh` → exit 0 (PASS) before and after every radio operation; `wlp3s0` still UP at 192.168.0.45/24 with the default route via 192.168.0.1; a tampered baseline correctly FAILs the `--compare-with` check |
| Bumble physical HCI | **WORKING** | both Bumble transports used live against hci1: `hci-socket:1` (btusb stays bound) and `usb:1-8` (port-path moniker, per-interface detach, auto re-bind) — `controller_info` read through each |
| Bumble virtual BLE | **WORKING** | `ble/virtual-armorx/selftest.py` re-run independently in this pass: **client 14/14, selftest 12/12, exit 0**, over a purely virtual TCP transport, no physical radio touched |
| Android reference AVD | **WORKING** | `armorx_ref_api33` created by `avd/reference/create-reference-avd.sh`; emulator 37.1.11.0, KVM usable, headless boot ≈36 s |
| Android research AVD | **WORKING** | `armorx_res_api30`, `armorx_res_api33` (x86_64 `google_apis` images) under `avd/research/avd-home` |
| MYGT 2.23 | **WORKING** (dynamic) | ships `x86_64` + `armeabi-v7a` + `arm64-v8a` → installs and runs natively on API 33; `.MainActivity` resumed, `flutter: REACTIVE_BLE …` in logcat |
| MYGT 2.24 | **BLOCKED** (dynamic) | arm64-only: `INSTALL_FAILED_NO_MATCHING_ABIS` on API 33; installs on API 30 then **SIGILL** in `libndk_translation` |
| MYGT 4.0.8 | **BLOCKED** (dynamic) | `DYNAMIC_AVD_4.0.8_BLOCKED_BY_ABI` — arm64-only APKM, same SIGILL; APKs deliberately not re-signed/modified |
| Frida | **WORKING** | frida-tools **16.7.19** (Frida 17 removed the bundled Java bridge and cannot run these hooks); platform BLE + network hooks fired live (`47.116.43.253:8080` captured) |
| btsnoop | **PARTIALLY WORKING** | capture plan, extraction tooling and correlation guide written; no on-device btsnoop file yet because only 2.23 is runnable and it was not driven through a full workflow |
| Virtual ARMOR-X | **WORKING** | 5 evidence-backed handlers (`0x0B`, `0xEF`, `0xD6`, `0xD7`, `0x0E`), 28 opcodes logged UNKNOWN-by-design with `reply_bytes_sent: 0`; GATT `00000000-…`/FFE1/FFE2 + 2A19/2A24/2A26; advertises `ARMOR-X Pro_<suffix>` |
| Real-device harness | **PARTIALLY WORKING** | harness, state machine, JSONL logging, watchdog and baseline capture verified by `harness_selftest.py` (**21/21 PASS**); no ARMOR-X has been attached, so no real session yet |
| Emergency restore | **PARTIALLY WORKING** | script + hard validation gate WORKING (`--dry-run` prints the exact frames; refuses without `restore_verified: true`); round-trip validation **NOT ATTEMPTED** — therefore **not usable in an emergency yet** |
| Version-comparison automation | **PARTIALLY WORKING** | static cross-version matrix built and verified for all three builds; dynamic comparison **NOT ATTEMPTED** (2 of 3 builds cannot run on this host) |

## Blockers (exact)

1. `DYNAMIC_AVD_4.0.8_BLOCKED_BY_ABI` — 2.24 and 4.0.8 are arm64-only. An arm64 AVD is impossible on
   this x86_64 host (`Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator`); API 30
   translation can install but not execute them. Needs a physical arm64 device (or an arm64 host).
2. No ARMOR-X Pro has been attached to this host, so every hardware-dependent item
   (real-device harness session, baseline, restore validation, live tests L01–L08, btsnoop
   correlation) is NOT ATTEMPTED rather than failed.
3. Frida ≥17 cannot be used for the Java-layer hooks; the lab pins 16.7.19.

## Safety audit (this pass)

* `wlp3s0`: unchanged — UP, 192.168.0.45/24, default route via 192.168.0.1 (checked before and after;
  `check-primary-network.sh` exit 0).
* No `rfkill block wifi` / `rfkill block all` anywhere in the lab (grepped), no driver blacklist,
  no whole-device unbind — only the single Wi-Fi USB interface `1-8:1.2` was ever unbound, and the
  BT interface `1-8:1.0` was only detached for the explicit `usb:1-8` Bumble transport test and
  re-bound automatically.
* The toolkit repo `~/armorx-re/repo` was left untouched on branch `research/mygt-4.0.8` at `dbe2ce7`.
* APK originals re-hashed after the pass: 2.23 `7ed18b77…c892`, 2.24 `0bae884b…f305`,
  4.0.8 `474f6609…3abf` — unchanged.

## Git / artifact state

* Lab repo: `/home/salamanka/armorx-lab` (own repo), branch `master`, HEAD **a7e08c6**, 94 tracked
  files; `.git` is 1.1 MB (emulator disks and downloaded binaries are ignored, not committed).
* Lab bundle: `/home/salamanka/armorx-lab/armorx-lab.bundle` (957 KB, `git bundle verify` → complete history).
* Toolkit repo `/home/salamanka/armorx-re/repo`: `research/mygt-4.0.8` untouched at **dbe2ce7**;
  new branch **`research/ble-lab-multiversion`** = `6f0acd5` adds `docs/lab/README.md` +
  `tools/lab/**` (harness, experiment matrix, radio isolation, emergency restore) — 20 files,
  +3,041 lines, no release code touched.
* Push artifacts (GitHub auth still unavailable → **AUTH_BLOCKED**):
  `/home/salamanka/armorx-lab/ble-lab-multiversion.patch` (140 KB) and
  `ble-lab-multiversion.bundle` (298 KB, verified). Exact command once credentials exist:
  `git -C /home/salamanka/armorx-re/repo push -u origin research/ble-lab-multiversion`.
