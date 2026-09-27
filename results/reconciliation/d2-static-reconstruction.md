# D2 / Button Test Static Reconstruction

## 1. Executive result

The official app's Button Test ("按键测试") is a **single-toggle** feature: it writes one 5-byte
frame to enable raw button reporting, listens to notifications, and writes the mirror frame on
exit. **No hidden start command, no delay, no firmware gate, no device-enum gate and no
re-subscribe step exists on this path in any of the four builds analysed.**

Consequence for our harness: the reconstructed 4.0.8 TX/RX sequence is **byte-for-byte what our
harness already does** for a 4.0.8-generation unit, so **no missing command-level precondition was
found**. The D2 silence on the real unit therefore remains unexplained by the official app's
protocol behaviour, and the verdict is `D2 ROOT CAUSE REMAINS UNKNOWN AFTER FULL STATIC
RECONSTRUCTION` — with one unproven behavioural difference left (write type: with vs without
response) recorded for a future reversible test.

## 2. Research question

What does the official app do before, during or after D2 that our real-device harness is missing?

## 3. Builds analyzed

| build | app version | Dart | AOT tree |
|---|---|---|---|
| 2.22 | 2.22.0901 | 2.x era | `armorx-lab/static/blutter/2.22.0901/blutter_out` |
| 2.23 | 2.23.x | 2.19.6 | `armorx/re/blutter_out` |
| 2.24 | 2.24.0919 | 3.2.3 | `armorx/re/v224/blutter_out` |
| 4.0.8 | 4.0.8 | 3.12.2 | `armorx-re/mygt408/blutter_out` |

## 4. 4.0.8 D2 entry point

Two entry layers, both PROVEN STATIC:

1. **UI**: `_ArmorXProMoreWidgetState::build` renders a ListTile whose caption is the literal
   string `按键测试` ("Button Test") at `0x940684`; its `onTap` closure `0x94773c` pushes a
   `MaterialPageRoute` whose builder `0x947674` returns `RainbowTest`. This is the ARMOR-X Pro line
   — the same product family as our unit — so this path is the relevant one.
2. **Page state**: `_RainbowTestState` (`createState` @ `0xb08f98`). Its `initState` registers an
   async callback that calls `BluetoothModel::testModeSwitch(true)` @ `0xacf8cc` and only then
   `subscribeCharacteristic()` @ `0xacf8dc`.

Frame builder: `BluetoothModel::testModeSwitch` @ **`0xabaef4`** (verified by the parent:
`mov x16, #0x14a` @ `0xabaf3c`, `#0xa` @ `0xabaf44`, `#0x1a4` @ `0xabaf4c`).

## 5. 4.0.8 complete TX workflow

| step | action | bytes | grade |
|---|---|---|---|
| 1 | GATT notify armed for FFE2 by `BluetoothModel::onCharacteristicChanged` @ `0xaca7c4`, called from `initGattServices` @ `0xaca690` — i.e. **at connect time**, not by the page | CCCD write (value UNKNOWN) | PROVEN STATIC |
| 2 | user opens 按键测试 → `RainbowTest` page | — | PROVEN STATIC |
| 3 | `testModeSwitch(true)` → `List<int>` of tagged Smis `0x14a/0xa/0x1a4/0x2/0xfa` (= `A5 05 D2 01 7D`), written via a stored async write callback on `FFE1` | `A505D2017D` | PROVEN STATIC |
| 4 | `subscribeCharacteristic()` wraps the already-armed notify stream (`_BroadcastStream` @ `0xacf974`) and listens (@ `0xacf9a4`) | — | PROVEN STATIC |
| 5 | on dispose: cancel the Dart listener, then `testModeSwitch(false)` if the Provider-resolved `BluetoothModel` is connected | `A505D2007C` | PROVEN STATIC |

**There is no second start command, no delay and no ack handling.** The checksum on this path is a
hard-coded literal (`getCheckSum` is not called here).

## 6. 4.0.8 complete RX / parser workflow

- Notifications arrive on **`0000FFE2`** and are forwarded through a broadcast stream
  (`BluetoothModel` field_43) by `BluetoothModel::onCharacteristicChanged`.
- `_RainbowTestState::analysisData` @ **`0xacfa64`** (size `0x1248`) is the parser.
- **Gate** (verified by the parent): `0xacfaac: cmp w0, #4` = tagged Smi 4 → **value 2**, i.e.
  `frame[2] == 0x02`. Frames failing it jump to `0xad0c80` (alternate branch, UNKNOWN).
- On match: bytes `[3..6]` are combined big-endian into a 32-bit key mask
  (`0xFF000000/0x00FF0000/0x0000FF00/0x000000FF`) requiring at least 7 bytes.
- The mask **bit index equals the key id**; the page holds one boolean per key (powers of two at
  state fields `0x117..0x177`), compares against the previous snapshot and calls `setState` only on
  change. Analog axes only trigger a rebuild when the delta exceeds `327.68`.

## 7. Preconditions and state gates

- The only gates found in 4.0.8 are: the parser's `frame[2] == 2`, and the **connected-state check
  before sending the disable frame** on dispose. PROVEN STATIC.
- No firmware-version gate, no device-enum branch, no gamepad/onboard mode check, no
  controller-presence check, no UI-state flag before enabling. PROVEN STATIC (absence in the
  analysed functions).
- See §21 and the precondition ledger for what "absence" can and cannot prove.

## 8. BLE subscription / connection behavior

- **4.0.8**: FFE2 notification is armed once at connect; the page only adds a Dart-level listener.
  Dispose removes the Dart listener only. No un-/re-subscribe sequence. PROVEN STATIC.
- **2.22 / 2.23 / 2.24**: the page itself performs `subscribeCharacteristic()` and cancels it on
  dispose; in these builds the D2 enable is issued **before** the page-level subscription exists
  (the write is not awaited). PROVEN STATIC.
- MTU: no MTU negotiation or BLE-state change appears on this path in any build. UNKNOWN whether a
  global connect-time MTU request exists elsewhere.

## 9. Timing / delays / asynchronous behavior

- The enable write is issued asynchronously and **not awaited** before the subscription is set up
  (all builds). PROVEN STATIC.
- No `Duration`-based delay exists in the D2 path. The only `Duration` in the page is a 500 ms
  re-render for the disconnected state. PROVEN STATIC.

## 10. D2 enable frame

`A5 05 D2 01 7D` — identical in all four builds, built as the tagged-Smi list
`[0x14a, 0xa, 0x1a4, 0x2, 0xfa]`; checksum = Sum8 of the preceding bytes (`0xA5+0x05+0xD2+0x01 =
0x17D → 0x7D`). PROVEN STATIC.

## 11. D2 disable frame

`A5 05 D2 00 7C` — same construction with `0x00` and checksum `0x7C`, sent from `dispose` and
gated on the connection being up. PROVEN STATIC.

## 12. Expected D2 event format

18-byte `A5 12 02 …` frames on FFE2: `[0]=0xA5`, `[1]=0x12` (length), `[2]=0x02` (status opcode),
`[3..6]` = 32-bit **big-endian** key mask, `[7..14]` = four signed 16-bit BE axes,
`[15]` = LT analog, `[16]` = RT analog, `[17]` = trailing byte never read by the page.

## 13. Press / release parsing

There is **no press/release event typing**: each notification carries the absolute mask, so a key
is *down* while its bit is set and *up* when the bit clears. The page derives edges by comparing
the new mask with the previous snapshot. No debounce, no ignore-counter. PROVEN STATIC.

## 14. Key-ID extraction

`mask = (b3<<24) | (b4<<16) | (b5<<8) | b6`; **bit index == key id** (verified live earlier in the
project and consistent with the reconstructed extraction). The 4.0.8 boolean field set uses bits
0,1,3,4,6,7,8,9,10,11,13,14,16–19,23–31 — i.e. ids 2,5,12,15,20,21,22 have no boolean field in
this page. STRONG EVIDENCE (derived from the state-field table, not a decoded literal list).

## 15. Device / firmware / enum branches

None found on the D2 path. `subpackageLength()` in `define.dart` branches on `curDevice.field_7`
for **configuration frame sizes** (20/48/72), which are unrelated to the 5-byte D2 toggle and the
18-byte status frame. PROVEN STATIC (for the absence of a D2-specific branch).

## 16. 2.24 comparison

Same frames and same toggle semantics. Entry `_RainbowTestState::initState` @ `0x91cf94`;
builders `testModeSwitch` @ `0x91e380` / `testModeSwitch1` @ `0x93371c`; parser `analysisData`
@ `0x91d130`. Enable is issued first (`@0x91cf94`) and not awaited, then `subscribeCharacteristic`
@ `0x91cfdc`. The parser's first comparison is `0x24` (tagged Smi → 36 or a length of 36); the
analyst could not settle whether that is a length gate or an element compare → recorded as
**UNKNOWN**. Key-mask extraction, press/release semantics and the dispose sequence match 4.0.8.

## 17. 2.23 comparison

Enable `A5 05 D2 01 7D` from `testModeSwitch` @ `0x8b1d68` (called from `initState` @ `0x8b0504`);
disable from `testModeSwitch1` @ `0x881a78` (called from `dispose` @ `0x8819d0`, gated on
`DeviceConnectionState == connected` @ `0x90dea1`). Write path
`BleDeviceInteractor::writeCharacterisiticWithoutResponse` @ `0x4d0eb4` → **write-without-response
on FFE1** (this is the strongest static evidence in the whole set for the write type). Parser is a
single closure @ `0x8b0654` that gates on **`frame[1] == 0x12` (18) only** and never compares the
opcode byte; the 5-byte D2 echo is therefore dropped by the length gate. 21 keys decoded
(Capture/Guide/M5/M7 absent).

## 18. 2.22 comparison

Same structure as 2.23: enable from `testModeSwitch` @ `0x8e3a88` / `0x8e3be4` (called from
`initState` @ `0x8e1e94`), disable from `dispose` @ `0x95a864` gated on the connection state, write
via `write-without-response` on FFE1, parser = notify closure @ `0x8e2430` gated on `frame[1] == 18`
with the header, opcode and checksum **not** validated. Same 21-key set, same absolute-mask
semantics.

## 19. Cross-version conclusions

- The D2 **toggle is stable across five years of builds**: same two frames, same characteristics,
  same absolute-mask status format, same "no ack, no delay, no extra command" structure.
- The **parser gate hardened over time**: length-only (2.22/2.23) → opcode-aware `frame[2] == 2`
  (4.0.8). No build gates on firmware version or device enum.
- The **subscription ownership moved**: page-owned (2.22–2.24) → connection-owned (4.0.8).
- No build shows a precondition our harness omits.

## 20. What our real-device harness is missing

Against the reconstructed 4.0.8 sequence, our harness already performs: connect with FFE2 notify
armed, a link-health `0B` (extra, not present in the app), the D2 enable write, and notification
listening. **No missing step was found at the command level.**

Differences that remain (evidence-graded, none proven to matter):

1. Our harness sends `0B` before D2 — the app does not. (STRONG EVIDENCE difference, benign
   UNKNOWN).
2. Write type for the D2 enable: `write-without-response` is PROVEN STATIC for 2.22/2.23; for
   **4.0.8 it is UNKNOWN**. Our harness uses write-without-response. If the 4.0.8 app used
   write-with-response, that would be the one unmodelled behavioural difference.
3. Our harness's D2 enable is awaited/observed and followed by a short drain; the app fires it
   unawaited. Timing only.

## 21. Candidate missing precondition(s)

`MISSING PRECONDITION: UNKNOWN` (none proven). The only candidates left, in evidence order:

1. **D2 write type (response vs no-response) in the 4.0.8 generation** — STRONG EVIDENCE that it
   is worth one reversible test; UNKNOWN whether it changes device behaviour.
2. **CCCD re-arm after the D2 enable** — INFERRED from the 2.22–2.24 ordering only; CONTRADICTED as
   a requirement by 4.0.8, where notifications are armed at connect before the enable.

## 22. Safe real-device test proposal

See `results/experiments/proposed-d2-precondition-test.md`. It is read-only with respect to
configuration: D2 enable/disable only, no D7/D8/DPI/lighting/RCSP command.

## 23. Rejected hypotheses

| hypothesis | why rejected |
|---|---|
| a hidden start command after D2 | no such call exists in any of the four builds (PROVEN STATIC) |
| a firmware/device-enum gate | no such comparison on the D2 path (PROVEN STATIC) |
| D2 requires a preceding `0B`/`EF`/`D4`/`D6` | the app sends none of them (PROVEN STATIC) |
| the first event is deliberately ignored | no skip counter; the D2 echo is dropped by the opcode/length gate (PROVEN STATIC) |
| the device needs a re-subscribe after enable | 4.0.8 subscribes at connect *before* the enable (CONTRADICTED) |
| a gamepad/onboard mode must be set first | nothing on the path reads D4 fields (PROVEN STATIC absence) |
| MTU negotiation is required | no MTU logic on this path (PROVEN STATIC absence) |

## 24. Remaining unknowns

See `d2-unknowns.md` — 29 unknowns across builds, of which the write type (4.0.8), the `0x24`
gate in 2.24, bytes `[15..16]` semantics and the alternate `analysisData` branch are the ones that
could still change the picture.

## 25. Evidence ledger

See `d2-evidence-index.json` (INDEXED, with ids `D2-<BUILD>-<CATEGORY>-###`).

## 26. Artifact / source provenance

- Blutter AOT disassembly trees for all four builds (paths in §3), plus `objs.txt` / `pp.txt`
  object-pool dumps, read with `grep`/`sed`/custom Python. No Ghidra/rizin pass was needed: the
  Blutter output already carries function names, addresses and cross-file call annotations.
- Parent-verified anchors: `testModeSwitch` @ `0xabaef4` (4.0.8) and the `analysisData` gate
  `cmp w0, #4` @ `0xacfaac` (4.0.8), both re-read from the binary tree by the parent.
- Live harness frames are used only as corroboration and are labelled as such.

## 27. Final verdict

**D2 ROOT CAUSE REMAINS UNKNOWN AFTER FULL STATIC RECONSTRUCTION.**

The official app's Button Test workflow is now fully reconstructed and it contains **no step our
harness is missing**. The silence is therefore not explained by an omitted command, gate, delay or
subscription step; it must lie in behaviour outside the reconstructed path (write type, device-side
state, or firmware), and the single remaining reversible candidate is the D2 write type, for which
a test is proposed but not executed.
