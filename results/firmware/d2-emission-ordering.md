# D2 emission ordering (2026-09-29)

Status: **PARTIALLY PROVEN STATIC**. No live validation. Nothing was transmitted.

## Method

CFG over `0x1e0ac14`-`0x1e0e414` (one function, 4311 blocks, 3112 reachable) built by
`tools/q32s/q32s_cfg.py`, then dominance verdicts on block indices and concrete forward paths
between the blocks of interest. Passing addresses instead of block indices yields a spurious
`UNREACHABLE`, which is worth knowing before trusting a verdict.

## Dominance says neither dominates

```text
synthesis 0x1e0cfc0  vs  memcmp 0x1e0dad2   CYCLIC_BOTH_ORDERS_POSSIBLE
r13 copy  0x1e0cd2e  vs  build14 0x1e0dafe  CYCLIC_BOTH_ORDERS_POSSIBLE
r13 copy  0x1e0cd2e  vs  build28 0x1e0e2c2  CYCLIC_BOTH_ORDERS_POSSIBLE
```

The container is a periodic loop, so none of these pairs dominates the other. The earlier
"population is sequential by dominance" statement is **not reproducible** under block-index
semantics and is corrected here. Ordering claims must rest on concrete paths.

## Concrete paths

```text
synthesis -> memcmp    42 blocks
memcmp -> synthesis   105 blocks (through 0x1e0c6a6, 0x1e0c8c0 ... i.e. the loop body)
r13 copy -> memcmp     48 blocks
r13 copy -> synthesis  61 blocks
```

## The comparison operand is the synthesis output

The memcmp at `0x1e0dad2` compares `r1 = sp+1080`, length `0x0e`, against the last-sent mirror at
`0x4ecc`. `sp+1080` is exactly the buffer written by the copy at `0x1e0cd2e`, the mask stores at
`0x1e0cef8`/`0x1e0cf00` and the trigger byte stores at `0x1e0cec6`/`0x1e0ceec`. Same frame, same
address: the compared state *is* the trigger synthesis output.

## Answers

* **Can an analogue trigger movement change internal state without causing a report?** YES. The
  candidate buffer is written every pass that reaches the synthesis or the copy; emission
  additionally needs `b[r15+0x10] != 0`, a memcmp difference, the periodic tick gate and the
  repeat counter. That is exactly the change-gating the live captures show.
* **Does the synthesis happen before the compared state?** On the concrete path yes. Globally it
  cannot be stated as dominance because both orders are reachable across iterations.
* **Is the edge/toggle path necessary for an emitted change?** **NO.** The analogue copy writes
  `candidate+0x0c/+0x0d`, so the memcmp can observe an analogue change without the toggle path.
  The toggle path produces the `0x00`/`0xFF` digital form: sufficient, not necessary. This is the
  direct answer to the RT-only question.

## Not proven

* a per-iteration ordering guarantee (needs a single-pass slice with post-dominators);
* which pass the send gate fires on;
* whether any arm between the synthesis and the memcmp rewrites `sp+1080`.

## Corrections preserved

* `r5 & r4` is an **intersection** of `[r15+0x1d0]` and the current candidate mask - not a
  changed-bit mask.
* `0x1e094de` is a deadzone/direction classifier - not the normalized-record producer.
