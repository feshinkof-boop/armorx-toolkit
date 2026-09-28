# D4 evidence matrix — project-wide reconciliation

**Branch:** `d4-reconciliation` · **Date:** 2026-09-27 · **Author:** Hermes subagent (offline, no hardware)
**Companions:** `d4-matrix.json` (machine-readable), `checksums-verified.md` (per-frame arithmetic),
`corpus-sweep.json`, `checksums-raw.json`.
**Scope:** every D4 observation across `results/final/`, `results/reconciliation/`, `results/experiments/`,
`results/static/2.22.0901/`, `baselines/`, `armorx_research/`, `armorx-re/repo/` and the four
Blutter/JADX static trees. Nothing was deleted or rewritten; this is a matrix laid over the existing
evidence.

Frame convention actually observed in the corpus (verified on all 227 recognized frames):
`A5 <LEN> <OPCODE> <payload…> <CHECKSUM>`, where **`LEN` = the TOTAL frame length in bytes**
(every frame has `LEN == len(frame)`) and `CHECKSUM = sum(all bytes except the last) & 0xFF`.
The brief's phrasing "LEN counts the bytes after it" does **not** match the corpus (see
`checksums-verified.md`); the checksum rule is the same either way, so no result depends on it.

---

## 1. The matrix

| # | date | app version / build | real / virtual / static | request bytes | response bytes | req len | resp len | req cks (recomputed) | resp cks (recomputed) | source path | static-or-live | confidence |
|---|---|---|---|---:|---:|---|---|---|---|---|---|
| 1 | (static) | 2.22.0901 | static | `A5 04 D4 7D` | layout `A5 06 D4 <g> <o> <cks>` | 4 | 6 (min, INFERRED) | `0x7D` | n/a | `static/blutter/2.22.0901/blutter_out`; `results/reconciliation/d4-reconstruction.{md,json}` | static | **PROVEN STATIC** |
| 2 | (static) | 2.23.0609 | static | `A5 04 D4 7D` | layout `A5 06 D4 <g> <o> <cks>` | 4 | 6 (min, INFERRED) | `0x7D` | n/a | `armorx-re/repo` blutter 2.23 (`getInputModel` @0x8afa98; rx @0x8af690/0x8097cc) | static | **PROVEN STATIC** |
| 3 | (static) | 2.24.0919 | static | `A5 04 D4 7D` | layout `A5 06 D4 <g> <o> <cks>` | 4 | 6 (min, INFERRED) | `0x7D` | n/a | `armorx-re/repo` v224 blutter (`getOnBoardConfig` @0x91b988, prints `板载mode`) | static | **PROVEN STATIC** |
| 4 | (static) | 4.0.8 | static | `A5 04 D4 7D` | layout `A5 06 D4 <g> <o> <cks>` | 4 | 6 (min, INFERRED) | `0x7D` | n/a | `armorx-re/mygt408/blutter_out` (`getInputModel` @0xa84258, prints `板载mode`) | static | **PROVEN STATIC** |
| 5 | 2026-09-27 | 2.22.0901 on AVD | virtual | `A5 04 D4 7D` | `A5 06 D4 00 00 7F` | 4 | 6 | `0x7D` | `0x7F` | `results/static/2.22.0901/d4-dynamic-verification.md`; `ble/virtual-armorx/logs/2220901-d4-live.*` | live (vs VIRTUAL peripheral) | **PROVEN LIVE** (exchange) — reply is a **constructed virtual default** |
| 6 | 2026-09-27 | 2.22.0901 on AVD | virtual probe | `A5 04 D4 7D` | `A5 06 D4 00 00 80` | 4 | 6 | `0x7D` | `0x7F` (recorded `0x80`) | `ble/virtual-armorx/logs/2220901-d4-badcksum.jsonl` | live (virtual probe) | **PROVEN LIVE** — app ignores inbound D4 checksum |
| 7 | 2026-09-27 | 2.22.0901 on AVD | virtual probe | `A5 04 D4 7D` | `A5 04 D4 00` | 4 | 4 (truncated) | `0x7D` | n/a | `ble/virtual-armorx/logs/2220901-d4-truncated.jsonl` | live (virtual probe) | **PROVEN LIVE** — index-4 read has no length guard |
| 8 | 2026-09-27 | **4.0.8 official app** | **real** | `A5 04 D4 7D` | **`A5 07 D4 11 01 00 92`** | 4 | **7** | `0x7D` | `0x92` | `results/experiments/official-vs-harness-session-.../official-session/.../official-att.jsonl` (frame 6259); `official-timeline.csv`; `results/overnight/20260927-203902/official-timeline-canonical.json`; `logcat-official.txt:1288,1295` | live (real ARMOR-X Pro, HCI snoop) | **PROVEN LIVE** — decisive (`板载mode = 1` == `data[4]=0x01`) |
| 9 | 2026-09-27 | Linux harness | **real** | `A5 04 D4 7D` | **`A5 07 D4 11 01 00 92`** | 4 | **7** | `0x7D` | `0x92` | `results/experiments/physical-20260927-{162448,165347,174445-buttons}/raw-tx-rx.log`; `tests/vectors/real-device-vectors.json` | live (real unit ×3 sessions) | **PROVEN LIVE** |
| 10 | older (imported) | brief / older docs | assumption | `A5 04 D4 7D` | `A5 06 D4 00 00 7F` **claimed REAL** | 4 | 6 | `0x7D` | `0x7F` | `armorx-re/repo/docs/real-device/live-findings.md:25`; `results/final/remaining-real-hardware-unknowns.md:36` | neither (assumed) | **CONTRADICTED** as a real reply |
| 11 | 2026-09-27 (earlier) | 2.22.0901 on AVD | virtual (pre-handler) | `A5 04 D4 7D` | *(none — `command_unknown`, `reply_bytes_sent:0`)* | 4 | 0 | `0x7D` | n/a | `results/static/2.22.0901/virtual-armorx-compat.md` §B | live (virtual, D4 handler not yet written) | **PROVEN LIVE** (older virtual vintage) |
| 12 | (static) | all builds | virtual-constructed | `A5 04 D4 7D` | `A5 06 D4 06 03 88` / `… 06 00 85` / `… 01 01 81` | 4 | 6 each | `0x7D` | `0x88` / `0x85` / `0x81` | `results/reconciliation/d4-reconstruction.json` test_vectors; `apk/manifests/*.json` | neither (constructed, never on wire) | **PROVEN STATIC** (arithmetic) |

**Distinct D4 vintages: 7 frame strings → 2 families.**
- 1 request form: `A5 04 D4 7D` (every build, every live path).
- 6 reply forms: `A5 06 D4 00 00 7F` (virtual default), `A5 06 D4 00 00 80` (bad-cks probe),
  `A5 04 D4 00` (truncated probe), `A5 07 D4 11 01 00 92` (**real**), the three static test vectors
  `A5 06 D4 06 03 88 / 06 00 85 / 01 01 81`, and the "no reply" older virtual state.
- Collapsed to **two families**: **F1** = 6-byte **constructed** `A5 06 D4 …` (virtual default +
  static vectors, chosen state `00/00`); **F2** = 7-byte **real** `A5 07 D4 11 01 00 92`.

### The decisive live artefact (row 8)

The official 4.0.8 capture is the strongest single piece of evidence and it is internally consistent:

```
logcat-official.txt:1288  I flutter : [A5, 04, D4, 7D]        <- app builds & sends the request
official-att.jsonl:78     handle 0x0077 value a507d411010092  <- real device reply (frame 6259)
logcat-official.txt:1295  I flutter : 板载mode = 1              <- app's D4 parser prints data[4]
```

`A5 07 D4 11 01 00 92` → `data[4] = 0x01` → the 4.0.8 branch prints `板载mode = 1`. The parser
consumed the real bytes and read exactly whole-frame index 4, which is what the static reconstruction
predicted. The request in the app's own log is `[A5, 04, D4, 7D]`, byte-identical to the static frame.
No inbound checksum complaint, and the app proceeds to `D6` (`[A5, 04, D6, 7F]` at :1297).

---

## 2. Checksums — recomputed, not copied

`checksums-verified.md` lists all 23 primary frames with the recorded vs recomputed trailing byte.
Summary:

- **All recorded checksums match the recomputation**, with **two deliberate exceptions**:
  the 2.22 robustness probes `A5 06 D4 00 00 80` (recorded `0x80`, computed `0x7F` — the wrong byte is
  the experiment) and `A5 04 D4 00` (no checksum byte by design).
- A corpus-wide sweep of **227** A5/A4 frame strings across the whole project found the **same two**
  deviations and **no others** — there is **no accidental checksum error** anywhere in the corpus.
- The disputed real frames are both self-consistent: `A5 04 D4 7D` → `0x7D`;
  `A5 07 D4 11 01 00 92` → `0x92`; and the constructed `A5 06 D4 00 00 7F` → `0x7F`.
- Convention flag: in every frame `LEN == total frame length`; the brief's "bytes after it" wording is
  wrong, though harmless to the arithmetic.

---

## 3. What the differences are attributable to (evidence per hypothesis)

| candidate cause | verdict | evidence |
|---|---|---|
| **software generation changed the query** | **CONTRADICTED** | `A5 04 D4 7D` is byte-identical in 2.22.0901, 2.23.0609, 2.24.0919 and 4.0.8 (static) and in 2.22-virtual, 4.0.8-official and harness live. Only the *sender* is renamed/relocated (`getOnBoardConfig`↔`getInputModel`, widget→`BluetoothModel`). |
| **device mode / state** | **SUPPORTED** | the payload **values** differ by device state: the virtual test used chosen `0x00 / 0x00`; the real unit returned `0x11 / 0x01`. The **field layout is unchanged** (index 3 = 手柄模式, index 4 = 板载mode); only the values differ. Live proof: `板载mode = 1` == `data[4]=0x01`. |
| **request variant** | **CONTRADICTED** | exactly one request form exists in the corpus. |
| **parser error** | **PARTIAL — already corrected, not the cause** | an earlier static pass read a tagged Smi index (`mov x16,#8` = index **4**, not 8); corrected and documented in `d4-reconstruction` / `smi-audit`. That fixed the *layout*; it does **not** explain 06-vs-07, which is a provenance difference. |
| **old assumption** | **SUPPORTED — PRIMARY** | `A5 06 D4 00 00 7F` is the virtual peripheral's default / the "brief" value. Two older documents (`live-findings.md:25`, `remaining-real-hardware-unknowns.md:36`) recorded it as the **REAL** reply. That misrecording *is* the conflict. |
| **virtual peripheral used in earlier work** | **SUPPORTED — PRIMARY** | `A5 06 D4 00 00 7F` originates as the virtual ARMOR-X default (`armorx_protocol.py` `D4_REQUEST`/default reply, `virtual_armorx.py --d4-gamepad-mode/--d4-onboard-mode`), fed with chosen state and frozen into `apk/manifests/*.json`. It was never observed on real hardware. |
| **genuine protocol variant** | **NO across versions; the length was simply unknown** | request and field layout are invariant. The real frame carries **one extra payload byte** (`index5 = 0x00`) before the checksum, so the real length is **7**, whereas the static reconstruction INFERRED **6** as the *minimum* and explicitly recorded the exact length as UNKNOWN (≥6). The "6" was a floor, not a contradicted value. |

---

## 4. Verdict

**The apparent D4 conflict is fully explained and is not a protocol contradiction.** There is exactly
one D4 **request**, `A5 04 D4 7D`, byte-identical across all four builds (static) and on every live
path (2.22 virtual, 4.0.8 official, Linux harness), and exactly one reply **structure**,
`A5 <LEN> D4 <手柄模式> <板载mode> […extra] <cks>`, whose index-3/index-4 reads are PROVEN STATIC and
now PROVEN LIVE (the official 4.0.8 app printed `板载mode = 1` from `data[4]=0x01` of the real reply
`A5 07 D4 11 01 00 92`). The two "conflicting" byte strings belong to **different provenances, not
different protocols**: `A5 06 D4 00 00 7F` is the **virtual peripheral's constructed default** (chosen
state `00/00`), which a prior pass mis-recorded in two documents as the *real* reply; the **real**
reply is `A5 07 D4 11 01 00 92`, captured five times (official HCI snoop + three harness sessions +
the frozen vector). The payload **values** (`00/00` vs `11/01`) differ because **device state**
differs; the **length** differs (6 vs 7) because the static 6 was an explicitly-INFERRED minimum and
the real length was UNKNOWN — the real frame simply has one more payload byte. No software-generation
change, no request variant, and no genuine per-version protocol variant is involved. Therefore D4
should **not** be closed as a blanket CONTRADICTED: only the specific claim *"the real D4 reply is
`A5 06 D4 00 00 7F`"* is CONTRADICTED; the D4 protocol itself is **consistent and now live-confirmed**.

### Grading (as required)

| claim | grade |
|---|---|
| D4 request `A5 04 D4 7D` | **PROVEN STATIC + PROVEN LIVE** |
| D4 reply field layout (index 3 = 手柄模式, index 4 = 板载mode) | **PROVEN STATIC + PROVEN LIVE** |
| real D4 reply bytes = `A5 07 D4 11 01 00 92` | **PROVEN LIVE** |
| claim "real D4 reply = `A5 06 D4 00 00 7F`" | **CONTRADICTED** |
| static `total_len = 6` | **INFERRED** (a valid parser floor) → superseded for this unit by live **7** |
| value domain of index 3 / index 4 | **UNKNOWN** |
| D4 semantics changed across generations | **CONTRADICTED** (no change) |
| sentinel: index 5 of the real frame (`0x00`) | **UNKNOWN** (no reader touches it on the ARMOR-X path) |

### Open items (unchanged, not guessed)

1. Value domain of `手柄模式` (index 3): real = `0x11`; only `6` is proven distinguished (gates `getDpi` in 2.23/2.24/4.0.8). `0x11 ≠ 6`, so no follow-up fired — consistent with the capture.
2. The extra real byte at index 5 (`0x00`) — read by no branch on the ARMOR-X path.
3. Whether the real length ever exceeds 7 (only one real reply form observed to date).

---

## 5. Reproduce

```bash
cd results/overnight/20260927-203902/branches/d4-reconciliation
python3 verify_checksums.py     # 23 primary frames, recomputed checksums
python3 sweep_corpus.py         # 227-frame corpus sweep
python3 build_matrix.py         # d4-matrix.json
python3 gen_checksums_md.py     # checksums-verified.md
```

Raw provenance for the decisive live frame:
`results/experiments/official-vs-harness-session-20260927-190741/official-session/transport-attempt-20260927-193109/official-session-live/official-att.jsonl:78`
and `.../raw/logcat-official.txt:1288,1295`.
