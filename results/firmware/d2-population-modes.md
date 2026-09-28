# D2 candidate population modes (V41, static)

r13 at the 28-byte copy is **not** a raw register: it is `[sp+24]`, assigned at `0x1e0baa0`.
The copy source is a structure referenced by that stack slot.

* `0x1e0baa0: r13 = [sp+24]` then `0x1e0cd2c: r1 = r13` -> 28-byte copy into the candidate
* the sibling block does `0x1e0e374: r1 = r13 & 0xffffff`, `0x1e0e37e: r13 = [sp+24]` and then `r13 |= r0` with bits 8/9 extracted as the LT/RT seeds
* so the value is address + tag, and the tag byte's nibbles are the injector mode ids (`r2 = r0 >> 0x18`)

## CFG verdict

The four mechanisms are **not** a proven sequential timeline. Each sits in its own block with its own entry
condition - the copy is gated at `0x1e0cd1e` by `b[r8+0x20] | b[state+0x10]`. **No field-precedence claim is
made** until a reachability walk of the 13,346-byte container is complete.

## Side findings

* `0x1e0cd3a: call 0x1e0a114(r0 = r8+0x1d6, r1 = candidate+0x0c)` - the LT/RT pair is passed as a pointer,
  so a consumer treats `+0x0c..` as an array.
* **F6 evidence**: `0x1e0ccb4`/`0x1e0cce4` emit opcode `0xf6` with a **1-byte payload 0x00 or 0x01**; the state machine
  at `0x1e0cc90` tests `r0 == 2` / `r0 != 1`, the arm compares two timer reads (`0x1f9b64`, `0x1f9b34`) and emits
  only when the delta is `>= 0x51` (81). `state+0x37` tracks it. No time unit is claimed for 0x51.
