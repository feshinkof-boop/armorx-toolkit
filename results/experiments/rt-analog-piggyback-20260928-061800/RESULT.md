# RT analog piggyback sampling — result

**Date:** 2026-09-28, 06:18–06:26 local · **Branch** `research/physical-armorx-live-2026-09-27`
**Starting HEAD** `e91996a` (229 tests / 12 subtests / 0 failed, clean) — verified, not reset.

## Why this experiment exists

Analog-only movement emits **no D2 frame at all**: a full stick travel window and a full RT travel window
both produced zero frames (2026-09-28 closure session). So "RT produced no frames" never proved anything
about RT's analog state — the state simply had no frame to appear in.

**Method:** make a *digital* control force frame transmission, then read the analog fields inside those
frames. `A` (bit 0, PROVEN LIVE) is the trigger. Windows: `P0` baseline (A only), `P1` LT fully held + A
bursts, `P2` RT fully held + A bursts, plus `P2R`, a repeat of `P2`.

Offsets were verified from `results/reconciliation/d2-frame-contract.md` **before** the run: `[3..6]` mask
(BE u32, bit == id), `[7..14]` four signed int16 BE axes, `[15]` LT analog, `[16]` RT analog, `[17]`
trailer. Only frames that are exactly 18 bytes, `A5 12 02`, checksum-valid are counted. Rest is never
assumed to be zero — every value below is measured.

## Results

| window | valid frames | bits seen | A-caused frames | byte[15] on A-caused | byte[16] on A-caused |
|---|---|---|---|---|---|
| **P0** baseline | 204 | {0} | 56 | **0** (all 56) | **0** (all 56) |
| **P1** LT held | 186 | {0, 8} | 36 | **255** (all 36) | 0 (all 36) |
| **P2** RT held | 191 | {0, 9} | 40 | 0 (all 40) | **255** (all 40) |
| **P2R** RT held (repeat) | 203 | {0, 9} | 52 | 0 (all 52) | **255** (all 52) |

**Rest values are measured, not assumed:** byte[15] and byte[16] are `0` in every one of P0's 204 frames,
and in every idle (`mask == 0`) frame of the other windows. At a full pull both bytes read `255`. The
intermediate values observed during the travel ramps (`9, 31, 62, 67, 95, 100, 102, 122, 160, 190, 204,
219, 238`) show a continuous scale, so the observed range is **0..255** — no finer unit is claimed.

### P1 — positive control: `LT_ANALOG_PIGGYBACK_PROVEN`

With LT fully held, **every one of the 36 A-caused frames carries byte[15] = 255** (baseline 0), while
byte[16] stays `0` in all of them. The method demonstrably samples analog state inside digitally triggered
frames, and it does so selectively. This is what licensed P2.

### P2/P2R — the actual question: `RT_ANALOG_PROVEN_LIVE__PLUS_DIGITAL_BIT_OBSERVED`

With RT fully held, **every A-caused frame carries byte[16] = 255** (baseline 0), byte[15] stays flat `0`,
the idle frames return byte[16] to `0`, and the effect repeats — 2 holds in P2 (13 and 27 A-caused frames)
and 2 more in the repeat (15 and 37). Criterion-by-criterion:

| brief criterion | result |
|---|---|
| 1. A-generated valid frames present | **met** (40 and 52) |
| 2. RT itself still produces no independent digital bit | **NOT met — see below** |
| 3. byte[16] changes consistently and substantially | **met**: 0 → 255, 100% of A-caused frames |
| 4. byte[16] returns toward baseline at rest | **met**: all idle frames read 0 |
| 5. effect repeats across both holds/bursts | **met**: 2 + 2 |
| 6. byte[15] shows no RT-specific change | **met**: flat 0 in every frame of both runs |

## The second finding: a digital bit *did* appear (id 9)

P2 and P2R both show mask bits **{0, 9}**: masks `513` (A + bit 9), `512` (bit 9 alone) and `0`, with
**no bit 9 in P0 or P1**. Bit 9 appears only while RT is physically held, across two holds in each of two
independent windows, 107 and 144 frames respectively, with byte[16] ramping alongside it.

Per the brief this bit is **preserved as evidence and NOT named here** — the candidate is obvious (RT was
the only control held, and the static reading for RT is id 9), but naming it is a separate claim that needs
its own one-variable confirmation, so it is recorded as:

> **`NEW_BIT_9_OBSERVED_UNNAMED`** — observed only in windows where RT was fully held; candidate control RT;
> not yet proven as RT's digital id.

**This supersedes the previous "RT = PROVEN_NEGATIVE as a digital bit" verdict, which was method-limited,
not proven.** The earlier negative rested on windows in which *no frame was ever emitted* because RT alone
does not trigger transmission — the bit could not have appeared there. The corrected statement is: **RT's
digital bit was unobservable by the earlier method**; when frames are forced by another control, it appears.

## HCI corroboration (honest coverage)

| file | lines | notifications | covers |
|---|---|---|---|
| `btmon.btsnoop` / `btmon-p0-partial.btsnoop` | 851 | **0** | scan traffic only — **P0 has no HCI coverage** |
| `btmon-rest.btsnoop` | 1532 | **189** | **P1 exactly** (186 button frames + 3 control-plane) |
| `btmon-p2r.btsnoop` | 1721 | **208** | **P2R exactly** (the harness recorded 208 notifications too) |

**Limitation, stated rather than papered over:** btmon stopped writing mid-session twice (the known
btsnoop-stall) — it did not cover P0, and it did not cover P2. `P2R` was run as a repeat specifically to
get the decisive window under HCI, and it matched the harness record frame-for-frame (208 = 208), with 3
Write Commands on `0x0075` and the CCCD write on `0x0078`. The harness raw bytes (`window-*.jsonl`) are the
primary record for all four windows.

## Post-test state

- Last runtime write on the wire: **`a5 05 d2 00 7c`** (D2 OFF), clean disconnect, in every window.
- **No D7, D8, configuration, DPI, lighting or macro write** was sent; no pre-clear was needed.
- Read-only D6 integrity: 144 bytes, sha256
  `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **`CONFIG_BASELINE_MATCH`**
  (integrity readback only; `DURABLE_OK` unchanged, `STAGED_OK != DURABLE_OK`).

## What this does and does not establish

- **Established:** RT's analog travel is present in D2 byte[16], provable through digitally triggered
  sampling; rest = 0, full pull = 255.
- **Established:** the earlier "RT has no digital id" conclusion is retracted as a method artifact; a
  distinct bit (9) accompanies RT's full pull.
- **NOT established:** that bit 9 *is* id 9 assigned to RT (needs its own one-variable confirmation), that
  the analog value maps linearly to physical travel, or anything about what the official app does with it.
- **Next action:** a single confirmation window — `A` bursts alone vs `A` bursts with RT fully held, one
  control only — to name bit 9, or read RT in the official app's trigger/DPI view to confirm the value the
  app itself displays.

Machine-readable verdicts: `ANALYSIS.json` (in this directory).
