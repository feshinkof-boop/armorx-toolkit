# C0 physical test result — D2 pre-clear during a confirmed A-twice press

**Date:** 2026-09-28, 05:49–05:50 local · **Verdict: `C0_STREAMS_WITH_PRECLEAR`**

## The question

Does the current harness's `D2 OFF → D2 ON` pre-clear sequence suppress otherwise-working D2 button
reports? One controlled answer was required.

## Answer

**No. The pre-clear is not a gate.** With the pre-clear present and a confirmed physical A-twice press,
the harness received **167 valid 18-byte `A5 12 02` frames**, including a complete
`PRESS → RELEASE → PRESS → RELEASE` sequence on bit 0.

Per the decision tree this is **CASE 1**, so the causal matrix stops here: **C1 and C2 were NOT run.**

## Exact TX sequence (the run that streams)

| order | frame | meaning |
|---|---|---|
| 1 | `a5 04 0b b4` | sanity query — reply `a5 05 0b 30 e5` received (control channel healthy) |
| 2 | `a5 05 d2 00 7c` | **D2 OFF pre-clear** |
| 3 | `a5 05 d2 01 7d` | D2 ON |
| — | *operator popup raised; A pressed twice; DONE clicked* | |
| 4 | `a5 05 d2 00 7c` | D2 OFF (post) |
| — | | clean disconnect |

All writes were **ATT Write Command (0x52)** on handle `0x0075` (FFE1) — independently confirmed at HCI
level (see below), i.e. the same operation the official app uses.

## Operator acknowledgement

The one-shot popup (`ArmorX D2 C0 Test`, buttons `DONE` / `CANCEL / STOP`) was acknowledged —
`results/runtime/operator-actions/armorx_d2_causal_c0_a_twice.json`:

    {"status":"ACK","action_id":"armorx_d2_causal_c0_a_twice","response":"done",
     "clicked_at":"2026-09-28T05:50:15-04:00"}

The popup button click was the acknowledgement channel; no chat input was used, no sound repeated, and
no popup was recreated.

## Measured result

| metric | value |
|---|---|
| total notifications | 171 (167 valid + 3 D2 echoes + 1 sanity reply) |
| **valid D2 frames** | **167** (all 18 bytes, all checksums valid, zero malformed) |
| nonzero-mask frames | 25 |
| key bits observed | **bit 0 only** — no unexpected bits |
| A transitions | **4: PRESS → RELEASE → PRESS → RELEASE** |
| press 1 / release 1 | t=44.697 s → 44.905 s (held 208 ms) |
| press 2 / release 2 | t=45.926 s → 46.098 s (held 172 ms) |
| gap between presses | 1.021 s |
| held repeat cadence | median **15.0 ms** (min 5.0 ms) |
| frames before the press | **0** |
| frames after the last release to D2 OFF | **0** (≈12.9 s idle window) |

Zero idle frames before the press and after the release is the expected, normal behaviour: D2 input is
event-driven.

## Identity and integrity

- Identity read on connect: `2a24` = `5a4a2d5854` (`ZJ-XT`), `2a26` = `32373431` (`2741`) — matches the
  manifest.
- Post-test D6 read (`automation/scripts/read-config-integrity.py`, read-only, one frame sent):
  **10 reply frames (nine 20-byte + one 14-byte) = 144 bytes**, sha256
  `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **`CONFIG_BASELINE_MATCH`**.
- This is an **integrity readback only. It is NOT a new durability proof.** Durability remains
  `DURABLE_OK` from the earlier write→readback→settle→power-cycle→D6 sequence, and
  `STAGED_OK != DURABLE_OK` is unchanged.

## HCI-level corroboration

`btmon -i hci1 -w btmon.btsnoop` ran across the session. **Coverage limitation, stated honestly:** the
capture contains the *first* C0 attempt (the one that never raised a prompt) and stops before the valid
run — btmon's file mtime is 05:48 while the valid run began 05:49:26. The valid run therefore has
harness-level raw bytes (`tx-rx.jsonl`, byte-exact, complete) but **no HCI-level trace**.

What the HCI capture does prove independently, for the no-press window:

- `ATT: Write Request (0x12)` to `0x0078` (the FFE2 CCCD) — subscription at the HCI level;
- **`ATT: Write Command (0x52)` on handle `0x0075`** — the harness uses write-without-response, matching
  the official app;
- exactly **3 Handle Value Notifications** in that window: the sanity reply and the two D2 echoes,
  i.e. **zero button frames when nothing was pressed** — corroborating the event-driven model from a
  second, independent angle.

## Defects found and fixed during this test

1. **C0 never ran as C0.** The case was excluded from the declarative path and fell through to a legacy
   inline branch that wrote `D2_ON` directly — **no pre-clear and no operator prompt**. The first run in
   this directory is that branch: a connect, a sanity query, an enable, 10 s of silence, a disable. It
   is exactly the historical "silent window with no press" artifact, reproduced. C0 now uses its
   declarative definition (pre-clear + prompt + observe).
2. **Two runs shared one `tx-rx.jsonl`** with per-process `monotonic_s`, so the file spliced two
   different sessions. Records now carry a `run_id` and each run writes a `run_start` marker.
3. **Device matching depended on the advertised name**, which this unit does not always include. The
   matcher now also accepts the known address and the manufacturer-data signature
   (`5a4a2d5854` = `ZJ-XT`). Note BlueZ surfaces the company id byte-swapped (`0xfffe`), so both
   orderings are accepted.
4. **The operator dialog had no cancel affordance** in the causal path. It now supports an explicit
   `CANCEL / STOP` button, and `--yesno` is used when a cancel label is supplied.

## What this settles

- **The D2 pre-clear does not suppress button reports.** `D2-U-010` → `C0_STREAMS_WITH_PRECLEAR`.
- **The historical "harness silent" windows were a no-physical-input artifact**, now reproduced
  deliberately: the same harness, on the same unit, streams 167 frames when a press happens and 0 when
  it does not.
- **`D2-U-009` (connection interval) is not implicated** and stays the weakest candidate; the 11.25 ms
  experiment is not needed and was not run.
- No configuration, DPI, lighting, macro or firmware command was sent. D7/D8 were not touched.
