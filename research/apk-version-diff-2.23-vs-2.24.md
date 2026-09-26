# APK semantic differential: 2.23.0609 vs 2.24.0919 — 2026-09-25

Basis: full Blutter dumps of both APKs (arm64-v8a; 2.23 Dart 2.19.6/Flutter 3.7,
2.24 Dart 3.2.3/Flutter 3.16), plus the frame-builder/dispatcher/template scans in this
directory. Logical functions matched by name and opcode behavior, not by string diff.

## Unchanged (protocol-critical)

- BLE service/characteristics: 00000000-0000-1000-8000-00805f9b34fb, FFE1
  write-without-response, FFE2 read+notify (2.24 static offsets differ: 0xfb4/0xfb8;
  same UUID strings). No AE00/AE01/AE02 reference in either build.
- A5 short-frame family: [A5, len=total frame bytes, opcode, data..., sum-mod-256].
- A4 fragmentation: 15-byte chunks, 1-based index, len byte = chunk+5, per-frame checksum.
- 0B/EF/D6/D7/0E/D2 request bytes identical (verified per-builder in
  android-frame-builders-*.json).
- Config CRC-16/MODBUS (init 0xFFFF, poly 0xA001, over bytes 2..end, big-endian at 0..1):
  self-validating templates exist in both pools (2.23: 240B/0x1605; 2.24: 240B/0x198B,
  484B/0xD0A4).
- checkConfigLength logic (-2 padding terminator, <240 short-circuit) identical;
  static field offset moved 0xfd8 → 0x1030.
- 88/144/144 factory templates byte-identical across versions (same SHA256).
- E2: absent from both builds (no reachable builder or parser; only intl-table
  offset arithmetic uses Smi 452).
- ARMOR-X Pro config size: 144 bytes in both (armor-x_pro pages + GamepadSet30 path
  persist; 280/484 pages belong to other devices).

## Renamed / renumbered

- Device enum: ARMOR-X Pro 6 → 8 (2.24 adds Rainbow2 Lite=4, Blitz2=5, CHOCO=7;
  BLITZ LITE removed).
- zkm static field: 0xfd4 → 0x102c (armorx-pro root page).

## Refactored

- Config logic pulled out of widgets into `base_gamepadset.dart` and
  `ble_gamepad_set_provider.dart` (provider architecture) in 2.24.
- A4 reassembly centralized: 2.24 dispatchers in configs_mian (V280/V484),
  configs_config, configs_config_only_c1, rainbow_tab_config_1s.

## New in 2.24 (protocol-affecting)

- gamepadset280.dart / gamepadset484.dart + configV280/configV484 widget trees:
  280- and 484-byte config formats for C1 Pro-class devices (router by derived config
  length 0x118/else in rainbow_tab_config_1s.dart @0x8aa014).
- transcribe_frame.dart + frame_config_macros.dart: frame recording/replay
  ("transcribe") — startTranscribe/stopTranscribe send 0B and FC (getZkmVer + getDpi);
  getMaxSize sends D3 (GetProfileSize in Windows terms).
- calibration/ (stick_calibration, motion_calibration): response parsers keyed on 0E.
- share_code_import.dart; new server endpoint /dev/queryGameList.
- getConnectModel / getMTU / getOnBoardConfig builders (0E/FC/D4-family requests
  in rainbow_more/rainbow_tab_config_1s).
- 5 additional default templates (see default-config-templates.json).

## Removed

- BLITZ LITE device entry (2.23 type 5) — replaced by Blitz2.

## 2.23 → 2.24 builder census

13 frame-builder functions → 21 (new: writeConnectModeConfig, getConnectModel,
getMTU, getOnBoardConfig, stopTranscribe, startTranscribe, getMaxSize,
configV484/config_stick_view testModeSwitch, rainbow_tab_config_1s writeDevice,
configs_config_only_c1 getDeviceConfig). 5 → 10 response dispatchers (new: V280/V484
configs_mian, configs_config_only_c1, stick/motion calibration).

## Uncertain / other-device-only

- Exact device models behind 280/484 (C1 Pro-class inferred from widget names
  c1pro_stick_curve_grid / c1pro_stick_dead_zone_widget sharing the configV280/484
  trees — STRONG EVIDENCE, not PROVEN).
- AB long-packet family: no Android trace in either build (UNKNOWN_ANDROID);
  Windows-side only.
