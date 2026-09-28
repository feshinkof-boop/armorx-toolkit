# ArmorX D2 trigger path (V41, static)

**The D2 frame is emitted when the 14-byte input payload changes.**

`0x1e0dad2`: `r0 = r12 + 0x8c` (with `r12 = 0x4e40`, so the input state is at **`0x4ecc`**),
`r1 = sp + 1080`, `r2 = 0x0e`, `call 0x2f92fa` (compare). If equal the report block is skipped
(`goto 0x1e0db1c`); if different, 28 bytes are copied and `b[r15+0x3a] = 0x64` arms the repeat counter.

## D2_SEND_IF

```
emit(A5 12 02, 14-byte payload)  IFF  b[state+0x10] != 0  AND  memcmp(state14 @ 0x4ecc, previous14) != 0
```

Plus a periodic gate `(tick - [state+0x18c]) >= h[r9+0x12]` and, after a change, up to 100 repeat sends
driven by the counter at `state+0x3a`.

## Zero idle frames - explained

The report is not free-running. The memcmp at `0x1e0dad2` suppresses it whenever the 14-byte state is
unchanged, which is exactly the idle case.

## RT no-self-trigger - NOT explained, and here is why

The compared region is 14 bytes = mask u32 + 4 axes + **LT + RT**, so an RT analogue change *should*
trip the same gate that fires reports. That contradicts the live observation. Either the RT byte at
`0x4ecc+0x0e` is only refreshed under a digital-event condition, or the compared buffer is a filtered
state. Untested - so RT is left open rather than declared explained.

## state+0x1b4

`0x1e0da8e` writes **2**, the record writer writes **3**. It is a **mode/state selector**, not a dirty
flag; the earlier terminology is retired.

## Structure note

`0x1e0aff2` (previously reported as a 13,346-byte function) has **no prologue**: it is a label inside
`0x1e0ac14`, which is the periodic tick body that also drains the A5 command queue into the dispatcher
`0x1e08772`. The entry thunk `0x1e0ef36` has **no in-image caller**, so the event source is registered
with the library rather than called from the app.
