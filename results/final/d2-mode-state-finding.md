# D2 test mode: acknowledged but no longer streaming (measured, not guessed)

**Status: BLOCKING the button-ID track. Recorded as a device-state finding, not a button finding.**

## The observation

| When | Path | 0B link | D2 ON ack | Status frames captured |
|---|---|---|---|---|
| 17:08:44 (earlier pass) | `armorx_real.py d2` (proven) | `a5 05 0b 30 e5` | `a5 05 d2 01 7d` | **3295** over 900 s, continuous stream |
| 17:47:24 | hand-rolled session | `a5 05 0b 30 e5` | `a5 05 d2 01 7d` | **0** |
| 17:48:28 | hand-rolled session | `a5 05 0b 30 e5` | `a5 05 d2 01 7d` | **0** |
| 17:50 | **proven** `armorx_real.py d2` | `a5 05 0b 30 e5` | `a5 05 d2 01 7d` | **1** (the ack echo itself) |

The last row is the important one: the *proven* capture path produced zero stream frames,
so this is **not** a bug in the new button tooling. Identity reads were normal in the same
connections (`2A24=ZJ-XT`, `2A26=2741`, `2A19=0x41` = 65%).

## Measured variations (`results/runtime/d2-stream-probe.json`)

Probe `automation/scripts/probe-d2.py`, run twice (before and after a full power cycle the
operator performed through the GUI):

| variant | frames (before power cycle) | frames (after power cycle) |
|---|---|---|
| A. plain D2 ON | 0 | 0 |
| B. D2 OFF → pause → D2 ON | 0 | 0 |
| C. D2 ON twice in a row | 1 | 1 |
| D. 0B then D2 ON | 2 | 1 |
| E. 10 s listen | 0 | 0 |
| verdict | `NO_STREAM_IN_ANY_VARIANT` | `NO_STREAM_IN_ANY_VARIANT` |

The handful of "frames" in C/D are the command echo of D2 ON itself, not a status stream:
a real D2 stream is ~20 frames/second (3295 frames in 900 s).

## What is ruled out

- **Not the frames**: byte-identical `D2 ON = A5 05 D2 01 7D`, identical 0B health reply.
- **Not the tooling**: the proven harness path shows the same silence.
- **Not identity/config**: 2A24/2A26 read normally; the config was restored to the immutable
  baseline (`bdef9c61…`) and re-verified `BASELINE_LIVE` before these attempts.
- **Not a plain power state**: an operator-performed power cycle did not restore the stream.
- **Not the link**: 0B answered after the operator's window ended in both button attempts
  (`link_alive_after_capture = a5 05 0b 30 e5`), so the unit was awake and connected while
  the presses produced nothing.

## What remains open (highest-value hypotheses, ordered)

1. **Console-side gating.** At 17:08 the operator was actively using the unit in the room
   with its host console powered; today the console state is unknown. If the controller only
   reports input events while it has a live console link, D2 silence is expected.
2. **Unit-side mode latch.** The earlier capture ended with an unacknowledged `D2 OFF`
   (link dropped during teardown) — a latched test mode could leave the reporting path in a
   state that answers the command but never streams. A config-level or mode-level reset
   would need evidence before being attempted; no such write was made.

## Consequence for the plan

Button-ID capture cannot proceed until the stream is back, because "no frames" would be
unfalsifiable evidence about any button. The tooling is ready and already refuses to blame
a button in this situation: `button-capture-harness.py` returns
`DEVICE_NOT_STREAMING` (exit 2) without touching the button map, and `button-capture.py`
records `d2_streaming` / `link_alive_after_capture` separately from the press analysis.
