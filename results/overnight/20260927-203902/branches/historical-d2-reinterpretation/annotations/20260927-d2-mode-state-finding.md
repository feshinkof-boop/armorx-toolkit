> **DATED CORRECTION ANNOTATION — 2026-09-27 (overnight shift 20260927-203902)**
>
> This file is an ADDENDUM to the run named below. It does **not** edit or replace the original
> report; append it to that run's directory by hand.
> Correction driven by the corrected model: **D2 input is EVENT-DRIVEN — zero idle frames != failure**
> (proof: `results/overnight/20260927-203902/official-timeline-verification.json`).

# Correction — `results/final/d2-mode-state-finding.md` (+ `results/runtime/d2-stream-probe.json`)

**Applies to:** `results/final/d2-mode-state-finding.md`, `results/runtime/d2-stream-probe.json`,
and the three unpress rows of `button-tests.jsonl` / the "proven path @17:50" row.

## Was a button pressed?

**No, in every row this finding rests on.**
- `d2-stream-probe.json` (variants A–E, 17:50–18:25): no operator press was requested; the probe
  only sent D2 enables/disables and listened.
- "proven `armorx_real.py d2` @ 17:50": unattended, no press requested.
- 17:47:24 / 17:48:28 rows: a press **was** claimed (RT), but that is the RT case — see the separate
  annotation `20260927-physical-20260927-174445-buttons.md`. RT has no digital key id.

## What is wrong with the original verdict

The title and body assert: *"D2 test mode: acknowledged but no longer streaming (measured, not
guessed)"* and conclude the unit entered a state where *"it answers the command but never streams"*.
That inference was drawn entirely from **zero frames while nothing was pressed** — exactly the
signature the event-driven model predicts for a **healthy** link. `NO_STREAM_IN_ANY_VARIANT` is not
evidence of a broken stream.

The counter-evidence the finding did **not** weigh: the same day, the same harness, on the same unit,
captured **3293 `A5 12 02` frames** (26 key ids) — `results/experiments/physical-20260927-170844-d2/`.
The hardware was demonstrably capable of streaming. (Note: that earlier run *did* include operator
tapping, so its frames were event-driven too — it is not proof of an idle stream either, and the
finding's "3295 frames over 900 s, continuous stream" phrasing over-states it.)

## Corrected conceptual verdict

**`NO_IDLE_FRAMES_OBSERVED`** — not `D2_STREAM_FAILED`, and not a durable device-state finding.

The two "open hypotheses" (console-side gating, unit-side mode latch) are **withdrawn as motivated
by this evidence**: with no press, silence is expected, so nothing here points to a latch.
(Console-gating was in any case already contradicted by the operator's `no_console` answer.)

**Grade:** PROVEN (no press). Mislabelled: **YES** — this is the single most load-bearing
mislabelled document, because `real-armorx-master-report.md` §6 cites it to explain why the
two-press button capture "could not be applied".
