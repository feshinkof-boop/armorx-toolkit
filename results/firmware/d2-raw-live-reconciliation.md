# Raw live D2 reconciliation (V41 vs captures)

Source: `results/experiments/rt-bit9-confirmation-20260928-063300`, frames with `checksum_ok` true.

## Frame contract confirmed byte-for-byte

`a5120200000201fa92fd60fa98fe1100ff45`
-> `A5 12 02` | mask `0x00000201` (bits 0 and 9) | axes `fa92fd60fa98fe11` | `[15] LT = 0x00` |
`[16] RT = 0xff` | `[17] = 0x45` = sum8 of the preceding 17 bytes.

## Distributions

| window | frames | frames with bit 9 | distinct byte15 | byte16 values |
|---|---|---|---|---|
| W0 A only | 228 | 0 | 1 | ['0'] |
| W1 RT held + A | 263 | 184 | 1 | ['0', '17', '255', '27', '96'] |
| W2 A only | 283 | 0 | 1 | ['0'] |

## Verdict

The historical field map is **CORRECT, and now PROVEN LIVE**: byte 15 is LT, byte 16 is RT. In W1 the RT
byte takes `0, 17, 27, 96, 255`, so the D2 payload's `+0x0c`/`+0x0d` carry **analogue** values on the live
streaming path.

Combined with the dominance result (the r13 copy precedes the compare gate and both builders), the
packed-bit seed arm would overwrite `+0x0d` with 0/1 whenever it is taken. The live frames show 0..255,
therefore **the seed arm is not taken on the normal streaming path**: the live bytes come from the
`state+0x1d4` record copy at `0x1e0cd2e`. The two mechanisms are mode-dependent, not a precedence chain
that always executes.

**Still open:** why an RT-only move does not by itself trip the change gate. Static says a change to
`+0x0d` should trip it; the live evidence says it does not. That contradiction is narrowed but not closed.
