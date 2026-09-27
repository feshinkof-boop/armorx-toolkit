# Real ARMOR-X Pro key-ID map (live D2 capture, claim-verified)

Frame `opcode 0x02`, 18 bytes. Key mask = bytes `[3][4][5][6]` with **bit == source id**
(`[6]`→ids 0-7, `[5]`→8-15, `[4]`→16-23, `[3]`→24-31). Every row below is corroborated
by a capture frame with exactly that bit set, inside the window of the request that
asked for that button.

| id | mask | physical button (live) | static label | evidence | frames |
|---|---|---|---|---|---|
| 0 | byte[6] bit 0 = `0x01` | A | A | PROVEN LIVE | 14 |
| 1 | byte[6] bit 1 = `0x02` | B | B | PROVEN LIVE | 13 |
| 3 | byte[6] bit 3 = `0x08` | X | X | PROVEN LIVE | 14 |
| 4 | byte[6] bit 4 = `0x10` | Y | Y | PROVEN LIVE | 14 |
| 6 | byte[6] bit 6 = `0x40` | LB | LB | PROVEN LIVE | 38 |
| 7 | byte[6] bit 7 = `0x80` | RB | RB | PROVEN LIVE | 35 |
| 8 | byte[5] bit 0 = `0x01` | LT | LT | PROVEN LIVE | 13 |
| 10 | byte[5] bit 2 = `0x04` | View/Select | View | PROVEN LIVE | 29 |
| 11 | byte[5] bit 3 = `0x08` | Menu/Start | Menu | PROVEN LIVE | 22 |
| 12 | byte[5] bit 4 = `0x10` | Guide/Xbox | UNKNOWN (was) | PROVEN LIVE | 26 |
| 13 | byte[5] bit 5 = `0x20` | L3 | L3 | PROVEN LIVE | 14 |
| 14 | byte[5] bit 6 = `0x40` | R3 | R3 | PROVEN LIVE | 18 |
| 15 | byte[5] bit 7 = `0x80` | Capture/Share | Capture | PROVEN LIVE | 28 |
| 16 | byte[4] bit 0 = `0x01` | D-pad Up | D-pad Up | PROVEN LIVE | 24 |
| 17 | byte[4] bit 1 = `0x02` | D-pad Down | D-pad Down | PROVEN LIVE | 24 |
| 18 | byte[4] bit 2 = `0x04` | D-pad Left | D-pad Left | PROVEN LIVE | 19 |
| 19 | byte[4] bit 3 = `0x08` | D-pad Right | D-pad Right | PROVEN LIVE | 18 |
| 20 | byte[4] bit 4 = `0x10` | UNATTRIBUTED - one frame with id 20 appeared in this window; it cannot be tied to RT with confidence | UNKNOWN (was) | PROVEN LIVE | 19 |
| 23 | byte[4] bit 7 = `0x80` | M1 | UNKNOWN (was) | PROVEN LIVE | 22 |
| 24 | byte[3] bit 0 = `0x01` | M2 | UNKNOWN (was) | PROVEN LIVE | 28 |
| 25 | byte[3] bit 1 = `0x02` | M3 | UNKNOWN (was) | PROVEN LIVE | 24 |
| 26 | byte[3] bit 2 = `0x04` | M4 | UNKNOWN (was) | PROVEN LIVE | 21 |
| 27 | byte[3] bit 3 = `0x08` | M5 | M5 | PROVEN LIVE | 19 |
| 28 | byte[3] bit 4 = `0x10` | M6 | M6 | PROVEN LIVE | 17 |
| 29 | byte[3] bit 5 = `0x20` | M7 | M7 | PROVEN LIVE | 24 |
| 30 | byte[3] bit 6 = `0x40` | extra button (as pressed by the operator) | UNKNOWN (was) | PROVEN LIVE | 13 |

Resolved ids (26): `[0, 1, 3, 4, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28, 29, 30]`

Still UNKNOWN after this pass: `[2, 5, 9, 21, 22, 31]`


## What could not be resolved

- **RT**: requested in press_group_B, press_group_D, press_group_E and press_group_F; no frame ever carried id 9, and the RT analog byte [16] never went non-zero. Three dedicated retries failed, so the digital id of RT stays UNKNOWN.
- **ids_2_5_9_21_22_31**: no physical button produced these bits in this capture
