# D2 cross-version matrix

| Field | 2.22 | 2.23 | 2.24 | 4.0.8 |
|---|---|---|---|---|
| D2 present | YES | YES | YES | YES |
| Entry function | _RainbowTestState::initState | _RainbowTestState::initState | _RainbowTestState::initState | _ArmorXProMoreWidgetState::build (按键测试) -> RainbowTest -> initState |
| Entry address | 0x8e1e94 | 0x8b0504 | 0x91cf94 | 0x940684 / 0xacf744 (callback 0xacf874) |
| Enable frame | A5 05 D2 01 7D | A5 05 D2 01 7D | A5 05 D2 01 7D | A5 05 D2 01 7D |
| Disable frame | A5 05 D2 00 7C | A5 05 D2 00 7C | A5 05 D2 00 7C | A5 05 D2 00 7C |
| Command before D2 | none | none | none | none |
| Command after D2 | none | none | none | none |
| Required state flag | connectionState==connected (disable only) | connectionState==connected (disable only) | connectionState (disable only) | Provider BluetoothModel (disable only) |
| Device enum gate | none found | none found | none found | none found |
| Firmware gate | none found | none found | none found | none found |
| Controller-presence gate | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN |
| FFE2 subscribe before D2 | NO (subscribe follows the enable) | NO (subscribe follows the enable) | NO (subscribe follows the enable) | YES (armed at connect, before the page enable) |
| Unsubscribe/re-subscribe | cancel on dispose | cancel on dispose | cancel on dispose | Dart listener removed on dispose; no CCCD change |
| MTU behavior | UNKNOWN (no MTU code on this path) | UNKNOWN | UNKNOWN | UNKNOWN |
| Delay before enable | none | none | none | none |
| Expected RX opcode | not compared (length gate only) | not compared (length gate only) | UNKNOWN (0x24 comparison unsettled) | 0x02 (frame[2]==2) |
| Expected RX length | 18 | 18 | UNKNOWN (36 or element 0x24) | no length gate; mask read needs >=7 |
| Parser function | notify closure @0x8e2430 | notify closure @0x8b0654 | _RainbowTestState::analysisData | _RainbowTestState::analysisData |
| Parser address | 0x8e2408 | 0x8b0654 | 0x91d130 | 0xacfa64 |
| Key-ID byte/field | mask bytes [3..6] BE, bit==id | mask bytes [3..6] BE, bit==id | mask bytes [3..6] BE, bit==id | mask bytes [3..6] BE, bit==id |
| Press/release representation | absolute mask, edge vs previous snapshot | absolute mask, edge vs previous snapshot | absolute mask, edge vs previous snapshot | absolute mask, edge vs previous snapshot |
| First event special handling | none found | none found | none found | none found (the D2 echo is dropped by the opcode gate) |
| Exit/cleanup behavior | dispose: cancel subscription, then D2 disable if connected | same | same | same (Dart listener + D2 disable) |
| Confidence | PROVEN STATIC | PROVEN STATIC | STRONG EVIDENCE (one UNKNOWN gate) | PROVEN STATIC |

No cell is blank: anything not recovered is written `UNKNOWN`. Grades per build: see `d2-static-reconstruction.md` §25 and `d2-evidence-index.json`.

## Structural takeaway

- the D2 toggle itself is unchanged since 2.22 (same two frames, same characteristics);
- the parser gate hardened: length-only → opcode-aware;
- subscription ownership moved from the page (2.22-2.24) to the connection (4.0.8);
- no build contains a precondition our harness omits.
