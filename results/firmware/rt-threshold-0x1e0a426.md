# 0x1e0a426 fully reversed (2026-09-29)

Status: **PROVEN STATIC**. Not hardware validated. One caller in the image.

## Signature

```text
r0  channel/index byte (the caller passes 1)
r1  current reading (the candidate RT byte)
r4  base pointer supplied by the caller
```

The function addresses a per-channel state block at `base + index` and returns
`0xFF` or `0x00`.

## Per-channel state

| offset | meaning |
| --- | --- |
| `+0x76` | previous reading, updated unconditionally |
| `+0x78` | mode byte (0, 1 or other) |
| `+0x7a` | hysteresis counter |
| `+0x7c` | armed byte - the return value is derived from this |

## Behaviour

* current < previous, mode 0: mode := 1, clear armed; set armed only when the drop is >= `0x1f` (31).
* current < previous, mode non-zero: counter++; after 3 consecutive decreases clear armed.
* current > previous, mode 1: mode := 0, clear armed.
* current > previous otherwise: counter++; with a rise >= `0x1e` (30) relative to previous, clear armed after
  5 consecutive increases.
* current == previous: arm.
* previous := current, then return `0xFF` if armed, else `0x00`.

## Why it matters

The byte this returns is written by the caller straight into the candidate RT byte
(`sp+1093`) and drives mask bit `0x200` from the same non-zero test. When this path
runs, the RT byte in a D2 frame is the **armed decision**, not the analogue reading.
That is a candidate explanation both for the observed RT values `0, 17, 27, 96, 255`
and for why an analogue-only change need not look like the same event.

## Open

* LT is set to `0xff` directly by the synthesis block; whether it ever uses this
  helper is unproven - this function has a single caller in this image.
* The mode byte's meaning beyond its 0/1 role, and the caller context that supplies
  `r4`, are not resolved.
