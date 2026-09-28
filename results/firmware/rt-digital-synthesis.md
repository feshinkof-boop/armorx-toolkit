# RT digital synthesis (2026-09-28)

The live report has no digital RT bit, yet the D2 frame carries mask bit 9 (`0x00000200`). This block is
where that bit becomes a byte.

`0x1e0cfc0-0x1e0d02c` toggles a previous-state byte, takes the changed-bit set `r0 = r5 & r4`, and:

* rising edge - ORs the bits into the candidate mask at `sp+1080` (candidate `+0x00`)
* changed bit `0x100` - `b[sp+1092] = 0xff` (candidate `+0x0c`, LT)
* changed bit `0x200` - `b[sp+1093] = 0xff` (candidate `+0x0d`, RT)
* falling edge - clears those bytes to `0x00` and ANDs the bits out of the mask

`candidate+0x0c`/`+0x0d` are exactly the bytes the `state+0x1d4` analogue copy writes, so each trigger
byte has two writers: the analogue copy and this edge synthesis. That reconciles the live data - in the W1
capture RT byte 16 took 0, 17, 27, 96 and **255**; the intermediates are analogue, the 255 is this block
firing on the edge.

`0x200` is tested in exactly two places in the whole firmware, both here. A descriptor byte
(`[r15+0x1b0]+0x78`) equal to 8 zeroes the LT byte for that device class.

Narrowed, not closed: how the changed-bit set is formed is untraced.
