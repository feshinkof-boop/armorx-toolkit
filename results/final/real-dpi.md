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

---

## DATED CORRECTION — 2026-09-27/28 (overnight shift): the motion query frames were mistranscribed

The two motion/gyro queries above are recorded as `a5 05 05 25 da` / `a5 05 05 26 db`. **Both fail
their own checksum** (sum8 of the leading bytes is `0xD4` / `0xD5`, not `0xDA` / `0xDB`). The
checksum-valid frames — and the ones the lab's own encoder produces (`build_ab(0x05,0x25)`) — are:

| corrected | checksum |
|---|---|
| `AB 05 05 25 DA` | `AB+05+05+25 = 0xDA` = trailer ✔ |
| `AB 05 05 26 DB` | `AB+05+05+26 = 0xDB` = trailer ✔ |

So the motion family is the **`AB` (`0xAB`) header family**, not `A5`, and the queries above should be
read as `AB ...`. The observation those rows carry (motion queries returned **no reply** while the link
was live, and the `FC 80` DPI query did answer `a5 05 ff fc a5`) is unaffected and still PROVEN LIVE.
This is a transcription fix, not a new experiment.
