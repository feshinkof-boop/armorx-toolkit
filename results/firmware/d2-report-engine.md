# ArmorX D2 report engine (V41, static)

The `A5 12 02` frame is built at **`0x1e0db0c`** with opcode `0x02` and a 14-byte payload: frame length
`0x12` = 14 + 4. A second `0x02` variant with a 28-byte payload is built at `0x1e0db5e`.

## Proof of the payload layout

`0x1e07464` serialises the payload field by field - this is why the live field map is what it is,
rather than an assumption:

| payload offset | width | serialisation | live frame bytes |
|---|---|---|---|
| 0x00 | 4 | `rev8` u32 | [3..6] digital mask |
| 0x04 | 2 | `rev8` s16 | [7..8] |
| 0x06 | 2 | `rev8` s16 | [9..10] |
| 0x08 | 2 | `rev8` s16 | [11..12] |
| 0x0a | 2 | `rev8` s16 | [13..14] |
| 0x0e | LT/RT | via `0x1e07444` | [15],[16] |

## Send gate

* `0x1e0dae6` reads `b[r15+0x10]`; if zero the 14-byte report is not built at all.
* `0x1e0dae0` sets a repeat counter `b[r15+0x3a] = 0x64` (100).
* `0x1e0db1c`..`0x1e0db2c` decrement it and jump back to re-send while it is nonzero.
* `0x1e0db38` requires `b[r15+0x11] != 0` for the 28-byte variant.

The D2 handler `0x1e08d24` writes `b[r8+0x10]`, or `b[r8+0x11]` when the selector is `0x19` - the two
flags that gate the two report variants.

## Still open

* What schedules this path on digital activity (the trigger side of FW-U-026): the containing function
  `0x1e0aff2` is called from `0x1e0a9b4`, not yet traced.
