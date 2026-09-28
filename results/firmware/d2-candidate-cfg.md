# D2 candidate population: CFG reachability walk (V41, static)

Region `0x1e0ac14`-`0x1e0e414` (the container that the splitter labelled as starting at
`0x1e0aff2`). Root of the induced graph: `0x1e0ac14`, in-degree 0. `4288`
blocks, `3905` reachable from the root, `4288` instructions
after masking `102` inline table ranges.

## The answer: sequential, not mutually exclusive

Reachability alone cannot order these blocks - every pair reports `CYCLIC_BOTH_ORDERS_POSSIBLE` because the
function contains internal loops. Forward order is therefore established by **dominance**, which holds on
every pass:

| marker | address | dominated by |
|---|---|---|
| r13 copy into candidate | `0x1e0cd24` / `0x1e0cd2e` | (itself) |
| packed-bit seed (14B arm) | `0x1e0da54` | r13 copy |
| compare/change gate | `0x1e0dad2` | r13 copy |
| 14B build | `0x1e0dafe`, builder `0x1e0db0c` | r13 copy, compare gate |
| 28B build | `0x1e0e2c2` | r13 copy, compare gate |

So in a normal pass the order is: **r13 28-byte copy -> (conditionally) packed-bit seed -> compare gate ->
14B build -> 28B build.** The r13 copy executes before both builders and before the change gate; nothing in
this region can write the candidate after the builders without another loop iteration.

## Field precedence (now evidence-based)

1. `0x1e0cd2e` copies 28 bytes from the object behind `[sp+24]` into the candidate - this writes **all**
   fields including `+0x0c`/`+0x0d`.
2. The packed-bit seed arm (`0x1e0da54`/`0x1e0da62`) then **overwrites** `+0x0c`/`+0x0d` with bits 8/9, but
   only on the arm that takes it: it is dominated by the copy and does **not** dominate the 14B build.
3. Injectors A/B overwrite axes `+0x04`/`+0x06` and `+0x08`/`+0x0a` when the selector nibbles are 1..10.

Consequence: the packed-bit values are the **later** write. A frame carries bit-derived LT/RT whenever the
seed arm is taken, even though the r13 copy supplied values first. The live analogue reading therefore
requires a pass where the seed arm is skipped - that is a concrete, testable reconciliation of the live
observation, and it is the opposite of the earlier assumption that the bits were only a pre-seed default.

## Tooling corrections (both regression-tested)

* The vendor disassembly renders **stack offsets in decimal** (`b[sp+1092]`) while globals are hex.
* `tbh`/`tbb` tables are emitted **inline and were being linear-swept as code**. The earlier "unresolved
  table at `0x1e0dbe4`" was table payload: bytes `00aa 0153 033c 018b` decode as `tbb [r10]`,
  `{pc, r3} = [sp++]`, `[sp+76] = r4`, `{rets, rete, reti} = [sp++]`. Table ranges are now masked before
  any CFG is built. Two bugs this exposed in my own earlier walk: out-of-region branch targets were clamped
  onto the last block (creating a phantom super-hub), and removing every back edge destroyed reachability
  and is not a valid way to order blocks.

## Open

* `packed_bit_seed_28B` (`0x1e0e3ae`) is **unreachable in this region's graph** and dominated by nothing. It
  is presumably reached from outside the region (possibly the exception-prologue function at `0x1e0dbec`).
  Unreachable in my model is not the same as dead - not claimed as dead.
* `[sp+24]`'s writer is still unidentified, so the identity of the object copied into the candidate is open.
