# Static version diff (summary)

Full tables: `results/version-diff/static-version-matrix.md` (human) and `.json` (machine).

Headline rows across 2.23.0609 → 2.24.0919 → 4.0.8:

| Field | 2.23 | 2.24 | 4.0.8 | Class |
|---|---|---|---|---|
| Package | com.moojiang.bigbigwon | com.moojiang.bigbigwon | com.moojiang.bigbigwon.mygt | renamed |
| Signer | release (CN=moojiang) | **debug** | Google App Signing | behaviour changed |
| ABI | arm64 + armeabi-v7a + **x86_64** | arm64-v8a | arm64-v8a (split) | removed |
| Dart | 2.19.6 | 3.2.3 | 3.12.2 | expanded |
| BLE library | flutter_reactive_ble | flutter_reactive_ble | **flutter_blue_plus** | behaviour changed |
| BLE service/chars | 00000000-…/FFE1/FFE2 | same | same | unchanged |
| **ARMOR-X enum value** | 6 | 8 | **10 (0x0A)** | behaviour changed |
| Device enum size | 7 | 9 | 13 | expanded |
| Config families | 88/144/240 | + 280/484 | + **335/456/508** | expanded |
| Config CRC | CRC-16/MODBUS 2..end | same | same (6 images self-validate) | unchanged |
| E2 readFirmware | absent | absent | **`A5 04 E2 8B`** | expanded |
| DPI | `A5 05 FC <sel&0x0F>` only, no F6 branch | FC, F6 when version ≥ 0x35, 2 devices | FC, F6 when version ≥ 0x35, 4 devices; motion `AB 07 05 25 <u16 LE>` | expanded |
| Turbo | (see manifests) | (see manifests) | config-resident: byte 80 + u32 BE 81..84 | expanded |
| Host / API | m.bigbigwon.com:8080 | same | same | unchanged |

Two prior claims were **disproven** by this pass and are recorded here rather than deleted:

1. 2.24's enum id 5 is `devC2SL`, not "Blitz2".
2. The DPI gate is **F6 when version ≥ 0x35** (`cmp x1,#0x35; b.lt <skip>`), i.e. the opposite of the
   earlier "fw < 0x35" wording; and 2.23 has no F6 branch at all.
3. 4.0.8 *does* contain `sendAllTurboKeySpeed`/`writeTurboClick` — but only in the keyboard
   (`kb_doujiang`) subsystem; the gamepad turbo path is config-resident. The earlier "does not exist"
   statement was scoped to the gamepad path and is now stated precisely.
