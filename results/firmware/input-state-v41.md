# ArmorX V41 input-state struct `0x4ecc` (static)

## The LT/RT exclusion hypothesis is REFUTED

`0x1e07444` is not a byte load - it byte-swaps **three** s16 fields (`h[r0+0]`, `h[r0+2]`, `h[r0+4]`).
So the serializer's calls at `+0x0e` and `+0x14` transform **six extra s16 fields**, not LT and RT.

**LT = `+0x0c` and RT = `+0x0d`** - two single bytes needing no swap - and both sit **inside** the 14
bytes the change detector compares (`0x00..0x0d`).

## Struct map (28 bytes, base `0x4ecc`)

| offset | width | semantic | in the compared 14? |
|---|---|---|---|
| 0x00 | 4 | digital mask (u32) | yes |
| 0x04 | 2 | axis s16 #1 | yes |
| 0x06 | 2 | axis s16 #2 | yes |
| 0x08 | 2 | axis s16 #3 | yes |
| 0x0a | 2 | axis s16 #4 | yes |
| 0x0c | 1 | **LT** | yes |
| 0x0d | 1 | **RT** | yes |
| 0x0e | 2 | s16 #5 (swapped, not sent in the 14B frame) | no |
| 0x10 | 2 | s16 #6 | no |
| 0x12 | 2 | s16 #7 | no |
| 0x14 | 2 | s16 #8 | no |
| 0x16 | 2 | s16 #9 | no |
| 0x18 | 2 | s16 #10 | no |
| 0x1a | 2 | untouched tail | no |

4 + 8 + 2 + 12 + 2 = 28 exactly, which also explains the 28-byte report variant's payload length.

## RT: still open, one candidate eliminated

Because `+0x0d` is inside the compared range, the only surviving explanation is that RT analogue
movement does not update `+0x0d` (perhaps it holds the digital/threshold state). Writers of
`0x4e40 + 0x8c + 0x0d` are the next provable step. RT is **not** reported as explained.
