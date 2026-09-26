# BLE initialization call graph — Android 2.23.0609 (ARMOR-X Pro page) — 2026-09-25

PROVEN_STATIC from Blutter asm; corroborated by the captured live session.

```
initState @0x8a9894 (_ArmorXProWidgetState)
  EasyLoading init
  BleDeviceConnector::connect @0x8a9af4
    -> FlutterReactiveBle::connectToDevice(deviceId)
  QualifiedCharacteristic FFE1 (write, state field_2b)
  QualifiedCharacteristic FFE2 (read+notify, state field_2f)
  Timer.periodic -> getBatteryParam (2A19 polling)

connection state stream (build @0x7609f0):
  disconnected -> disconnect cleanup
  connected (field_13 false -> true):
    BleDeviceInteractor::subScribeToCharacteristic (FFE2)   [CCCD 01 00]
    -> getZKMVer @0x7617f4                                  [0B: A5 04 0B B4]

notification handler @0x761b6c (FFE2 stream):
  data[0]==0xA5?
    data[2]==0x0B (cmp #0x16):
      zkm = data[3] -> static 0xfd4
      -> getDeviceParam @0x791f04
           readCharacteristic 2A24 (Model Number String)
             -> readCharacteristic 2A26 (Firmware Revision)
      -> getBatteryParam @0x791738 (readCharacteristic 2A19)
    data[2]==0xEF (cmp #0x1de):
      data[3..10] -> hex string -> onGetDeviceUUID @0x761e44
        -> state field_1b, server.dart::devRegister

onNewReceivedData @0x7918c0 (characteristic-read completions):
  characteristic == 2A26 -> firmware -> static 0xef0 -> getDeviceUUID @0x791a30 [EF]
  characteristic == 2A19 -> battery -> setState

[rainbow_tab_config_1s page] build @0x816bfc:
  Future.delayed(500 ms) -> getDeviceConfig @0x810d2c         [D6: A5 04 D6 7F]
  notification closure @0x808d68: A4/D6 reassembly -> parsingData -> checkConfigLength
```

State variables mutated during init: connector field_13 (false->true),
static 0xfd4 (zkm), static 0xef0 (firmware string), state field_1b (devUuid),
state field_1f (battery). No protocol sleeps except the 500 ms pre-D6 delay.

Distinction preserved: 0B -> EF -> D6 is the VENDOR COMMAND subsequence; the
complete chronological GATT sequence is connect -> CCCD subscribe -> 0B ->
(2A24/2A26/2A19 standard reads interleaved) -> EF -> [page] -> 500 ms -> D6.
