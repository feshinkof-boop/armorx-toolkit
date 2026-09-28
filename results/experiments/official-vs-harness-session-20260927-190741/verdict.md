# Verdict — official vs harness session differential

## Status: **COMPLETE**

**Classification: `OFFICIAL_WORKS_HARNESS_SILENT`.**

The official BIGBIG WON 4.0.8 app, running on the real vivo V2304A against the real ArmorX Pro,
**does** receive valid `A5 12 02` button frames (155 during the A-twice test), while the Linux
harness received none.

## What this settles

| question | answer |
|---|---|
| Does official Button Test produce `A5 12 02`? | **YES** — event-driven, only while a button is held/changed |
| Is Android bonded? | **NO** — the ArmorX is not in the phone's bond list |
| Is the link encrypted before D2? | **NO** — 0 SMP frames, 0 encryption-change events |
| What MTU does Android negotiate? | **64** (after a default 23 exchange) — same as the harness |
| Connection interval / latency / timeout? | 11.25 ms / 0 / 2000 ms (history 30→7.5→30→11.25 ms) |
| What PHY? | no PHY-update events observed (1M assumed) |
| When is FFE2 CCCD written? | +1.34 s, handle `0x0078`, Write Request |
| What carries the official D2 enable? | **Write Command (0x52)** on `0x0075`, value `a505d2017d` — identical to ours |
| Writes between connection and D2 absent from our harness? | **YES** — EF, E2, D4 and a full D6 config read (8 fragments) |
| Earliest material difference? | **OFFICIAL_CONNECTION_INTERVAL_DIFFERENT** (11.25 vs 7.50 ms) |

## Hypothesis status

- **D2-U-008** (bonding/encryption prerequisite): **REFUTED.** Official streams unbonded and
  unencrypted; the harness is in the same state, so security cannot be the differentiator.
- **D2-U-009** (MTU/PHY/connection-parameter/session differences): **SUPPORTED** (not causal).
  MTU and PHY turn out equal; the connection-interval profile differs. Recorded as
  `SUPPORTED`, never as `D2_REQUIRES_...`.
- **D2-U-007** (why our harness stays silent): **NARROWED, still UNKNOWN.** Ruled out by this
  capture: the D2 value, the ATT write type, the handle, the write order, MTU, CCCD behaviour and
  security state. The leading remaining candidate is the **pre-D2 device-info + full-config read
  burst** (EF, E2, D4, D6×8) that the harness omits — correlation only, causality **not**
  demonstrated. A second, weaker candidate is the connection-interval difference.

## Configuration integrity

Fresh D6 read this pass, after the official app disconnected and Linux regained the adapter:

`sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **CONFIG_BASELINE_MATCH**

Device identity observed live (`2A24=ZJ-XT`, `2A26=2741`) matches the manifest before the read.
The 144-byte raw readback follows the repository's global `*.bin` ignore rule, so the committed
evidence is its sha256 + length (in `final-d6.json` / `id15-probe-result.json`).

Readback integrity confirmation **only** — not a new durability proof. The baseline remains
**DURABLE_OK** from the earlier `write → readback → idle/settle → power cycle → D6 exact match`
procedure; immediate readback alone is still **STAGED_OK**.

## Method notes / corrections

- The `.cfa` snoop file produced by this Android 16 build is a plain **BTSnoop v1 (HCI UART)** file
  and decodes directly with tshark, extracted from a bugreport (no root).
- **tshark is AppArmor-confined on this host**: it cannot read paths under `/home/salamanka`. Every
  capture must be copied to `/tmp` first. This also invalidated an earlier conclusion that tshark
  could not decode our Linux-monitor captures — it can, and its view agrees exactly with `btmon -r`.
- `btatt.mtu` is not a valid field in tshark 4.6.4 here; asking for it makes tshark exit non-zero and
  return nothing (which silently looked like "no frames"). MTU values were taken from `-V` output.

> **CORRECTION 2026-09-27 (overnight shift):** the D6 configuration read is **TEN reply frames**, not
> eight: nine 20-byte frames (`A4 14 D6 01`..`A4 14 D6 09`, 15 payload bytes each) followed by one
> 14-byte tail frame (`A4 0E D6 0A 01 0D 19 1A 1B 1C 1D 1E 1F 64`, 9 payload bytes). Payload total is
> 135 + 9 = **144 bytes**, and it reassembles to sha256
> `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` - byte-identical to the lab's
> durable baseline. An earlier extraction step capped the list at eight and that error propagated into
> this file's wording. The numbers above were correct for the frames examined; the count was not.

---

## DATED CORRECTION — 2026-09-27/28 (overnight shift): the "harness silent" reading is superseded

**This document's observation stands; its implication does not.** The harness half of this experiment
requested **no physical press** (the operator-action log for that window contains only power-on/setup
popups), while the official half requested one (`armorx_official_a_twice`, ACKed 19:46:25). Under the
corrected event-driven model a window with no press is expected to produce zero frames in *every*
configuration, so this comparison does not demonstrate a device difference.

The harness demonstrably receives button frames: on 2026-09-27 at 17:08 the Linux/bleak harness
captured **3,292 valid 18-byte `A5 12 02` frames across 26 key ids** with the control plane
`0B → D2 ON` (no pre-clear). See `results/reconciliation/d2-u007-harness-streaming-reconciliation.md`
and the reproducible audit `automation/scripts/harness-streaming-audit.py`.

Consequently `OFFICIAL_WORKS_HARNESS_SILENT` is reclassified
`HARNESS_STREAMS_UNDER_PRESS__DIFFERENTIAL_WINDOWS_WERE_NOT_PRESS-MATCHED`, and the pre-clear becomes
the single untested-with-a-press variable (case `C0`).
