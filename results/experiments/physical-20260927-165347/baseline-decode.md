# ARMOR-X baseline decode

- length: 144
- sha256: `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`
- stored CRC (bytes 0-1 BE): 0x2C40
- declared length (bytes 2-3 BE): 0x0090 (144)
- CRC-16/MODBUS over bytes 2..end verifies: **True**

| offset | size | field | raw | value | evidence |
|---|---|---|---|---|---|
| 0-1 | 2 | header (semantics UNKNOWN) | `2c 40` | `0x2c40` | STRONG EVIDENCE |
| 2-3 | 2 | len = total config length (BE) | `00 90` | `0x0090` | PROVEN STATIC |
| 4-4 | 1 | UNKNOWN (global static written) | `33` | `51` | STRONG EVIDENCE |
| 5-5 | 1 | motorMax | `ff` | `255` | PROVEN STATIC |
| 6-8 | 3 | UNKNOWN | `00 00 00` | `0x000000` | UNKNOWN |
| 9-9 | 1 | triggerMode | `00` | `0` | PROVEN STATIC |
| 10-11 | 2 | triggerLeftDeadzone (center,side) | `00 00` | `0x0000` | PROVEN STATIC |
| 12-13 | 2 | triggerRightDeadzone | `00 00` | `0x0000` | PROVEN STATIC |
| 14-14 | 1 | joystickCircleLimit | `00` | `0` | PROVEN STATIC |
| 15-15 | 1 | stickTurn | `00` | `0` | PROVEN STATIC |
| 16-17 | 2 | stickLeftDeadzone | `00 00` | `0x0000` | PROVEN STATIC |
| 18-19 | 2 | stickRightDeadzone | `00 00` | `0x0000` | PROVEN STATIC |
| 20-25 | 6 | stickLeftCurve | `01 00 1e 1e 46 46` | `0x01001e1e4646` | PROVEN STATIC |
| 26-27 | 2 | UNKNOWN | `00 00` | `0x0000` | UNKNOWN |
| 28-33 | 6 | stickRightCurve | `01 00 1e 1e 46 46` | `0x01001e1e4646` | PROVEN STATIC |
| 34-35 | 2 | UNKNOWN | `00 00` | `0x0000` | UNKNOWN |
| 36-36 | 1 | sensorMode | `02` | `2` | PROVEN STATIC |
| 37-37 | 1 | sensorDir | `00` | `0` | PROVEN STATIC |
| 38-38 | 1 | sensorRightKey0 | `02` | `2` | PROVEN STATIC |
| 39-39 | 1 | sensorRightKey1 | `02` | `2` | PROVEN STATIC |
| 40-43 | 4 | sensorRightKeyBit (u32 BE) | `00 00 00 00` | `0x00000000` | PROVEN STATIC |
| 44-49 | 6 | sensorRightCurve0 | `00 0a 3c 3c 2a 00` | `0x000a3c3c2a00` | PROVEN STATIC |
| 50-51 | 2 | UNKNOWN | `00 00` | `0x0000` | UNKNOWN |
| 52-57 | 6 | sensorRightCurve1 | `00 0a 3c 3c 2a 00` | `0x000a3c3c2a00` | PROVEN STATIC |
| 58-59 | 2 | UNKNOWN | `00 00` | `0x0000` | UNKNOWN |
| 60-65 | 6 | sensorRightCurve2 | `00 0a 3c 3c 2a 00` | `0x000a3c3c2a00` | PROVEN STATIC |
| 66-67 | 2 | UNKNOWN | `00 00` | `0x0000` | UNKNOWN |
| 68-68 | 1 | sensorMin | `00` | `0` | PROVEN STATIC |
| 69-72 | 4 | sensorSwitch (u32 BE) | `00 00 00 00` | `0x00000000` | PROVEN STATIC |
| 73-75 | 3 | UNKNOWN | `00 00 00` | `0x000000` | UNKNOWN |
| 76-76 | 1 | UNKNOWN (global static written) | `00` | `0` | STRONG EVIDENCE |
| 77-80 | 4 | turboKey (u32 BE) | `00 00 00 00` | `0x00000000` | PROVEN STATIC |
| 81-93 | 13 | UNKNOWN for 0x90 (written only in the 0xF0 branch) | `00 00 00 00 00 00 00 00 00 00 00 00 00` | `0x00000000000000000000000000` | UNKNOWN |
| 94-111 | 18 | UNKNOWN | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `0x000000000000000000000000000000000000` | UNKNOWN |

## mapKeys[0..31] (config bytes 112..143)

| src id | src label | target id | abs offset | raw byte | key mask (bit==ID) |
|---|---|---|---|---|---|
| 0 | A | 0 | 112 | 0x00 | 0x1 |
| 1 | B | 1 | 113 | 0x01 | 0x2 |
| 2 | Empty | 2 | 114 | 0x02 | 0x4 |
| 3 | X | 3 | 115 | 0x03 | 0x8 |
| 4 | Y | 4 | 116 | 0x04 | 0x10 |
| 5 | UNKNOWN | 5 | 117 | 0x05 | 0x20 |
| 6 | LB | 6 | 118 | 0x06 | 0x40 |
| 7 | RB | 7 | 119 | 0x07 | 0x80 |
| 8 | LT | 8 | 120 | 0x08 | 0x100 |
| 9 | RT | 9 | 121 | 0x09 | 0x200 |
| 10 | View | 10 | 122 | 0x0A | 0x400 |
| 11 | Menu | 11 | 123 | 0x0B | 0x800 |
| 12 | UNKNOWN | 12 | 124 | 0x0C | 0x1000 |
| 13 | L3 | 13 | 125 | 0x0D | 0x2000 |
| 14 | R3 | 14 | 126 | 0x0E | 0x4000 |
| 15 | Capture | 15 | 127 | 0x0F | 0x8000 |
| 16 | D-pad Up | 16 | 128 | 0x10 | 0x10000 |
| 17 | D-pad Down | 17 | 129 | 0x11 | 0x20000 |
| 18 | D-pad Left | 18 | 130 | 0x12 | 0x40000 |
| 19 | D-pad Right | 19 | 131 | 0x13 | 0x80000 |
| 20 | UNKNOWN | 20 | 132 | 0x14 | 0x100000 |
| 21 | UNKNOWN | 21 | 133 | 0x15 | 0x200000 |
| 22 | UNKNOWN | 22 | 134 | 0x16 | 0x400000 |
| 23 | UNKNOWN | 1 | 135 | 0x01 | 0x800000 |
| 24 | UNKNOWN | 13 | 136 | 0x0D | 0x1000000 |
| 25 | UNKNOWN | 25 | 137 | 0x19 | 0x2000000 |
| 26 | UNKNOWN | 26 | 138 | 0x1A | 0x4000000 |
| 27 | M5 | 27 | 139 | 0x1B | 0x8000000 |
| 28 | M6 | 28 | 140 | 0x1C | 0x10000000 |
| 29 | M7 | 29 | 141 | 0x1D | 0x20000000 |
| 30 | UNKNOWN | 30 | 142 | 0x1E | 0x40000000 |
| 31 | UNKNOWN | 31 | 143 | 0x1F | 0x80000000 |

identity mapping (target == source for all 32): **False**
mapKeys[15]: {"source_id": 15, "source_label": "Capture", "target_id": 15, "absolute_offset": 127, "raw_byte": "0x0F", "key_mask": "0x8000"}

key-mask rule examples (bit == ID): {"6": "0x40", "15": "0x8000", "16": "0x10000"}
