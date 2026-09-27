# Full string / asset inventory — BIGBIG WON 2.22.0901

Frozen APK: `/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk`
(sha256 `785684ec…c0361c`). All extraction is **read-only** over the untouched APK and the
already-extracted tree `apk/extracted/2.22.0901/`, plus the existing Blutter tree
`static/blutter/2.22.0901/blutter_out/`.

Producer: `strings_inventory.py` (this pass). The full per-artifact dumps live next to this file:

| dump file | source | `strings -n` |
|---|---|---|
| `strings-classes.dex.txt` | `classes.dex` | 4 |
| `strings-lib_arm64_libapp.so.txt` | `lib/arm64-v8a/libapp.so` | 4 |
| `strings-lib_armeabi_libapp.so.txt` | `lib/armeabi-v7a/libapp.so` | 4 |
| `strings-lib_x86_64_libapp.so.txt` | `lib/x86_64/libapp.so` | 4 |
| `strings-lib_arm64_libflutter.so.txt` / `…armeabi…` / `…x86_64…` | `lib/*/libflutter.so` | 4 |
| `strings-resources.arsc.txt` | `resources.arsc` | 4 |
| `strings-bledata.proto.txt` | `bledata.proto` | 4 |
| `strings-*asset*.txt`, `strings-google_*.proto.txt` | `assets/**` text, `google/protobuf/*.proto` | 4 |
| `strings-dart-pool-pp.txt` | **Dart AOT string pool** (`pp.txt` `String:` literals) | — |
| `class-*.txt` | classified, deduplicated subsets | — |
| `strings-AndroidManifest.xml.txt` | (empty — binary AXML has no usable ASCII) | 4 |

Exact extraction command: `strings -a -n 4 <decompressed-member>`; the Dart pool was read as
`grep -o 'String: ".*"' static/blutter/2.22.0901/blutter_out/pp.txt`.

> **Note on methodology.** Grepping the APK *container* is meaningless for string work: 89/123
> entries are DEFLATE-compressed, so ASCII literals do not appear literally. Every count below is
> over *decompressed* members (extracted tree) or over the Blutter pool text.

## Per-artifact unique-string counts (`strings -n 4`)

| artifact | lines |
|---|---|
| classes.dex | 17,779 |
| lib/arm64-v8a/libapp.so | 53,934 |
| lib/armeabi-v7a/libapp.so | 36,964 |
| lib/x86_64/libapp.so | 127,713 |
| lib/arm64-v8a/libflutter.so | 49,443 |
| lib/armeabi-v7a/libflutter.so | 90,090 |
| lib/x86_64/libflutter.so | 112,141 |
| resources.arsc | 228 |
| bledata.proto | 95 |
| DebugProbesKt.bin | 33 |
| Dart pool (`pp.txt` `String:`) | 15,023 (unique) — 20,279 literals total |
| **grand-total unique across all artifacts** | **171,840** |

(`x86_64` libs simply expose more symbol strings; they are the same build.)

---

## A. BLE / protocol strings

The build uses **flutter_reactive_ble** over a protobuf transport. Confirmed plugin/transport
markers (PROVEN STATIC, all in `pp.txt` and `libapp.so`):

```
package:flutter_reactive_ble/src/device_scanner
package:flutter_reactive_ble/src/device_connector
package:flutter_reactive_ble/src/device_interactor
package:flutter_reactive_ble/src/connected_device_operation
package:flutter_reactive_ble/src/discovered_devices_registry
package:flutter_reactive_ble/src/reactive_ble
package:reactive_ble_mobile/src/converter/protobuf_converter
package:reactive_ble_mobile/src/reactive_ble_mobile_platform
package:reactive_ble_platform_interface/src/model/uuid
```

GATT identifiers (PROVEN STATIC, `pp.txt`):

```
00000000-0000-1000-8000-00805F9B34FB   vendor service (all-zero service UUID)
0000FFE1-0000-1000-8000-00805F9B34FB   command write characteristic
0000FFE2-0000-1000-8000-00805F9B34FB   notify/read characteristic
```

Named UUID symbols in the app code: `uuidRainbowService`, `uuidRainbowRead`, `uuidRainbowWrite`
(`init:uuidRainbowService`, `init:uuidRainbowRead`, `init:uuidRainbowWrite`).

App-level BLE/command vocabulary found in the Dart pool (PROVEN STATIC):

```
scanForDevices, connectToDevice, disconnectFromDevice
controlLight, controlLightLight, defalutLight        (sic: "defalut")
firmwareVersion, devModel, configList, macroList, mapList
keyNameList, leftList, rightList, enableDeltaModel, forceReport
```

Frame byte constants: **no literal `A5 `/`A4 `/`A8 ` frame strings exist in the Dart pool** of
2.22 — the A5/A4/A8 frame headers that later builds expose as pool literals are assembled from
integers here, so the 2.22 pool carries no readable hex-frame constant (this is a real difference
from 2.23+, not a tooling gap: `grep -E '"A5 [0-9A-F]{2}"' pp.txt` → 0 hits).

## B. Device model names

Device `enum` (PROVEN STATIC, `objs.txt`): only **four** members —

| idx | name |
|---|---|
| 0 | `devNone` |
| 1 | `devRainbow` |
| 2 | `devRainbowS` |
| 3 | `devArmorX` |

Human labels present in the pool: `"Rainbow"`, `"RAINBOW"`, `"ArmorX Pro"`, `"ARMOR-X Pro"`.
Library/marketing URL segments: `product-pic/AEMOR-X/` (misspelt ARMOR-X) and `product-pic/C1/`
(C1 = RAINBOW C1, a device *not* present in the `Device` enum).
Widget/package names: `package:moojiang/widgets/armor-x_pro/armorx_pro_root.dart`,
`…armorx_pro_config_config.dart`, `…armorx_pro_config_macro.dart`, `…armorx_pro_more.dart`;
`ArmorXProScreen/Widget/Config/Macro/MoreWidget`, `Rainbow*` widget family
(`RainbowScreen`, `RainbowDeviceConfig`, `RainbowLightConfig`, `RainbowMacroConfig`, `RainbowTest`).

    grep -a -oE 'dev[A-Za-z]+|ARMOR-X|ArmorX|Rainbow|RainbowS' pp.txt | sort -u

No `devRainbow2Pro`, `devBLITZ_ULT/_LITE`, `devCHOCO`, `devC2SL`, `devMSY`, `devRainbow3`,
`devGale2`, `devKeyboardDouJiangV1` in 2.22 (those are 2.23/2.24/4.0.8 additions).

## C. Server URLs / hosts

    grep -a -oE 'https?://[A-Za-z0-9.:/_-]+' pp.txt | sort -u

* API host: `http://m.bigbigwon.com:8080` (plaintext; manifest sets `usesCleartextTraffic=true`)
* OSS buckets:
  * `https://bigbig-won-cn.oss-cn-shanghai.aliyuncs.com`
  * `https://bigbigwon-jp.oss-ap-northeast-1.aliyuncs.com`
  * `https://bigwon-us.oss-us-west-1.aliyuncs.com`
  * (**no `bigwon-germany.oss-eu-central-1`** — that host appears from 2.23)
* Support/legal: `https://www.bigbigwon.com`, `https://www.bigbigwon.cn`,
  `https://jp.bigbigwon.com`, `https://kr.bigbigwon.com`
  (`/support/`, `/usercenter/privacy/`, `/usercenter/user-agreement/`)
* Manual PDFs: `oss…/product-pic/AEMOR-X/<urlencoded>/armorx Pro user manual-{EN,JP}.pdf`,
  `oss…/product-pic/C1/…/RAINBOW-user manual-{EN,JP,KR}.pdf`
* Framework noise (not app hosts): `ns.adobe.com`, `purl.org`, `w3.org`, `flutter.dev`,
  `api.flutter.dev`, `stackoverflow.com`, `developer.android.com`, `github.com/dart-lang`.

Endpoint paths — see `server-api.md` (13 `/dev/*` endpoints). No `/dev/queryGameList`.

## D. Error / debug strings

Classified subset (`class-error_debug.txt`, 2,039 lines) is dominated by **Flutter/Dart framework**
assertions, not app logic. App-relevant entries:

```
"defalutLight"            (typo carried into a default-name)
device_permission_error
device_disconnect
"Connection was upgraded"
"Unable to load asset: "
No channel registered with name
"`shared_preferences_android` threw an error: "
```

The `/Volumes/Project/Projects/moojiang/.dart_tool/…/dart_plugin_registrant.dart` path leaks the
build machine directory (`/Volumes/Project/Projects/moojiang`) — PROVEN STATIC, `pp.txt`.

## E. Flutter plugin package names

From `package:**` literals (PROVEN STATIC, `pp.txt`; app code emits 33 `package:moojiang/**` units):

```
flutter_reactive_ble, reactive_ble_mobile, reactive_ble_platform_interface
app_settings, device_info_plus(_platform_interface), package_info_plus(_platform_interface)
permission_handler(_platform_interface), shared_preferences(_android/_ios/_linux/_macos/_windows)
path_provider(_linux/_windows), url_launcher, webview_flutter_android
fluttertoast, dio, http, http_parser, intl, provider, crypto, protobuf, petitparser,
nested, collection, characters, source_span, path, file, async
```

`META-INF/*.kotlin_module` (15) corroborate the plugin set on the Java/Kotlin side:
`reactive_ble_mobile_release`, `app_settings_release`, `package_info_plus_release`,
`fluttertoast_release`, `window_release`, `window-java_release`, `app_release`,
`kotlin-stdlib(-common/-jdk7/-jdk8)`, `kotlinx-coroutines-(core/-android)`, `rxkotlin`,
`annotation-experimental_release`.

## F. Binary blobs

* `bledata.proto` (3,144 B) — the flutter_reactive_ble protobuf schema; 28 message types
  (`java_package com.signify.hue.flutterreactiveble`). Full analysis in `server-api.md`.
* `assets/flutter_assets/…` — only PNG/GIF/TTF/OTF/JSON (`AssetManifest.json`, `FontManifest.json`,
  `NOTICES.Z`, `toastify.{css,js}`). **No default-config or protocol blob under assets/.**
* `google/protobuf/*.proto` (10 files) — standard well-known protos (`any/type/duration/api/…`),
  library artifact, no app meaning.
* `DebugProbesKt.bin` (1,714 B) — kotlinx-coroutines debug-probes artifact.