# D2 frame contract (static)

## Enable

Raw bytes: `A5 05 D2 01 7D`
Length: 5
Checksum: `0x7D` = Sum8(`A5 05 D2 01`) & 0xFF = `0x17D & 0xFF` — a hard-coded literal on this path
(`getCheckSum` is not called here)
Builder: `BluetoothModel::testModeSwitch` @ `0xabaef4` (4.0.8); `testModeSwitch` @ `0x91e380` (2.24),
@ `0x8b1d68` (2.23), @ `0x8e3a88`/`0x8e3be4` (2.22)
Callers: `_RainbowTestState::initState` callback (4.0.8 @ `0xacf8cc`; 2.24 @ `0x91cf94`;
2.23 @ `0x8b0504`; 2.22 @ `0x8e1e94`), **not awaited**
Observed build(s): all four (identical bytes)
Blutter note: the list is built from **tagged Smis** (`0x14a, 0xa, 0x1a4, 0x2, 0xfa`); halve each to
get the byte.

## Disable

Raw bytes: `A5 05 D2 00 7C`
Length: 5
Checksum: `0x7C` = Sum8(`A5 05 D2 00`) & 0xFF
Builder: same function, mirror branch (4.0.8 @ `0xabaf9c`; 2.24 `testModeSwitch1` @ `0x93371c`;
2.23 @ `0x881a78`; 2.22 in `dispose` @ `0x95a864`)
Callers: `dispose`, **gated on the connection state being connected** (2.23 @ `0x90dea1`;
4.0.8 via the Provider-resolved `BluetoothModel`)
Observed build(s): all four

## RX event

Expected bytes / shape: 18-byte frame, header `0xA5`, length byte `0x12`, opcode `0x02`
Minimum length: **18 in 2.22/2.23** (gate `frame[1] == 18`); **no length gate in 4.0.8** — the
opcode gate is `frame[2] == 0x02` and the mask read consumes indices 3..6, so ≥7 bytes are
required for a mask. 2.24: UNKNOWN (its gate compares against `0x24`).
Opcode position: index 2 (`0x02`)
Key-ID position: indices 3..6 as one **big-endian u32**; `bit index == key id`
Press/release field: none — the mask is absolute state (bit set = down)
Other fields: `[7..14]` four signed int16 BE axes; `[15]` LT analog; `[16]` RT analog;
`[17]` trailer, never read by the page
Checksum handling: **not validated by the app on this path** (the app's checksum helper is used for
outgoing frames only)
Length validation: 2.22/2.23 yes (==18); 4.0.8 no explicit length gate
Malformed-frame behavior: 4.0.8 jumps to the alternate branch @ `0xad0c80` (UNKNOWN); 2.22/2.23
silently ignore anything whose length byte is not 18

## Unknown fields

- `[15]` / `[16]`: our live capture showed LT moving byte `[15]` with the trigger (`0x83 → 0xFF`),
  but the **app does not read `[15..16]` at all in the decoded page** → the two facts are kept
  separate: live observation PROVEN LIVE, app interpretation **UNKNOWN**.
- `[17]`: UNKNOWN (never read; our captures carry a checksum there).
- 4.0.8 CCDD write value: UNKNOWN.

---

## DATED CORRECTION — 2026-09-27 (overnight autonomous shift, no hardware)

**Applies to the "silent / no stream" conclusions in the text above. The original wording is left
exactly as it was written; this annotation records what later evidence changed.**

The official BIGBIG WON 4.0.8 app was captured live against the real ARMOR-X Pro (Android HCI snoop,
official-session differential, `results/experiments/official-vs-harness-session-20260927-190741/`)
and the correction is unambiguous:

**D2 input is EVENT-DRIVEN.** During that session the official app produced

* **0** valid `A5 12 02` frames while nothing was pressed, and
* **155** valid `A5 12 02` frames while the A button was pressed (18-byte frames, every checksum
  valid, only bit 0 ever set, PRESS -> RELEASE -> PRESS -> RELEASE, repeats ~every 11.7 ms).

Consequences for the conclusions above:

1. `NO_STREAM_IN_ANY_VARIANT` / "silent" / "no longer streaming" records where **no physical button
   was pressed after D2 was enabled** must be read as **`NO_IDLE_FRAMES_OBSERVED`**. In those runs
   the harness was looking for idle traffic; the device does not emit idle traffic even when it is
   working perfectly. Zero idle frames is the *expected* signature of a healthy link.
2. Such a result is therefore **not** evidence that the D2 stream is broken, and it is not a durable
   device-state finding.
3. Conversely, a run *with* a physical press and still no frames remains meaningful evidence, and has
   not been reinterpreted.

See `results/overnight/20260927-203902/branches/historical-d2-reinterpretation/` for the per-run
table, per-run annotations and the strongest remaining live button-streaming evidence.

Also corrected on the same date: `tshark` on this host is AppArmor-confined and cannot read paths
under `/home/salamanka` (copy captures to `/tmp` first), and `btatt.mtu` is not a valid field in
tshark 4.6.4 (requesting it makes tshark exit non-zero and print nothing, which previously looked
like "no frames").


---

## 2026-09-28T06:26:00-04:00 — RT analog PROVEN LIVE in `[16]` (append-only; offsets unchanged)

`[15]` LT analog and `[16]` RT analog stay as contracted — what changed is that `[16]` is no longer an
unverified field.

- **`[16]` = RT analog: PROVEN LIVE.** Rest = `0`, full pull = `255`, sampled inside frames whose
  transmission was caused by `A` (bit 0): every one of the 40 A-caused frames in P2 and all 52 in the
  repeat carried `255`, against `0` in all 56 A-caused baseline frames. Observed ramp values during travel
  (`9, 31, 62, 67, 95, 100, 102, 122, 160, 190, 204, 219, 238`) show a continuous 0..255 scale.
- **`[15]` LT analog reconfirmed** by positive control: 255 in all 36 A-caused frames while LT was held,
  `0` in all 36 while RT was held — the two channels do not leak into each other.
- **Method note (important for anyone re-reading old notes):** analog-only movement emits **no frame**, so a
  field can only be sampled while a digital event forces transmission. "The analog byte never left zero" in
  an earlier note meant *unsampled*, not *measured zero*.
- **Digital side:** a mask bit **9** appeared only in the two windows where RT was physically held
  (masks `513`/`512`), never in the baseline or LT-control windows. Recorded as
  `NEW_BIT_9_OBSERVED_UNNAMED` — preserved, deliberately **not named** in this pass.
- Evidence: `results/experiments/rt-analog-piggyback-20260928-061800/RESULT.md` and `ANALYSIS.json`.


---

## 2026-09-28T06:38:30-04:00 — RT digital bit **9** PROVEN LIVE (append-only; offsets unchanged)

- **Mask bit 9 = RT, PROVEN LIVE** by one-variable confirmation (`A` alone → `RT` fully held + `A` → `A`
  alone; one connection, one D2 session). Bit 9 frames: **0/228** (W0) → **184/263** (W1, two holds, with
  byte[16] ramping 0..255) → **0/283** (W2). Mask value `1 << 9` = **`0x00000200`**.
- **`[16]` RT analog** (proven earlier the same day, rest 0 / full pull 255) is confirmed again inside the
  same windows, and `[15]` LT stayed flat while RT was held.
- **Behavioural note for readers of the frame stream:** RT's state *is* in D2 frames, but **RT alone does
  not cause a report to be emitted** — an isolated RT pull produced zero frames. RT's bit and analog value
  become observable when another digital event (e.g. A) forces transmission. **RT is not analog-only**, and
  "no frames" from an isolated RT window must never be read as "RT is absent from the protocol".
- The earlier note in this file/session history (`RT = PROVEN_NEGATIVE as a digital bit`) is **superseded as
  method-limited**, not deleted: the bit could not have appeared in windows where no frame was ever emitted.
- Evidence: `results/experiments/rt-bit9-confirmation-20260928-063300/` (`RESULT.md`, `RESULT.json`).
