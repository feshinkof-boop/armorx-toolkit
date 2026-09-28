# The two 'normalized-state producers' (V41, static)

`0x1e0a5f2` and `0x1e0a656` are **not** input parsers and **not** state copiers. They are 30- and 32-byte
`tbb` switch tables that **inject pre-canned synthetic axis constants** into the candidate buffer.

| | producer A `0x1e0a5f2` | producer B `0x1e0a656` |
|---|---|---|
| selector | `(r0 & 0xf) - 1`, 10 entries | `((r0 & 0xf0) - 0x10) >> 4`, 10 entries |
| writes | `+0x04`, `+0x06` (axes #1/#2) | `+0x08`, `+0x0a` (axes #3/#4) |
| LT `+0x0c` | **no** | **no** |
| RT `+0x0d` | **no** | **no** |

Canned values: `0x0000`, `0x8000` (axis centre), `0x7fff` (full scale) and s16 pairs `+/-0x2582`
(`0x5a7e` = +0x2582, `0xa582` = -0x2582). Those are recognisable stick-test positions.

## Consequences

1. The "source mux" reading of the selector is **wrong**: the nibbles are *mode/pattern ids*, and what gets
   written are constants, not copies of any source structure.
2. This **removes the previous best hypothesis for RT**. The mux does not touch LT/RT, so it explains
   nothing about the live RT observation.

## Where RT stands now

On this path the candidate's `+0x0c`/`+0x0d` are seeded from **packed bits 8 and 9** (`0x1e0da54`,
`0x1e0da62`) - i.e. digital by construction - and no other store in `0x1e0ac14`-`0x1e0f154` touches them.

If that is the whole story, the 14-byte D2 frame carries **digital** LT/RT, and the analogue 0..255 values
observed live in bytes [15]/[16] would have to come from another report path. That would be a significant
correction to the live field map - it is **not proven**, and is not stated as fact. The remaining buffer
references (`0x1e0e29c`, `0x1e0e2bc`, `0x1e0e3c6`, `0x1e0e3d6`, next to the second report variant) are the
place to check.
