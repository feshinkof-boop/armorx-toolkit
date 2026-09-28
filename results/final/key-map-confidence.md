# Key-id confidence table (ids 0..33)

**Indexing note: 15 ids differ between the wire bit and the app's
`moojiang/define.dart` getters - the getters sit exactly one bit above the wire for the same
name** (keyUp=bit17 vs wire Up=16, keyM1=24 vs wire M1=23, keyCapture=16 vs wire Capture=15,
keyRThumb=15 vs wire R3=14). This is NOT a contradiction of the wire naming: the wire mapping
is corroborated twice over - by the `key mask rule` recorded for all four builds
(`keyL1=0x40` = bit 6 = LB, `keyCapture=0x8000` = bit 15, `keyUp=0x10000` = bit 16) and by the
live single-bit frames themselves. The define.dart constants are therefore a separate,
offset enumeration, and must not be used to name a wire bit. Per-id detail is in
`name_conflicts` in the JSON.

Mask rule: `mask_bytes[3..6] big-endian u32; bit index == key id (no +1)`

Counts: **26 PROVEN LIVE**, 8 UNKNOWN, 0 unobserved.

| id | name | name confidence | grade | live frames | static constant | notes |
|---|---|---|---|---|---|---|
| 0 | A | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 14 | — | single-bit mask inside press_group_A window (2026-09-27T17:09:23-04:00 .. 2026-09-27T17:10:15-04:00) |
| 1 | B | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 13 | — | single-bit mask inside press_group_A window (2026-09-27T17:09:23-04:00 .. 2026-09-27T17:10:15-04:00) |
| 2 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |
| 3 | X | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 14 | — | single-bit mask inside press_group_A window (2026-09-27T17:09:23-04:00 .. 2026-09-27T17:10:15-04:00) |
| 4 | Y | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 14 | — | single-bit mask inside press_group_A window (2026-09-27T17:09:23-04:00 .. 2026-09-27T17:10:15-04:00) |
| 5 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |
| 6 | LB | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 57 | — | single-bit mask inside press_group_B window (2026-09-27T17:10:49-04:00 .. 2026-09-27T17:11:34-04:00) |
| 7 | RB | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 46 | keyL1 | single-bit mask inside press_group_B window (2026-09-27T17:10:49-04:00 .. 2026-09-27T17:11:34-04:00) |
| 8 | LT | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 13 | keyR1 | single-bit mask inside press_group_B window (2026-09-27T17:10:49-04:00 .. 2026-09-27T17:11:34-04:00) |
| 9 | — | UNKNOWN | UNKNOWN | 0 | keyL2 | RT: requested in press_group_B/D/E/F and three dedicated retries - NEVER appeared |
| 10 | View/Select | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 29 | keyR2 | single-bit mask inside press_group_C window (2026-09-27T17:11:53-04:00 .. 2026-09-27T17:12:27-04:00) |
| 11 | Menu/Start | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 44 | keySelect | single-bit mask inside press_group_C window (2026-09-27T17:11:53-04:00 .. 2026-09-27T17:12:27-04:00) |
| 12 | Guide/Xbox | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 26 | keyStart | single-bit mask inside press_group_E window (2026-09-27T17:13:26-04:00 .. 2026-09-27T17:14:27-04:00); no static label found in the builds we hold |
| 13 | L3 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 14 | — | single-bit mask inside press_group_C window (2026-09-27T17:11:53-04:00 .. 2026-09-27T17:12:27-04:00) |
| 14 | R3 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 18 | — | single-bit mask inside press_group_C window (2026-09-27T17:11:53-04:00 .. 2026-09-27T17:12:27-04:00) |
| 15 | Capture/Share | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 28 | keyRThumb | single-bit mask inside press_group_E window (2026-09-27T17:13:26-04:00 .. 2026-09-27T17:14:27-04:00) |
| 16 | D-pad Up | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 66 | keyCapture | single-bit mask inside press_group_D window (2026-09-27T17:12:38-04:00 .. 2026-09-27T17:13:08-04:00) |
| 17 | D-pad Down | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 68 | keyUp | single-bit mask inside press_group_D window (2026-09-27T17:12:38-04:00 .. 2026-09-27T17:13:08-04:00) |
| 18 | D-pad Left | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 72 | keyDown | single-bit mask inside press_group_D window (2026-09-27T17:12:38-04:00 .. 2026-09-27T17:13:08-04:00) |
| 19 | D-pad Right | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 66 | keyLeft | single-bit mask inside press_group_D window (2026-09-27T17:12:38-04:00 .. 2026-09-27T17:13:08-04:00) |
| 20 | UNATTRIBUTED | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 19 | keyRight | single-bit mask inside press_group_F window (2026-09-27T17:14:50-04:00 .. 2026-09-27T17:15:38-04:00); no static label found in the builds we hold |
| 21 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |
| 22 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |
| 23 | M1 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 22 | — | single-bit mask inside press_group_E window (2026-09-27T17:13:26-04:00 .. 2026-09-27T17:14:27-04:00); no static label found in the builds we hold |
| 24 | M2 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 28 | keyM1 | single-bit mask inside press_group_E window (2026-09-27T17:13:26-04:00 .. 2026-09-27T17:14:27-04:00); no static label found in the builds we hold |
| 25 | M3 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 24 | keyM2 | single-bit mask inside press_group_E window (2026-09-27T17:13:26-04:00 .. 2026-09-27T17:14:27-04:00); no static label found in the builds we hold |
| 26 | M4 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 21 | keyM3 | single-bit mask inside press_group_E window (2026-09-27T17:13:26-04:00 .. 2026-09-27T17:14:27-04:00); no static label found in the builds we hold |
| 27 | M5 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 19 | keyM4 | single-bit mask inside press_group_F window (2026-09-27T17:14:50-04:00 .. 2026-09-27T17:15:38-04:00) |
| 28 | M6 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 17 | — | single-bit mask inside press_group_F window (2026-09-27T17:14:50-04:00 .. 2026-09-27T17:15:38-04:00) |
| 29 | M7 | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 24 | — | single-bit mask inside press_group_F window (2026-09-27T17:14:50-04:00 .. 2026-09-27T17:15:38-04:00) |
| 30 | extra button (as pressed by the operator) | PROVEN LIVE + corroborated by the mask rule in all four builds | PROVEN LIVE | 13 | — | single-bit mask inside press_group_F window (2026-09-27T17:14:50-04:00 .. 2026-09-27T17:15:38-04:00); no static label found in the builds we hold |
| 31 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |
| 32 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |
| 33 | — | UNKNOWN | UNKNOWN | 0 | — | no physical button produced this bit in any capture we hold |

## How an id is proven

A bit counts as proven for a button only when a frame carrying exactly that single bit
appears inside the window in which the operator was asked to press that button. Positional
pairing is deliberately not used, and the configuration `mapKeys` region is a source->target
remap, so it is never used to name a bit.

## Residuals

- **RT (id 9)**: requested in four windows plus three dedicated retries, never appeared, and
  its analog byte [16] never left zero. On this unit RT has no digital key id - a proven
  negative worth stating as such rather than as a gap.
- **ids 2, 5, 21, 22, 31, 32, 33**: no physical button produced these bits in any capture we
  hold. They are UNKNOWN, and the static label inventories above do not resolve them either.
- **id 20**: one live bit was seen in the group-F window but cannot be attributed to RT, so it
  stays unattributed.
