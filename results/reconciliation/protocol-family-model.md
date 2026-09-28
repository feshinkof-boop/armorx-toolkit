# ArmorX protocol family model

Derived from raw wire recordings and firmware code; no hardware was used to produce this pass.

## The rule

A5 and A4 are NOT independent opcode namespaces: they are the two FRAMING modes of one opcode space. A5 = single frame (payload fits the transport buffer); A4 = fragmented frame (payload too large), carrying an ordinal at frame[3]. Proven in firmware at 0x1e05dc0, which writes magic 0xA5 and flips it to 0xA4 when the payload does not fit.

## Wire evidence (raw log, no prose)

Source: `results/experiments/physical-20260927-170455-noop-d7/raw-tx-rx.log`

| direction | frames | framing |
|---|---|---|
| D7 write request | 10 | A4, ordinals 01..0a, 15 payload bytes each |
| D7 acknowledgement | 1 | A5, zero-length payload |
| D6 read request | 1 | A5, zero-length payload |
| D6 read response | 10 | A4, ordinals 01..0a |

Reassembled config: **144 bytes**, SHA-256 `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` - identical to the durable baseline.

All 24 frames in the log satisfy the frame checksum (sum8 over bytes[:-1]).

## Firmware proof

- **frame_builder** `0x1e05dc0`: 0x1e05dc4: r2 = 0xa5 ; b[r4+0] = 0xA5 (default magic); 0x1e05dcc: r2 = h[r1+0x4] (payload length) ; 0x1e05dce: r3 = capacity-4; 0x1e05dd2: ifs (r2 <= r3) goto <single-frame tail>; 0x1e05dd6: r2 = 0xa4 ; b[r4+0] = 0xA4 (does not fit -> fragmented); 0x1e05dda-0x1e05de4: nfrags = (len + 2) / (capacity - 5)
- **frame_checksum** `0x1e05dae`: 0x1e05db2: r3 = b[r0 ++= 1]; 0x1e05db6: r2 += r3; 0x1e05dbc: r0 = r2.l (u)
- **response_post** `0x1e0642c`: 0x1e06440: call 0x1e05d94 (alloc); 0x1e06452-0x1e06454: store value+opcode; 0x1e06476: call 0x1e06418 (direct send fallback)
- **send** `0x1fd3d0`: transport send (library call from 0x1e09426)
- **tx_magic_check** `0x1e064b4`: i; f;  ; (; b; [; f; r; a; m; e; +; 0; ];  ; !; =;  ; 0; x; a; 5; );  ; .; .; .;  ; ;;  ; 0; x; 1; e; 0; 6; 4; c; e; /; 0; x; 1; e; 0; 6; 4; d; 4;  ; a; c; c; e; p; t;  ; 0; x; A; 4; |; 1;  ; a; n; d;  ; 0; x; A; 4; ;;  ; 0; x; 1; e; 0; 6; 4; d; a;  ; r; e; a; d; s;  ; t; h; e;  ; o; r; d; i; n; a; l;  ; a; t;  ; f; r; a; m; e; [; 3; ]
- **parser_has_no_magic_check**: grep of the whole image finds no compare against 0xA4/0xA5/0xAB, so the RX parser 0x1e08772 accepts either framing

## Command semantics in this model

- `A5-or-A4/D6`: read the config record through the descriptor at [state+0x1b0]: the handler 0x1e0921c extracts the big-endian 16-bit LENGTH field (record bytes 2..3 = 0x0090 = 144) and the response builder streams the whole 144-byte record as A4/D6 fragments
- `A5-or-A4/D7`: write: assemble 144 bytes into the staging buffer, validate with 0x1e0566a (CRC-16/MODBUS over bytes 2..143) and write 4 x 220-byte records (0x1e09232)
- `A5-or-A4/D8`: write ONE 220-byte record, index = payload[2] (0x1e0928c)
- `A5-or-A4/D9`: read record[index] (index < 4): same length-extraction shape as D6, reply opcode 0xD9 (0x1e09346)
- `response_echo`: 0x1e09426 also emits an A5/FF response echoing the request opcode byte (0x1e09446-0x1e0944c), which is exactly the live A5/FF echo seen after A5/FC requests

## Retired leads (false positives, kept visible)

- `0x1e0aff2 / 0x1e0a944 contain protocol 0B compares` -> **RETIRED - FALSE POSITIVE**

  - 0x1e0a97c/0x1e0a98c use r0 = r9 | 1 ; if (r0 != 0xb) - that is a check for the value pair {0x0A, 0x0B}, a state/mode selector, not the opcode
  - 0x1e0a944 is a tbb dispatch on an index <= 6 selecting string pointers (0x1e2359c, 0x1e24178, 0x1e236dc)
  - 0x1e0aff2 is a 32-iteration mask-table builder operating on r15+0x124
