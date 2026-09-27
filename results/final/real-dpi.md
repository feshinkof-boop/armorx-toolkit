# Real DPI (READ-ONLY status)

## Query frames and real replies (PROVEN LIVE)

| direction | frame | note |
|---|---|---|
| TX | `a5 05 fc 80 26` | normal DPI query — matches the brief exactly |
| RX | `a5 05 ff fc a5` | valid checksum |
| TX | `a5 05 05 25 da` and `a5 05 05 26 db` | AB motion/gyro queries |
| RX | **(none)** | see below |

## Motion/gyro: no reply, link proven healthy

The `AB 05 05 25 / 26` queries returned nothing while the link was demonstrably alive (an
immediately following `0B` was answered `a5 05 0b 30 e5`). Classified as:

**PROVEN LIVE — NO REPLY ON TESTED REAL FIRMWARE.**

They are **not** retried continuously, per the brief.

## What is NOT claimed

- **No numeric DPI value is assigned.** The selector mapping is not established from evidence, so
  no "current DPI = N" statement is made. Assigning one would be a guess.
- **No DPI write has been performed.** Anything mutating would require: the original selector
  recovered, a same-value no-op write proven, then at most one reversible adjacent-value test,
  followed by restoration. None of that has happened, and it is not scheduled while the unit's
  input-reporting state is unresolved.

## Next safe step

Re-read the `FC 80` reply on the next live connection and compare with `a5 05 ff fc a5`, then
look for the selector semantics in the 4.0.8 Dart AOT image (static) before any write is even
considered — tool-first, and only with a recovery path established.
