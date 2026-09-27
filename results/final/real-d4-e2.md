# Real D4 / E2 (and 0B / EF) on the physical unit

## 0B — link-health / version query

| direction | frame | notes |
|---|---|---|
| TX | `a5 04 0b b4` | `A5 04 0B B4` |
| RX | `a5 05 0b 30 e5` | consistent across every session today |

`0B` is the workhorse liveness check: it is sent after any no-reply so that "no reply" can never
be silently read as "the device rejected the frame".

## D4 — mode query

| direction | frame | evidence |
|---|---|---|
| TX | `a5 04 d4 7d` | PROVEN LIVE (matches the brief exactly) |
| RX | `a5 07 d4 11 01 00 92` | **PROVEN LIVE** — recorded in two independent sessions |

Decoding the captured reply with the documented layout (byte 3 = gamepad mode, byte 4 = onboard
mode): frame length `0x07`, opcode `D4`, payload `11 01 00`, checksum `92` (valid sum8).

### CONFLICT — recorded

The working brief states the existing REAL D4 result is `A5 06 D4 00 00 7F` with
`gamepad_mode = 0` and `onboard_mode = 0`. **The captures on disk do not contain that frame.**
Every D4 reply recorded for this unit is `a5 07 d4 11 01 00 92` (2 occurrences, two sessions).

Status of the two readings:

| reading | status |
|---|---|
| `A5 07 D4 11 01 00 92` (`11`/`01`/`00`) | **PROVEN LIVE** — this is what the real unit returned |
| `A5 06 D4 00 00 7F` (`00`/`00`) | **CONTRADICTED by the captures on disk** — it matches the *expected shape* rather than the observed bytes; its origin is not identifiable in this repo's captures |

Neither value has been quietly adopted over the other. A read-only D4 re-query on the next live
connection settles it (the query is non-mutating), and the result will be appended here.

## E2 — firmware / model read

| direction | frame | notes |
|---|---|---|
| TX | `a5 04 e2 8b` | present on 4.0.8; **absent** on 2.22 / 2.23 / 2.24 |
| RX | `a5 10 e2 27 41 02 5a 4a 2d 58 54 00 00 00 00 7e` | PROVEN LIVE |

**Firmware is BCD, not ASCII:** payload begins `0x27 0x41` = `2741`, followed by a `0x02` byte
(semantics **UNKNOWN** — it is *not* a name length, since the name that follows is 5 bytes) and
then the ASCII model `ZJ-XT`. This was established from the live bytes and is locked in by
`tests/test_real_device_vectors.py`.

## EF — identity/UUID flow

| direction | frame |
|---|---|
| RX | `a5 0c ef bb 92 15 42 f2 1f 55 80 2a` |

8 payload bytes preserved raw; no field semantics are asserted beyond the framing (the brief
requires raw preservation and evidence-backed decoding only).
