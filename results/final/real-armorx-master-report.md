# Real ARMOR-X Pro — master report (physical research pass)

Device: REAL ARMOR-X Pro, `ARMOR-X Pro_11` / `2D:37:35:6D:66:11`, model `ZJ-XT`, firmware `2741`.
Everything in this report is about that unit. Virtual-peripheral results are labelled VIRTUAL.

## 1. Resumed state and what was reused

- Branch `research/physical-armorx-live-2026-09-27`; lab HEAD at resume `ee772ec`, now `68dc6ea`
  (see §12 for the full commit list). Toolkit repo `armorx-re/repo` @ `156368d`, same branch.
- Reused, **not** re-proven: the D7 no-op round trip, the Emergency Restore exercise, the
  immutable baseline, the D4/E2/0B/EF/DPI captures, the corrected D8 terminator, the Smi audit and
  the `bit == id` correction.
- Resume check: read-only D6 on the real unit found a **leftover ID-15 mutant** (not the
  baseline) — an interrupted write. It was frozen as evidence, shown to be byte-for-byte our own
  experiment (`diff {0,1,127}`), then restored and re-verified on a fresh connection.
  Current D6 SHA: **`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`**
  (identical to the original baseline → **baseline intact**).

## 2. Operator interaction (new model, validated)

Repeating-popup alert **retired**. New contract: ONE popup, ONE sound, the **click** is the
acknowledgement, returned to Hermes as JSON — chat is not the channel.
`results/final/operator-ui-validation.md` records the validated test (`ACK/confirm_test` via click,
`pw-play` fired once, no repeats). Dialogs used this pass: `operator_ui_test`,
`armorx_power_required_restore`, `armorx_powercycle`, `armorx_console_state`,
`armorx_wake_keep_active`. Every request + acknowledgement is in
`results/runtime/operator-actions.jsonl`.

## 3. Identity, GATT, and RCSP

- Identity: `2A24 = ZJ-XT`, `2A26 = 2741`, `2A19 = 0x44` (68 %) → `0x41` (65 %). Advertisement
  carries no service UUIDs. 6 services / 18 characteristics (`real-gatt-services.md`).
- `AE00`/`AE01`/`AE02` (JieLi RCSP-compatible) **present on the device — PROVEN LIVE**; the
  Android app does **not** use RCSP (PROVEN STATIC, control-verified, and re-confirmed this pass
  with an independent zip-level scanner; `rcsp`/`FE DC BA` hits are coincidences — `strcspn`, a
  compiler constant table). Verdict: `jieli-rcsp-verdict.md`.

## 4. Protocol

Full contract: `real-armorx-protocol-contract.md`. Headlines: `A5` short frames with sum8;
`A4` fragments with 1-based ordinal and 20-byte frames (payload class **15**) on this unit;
144-byte config with big-endian CRC-16/MODBUS and `mapKeys` at bytes 112–143.

## 5. D4 / E2

`real-d4-e2.md`. Note the **recorded conflict**: TX `A5 04 D4 7D` ✓, but every captured reply is
`A5 07 D4 11 01 00 92`, whereas the brief states `A5 06 D4 00 00 7F`. The captured value is
PROVEN LIVE; the brief's value is recorded as CONTRADICTED by the captures on disk and will be
settled by a read-only re-query. `E2` firmware is **BCD** (`0x27 0x41` = `2741`), not ASCII.

## 6. Key-ID map (button capture)

`real-key-id-map.md`. 26 ids resolved, all PROVEN LIVE, from real D2 captures by claim
verification (never positional guessing). Mask = bytes `[3][4][5][6]`, **bit == id**.
Resolved: A 0, B 1, X 3, Y 4, LB 6, RB 7, LT 8, View 10, Menu 11, Guide 12, L3 13, R3 14,
**Capture 15**, D-pad 16-19, M1-M4 23-26, M5-M7 27-29, plus an unattributed id 20.
**RT unresolved** (4 attempts, no frame; its analog byte `[16]` never left zero).
**ID 15 = Capture is PROVEN LIVE from live capture — no config write was needed.** The byte-127
mutation was executed once, verified live (`97fb2061…`), then restored & verified; its operator
verdict was never collected, so it is recorded **INCONCLUSIVE** and is not used as evidence.

### Two-press standard and how it stands

The two-press protocol was implemented (`button-capture-harness.py`) but could not be applied:
the unit stopped streaming D2 status frames (`d2-mode-state-finding.md`). The existing rows are
therefore single-clean-press evidence with releases observed, stated as such.

## 7. D8

`real-d8.md`. Fragment class for this unit determined as **15-byte payload** from static
(`subpackageLength()` → 20/48/72) **and** live frames (only 20-byte `A4` frames accepted).
**No D8 write attempted** — macro preservation must be established first (provably empty slot or
an operator-chosen slot via dialog).

## 8. DPI / lighting / motion

- DPI: `real-dpi.md`. Query `A5 05 FC 80 26` → `A5 05 FF FC A5` (PROVEN LIVE). **No numeric DPI
  assigned, no write performed.**
- Motion/gyro `AB 05 05 25 / 26`: **no reply while the link was proven healthy** — PROVEN LIVE,
  not retried.
- Lighting: `real-lighting.md`. **Not started**; RGB order UNKNOWN; no mutation without a
  verified restore path and GUI-collected colour observation.

## 9. Not done in this pass (honest list)

- D2 button capture with the two-press standard (blocked, §6).
- D8 macro readback/write; DPI and lighting work; normal USB enumeration; F20 receiver/HID and
  Linux-driver evidence; firmware-upgrade-mode enumeration; any firmware dump.
- `real-gatt-services-bleak.json` characteristic **properties** (independent BlueZ path ran while
  the unit was asleep and correctly reported `DEVICE_NOT_ADVERTISING`).

## 10. Bugs found and fixed (not worked around)

1. Capture tool defaulted to `hci-socket` (hci0) instead of the lab `hci-socket:1` → `Errno 16`.
2. Harness phase is a **positional** argument, not `--phase`.
3. Operator-dialog ack files were landing **root-owned** because the harness re-execs as root —
   the dialog now launches as the desktop user.
4. Shell quoting: multi-line `--message` through `use-bumble.sh --command` is word-split — tools
   now tolerate trailing harness args (`parse_known_args`) and avoid multi-line CLI text.
5. `bluetoothd` wedged (>90 s hang on `bluetoothctl show`) → mgmt restart; primary network
   re-verified PASS.

## 11. Tests

`PYTHONPATH=ble/virtual-armorx:automation/scripts /usr/bin/python3.14 -m pytest tests -q`
→ **104 passed**, including real-device regression vectors exported from the captures
(`tests/vectors/real-device-vectors.json`, 61 real status frames + real 0B/EF/D4/E2 replies).
Harness selftest: ALL CHECKS PASSED.

## 12. Git

Branch `research/physical-armorx-live-2026-09-27` (lab): `ee772ec` → `68dc6ea` →
`7ead4a4`, `d9a4d52`, `47b7b98`, `dc537cf`, `5fd60fb`, `dc902f6`. Toolkit `armorx-re/repo`
unchanged at `156368d`. No public-release branch touched, no history rewritten. Remote push is
**auth-blocked** (no SSH key / `gh`) — hand-off remains git bundle + patch.

## 13. Highest-value next experiment

**Revive the D2 status stream and complete the button map under the two-press rule** — cheapest
concrete test first: with the unit freshly powered and being actively used, re-probe the stream
(`probe-d2.py`); if it returns, run `button-capture-harness.py` for **RT** (the only unresolved
button), then re-run the 23 resolved buttons to upgrade them from single-press to two-press
evidence. Rationale: the map underpins every later write experiment (macros, lighting, ID 15
confirmation), and RT is the one button whose silence is currently unexplained.
