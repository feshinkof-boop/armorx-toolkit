# F7 — "trigger travel" reconstruction (and why the trigger hypothesis is REFUTED)

**Date:** 2026-09-28 · static only, no hardware touched · branch `research/physical-armorx-live-2026-09-27`
**Method:** Blutter Dart-AOT disassembly of all four builds + `automation/scripts/frame-literal-scan.py`
(a new tool that reconstructs wire frames from `List<int>` literals and computes their trailers).
**Evidence priority applied:** wire/static dataflow > UI semantics > name inference.

## Headline

`F7` is **not** a trigger-travel command. It is the **stick step-length / "step accuracy"** setting:

| fact | evidence | grade |
|---|---|---|
| opcode `F7` is the read request built by `BluetoothModel::getStepLength` @**0x8b4d30** (4.0.8) | the frame literal `A5 04 F7 A0` is constructed in that function and handed to `BluetoothModel::write` | PROVEN STATIC |
| the write is `writeStepLengthConfig` @**0x9445d4** | frame built there, then `Provider.of<BluetoothModel>().write(frame)` | PROVEN STATIC |
| the feature's UI strings are `step_accuracy_setting` / `step_accuracy_chose` | in the 4.0.8 localization tables | PROVEN STATIC |
| those strings read 「步长精度设置」 / 「Step accuracy setting」 | zh + en message tables | PROVEN STATIC |
| the tip text 「步长精度影响**摇杆**的精确度」 says the setting affects the **stick** (摇杆), not the trigger | zh message text | PROVEN STATIC |
| **"F7 = trigger travel"** | contradicted by the above: no trigger string, no trigger enum, no D2-trigger code path is connected to F7 | **CONTRADICTED** |

The brief's hypothesis (F7 ∈ {travel, threshold, actuation, range, calibration, deadzone, trigger mode})
is therefore answered **"none of these"** for the build that is actually installed on the live unit.
Trigger vocabulary *does* exist in the app (扳机 trigger, 左/右扳机死区 left/right trigger deadzone,
快速扳机 fast trigger, 扳机智能锁 trigger smart lock) — it simply is **not** behind `F7`.

## Wire forms

| form | bytes | where | grade |
|---|---|---|---|
| read request | `A5 04 F7 A0` | `getStepLength` @0x8b4d30; trailer = `A5+04+F7 = 0x1A0 → 0xA0` | PROVEN STATIC |
| write | `A5 07\|08 F7 <flag 00\|01> <value_lo> <value_hi> [<extra>] <cks>` | `writeStepLengthConfig` @0x9445d4 | PROVEN STATIC (layout) |

Write-field detail, from the disassembly:

| byte | source | meaning | grade |
|---|---|---|---|
| [0] | literal | `0xA5` header | PROVEN STATIC |
| [1] | `NN = ((arg & 2) + 14) / 2` → **7 or 8** | total frame length | PROVEN STATIC |
| [2] | literal | `0xF7` | PROVEN STATIC |
| [3] | `(bool ? 1 : 0)` | boolean flag written as `00`/`01` | PROVEN STATIC |
| [4] | `value & 0xFF` | low byte of a 16-bit value | PROVEN STATIC |
| [5] | `value >> 8` | high byte (little-endian pair) | PROVEN STATIC |
| [6] | — | present only in the length-8 form | UNKNOWN |
| last | `getCheckSum()` | `sum8` of the preceding bytes | PROVEN STATIC |

Call sites require **firmware version `>= 0x36`** (`cmp x3, #0x36 ; b.lt` against the static version
field `0xb6c`); below that the call is skipped entirely.

## Units, bounds, defaults, scope

| question | answer | grade |
|---|---|---|
| units | **UNKNOWN**. The value is a 16-bit little-endian quantity; no scale factor, no unit string and no bounds check exist in the binary near the builder. The UI strings do not state units. | UNKNOWN |
| min/max | no clamp or validation found in the builder beyond the 16-bit split | UNKNOWN |
| default | not present in the binary (the value is a model field, `field_3b` of the device/config object, not a literal) | UNKNOWN |
| per-stick / per-profile / global | **not established.** No per-stick index byte is present in the frame; the only structural variable is the boolean flag. | UNKNOWN |
| signed/unsigned | unsigned (bytes split by `>> 8` and `& 0xFF`, no sign handling) | INFERRED |

## Cross-version

| build | `F7` | notes |
|---|---|---|
| 2.22.0901 | **ABSENT** | exhaustive scan of `asm/moojiang`: zero F7/F6/FC frame literals |
| 2.23.0609 | **ABSENT** | FC-only DPI era |
| 2.24.0919 | present | first appearance, same frame shapes as 4.0.8 |
| 4.0.8 | present | installed build; addresses above |

## Relationship to D2 analog triggers — none found (Part 11)

Live D2 analog facts (RT byte `[16]`, LT byte `[15]`, both `0..255`) were compared against everything
F7 touches. Result: **no connection exists in the binary.** `getStepLength`/`writeStepLengthConfig` do
not read or write any trigger field, do not reference the D2 frame contract, and contain no
`clamp`/`scale`/`normalize`/`threshold`/piecewise code. There is no static formula linking F7 to the
reported D2 trigger bytes, and therefore **no claim is made that F7 transforms trigger input, the
reported D2 values, the actuation threshold, deadzone or range**. They are separate subsystems.

## What would settle the remaining unknowns (static first)

1. Resolve the pool objects behind the `step_accuracy_setting` UI widget to confirm the *slider range*
   rendered to the user — that gives the value's practical min/max (needs resolving the `field_3b`
   source, not a label).
2. Find the reply parser for the `F7` read (`0xFF` family, likely `A5 05 FF F7 …`) — whether the reply
   carries the current value at all.
3. Diff the 2.24 vs 4.0.8 `writeStepLengthConfig` bodies to see if the value width or the flag meaning
   changed (they currently look identical in shape).

## Safety note

No F7 frame has ever been sent to real hardware. If a future session proposes to, it must first
establish a read-back path, and must not assume the value is a trigger parameter.


---

## DATED ADDENDUM — 2026-09-28T07:48:30-04:00 (LIVE, read-only): the F7 read produces no observable reply

`A5 04 F7 A0` (the application's own `getStepLength` request) was sent **twice** to the live unit.
**Zero notifications of any kind** followed, in a 3 s and then a 5 s window with no opcode filtering.

The link and the request/notification path were healthy throughout, proven by controls:
`A5 04 0B B4` → `A5 05 0B 30 E5` **before, between and after** the two attempts, and the FC positive
control `A5 05 FC 80 26` → `A5 05 FF FC A5` **before and after** — every reply in 23-30 ms.
HCI (`btmon -r`) confirms 7 writes and 5 notifications, with the two `A5 04 F7 A0` writes followed by
**nothing**. D6 read-only integrity: `bdef9c61...` **CONFIG_BASELINE_MATCH**.

**Verdict: `F7_NO_REPLY_LINK_HEALTHY`.**

**F7 is NOT classified `F7_WRITE_ONLY`.** Silence is compatible with: no protocol reply on this model,
state delivered asynchronously elsewhere, an unidentified generic acknowledgement, a firmware/model
gate, a timing/state requirement, or acceptance without payload. None of those is claimed.
Across all four builds there is **exactly one** comparison against `0xF7` (`cmp w0, #0x1ee`, in
`config_simulate_command.dart` 0xab9614, inside the closure `_handleConfigEvent`); what its argument
is has not been established, and no other F7 handling exists anywhere.

Evidence: `results/experiments/f7-read-live-20260928-074652/` (`RESULT.md`, `analysis.json`,
`notifications.json`, `tx.json`, `session.jsonl`, `btmon.btsnoop`, `btmon.txt`).

---

## 2026-09-28 (F7 value-provenance pass, static-only, HEAD 0e59a66)

**Question answered: where does the app obtain the current F7 step-length value?** Full trace in `results/reconciliation/f7-value-provenance.md` (+ `.json`, `f7-dataflow.dot`).

- **ORIGIN = a device F7 *event* frame, ≥7 bytes, write-shaped** — not a short reply. The F7 handler requires `len>=7`, `frame[0]==0xA5`, `frame[2]==0xF7` and parses `value = ([5]<<8) | [4]` with the flag at `[3]` — the same layout as `writeStepLengthConfig` (`A5 07|08 F7 <flag> <lo> <hi> [extra] <cks>`).
- **The read is a trigger, not a request-reply pair.** `getStepLength` (0x8b4d30) only builds `A5 04 F7 <cks>` and writes it: no await, no callback, no pending flag, no version gate. The expectation lives in the page: `_requestStepLength` (0xa6e320) sends the read **up to 3 times** with delays between attempts and **breaks when state `field_23` becomes non-null**; the handler's follow-up closure (0xab9764) sets exactly that field.
- **Inbound path is generic:** `BluetoothModel.notifyCharacteristicStream` (0x826814) = `_BroadcastStream<List<int>>` over an `AsyncBroadcastStreamController` (`field_43`), fed by the notify callback (0xacb7f8). Consumers: 0 files (2.22/2.23) → 15 (2.24) → 2 (4.0.8). The generic `A5 05 FF <opcode> <cks>` envelope is **not** the F7 carrier.
- **No local/cloud/D6 source exists** for the value (`step_accuracy`/`stepLength`: 24/27 AOT hits, **0 in app assets**), and **`F7_NOT_D6_GOVERNED_STATICALLY_OBSERVED`** (STRONG EVIDENCE).
- **Live silence, ranked:** (1) a device event is expected and never arrived; (2) the read expects no reply on this model; (3) a state/page gate was missing — the earlier probe sent **2 of the app's 3 attempts** and omitted the handshake ordering. A corrected READ-ONLY probe (3 attempts + ≥10 s listening tail + app handshake first) is **justified but not run**.
- **`WRITE_TEST_NOT_YET_SAFE`** — no reliable restoration value exists (no readback, no proven event; `field_23` is filled only by that same missing event).
- **No hardware was touched in this pass**; the F7 = trigger-travel hypothesis remains **CONTRADICTED** and its provenance is preserved above.
