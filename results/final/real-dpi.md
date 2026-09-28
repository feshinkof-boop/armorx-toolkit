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


---

## DATED ADDENDUM — 2026-09-28T07:05:00-04:00 (static-only pass): FC's three roles, the F6 gate, and the writer

Nothing below was sent to hardware; the three wire frames that hardware *has* already answered are
reproduced exactly by `automation/scripts/frame-literal-scan.py`, which is the validation of the method.

| finding | evidence | grade |
|---|---|---|
| `FC 80` is the **default read request** built by `BluetoothModel::getDpi` @0x8b4e3c = `A5 05 FC 80 26` | matches the captured live TX byte-for-byte | PROVEN STATIC + PROVEN LIVE |
| the reply to it is `A5 05 FF FC A5`: opcode `0xFF`, byte[3] echoes the queried opcode, and the frame has **zero payload** | live capture | PROVEN LIVE |
| `getDpi` holds **three** wire variants selected by device-model + firmware version | `A5 05 FC 80 26` (default) / `A5 05 F6 80 20` (model set A, version >= 0x35) / `A5 04 F6 9F` (model set B, version >= 0x36) | PROVEN STATIC |
| the DPI **writer** is `writeDpiConfig` @0x946750 → `A5 05 FC|F6 <selector & 0x0F> <cks>` | 5-byte frame; selector masked to 4 bits; `F6` replaces `FC` under the same version gate; finished by `BluetoothModel::write` | PROVEN STATIC |
| `FC` has a **third, unrelated role**: macro transcription control | `startTranscribe` → `A5 0B FC 01`, `stopTranscribe` → `A5 0B FC 00` — the **static prefix of an 11-byte frame** whose remaining 8 bytes are a runtime payload; length byte `0x0B`, a different feature entirely | PROVEN STATIC |
| no bound check beyond `& 0x0F`; no numeric DPI value in the binary | exhaustive read of both builders | PROVEN STATIC (negative) |
| is it stick DPI or mouse DPI? | **still UNKNOWN** — the frame carries only a selector; the app has both 鼠标灵敏度 (mouse sensitivity) and 摇杆/视角 (stick/view) strings, and the selector table is server-side | UNKNOWN |

A **fourth** `FC` occurrence, `getMaxSize` (`A5 04 D3` family context), was **not** resolved in this
pass and is not claimed.

Chained-read observation: the notification handler closure at `rainbow_more.dart` 0x8b3b40 calls
`getDpi()` and then `getStepLength()` on the same code path — i.e. the official workflow is a
**read sequence**, not a single query. The exact received opcode that triggers the pair is not yet
pinned (recorded in the callgraph's pinned unknowns).
