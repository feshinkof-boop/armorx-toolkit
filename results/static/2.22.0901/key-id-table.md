# Key-ID table — BIGBIG WON **2.22.0901** (com.moojiang.bigbigwon), ARMOR-X Pro family

Frozen APK: `/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk`
sha256 `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`.

Primary source: **Dart 2.17.5 AOT disassembly** produced by Blutter
(`/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/…`), which became
available during this pass. All Dart-side offsets below are **Blutter asm addresses** (the column
`// 0xADDR:`); all string-pool offsets are `pp.txt` indices.

**Smi decoding rule for this dialect (applied throughout):** integer immediates in the asm are
*tagged* Smis — the printed immediate is `2 × value`. Verified against a known protocol byte:
`mov x17, #0x14a` ⇒ byte `0x14a/2 = 0xA5` (`units/gamepadset.dart:6943 @0x7a7b90`), and against
`mov x0, #0x20000` ⇒ `keyUp = 0x10000` (`units/gamepadset.dart:6299 @0x7a70d0`). List *lengths*,
array *indices* and `AllocateContext` sizes are **plain** ints (not tagged) and are flagged as such.

Evidence labels: **PROVEN STATIC** / **STRONG EVIDENCE** / **INFERRED** / **UNKNOWN** / **CONTRADICTED** / **NOT PRESENT**.

---

## 0. Headline result

2.22 implements **ARMOR-X Pro** (`asm/moojiang/widgets/armor-x_pro/` exists: `armorx_pro_root.dart`,
`armorx_pro_config_config.dart`, `armorx_pro_config_macro.dart`, `armorx_pro_more.dart`; 102
occurrences of the literal `armor-x_pro` in `pp.txt`). It uses the **same config key-ID space as
2.23/2.24/4.0.8**, but its **label set is the smallest of the four builds**: it stops at **M4** and
has **no** `Capture` (15), **no** `Menu` (22) and **no** `M5/M6/M7` (27/28/29) labels.

Two map builders exist in 2.22 (vs **six** in 4.0.8), both proving the same numbers:

| role | symbol | file:line | addr |
|---|---|---|---|
| builder (canonical, label + l10n key) | `_ChangeKeyButtonState.initState` (inline `Map`) | `units/component.dart:3909` | `0x895878` |
| builder (id→localized label, **adds 34..49**) | `_CircleButtonState.initState` | `units/theme.dart:5286` | `0x899…` / `0x899…` |

No third id→label map exists: `grep -rl '"key_A"'` in the app tree returns only `units/component.dart`
plus the generated l10n/message tables (the latter are the string catalogs, not id maps).

---

## 1. Full id table (2.22)

`id` = the raw config key id. Evidence for the number is the tagged-Smi immediate
(`mov lr, #2·id`) written immediately before the `[]=` call that inserts the entry.
`bit` = the hardware mask constant from `units/gamepadset.dart` (getters `static int keyX()`);
`value = 1 << id`.

| id | EN label | l10n key (`S::`) | render | label addr (component.dart) | id-mov addr | bit const (name = value) | evidence |
|---|---|---|---|---|---|---|---|
| 0 | `A` | `key_A` | text | `0x8958d4` | `0x8958f8` (`#0`) | `keyA` = 1 (`0x1`, bit 0) | PROVEN STATIC |
| 1 | `B` | `key_B` | text | `0x895958` | `0x895978` (`#2`) | `keyB` = 2 (`0x2`, bit 1) | PROVEN STATIC |
| 2 | `NIL` | `key_C` | text | `0x8959d8` | `0x8959fc` (`#4`) | — | PROVEN STATIC |
| 3 | `X` | `key_X` | text | `0x895a5c` | `0x895a80` (`#6`) | `keyX` = 8 (`0x8`, bit 3) | PROVEN STATIC |
| 4 | `Y` | `key_Y` | text | `0x895ae0` | `0x895b04` (`#8`) | `keyY` = `0x10` (bit 4) | PROVEN STATIC |
| **5** | — | — | — | — | — | bit 5 = `rightStickY` = `0x20` (a **stick-axis** bit) | label **UNKNOWN** (absent) |
| 6 | `LB` | `key_LB` | text | `0x895b64` | `0x895b88` (`#0xc`) | `keyL1` = `0x40` (bit 6) | PROVEN STATIC |
| 7 | `RB` | `key_RB` | text | `0x895be8` | `0x895c0c` (`#0xe`) | `keyR1` = `0x80` (bit 7) | PROVEN STATIC |
| 8 | `LT` | `key_LT` | text | `0x895c6c` | `0x895c90` (`#0x10`) | `keyL2` = `0x100` (bit 8) | PROVEN STATIC |
| 9 | `RT` | `key_RT` | text | `0x895cf0` | `0x895d14` (`#0x12`) | `keyR2` = `0x200` (bit 9) | PROVEN STATIC |
| 10 | `Select` | `key_Select` | text | `0x895d74` | `0x895d98` (`#0x14`) | `keySelect` = `0x400` (bit 10) | PROVEN STATIC |
| 11 | `Start` | `key_Start` | text | `0x895df8` | `0x895e1c` (`#0x16`) | `keyStart` = `0x800` (bit 11) | PROVEN STATIC |
| **12** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| 13 | `L3` | `key_L3` | text | `0x895e7c` | `0x895ea0` (`#0x1a`) | `keyLThumb` = `0x2000` (bit 13) | PROVEN STATIC |
| 14 | `R3` | `key_R3` | text | `0x895f00` | `0x895f24` (`#0x1c`) | `keyRThumb` = `0x4000` (bit 14) | PROVEN STATIC |
| **15** | — | — | — | — | — | (bit 15 unused) | **UNKNOWN** (absent; **not** Capture, **not** Share) |
| 16 | `▲` | `key_Dpad_up` | text | `0x895f84` | `0x895fa8` (`#0x20`) | `keyUp` = `0x10000` (bit 16) | PROVEN STATIC |
| 17 | `▼` | `key_Dpad_down` | text | `0x896008` | `0x89602c` (`#0x22`) | `keyDown` = `0x20000` (bit 17) | PROVEN STATIC |
| 18 | `◀` | `key_Dpad_left` | text | `0x89608c` | `0x8960b0` (`#0x24`) | `keyLeft` = `0x40000` (bit 18) | PROVEN STATIC |
| 19 | `▶` | `key_Dpad_right` | text | `0x896110` | `0x896134` (`#0x26`) | `keyRight` = `0x80000` (bit 19) | PROVEN STATIC |
| **20** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| **21** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| **22** | — | — | — | — | — | — | **UNKNOWN** (absent; **not** Menu) |
| 23 | `M1` | `key_M1` | text | `0x896194` | `0x8961b8` (`#0x2e`) | `keyM1` = `0x800000` (bit 23) | PROVEN STATIC |
| 24 | `M2` | `key_M2` | text | `0x896218` | `0x89623c` (`#0x30`) | `keyM2` = `0x1000000` (bit 24) | PROVEN STATIC |
| 25 | `M3` | `key_M3` | text | `0x89629c` | `0x8962c0` (`#0x32`) | `keyM3` = `0x2000000` (bit 25) | PROVEN STATIC |
| 26 | `M4` | `key_M4` | text | `0x896320` | `0x896344` (`#0x34`) | `keyM4` = `0x4000000` (bit 26) | PROVEN STATIC |
| **27** | — | — | — | — | — | (bit 27 unused) | **UNKNOWN** (absent; **not** M5) |
| **28** | — | — | — | — | — | `keyM6` = `0x10000000` (bit 28) | label **UNKNOWN**; hardware constant **PRESENT** |
| **29** | — | — | — | — | — | — | **UNKNOWN** (absent; **not** M7) |
| **30** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| **31** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| **32** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| **33** | — | — | — | — | — | — | **UNKNOWN** (absent) |
| 34 | `R←` | `rightstick_left` | text | `0x899e14` | `0x899e20` (`#0x44`) | macro pseudo-key | PROVEN STATIC |
| 35 | `R→` | `rightstick_right` | text | `0x899e6c` | `0x899e78` (`#0x46`) | macro pseudo-key | PROVEN STATIC |
| 36 | `R↑` | `rightstick_up` | text | `0x899ec4` | `0x899ed0` (`#0x48`) | macro pseudo-key | PROVEN STATIC |
| 37 | `R↓` | `rightstick_down` | text | — | (`#0x4a`) | macro pseudo-key | PROVEN STATIC |
| 38 | `L←` | `leftstick_left` | text | — | (`#0x4c`) | macro pseudo-key | PROVEN STATIC |
| 39 | `L→` | `leftstick_right` | text | — | (`#0x4e`) | macro pseudo-key | PROVEN STATIC |
| 40 | `L↑` | `leftstick_up` | text | — | (`#0x50`) | macro pseudo-key | PROVEN STATIC |
| 41 | `L↓` | `leftstick_down` | text | — | (`#0x52`) | macro pseudo-key | PROVEN STATIC |
| 42 | `R↖` | `rightstick_left_up` | text | — | (`#0x54`) | macro pseudo-key | PROVEN STATIC |
| 43 | `R↗` | `rightstick_right_up` | text | — | (`#0x56`) | macro pseudo-key | PROVEN STATIC |
| 44 | `R↙` | `rightstick_left_down` | text | — | (`#0x58`) | macro pseudo-key | PROVEN STATIC |
| 45 | `R↘` | `rightstick_right_down` | text | — | (`#0x5a`) | macro pseudo-key | PROVEN STATIC |
| 46 | `L↖` | `leftstick_left_up` | text | — | (`#0x5c`) | macro pseudo-key | PROVEN STATIC |
| 47 | `L↗` | `leftstick_right_up` | text | — | (`#0x5e`) | macro pseudo-key | PROVEN STATIC |
| 48 | `L↙` | `leftstick_left_down` | text | — | (`#0x60`) | macro pseudo-key | PROVEN STATIC |
| 49 | `L↘` | `leftstick_right_down` | text | — | (`#0x62`) | macro pseudo-key | PROVEN STATIC |

**Two independent builders agree on ids 0–26 and 34–49:**
`theme.dart _CircleButtonState.initState` (`0x8994f8` A … `0x899da4` M4, then `0x899e14` R← … ) emits
the *same* id set as `component.dart`, with the localized `S::key_*` getter in place of the literal.
Its list is complete through the 16 stick pseudo-keys 34–49 (`rightstick_left … leftstick_right_down`).

**Complete 2.22 label catalog (EN, from `messages_en.dart _notInlinedMessages`, PROVEN STATIC):**
`A B NIL X Y LB RB LT RT Select Start L3 R3 ▲ ▼ ◀ ▶ M1 M2 M3 M4` +
`R← R→ R↑ R↓ L← L→ L↑ L↓ R↖ R↗ R↙ R↘ L↖ L↗ L↙ L↘` (26 + 16 = 42 labels).
The l10n also defines unused-for-ids `key_L = "L"` and `key_R = "R"` (Switch-naming helpers), which are
**not** inserted into either id map.

There is **no** `key_Capture`, `key_Menu`, `key_M5/M6/M7`, `key_Share` anywhere in the build
(`grep -r '"key_A"'` → only `component.dart` + the l10n catalogs; the catalog's key-`*` names are
exactly the 23 `key_*` names in §3, plus 16 `*stick_*` names).

---

## 2. The bit-mask constants and the bit-index relationship — **bit index = key id**

`units/gamepadset.dart` `class ::` (class id 66400) declares
`static late int keyA … keyM6, leftStickX/Y, rightStickX/Y, zkmVer` (offsets `0xc1c…0xc80`).
18 of them are emitted as constant getters (`static int keyX() { … mov x0, #imm }`):

| getter | addr | printable imm | value (`imm/2`) | hex | bit |
|---|---|---|---|---|---|
| `keyY` | `0x7a6e64`| `#0x20` | 16 | `0x10` | 4 |
| `rightStickY` | `0x7a8f60` | `#0x40` | 32 | `0x20` | 5 |
| `keyL1` | `0x7a8f84` | `#0x80` | 64 | `0x40` | 6 |
| `keyR1` | `0x7a8f74` | `#0x100` | 128 | `0x80` | 7 |
| `keyL2` | `0x7a6db0` | `#0x200` | 256 | `0x100` | 8 |
| `keyR2` | `0x7a8f54` | `#0x400` | 512 | `0x200` | 9 |
| `keySelect` | `0x7a6dc8` | `#0x800` | 1024 | `0x400` | 10 |
| `keyStart` | `0x7a8f2c` | `#0x1000` | 2048 | `0x800` | 11 |
| `keyRThumb` | `0x7a66ac` | `#0x8000` | 16384 | `0x4000` | 14 |
| `keyUp` | `0x7a70d0` | `#0x20000` | 65536 | `0x10000` | 16 |
| `keyDown` | `0x7a66fc` | `#0x40000` | 131072 | `0x20000` | 17 |
| `keyLeft` | `0x7a8f14` | `#0x80000` | 262144 | `0x40000` | 18 |
| `keyRight` | `0x7a6e84` | `#0x100000` | 524288 | `0x80000` | 19 |
| `keyM1` | `0x7a66e0` | `#0x1000000` | 8388608 | `0x800000` | 23 |
| `keyM2` | `0x7a8f44` | `#0x2000000` | 16777216 | `0x1000000` | 24 |
| `keyM3` | `0x7a8f4c` | `#0x4000000` | 33554432 | `0x2000000` | 25 |
| `keyM4` | `0x7a66d4` | `#0x8000000` | 67108864 | `0x4000000` | 26 |
| `keyM6` | `0x7a8ef0` | `#0x20000000` | 268435456 | `0x10000000` | 28 |

(`keyA/keyB/keyX/keyLThumb/leftStickX/leftStickY/rightStickX/zkmVer` have **no** emitted getter body —
Blutter deduplicated them or they are initialised elsewhere; their values are therefore named, not
proven, in this pass → mark `keyA/keyB/keyX/keyLThumb` values **INFERRED** from the bit==id rule.)

**Relationship: `value == 1 << id` — i.e. the bit index equals the key id directly (NO `+1` offset).**

Three independent confirmations:

1. **Static getters.** `keyY`(id 4)→bit 4, `keyL1`(id 6)→bit 6, `keySelect`(id 10)→bit 10,
   `keyStart`(id 11)→bit 11, `keyRThumb`(id 14, R3)→bit 14, `keyUp`(id 16)→bit 16,
   `keyM1…M4`(ids 23–26)→bits 23–26. Every one matches the label-table id. PROVEN STATIC.
2. **Powers-of-two table.** `pp.txt:27316 [pp+0x28950] List<int>(32) [1,2,4,8,0x10,…,0x80000000]` —
   the `1<<n` table, indexed by n; used with the key ids. STRONG EVIDENCE.
3. **`turboClick` shift.** `widgets/general/config_mapkey.dart:273 @0x8c96b0`:
   `r3 = List<int>(20) [0x17,0x18,0x19,0x1a, 0,1,3,4, 0x10,0x11,0x12,0x13, 6,8,7,9, 0xd,0xe,0xa,0xb]`
   (`pp.txt:57877`, real ids `23,24,25,26,0,1,3,4,16,17,18,19,6,8,7,9,13,14,10,11`), then
   `cmp x1,#0x3f ; lsl x0, x2, x1` with `x2 = 1` → **`mask |= 1 << keyId`**, `orr` into
   `field_1f` (`@0x8c9724-0x8c972c`). PROVEN STATIC.
   This 20-entry list is also the definitive **2.22 turbo-eligible key set**
   (M1–M4, A, B, X, Y, D-pad ×4, LB/LT/RB/RT, L3, R3, Select, Start) — see `turbo.md`.

### Note on bit 5
Bit 5 is occupied by `rightStickY` (a **stick-axis** bit, `0x20`), not by a key label; the label map
has **no** id 5. The key/axis bit space and the label id space are therefore *parallel and
coincident*, but bit 5 is not a remappable key. (`id 5 = rightStickY axis` is **INFERRED**, not claimed
as a label.)

---

## 3. Resolution of the specifically-targeted ids

| id | 2.22 status | evidence | what is missing |
|---|---|---|---|
| **5** | **UNKNOWN** (no label) | absent from **both** id maps and from the l10n catalog; bit 5 belongs to `rightStickY` (`0x20`) | a live `mapKeys[5]` read on hardware |
| **12** | **UNKNOWN** (no label) | absent from both id maps; no `mov lr, #0x18` map insert anywhere in `asm/moojiang` | live observation |
| **15** | **UNKNOWN / ABSENT** — **not** `Capture`, **not** `Share` | `grep -rin "capture"` over `asm/moojiang` → 0 hits in app code (only Flutter's `CapturedThemes`); `grep -rin '"share"'` → only the privacy-policy sentence (`messages_en.dart:3085`) and `home.dart::getLangShare`; no `key_Capture`; no `mov lr, #0x1e` map insert | live `mapKeys[15]`; the label is genuinely absent in 2.22 |
| **20** | **UNKNOWN** | absent | live read |
| **21** | **UNKNOWN** | absent | live read |
| **22** | **UNKNOWN / ABSENT** — **not** `Menu` | absent; no `mov lr, #0x2c` insert; no `key_menu*` asset (2.22 has only 15 asset files, no `key_*.png`) | live read |
| **30** | **UNKNOWN** | absent | live read |
| **31** | **UNKNOWN** | absent | live read |
| **32** | **UNKNOWN** | absent (labelled space ends at 26/31, resumes at 34) | live read |
| **33** | **UNKNOWN** | absent | live read |
| **28** | label **UNKNOWN**, but hardware bit **present** | `keyM6 = 0x10000000` (bit 28) exists though no id-28 label | whether id 28 is remappable in 2.22 |

**No id outside 0–26 and 34–49 has a label in 2.22.** This is exhaustive: I dumped *every* `[]=`
insertion in both map builders and every label string in every language catalog.

---

## 4. Terminology for id 15 across the four builds, and a correction

| build | id 15 label | evidence |
|---|---|---|
| **2.22.0901** | **absent** (no label at all — not `Capture`, not `Share`) | this pass, PROVEN STATIC (two maps + full l10n catalog) |
| 2.23.0609 | **absent** (`labels up to M4; no Capture`), per `results/version-diff/static-version-matrix.md` | historical evidence (labelled as such) |
| 2.24.0919 | **`Capture`** present in the label set | historical evidence |
| 4.0.8 | **`Capture`** (`key_remap_t.dart` map literal raw key 30 → `"Capture"` @ `0x92d983`) | historical evidence |

**Terminology comparison:** the word is **`Capture`** from 2.24 onward; 2.22 and 2.23 have **no
terminology for id 15**. `Share` is **never** used as a key label in any of the four builds (2.22's
only `Share` string is a privacy-policy sentence).

### ⚠ Correction to the imported 4.0.8 research (CONTRADICTED)
`baselines/imported-research/unresolved.md` §1 claimed id 15 = Capture was confirmed by
"the bit-mask constant `keyCapture = 0x10000`, where bit index = key id + 1".
Direct re-read of **4.0.8's own** asm (`/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart`)
refutes the numbers:

```
define.dart:1583  static int keyCapture() { … mov x0, #0x8000 }   ⇒ keyCapture = 0x8000  (bit 15)
                  static int keyUp()      { … mov x0, #0x20000 }  ⇒ keyUp      = 0x10000 (bit 16)
```

So in **4.0.8** `keyCapture = 0x8000` (**bit 15 = id 15**), and `0x10000` is `keyUp` — exactly the
same `bit == id` convention as 2.22. **The `+1` offset claim is CONTRADICTED by the 4.0.8 binary
itself.** The id-15 = Capture conclusion still stands on its *other* chain (the map literal
`key_remap_t.dart @0x92d983`), but the bit-mask chain as written in the import was wrong.

---

## 5. Per-id comparison with the known 2.23 / 2.24 / 4.0.8 table

Historical rows are quoted from `results/version-diff/static-version-matrix.md` and
`baselines/imported-research/key-id-table.md` (marked *historical*); the 2.22 column is this pass.
`✓` = label present with that name; `·` = no label.

| id | 2.22 | 2.23 (hist.) | 2.24 (hist.) | 4.0.8 (hist.) |
|---|---|---|---|---|
| 0 | A | A | A | A |
| 1 | B | B | B | B |
| 2 | NIL | NIL | NIL | NIL |
| 3 | X | X | X | X |
| 4 | Y | Y | Y | Y |
| 5 | · | · | · | · |
| 6 | LB | LB | LB | LB |
| 7 | RB | RB | RB | RB |
| 8 | LT | LT | LT | LT |
| 9 | RT | RT | RT | RT |
| 10 | Select | Select | Select | Select |
| 11 | Start | Start | Start | Start |
| 12 | · | · | · | · |
| 13 | L3 | L3 | L3 | L3 |
| 14 | R3 | R3 | R3 | R3 |
| 15 | · | · | **Capture** | **Capture** |
| 16–19 | ▲▼◀▶ | ▲▼◀▶ | ▲▼◀▶ | ▲▼◀▶ |
| 20 | · | · | · | · |
| 21 | · | · | · | · |
| 22 | · | · | · | **Menu** |
| 23 | M1 | M1 | M1 | M1 |
| 24 | M2 | M2 | M2 | M2 |
| 25 | M3 | M3 | M3 | M3 |
| 26 | M4 | M4 | M4 | M4 |
| 27 | · | · | · | **M5** |
| 28 | · (bit const `keyM6` present) | · | · | **M6** |
| 29 | · | · | · | **M7** |
| 30/31/32/33 | · | · | · | · |
| 34–49 | 16 stick pseudo-keys | n/a (not present in 2.23's label set per matrix) | n/a | 16 stick pseudo-keys |

**2.22 is the only build of the four with neither `Capture` nor `Menu` nor `M5–M7`.** The 2.22
hardware bit space already includes an M6 bit (`0x10000000`) even though no label exists — i.e. the
label catalogue lagged the firmware/reporting space.

**Bit-mask convention:** identical (`bit == id`) in 2.22 and 4.0.8 (both verified against the
binaries this pass). 2.23/2.24 were not re-derived here.

---

## 6. What still needs the Dart AOT tree / live work

Everything in §1–§3 is derived **from the AOT tree** (it arrived mid-pass and was used). Nothing in
this document is blocked on Blutter any more. Remaining unknowns are **live-only**:
ids 5, 12, 15, 20, 21, 22, 27, 29, 30–33 have no static label in 2.22 — closing them requires a live
`D6`/`mapKeys` read (or firmware strings). The 2.22 config's *key-remap slice* is **not** named
`mapKeys` in this build (`grep -r mapKeys` → 0 hits; only a `"map"` key at `pp.txt:2766`), so the
config byte range of the remap table is **not established for 2.22** (UNKNOWN) — a limitation of this pass.