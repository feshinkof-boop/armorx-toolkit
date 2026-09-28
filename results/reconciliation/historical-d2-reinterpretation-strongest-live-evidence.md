# Strongest live button-streaming evidence (corrected, event-driven model)

Ordered by evidential weight. Grades: **PROVEN** / **STRONG EVIDENCE** / **INFERRED** / **UNKNOWN**.

---

## 1. PROVEN — the harness itself streamed live button input: 26 key ids, 3293 frames

**Path:** `results/experiments/physical-20260927-170844-d2/`
- `session.jsonl` — **3293** `A5 12 02` capture frames, `21:08:47.480Z → 21:24:00.837Z` (≈912 s).
- `real-key-id-map.md` — **26 ids PROVEN LIVE** with per-id bit masks and frame counts:
  `[0,1,3,4,6,7,8,10,11,12,13,14,15,16,17,18,19,20,23,24,25,26,27,28,29,30]`.
- `observations/group-A.json` (A/B/X/Y, 1138 frames in the window) and
  `observations/press_group_C.json` (View/Menu/L3/R3, 1827 frames) — per-window frame dumps.
- Mirror: `results/final/real-key-id-map.md`.

**Why this is the strongest:** it is the only artifact where the **harness's own BLE stack** received
real button frames from the real unit, and each id is claim-verified (a frame whose mask has exactly
that one bit set, inside the request window), not guessed. It proves the harness *can* stream; it also
proves the streaming is **event-driven**, because the frames map 1:1 onto the operator's
`press_group_A…F` requests (`results/runtime/press-groups.jsonl`).

**Caveat (honest):** the operator was told to keep tapping (`d2_window_prepare`), so this run does not
prove an *idle* stream exists — and under the corrected model there is no reason to expect one.

**RT is the exception:** requested 4× (groups B, D, E, F) and **never** produced a digital bit; analog
byte `[16]` never left zero. So **RT has no digital key id on this unit** — PROVEN LIVE negative.

---

## 2. PROVEN — the official app's event-driven stream, with the idle-vs-press contrast

**Paths:** `results/overnight/20260927-203902/fixtures/official-fixtures.json`,
`results/overnight/20260927-203902/official-timeline-verification.json`,
`results/overnight/20260927-203902/official-timeline-canonical.json`
(source capture `bt_hci_20260928_023405_d.cfa`, sha256 `bbaf10bd…`).

- **155 frames**, all 18-byte, all checksum-valid; masks `00000001`×29 (press) and `00000000`×126 (release/repeat).
- Transitions: PRESS @104.86 s → RELEASE @105.086 s → PRESS @105.929 s → RELEASE @106.165 s.
- **0 frames** across the 61.0 s window between D2 enable (68.498 s) and D2 disable (129.526 s) —
  `"idle_window": {"status": "VALID_EVENT_DRIVEN_SILENCE"}`.
- Only bit 0 (button A) ever set; held-button reports repeat ~every 12 ms.

**Why it matters:** this is the **definitive control** for the event-driven model — same unit, official
app, D2 on the whole time, **zero frames while idle and 155 while pressed**. It is the artifact that
makes every historical "0 frames" reading unsafe to treat as failure.

---

## 3. STRONG EVIDENCE — the button-request ledger that pins the successful run to real presses

**Path:** `results/runtime/press-groups.jsonl`, `results/runtime/physical-action-acks.jsonl`,
`results/runtime/operator-actions.jsonl`.

Seven press groups (17:09:23–17:17:15 EDT) plus `d2_window_prepare`, **all acknowledged `done`**, all
inside the `physical-20260927-170844-d2` capture window. This is what upgrades §1 from "frames
appeared" to "frames appeared *because the operator pressed the named buttons*".

---

## 4. STRONG EVIDENCE — Capture (id 15) is real and live

**Path:** `results/experiments/physical-20260927-170844-d2/real-key-id-map.md`, row id 15
(`byte[5] bit 7`, 28 frames in `press_group_E`). Plus the operator was asked to press Capture once
(`id15_observe_capture`, ack `done` 17:27:03) — though that press was observed on a console, not via D2.

---

## 5. What this means for the mislabels

The historical "silent" verdicts were **not** evidence of a broken stream. The one run with confirmed
presses on the harness link (§1) streamed 3293 frames; the mislabelled runs had **no press** in their
windows (§ `annotations/`). The only confirmed press with 0 frames on the harness is the **RT** test,
and RT is a button with no digital key id — so it too is expected, not a failure.

## 6. Remaining UNKNOWN (not to be promoted)

- Whether the harness link produces frames when a **reported** button is pressed *without* the earlier
  session's awake-tapping context — i.e. a clean single-button press-on-harness test has never been run.
- The digital id of **RT** (UNKNOWN; likely analog-only or unmapped on this firmware).
- ids `[2, 5, 9, 21, 22, 31]` — no physical button produced these bits.
