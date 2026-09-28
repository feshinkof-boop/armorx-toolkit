# D2-U-007 — the harness is NOT silent: reconciliation of the "harness silence" finding

**Date:** 2026-09-27/28 (overnight autonomous shift)
**Supersedes the implication of:** `OFFICIAL_WORKS_HARNESS_SILENT`
**Corrected classification:** `HARNESS_STREAMS_UNDER_PRESS__DIFFERENTIAL_WINDOWS_WERE_NOT_PRESS-MATCHED`

## The finding

The Linux/bleak harness received **3,292 valid button frames** from the real ARMOR-X Pro on
2026-09-27, across **26 distinct key ids**, every frame 18 bytes with a valid checksum.

Source (raw session record, re-derived — not prose):
`results/experiments/physical-20260927-170844-d2/session.jsonl`
Audit: `automation/scripts/harness-streaming-audit.py` → `results/reconciliation/harness-streaming-170844.json`

| property | value |
|---|---|
| records | 3,315 (3 tx, 3,295 rx) |
| button frames (`A5 12 02`) | **3,292** |
| frame length | 18 bytes (all 3,292) |
| checksums | all valid |
| zero-mask frames | 2,503 |
| non-zero-mask frames | 789 |
| key ids seen | 26 — `0,1,3,4,6,7,8,10,11,12,13,14,15,16,17,18,19,20,23,24,25,26,27,28,29,30` |
| window | `21:08:59.498Z` → `21:15:26.255Z` |
| control plane | `0B` (21:08:57.031) → **D2 ON** (21:08:57.120) → D2 OFF (21:23:57.835) |
| D2 pre-clear before the enable | **none** |

So the harness streams normally, and the configuration that streams is `0B → D2 ON` — i.e. **C1**
(no pre-clear) has already been demonstrated working, with a real operator pressing keys.

## Why the previous conclusion was wrong

`OFFICIAL_WORKS_HARNESS_SILENT` compared two windows that were **not press-matched**:

| window | press requested? | frames |
|---|---|---|
| official Android half (19:43–19:47) | **yes** — operator action `armorx_official_a_twice`, ACKed 19:46:25 | 155 valid frames |
| harness half (19:07) | **no press action exists anywhere in the log for that window**; the only operator actions were power-on popups | 0 frames |
| harness run 17:08 (with press windows) | **yes** — `press_group_A…F`, ACKed 17:10:15 → 17:15:38 | **3,292 frames** |

The operator-action log (`results/runtime/operator-actions.jsonl`) contains **no press request** for
the differential windows: the action ids there are power-on / setup / shutdown popups. Every
`press_group_*` request in the project belongs to the 17:09–17:15 windows.

Because D2 input is event-driven, a window with no press is **expected** to produce zero frames in
every configuration. A comparison of "pressed" vs "not pressed" therefore measures the experiment, not
the device. The old classification is a design artifact.

## What this does to the four refuted hypotheses

The `d2-live-differential` run (18:46) tested write-with-response, CCCD renewal, and disable/re-enable,
observing `0 valid frames` in all four variants (`C0`, `A`, `B`, `C`). Its own operator actions were
`armorx_power_on_d2diff` and `armorx_power_on_for_case_c` — **power-on popups only**. No press was
requested during any variant.

Consequence, stated precisely: those four variants are **not evidence** about write type, CCCD state or
link re-use, because an idle window cannot distinguish "this configuration is silent" from "nothing was
pressed" — and under the corrected model all four were expected to be silent. Their `REFUTED` labels
are **vacuous**, not wrong-in-detail. They remain valid only as "these variants did not spontaneously
stream while idle", which was never in question.

## What is left of D2-U-007

D2-U-007 asked why the harness appeared silent. The appearance is now explained. The narrowed remainder:

1. **The pre-clear is now the single untested variable.** Every harness window that streamed had no
   pre-clear; every window with a pre-clear (the differential run) had no press and therefore proves
   nothing. `C0` (pre-clear + a real press) has never been run. This is the first physical action for
   the next session, and it is a one-variable experiment.
2. **The pre-D2 read burst is not required** — the streaming run sent only `0B` before D2. The
   cross-version branch independently found the burst to be generic application initialisation, not
   D2-specific. Both point the same way.
3. Connection-interval differences remain unproven as causal, and the app never requests an interval
   profile (see the connection-parameters branch), so intervals are stack-driven and are the weakest
   remaining candidate.

## Grading

| claim | grade |
|---|---|
| the harness received 3,292 valid button frames | **PROVEN LIVE** (raw record re-derived) |
| those frames carried 26 distinct key ids | **PROVEN LIVE** |
| the streaming configuration had no D2 pre-clear | **PROVEN LIVE** |
| the differential windows were not press-matched | **PROVEN** (operator-action log) |
| `OFFICIAL_WORKS_HARNESS_SILENT` implies a device difference | **CONTRADICTED** |
| the pre-clear is the cause of the remaining asymmetry | **UNKNOWN** — untested with a press, which is exactly what `C0` now tests |

## Bookkeeping note

This document does not rewrite the historical reports. The original classification stays in place in
the artifacts that produced it; this is the dated correction, and the ledger and master report point
here.
