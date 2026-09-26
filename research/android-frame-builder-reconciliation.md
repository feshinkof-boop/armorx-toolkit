# Android frame-builder / wire-frame reconciliation — 2026-09-25

This document reconciles the app's internal list construction (Dart AOT, Blutter output)
against the captured wire frames, opcode by opcode. It resolves the
"internal zero placeholder vs. wire byte" question definitively.

Evidence levels: PROVEN_STATIC (Blutter asm dataflow), PROVEN_LIVE (captured BLE frames,
`android_lab/captures/armorx_ble_capture_run2.jsonl`).

## Frame construction model (PROVEN_STATIC)

Every builder allocates a fixed-size `List<int>`, stores Smi-tagged element values,
leaves the checksum slot as literal zero (`StoreField ... = rZR`), then calls
`::getCheckSum` (`gamepadset.dart` @0x761954) which computes
`sum(all elements) & 0xFF` and stores it into the last slot.

Key fact: **the internal pre-checksum list is the wire frame**, element i = wire byte i.
The zero checksum placeholder is not transmitted as an extra byte — it is replaced
in place before the write. The list IS the frame.

## Length-byte semantics (PROVEN_STATIC + PROVEN_LIVE)

The second byte of A5/A4 frames equals the **total frame length in bytes**:

| Frame | Wire bytes | Length byte | Source |
|---|---|---|---|
| A5 04 0B B4 | 4 | 0x04 | getZKMVer @0x7617f4 |
| A5 05 0E 00 B8 | 5 | 0x05 | writeDevice @0x7989bc |
| A5 05 D2 00/01 7C/7D | 5 | 0x05 | testModeSwitch @0x881a78/@0x8b1d68 |
| A5 0C EF 00×8 A0 | 12 | 0x0C | getDeviceUUID @0x791a30 |
| A4 14 D7 01 ... | 20 | 0x14 | writeDeviceConfig @0x79e63c (fragment i: chunk+5) |
| A4 0E D7 0A ... | 14 | 0x14/0x0E | final fragment (9-byte chunk: 9+5=14) |

The A4 length byte is computed as `chunk_size + 5` in the fragment loop
(`sub x1, x11, x9; add x11, x1, #5` at 0x79eaa0-0x79eaa8), where chunk_size =
`min((i+1)*15, config.length) - i*15`. Live census (run2): full fragments
frame_len=20/len_byte=0x14 ×306, tail frame_len=14/len_byte=0x0E ×34, exactly matching.

The earlier "0x0e = 14" phrasing in `docs/android-protocol.md` refers to total
frame length of the final fragment, not to a distinct length-byte rule. Both
rules are the same rule: length byte = total frame length.

## Per-opcode reconciliation

### 0B — GetZkmVersion (PROVEN_STATIC + PROVEN_LIVE)
- Encoder: `_ArmorXProWidgetState::getZKMVer` @0x7617f4 (armorx_pro_root.dart),
  `::getZKMVer` @0x800610 (rainbow_root.dart).
- Built list: [330, 8, 22, 0, 0] → wire `A5 04 0B 00` + checksum B4 (Smi 330=A5, 8=0x04, 22=0x0B).
- Live OUT `a5040bb4` ×2. Live IN `a5050b30e5` (`A5 05 0B 30 E5`, zkm=0x30=48 ✓ matches captured V41/zkm48).

### EF — GetDeviceUUID (PROVEN_STATIC + PROVEN_LIVE)
- Encoder: `_ArmorXProWidgetState::getDeviceUUID` @0x791a30 (armorx_pro_root.dart),
  @0x7ff67c (rainbow_root.dart).
- Built list: [330, 24, 478, 0,0,0,0,0,0,0,0, 0] (12 elements: A5, 0C, EF, 8 zero bytes, checksum slot).
  Eight data bytes are literal compiled zeros: StoreField rZR at 0x791a8c..0x791aa8.
  No caller can override them — the builder has no parameters for the data bytes.
- Checksum: (A5+0C+EF)&0xFF = 0xA0. Live OUT `a50cef0000000000000000a0` ×2. Exact match.
- **Precise conclusion: in the analyzed Android 2.23 client implementation, the eight EF
  request-data bytes are fixed zero literals.**

### EF reply → devUuid flow (PROVEN_STATIC)
- Reply handler (dispatcher closure @0x761b6c): `data[2]==EF` (cmp w0, #0x1de),
  requires length ≥ 12 (`cmp x1, #0xef` = 119/2≈… decoded: length check on data[2] bounds),
  reads `data[3..10]` (8 bytes), formats each as 2-hex-digit lowercase (`padLeft(2,'0')`),
  concatenates to a 16-char hex string, calls `onGetDeviceUUID` @0x761e44 →
  stores into state field_1b and forwards to `server.dart::devRegister` as devUuid.
- Live IN: a sanitized example reply `a50cef XX XX XX XX XX XX XX XX <ck>` — 8 payload bytes →
  devUuid = the 16-hex-char string of those bytes (value sanitized; raw bytes retained in the private capture).

### D6 — ReadConfig (PROVEN_STATIC + PROVEN_LIVE)
- Encoder: `_RainbowTabConfig1sWidgetState::getDeviceConfig` @0x810d2c,
  `_ConfigsConfigWidgetState::getDeviceConfig` @0x8abc64. Built list: [330, 8, 428, 0, 0]
  → `A5 04 D6 7F` (checksum 7F = A5+04+D6 & 0xFF ✓).
- Callers (2.23): page-open after 500 ms `Future.delayed` (0x7a120 µs @0x80866c), and after
  every cloud config-list response (queryConfigListResponse, delConfigResponse,
  renameConfigResponse, changeConfigResponse, addConfigResponse).
- Reply: A4/D6 fragments; dispatcher closure @0x808d68 (rainbow_tab_config_1s.dart) /
  @0x8abf40 (configs_config.dart). Requires data[0]==A5? No — A4 (cmp #0xa4) and
  data[2]==D6 (cmp w0, #0x1ac), then bounds `0 <= data[3] <= 16`, then 17-entry
  _Int32List jump table @pp+0x4cc28 relative to closure base. Case k writes
  `replaceRange((k-1)*15, min(k*15, len), data[4..])`.
- Live: 16 D6 requests → 16 complete 144-byte images (frame census 20/14 = 144/16 ✓).

### D7 — WriteConfig (PROVEN_STATIC + PROVEN_LIVE)
- Encoder: `::writeDeviceConfig` @0x79e63c (gamepadset.dart), static, takes optional
  `gamepadSet` / `gamepadSet30` named params. Serializes via `GamepadSet30::toList` @0x7a0530
  (or GamepadSet::toList @0x79f1e4), then chunks into 15-byte fragments, 1-based index,
  per-fragment checksum via getCheckSum.
- Whole-image write: the loop always writes all fragments — no delta mode (PROVEN_STATIC).
  Live: 17/17 writes were full 144-byte images.
- Ack: IN `a505d70081` ×13 for 17 writes (observer loss vs device omission unresolved).

### 0E (PROVEN_STATIC + PROVEN_LIVE)
- Encoder: `::writeDevice` @0x7989bc → `A5 05 0E 00 B8` (list [330, 10, 28, 0, 0], checksum B8 ✓).
  Also emitted from writeDpiConfig tail, writeMacroConfig tail, config_mapkey, keyboard_mapping_alert.
- Live OUT ×14, IN echo ×14 (device returns it verbatim).
- Semantics: post-write command emitted by multiple configuration-related workflows.
  Position between D7 write/ack and D6 read-back. Not named commit/apply/save — no
  decoder names it and no response payload exists. UNKNOWN beyond this.

### D2 (PROVEN_STATIC + PROVEN_LIVE)
- Encoders: `_RainbowTestState::testModeSwitch1` @0x881a78 → `A5 05 D2 00 7C`,
  `_RainbowTestState::testModeSwitch` @0x8b1d68 → `A5 05 D2 01 7D`.
- Owning page: rainbow_test.dart (the controller test-mode UI). This corrects the earlier
  "version/firmware page" temporal association: the version page hosts the test-mode
  entry; D2 is triggered by the test-mode switch UI, not by opening the version page.
- Live: the unique `D2 01`/`D2 00` pair 1.47 s apart, each echoed twice by the device.

### A4 family length-byte rule (PROVEN_STATIC + PROVEN_LIVE)
- `A4 <len> <opcode> <fragIndex> <data…> <checksum>`, len = total frame bytes = chunk+5.
- Fragmentation: 15 data bytes per full fragment; final = remainder (9 for 144);
  1-based indices; reassembly offset = (idx-1)*15.

## E2 — GetMode (PROVEN_STATIC)
No E2 frame-construction or response-decoding path exists in the analyzed Android builds:
- 2.23: all 13 enumerated frame builders lack the E2 opcode Smi (452 = 0x1c4);
  the only 452/0x1c4 immediates in package:moojiang are string-pool offset arithmetic in
  generated intl message tables (`add x2, x1, w0` before string constants), not opcodes.
- 2.24: same result across 21 builders (all listed in android-frame-builders-224.json);
  only intl-table occurrences.
- No `GetMode`/`getMode` strings exist in either object pool.
Preferred statement: **"No reachable E2 frame-construction or response-decoding path was
found in the analyzed Android 2.23 and 2.24 builds."**
