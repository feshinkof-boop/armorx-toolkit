# D4 / Smi / protocol reconciliation — final report

Autonomous pass, 2026-09-27. Answers the 31 required points, plus the two mandated sections
("PROJECT-WIDE CORRECTIONS CAUSED BY THE SMI AUDIT" and "D4 — FINAL PROTOCOL CONTRACT").
Evidence labels: PROVEN STATIC / PROVEN LIVE / STRONG EVIDENCE / INFERRED / UNKNOWN / CONTRADICTED.
No physical ARMOR-X was touched; no public-release code was modified; history was amended by dated
append only.

---

## 1–7. D4

| # | Answer |
|---|---|
| 1 | **Request (all four builds): `A5 04 D4 7D`** — PROVEN STATIC. Same 4-element list literal in every tree (0xA5, 0x04, 0xD4, placeholder checksum), checksum `(0xA5+0x04+0xD4+0x00)&0xFF = 0x7D`; matches the byte-exact 2.22 live capture. Senders: 2.22 `_ArmorXProConfigWidgetState::getOnBoardConfig` @`0x89adac`; 2.23 `_RainbowMoreWidget::getInputModel` @`0x8afa98`; 2.24 `_RainbowTabConfig1sWidgetState::getOnBoardConfig` @`0x91b988`; 4.0.8 `BluetoothModel::getInputModel` @`0xa84258` (moved into the BLE model). |
| 2 | **Reply format (PROVEN STATIC once the tagged-index bug was corrected): `A5 06 D4 <gamepad_mode> <onboard_mode> <cks>`.** The reply index immediates are tagged, so `mov x16,#8` is whole-frame index **4** and `#6` is index **3**; pinned against the already-decoded `0xEF` UUID loop. Receivers: 2.22 @`0x89bcac` (index 4 → `field_1f`); 2.23 @`0x8af690` (index 3 `==6` → `getDpi()` follow-up) and @`0x8097cc` (index 4); 2.24 @`0x91a528` (index 3 `==6` → `getDpi`) and @`0x8a9824` (index 4, prints `"板载mode = "`); 4.0.8 @`0x8b3c84` (index 3 `==6`, index 4 `==3`) and @`0x826ecc` (prints `"板载mode = "`). |
| 3 | **Payload meaning: byte 3 = 手柄模式 (gamepad mode), byte 4 = 板载mode (onboard mode).** The decisive evidence is the literal format string `"板载mode = "` fed by index 4 in both 2.24 and 4.0.8 — not the function name. |
| 4 | **Why 2.24 calls it `getOnBoardConfig`:** because that build reads and prints the *onboard* mode field. It is a rename, not a semantic change — the same request, the same two payload bytes. |
| 5 | **Semantically unchanged across versions: UNCHANGED** (four-version table classifies the wire contract as identical; only naming, the boolean checks the client applies to byte 3, and the follow-up `getDpi()` differ). Active onboard **slot** and **config bank** are **CONTRADICTED** (no slot/bank arithmetic in any reader); "input mode / device mode" is SUPPORTED; "profile number" stays UNKNOWN. |
| 6 | **Virtual ARMOR-X implementation status: IMPLEMENTED for the request/reply shell.** `armorx_protocol.py` gained the D4 constants, `build_d4_reply`, structured `parse_d4_reply` and `REPLY_TABLE[0xD4]`; `virtual_armorx.py` a 0xD4 branch with structured `d4_reply` logging and `--d4-gamepad-mode/--d4-onboard-mode` flags; `armorx_central_client.py` a D4 step. Default reply `A5 06 D4 00 00 7F`. Test vectors: `A5 06 D4 00 00 7F`, `…06 03 88`, `…06 00 85`, `…01 01 81`. Suite: **pytest 29 passed**, selftest **12/12 peripheral + 15/15 client** (I re-ran the suite myself: 29 passed, and the selftest 12/12). The payload **values** are CLI-chosen device state, documented exactly like `--device-uuid` — no researched value is claimed. |
| 7 | **2.22 dynamic D4 test result:** *see §39 addendum — dynamic verification run recorded in `results/static/2.22.0901/d4-dynamic-verification.md`.* |

## 8–13. The Smi audit

| # | Answer |
|---|---|
| 8 | **Methodology:** `results/reconciliation/dart-smi-methodology.md` — the tagged-Smi rules for Dart 2.17.5/2.19.6/3.2.3/3.12.2, eight detection signatures (P1–P5 tagged, N1–N8 raw), a mechanical decision procedure, and seven worked examples. Two rules matter most: (a) an **odd immediate is never a Smi** (tagged values are even); (b) `LoadInt32Instr`/`sbfx x,x,#1` marks an **untagged** operand, so a compare against `#0x35` is the literal 53 and must **not** be halved. I added a third finding myself while verifying: **Blutter's own `rN = <value>` annotation is the raw immediate, not the decoded Dart value** (`keyCapture()` prints `r0 = 65536` for `mov x0,#0x10000`), so the annotation is not a safe source. |
| 9 | **Incorrect constants found:** 6 TAGGED SMI — CORRECTED out of 46 audited. Headline: **K1** `bit == key id` (the `keyCapture = 0x10000` / `bit = id+1` claim); **D1** D8 commit byte `0x0A → 0x05`; **L3/L4** light-mode ordinals `2,4,6 → 1,2,3`; **D5/D6** 2.22 macro envelope defaults `runKey 46 → 23` (=M1) and `repeatTime 200 → 100` ms; plus a non-Smi correction **D4-b** `subpackageLength()` id 11 → 72 (devGale2), not 20. |
| 10 | **Every corrected constant:** the six above, with raw evidence, two anchors each where possible, affected docs and code, and evidence label, in `smi-audit.md` / `smi-audit.json`. 13 items were CORRECT AS DOCUMENTED, 26 RAW INTEGER — NO CHANGE, 1 AMBIGUOUS (D11: the D8 readback table `0x4e/0x50/0x52/0x5e/0x62/0xfe` — both hypotheses recorded, the old `78/80/82/94/98` reading deliberately not promoted). |
| 11 | **Key-mask conclusions changed: YES.** `keyCapture` = **0x8000 (bit 15)**, `keyUp` = **0x10000 (bit 16)**, `keyL1` = **0x40 (bit 6 = LB)** — `bit == id`, no +1. Four anchors; the old rule was self-contradictory (un-halved `keyL1 = 0x80` would be bit 7 = RB while the app's own map says L1 = LB = id 6). The id-15 = Capture label survives on its independent map-literal chain. Verified identically in all four trees. |
| 12 | **D8 conclusions changed: YES, three ways** — the commit length byte is **0x05, not 0x0A**; there **is** an ordinal byte at frame offset 3 in every version (the imported "no ordinal" claim is CONTRADICTED); and the dispatcher index immediates are tagged, so the opcode sits at **byte 2** and the ordinal at **byte 3** (the earlier `data[4]`/`data[6]` labelling is CONTRADICTED). |
| 13 | **Lighting-mask conclusions changed: YES, narrowly.** LED/zone masks themselves were RAW INTEGER — NO CHANGE (`1<<id` and `0x3F` stand), but the per-zone **mode ordinals** are corrected from a 1-based reading to the real values, and the 2.22 call-site arguments `2,6` become `1,3`. No RGB byte-order claim was made, because no independent anchor exists. |

## 14–17. E2 and AB verdicts (matrix stale-UNKNOWNs closed)

| # | Answer |
|---|---|
| 14 | **2.23 E2: ABSENT — PROVEN STATIC.** Complete negative search: Smi `#0x1c4`, raw `#0xe2`, pool/decimal 226/452, dispatcher comparisons, byte sequences, builder shapes, DEX and string dumps — all zero, outside `generated/intl/` (a false-positive zone). E2 does **not** hide under a misleading name: `getZKMVer` emits `0x0B`, not E2. |
| 15 | **2.24 E2: ABSENT — PROVEN STATIC**, same exhaustive search. |
| 16 | **2.23 AB: ABSENT — PROVEN STATIC** (no `#0x156`, no `AB 05`/`AB 07`/`05 25`/`05 26` shapes, no motion/gyro/sensor/aim/transcribe naming). |
| 17 | **2.24 AB: ABSENT — PROVEN STATIC.** (4.0.8 is `PRESENT_SEND`: `AB 07 05 25 <u16 LE> <cks>` @`0x946158`.) |

One methodology find is worth recording: an early scan used a **relative path** from the wrong cwd and
read the whole 2.24 tree as zeros — indistinguishable from ABSENT. Every verdict was re-run on
absolute paths. This is exactly why the pass demanded "ABSENT only after a complete negative search".

## 18. Exact F6 condition in 2.24 (raw code, settled)

```dart
var frame = [0xA5, 0x05, 0xFC, dpi & 0x0F, 0];      // FC is the default
if (curDevice == devRainbow2Pro || curDevice == devC2SL)   // Obj!Device@9ef941 / @9ef981
  if (zkmVersion >= 0x35) frame[2] = 0xF6;                  // @0x8940f8: b.lt skips the store
```
Threshold **0x35 = 53**, operator `>=`, **F6 when version ≥ 0x35**, FC otherwise. The previously
documented "`< 0x35`" wording is **CONTRADICTED**. Note the Smi trap: this operand is explicitly
untagged (`LoadInt32Instr`), so it is the plain `#0x35` and must **not** be halved to 0x6a. 2.23 is
FC-only and unconditional (zero `#0x1ec` under `asm/moojiang`). 4.0.8 keeps the branch and adds
devRainbow3/devGale2 to the gate.

## 19–25. D8 across versions

| # | Version | Answer |
|---|---|---|
| 19 | 2.22.0901 | **OLD format**: 7-byte `GamepadDefMap` records, `N = 10 + 7n`, **chunk literal 15**, `subpackageLength()` absent, header byte 4 = `GamepadAtt.type`, defaults runKey 46 / repeatTime 200 (both now corrected by the Smi audit to 23 / 100). |
| 20 | 2.23.0609 | **OLD format** — same 7-byte records, same hard-coded 15, `subpackageLength()` still absent (only the fragment ordinal is STRONG EVIDENCE rather than PROVEN here). |
| 21 | 2.24.0919 | **MODERN format**: 10-byte `TranscribeFrame` records, `N = 10 + 10n`, chunk = `subpackageLength() - 5` with `subpackageLength()` = `{20,72,48}` @`0x7b9064`, header byte 4 = constant `0x00`. |
| 22 | 4.0.8 | **MODERN format**, same 10-byte records and the same `subpackageLength()` = `{20,72,48}` @`0x819190`; runKey now parsed via `int.parse` with `0 → 5`. (The 2.24 and 4.0.8 device-id branches are not identical: 2.24 lacks the `9/10` arms, so the ARMOR-X Pro's `field_7` id is still UNKNOWN statically.) |
| 23 | **Commit frame, all four versions — identical:** `A4 05 D8 <nfrags+1> <csum>` (5 bytes total). Data fragment: `A4 (segLen+5) D8 (i+1) seg csum`. |
| 24 | **Is a literal 0x0A valid anywhere? NO.** The 0x0A came from reading `mov x16, #0xa` at 4.0.8 `0x85aba8` (2.24 `0x80012c`) as a wire byte; the same `List<int>` stores `0xA4` as `#0x148` and `0xD8` as `#0x1b0` — exactly 2× — so `#0xa` is Dart **5**, i.e. wire **0x05**. **I verified this myself** in `gamepadset.dart` (the sibling-store context around `0x85aba8`). A genuine 0x0A byte appears only as the *ordinal of the 10th fragment* in the live 144-byte D6 readback. Consequently the `0x0A` special case in `ble/virtual-armorx/armorx_protocol.py` and in the toolkit `frames.py` is now known-wrong and must be deleted. |
| 25 | **Readback/parser status:** 2.22/2.23 generic A4/D6 reassembler **PRESENT** (2.22 @`0x8a6a04`) but **D8 macro readback ABSENT** (no `0xD8`/216 compare under `widgets/`). 2.24/4.0.8 **PRESENT/PARTIAL**: a closure tests `list[2]` against `0xFC`/`0xD8` (`"写入结果"` + `printHex`)/`0xD3`, then `parsingData` @`0xac35ac`/`0x915c38` → `fromConfigData` → `changeTranscribeFrameToDefMacro`. Proven readback offsets: byte 2 = opcode, byte 3 = limit compare, bytes 15–16 = u16 LE ×8 ms frame time. |

## 26–29. Matrix, documents, tests, git

* **26. Updated matrix:** `results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.{md,json}` — rebuilt from the
  manifests after `scripts/apply_reconciliation_fields.py` wrote canonical fields (E2, AB family, D4,
  D8 format/commit/readback, DPI timeline, key-mask rule, Smi corrections) into each build. Stale
  UNKNOWNs for E2/AB at 2.23/2.24 are now **ABSENT — PROVEN STATIC**; a missing input still yields
  UNKNOWN, so "not checked" stays distinguishable from "absent".
* **27. Canonical documents amended:** **12 lab documents** by dated append (9 ×
  `baselines/imported-research/*.md`, `baselines/imported-research/docs/mygt-4.0.8-reconciliation.md`,
  and new lab copies of `docs/usb-protocol.md` and `docs/research-status-2026-09-25.md`), each block
  carrying OLD CLAIM / NEW EVIDENCE / CORRECTED INTERPRETATION / AFFECTED VERSIONS. Exact appended text
  and post-append hashes: `results/reconciliation/docs-amended.md`. `SHA256SUMS` left intact. Nothing
  historical was deleted or reworded; the toolkit repo was **not** edited by that workstream.
* **28. Tests run:** virtual ARMOR-X `pytest -q` → **29 passed**; peripheral `selftest.py` →
  **12/12** (client 15/15); `tests/test_smi_constants.py` → **12/12 passed**; `tests/test_d8_versions.py`
  → **21 tests OK** (old builder rejects a 10-byte frame, modern rejects a 7-byte record, every commit
  length byte == 0x05, commit == `A4 05 D8 03 84`, the 2.22 vector reproduced byte-for-byte, the
  imported 4.0.8 vector rejected); `harness_selftest.py` → **ALL CHECKS PASSED**; JSON sweep → 54/54 valid
  before the pass, re-run after. Format-confusion between the old and modern D8 serializers is now
  mechanically prevented, as required.
* **29. Git:** lab branch **`research/d4-smi-protocol-reconciliation`** (commit recorded in the closing
  message); toolkit `research/mygt-4.0.8` still `dbe2ce7`, `research/ble-lab-multiversion` `6f0acd5`,
  `research/mygt-2.22.0901` `5524f54`. Patch + bundle produced; **AUTH_BLOCKED** for push. No force
  pushes, no rewrites.

## 30. Remaining UNKNOWN

The value domain of the two D4 payload bytes (only `6` for byte 3 and `3` for byte 4 are known
distinguished values); whether the app verifies inbound checksums and reply length (being settled by
the robustness experiment in the live run); the D8 readback field table's encoding (D11, AMBIGUOUS);
the ARMOR-X Pro's `subpackageLength()` device id (statically UNKNOWN, observable at runtime from the
app's `包数->N` log); the 2.22 reassembler's `replaceRange` offset ladder (mixed tagged/raw rendering,
flagged rather than overclaimed); DPI selector→value table and DPI reply parser (static-unrecoverable
in all builds); lighting RGB byte order; the exact real total length of a D4 reply beyond "≥6 proven".

## 31. The ONE next highest-value experiment

**Serve the corrected D8 commit byte (`A4 05 D8 …`) to 2.22 and 4.0.8 and watch the macro-write
acknowledgement path** — the 0x0A→0x05 correction changes a byte that the firmware is being asked to
interpret as a fragment count, it is the one D8 constant that was wrong in *both* directions
(reference docs *and* lab code), and the 2.24/4.0.8 `"写入结果"` readback closure gives an immediate,
observable verdict on whether the corrected frame is accepted.

---

# PROJECT-WIDE CORRECTIONS CAUSED BY THE SMI AUDIT

1. **`bit == key id`, not `id + 1`.** The single most important correction, and it was arithmetically
   forced: un-halved, `keyL1 = 0x80` would mean bit 7 = RB, contradicting the app's own `gamePadKeyName`
   map (L1 = LB = id 6). Corrected: `keyL1 = 0x40`, `keyCapture = 0x8000`, `keyUp = 0x10000`. Four
   anchors, identical in all four trees. Practical effect: every bit-mask constant derived from a `mov`
   immediate in the toolkit's docs moves one bit, and the "id 15 = Capture" conclusion survives on its
   independent map-literal chain rather than on the mask.
2. **The D8 commit byte is 0x05, and the `0x0A` special case came from a tagged Smi read as raw.** The
   root cause is visible in the sibling stores (`#0x148` = 0xA4, `#0x1b0` = 0xD8, both doubled): the
   odd-looking `#0xa` is Dart 5. My own `frames.build_frag()`/terminator path and
   `armorx_protocol.py`'s 0x0A handling both inherited the error; both are now known-wrong.
3. **"No ordinal byte in A4 fragments" is wrong** — the ordinal is at frame offset 3 in every version,
   which is *why* the length byte is `segLen + 5` and not `+ 4`. That resolves the discrepancy that had
   been papered over as "two acceptable forms" in the lab code.
4. **Dispatcher index immediates are tagged**, so D8/D6 frame fields sit at **byte 2 (opcode)** and
   **byte 3 (ordinal)**; the earlier `data[4]`/`data[6]` field labelling was off by the tag.
5. **Methods that protect against the bug class:** odd immediates are never Smis; `LoadInt32Instr`/`sbfx`
   marks an untagged compare (the F6 `>= 0x35` threshold is a literal 53); Blutter's `rN = <value>`
   annotation is the raw immediate and must not be trusted as the Dart value; and **a path error looks
   exactly like ABSENT** (the relative-path scan that read the whole 2.24 tree as zeros), so negative
   results need absolute paths and a positive control.
6. **What did *not* change** (26 items RAW INTEGER — NO CHANGE) is as important as what did: config sizes
   88–508, device enum ids (6/8/10), CRC constants, stick `orr` masks, DPI `&0x0F`, LED `1<<id`/`0x3F`,
   turbo shifts, D8 timing packs, sensor masks, and every byte captured live on the wire.

# D4 — FINAL PROTOCOL CONTRACT

```
REQUEST   A5 04 D4 7D                     (all four builds; checksum = sum of preceding bytes & 0xFF)
REPLY     A5 06 D4 <gamepad_mode> <onboard_mode> <cks>
           byte 0   0xA5  frame magic
           byte 1   0x06  total frame length (6)
           byte 2   0xD4  opcode
           byte 3   gamepad mode   (手柄模式)   — client compares == 6
           byte 4   onboard mode   (板载mode)   — 2.24/4.0.8 print this; 4.0.8 also compares == 3
           byte 5   checksum      (sum of bytes 0..4 & 0xFF)
EXAMPLE   A5 06 D4 00 00 7F               (virtual-peripheral default; 0x7F verified by hand)
FOLLOW-UP 2.23/2.24 readers call getDpi() after a byte-3 value of 6
STATUS    request PROVEN STATIC + PROVEN LIVE (2.22); reply layout PROVEN STATIC;
          payload value domain UNKNOWN; whether the app validates the inbound checksum and length
          is being determined by the live robustness experiment (see the addendum)
NOT PROVEN DO NOT USE: any claim that byte 3/4 encode an onboard *slot* or config *bank*
          (CONTRADICTED — no slot/bank arithmetic exists in any reader)
```
