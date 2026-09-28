# ARMOR-X command dispatcher (from V41 firmware, static)

Function `0x1e08772` .. `0x1e0948c`  (1027 instructions examined).

| opcode | compare at | test | handler | family / known meaning | evidence |
|---|---|---|---|---|---|
| 0x02 | 0x1e08864 | != | 0x1e08868 | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x05 | 0x1e08e5e | != | 0x1e08e62 | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x0d | 0x1e091de | != | 0x1e091e2 | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x19 | 0x1e08826 | == | 0x1e08d32 | UNKNOWN | PROVEN STATIC (opcode compared in the frame handler) |
| 0x1b | 0x1e0882a | != | 0x1e0882e | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x2f | 0x1e08d1a | == | 0x1e0914a | unknown family seen in dispatch chain | PROVEN STATIC (opcode compared in the frame handler) |
| 0x70 | 0x1e0893a | == | 0x1e093e4 | unknown family seen in dispatch chain | PROVEN STATIC (opcode compared in the frame handler) |
| 0xd2 | 0x1e08d1e | != | 0x1e08d24 | D2 input-report enable/disable (live: A5 05 D2 01 7D / A5 05 D2 00 7C) | STRONG EVIDENCE (fell through the != test) |
| 0xd4 | 0x1e087c8 | != | 0x1e087ce | D4 query (live: A5 04 D4 7D -> A5 07 D4 11 01 00 92) | STRONG EVIDENCE (fell through the != test) |
| 0xd4 | 0x1e0893e | != | 0x1e08944 | D4 query (live: A5 04 D4 7D -> A5 07 D4 11 01 00 92) | STRONG EVIDENCE (fell through the != test) |
| 0xd7 | 0x1e08854 | == | 0x1e08a68 | D7 configuration write | PROVEN STATIC (opcode compared in the frame handler) |
| 0xef | 0x1e08e8c | != | 0x1e08e92 | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0xf7 | 0x1e0885a | != | 0x1e08860 | F7 stick step-length / step accuracy | STRONG EVIDENCE (fell through the != test) |
| 0xf8 | 0x1e08982 | == | 0x1e08b86 | F8 brightness-compensation config (app: A5 04 F8) | PROVEN STATIC (opcode compared in the frame handler) |
| 0xf9 | 0x1e087c2 | == | 0x1e08912 | unknown family seen in dispatch chain | PROVEN STATIC (opcode compared in the frame handler) |
| 0xfa | 0x1e08988 | != | 0x1e0898e | unknown family seen in dispatch chain | STRONG EVIDENCE (fell through the != test) |

Range gates (opcodes above these leave the chain):
- `0x1e0881c` ifs (r1 > 0xd6) goto 0x2c <fw_start+0x884E : 1e0884e >
- `0x1e08822` ifs (r1 > 0x6f) goto 0x114 <fw_start+0x893A : 1e0893a >
- `0x1e0884e` ifs (r1 > 0xf7) goto 0x12e <fw_start+0x8982 : 1e08982 >
- `0x1e089b6` ifs (r1 > 0x2e) goto 0x3a <fw_start+0x89F4 : 1e089f4 >
- `0x1e089be` if (r2 > 0x10) goto 0x49c <fw_start+0x8E5E : 1e08e5e >
- `0x1e089fe` if (r0 > 0x4) goto 0x48a <fw_start+0x8E8C : 1e08e8c >
- `0x1e08ba8` if (r0 > 0x1) goto 0x1ba <fw_start+0x8D66 : 1e08d66 >
- `0x1e08e72` if (r0 > 0x5) goto 0x52c <fw_start+0x93A2 : 1e093a2 >
- `0x1e08ff6` if (r0 > 0xa) goto 0x370 <fw_start+0x936A : 1e0936a >
- `0x1e09028` if (r0 > 0xe) goto 0x1c8 <fw_start+0x91F4 : 1e091f4 >
- `0x1e0905a` if (r0 > 0x5) goto 0x19a <fw_start+0x91F8 : 1e091f8 >
- `0x1e092be` if (r1 > 0xdc) goto 0x15a <fw_start+0x941C : 1e0941c >
- `0x1e092cc` if (r1 > 0x3) goto 0x1c <fw_start+0x92EC : 1e092ec >
- `0x1e09462` if (r1 > 0x1) goto 0x2 <fw_start+0x9468 : 1e09468 >
- `0x1e09470` if (r1 > 0x1) goto 0x8 <fw_start+0x947C : 1e0947c >
