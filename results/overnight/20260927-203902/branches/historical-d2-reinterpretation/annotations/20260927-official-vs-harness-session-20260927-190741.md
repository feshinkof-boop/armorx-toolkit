> **DATED CORRECTION ANNOTATION — 2026-09-27 (overnight shift 20260927-203902)**
>
> This file is an ADDENDUM to the run named below. It does **not** edit or replace the original
> report; append it to that run's directory by hand.
> Correction driven by the corrected model: **D2 input is EVENT-DRIVEN — zero idle frames != failure**
> (proof: `results/overnight/20260927-203902/official-timeline-verification.json`).

# Correction — `official-vs-harness-session-20260927-190741`

**Applies to:** `results/experiments/official-vs-harness-session-20260927-190741/` (`README.md`, `verdict.md`, `official-vs-harness-diff.md`)

## Was a button pressed?

- **Harness leg:** **No.** The README records a 10 s passive idle after the D2 enable
  (`D2 ENABLE @28.521 → 10 s idle → D2 OFF @38.531`), no press requested or made.
- **Official leg:** **Yes** — `armorx_official_a_twice` (ack `done` 19:46:25), A pressed twice.

## What is wrong with the original verdict

The classification **`OFFICIAL_WORKS_HARNESS_SILENT`** is *factually* right but the label
**"HARNESS_SILENT"** is misleading in the same way as the others: the harness had **no press in its
window**, so "silent" is the expected healthy outcome, not a defect. The verdict body already
concedes this ("the stream is event-driven … the harness's historical '0 idle frames' was therefore
never evidence of failure by itself") — so this document is the **least wrong** of the set; the
legend/label is what needs correcting, not the analysis.

## Corrected conceptual verdict

- Harness leg → **`NO_IDLE_FRAMES_OBSERVED`** (label corrected; analysis unchanged).
- Official leg → **`BUTTON_FRAMES_OBSERVED`** (155 frames; correct as-is).

`D2-U-007` should be restated as **"why does the harness receive nothing *when a button is pressed*"**
— the harness has simply never had a confirmed press inside a D2 capture window, so **D2-U-007 is
unproven-to-exist** as stated; the open question is whether a press on the harness link ever
produces frames (it did, once: `physical-20260927-170844-d2`).

**Grade:** PROVEN (no press, harness leg). Mislabelled: **partially / label only**.
