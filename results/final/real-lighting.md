# Real lighting / RGB (status: NOT STARTED, and why)

## Evidence available

**None yet, on the real unit.** No lighting command has been sent to the physical ARMOR-X in this
research line, and no lighting readback has been captured. RGB channel order therefore remains
**UNKNOWN**.

## Constraints recorded in advance (project rules)

A lighting experiment is only acceptable when all of these hold:

1. the current lighting state can be **read or reliably restored** first;
2. the mutation changes **exactly one variable** (one zone, one channel, others zero);
3. effect/speed settings stay untouched;
4. the human observation is collected through a **structured GUI choice** (OFF / SOLID / SLOW
   BLINK / FAST BLINK and a colour choice), never by typing colour names into chat;
5. the original state is restored immediately afterwards and the restoration is verified.

## Why it has not been attempted

Lighting is priority 6 in the current plan, and the earlier priorities are partly blocked on the
unit's input-reporting state (`d2-mode-state-finding.md`). Writing lighting state before a restore
path exists would risk leaving persistent state on the operator's hardware — explicitly forbidden.

## Highest-value first step when it resumes

Reconnaissance, not mutation: find the lighting opcode and its read form in the 4.0.8 Dart AOT
image (as was done for `subpackageLength` in `real-d8.md`), then perform a **same-value no-op
read/write** on the real unit and verify by readback before any visible change.
