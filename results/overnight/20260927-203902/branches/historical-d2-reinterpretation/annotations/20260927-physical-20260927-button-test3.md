> **DATED CORRECTION ANNOTATION — 2026-09-27 (overnight shift 20260927-203902)**
>
> This file is an ADDENDUM to the run named below. It does **not** edit or replace the original
> report; append it to that run's directory by hand.
> Correction driven by the corrected model: **D2 input is EVENT-DRIVEN — zero idle frames != failure**
> (proof: `results/overnight/20260927-203902/official-timeline-verification.json`).

# Correction — `physical-20260927-button-test3`

**Applies to:** `results/experiments/physical-20260927-button-test3/session.jsonl`

## Was a button pressed?

**No.** `session.jsonl` shows: connect → identity reads → `0B` `a5040bb4` → **`D2 test ON`
`a505d2017d` @20:31:08** → `RUNNING_READ_ONLY_TEST / button_capture` → stream ends, no frames.
No operator request existed at this time: the earliest entry in `results/runtime/operator-actions.jsonl`
is `operator_ui_test` at **17:42**, and the earliest physical request in `physical-actions.jsonl` is
`power_on_armorx` at **16:55** — both *after* 16:30/16:31 EDT (20:30Z). So no press was asked for and
none occurred.

## Corrected conceptual verdict

**`NO_IDLE_FRAMES_OBSERVED`** (no press made). No original verdict text exists to contradict, but
this dir is a D2 "no frames" run and must not be counted as a stream failure.

**Grade:** PROVEN (operator ledger empty at that time). Mislabelled: **YES (unlabelled — no verdict recorded)**.
