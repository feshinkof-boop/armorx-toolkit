# D2 frame contract (static)

## Enable

Raw bytes: `A5 05 D2 01 7D`
Length: 5
Checksum: `0x7D` = Sum8(`A5 05 D2 01`) & 0xFF = `0x17D & 0xFF` — a hard-coded literal on this path
(`getCheckSum` is not called here)
Builder: `BluetoothModel::testModeSwitch` @ `0xabaef4` (4.0.8); `testModeSwitch` @ `0x91e380` (2.24),
@ `0x8b1d68` (2.23), @ `0x8e3a88`/`0x8e3be4` (2.22)
Callers: `_RainbowTestState::initState` callback (4.0.8 @ `0xacf8cc`; 2.24 @ `0x91cf94`;
2.23 @ `0x8b0504`; 2.22 @ `0x8e1e94`), **not awaited**
Observed build(s): all four (identical bytes)
Blutter note: the list is built from **tagged Smis** (`0x14a, 0xa, 0x1a4, 0x2, 0xfa`); halve each to
get the byte.

## Disable

Raw bytes: `A5 05 D2 00 7C`
Length: 5
Checksum: `0x7C` = Sum8(`A5 05 D2 00`) & 0xFF
Builder: same function, mirror branch (4.0.8 @ `0xabaf9c`; 2.24 `testModeSwitch1` @ `0x93371c`;
2.23 @ `0x881a78`; 2.22 in `dispose` @ `0x95a864`)
Callers: `dispose`, **gated on the connection state being connected** (2.23 @ `0x90dea1`;
4.0.8 via the Provider-resolved `BluetoothModel`)
Observed build(s): all four

## RX event

Expected bytes / shape: 18-byte frame, header `0xA5`, length byte `0x12`, opcode `0x02`
Minimum length: **18 in 2.22/2.23** (gate `frame[1] == 18`); **no length gate in 4.0.8** — the
opcode gate is `frame[2] == 0x02` and the mask read consumes indices 3..6, so ≥7 bytes are
required for a mask. 2.24: UNKNOWN (its gate compares against `0x24`).
Opcode position: index 2 (`0x02`)
Key-ID position: indices 3..6 as one **big-endian u32**; `bit index == key id`
Press/release field: none — the mask is absolute state (bit set = down)
Other fields: `[7..14]` four signed int16 BE axes; `[15]` LT analog; `[16]` RT analog;
`[17]` trailer, never read by the page
Checksum handling: **not validated by the app on this path** (the app's checksum helper is used for
outgoing frames only)
Length validation: 2.22/2.23 yes (==18); 4.0.8 no explicit length gate
Malformed-frame behavior: 4.0.8 jumps to the alternate branch @ `0xad0c80` (UNKNOWN); 2.22/2.23
silently ignore anything whose length byte is not 18

## Unknown fields

- `[15]` / `[16]`: our live capture showed LT moving byte `[15]` with the trigger (`0x83 → 0xFF`),
  but the **app does not read `[15..16]` at all in the decoded page** → the two facts are kept
  separate: live observation PROVEN LIVE, app interpretation **UNKNOWN**.
- `[17]`: UNKNOWN (never read; our captures carry a checksum there).
- 4.0.8 CCDD write value: UNKNOWN.
