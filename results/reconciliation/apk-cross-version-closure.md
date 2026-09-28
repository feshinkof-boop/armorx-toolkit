# APK cross-version closure: 2.22.0901 / 2.23.0609 / 2.24.0919 / 4.0.8 (Part C)

Static only. This consolidates the per-version findings that already exist in this tree into one
matrix, de-duplicates them against the DPI/motion/lighting and D8 branches, and lists what remains
genuinely unresolved rather than re-deriving what is already proven.

Trees used (each verified to exist; see the provenance caveat at the end):
`static/blutter/2.22.0901/blutter_out`, `/armorx/re/blutter_out` (2.23-era, Dart 2.19.6),
`/armorx/re/v224/blutter_out` (2.24), `/armorx-re/mygt408/blutter_out` (4.0.8).

## Command-family presence by version

| family / opcode | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|---|---|---|---|
| `0B` version query | yes | yes | yes | yes |
| `EF` device UUID | yes | yes | yes | yes |
| `E2` firmware read | **NOT PRESENT** | not stated | not stated | yes (`readFirmware` @ `0x8b6860`) |
| `D4` input model | yes | yes | yes | yes (`getInputModel` @ `0xa84258`) |
| `D6` configuration read | yes | yes | yes | yes (`getDeviceConfig` @ `0x80dbfc`) |
| `D2` test-mode switch | yes (`testModeSwitch` `0x8e3a88`) | yes | yes (`0x8e3a88`/`0x8e1efc`) | yes (`0xabaef4`) |
| `FC` DPI | **NOT PRESENT** | present | present (+`F6`) | present (+`F6`) |
| `AB` motion/gyro | **NOT PRESENT** | **NOT PRESENT** | **NOT PRESENT** | present (`AB 07 05 25`, `writeMotionDpiConfig` @ `0x946158`) |
| `D8` macro / `A4` fragmentation | present | present | present | present (commit byte `0x05`, ordinal at offset 3) |
| lighting `0x70` | `writeLightConfig` only | present | present (+`0x0D` logo) | present + R3 writers (`A5 10 70`, `A5 04 70`) |
| key mask rule | bit == id, no +1 | same | same | same (`keyL1=0x40` = bit 6 = LB) |

## Parser gates (Button Test)

| version | gate | evidence |
|---|---|---|
| 2.22.0901 | `untag(data[1]) == 0x12` | `0x8e2450` (`sbfx` untag then compare) |
| 2.23.0609 | `untag(data[1]) == 0x12` | `0x8b06e8` - **read byte-level this pass**: `LoadInt32Instr` (`sbfx x1, x0, #1, #0x1f`) then `cmp x1, #0x12` |
| 2.24.0919 | `data[1] == Smi(18)` (`cmp w0, #0x24`) | `0x91d168`; `0x24 = 18 << 1` |
| 4.0.8 | `frame[2] == 0x02` | the live parser contract; consistent with all 155 captured frames |

Note the two kinds of check are the same test at different optimisation levels: where the compiler kept
the value tagged, the compare is against `0x24`; where it untagged first, against `0x12`. The constant
is 18 either way, matching the 18-byte report.

## What remains unresolved

1. **The selector→DPI table** (not in the binary; server-side presets) - see
   `results/final/protocol-closure-fc-dpi-motion-lighting.md`.
2. **The DPI reply parser** - never located in any build.
3. **RGB byte order** - no anchor in any of the four builds.
4. **The lighting field layout** (`0x70` sub-commands `0x05`/`0x3F` are known by constant only).
5. **Which build introduced `E2`** - 2.22 lacks it (proven), and the 2.23/2.24 trees were not
   exhaustively searched for `readFirmware` in this pass; it is a cheap grep left for the next pass
   rather than asserted now.
6. **OTA / firmware-download entry points** - see the JieLi/firmware document; nothing here claims
   an update path exists.

## Provenance caveat (must travel with this table)

Tree -> version labels are inferred from directory naming plus address distinctness, not from a
recorded APK hash per tree: `static/blutter/2.22.0901` is self-labelled, `/armorx/re/v224` is the 2.24
generation, `/armorx/re/blutter_out` is the remaining 2.2x build used for the 2.23 claims, and
`mygt408` is 4.0.8. A future pass should hash the APK each tree was built from and record it here; the
matrix above should be re-checked if any label turns out wrong. Flagged rather than hidden.
