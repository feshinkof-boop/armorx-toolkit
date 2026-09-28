# F7 getStepLength read probe — live, read-only

**Date:** 2026-09-28, 07:47:46–07:48:02 local · **Branch** `research/physical-armorx-live-2026-09-27`
**Starting HEAD** `c36d71a` (274 tests) · **Operator ACK** `armorx_f7_read_power_on` @ 07:46:25
**Device** ARMOR-X Pro `2D:37:35:6D:66:11`, rssi −86 at scan
**Adapter** resolved **by identity**: hci1 = `E8:4E:06:8A:F2:00` (USB `0bda:b720`); `wlp3s0` stayed up

## Verdict

# `F7_NO_REPLY_LINK_HEALTHY`

Two identical `A5 04 F7 A0` requests produced **zero notifications of any kind** (3 s and 5 s windows),
while the `0B` sanity control answered **before, between and after** both attempts and the FC DPI
positive control passed **both** before and after — every reply arriving in **23–30 ms**.

**This is NOT `F7_WRITE_ONLY`.** The brief's classification correction is adopted verbatim: an
application that emits a `getStepLength` request can be silent for many reasons beyond write-only —
no protocol reply on this model, state returned asynchronously elsewhere, an unidentified generic
acknowledgement, a firmware/model gate, a timing/state requirement, or acceptance without an explicit
payload. Silence alone proves none of these, so none is claimed.

## Frames sent (all read-only — nothing else exists in the runner)

| # | frame | what it is | reply | latency |
|---|---|---|---|---|
| 1 | `A5 04 0B B4` | `0B` sanity control (phase A) | `A5 05 0B 30 E5` | **0.023 s** |
| 2 | `A5 05 FC 80 26` | FC DPI read (phase B, positive control, live-proven) | `A5 05 FF FC A5` | **0.030 s** |
| 3 | `A5 04 F7 A0` | **F7 getStepLength, attempt 1 (phase C, 3 s window)** | **none** | — |
| 4 | `A5 04 0B B4` | `0B` health (phase D) | `A5 05 0B 30 E5` | **0.026 s** |
| 5 | `A5 04 F7 A0` | **F7 getStepLength, attempt 2 (phase E, 5 s window)** | **none** | — |
| 6 | `A5 04 0B B4` | `0B` health (phase F) | `A5 05 0B 30 E5` | **0.029 s** |
| 7 | `A5 05 FC 80 26` | FC DPI read (phase F, post-F7 control) | `A5 05 FF FC A5` | **0.030 s** |

The runner refuses any frame outside the allow-list of those three, and checks each frame's own
sum8 trailer before transmitting. **No write was sent**: no `A5 07/08 F7 …`, no FC/F6 selector write,
no D6/D7/D8, no D2, no lighting, no macro traffic.

## Every notification received (unfiltered — all five)

| t (s) | phase | frame | after its TX |
|---|---|---|---|
| 6.522 | A | `A5 05 0B 30 E5` | +0.023 s |
| 6.553 | B | `A5 05 FF FC A5` | +0.030 s |
| 9.582 | D | `A5 05 0B 30 E5` | +0.026 s |
| 15.614 | F | `A5 05 0B 30 E5` | +0.029 s |
| 15.644 | F | `A5 05 FF FC A5` | +0.030 s |

Recorded **without opcode filtering** (the brief's requirement): the F7 windows contain nothing at
all — not an `F7` reply, not an `FF` envelope, not a shared acknowledgement, not a late frame. The
`0B` health check that follows attempt 1 reported `other_frames: []`, i.e. no delayed F7 frame
appeared even after the next control.

## HCI coverage (verified after stopping the capture, via `btmon -r`)

One capture, started **before** connecting, never restarted (the proven rule). Decoded timeline:

| HCI write on `0x0075` | value | HCI notification on `0x0077` |
|---|---|---|
| #74 | `a5040bb4` | `a5050b30e5` (+19 ms) |
| #80 | `a505fc8026` | `a505fffca5` (+30 ms) |
| #83 | **`a504f7a0`** | **none** |
| #85 | `a5040bb4` | `a5050b30e5` (+26 ms) |
| #88 | **`a504f7a0`** | **none** |
| #90 | `a5040bb4` | `a5050b30e5` (+29 ms) |
| #93 | `a505fc8026` | `a505fffca5` (+30 ms) |

Coverage confirmed: **1** connection complete, CCCD write `0100` on `0x0077`, **7** ATT Write
Commands on `0x0075` (exactly the seven above — no more, no fewer), **5** notifications, **1**
disconnect complete. The 6th `0x0077` decode line is the CCCD subscription, not a notification.
Harness timestamps and HCI timestamps agree frame-for-frame; the capture is **not** empty (4,877
bytes; `tshark` is known unreliable on these files and was not used for the verdict).

## Static cross-check against the real result (as required if a response appeared)

No response appeared, so there is nothing to match. For the record, across all four builds there is
**exactly one** comparison against the value `0xF7` (`cmp w0, #0x1ee`), at
`widgets/configV280/config_simulate_command.dart` 0xab9614, inside
`[closure] void _handleConfigEvent(dynamic, List<int>)` — the *simulate-command* page. What that
closure's argument is (an inbound wire opcode, or a UI/command-registry value) is **not established**;
it is therefore reported as the only `0xF7` comparison, not as an F7 reply parser. No other `F7`
handling exists in 2.22.0901, 2.23.0609, 2.24.0919 or 4.0.8.

## Config integrity (read-only)

`sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **`CONFIG_BASELINE_MATCH`**.
This is an integrity readback only — **not** a new durability proof. Historical durability state
remains `DURABLE_OK`.

## Evidence grades after this run

| claim | grade |
|---|---|
| `getStepLength` request exists in the app and is `A5 04 F7 A0` | PROVEN STATIC |
| that exact frame was transmitted to real hardware | **PROVEN LIVE TX** |
| observable response on this tested unit/firmware | **NO_REPLY_LINK_HEALTHY** |
| F7 write-only | **NOT CLAIMED** (silence cannot establish it) |
| F7 = stick step-length / "step accuracy" | PROVEN STATIC (unchanged) |
| F7 = trigger travel | **CONTRADICTED** (dated provenance preserved) |

## Artifacts

`session.jsonl` (every event, timestamped), `notifications.json` (all 5 raw frames + deltas),
`tx.json` (all 7 writes), `analysis.json` (phases + verdict), `btmon.btsnoop` + `btmon.txt` (HCI),
`post-integrity-d6/` (D6 read), `RESULT.md` (this file).
Runner: `automation/scripts/f7-read-probe.py`.

## What would legitimately come next (no write yet)

Per the brief: before proposing any write experiment, do the offline work — determine how the
application is supposed to *obtain* the setting given that no reply is observable. Concretely: the
`_handleConfigEvent` path in `config_simulate_command.dart` and the `_requestStepLength` /
`_scheduleStepLengthRead` helpers suggest the app may expect the value from device-initiated config
events rather than as a reply to `A5 04 F7 A0`. Chasing that statically is the correct next step; a
same-value/reversible write is **not** justified yet.
