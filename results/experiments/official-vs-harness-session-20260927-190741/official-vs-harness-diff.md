# Official app vs Linux harness — session differential (COMPLETE)

**Overall status: COMPLETE.** The official BIGBIG WON 4.0.8 session was captured on the real phone
(Android HCI snoop, extracted via bugreport) and compared stage-by-stage with the preserved Linux
harness session.

## Result

**`OFFICIAL_WORKS_HARNESS_SILENT`** — the official app's Button Test produces valid `A5 12 02`
frames on this unit, while the Linux harness received none. The D2 command itself is **identical**
in both, so the difference is not the D2 protocol.

## CONNECTION

| field | official (Android) | harness (Linux) | same? |
|---|---|---|---|
| role | Central | Central | ✅ |
| peer address type | Public | Public | ✅ |
| connection interval | **11.25 ms** (history 30 → 7.5 → 30 → 11.25) | **7.50 ms** (1 update) | ❌ **OFFICIAL_CONNECTION_INTERVAL_DIFFERENT** |
| peripheral latency | 0 | 0 | ✅ |
| supervision timeout | 2000 ms (after 5 s) | 2000 ms | ✅ |
| PHY | no PHY update events | not reported | – |

## SECURITY

| field | official | harness | same? |
|---|---|---|---|
| bonded | **no** (ArmorX absent from the phone's 8 bonded devices) | no | ✅ |
| encrypted | **no** (0 SMP frames, 0 encryption-change events) | no | ✅ |

→ **D2-U-008 REFUTED**: the official app streams on an unbonded, unencrypted link, exactly like ours.

## ATT / GATT

| field | official | harness | same? |
|---|---|---|---|
| ATT MTU | 64 (after Android's default 23 exchange, then 512→64) | 64 | ✅ |
| CCCD | Write Request, handle `0x0078`, +1.34 s | handle `0x0078` = `0100` | ✅ |
| FFE1 / FFE2 / CCCD handles | `0x0075` / `0x0077` / `0x0078` | `0x0075` / `0x0077` / `0x0078` | ✅ |

## APPLICATION SEQUENCE (this is where they differ)

```text
official:  connect -> MTU(23) -> MTU(512->64) -> CCCD 0x0078 -> [58 s idle]
           -> EF  a50cef0000000000000000a0   -> reply a50cefbb921542f21f55802a
           -> 0B  a5040bb4                   -> reply a5050b30e5
           -> E2  a504e28b                   -> reply a510e22741025a4a2d5854000000007e
           -> D4  a504d47d                   -> reply a507d411010092
           -> D6  a504d67f                   -> 8 reply fragments a414d6NN.. (full config read)
           -> D2 enable a505d2017d           (Write Command 0x52, handle 0x0075) -> echo x2

harness:   connect -> MTU(512->64) -> CCCD 0x0078 -> 0B a5040bb4 -> D2 OFF a505d2007c -> D2 enable a505d2017d
```

→ **`EXTRA_OFFICIAL_WRITE_OBSERVED`**: the app performs a device-info + **full configuration read**
(EF, E2, D4, D6) before D2 that our harness never sends. The harness also pre-clears D2 OFF, which
the app does not. **Neither is labelled `MISSING_PRECONDITION`** — causality is not established.

## D2 ITSELF — identical

| field | official | harness |
|---|---|---|
| value | `a505d2017d` | `a505d2017d` |
| ATT op | **Write Command (0x52)** | **Write Command (0x52)** |
| handle | `0x0075` | `0x0075` |
| response | 5-byte echo ×2 | 5-byte echo |
| disable | `a505d2007c`, Write Command, +129.5 s | `a505d2007c`, Write Command |

## RX

| field | official | harness |
|---|---|---|
| idle `A5 12 02` frames | **0** | 0 |
| frames with A pressed | **155** | 0 |
| first frame after enable | +36.36 s (when A was first pressed) | – |
| event-driven | yes | (untested with a press in that session) |

The official app produces **zero** frames while nothing is pressed — the stream is event-driven.
The harness's historical `0 idle frames` was therefore never evidence of failure by itself.

A-button proof (official session, bit index 0 = A):

```text
PRESS   mask 00000001  t=+104.86 s
RELEASE mask 00000000  +0.225 s
PRESS   mask 00000001  +1.068 s
RELEASE mask 00000000  +1.305 s
```
18-byte frames, valid checksums, only bit 0 ever set, ~12 ms repeat cadence while held.

## Earliest proven material difference

**`OFFICIAL_CONNECTION_INTERVAL_DIFFERENT`** — official final interval **11.25 ms** after four
link-layer updates vs the harness's **7.50 ms** after one; it occurs in the first seconds, before
every other difference. Causality: **not established**.

The first *protocol-level* difference is the pre-D2 config/status read burst
(`EXTRA_OFFICIAL_WRITE_OBSERVED`), ~9 s before the D2 enable.

No unknown official traffic was replayed from Linux.
