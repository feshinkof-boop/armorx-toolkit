# Tomorrow's plan (prepared overnight, nothing executed)

Written 2026-09-27, revised 2026-09-27/28 after the second overnight pass. Hardware was not touched:
every command below is **prepared and offline-tested**, not run.

## The corrected starting state (changed since the first draft)

The harness is **not** silent. On 2026-09-27 at 17:08 it captured **3,292 valid 18-byte `A5 12 02`
frames across 26 key ids** with the control plane `0B -> D2 ON` and **no pre-clear**
(`results/reconciliation/d2-u007-harness-streaming-reconciliation.md`). Every window previously read as
"silent" had **no physical press requested**; the official window did.

Two consequences for tomorrow:

1. **Case C1 (no pre-clear) is already known-good with a real press** - so the only untested variable is
   the pre-clear, which is exactly what `C0` isolates.
2. **A press must be CONFIRMED inside the observation window.** Without a press, every configuration
   produces zero frames, and the run would prove nothing.

## Safety limits that still apply

- Allowed: BLE discovery, identity reads, proven read-only queries, the `0B` sanity query, **D2 runtime
  enable/disable**, notification/CCCD operations, passive capture (`btmon`/`tshark`), **D6 configuration
  READ**, disconnect/reconnect, and one-button physical validation **only after valid D2 streaming exists**.
- Forbidden: D7, D8, configuration writes, DPI writes, lighting writes, macro/config mutation,
  undocumented commands, AE01/RCSP writes, OTA, firmware writes, bootloader, flash, AC632Nuke.
- `D2` is a runtime mode only: **always attempt D2 disable before disconnect.**
- Never invent an operator verdict. A bare "done" proves the action happened, nothing more.
- Correlate, never claim causality the captures do not prove.
- Operator contract: **one popup, one sound, one requested action, popup persists until clicked, the
  popup button click is the acknowledgement channel.** No chat acknowledgement, no repeating alerts.

## Experiment 1 — the D2 causal run (highest value, ~20 minutes)

Purpose: separate the three remaining D2 candidates, one variable at a time.

### First action (shortest path)

**Run `C0` only.** If C0 streams during a confirmed A-twice press: **STOP** - the pre-clear was never
the problem, and the next work is the unresolved key ids, one button per popup. Only if C0 is silent
*with a confirmed press* do you run `C1`, and only if C1 also fails, `C2` (the official burst is not
required: the streaming run sent only `0B` before D2, and the static work shows the burst is generic
application initialisation, not a D2 precondition).

| case | sequence | isolates |
|---|---|---|
| C0 | connect → sanity `0B` → **D2 OFF (pre-clear)** → D2 ON → A-twice → observe → D2 OFF | control (today's harness) |
| C1 | connect → sanity `0B` → D2 ON (no pre-clear) → A-twice → observe → D2 OFF | the pre-clear |
| C2 | connect → sanity `0B` → `EF` → `0B` → `E2` → `D4` → **full D6 read** → D2 ON (no pre-clear) → A-twice → observe → D2 OFF | the official read burst |

**Offline proof that this is decidable:** `results/reconciliation/offline-causal-run/offline-causal-matrix.json`
- with a device where the pre-clear matters, `C0` is silent and `C1`/`C2` stream; with a device where it
does not, all three stream. Redo it any time with
`python3 automation/scripts/offline-causal-run.py` (no hardware, ~1 minute).

Success is measured **during a real key press**, never by idle traffic:

- minimum: one or more valid 18-byte `A5 12 02` frames while A is held/changed;
- strong: PRESS → RELEASE → PRESS → RELEASE for key id 0;
- **zero idle frames is NORMAL** — the stream is event-driven (the official app produced 0 while idle
  and 155 while A was pressed).

Commands (run from `/home/salamanka/armorx-lab`, one case at a time, unit awake, operator at the bench):

```bash
# 0. unit awake check + capture
.venv-bumble/bin/python automation/scripts/d2-differential.py scan --outdir results/experiments/d2-causal-<ts>
sudo -n btmon -i 1 -w results/experiments/d2-causal-<ts>/raw/btmon.btsnoop &

# 1. the case (raises ONE popup asking for the A-twice; click DONE when done)
D2_OBSERVE_S=15 .venv-bumble/bin/python automation/scripts/d2-differential.py variant \
    --outdir results/experiments/d2-causal-<ts> --case C0      # then C1, then C2

# 2. decode
sudo -n btmon -r results/experiments/d2-causal-<ts>/raw/btmon.btsnoop > results/experiments/d2-causal-<ts>/raw/btmon.txt
```

The harness writes `tx-rx.jsonl`, `timeline.csv` and `result.json` per case. Classify with
`d2_runner.verdict_from_frames` (`NO_IDLE_FRAMES_OBSERVED` / `BUTTON_FRAMES_RECEIVED` /
`A_TWICE_PROVEN`).

Interpretation rules, decided in advance:

- C0 reproduces silence AND C1/C2 stream ⇒ the cause was the pre-clear or the read burst; the next
  step splits those two by their own cases.
- C1 streams but C2 does not ⇒ the read burst is harmful, not helpful.
- All three silent, each with a **confirmed physical press** ⇒ the remaining candidates are the
  connection-parameter profile (11.25 ms vs 7.50 ms) and something not yet identified; move to
  Experiment 2 and stop guessing at protocol bytes.
- Any case streaming ⇒ immediately capture the unresolved key ids with one button per popup
  (RT/id 9 is still unregistered).

## Experiment 2 — connection interval 11.25 ms (only if Experiment 1 is fully silent)

Mechanism documented by the connection-parameters branch (`branches/connection-params-11ms/`); do not
apply to the adapter without reading it. The measured official profile is 30 → 7.5 → 30 → 11.25 ms
across four link-layer updates, while the harness sits at 7.50 ms.

## Experiment 3 — read-first closures (only when the unit is awake and idle)

For each of D8/macros, DPI/FC, motion/AB and lighting: **query first, same-value no-op second, a single
controlled mutation third, restore last.** The static branches produced the frame shapes and the open
questions; no writes should be attempted before reading those deliverables.

## Deferred (needs hardware or operator)

- the causal run above (needs a real press);
- unresolved key-id capture (one button per popup);
- the F20 receiver and any USB-side work;
- Android app-side dynamic work against the real phone (ADB is available now, but BLE capture requires
  the phone in hand).

## What is NOT needed any more

- re-deriving the official D2 command: it is identical to ours (`A5 05 D2 01 7D`, ATT Write Command
  `0x52`, handle `0x0075`) — PROVEN LIVE;
- bonding/encryption theories: D2-U-008 is REFUTED (both links unbonded and unencrypted);
- MTU theories: both sides negotiate 64;
- re-counting the official D6 read: it is **10 frames / 144 bytes** and reassembles byte-identical to
  our durable baseline `bdef9c61…`;
- the D2 write type: the official frame is an ATT **Write Command (0x52)**, i.e. without response, same
  as ours — D2-U-001 is CLOSED;
- the pre-D2 burst as a *necessary* precondition: the streaming run sent no EF/E2/D4/D6, and the static
  work shows the burst is generic initialisation — do not spend a case on it unless C0 and C1 both fail.

## Full ledger

`results/reconciliation/master-unknown-ledger.md` - 19 entries: 4 statically exhausted, 4 requiring the
operator, 8 requiring hardware, 3 requiring new external evidence.
