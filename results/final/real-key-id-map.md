# Real ARMOR-X Pro key-ID map (canonical)

Generated 2026-09-28T06:09:10.954413. Rule: **bit == id**; mask = bytes [3..6] big-endian u32.

## PROVEN LIVE (26 ids)

| id | mask bit | physical control | request group | frames |
|---|---|---|---|---|
| 0 | [6] bit 0 | A | press_group_A | 14 |
| 1 | [6] bit 1 | B | press_group_A | 13 |
| 3 | [6] bit 3 | X | press_group_A | 14 |
| 4 | [6] bit 4 | Y | press_group_A | 14 |
| 6 | [6] bit 6 | LB | press_group_B | 38 |
| 7 | [6] bit 7 | RB | press_group_B | 35 |
| 8 | [5] bit 0 | LT | press_group_B | 13 |
| 10 | [5] bit 2 | View/Select | press_group_C | 29 |
| 11 | [5] bit 3 | Menu/Start | press_group_C | 22 |
| 12 | [5] bit 4 | Guide/Xbox | press_group_E | 26 |
| 13 | [5] bit 5 | L3 | press_group_C | 14 |
| 14 | [5] bit 6 | R3 | press_group_C | 18 |
| 15 | [5] bit 7 | Capture/Share | press_group_E | 28 |
| 16 | [4] bit 0 | D-pad Up | press_group_D | 24 |
| 17 | [4] bit 1 | D-pad Down | press_group_D | 24 |
| 18 | [4] bit 2 | D-pad Left | press_group_D | 19 |
| 19 | [4] bit 3 | D-pad Right | press_group_D | 18 |
| 20 | [4] bit 4 | UNATTRIBUTED - one frame with id 20 appeared in this window; it cannot be tied to RT with confidence | press_group_F | 19 |
| 23 | [4] bit 7 | M1 | press_group_E | 22 |
| 24 | [3] bit 0 | M2 | press_group_E | 28 |
| 25 | [3] bit 1 | M3 | press_group_E | 24 |
| 26 | [3] bit 2 | M4 | press_group_E | 21 |
| 27 | [3] bit 3 | M5 | press_group_F | 19 |
| 28 | [3] bit 4 | M6 | press_group_F | 17 |
| 29 | [3] bit 5 | M7 | press_group_F | 24 |
| 30 | [3] bit 6 | extra button (as pressed by the operator) | press_group_F | 13 |

## Unresolved ids

| id | classification |
|---|---|
| 2 | `UNOBSERVED_RESERVED_OR_UNUSED` |
| 5 | `UNOBSERVED_RESERVED_OR_UNUSED` |
| 9 | `PROVEN_NEGATIVE` |
| 21 | `UNOBSERVED_RESERVED_OR_UNUSED` |
| 22 | `UNOBSERVED_RESERVED_OR_UNUSED` |
| 31 | `UNOBSERVED_RESERVED_OR_UNUSED` |
| 32 | `UNOBSERVED_RESERVED_OR_UNUSED` |
| 33 | `UNOBSERVED_RESERVED_OR_UNUSED` |

### id 9 (RT)

PROVEN NEGATIVE as a digital bit. Requested in press_group_B/D/E/F, three dedicated retries, and again on 2026-09-28 with two FULL pulls in a popup open 16.8 s (ACKed 06:05:49): zero frames of any kind arrived. Because the device emits nothing while only RT moves, the analog byte [16] is unsamplable, so RT_ANALOG_ONLY is neither confirmed nor excluded. No analog claim is made.

### ids 2, 5, 21, 22, 31, 32, 33

UNOBSERVED_RESERVED_OR_UNUSED: no physical control that was ever requested maps to these bits, and no label for them exists in any of the four builds' inventories (the app's label set is A B X Y LB RB LT RT L3 R3 Menu Select Start Capture Up Down Left Right M1-M7 NIL + keyboard keys + ZL/ZR). The 32-slot mapKeys space is larger than the number of controls this unit reports.

## 2026-09-28 closure session

One control remained untested (RT); it and a stick probe both produced zero frames.

- **RT** -> `RT_NO_REPORT_OBSERVED` (0 valid frames)
- **L stick** -> `STICK_NO_REPORT_OBSERVED` (0 valid frames)
- ~~R stick~~ skipped: the L-stick probe already proved analog-axis-only changes produce no frames, so the outcome was determined

## Sources

- live_experiment: `results/experiments/physical-20260927-170844-d2/real-key-id-map.json`
- consolidated: `results/final/key-map-confidence.json`
- closure_session: `results/experiments/key-id-closure-20260928-060134/RESULT.md`
