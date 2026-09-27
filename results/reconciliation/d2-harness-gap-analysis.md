# Official App vs Current Harness

## Confirmed identical behavior

1. The D2 enable frame is byte-identical: `A5 05 D2 01 7D`, written to `FFE1`.
2. The D2 disable frame is byte-identical: `A5 05 D2 00 7C`.
3. Notifications are taken from `0000FFE2` and the status frame is the 18-byte `A5 12 02 …`.
4. The key mask is the big-endian u32 at indices 3..6 and **bit index == key id**.
5. The mask is absolute state, so press/release is bit-set/bit-clear with no event typing.
6. No ack is required for either D2 frame, and neither is awaited.
7. No delay, gate, mode query or second start command exists on the path.

## Confirmed differences

1. **Our harness sends `0B` before D2; the app sends nothing.** (PROVEN STATIC difference;
   INFERRED harmless.)
2. Our harness awaits/observes its frames and drains before analysis; the app fires and forgets.
   (Timing only.)

## Possible differences not yet proven

1. **Write type for the D2 enable** — `write-without-response` is PROVEN STATIC for the 2.22/2.23
   code path; for 4.0.8 it is UNKNOWN, and our harness uses write-without-response.
2. Whether the device needs the CCCD write to be re-issued after the enable (INFERRED from the
   2.22–2.24 ordering, CONTRADICTED by 4.0.8's connect-time arming).
3. Whether the unit reports input only when its console link is active — CONTRADICTED live: the
   operator confirmed there is no console at all, yet one run streamed 3295 frames.

## Missing behavior ranked by evidence

A. Write type of the D2 enable (UNKNOWN; the only unmodelled protocol-level difference).
B. CCCD re-arm after the enable (INFERRED, contradicted by 4.0.8).
C. Nothing else: every other candidate is PROVEN STATIC-absent.

## Most likely root cause

**UNKNOWN.** Static reconstruction eliminated every command-level candidate; the remaining
explanations are device-side or transport-level, and the reconstructed official sequence is
byte-for-byte our sequence.

## Confidence

High confidence in the reconstruction itself (PROVEN STATIC anchors re-verified by the parent in
two independent functions). Low confidence in any root-cause claim, because none is supported.

## Why competing hypotheses are weaker

- *Missing command*: the app never sends one (PROVEN STATIC across four builds).
- *Missing gate*: no firmware/enum/mode check exists on this path (PROVEN STATIC).
- *Needs console*: refuted by the operator's `no_console` answer and the historical success.
- *Config state*: refuted — the durable baseline was live and D2 still produced no stream.
- *Adapter/HCI path*: refuted — the same path streamed 3295 frames earlier today.
