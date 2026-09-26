# ARMOR-X Pro Android / BLE protocol research

This document records the normal Android/BLE control path recovered from a real ARMOR-X Pro using the current BIGBIG WON Android application. Firmware/DFU/update paths are intentionally out of scope.

## Evidence levels

- **PROVEN** — directly observed in live traffic or confirmed by static/runtime analysis.
- **STRONG EVIDENCE** — multiple signals agree but one link remains indirect.
- **UNKNOWN** — deliberately unresolved.

## Tested Android application

The tested package is:

```text
package:      com.moojiang.bigbigwon
versionName:  2.23.0609
versionCode:  12
ABI:          arm64-v8a
```

The application is Flutter/Dart AOT. The BLE implementation uses `flutter_reactive_ble` on top of RxAndroidBle2. Static analysis identified the app-side BLE layer under the Dart `moojiang/units/ble/*` classes.

A non-root physical Android device was instrumented with Frida Gadget. Gadget 17.19.0 crashed during its own constructor on the tested phone; Gadget/client 17.18.0 was stable and provided working Java instrumentation.

## Live device identity

### PROVEN

The controller advertises with an `ARMOR-X Pro_*` name. The hardware address is intentionally omitted from this repository.

Standard GATT reads returned:

```text
2A24 Model Number String:   ZJ-XT
2A26 Firmware Revision:     2741
2A19 Battery Level:         91% in the captured session
```

`ZJ-XT` is therefore a **captured runtime mark/model string**, not an inference from the retail product name.

## GATT transport

### PROVEN

The normal configuration transport uses the vendor service:

```text
00000000-0000-1000-8000-00805f9b34fb
```

with:

```text
FFE1  write without response
FFE2  read + notify
2902  CCCD, written 01 00 to enable notifications
```

No explicit MTU request was made in the captured first-contact session, so notifications used the default ATT MTU of 23 and carried at most 20 bytes.

A second vendor-looking service/characteristic family `AE00/AE01/AE02` is present. A later controlled Windows BLE inventory on the same ARMOR-X Pro established:

```text
AE01  WriteWithoutResponse
AE02  Notify
AE02 CCCD 2902
```

Passive AE02 subscription succeeded, but no AE02 notifications appeared during clean standalone or controller-attached idle windows. No guessed AE01 writes were sent. Its application semantics therefore remain **UNKNOWN**.

An earlier working note guessed an `FFE0` service by convention. Live GATT enumeration corrected that: the actual vendor service UUID is the all-zero Bluetooth-base UUID above.

## Shared packet family with Windows

### PROVEN

Android and Windows use the same application protocol family.

Short frames:

```text
A5 | length | opcode | data... | checksum
```

Checksum:

```text
checksum = sum(all preceding frame bytes) & 0xFF
```

Every captured Android short frame validated under this rule. The same rule reproduces the recovered Windows commands including GetMode, GetZkmVersion, GetProfileSize, GetMacroList, and D6.

### First-contact sequence

The captured Android first-contact sequence issued:

```text
A5 04 0B B4
A5 0C EF 00 00 00 00 00 00 00 00 A0
A5 04 D6 7F
```

The app did **not** issue E2/GetMode during this first-contact window.

The eight zero bytes in the captured EF request are a live instance of the Windows-recovered request shape:

```text
A5 0C EF <8 bytes> checksum
```

Static analysis of the 2.23 Dart AOT builder (`_ArmorXProWidgetState::getDeviceUUID` @0x791a30) proves the eight request bytes are **compiled zero literals** with no runtime source and no caller-overridable parameter: in the analyzed Android 2.23 client implementation, the eight EF request-data bytes are fixed zero literals. The EF reply's bytes 3..10 are hex-formatted into the 16-char `devUuid` string that the app sends to `/dev/register` (see `research/apk-2.23.0609/ef-dataflow.md`).

## A4 fragmentation

### PROVEN

Long transfers use `A4` fragments:

```text
A4 | length | opcode | fragment_index | up to 15 data bytes | checksum
```

For the 144-byte configuration image:

- fragments are indexed 1 through 10;
- fragments 1..9 carry 15 data bytes each;
- fragment 10 carries the remaining 9 data bytes;
- `9 * 15 + 9 = 144`;
- the frame checksum remains the same sum-mod-256 rule.

Fragments may be interleaved when the app pipelines write-without-response traffic, so reassembly must use the fragment index as an offset/key rather than assuming sequential arrival.

## D6: full configuration read

### PROVEN

Request:

```text
A5 04 D6 7F
```

Behavior:

- D6 is issued as a payload-free short request;
- the device replies with ten `A4` fragments carrying opcode D6;
- the reassembled payload is exactly 144 bytes;
- 16 captured D6 requests produced 16 complete 144-byte replies in the analyzed run.

Therefore D6 is the normal **full configuration read** operation for the captured Android path.

## D7: full configuration write

### PROVEN

D7 sends the complete 144-byte configuration image as ten `A4` fragments.

All 17 captured D7 write passes carried a complete 144-byte image, even when the logical edit changed only one configuration byte.

The device emits a short D7 acknowledgement:

```text
A5 05 D7 00 81
```

Thirteen acknowledgements were observed for 17 write images. The capture cannot distinguish device-side omission from observer loss for the four missing acknowledgements, so a strict one-ack-per-write contract is **not** claimed.

## Configuration integrity

### PROVEN live

The 144-byte configuration carries an internal CRC in addition to the per-frame checksum.

```text
bytes 0..1   CRC16, stored big-endian
bytes 2..143 CRC input
algorithm    CRC-16/MODBUS style, init 0xFFFF, polynomial 0xA001
```

All distinct captured configuration images validated under the same algorithm already implemented by the toolkit.

All captured outbound D7 images carried a valid app-generated CRC before transmission.

## Live field correlation

Two controlled UI actions provide direct live confirmation of existing config-field semantics.

### Profile change

Only the CRC plus absolute offset 45 changed:

```text
offset 45
field: sensorRightCurve0YDivx
0x0A -> 0x28
10 -> 40
```

This does **not** make offset 45 a profile-index field. It proves that the selected profiles differed at the already named sensor-curve field.

### Rear mapping M1 -> A

Only the CRC plus absolute offset 135 changed:

```text
mapKeys starts at offset 112
M1 source ID = 23
112 + 23 = 135

offset 135:
0x17 -> 0x00
23   -> 0
M1   -> A
```

This is live confirmation of the toolkit rule:

```text
mapKeys[source_button_id] = target_button_id
```

## Other observed opcodes

### 0E

A recurring sequence was observed around config write/read cycles:

```text
D7 write
D7 acknowledgement
0E
D6 read
```

Static analysis (2.23/2.24) showed 0E as a post-write command emitted by multiple configuration-related workflows (`writeDevice` after config/macro/DPI writes; also `writeConnectModeConfig`, `getConnectModel`, `getMTU`, and the 2.24 calibration pages key their response parsers on it).

A controlled 2026-09-26 power-cycle experiment now provides direct live evidence for configuration persistence:

1. D7 wrote a one-byte logical M1 mapping change (plus CRC).
2. D6 immediately read the new image back exactly.
3. Without 0E, a power cycle reverted the controller to the previously persisted configuration.
4. Repeating the same D7 write followed by `A5 05 0E 00 B8` preserved the new configuration across power cycle.

Therefore, for the tested ARMOR-X Pro configuration-write path, **D7 applies the image to live/volatile state and 0E persists that written configuration across power loss**. This conclusion is intentionally limited to the tested configuration path; it does not claim a broader firmware-internal implementation.

In the Windows BLE run, each 0E transmit was followed by two identical FFE2 notifications of `A5 05 0E 00 B8`.

### D2

A unique pair:

```text
D2 01
D2 00
```

Static analysis (2.23) placed both D2 encoders in `rainbow_test.dart` (`testModeSwitch1` @0x881a78 -> `A5 05 D2 00 7C`; `testModeSwitch` @0x8b1d68 -> `A5 05 D2 01 7D`) — the controller test-mode UI.

A controlled live Windows BLE test now closes the primary ARMOR-X Pro semantics:

- `A5 05 D2 01 7D` enables a continuous raw-input stream on FFE2.
- `A5 05 D2 00 7C` disables it.
- 4,812 18-byte reports were captured over 75.20 s (~63.98 Hz).
- All 4,812 checksums validated.

Raw report layout:

```text
byte 0      A5
byte 1      12  (18-byte frame)
byte 2      02  (raw input report)
byte 3      rear buttons: bit0=M2, bit1=M3, bit2=M4
byte 4      bit0=Up, bit1=Down, bit2=Left, bit3=Right, bit7=M1
byte 5      bit0=LT digital, bit1=RT digital, bit5=L3, bit6=R3
byte 6      bit0=A, bit1=B, bit3=X, bit4=Y, bit6=LB, bit7=RB
bytes 7..8  left-stick X, signed 16-bit big-endian
bytes 9..10 left-stick Y, signed 16-bit big-endian
bytes 11..12 right-stick X, signed 16-bit big-endian
bytes 13..14 right-stick Y, signed 16-bit big-endian
byte 15     LT analog 0..255
byte 16     RT analog 0..255
byte 17     additive checksum modulo 256
```

Observed stick extrema were -32768 / +32767. D2 is therefore a controller-test/raw-input streaming mode on the tested ARMOR-X Pro path, not a firmware/version query.

In 2.24 a second D2 family also appears in configV484 stick pages; that separate family is not generalized from this ARMOR-X Pro result.

## Instrumentation lessons

- Frida hooks placed only on Android base callback classes can miss obfuscated subclasses that override the methods. The working logger hooks the concrete callback object's class when it is passed into `startScan` / `connectGatt`, plus a live loaded-class sweep.
- Frida 17 host-created scripts may require explicitly loading the Java bridge used by `frida-tools`.
- Generic Java collections returned through Frida may expose elements as erased `java.lang.Object`; `Java.cast` to `BluetoothGattService`, `BluetoothGattCharacteristic`, and `BluetoothGattDescriptor` is required before calling concrete methods.
- `BluetoothGattCharacteristic.getValue()` observed in completion callbacks may be stale under pipelined writes. For outbound reconstruction, use the write-call stream itself.
- Duplicate hook events must not be mistaken for duplicate wire writes; correlate against the authoritative write/ack stream.

## Independent public corroboration

The public project `ceeprus/armorx-battery` independently reads the Armor X Pro battery through standard BLE characteristic `2A19` from Windows using Bleak. Its source also states that the author decoded official ELITE BLE traffic and probed the USB/dongle path, but those underlying captures are not published in that repository. Treat those statements as external corroboration, not as substitutes for this project's captured evidence.

## Current unknowns

- Broader semantics of 0E outside the tested configuration-write persistence path.
- Purpose/application protocol of AE01/AE02 beyond the proven GATT properties and passive-notify behavior.
- Whether the Windows/F20 HID path exposes the same normal command stream once the RF link state and backend behavior are reproduced.
- Whether E2/GetMode requires a state transition not exercised by the Android application (no reachable E2 frame-construction or response-decoding path was found in the analyzed Android 2.23 and 2.24 builds — see `research/android-frame-builder-reconciliation.md`).

## Static dispatch closure (2026-09-25)

The formerly open "exact static Dart AOT dispatch sites" question is closed for both analyzed builds by full Blutter dumps: 13 frame-builder functions in 2.23 and 21 in 2.24 are enumerated in `research/android-frame-builders-*.json`, and 5/10 response dispatchers in `research/android-response-dispatchers-*.json`. The config-length derivation (checkConfigLength, -2/0xFE padding terminator) and the 88/144/240/280/484 family routing are documented in `research/config-format-family-map.md`; factory templates with verified CRCs are in `research/default-config-templates.json`.

Firmware/DFU/update behavior remains intentionally separate.
