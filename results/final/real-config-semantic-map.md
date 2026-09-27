# ARMOR-X Pro config: raw bytes vs normalized semantics

Baseline `sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` (144 bytes).
Raw region `mapKeys[0..31]` = absolute offsets 112–143:

| idx | src id | src label (live if known) | abs offset | raw byte | target id | identity? |
|---|---|---|---|---|---|---|
| 0 | 0 | A | 112 | `0x00` | 0 | yes |
| 1 | 1 | B | 113 | `0x01` | 1 | yes |
| 2 | 2 | Empty | 114 | `0x02` | 2 | yes |
| 3 | 3 | X | 115 | `0x03` | 3 | yes |
| 4 | 4 | Y | 116 | `0x04` | 4 | yes |
| 5 | 5 | UNKNOWN | 117 | `0x05` | 5 | yes |
| 6 | 6 | LB | 118 | `0x06` | 6 | yes |
| 7 | 7 | RB | 119 | `0x07` | 7 | yes |
| 8 | 8 | LT | 120 | `0x08` | 8 | yes |
| 9 | 9 | RT | 121 | `0x09` | 9 | yes |
| 10 | 10 | View/Select | 122 | `0x0A` | 10 | yes |
| 11 | 11 | Menu/Start | 123 | `0x0B` | 11 | yes |
| 12 | 12 | Guide/Xbox | 124 | `0x0C` | 12 | yes |
| 13 | 13 | L3 | 125 | `0x0D` | 13 | yes |
| 14 | 14 | R3 | 126 | `0x0E` | 14 | yes |
| 15 | 15 | Capture/Share | 127 | `0x0F` | 15 | yes |
| 16 | 16 | D-pad Up | 128 | `0x10` | 16 | yes |
| 17 | 17 | D-pad Down | 129 | `0x11` | 17 | yes |
| 18 | 18 | D-pad Left | 130 | `0x12` | 18 | yes |
| 19 | 19 | D-pad Right | 131 | `0x13` | 19 | yes |
| 20 | 20 | UNATTRIBUTED - one frame with id 20 appeared in this window; it cannot be tied to RT with confidence | 132 | `0x14` | 20 | yes |
| 21 | 21 | UNKNOWN | 133 | `0x15` | 21 | yes |
| 22 | 22 | UNKNOWN | 134 | `0x16` | 22 | yes |
| 23 | 23 | M1 | 135 | `0x01` | 1 | NO |
| 24 | 24 | M2 | 136 | `0x0D` | 13 | NO |
| 25 | 25 | M3 | 137 | `0x19` | 25 | yes |
| 26 | 26 | M4 | 138 | `0x1A` | 26 | yes |
| 27 | 27 | M5 | 139 | `0x1B` | 27 | yes |
| 28 | 28 | M6 | 140 | `0x1C` | 28 | yes |
| 29 | 29 | M7 | 141 | `0x1D` | 29 | yes |
| 30 | 30 | extra button (as pressed by the operator) | 142 | `0x1E` | 30 | yes |
| 31 | 31 | UNKNOWN | 143 | `0x1F` | 31 | yes |

Notes:

- every source slot currently maps to its own id (identity mapping) - the unit is on stock mapping
- source id 2 is labelled 'Empty' and source ids 5, 30, 31 have no live-verified physical button
- the ID-15 experiment set abs offset 127 (source slot 15) to 0x02 = the NIL/empty target

Policy: the **raw** image is authoritative and is the only thing written back byte-exactly;
the normalized view exists so a future `.axprofile`/`.axmacro` format is not built around an
opaque 144-byte blob.
