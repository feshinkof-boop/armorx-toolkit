# Config write durability — the most important correction in this pass

## Summary

**A `D7` configuration write is not durable.** It updates a working/staging copy that a `D6`
readback faithfully reflects, but a power cycle reloads the previously persisted flash image.
Durability was observed only after the write was followed by a **long idle window** (~12-19 min)
before the unit was power-cycled.

## The experiment chain (all on the real unit)

| # | action | D6 read afterwards | verdict |
|---|---|---|---|
| 1 | `D7` mutant write (17:25), then ~19 min idle | (not read until later) | — |
| 2 | `D7` baseline restore (17:44) | `bdef9c61…` (= baseline) | looked correct |
| 3 | hard power cycle | `97fb2061…` (= mutant) | **restore lost** |
| 4 | `D7` baseline restore (18:08) + immediate clean shutdown/boot | `97fb2061…` | **restore lost** |
| 5 | `D7` baseline restore + **12 min idle** | `bdef9c61…` | staged write now live |
| 6 | hard power cycle after the idle window | `bdef9c61…` | **DURABLE** |

Rows 4 and 6 differ only in the idle window, so the settle period (not the shutdown type) is the
variable. The observed threshold is somewhere between "immediate" and ~12 minutes; the exact value
is **UNKNOWN** and must not be guessed.

## Consequence: a claim in this project was wrong

Earlier passes recorded `restore_verified: true` and `RESTORE_NOOP_VALIDATED = true`, and this pass
initially repeated "baseline intact" on the strength of a `D6` readback. **That reasoning was
invalid**: readback proves the staging copy only. Corrected statement:

> A configuration write may be claimed **staged-verified** after a `D6` readback. It may be claimed
> **persistent** only after a settle window and a power cycle, with a further `D6` read matching.

The no-op `D7` gate and the Emergency Restore exercise both remain true *as staging tests*; their
durability claim is withdrawn and must be re-earned if it matters.

## Why this matters beyond bookkeeping

1. Every later persistent experiment (D8 macros, DPI, lighting) needs the settle-window discipline,
   or the operator's hardware can be left in an experiment state that looks restored and is not.
2. Any future tool must treat "write, readback, power cycle, read" as the minimum verification
   sequence, and must never report success from the readback alone.

## Was it the cause of the D2 silence?

**No — that hypothesis is refuted.** After the durable baseline restore, D2 test mode still
produced no status stream (`NO_STREAM_IN_ANY_VARIANT`, 5 variants). The D2 silence remains
**UNKNOWN and unexplained** (see `d2-mode-state-finding.md`).

## Final unit state at the time of writing

- D6 = `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` = the immutable
  as-found baseline, **verified persistent across a power cycle**.
- No experiment state is left on the device.

---

## Verification vocabulary (authoritative)

```text
STAGED_OK

D7 write
→ immediate D6 readback equals target

does NOT prove flash durability.
```

```text
DURABLE_OK

D7 write
→ immediate D6 readback
→ idle / settle period
→ power cycle
→ D6 equals expected SHA256
```

Current durable baseline:

`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`

Previous no-op D7 and Emergency Restore evidence is **retained and reclassified as staging
evidence** — it was never a durability proof, and nothing is deleted.

---

## DATED CORRECTION — 2026-09-27 (overnight autonomous shift, no hardware)

**Applies to the "silent / no stream" conclusions in the text above. The original wording is left
exactly as it was written; this annotation records what later evidence changed.**

The official BIGBIG WON 4.0.8 app was captured live against the real ARMOR-X Pro (Android HCI snoop,
official-session differential, `results/experiments/official-vs-harness-session-20260927-190741/`)
and the correction is unambiguous:

**D2 input is EVENT-DRIVEN.** During that session the official app produced

* **0** valid `A5 12 02` frames while nothing was pressed, and
* **155** valid `A5 12 02` frames while the A button was pressed (18-byte frames, every checksum
  valid, only bit 0 ever set, PRESS -> RELEASE -> PRESS -> RELEASE, repeats ~every 11.7 ms).

Consequences for the conclusions above:

1. `NO_STREAM_IN_ANY_VARIANT` / "silent" / "no longer streaming" records where **no physical button
   was pressed after D2 was enabled** must be read as **`NO_IDLE_FRAMES_OBSERVED`**. In those runs
   the harness was looking for idle traffic; the device does not emit idle traffic even when it is
   working perfectly. Zero idle frames is the *expected* signature of a healthy link.
2. Such a result is therefore **not** evidence that the D2 stream is broken, and it is not a durable
   device-state finding.
3. Conversely, a run *with* a physical press and still no frames remains meaningful evidence, and has
   not been reinterpreted.

See `results/overnight/20260927-203902/branches/historical-d2-reinterpretation/` for the per-run
table, per-run annotations and the strongest remaining live button-streaming evidence.

Also corrected on the same date: `tshark` on this host is AppArmor-confined and cannot read paths
under `/home/salamanka` (copy captures to `/tmp` first), and `btatt.mtu` is not a valid field in
tshark 4.6.4 (requesting it makes tshark exit non-zero and print nothing, which previously looked
like "no frames").
