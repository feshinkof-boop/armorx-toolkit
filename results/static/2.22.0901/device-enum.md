# 2.22.0901 — the `Device` enum, and proof that ARMOR-X Pro is implemented

All device facts below come from the 2.22.0901 binary itself
(`/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/`, APK sha256
`785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`).
No later build is used as evidence.

## 1. The complete 2.22 `Device` enum

`enum Device` is declared in `define.dart` (as in later builds), and each value is emitted as an
object instance. PROVEN STATIC from `objs.txt`:

```
grep -A3 'Obj!Device@' objs.txt | grep -E 'Obj!Device|off_8|off_10' | paste - - -
```
```
Obj!Device@8fce31 : {  off_8: int(0x0),  off_10: "devNone"     }
Obj!Device@8fce51 : {  off_8: int(0x1),  off_10: "devRainbow"  }
Obj!Device@8fce71 : {  off_8: int(0x2),  off_10: "devRainbowS" }
Obj!Device@8fce91 : {  off_8: int(0x3),  off_10: "devArmorX"   }
```

| id | symbol | display name (recoverable?) | config family | screen | BLE name / scan prefix | feature flags |
|---|---|---|---|---|---|---|
| 0 | `devNone` | none (placeholder) | — | home / device chooser | — | — |
| 1 | `devRainbow` | **"RAINBOW"** — PROVEN (`messages_en.dart` 0x5bc2a4, stored for key `device_rainbow_title` @0x5bc290) | 88 and/or 144 — see §3 | `_RainbowWidget` (`widgets/rainbow/rainbow_root.dart`) | scan prefix **"Rainbow"** — PROVEN (home.dart 0x8d0564, devRainbow branch of `_startScanning`) | ARMOR-X-specific flags absent |
| 2 | `devRainbowS` | UNKNOWN — no l10n title key found | UNKNOWN | UNKNOWN — no dedicated root widget found | branch exists at home.dart 0x8d05fc (compare against `Obj!Device@8fce71`) but the prefix string was not resolved | UNKNOWN |
| 3 | `devArmorX` | **"ARMOR-X Pro"** — PROVEN (`messages_en.dart` 0x5bc0d8, stored for key `device_armor_title` @0x5bc0c4) | **144** (`GamepadSet30`) — PROVEN, see §3 | `ArmorXProWidget` / `_ArmorXProWidgetState` (`widgets/armor-x_pro/armorx_pro_root.dart`) | scan prefix **"ARMOR-X Pro_"** — PROVEN (home.dart **0x8d05d8**, devArmorX branch of `_startScanning` @0x8d0470) | see §4 |

**ARMOR-X Pro enum id in 2.22 = 3.** PROVEN STATIC.
Display name for the device is also present as the bare pool string `"ARMOR-X Pro"` at
`pp+0x2b000`; the device-thumbnail asset is `assets/dev_armorx.png`.
Related assets present: `assets/dev_armorx.png`, `assets/dev_rainbow.png`.
l10n keys present: `device_armor_title`, `device_armor_description`, `device_rainbow_title`,
`device_rainbow_description`, `device_choose`, `device_config`, `device_disconnect`.

`devRainbowS` display name and screen are **UNKNOWN** — the "S" variant has no title key and no
`rainbow_s/` widget file exists; settling it needs a trace of the device chooser taps or a
selector-resolved Blutter build.

## 2. Four-way history

Machine-readable: `/home/salamanka/armorx-lab/results/version-diff/device-enum-history.json`.

| symbol | 2.22.0901 | 2.23 | 2.24 | 4.0.8 |
|---|---|---|---|---|
| `devNone` | **0** | 0 | 0 | 0 |
| `devRainbow` | **1** | 1 | 1 | 1 |
| `devRainbowS` | **2** | 2 | 2 | 2 |
| `devRainbow2Pro` | — | 3 | 3 | 3 |
| `devRainbow3` | — | — | — | 4 |
| `devMSY` | — | — | — | 5 |
| `devRainbow2Lite` | — | — | 4 | 6 |
| `devC2SL` | — | — | 5 | 7 |
| `devBLITZ_ULT` | — | 4 | 6 | 8 |
| `devBLITZ_LITE` | — | 5 | — | — |
| `devCHOCO` | — | — | 7 | 9 |
| **`devArmorX`** | **3** | **6** | **8** | **10** |
| `devGale2` | — | — | — | 11 |
| `devKeyboardDouJiangV1` | — | — | — | 12 |
| **enum size** | **4** | **7** | **9** | **13** |

Growth pattern: devices are inserted into the *middle* of the enum, so every insertion renumbers
all later ids (ARMOR-X walks 3 → 6 → 8 → 10). Any artefact keyed on the numeric id is build-specific.
`devBLITZ_LITE` is the only value ever removed (present 2.23, gone by 2.24).

## 3. Is ARMOR-X Pro implemented in 2.22? — YES, five independent anchors

| anchor | evidence | label |
|---|---|---|
| **1. enum value** | `devArmorX`, id 3, `Obj!Device@8fce91` in `objs.txt` | PROVEN STATIC |
| **2. screen / widget class** | `ArmorXProWidget` (class id 2903) + `_ArmorXProWidgetState` in `widgets/armor-x_pro/armorx_pro_root.dart`; its state has `subscribeCharacteristic`, `getZKMVer`, `getDeviceUUID`, `onGetDeviceUUID`, `devRegisterResponse`, a `TabBar` of sub-screens, plus a separate `armorx_pro_config_config.dart` widget and the macro widget | PROVEN STATIC |
| **3. device chooser entry** | `_DeviceListState::_build` @**0x93f244** branches on `Obj!Device@8fce91` (home.dart:2901) and builds `deviceRouteButton(..., Device.devArmorX, S::device_armor_description(), "assets/dev_armorx.png", onClick: …)` via `moojiang/routes/device.dart::deviceRouteButton` @**0x93f8c4** (`routes/device.dart:6`) | PROVEN STATIC |
| **4. scan / advertisement filter** | `_HomeState::_startScanning` @**0x8d0470**: `if (device == Obj!Device@8fce91) prefix = "ARMOR-X Pro_"` (string at **0x8d05d8**; the devRainbow branch uses `"Rainbow"` at 0x8d0564) | PROVEN STATIC |
| **5. config serializer** | 144-byte `GamepadSet30` + `GamepadParam30`; `widgets/armor-x_pro/armorx_pro_config_config.dart` allocates **only** `GamepadSet30` (1× `AllocateGamepadSet30Stub`, 0× `AllocateGamepadSetStub`) while the generic/Rainbow config pages allocate both | PROVEN STATIC |

Also present: GATT UUIDs for the ARMOR-X path in `define.dart`
(`uuidBatteryService "180F"`, plus the vendor service/characteristic UUIDs), and the ARMOR-X
first-contact sequence in `armorx_pro_root.dart`: subscribe → `getZKMVer` (`A5 04 0B B4`) →
on the 0x0B reply call `getDeviceParam` + `getBatteryParam` → `getDeviceUUID` (`A5 0C EF …`) →
`onGetDeviceUUID` → `devRegisterResponse` (`POST /dev/register`).

### Config-family guard

`GamepadDef::writeDeviceConfig` @**0x7a005c** chooses the serializer by **which config object the
widget state holds** (null-check on `field_23` vs `field_27`, gamepadset.dart ~0x7a025c-0x7a02b4):
`field_23 != null` → `GamepadSet30::toList` @0x7a1f60 (144 bytes); otherwise `field_27` →
`GamepadSet::toList` @0x7a0c50 (88 bytes). So the family is a *device/state* property, not an
opcode property. No firmware-version guard was found on any builder.

## 4. Earliest ARMOR-X-specific code

Lowest addresses in the ARMOR-X files (PROVEN STATIC — first `addr:` headers per file):

| file | earliest address | first function |
|---|---|---|
| `widgets/armor-x_pro/armorx_pro_root.dart` | **0x7a9e40** | `_ArmorXProWidgetState::deviceConnected` (the first ARMOR-X-only body) |
| `widgets/armor-x_pro/armorx_pro_config_config.dart` | **0x89a408** | `_ArmorXProConfigWidgetState::_changeTab` region (block also contains 0x573c28/0x585664 which are shared helper closures) |

The earliest ARMOR-X-specific code object in the image is therefore
`_ArmorXProWidgetState::deviceConnected` at **0x7a9e40** in
`package:moojiang/widgets/armor-x_pro/armorx_pro_root.dart`. The class `ArmorXProWidget` itself
is instantiated by `_HomeState`/`_DeviceListState` when `curDevice == Device.devArmorX`.
Note: in 2.22 the ARMOR-X protocol logic lives entirely in the **widget state** — there is no
dedicated `ArmorXProInteractor`/repository class (that abstraction appears in later builds).

## 5. Raw search commands

```
cd /home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out
grep -A3 'Obj!Device@' objs.txt | grep -E 'Obj!Device|off_8|off_10' | paste - - -
grep -rn 'Obj!Device@8fce91' asm/moojiang/
grep -rn '"ARMOR-X Pro_"\|"Rainbow"' asm/moojiang/widgets/home.dart
grep -n 'device_armor_title' -A4 -B4 asm/moojiang/generated/intl/messages_en.dart
grep -oE 'addr: 0x[0-9a-f]+' asm/moojiang/widgets/armor-x_pro/armorx_pro_root.dart | sort | head -3
for f in widgets/armor-x_pro/armorx_pro_config_config.dart widgets/rainbow/rainbow_tab_config.dart; do
  echo $f; grep -c AllocateGamepadSet30Stub $f; grep -c AllocateGamepadSetStub $f; done
```