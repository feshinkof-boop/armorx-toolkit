# Prepared key-ID session — ids 2, 5, 9, 21, 22, 31, 32, 33

**Prepared, NOT started.** Per the C0 brief: the button prompts are not raised in this task. This
document is the ready-to-run plan for the next physical session.

## Why these ids

26 ids are PROVEN LIVE (`results/final/key-map-confidence.{json,md}`): 0, 1, 3, 4, 6, 7, 8, 10, 11, 12,
13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28, 29, 30. Eight remain:

| id | standing | what the session must establish |
|---|---|---|
| 2 | never observed | whether any physical control sets it |
| 5 | never observed | same |
| 9 | **proven negative as a digital bit** (requested in 4 windows + 3 dedicated retries; analog byte `[16]` never moved) | whether RT is analog-only, or absent, on this unit |
| 21 | never observed | whether any control sets it |
| 22 | never observed | same |
| 31 | never observed | same |
| 32 | never observed | same |
| 33 | never observed | same |

## Method (unchanged from the validated contract)

**ONE button per popup. The operator presses that same button twice, clicks DONE. Analyse, then move to
the next button.** Never batch several buttons into one window — the batch windows are exactly how the
historical name↔bit misassignments arose, and `define.dart`'s key getters are offset by one bit, so
order assumptions must not be used to name a bit.

Per popup:

- title `ArmorX D2 Key-ID <n>`; message names exactly one control;
- buttons `DONE` / `CANCEL / STOP`; click = ACK; one sound, no repeats, no chat;
- D2 enable before the prompt; **D2 disable after every popup**; keep notifications armed throughout;
- analyse only 18-byte `A5 12 02` frames with a valid checksum, and only bits that appear **alone**
  (single-bit masks) count as evidence for that control.

Run it with the case machinery already in place (`automation/scripts/d2-differential.py variant
--case C1` semantics: no pre-clear — the pre-clear is now known not to matter either way, so no
pre-clear keeps the wire shorter) or the existing button-capture harness with one press group per
popup.

## RT (id 9) needs one extra step

The digital question is already answered (negative), so the RT popup must also capture the **analog**
channel: hold RT fully and read `frame[17]` (`RT` analog byte). Decision rule:

- analog byte moves and no bit appears → **RT is analog-only** on this unit (record as such);
- neither moves → **RT is not wired to this unit's report frame** (record as such).

Do not merge these two outcomes: they are different findings.

## Ordering

Cheapest and least ambiguous first: 9 (RT, with the analog check), then 5, 2, 21, 22, 31, 32, 33.
After each popup, decode and record before raising the next one. Stop immediately if a popup is
cancelled (`OPERATOR_CANCELLED`), send D2 OFF, disconnect, and report.

## Prerequisites already satisfied

- D2 receiving is proven working with a press (C0, 2026-09-28: 167 frames, 4 transitions on bit 0).
- The operator dialog supports `CANCEL / STOP` and one-shot ACK recording.
- The config baseline is intact (`CONFIG_BASELINE_MATCH`, `bdef9c61…`) and this session needs **no
  configuration writes** — it is D2 enable/press/disable only.
