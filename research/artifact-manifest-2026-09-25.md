# Artifact manifest — 2026-09-25

Provenance and integrity record for analyzed artifacts. Private identifiers,
serials, MACs and raw proprietary binaries are NOT committed to this repository;
this manifest records their hashes and provenance only.

| Artifact | SHA256 | Size | Version | Source | Analysis status |
|---|---|---|---|---|---|
| base.apk | `7ed18b774bf8beab0ff2ff11bc0669f4cacb9baa5cc309bf277752592a2bc892` | 35958605 | 2.23.0609 | Google Drive share (user), 2026-09-25 | Blutter-dumped, fully indexed (2.23.0609) |
| com.moojiang.bigbigwon_2.24.0919_24.apk | `0bae884badc004991e638b0e62a0a6afc07256a5deabd8bb833f0bb36638f305` | 16087829 | 2.24.0919 | local APK collection (prior session) | Blutter-dumped, fully indexed (2.24.0919) |
| DevMgr.dll | `653cb3219abd09338c1590375a60162e6e4fd7b72c1856aaa7b796b7da7d709c` | 7299472 | BIGBIG WON Assistant DevMgr | Windows Assistant 1.0.6.1 install | Prior static analysis preserved (devmgr_static/) |
| BigBigWonAssistant.exe | `45cfd9562b73ece6d08b29e0f71c1568bea3d5a84b63e11dca8c8ed83289945b` | 583056 | - | Windows Assistant 1.0.6.1 | prior analysis (dongle_baseline_v13) |
| NetMgr.dll | `26ba759955bb7804ad3f3428b4908f4cd044ff45728a1cafda00c3ec1c5302c0` | 2234768 | - | Windows Assistant 1.0.6.1 | inventory only |
| WndMgr.dll | `998d1306bffec1b34dbbc96a50be3bca3a4e2e11e9131f3bc7a6f2e7389045a5` | 24313232 | - | Windows Assistant 1.0.6.1 | inventory only |
| armorx_ble_capture_run2.jsonl | `d74a4c8c90baf4532736a7341f1aa8978420ee8debe496ae982a6669fd804330` | 1693909 | - | Frida passive capture on test phone | primary live evidence (d6_d7_semantics, frame census) |
| armorx_ble_capture_run1.jsonl | `7f2a1fcec1c8acd6ccdd50a44bcc60ace4c9e36e222b35fdadb5afdd96860958` | 98205 | - | Frida passive capture | secondary live evidence |

## Toolchain used/provenance

- Blutter commit 4a60ac6 (worawit/blutter) with per-version Dart SDK builds (2.19.6 for 2.23 APK; 3.2.3 for 2.24 APK)
- Frida Gadget/client 17.18.0 (17.19.0 crashed on test device; preserved working env)
- python3 + pytest for scripts/tests
