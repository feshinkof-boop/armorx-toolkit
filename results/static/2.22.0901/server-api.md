# Server / API surface — BIGBIG WON 2.22.0901

Frozen APK: sha256 `785684ec…c0361c`. Read-only. All coordinates are offsets into the Dart AOT
string pool `static/blutter/2.22.0901/blutter_out/pp.txt` (line numbers given where useful); the same
literals are present byte-for-byte in each `lib/{arm64-v8a,armeabi-v7a,x86_64}/libapp.so`.

Extraction commands:

```bash
grep -a -oE '\[pp\+0x[0-9a-f]+\] String: "https?://[^"]+"' pp.txt      # hosts/URLs + offsets
grep -a -oE '\[pp\+0x[0-9a-f]+\] String: "/dev/[a-zA-Z]+"' pp.txt       # endpoints + offsets
grep -a -oE '"[0-9]{1,3}(\.[0-9]{1,3}){3}(:[0-9]+)?"' pp.txt            # IPv4 literals
```

## 1. Hosts / IPs / ports

| kind | value | artifact + offset | evidence |
|---|---|---|---|
| API base | `http://m.bigbigwon.com:8080` | `pp.txt:39890 [pp+0x39d58]` | PROVEN STATIC |
| OSS | `https://bigbig-won-cn.oss-cn-shanghai.aliyuncs.com` | `pp.txt [pp+0xc798…0xc7a0]` | PROVEN STATIC |
| OSS | `https://bigbigwon-jp.oss-ap-northeast-1.aliyuncs.com` | `pp.txt [pp+0xc778, 0xc7a8, 0xc7b0]` | PROVEN STATIC |
| OSS | `https://bigwon-us.oss-us-west-1.aliyuncs.com` | `pp.txt [pp+0xc788, 0xc790]` | PROVEN STATIC |
| legal/privacy | `https://www.bigbigwon.com/usercenter/{user-agreement,privacy}/` | `pp.txt [pp+0x40598,0x405a8]` | PROVEN STATIC |
| legal/privacy | `https://www.bigbigwon.cn/usercenter/{user-agreement,privacy}/` | `pp.txt [pp+0x405a0,0x405b0]` | PROVEN STATIC |
| support | `https://www.bigbigwon.com/support/`, `…/www.bigbigwon.cn/support/`, `https://jp.bigbigwon.com/support/`, `https://kr.bigbigwon.com/support/` | `pp.txt` | PROVEN STATIC |
| IPv4 literals | **none** — 0 matches | — | PROVEN STATIC (grep returned nothing) |
| ports | only `:8080` (API) — 10 pool occurrences, all the `m.bigbigwon.com` URL | `pp.txt` | PROVEN STATIC |

**No `bigwon-germany.oss-eu-central-1.aliyuncs.com`** in 2.22 (that 4th OSS bucket first appears in
2.23). Plaintext HTTP is permitted because the manifest sets `android:usesCleartextTraffic=true`.

## 2. Endpoints (all 13, with offsets)

| # | endpoint | pp offset |
|--:|---|---|
| 1 | `/dev/register` | `pp+0x41d28` |
| 2 | `/dev/userLogin` | `pp+0x39d60` |
| 3 | `/dev/queryConfigList` | `pp+0x45f30` |
| 4 | `/dev/addConfig` | `pp+0x45e80` |
| 5 | `/dev/changeConfig` | `pp+0x45e68` |
| 6 | `/dev/renameConfig` | `pp+0x48808` |
| 7 | `/dev/delConfig` | `pp+0x46048` |
| 8 | `/dev/queryMacroList` | `pp+0x45cf8` |
| 9 | `/dev/addMacro` | `pp+0x45a10` |
| 10 | `/dev/changeMacro` | `pp+0x45920` |
| 11 | `/dev/delMacro` | `pp+0x45c18` |
| 12 | `/dev/queryDefaultConfig` | `pp+0x46230` |
| 13 | `/dev/setConfig` | `pp+0x461d8` |

`/dev/queryDefaultConfig` **is present** (pp+0x46230). `shareConfig`, `importShareConfig` and
`queryGameList` are **absent** (0 hits). Other `/`-paths in the pool are not API routes
(`/device_info`, `/rainbow_instructions`, `/proc/self/exe`, `/dev/null`, `/dev/urandom`).

## 3. `bledata.proto` — flutter_reactive_ble Java transport

`use` command: `bledata.proto` (raw, 3,144 B) at the APK root. Header:

```proto
syntax = "proto3";
option java_package = "com.signify.hue.flutterreactiveble";
option java_outer_classname = "ProtobufModel";
```

**28 message types** (no enums):

```
ScanForDevicesRequest, DeviceScanInfo, ConnectToDeviceRequest, DeviceInfo,
DisconnectFromDeviceRequest, ClearGattCacheRequest, ClearGattCacheInfo,
NotifyCharacteristicRequest, NotifyNoMoreCharacteristicRequest, ReadCharacteristicRequest,
CharacteristicValueInfo, WriteCharacteristicRequest, WriteCharacteristicInfo,
NegotiateMtuRequest, NegotiateMtuInfo, BleStatusInfo, ChangeConnectionPriorityRequest,
ChangeConnectionPriorityInfo, CharacteristicAddress, ServiceDataEntry,
ServicesWithCharacteristics, ServiceWithCharacteristics, DiscoverServicesRequest,
DiscoverServicesInfo, DiscoveredService, DiscoveredCharacteristic, Uuid, GenericFailure
```

### What this implies about the plugin's Java-side API surface

`bledata.proto` is **not** app protocol — it is the verbatim `flutter_reactive_ble` mobile bridge
schema (signalled by `java_package com.signify.hue.flutterreactiveble` and the Dart side referencing
`package:reactive_ble_mobile/src/converter/protobuf_converter`). Every Dart↔Java BLE call is a
`MethodChannel`/`EventChannel` message that is a serialized one of these 28 messages:

* **Scanning** — `ScanForDevicesRequest{serviceUuids, scanMode, requireLocationServicesEnabled}` →
  event stream `DeviceScanInfo{id, name, rssi, serviceData, manufacturerData, serviceUuids, failure}`.
* **Connection lifecycle** — `ConnectToDeviceRequest{deviceId, servicesWithCharacteristicsToDiscover,
  timeoutInMs}`, `DisconnectFromDeviceRequest`, `DeviceInfo{connectionState, failure}`,
  `ClearGattCacheRequest/Info`, `BleStatusInfo{status}`.
* **GATT discovery** — `DiscoverServicesRequest/Info`, `DiscoveredService{serviceUuid,
  characteristicUuids, includedServices, characteristics}`, `DiscoveredCharacteristic{isReadable,
  isWritableWithResponse, isWritableWithoutResponse, isNotifiable, isIndicatable}`.
* **Data transfer** — `ReadCharacteristicRequest`/`CharacteristicValueInfo{value}`,
  `WriteCharacteristicRequest{characteristic, value}`/`WriteCharacteristicInfo`,
  `NotifyCharacteristicRequest`/`NotifyNoMoreCharacteristicRequest`.
* **Connection tuning** — `NegotiateMtuRequest/Info`, `ChangeConnectionPriorityRequest/Info`.
* **Addressing** — `CharacteristicAddress{deviceId, serviceUuid, characteristicUuid}`,
  `Uuid{bytes}`, `GenericFailure{code, message}`.

**Implication.** The Java/Kotlin side exposes exactly the reactive-BLE bridge methods
(scan / connect / discoverServices / readCharacteristic / writeCharacteristic /
requestMtu / changeConnectionPriority / disconnect …). The vendor protocol (A5/A4/A8 frames on
FFE1/FFE2) is **entirely above** this bridge: it lives in Dart, so this proto defines no
vendor/device semantics. `CharacteristicValueInfo.value` / `WriteCharacteristicRequest.value`
(`bytes`) are the sole carrier of every app command — i.e. the bridge is a generic byte pipe.
There are no custom messages: the plugin is used unmodified, and 2.22 introduces no vendor proto.