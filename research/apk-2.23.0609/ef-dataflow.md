# EF (GetDeviceUUID) dataflow — Android 2.23.0609 — 2026-09-25

All steps PROVEN_STATIC (Blutter asm addresses) unless marked PROVEN_LIVE.

```
[request]
  _ArmorXProWidgetState::getDeviceUUID @0x791a30 (armorx_pro_root.dart)
    allocate List<int>(12)
    [0]=0xA5(330) [1]=0x0C(24) [2]=0xEF(478)
    [3..10]=0×8   (StoreField rZR @0x791a8c..0x791aa8 — compiled literals,
                   no runtime source, no caller parameter)
    [11]=checksum slot 0
    getCheckSum @0x761954 -> (A5+0C+EF)&0xFF = 0xA0
    write FFE1 (writeCharacterisiticWithoutResponse)
  wire: A5 0C EF 00 00 00 00 00 00 00 00 A0        [PROVEN_LIVE x2]

[trigger chain]
  connect -> build() -> subscribeCharacteristic (CCCD 01 00 on FFE2)
          -> getZKMVer (A5 04 0B B4)                [0B]
  0B reply (A5 05 0B VV CC) -> zkm=VV stored (static 0xfd4)
          -> getDeviceParam -> GATT reads 2A24 (model), 2A26 (firmware)
  onNewReceivedData @0x7918c0:
    characteristic == 2A26 -> firmware string -> static 0xef0
                           -> getDeviceUUID()          [EF fires here]
    characteristic == 2A19 -> battery -> setState

[reply]
  dispatcher closure @0x761b6c (notification handler):
    data[0]==0xA5; data[2]==0xEF (cmp w0,#0x1de); length check
    payload = data[3..10] (8 bytes)
    hex-format: for i in 0..7: data[i+3].toRadixString(16).padLeft(2,'0')
    -> 16-char lowercase hex string
    onGetDeviceUUID @0x761e44:
      state.field_1b = hex string
      server.dart::devRegister(devUuid=<hex string>, ...)
        POST /dev/register {devUuid, devModel:"devArmorX", ...}

[wire evidence]
  IN: A5 0C EF <8 device-uuid bytes> <checksum>       [PROVEN_LIVE x1]
  The reply payload bytes ARE the devUuid the app registers server-side.
  phoneUuid never enters the EF frame in either direction.
```

Conclusion: the EF request's eight data bytes are fixed zeros in this
implementation; the EF REPLY supplies the 8-byte device UUID that becomes the
account-scoped devUuid. The Windows-recovered shape `A5 0C EF <8 bytes> CC`
is therefore an identity QUERY whose request payload is unused by the Android
client (and, by the captured evidence, by the device's reply semantics).
