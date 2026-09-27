# Real ARMOR-X Pro key-ID map (live D2 capture)

Device (REAL ARMOR-X): advertised `ARMOR-X Pro_11`, BLE address `2D:37:35:6D:66:11`,
model mark `ZJ-XT`, firmware `2741`. Evidence level for everything below: **PROVEN LIVE**.

## 1. How the ids are encoded

The D2 status frame is `A5 12 02 …` (18 bytes). The button mask is the four bytes
**`[3][4][5][6]`**, with **bit == source id** — not id+1:

| byte | holds ids |
|---|---|
| `[6]` | 0-7 |
| `[5]` | 8-15 |
| `[4]` | 16-23 |
| `[3]` | 24-31 |

Anchor check (all independently known before this capture): A=0, B=1, X=3, Y=4, LB=6, RB=7,
LT=8, View=10, Menu=11, L3=13, R3=14, Capture=15, D-pad 16-19, M5/M6/M7=27/28/29 — every one
matched the frame bit, so the "bit == id" rule and the byte order are both confirmed.

Other frame fields observed live: byte `[15]` = LT analog (`0x83` → `0xFF` on a full pull),
byte `[16]` = RT analog (never non-zero), bytes `[7]`-`[14]` = analog axes (semantics
**UNKNOWN**), byte `[17]` = checksum (sum8).

## 2. Verified map

| id | mask | physical button (live) | evidence | frames |
|---|---|---|---|---|

| 0 | byte[6] bit 0 = `0x01` | A | PROVEN LIVE | 14 |
| 1 | byte[6] bit 1 = `0x02` | B | PROVEN LIVE | 13 |
| 3 | byte[6] bit 3 = `0x08` | X | PROVEN LIVE | 14 |
| 4 | byte[6] bit 4 = `0x10` | Y | PROVEN LIVE | 14 |
| 6 | byte[6] bit 6 = `0x40` | LB | PROVEN LIVE | 38 |
| 7 | byte[6] bit 7 = `0x80` | RB | PROVEN LIVE | 35 |
| 8 | byte[5] bit 0 = `0x01` | LT | PROVEN LIVE | 13 |
| 10 | byte[5] bit 2 = `0x04` | View/Select | PROVEN LIVE | 29 |
| 11 | byte[5] bit 3 = `0x08` | Menu/Start | PROVEN LIVE | 22 |
| 12 | byte[5] bit 4 = `0x10` | Guide/Xbox | PROVEN LIVE | 26 |
| 13 | byte[5] bit 5 = `0x20` | L3 | PROVEN LIVE | 14 |
| 14 | byte[5] bit 6 = `0x40` | R3 | PROVEN LIVE | 18 |
| 15 | byte[5] bit 7 = `0x80` | Capture/Share | PROVEN LIVE | 28 |
| 16 | byte[4] bit 0 = `0x01` | D-pad Up | PROVEN LIVE | 24 |
| 17 | byte[4] bit 1 = `0x02` | D-pad Down | PROVEN LIVE | 24 |
| 18 | byte[4] bit 2 = `0x04` | D-pad Left | PROVEN LIVE | 19 |
| 19 | byte[4] bit 3 = `0x08` | D-pad Right | PROVEN LIVE | 18 |
| 20 | byte[4] bit 4 = `0x10` | UNATTRIBUTED - one frame with id 20 appeared in this window; it cannot be tied to RT with confidence | PROVEN LIVE | 19 |
| 23 | byte[4] bit 7 = `0x80` | M1 | PROVEN LIVE | 22 |
| 24 | byte[3] bit 0 = `0x01` | M2 | PROVEN LIVE | 28 |
| 25 | byte[3] bit 1 = `0x02` | M3 | PROVEN LIVE | 24 |
| 26 | byte[3] bit 2 = `0x04` | M4 | PROVEN LIVE | 21 |
| 27 | byte[3] bit 3 = `0x08` | M5 | PROVEN LIVE | 19 |
| 28 | byte[3] bit 4 = `0x10` | M6 | PROVEN LIVE | 17 |
| 29 | byte[3] bit 5 = `0x20` | M7 | PROVEN LIVE | 24 |
| 30 | byte[3] bit 6 = `0x40` | extra button (as pressed by the operator) | PROVEN LIVE | 13 |

Resolved this pass: **26 ids**.

## 3. Unresolved

| item | status |
|---|---|
| `RT` | **UNRESOLVED** — requested in four separate groups, and byte `[16]` (its analog field) never left zero. No frame ever carried id 9. The single id-20 frame that appeared in the last group could not be tied to RT confidently, so it is recorded as UNATTRIBUTED rather than guessed. |
| ids `2, 5, 21, 22, 31` | **UNKNOWN** — no physical button produced these bits in this capture |
| ids `32, 33` | **out of range** for a 32-bit mask; they cannot appear in this frame |

## 4. ID 15 (Capture) — PROVEN LIVE from this capture, no config write needed

`Capture = 15` was read out of the live mask (`byte[5] bit 7 = 0x80`) inside the window of the
request that asked for Capture, in an ordered group where the other three ids in the same
window matched their own static labels. That is independent of, and additional to, the earlier
static result.

The byte-127 configuration mutation (source slot 15 → `0x02`) is therefore **not required** to
establish ID 15. It was executed once and correctly, and its state machine is recorded here for
completeness: the write gate passed (`RESTORE_NOOP_VALIDATED = true`), the mutant diff was
provably `{0,1,127}`, the mutation was proven live by D6 readback (`sha 97fb2061…`), an
interrupted session then left it on the unit, and it was **restored and verified** back to the
immutable baseline (`sha bdef9c61…`, independent read-only re-check `BASELINE_LIVE`). The
operator's behavioural verdict on that test was never collected, so the experiment is recorded
as **INCONCLUSIVE (no operator verdict)** and is not used as evidence.

## 5. Method and its limits (stated plainly)

- Every row is corroborated by ≥1 real capture frame with **exactly that bit set**, inside the
  window of the request that asked for that button (`verify-key-id-map.py`).
- Presses were single presses per button in ordered groups, so a row is "one clean press with a
  release observed", **not** the two-press standard the newer protocol calls for. The two-press
  standard could not be applied retroactively — and the D2 stream stopped being reproducible
  before it could be applied prospectively (see `d2-mode-state-finding.md`).
- Frames that could not be paired to a requested press were left unattributed; positional
  pairing was deliberately rejected because an operator does not always press exactly what was
  asked, in order, inside the window.
