# FC / DPI in BIGBIG WON **2.22.0901** — verdict: **NOT PRESENT**

APK sha256 `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`.
Source: Blutter AOT tree `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out`
(Dart 2.17.5, arm64).

Evidence labels: PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN / **NOT PRESENT**.

---

## 1. Verdict

**2.22.0901 contains no DPI command path of any kind** — no normal-DPI (`0xFC`/`0xF6`) builder, no
motion/gyro-DPI (`0xAB 05 25`) builder, no DPI query parser, no DPI UI, no `selectDpi`/
`motionReportRate` string, and no DPI preset table.

## 2. Exhaustive search evidence (PROVEN STATIC, negative)

| search | scope | result |
|---|---|---|
| `grep -rin "dpi"` | whole `asm/moojiang/` (all app Dart) | **0 hits** |
| `grep -i "dpi"` | whole `libarm64-v8a/libapp.so` raw string table (53 935 strings) | **6 hits, all unrelated**: `Odpiranje menija za krmarjenje` (Slovene l10n word containing "dpi"), `lookAheadPictorgraphicExtend`, `_addPicture@16065589`, `SceneBuilder_addPicture`, `addPicture` (Flutter PDF/picture symbols), `TDpI` (base64-ish blob) |
| opcode immediate `#0x1f8` = `0xFC` (Smi-tagged) | whole `asm/moojiang/` | only in `generated/intl/messages_*.dart` as a **plain array index** `r0 = 504` (`mov x0, #0x1f8`, e.g. `messages_en.dart:4745`), i.e. **not** a frame byte |
| opcode immediates `#0x1ec`(`0xF6`), `#0x156`(`0xAB`) | whole `asm/moojiang/` | same — only localization-table indices, no builder |
| function-name search `writeDpiConfig`, `getDpi`, `writeMotionDpiConfig`, `getMotionDpi`, `MotionDpi`, `dpiConfig` | whole tree | **0 hits** (contrast: 2.23/2.24 contain `getDpi`+`writeDpiConfig`; 4.0.8 contains all four — verified in `static/strings/*.strings` of the baseline) |
| complete method inventory of `asm/moojiang/` | all files | no DPI-related method exists; the DPI-named methods present in later builds are simply absent |

**Opcode census of the only frame builder file (`units/gamepadset.dart`):** the only protocol
immediates that occur are `0xA5` (`#0x14a`, 2 hits), `0xA4` (`#0x148`, 6 hits) and `0x70` (`#0xe0`,
3 hits) — the light-frame header/opcode family (§`lighting.md`). No `0xFC`, `0xF6`, `0xAB`, `0xF8`,
`0xDD`, `0xF7` or `0xE1` occurs anywhere in the app's code.

## 3. What this means for the questions asked

| question | answer for 2.22 |
|---|---|
| every FC and F6 frame builder | **none exist** (NOT PRESENT) |
| comparison operator / firmware threshold selecting F6 | **not applicable** — there is no F6 branch (the `cmp … #0x35` gate is a 2.24/4.0.8 construct) |
| AB-family motion-DPI frames | **not present** |
| DPI selector values | **not present** (no 4-bit selector, no preset list) |
| `400/800/1200/1600/2000/3200`-style numeric tables | searched the Dart pool (`pp.txt`, 58 780 lines), `classes.dex`, `assets/` (15 files, all images/fonts/AssetManifest — **no config or preset blobs**), `res/`, `resources.arsc`, and the raw libapp string table: **no such DPI preset list**. The only `List<int>` literals of interest are `List(32)` powers-of-two (`pp.txt:27316`) and `List(20)` turbo key ids (`pp.txt:57877`) — neither is a DPI table. |
| selector→DPI mapping resolved here? | **no** — there is nothing to resolve in 2.22; the mapping remains UNKNOWN in *all* builds (see `dpi-history.md`) |
| reply parser resolved? | **no** — 2.22 has none; UNKNOWN in all builds |

## 4. Missing evidence / what would close it

* For 2.22 the DPI *feature* was simply not shipped in the app; nothing static can be recovered.
  A live capture on 2.22-era firmware is the only way to know whether the device accepted DPI
  commands from an older/other app revision.
* Across builds, the two standing gaps are unchanged and are **not** 2.22-specific:
  1. the **selector → real-DPI-value** table (the byte is a 4-bit selector; the numbers are
     server-supplied), and
  2. the **DPI reply parser** (write frames are byte-exact; the notification handler was never
     located).
  Closing either needs a live BLE capture or a server-response dump, not more static work.

## 5. Test vectors

None — no DPI frame exists in 2.22 to vectorise. (Baseline vectors for 4.0.8 remain in
`baselines/imported-research/fc-dpi-test-vectors.json`.)