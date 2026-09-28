# RT digital id 9 — one-variable confirmation

**Date:** 2026-09-28, 06:36–06:38 local · **Branch** `research/physical-armorx-live-2026-09-27`
**Starting HEAD** `e91996a`…`3bddfe2` (245 tests / 12 subtests / 0 failed, clean) — verified, not reset.

## Question

Is digital mask **bit 9** RT's digital state? (Ledger `KEY-U-003`.)

## Design

ONE connection, ONE D2 session, three operator windows — the only physical variable changed is RT:

| window | popup title | what the operator did |
|---|---|---|
| **W0** control-before | `ArmorX RT Bit 9 — Control` | A held ~1 s + release, twice. Nothing else touched. |
| **W1** variable | `ArmorX RT Bit 9 — RT Test` | RT pulled fully and **kept held**; A held/released twice inside that hold; then RT released. |
| **W2** control-after | `ArmorX RT Bit 9 — Final Control` | same as W0. |

Popups: one per window, one sound each, ACKed by the DONE click. Sequence `A5 04 0B B4` sanity →
`A5 05 D2 01 7D` → windows → `A5 05 D2 00 7C` → clean disconnect.

## Result — `RT_DIGITAL_ID_9_PROVEN_LIVE`

| window | valid frames | A-caused (bit 0) | **frames containing bit 9** | bits seen | byte[16] range |
|---|---|---|---|---|---|
| **W0** | 228 | 78 | **0** | {0} | 0 – 0 |
| **W1** | 263 | 113 | **184** | {0, 9} | **0 – 255** |
| **W2** | 283 | 132 | **0** | {0} | 0 – 0 |

Inside W1 the bit-9 state is **DOWN → UP → DOWN → UP** (27.067 s → 28.447 s, 31.581 s → 33.154 s), so it
tracks two physical RT holds; on those frames byte[16] reads `17, 27, 96, 255` — the analog ramp of the same
pulls. Of W1's 79 frames with an empty mask, **not one** has bit 9 set, i.e. the bit clears when RT is
released. The four values `0 → 255` in W1 vs `0 – 0` in both controls show the analog channel moving at the
same time.

Every brief criterion, reported individually:

| criterion | result |
|---|---|
| 1. W0 contains valid A-generated frames | **pass** (78) |
| 2. bit 9 absent in W0 | **pass** (0 of 228) |
| 3. W1 contains valid A-generated frames | **pass** (113) |
| 4. bit 9 consistently present while RT held | **pass** (184 of 263 frames; every frame of both holds) |
| 5. byte[16] shows the known RT analog change simultaneously | **pass** (0 → 255) |
| 6. bit 9 clears after release where sample frames permit | **pass** (0 of 79 idle frames) |
| 7. bit 9 absent again in W2 | **pass** (0 of 283) |
| 8. no other changed control explains the transition | **pass** (no bit outside {0, 9} in any window) |

**Verdict: `RT_DIGITAL_ID_9_PROVEN_LIVE`.** Temporal ABSENT → PRESENT-WITH-RT → ABSENT under a
one-variable physical experiment. `KEY-U-003` is **RESOLVED**.

## Canonical RT mapping

| field | value |
|---|---|
| physical control | RT (right trigger) |
| **digital id** | **9** |
| **digital mask** | **`1 << 9` = `0x00000200`** |
| analog byte | `[16]` |
| analog observed range | 0 (rest) … 255 (full pull) |
| report-generation behaviour | **RT state is represented in D2 frames, but RT alone did not make the device emit a report in the isolated windows: its state becomes observable when another digital event forces D2 reports.** RT is **not** analog-only. |

## HCI coverage (this time verified per window)

One `btmon` instance for the whole run, started **before** the connection and never restarted — included
because restarting it mid-connection is what voided attempt 1. Per-window measurement: `btmon_running=True`,
file growth `6257→18341`, `18451→32390`, `32500→47499` bytes, `hci_coverage=True` for **W0, W1 and W2**.
Decoded afterwards: **780 notifications** = 777 harness records + 2 between-window liveness replies + the
D2-OFF echo; **6** writes on `0x0075` (0B sanity, D2 ON, 3 liveness probes, D2 OFF); 1 CCCD write on
`0x0078`.

Between every window an **active liveness probe** (the permitted `0B` query) was sent and a fresh reply was
required: `link_alive_after_window = True` for all three windows. This exists because in attempt 1 a dead
link was indistinguishable from "the operator pressed nothing".

## Attempt 1 — void (kept as evidence, `attempt-1-link-lost/`)

W0 captured 248 valid frames (bit 0 only, byte[16]=0 — a good control) and then **W1 and W2 captured
nothing**. Cause, found and fixed here: the runner restarted `btmon` before every window, and btmon takes
the **HCI user channel**, so cycling it under a live BLE connection killed the link. All four attempt-1
capture files are 383 bytes (header only). The operator performed all three windows correctly
(ACKs 06:33:59 / 06:34:43 / 06:35:18) — the windows were lost on our side, not theirs. A second attempt was
therefore made with: one capture started before the connection, per-window notification buckets, and the
liveness probe. Result above.

## Post-test state

- Last runtime write: **`a5 05 d2 00 7c`** (D2 OFF), clean disconnect, `cancelled=False`.
- **No D7, D8, configuration, DPI, lighting or macro write.** No pre-clear used.
- Read-only D6 integrity: sha256
  `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **`CONFIG_BASELINE_MATCH`**
  (integrity readback only; `DURABLE_OK` provenance unchanged).

## Provenance of the superseded negative

The 2026-09-28 closure session recorded `RT = PROVEN_NEGATIVE as a digital bit`; that verdict is
**superseded, not deleted** — it was method-limited, because RT alone emits no frame at all, so bit 9 could
never have appeared in those windows. It remains in the canonical files as dated history, and the wording
"the analog byte never left zero" is corrected there to *unsampled*.

Machine-readable: `RESULT.json` (criteria + verdict + capture log), `result-w{0,1,2}.json`,
`window-w{0,1,2}.jsonl`.
