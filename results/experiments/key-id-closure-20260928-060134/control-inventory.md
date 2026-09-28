# Control inventory - key-ID closure session

Generated 2026-09-28T06:01:42.832704. Derived from the real request log cross-referenced with the proven-live map.

## Distinct physical controls the operator was actually asked to press

LB, RB, LT, RT, View, Menu, L3, R3, D-pad Up, D-pad Down, D-pad Left, D-pad Right, Capture, Guide, M1, M2, M3, M4, M5, M6, M7, other, A, B, X, Y

## Already PROVEN LIVE (26 ids) - NOT requested again

| id | control | request group | corroborating frames |
|---|---|---|---|
| 0 | A | press_group_A | 14 |
| 1 | B | press_group_A | 13 |
| 3 | X | press_group_A | 14 |
| 4 | Y | press_group_A | 14 |
| 6 | LB | press_group_B | 38 |
| 7 | RB | press_group_B | 35 |
| 8 | LT | press_group_B | 13 |
| 10 | View/Select | press_group_C | 29 |
| 11 | Menu/Start | press_group_C | 22 |
| 12 | Guide/Xbox | press_group_E | 26 |
| 13 | L3 | press_group_C | 14 |
| 14 | R3 | press_group_C | 18 |
| 15 | Capture/Share | press_group_E | 28 |
| 16 | D-pad Up | press_group_D | 24 |
| 17 | D-pad Down | press_group_D | 24 |
| 18 | D-pad Left | press_group_D | 19 |
| 19 | D-pad Right | press_group_D | 18 |
| 20 | UNATTRIBUTED - one frame with id 20 appeared in this window; it cannot be tied to RT with confidence | press_group_F | 19 |
| 23 | M1 | press_group_E | 22 |
| 24 | M2 | press_group_E | 28 |
| 25 | M3 | press_group_E | 24 |
| 26 | M4 | press_group_E | 21 |
| 27 | M5 | press_group_F | 19 |
| 28 | M6 | press_group_F | 17 |
| 29 | M7 | press_group_F | 24 |
| 30 | extra button (as pressed by the operator) | press_group_F | 13 |

## PHYSICAL CONTROLS NOT YET PROVEN - the session target list

- **RT**
- **L stick (analog, full deflection)**
- **R stick (analog, full deflection)**

## Unresolved numeric ids

`2, 5, 9, 21, 22, 31, 32, 33`

Of the unresolved ids, only id 9 has a candidate physical control (RT, requested 4x and never observed). The rest correspond to no requested control and may be unused, reserved, mode-dependent, analog-only, or not emitted by this unit - no name is assumed.

## App label inventory (4.0.8)

A B X Y LB RB LT RT L3 R3 Menu Select Start Capture Up Down Left Right M1..M7 NIL, plus keyboard keys and ZL/ZR (Switch-mode names). No M8+ and no Turbo label exists.

## Plan

1. RT (digital mask + analog channel)
2. L stick (analog, full deflection)
3. R stick (analog, full deflection)

One control per popup. No batch windows, no order-based attribution.

