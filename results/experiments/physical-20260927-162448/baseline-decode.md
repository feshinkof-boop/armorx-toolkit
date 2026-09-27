# Real ARMOR-X Pro baseline decode

- length: 144
- sha256: `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`
- stored CRC (bytes 0-1 BE): 0x2C40
- declared length (bytes 2-3 BE): 0x0090 (144)
- CRC-16/MODBUS over bytes 2..end verifies: **True**

| offset | size | endian | field | raw | value | evidence |
|---|---|---|---|---|---|---|
| 0-1 | 2 | raw | header (semantics UNKNOWN) | `2c 40` | `2c 40` | STRONG EVIDENCE |
| 2-3 | 2 | BE | len = total config length | `00 90` | `00 90` | PROVEN STATIC |
| 4-4 | 1 | byte | UNKNOWN (global static written) | `33` | `51` | STRONG EVIDENCE |
| 5-5 | 1 | byte | motorMax | `ff` | `255` | PROVEN STATIC |
| 6-8 | 3 | 3 bytes | UNKNOWN | `00 00 00` | `00 00 00` | UNKNOWN |
| 9-9 | 1 | byte | triggerMode | `00` | `0` | PROVEN STATIC |
| 10-11 | 2 | 2 bytes | triggerLeftDeadzone (center,side) | `00 00` | `00 00` | PROVEN STATIC |
| 12-13 | 2 | 2 bytes | triggerRightDeadzone | `00 00` | `00 00` | PROVEN STATIC |
| 14-14 | 1 | byte | joystickCircleLimit | `00` | `0` | PROVEN STATIC |
| 15-15 | 1 | byte | stickTurn | `00` | `0` | PROVEN STATIC |
| 16-17 | 2 | 2 bytes | stickLeftDeadzone | `00 00` | `00 00` | PROVEN STATIC |
| 18-19 | 2 | 2 bytes | stickRightDeadzone | `00 00` | `00 00` | PROVEN STATIC |
| 20-25 | 6 | 3 x Axis2 | stickLeftCurve | `01 00 1e 1e 46 46` | `01 00 1e 1e 46 46` | PROVEN STATIC |
| 26-27 | 2 | 2 bytes | UNKNOWN | `00 00` | `00 00` | UNKNOWN |
| 28-33 | 6 | StickCurve | stickRightCurve | `01 00 1e 1e 46 46` | `01 00 1e 1e 46 46` | PROVEN STATIC |
| 34-35 | 2 | 2 bytes | UNKNOWN | `00 00` | `00 00` | UNKNOWN |
| 36-36 | 1 | byte | sensorMode | `02` | `2` | PROVEN STATIC |
| 37-37 | 1 | byte | sensorDir | `00` | `0` | PROVEN STATIC |
| 38-38 | 1 | byte | sensorRightKey0 | `02` | `2` | PROVEN STATIC |
| 39-39 | 1 | byte | sensorRightKey1 | `02` | `2` | PROVEN STATIC |
| 40-43 | 4 | u32 BE | sensorRightKeyBit | `00 00 00 00` | `0` | PROVEN STATIC |
| 44-49 | 6 | StickCurve | sensorRightCurve0 | `00 0a 3c 3c 2a 00` | `00 0a 3c 3c 2a 00` | PROVEN STATIC |
| 50-51 | 2 | - | UNKNOWN | `00 00` | `00 00` | UNKNOWN |
| 52-57 | 6 | StickCurve | sensorRightCurve1 | `00 0a 3c 3c 2a 00` | `00 0a 3c 3c 2a 00` | PROVEN STATIC |
| 58-59 | 2 | - | UNKNOWN | `00 00` | `00 00` | UNKNOWN |
| 60-65 | 6 | StickCurve | sensorRightCurve2 | `00 0a 3c 3c 2a 00` | `00 0a 3c 3c 2a 00` | PROVEN STATIC |
| 66-67 | 2 | - | UNKNOWN | `00 00` | `00 00` | UNKNOWN |
| 68-68 | 1 | byte | sensorMin | `00` | `0` | PROVEN STATIC |
| 69-72 | 4 | u32 BE | sensorSwitch | `00 00 00 00` | `0` | PROVEN STATIC |
| 73-75 | 3 | - | UNKNOWN | `00 00 00` | `00 00 00` | UNKNOWN |
| 76-76 | 1 | byte | UNKNOWN (global static written) - turboSpeedIdx (name unproven) | `00` | `0` | STRONG EVIDENCE |
| 77-80 | 4 | u32 BE | turboKey | `00 00 00 00` | `0` | PROVEN STATIC |
| 81-93 | 13 | - | UNKNOWN for 0x90 (written only in the 0xF0 branch) | `00 00 00 00 00 00 00 00 00 00 00 00 00` | `00 00 00 00 00 00 00 00 00 00 00 00 00` | UNKNOWN |
| 94-111 | 18 | - | UNKNOWN | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | UNKNOWN |

## mapKeys[0..31] (config bytes 112..143)

| src id | src label | target id | abs offset | raw byte |
|---|---|---|---|---|
| 0 | A | 0 | 112 | 0x00 |
| 1 | B | 1 | 113 | 0x01 |
| 2 | Empty | 2 | 114 | 0x02 |
| 3 | X | 3 | 115 | 0x03 |
| 4 | Y | 4 | 116 | 0x04 |
| 5 | UNKNOWN | 5 | 117 | 0x05 |
| 6 | LB | 6 | 118 | 0x06 |
| 7 | RB | 7 | 119 | 0x07 |
| 8 | LT | 8 | 120 | 0x08 |
| 9 | RT | 9 | 121 | 0x09 |
| 10 | View | 10 | 122 | 0x0A |
| 11 | Menu | 11 | 123 | 0x0B |
| 12 | UNKNOWN | 12 | 124 | 0x0C |
| 13 | L3 | 13 | 125 | 0x0D |
| 14 | R3 | 14 | 126 | 0x0E |
| 15 | Capture | 15 | 127 | 0x0F |
| 16 | D-pad Up | 16 | 128 | 0x10 |
| 17 | D-pad Down | 17 | 129 | 0x11 |
| 18 | D-pad Left | 18 | 130 | 0x12 |
| 19 | D-pad Right | 19 | 131 | 0x13 |
| 20 | UNKNOWN | 20 | 132 | 0x14 |
| 21 | UNKNOWN | 21 | 133 | 0x15 |
| 22 | UNKNOWN | 22 | 134 | 0x16 |
| 23 | UNKNOWN | 1 | 135 | 0x01 |
| 24 | UNKNOWN | 13 | 136 | 0x0D |
| 25 | UNKNOWN | 25 | 137 | 0x19 |
| 26 | UNKNOWN | 26 | 138 | 0x1A |
| 27 | M5 | 27 | 139 | 0x1B |
| 28 | M6 | 28 | 140 | 0x1C |
| 29 | M7 | 29 | 141 | 0x1D |
| 30 | UNKNOWN | 30 | 142 | 0x1E |
| 31 | UNKNOWN | 31 | 143 | 0x1F |

identity mapping (target == source for all 32): **False**
mapKeys[15] at absolute offset 127: {"source_id": 15, "source_label": "Capture", "target_id": 15, "absolute_offset": 127, "raw_byte": "0x0F"}
