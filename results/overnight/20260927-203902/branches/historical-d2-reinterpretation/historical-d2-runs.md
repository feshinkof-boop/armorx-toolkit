# Historical live D2 runs — re-interpretation under the corrected EVENT-DRIVEN D2 model

**Shift:** overnight 2026-09-27T20:39:02-04:00 · **Branch:** `historical-d2-reinterpretation`
**Method:** reinterpretation pass, NOT a rewrite. No original report was edited. Every correction
below is carried in a separate dated annotation file under `annotations/`, to be appended to the
run's own directory by a human later.

## The corrected premise (authoritative, from `results/overnight/…/manifest.json`)

> **No-regression rule:** *"D2 input is EVENT-DRIVEN: zero idle frames != failure."*

Confirmed empirically this repo already contains the proof:
`results/overnight/20260927-203902/official-timeline-verification.json` — the official app on the
real unit received **0 button frames** across a **61.0 s** window in which nothing was pressed
(`VALID_EVENT_DRIVEN_SILENCE`), then **155 frames** when A was pressed twice. **Zero frames while
idle is the expected, healthy behaviour, not a fault.** Any historical verdict that read "0 frames"
as "the D2 stream is broken / D2_STREAM_FAILED" is therefore unsafe and is reinterpreted here.

Conceptual reclassification used in this document:

| old conceptual label | corrected conceptual label | when |
|---|---|---|
| D2_STREAM_FAILED / "no longer streaming" / "silent" / "CASE 6 none succeed" | **NO_IDLE_FRAMES_OBSERVED** | no button was actually pressed after D2 was enabled |
| D2_STREAM_FAILED | **PRESS_PERFORMED__BUTTON_NOT_IN_MASK** | a press occurred but the button pressed has no digital key id (so 0 frames is still expected) |
| (unaffected) | **BUTTON_FRAMES_OBSERVED** | a press occurred and frames were captured |

Grades: **PROVEN** (direct artifact) / **STRONG EVIDENCE** (multiple corroborating artifacts) /
**INFERRED** (reasoned from adjacent evidence) / **UNKNOWN**.

---

## A. Primary table — runs that actually enabled D2 (or probed it)

Run dir is relative to `results/experiments/` unless noted.

| run dir | date/time (EDT) | what was asked of the operator | press performed? | button frames observed | original verdict | corrected conceptual verdict | grade |
|---|---|---|---|---|---|---|---|
| `physical-20260927-button-test` | 16:29:23 | nothing (scan only) | no | n/a — **D2 never sent** (never connected) | (implicit: no capture) | **NOT_APPLICABLE_NO_D2** | PROVEN |
| `physical-20260927-button-test2` | 16:29:57 | nothing | no | n/a — **D2 never sent** (SESSION_START only) | (implicit: no capture) | **NOT_APPLICABLE_NO_D2** | PROVEN |
| `physical-20260927-button-test3` | 16:30:54 | **nothing** — D2 ON sent 16:31:08, session ended; no operator request existed before 16:55 | no | 0 | (no verdict recorded; a "no frames" D2 run) | **NO_IDLE_FRAMES_OBSERVED** *(MISLABELLED / unlabelled)* | PROVEN (no press — operator ledger empty at that time) |
| `physical-20260927-button-test4` | 16:38:49 | nothing | no | n/a — no ARMOR-X advert, SESSION_END | (implicit: no capture) | **NOT_APPLICABLE_NO_D2** | PROVEN |
| `physical-20260927-170844-d2` | 17:08:47–17:24:00 | `d2_window_prepare` (17:07:47: "keep awake, tap ~every 30 s") + `press_group_A…F` (17:09:23–17:14:50), **all acked DONE** | **YES — many** | **3293 `A5 12 02` frames**; 26 key ids verified | **SUCCESS** (real-key-id-map.md, PROVEN LIVE) | **BUTTON_FRAMES_OBSERVED** — this is the live-streaming proof run | **PROVEN** |
| `physical-20260927-171616-id15` | 17:16:16 | `id15_observe_capture` (17:26:06): "press Capture/Share ONCE" | **YES** (ack `done`, verdict never given; ack note = AMBIGUOUS) | n/a — **no D2 capture in this dir** (id15 was observed on a console, not via D2) | id15 probe: BASELINE_LIVE / mutant recorded INCONCLUSIVE | **NOT_APPLICABLE_NO_D2_CAPTURE** (press happened; channel was console observation) | PROVEN (request+ack) |
| `physical-20260927-174445-buttons` | 17:44:45 onward | `button_rt` (17:47:24 **and** 17:48:28): "press RT TWICE, PRESS-RELEASE, short pause, PRESS-RELEASE" — **both acked DONE** | **YES** (ack ×2) | **0** (`button-tests/rt.json`: frames_in_window 0, idle_frames 0) | **RETRY** (read as device-not-streaming) | **PRESS_PERFORMED__BUTTON_NOT_IN_MASK** — RT has no digital key id on this unit, so 0 frames is expected, **not** a stream failure | press: PROVEN; RT-not-in-mask: STRONG EVIDENCE |
| `d2-live-differential-20260927-184643` | 18:46:43–18:59 | **nothing — README states "no button presses (none was justified)"** | **no** | 0 across C0/A/B/C (claimed "the silence") | **CASE 6 — none succeed / D2-U-007 UNKNOWN** | **NO_IDLE_FRAMES_OBSERVED** *(MISLABELLED)* — the run's own success rule demanded idle frames, which do not exist under the event-driven model | PROVEN (no press — stated in the run's own README) |
| `official-vs-harness-session-20260927-190741` — **harness leg** | 19:07–19:11 | **nothing** (10 s passive idle after D2) | no | 0 | **OFFICIAL_WORKS_HARNESS_SILENT** (the "HARNESS_SILENT" half) | **NO_IDLE_FRAMES_OBSERVED** *(MISLABELLED label)* | PROVEN (no press) |
| `official-vs-harness-session-20260927-190741` — **official leg** | 19:07–19:47 | `armorx_official_a_twice` (19:46:25): press A twice | **YES** (ack `done`) | **155 frames** (29 press-mask `00000001`, 126 release-mask `00000000`); 0 in the 61 s idle window | **OFFICIAL_WORKS** | **BUTTON_FRAMES_OBSERVED** | **PROVEN** |
| `results/runtime/d2-stream-probe.json` (probe, run 17:50–18:25) | 17:50–18:25 | **nothing** (variants A–E; no press request) | no | 0–2 echo-only "frames" per variant, 0 real | **`NO_STREAM_IN_ANY_VARIANT`** (mirrored in `results/final/d2-mode-state-finding.md`) | **NO_IDLE_FRAMES_OBSERVED** *(MISLABELLED)* | PROVEN (no press) |
| `results/runtime` proven-path row `armorx_real.py d2` @ 17:50 | 17:50 | **nothing** (unattended) | no | 0 (1 = echo) | **"proven path also silent" → device-state finding** | **NO_IDLE_FRAMES_OBSERVED** *(MISLABELLED)* | PROVEN (no press) |
| `physical-20260927-174445-buttons/raw-tx-rx.log` D2 @ 18:06:40 | 18:06:40 | **nothing** (query-dpi session; D2 sent, echo only) | no | 0 | (uneventful; recorded in raw log) | **NO_IDLE_FRAMES_OBSERVED** | PROVEN (no press) |
| `physical-20260927-174445-buttons/raw-tx-rx.log` D2 @ 18:08:37 | 18:08:37 | **nothing** (EF/E2/D4/D6 pre-read then session ended) | no | 0 | (uneventful) | **NO_IDLE_FRAMES_OBSERVED** | PROVEN (no press) |

**Button presses that really happened, and where the evidence is:**

| when (EDT) | action_id | what was asked | ack | evidence file |
|---|---|---|---|---|
| 17:07:47 | `d2_window_prepare` | power on + keep awake, tap ~every 30 s | done 17:08:42 | `results/runtime/physical-action-acks.jsonl` |
| 17:09:23 | `press_group_A` | A, B, X, Y one at a time ~4 s apart | done 17:10:15 | `results/runtime/press-groups.jsonl` |
| 17:10:49 | `press_group_B` | LB, RB, LT, RT | done 17:11:34 | `results/runtime/press-groups.jsonl` |
| 17:11:53 | `press_group_C` | View, Menu, L3, R3 | done 17:12:14 / 17:12:27 | `results/runtime/press-groups.jsonl` |
| 17:12:38 | `press_group_D` | RT, D-pad Up/Down/Left/Right | done 17:13:08 | `results/runtime/press-groups.jsonl` |
| 17:13:26 | `press_group_E` | RT, Capture, Guide, M1–M7 | done 17:14:27 | `results/runtime/press-groups.jsonl` |
| 17:14:50 | `press_group_F` | RT, M5, M6, M7, extra | done 17:15:38 | `results/runtime/press-groups.jsonl` |
| 17:26:06 | `id15_observe_capture` | press Capture ONCE | done 17:27:03 (no verdict) | `results/runtime/physical-action-acks.jsonl` |
| 17:47:24 | `button_rt` | press RT twice | done 17:47:40 | `results/runtime/operator-actions.jsonl` |
| 17:48:28 | `button_rt` | press RT twice (retry) | done 17:48:44 | `results/runtime/operator-actions.jsonl`, `…/button_rt.json` |
| 19:46:25 | `armorx_official_a_twice` | press A twice (official app) | done 19:46:25 | `results/runtime/operator-actions/armorx_official_a_twice.json` |

---

## B. Secondary table — experiment dirs with NO D2 in them (config/baseline/scan work)

Listed for a complete inventory; reinterpretation does not apply (D2 was never sent).

| run dir | date/time (EDT) | phase | D2 sent? | note |
|---|---|---|---|---|
| `physical-20260927-162321` | 16:23 | scan | no | scan only |
| `physical-20260927-162327` | 16:23 | scan | no | scan only |
| `physical-20260927-162402` | 16:24 | scan | no | scan only |
| `physical-20260927-162427` | 16:24 | identity | no | identity reads |
| `physical-20260927-162448` | 16:24 | readonly | no | as-found baseline `bdef9c61…` |
| `physical-20260927-162545` | 16:25 | noop-d7 | no | no-op D7 round-trip |
| `physical-20260927-162602` | 16:26 | noop-d7 | no | no-op D7 round-trip |
| `physical-20260927-162801` | 16:28 | query-dpi | no | DPI query |
| `physical-20260927-162815` | 16:28 | query-dpi | no | DPI query |
| `physical-20260927-162846` | 16:28 | query-dpi | no | DPI query |
| `physical-20260927-164022` | 16:40 | scan | no | scan only |
| `physical-20260927-165347` | 16:53 | scan | no | baseline + BlueZ scan; alert screenshot |
| `physical-20260927-170455-noop-d7` | 17:04 | noop-d7 | no | restore validation, PROVEN LIVE |

---

## C. Tally

- **D2-relevant runs/records reviewed:** 14 (8 experiment dirs that touch D2 + 4 runtime probe/raw-log records + 1 official leg + 1 proven-path row).
- **Runs/records whose "silent / failed / no-frames" label is now WRONG (mislabelled):** **5**
  1. `d2-live-differential-20260927-184643` — "CASE 6 none succeed" (no press made)
  2. `results/final/d2-mode-state-finding.md` + `results/runtime/d2-stream-probe.json` — "acknowledged but no longer streaming" / `NO_STREAM_IN_ANY_VARIANT` (no press made)
  3. `official-vs-harness-session-20260927-190741` harness leg — "HARNESS_SILENT" (no press made)
  4. `physical-20260927-174445-buttons` (RT) — "RETRY" read as stream failure (press made, but RT has no digital id)
  5. `physical-20260927-button-test3` — no verdict recorded, but it is a D2 no-frames run with no press made
- **Runs where a button WAS actually pressed:** **4**
  1. `physical-20260927-170844-d2` — press_groups A–F (A,B,X,Y,LB,RB,LT,View,Menu,L3,R3,D-pad,Capture,Guide,M1–M7) → **3293 frames, 26 ids**
  2. `physical-20260927-174445-buttons` — RT ×2 → 0 frames (RT not in mask)
  3. `physical-20260927-171616-id15` — Capture ×1 (no D2 capture channel; console observation)
  4. `official-vs-harness-session-20260927-190741` official leg — A ×2 → **155 frames**
- **Runs labelled correctly as-is:** the two immediate scan/never-connected dirs and all §B config dirs.

## D. Strongest live button-streaming evidence

See `strongest-live-evidence.md` in this directory.
