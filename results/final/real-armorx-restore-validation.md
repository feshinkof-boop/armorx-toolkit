# Real-device restore validation (REAL ARMOR-X)

Immutable baseline (the unit's own config, as found):
`sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`, 144 bytes,
declared length `0x0090`, stored CRC `2c40`, CRC valid.

## 1. Inherited results (not repeated)

Per the resume rule, the previously validated results are **reused, not re-proven**:

- D7 no-op write gate: exact-baseline write → D6 readback → **byte-for-byte equal** (`RESTORE_NOOP_VALIDATED = true`).
- Emergency Restore path: physically exercised against this same baseline against this unit.

No further no-op D7 write was performed merely for ceremony.

## 2. Resume check on the real unit

A **read-only D6** was taken on resume and compared by SHA-256 — exactly the rule in the brief.
That check found a **leftover experimental state**, not the baseline:

| item | value |
|---|---|
| read-only D6 on resume | `sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` |
| verdict | **BASELINE_LIVE** (`probe-readback.bin`, saved as `baseline-resume-current.bin`) |
| byte diff vs the immutable baseline | `[0, 1, 127]` |
| interpretation | the leftover state is **byte-for-byte the ID-15 experiment image** (byte 127 → `0x02`, CRC recomputed) — i.e. our own experiment, **not** legitimate user state |

Cause: an interrupted session. The ID-15 write had been executed and verified live
(`MUTANT_LIVE`), and the restore that followed it was cut short by an operator stop, so the unit
kept the test mapping.

## 3. Restoration performed and verified

| step | evidence |
|---|---|
| leftover bytes frozen first | `baseline-resume-current.bin` = `97fb2061a352650c29007b7918ecc2bed907291073b849cfda61e460296b103d` |
| D7 restore write of the immutable baseline | ack `['a505d70081']` |
| D6 readback after restore | `sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`, `readback_equals_target = True`, CRC valid = True` |
| independent read-only re-check (new connection) | verdict **BASELINE_LIVE** = `bdef9c619dba4836…` |

`EMERGENCY_RESTORE_REAL_DEVICE = VERIFIED` — the unit is back on its original configuration, and
that was confirmed by a fresh connection's read, not by the write's own return value.

## 4. Provenance

- identity gate at every write: live `2A24 = ZJ-XT`, `2A26 = 2741` matched the manifest
  `baselines/device/ZJ-XT_2741_2D-37-35-6D-66-11/20260927-170400-baseline-as-found.json`
- tool: `automation/scripts/id15-experiment.py` (`--probe` read-only / `--restore` write+verify),
  run through `automation/radio/use-bumble.sh` on the lab adapter
- operator actions involved: `armorx_power_required_restore` (READY click) and, earlier,
  `armorx_powercycle` — both acknowledged by GUI click, recorded in
  `results/runtime/operator-actions.jsonl`

---

## CORRECTION (later in the same pass) — durability claim WITHDRAWN

This document's verification chain is a **staging** proof: a `D6` readback matches the written
image. It is **not** a durability proof, and the durability statement it implies was **wrong**.

A hard power cycle later showed the unit reloading a previously persisted image (the ID-15 mutant)
even though the readback had matched the intended baseline. A write only became persistent after a
**settle/idle window** of roughly 12–19 minutes before power-off, verified by a further read after
a power cycle. See `real-config-durability.md` for the six-step experiment chain.

Corrected wording for anything above:

- "restore verified" → **staged-verified by readback**;
- "byte-for-byte equal" → true of the staging copy at that moment;
- "restore_verified: true" → **withdrawn as a durability claim**.

The unit's final state *is* durable (`bdef9c61…`, survives a power cycle), but that was earned at
the end of the pass, not by the readback that this document describes.
