# Key-ID closure session — result

**Date:** 2026-09-28, 06:01–06:07 local · **Branch** `research/physical-armorx-live-2026-09-27`

## Question

Which physical controls remain unmapped, and can any of the unresolved numeric ids
(`2, 5, 9, 21, 22, 31, 32, 33`) be attributed to a physical control?

## Phase 1 — the control list was derived before touching the device

Derived from what the operator was **actually asked to press** (`results/runtime/press-groups.jsonl`)
cross-referenced with the proven-live map — not from list order, and without the old erroneous +1 bit
reading (rule: **bit == id**). Sources: `control-inventory.{json,md}` in this directory.

- Distinct physical controls ever requested: **26** — LB, RB, LT, RT, View, Menu, L3, R3, D-pad
  Up/Down/Left/Right, Capture, Guide, M1–M7, other, A, B, X, Y.
- **Already PROVEN LIVE: 26 ids** (0, 1, 3, 4, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23,
  24, 25, 26, 27, 28, 29, 30) — **none of these was requested again.**
- **Requested but never proven: `RT` (one control).** Requested in press_group_B, D, E and F and in
  three dedicated retries; no frame ever carried bit 9.
- Physical controls **never requested at all**: the two analog sticks (their clicks, L3/R3, are separate
  and already proven).
- The app's own 4.0.8 label inventory is A B X Y LB RB LT RT L3 R3 Menu Select Start Capture Up Down
  Left Right M1–M7 NIL plus keyboard keys and ZL/ZR (Switch-mode). **No M8+ and no Turbo label exists**,
  so ids 2/5/21/22/31/32/33 have no label in the app either.

**Conclusion of Phase 1: exactly one physical control remained — RT — plus two analog-axis probes.**

## Phase 2 — setup

- Primary network protected: wlp3s0 UP on 192.168.0.45 with the default route.
- Lab adapter resolved **by identity**, not by assumed index: **hci1 = `E8:4E:06:8A:F2:00`**, USB
  `0bda:b720` at path `1-8` (hci0 = `0489:e10d`, a different controller, untouched).
- The unit was not advertising → **exactly ONE** power-on popup (`ArmorX Key Map`, DONE / CANCEL / STOP),
  ACKed **06:02:43**. No chat acknowledgement was used, no sound repeated.

## Tested controls

Sequence per control (the shorter proven-good form; the pre-clear is omitted because C0 already proved it
harmless): `discover → connect → identity → subscribe FFE2 → sanity 0B (reply required) → D2 ON →
ONE popup naming ONE control → observe → D2 OFF → disconnect`.

### Control 1 — RT

| metric | value |
|---|---|
| popup | `ArmorX Key Map — RT` ("Press RT fully TWICE … click DONE") |
| popup open | ~16.8 s; **ACKed at 06:05:49** |
| valid D2 frames | **0** |
| nonzero-mask frames | 0 |
| bits | none |
| transitions | none |
| analog `[15]` LT / `[16]` RT | **not sampleable** — no frame of any kind arrived |
| HCI corroboration | **yes** — the capture contains exactly 3 notifications for this run (sanity reply `a5 05 0b 30 e5`, D2-enable echo, D2-disable echo) and 3 Write Commands on `0x0075` |
| **classification** | **`RT_NO_REPORT_OBSERVED`** |

Two full pulls inside a window that stayed open long enough, with the link verified healthy at both ends
of it, produced **no frame at all**. Because the device emits nothing while only RT moves, the analog byte
`[16]` cannot be read by this method — so **`RT_ANALOG_ONLY` can neither be confirmed nor excluded**, and
no analog claim is made. ID 9 stays **unresolved / negative**.

The RT analog offset was verified *before* trusting it, as required: `results/reconciliation/d2-frame-contract.md`
states `[15]` = LT analog, `[16]` = RT analog, `[17]` = trailer, and LT was PROVEN LIVE to move `[15]`.

### Control 2 — L stick (bounded analog probe; never requested before)

| metric | value |
|---|---|
| popup | `ArmorX Key Map — L stick` ("Push the LEFT stick fully … TWICE … click DONE") |
| valid D2 frames | **0** |
| bits / transitions | none |
| HCI corroboration | yes — 3 notifications for the run, 3 Write Commands on `0x0075` |
| **classification** | **`STICK_NO_REPORT_OBSERVED`** |

### Control 3 — R stick — **deliberately not run**

The L-stick probe answered the question it was there to answer: **this device does not emit report frames
for analog-axis-only changes.** Running the R stick would have raised a second popup asking the operator to
repeat a measurement whose outcome is already determined by the same mechanism, so it was skipped and that
decision is recorded here rather than silently dropped. If a future session needs the axis values, the
method has to change (see "what would actually resolve it" below).

## Final classifications of the unresolved numeric ids

| id | classification | basis |
|---|---|---|
| 2 | `UNOBSERVED_RESERVED_OR_UNUSED` | no requested control maps to it; no label exists in any build; no frame ever carried bit 2 |
| 5 | `UNOBSERVED_RESERVED_OR_UNUSED` | same |
| **9** | **`PROVEN_NEGATIVE`** (as a digital bit) | requested 4× plus 3 retries plus this session's two full pulls; never appeared, and no frame at all arrived |
| 21 | `UNOBSERVED_RESERVED_OR_UNUSED` | no requested control maps to it; no label exists |
| 22 | `UNOBSERVED_RESERVED_OR_UNUSED` | same |
| 31 | `UNOBSERVED_RESERVED_OR_UNUSED` | same |
| 32 | `UNOBSERVED_RESERVED_OR_UNUSED` | same |
| 33 | `UNOBSERVED_RESERVED_OR_UNUSED` | same |

These are **not** forced to acquire names. On this hardware they are consistent with unused or reserved
slots: the app's 32-slot `mapKeys` space is larger than the number of controls this unit reports.

## What would actually resolve RT

RT emits no frame, so the analog value is invisible in the D2 stream. Options, in order of value:

1. **Watch the official app instead of the frame stream.** The app's DPI/trigger page reads the trigger
   over the same link; capture what the official app shows/asks while RT is pulled. That works whatever
   the wire format does.
2. Ask the vendor tooling/Windows side for the trigger calibration read path (the Assistant's trigger
   view) — static first.
3. Only then consider a firmware-side question; that is out of scope and not proposed.

## Session hygiene

- Final runtime write on the wire: **`a5 05 d2 00 7c`** (D2 OFF) before clean disconnect, in both runs.
- **No D7, no D8, no configuration, DPI, lighting or macro write was sent.**
- Post-session integrity read (read-only): 144 bytes, sha256
  `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → **`CONFIG_BASELINE_MATCH`**.
  Integrity readback only — **not** a new durability proof (`DURABLE_OK` unchanged, `STAGED_OK != DURABLE_OK`).

## Harness defects found and fixed during this session

1. **The first popup never appeared.** The runner resolved the dialog helper as
   `automation/scripts/operator-dialog-kdialog.sh`, which does not exist; `bash <missing>` exits 127, and
   the runner **misreported that as `OPERATOR_CANCELLED`**. The operator was never asked anything. Fixed:
   the helper is resolved at its real path, its absence is now a hard error, and exit codes are read
   properly — **only rc == 1 is an operator cancel**; rc 2/3/127 are harness faults and are reported as
   such.
2. One unnecessary 3-second probe dialog was raised while diagnosing the above. It was auto-killed, asked
   nothing of the operator, and is recorded here rather than omitted.
3. tshark cannot read a btmon btsnoop written by this stack (0 frames) even though `btmon -r` decodes it
   fully (2,049 lines). The HCI evidence in this document was extracted with `btmon -r`; this is a
   tooling quirk to remember, not a capture failure.
