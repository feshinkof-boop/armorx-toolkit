# Static APK version matrix - BIGBIG WON 2.23.0609 / 2.24.0919 / 4.0.8

Built from the three **local originals** only (no download). Every row carries evidence
(binary / AOT-asm location) and one label: PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN.

Extracted trees: `/home/salamanka/armorx-lab/apk/extracted/{2.23,2.24,4.0.8}/`.
Per-build manifests: `/home/salamanka/armorx-lab/apk/manifests/{2.23,2.24,4.0.8}.json`.

## A. Identity, packaging, signing

| field | 2.23.0609 | 2.24.0919 | 4.0.8 | class | evidence | label |
|---|---|---|---|---|---|---|
| original filename | base.apk | BIGBIGWON-2.24.0919.apk | BIGBIGWON-4.0.8.apkm (+ base.apk) | behaviour changed | file listing | PROVEN STATIC |
| sha256 | 7ed18b77…c892 | 0bae884b…f305 | 474f6609…3abf | unchanged | sha256sum of the untouched originals | PROVEN STATIC |
| package name | com.moojiang.bigbigwon | com.moojiang.bigbigwon | com.moojiang.bigbigwon.mygt | renamed-restructured | AndroidManifest.xml package= (2.23 base.apk offset 0xb54 chunk; 4.0.8 base split) | PROVEN STATIC |
| versionName / versionCode | 2.23.0609 / 12 | 2.24.0919 / 24 | 4.0.8 / 409 | expanded | manifest attrs | PROVEN STATIC |
| signing certificate | CN=moojiang (release key) 5472…78C | CN=Android Debug 44C3…541 | Google App Signing F745…B62 | behaviour changed | v1 CERT.RSA (2.23/2.24) and v2/v3 signing block (4.0.8) | PROVEN STATIC |
| minSdk | 21 | 21 | 24 | behaviour changed | uses-sdk minSdkVersion | PROVEN STATIC |
| targetSdk | 32 | 34 | 36 | expanded | uses-sdk targetSdkVersion | PROVEN STATIC |
| ABI set | arm64-v8a, armeabi-v7a, x86_64 | arm64-v8a | arm64-v8a (ABI split) | removed | lib/ entries per APK | PROVEN STATIC |
| split-APK structure | none (fat APK) | none | APKM: base + config.arm64_v8a + config.en + config.ar + config.xxhdpi | expanded | APKM listing + each split's AndroidManifest split=/splitTypes= attrs | PROVEN STATIC |

## B. Runtime, transport, protocol and config

| field | 2.23.0609 | 2.24.0919 | 4.0.8 | class | evidence | label |
|---|---|---|---|---|---|---|
| Dart runtime | 2.19.6 | 3.2.3 | 3.12.2 | expanded | libflutter.so version banner string | PROVEN STATIC |
| Flutter framework | 3.7.x | 3.16.x | UNKNOWN | unknown | not stored in the bundle; 4.0.8 in particular has no version string | INFERRED |
| BLE library | flutter_reactive_ble | flutter_reactive_ble | flutter_blue_plus | behaviour changed | libapp.so string pool package paths | PROVEN STATIC |
| server host | m.bigbigwon.com:8080 | m.bigbigwon.com:8080 | m.bigbigwon.com:8080 | unchanged | libapp.so string pool | PROVEN STATIC |
| server endpoints | 15 (…queryDefaultConfig, setConfig) | 16 (+queryGameList) | 14 (-queryDefaultConfig, -queryGameList) | removed | string pool /dev/* literals | PROVEN STATIC |
| ARMOR-X Pro device enum | 6 | 8 | 10 | renamed-restructured | objs.txt Obj!Device@90e4a1 / @9ef961 / @b2eec1 off_8 | PROVEN STATIC |
| device enum size | 7 | 9 | 13 | expanded | objs.txt enum object count | PROVEN STATIC |
| vendor service / FFE1 / FFE2 | 00000000-… / FFE1 write / FFE2 notify | same | same (+180A,180F,2A24,2A26,2A19,2902,F530-F532) | expanded | libapp.so UUID literals | PROVEN STATIC |
| config families (bytes) | 88/144/240 (4 templates) | 88/144/240/280/484 (8 templates) | 88/144/240/280/335/456/484/508 (12 templates) | expanded | pp.txt default-config string literals, declared length == total length | PROVEN STATIC |
| ARMOR-X Pro config length | 144 | 144 | 144 (or 240 - negotiated via defaultConfig) | behaviour changed | bc536085 template present in all three; 4.0.8 defaultConfig branches 0x90->144, 0xF0->240 | PROVEN STATIC |
| config CRC rule | CRC-16/MODBUS over 2..end | same (3 images self-validate) | same (6 images self-validate) | expanded | recomputed CRC == stored CRC on the embedded images | PROVEN STATIC |
| config length static field | 0xfd4 | 0x102c | 0xb6c | renamed-restructured | StoreStaticField in the 0B reply handler | PROVEN STATIC |
| opcode inventory (proven builders) | 0B,0E,EF,D2,D4,D6,D7,D8,FC,FF (+A4/A5) | +D3,E1,E4,F6,F7,F8,F5,0D | +E2,DD,70,73,04,AB(05/25,05/26),1A,1B | expanded | frame-builder census + byte-exact reconstruction over each asm tree | PROVEN STATIC |
| E2 readFirmware | absent | absent | A5 04 E2 8B (@0x8b6860) | expanded | no builder/parser constructs 0xE2 in 2.23/2.24; 4.0.8 readFirmware builds it | PROVEN STATIC |
| D6 read / D7 write | A5 04 D6 7F / A4 fragments, hard-coded 15-byte chunk | same / chunk = subpackageLength()-5 (=15 for ARMOR-X Pro) | same / chunk = subpackageLength()-5 (=15) | behaviour changed | writeDeviceConfig bodies; subpackageLength switch in define.dart | PROVEN STATIC |
| D8 macro | present: A4/D8 fragmentation (writeMacroConfig @0x797fa0); no transcribe_frame.dart | present + frame recording (transcribe_frame.dart, frame_config_macros.dart new) | present, payload reconstructed byte-exact (10+10N, CRC-16, 8 ms granularity) | expanded | writeMacroConfig bodies / d8-macro reconstruction | PROVEN STATIC (2.24/4.0.8); payload layout UNKNOWN for 2.23 |
| FC/F6 DPI | A5 05 FC <sel&0x0F>, no F6 branch, no device gate | FC default; F6 for {devRainbow2Pro, devC2SL} when static 0x102c >= 0x35 | FC default; F6 for {devRainbow2Pro, devRainbow3, devGale2, devC2SL} when static 0xb6c >= 0x35; motion DPI = AB 07 05 25 <u16 LE> | expanded | writeDpiConfig bodies; `cmp x1,#0x35; b.lt <skip F6 store>` | PROVEN STATIC |
| lighting | writeLightConfig -> A5 + A4/FF | same (+0D writeLogoColorConfig) | A5 04 70 / A5 10 70 R3, main writeLightConfig FF+05+3F, additional DD/F8/73/F5 | expanded | light config builder census | PROVEN STATIC |
| turbo | config-resident (GamepadParam30.turboKey @0x54) | config-resident (@0x5c) | config-resident, byte 80 = speed idx, bytes 81..84 = turboKey u32 BE | unchanged | turboKey field + hex-parse serialisation; 4.0.8 offsets proven byte-exact | PROVEN STATIC (4.0.8); byte offsets UNKNOWN for 2.23/2.24 |
| key-ID table | labels up to M4; no Capture/Menu/M5-M7 | +Capture, keyboard labels | +Menu, M5/M6/M7; full 0..49 id table (re-verified) | expanded | key_remap_t.dart::gamePadKeyName + string pool | PROVEN STATIC (4.0.8); label sets only (numeric binding UNKNOWN) for 2.23/2.24 |
| device enum id 5 label (2.24) | devBLITZ_LITE | devC2SL (NOT 'Blitz2') | devMSY (different namespace position) | behaviour changed | objs.txt @9ef981 | PROVEN STATIC |
| queryDefaultConfig / queryGameList endpoints | both present | both present | both removed | removed | string pool /dev/* literals | PROVEN STATIC |
| transcribe / frame_config_macros modules | absent | present | present | expanded | asm/moojiang/units/transcribe_frame.dart, widgets/general/frame_config_macros.dart | PROVEN STATIC |
| 280/484 serializer modules | absent | present (gamepadset280/484, base_gamepadset) | present | expanded | asm/moojiang/units listing | PROVEN STATIC |

## C. Evidence anchors used in this pass

| anchor | what it proves |
|---|---|
| `unzip -l` on the originals | split layout, member hashes |
| pyaxmlparser + androguard on each AndroidManifest | package / versionName / versionCode / minSdk / targetSdk / split attrs / signer |
| `strings` on `lib/<abi>/libapp.so` | BLE library, UUIDs, hosts, endpoints, device labels |
| libflutter.so version banner | Dart runtime version |
| libapp.so snapshot header (`f5 f5 dc dc` + engine hash) | Flutter engine hash |
| `objs.txt` (`Obj!Device@<addr>` `off_8`/`off_10`) | device enum ids and names |
| `pp.txt` config string literals | config families, template hashes, stored vs recomputed CRC |
| frame-builder census over `asm/moojiang` | which opcodes are constructed, and which are absent |
| `reconstruct_frames.py` register-map extraction | byte-exact frames (checksums match the live-proven ones) |
