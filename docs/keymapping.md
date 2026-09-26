# ARMORX Pro key mapping

This page documents the current `mapKeys[32]` model for the **BIGBIG WON ARMORX Pro** and its Xbox-style controller controls.

## Proven IDs

| ID | ARMORX Pro / Xbox control | Status |
|---:|---|---|
| 0 | A | PROVEN |
| 1 | B | PROVEN |
| 2 | Empty / Clear | PROVEN |
| 3 | X | PROVEN |
| 4 | Y | PROVEN |
| 6 | LB | PROVEN |
| 7 | RB | PROVEN |
| 8 | LT | PROVEN |
| 9 | RT | PROVEN |
| 10 | View / Select | PROVEN |
| 11 | Menu / Start | PROVEN |
| 12 | Guide / Xbox / Mode | PROVEN LIVE |
| 13 | L3 / Left Stick Click | PROVEN |
| 14 | R3 / Right Stick Click | PROVEN |
| 16 | D-pad Up | PROVEN |
| 17 | D-pad Down | PROVEN |
| 18 | D-pad Left | PROVEN |
| 19 | D-pad Right | PROVEN |
| 23 | M1 | PROVEN |
| 24 | M2 | PROVEN |
| 25 | M3 | PROVEN |
| 26 | M4 | PROVEN |

## Mapping direction

The serialized direction is:

```text
mapKeys[source_button_id] = target_button_id
```

Example:

```text
mapKeys[23] = 0
M1 -> A
```

The `mapKeys` array occupies bytes **112..143** in the 144-byte configuration.

## Protocol-space corroboration

The low IDs closely match the common Linux/Xbox gamepad ordering:

```text
0  A / South
1  B / East
2  C / clear slot in this mapping model
3  X / North
4  Y / West
5  Z
6  TL  -> LB
7  TR  -> RB
8  TL2 -> LT
9  TR2 -> RT
10 Select -> View
11 Start  -> Menu
12 Mode   -> Guide
13 ThumbL -> L3
14 ThumbR -> R3
```

ID 12 is now **PROVEN LIVE** as Guide / Xbox / Mode. A controlled M1 remap to target ID 12 was written and read back successfully on firmware 2741, and the operator observed the Guide/Xbox/Mode action.

## Unresolved slots

These IDs remain intentionally unresolved or version-specific:

```text
5, 15, 20, 21, 22, 27, 28, 29, 30, 31
```

ID 15 is a **provisional Share/Capture/Screenshot candidate** only. In the 2026-09-26 autonomous sweep, the structured observation chooser was set to Guide/Mode while the operator note said `screenshot`; because those two observations conflict, ID 15 is not promoted to a stable symbolic mapping yet.

The remaining IDs 5, 20, 21, 22, 27, 28, 29, 30, and 31 produced no visible action in that attached-controller M1 sweep. That result does **not** prove they are unused or reserved.

## Contribution target

If you can identify one unresolved ID, please submit a controlled test showing:

1. the source button;
2. the target button;
3. the exact config diff;
4. firmware version;
5. repeatability.
