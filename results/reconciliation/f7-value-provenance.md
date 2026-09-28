# F7 — step-length / step-accuracy value provenance (offline, static)

**Generated** 2026-09-28 · **Branch** `research/physical-armorx-live-2026-09-27` · **Starting HEAD** `0e59a66`
**Scope:** where the application actually obtains the current F7 value. **No hardware was touched**: no scan, no connection, no popup, no ADB, no write, no F7 sent.

Canonical: **F7 = stick step-length / "step accuracy"** (`step_accuracy_setting` = 「步长精度设置」, tip 「步长精度影响**摇杆**的精确度」 — affects the **stick**). The old *F7 = trigger travel* hypothesis stays **CONTRADICTED**.

---

## 1. The lifecycle, with code evidence

| stage | answer | address evidence | grade |
|---|---|---|---|
| **ORIGIN** | a **device F7 event frame**, ≥7 bytes, write-shaped | `_handleConfigEvent` requires `len>=7`, `frame[0]==0xA5`, `frame[2]==0xF7` (0xab9614); `value = (frame[5]<<8) \| frame[4]`, flag = `frame[3]` | STRONG EVIDENCE |
| **STORAGE** | page state `field_23` | handler's follow-up closure stores it: `StoreField r3->field_23` @0xab97d8 | PROVEN STATIC |
| **REQUEST** | `BluetoothModel.getStepLength` (0x8b4d30) → `A5 04 F7 A0`. Builds and **writes only** — no await, no callback, no pending flag, **no version gate** | literals 330/8/494 @L478-486; `getCheckSum` @0x8b4dac then write @0x8b4e18; no 0xb6c reference | PROVEN STATIC |
| **DELIVERY** | **event-driven, polled**: `_scheduleStepLengthRead` registers a closure on a static listener list → `_requestStepLength` sends the read **up to 3 times**, `Future.delayed` between attempts, and **breaks when `field_23` becomes non-null** | 0xa6e178 → closure @0xa6e2d8 → `_requestStepLength` 0xa6e320: `cmp x1,#3`, `getStepLength()` @0xa6e40c, `LoadField field_23` @0xa6e3fc | PROVEN STATIC |
| **UI STATE** | `_setKeyExchange` (0x95c578) reads `field_23` and passes it to the writer | `LoadField r2 = r1->field_23` @0x95c5e0 → `bl ::writeStepLengthConfig` @0x95c60c | STRONG EVIDENCE (the UI-edit step is INFERRED) |
| **WRITE** | `writeStepLengthConfig` (0x9445d4): `A5 <len> F7 <flag> <lo> <hi> [extra] <cks>`, `len = ((flag & 2) + 14) / 2` → 7 or 8, 16-bit LE, checksum `define::getCheckSum` | `and x3,x3,#2` @0x944610; `r16=330`/`r16=494` @0x94466c-0x94467c; value @0x944690; cks @0x94471c | PROVEN STATIC |
| **PERSISTENCE** | direct characteristic write (`BluetoothManager::write`) — **no D6/D7 commit** in the F7 path | same shape as the DPI writers | STRONG EVIDENCE (durability of a write is UNKNOWN) |

**The two layouts agree.** The parser reads the value at **[4] (low) / [5] (high)** with the flag at **[3]** — precisely the `writeStepLengthConfig` layout. So the frame the app waits for is **not a short reply but a write-shaped configuration event**.

## 2. Inbound dispatch (is there an F7 parser? does generic FF carry it?)

- **Yes, an F7 parser exists** — but it is a **per-page stream listener**, not a switch arm: `listen(_handleConfigEvent)` on `BluetoothModel.notifyCharacteristicStream`.
- The stream: `field_43` is an **`AsyncBroadcastStreamController`**; the getter (0x826814) wraps it as `_BroadcastStream<List<int>>`; the **notify callback (0xacb7f8) adds every non-empty payload** to it.
- Consumers: **0** files in 2.22.0901 / 2.23.0609 → **15** in 2.24.0919 → **2** in 4.0.8 (`armorx_pro_root.dart` for the handshake opcodes 0xA5/0x0B/0xEF; the definition itself). The architecture appeared with the F6/F7 command set in 2.24.
- The generic **`A5 05 FF <opcode> <cks>`** envelope (proven live for FC: `A5 05 FF FC A5`) is the model-agnostic reply form; **F7 does not use it**. So an F7 event would arrive through the *stream*, and a generic `FF F7` is **not** the expected carrier.

## 3. Device-initiated config events (Phase 6)

**None found in the evidence held**, and this is a bounded claim:
- 3 decoded btmon captures: **0** RX notifications without a TX within 2.0 s.
- The official app's own live session (`official-att.jsonl`, 250 ATT records, opcodes `{02:155, D2:6, EF:2, 0B:2, E2:2, D4:2, D6:1}`): **zero records containing `f7` at all**.
- Caveat, stated deliberately: that official session was a **D2/button** session — the app was not on the step-accuracy page, so its F7 absence is *expected* and is **not** evidence about F7 itself. It does establish the observed opcode set on the wire.

## 4. Value source, bounds, flag, scope

- **Source of the displayed value:** device event only. There is **no local, D6, profile, or cloud source**: `step_accuracy`/`stepLength` occur 24/27 times in the AOT image but **0 times in the app's assets** → no server/profile field (`SERVER_PROFILE_VALUE`: **NOT OBSERVED**), and `step_length`/`stepAccuracy` spellings do not exist.
- **Min / max / step / default / units:** **UNKNOWN**. No step-length-specific clamp or slider exists in `config_simulate_command.dart`; the only clamp there is `_clampPercentage` (0x95a304).
- **Flag:** controls the frame *length* (7 vs 8) ⇒ it is what selects the optional byte. Its feature meaning is **UNRESOLVED** (candidates: stick side, enable, precision class) — no UI string ties it yet. **Optional byte:** present only in the 8-byte form; source **UNKNOWN**.
- **Stick scope / profile scope:** **UNKNOWN** — no left/right or profile selector appears in the builder, the handler, or the writer. Only one F7 write per operation was observed.

## 5. D6 relationship (Phase 14)

**`F7_NOT_D6_GOVERNED_STATICALLY_OBSERVED`** — STRONG EVIDENCE. The F7 builder, handler and writer never reference a D6 offset or the config model, and the write terminates in a direct `BluetoothManager::write`, exactly like the DPI writers. No same-property/serializer/offset/conversion path ties F7 to D6. (No correlation-by-coincidence is claimed.)

## 6. Why did the live read return nothing? (Phase 15, ranked by evidence)

1. **B — an F7 *event* is expected that never arrived.** Strongest: the app designed a 3-attempt polling loop, waits for a ≥7-byte F7 frame, and stores it in `field_23`. The read is a *trigger for a later event*, not a request-reply pair.
2. **A — the read deliberately expects no reply on this model.** Consistent with silence, but does not explain the handler's existence.
3. **E — a state/page/mode gate was absent.** Supported by the probe gaps below.
4. **F — a generic path we failed to recognise.** Now weaker: the generic stream is understood, and no F7 frame appears in any capture.
5. **D — legacy/dead code on this device.** Unlikely: the page still schedules the read and registers the handler in 4.0.8.
6. **C — the value is already cached locally.** Refuted: no local source exists.
7. **G — unresolved.**

Ranking follows evidence strength only; no single explanation is forced.

## 7. Was the previous live probe missing anything? (Phase 16) — yes, three things

1. It sent **2 attempts**; the application's own loop caps at **3**.
2. Each attempt's window closed at 3 s / 5 s with **no listening tail** after the final attempt.
3. It did not reproduce the app's **handshake ordering** (identity reads `2A24`/`2A26` → `EF` → config `D6`) before the F7 read.

A **corrected READ-ONLY probe is justified** (and is *not* executed here): 3 attempts, a ≥10 s listening tail after the last one, and the app's handshake reproduced first. Given the controls answered in 23–30 ms, the tail is cheap.

## 8. Is a write test safe yet? (Phase 17) — **no**

**`WRITE_TEST_NOT_YET_SAFE`.** No reliable restoration value exists: there is no live readback, no proven device-generated event, and the app's own `field_23` is populated *only* by that same missing event. A hard-coded or default value is not acceptable. The Phase-18 reversible plan stays **prepared but unrun**, and its bytes are not derived here because the value `V` is unknown. Should an event path be established, the **Phase-19 passive experiment becomes the next physical task instead of a mutation**.

## 9. Cross-version matrix (Phase 12)

| | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|---|---|---|---|
| F7 present | absent | absent | present | present |
| read builder | — | — | yes | `getStepLength` 0x8b4d30 |
| write builder | — | — | yes | `writeStepLengthConfig` 0x9445d4 |
| inbound handler | — | — | yes | 0xab94fc / 0xab9614 |
| notification stream | absent | absent | present (15 consumers) | present (2 consumers) |
| UI page | — | — | step-accuracy page | `config_simulate_command` |
| value source | — | — | device event | device event |
| firmware gate | — | — | — | write ≥0x36 (static); read ungated |
| defaults / bounds | — | — | UNKNOWN | UNKNOWN |
| persistence | — | — | UNKNOWN | direct write, no commit |

The **arrival of the broadcast-stream architecture with F6/F7 in 2.24** is the point where this feature's design changed; before it there is no inbound config-event mechanism at all.
