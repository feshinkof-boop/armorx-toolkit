# Lighting in BIGBIG WON **2.22.0901** — ARMOR-X Pro

APK sha256 `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c`.
Source: Blutter AOT tree `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out`
(Dart 2.17.5, arm64). File of record: `asm/moojiang/units/gamepadset.dart`.

Evidence labels: PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN / NOT PRESENT.
**Smi rule** (this dialect): immediates stored into `List<int>` are tagged — printed `2×value`
(verified: `mov x17,#0x14a` ⇒ `0xA5`). Plain array indices / `AllocateContext` sizes are untagged.

---

## 1. Builder census in 2.22

| opcode / builder | 2.22 status | evidence |
|---|---|---|
| `writeLightConfig` (`A5`/`A4`/`0x70` family) | **PRESENT** (`static _ writeLightConfig` @ `units/gamepadset.dart:1722`, addr `0x7a72fc`; body closure `async_op` @ `0x7a74c4`, size `0x1a20` → `0x7a8ee4`) | PROVEN STATIC |
| `changeLightColorList` (colour-list normaliser) | **PRESENT** @ `units/gamepadset.dart:1534`, addr `0x7a70d8` | PROVEN STATIC |
| `0x70` light opcode | **PRESENT** — `mov x17, #0xe0` (⇒ `0x70`) at closure offsets `0x7a7ba0`, `0x7a8624` | PROVEN STATIC |
| `0xA5` short-frame header | **PRESENT** — `mov x17, #0x14a` (⇒ `0xA5`) at `0x7a7b90` (array-literal index 0) | PROVEN STATIC |
| `0xA4` long/data-frame header | **PRESENT** — `mov x17, #0x148` (⇒ `0xA4`) at `0x7a7b04` | PROVEN STATIC |
| `0xF8` `writeBriCompConfig` | **NOT PRESENT** (`#0x1f0` occurs only as a localization array index) | PROVEN STATIC (negative) |
| `0xDD` `writeChargingLightEffectConfig` | **NOT PRESENT** (`#0x1ba` only in l10n tables) | PROVEN STATIC (negative) |
| `0xF7` `writeStepLengthConfig` | **NOT PRESENT** | PROVEN STATIC (negative) |
| `0xE1` `writeConnectModeConfig` | **NOT PRESENT** | PROVEN STATIC (negative) |
| `writeLightConfigR3` / `writeApplyLightR3Common` / `LightDataR3` / `LightColorRainBow3` / `LightColorArea` | **NOT PRESENT** (0 grep hits) | PROVEN STATIC (negative) |
| `0x73`, `0xF5`, `0x0D writeLogoColorConfig` | **NOT PRESENT** | PROVEN STATIC (negative) |

**So 2.22 has exactly one lighting writer family** — a generic `writeLightConfig` emitting
`0xA5` control + `0xA4` data frames with the `0x70` opcode. The whole R3 light API and the
brightness-comp / charging-light / trigger-step / connect-mode commands that 4.0.8 has are **absent**.

## 2. Frame reconstruction (PARTIALLY RESOLVED)

Inside the `writeLightConfig` closure two growable `List<int>` frames are built:

* **Control frame (12 elements)** — `AllocateArray(12)` @ `0x7a7b84` (length 12 = **plain** int),
  populated at fixed slots:

  | list index | printed imm | value (imm/2) | meaning |
  |---|---|---|---|
  | 0 | `#0x14a` | **`0xA5`** | short-frame header |
  | 1 | `#0` | 0 | length byte — filled at runtime |
  | 2 | `#0xe0` | **`0x70`** | light opcode |
  | 3–5 | `#0` | 0 | payload bytes — filled at runtime |

  ⇒ frame shape **`A5 <len> 70 <payload…> <cks>`** (PROVEN STATIC for header/opcode/len slot;
  payload length and checksum position INFERRED from the `A5`-family convention
  `cks = sum(all) & 0xFF`, which is separately proven in this build by `getCheckSum`).

* **Data frame** — a second list whose header byte is `0xA4` (`0x7a7b04`), i.e. the
  `A4`-fragmented long-frame path (same split `A5` control + `A4` data as 4.0.8). STRONG EVIDENCE.

* A third list at `0x7a8624` again carries `0x70` — a second `0x70` payload (multi-frame send).

**Cross-check against the sibling pass** (`results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.md`)
which reports that 2.23/2.24/4.0.8 `writeLightConfig` emits frames with opcode **`FF`** and 4.0.8's
R3 paths use `0x70`: 2.22 is consistent with having **both** — a `0x70` at the control-frame slot
and a `255` (=`0xFF`) list constant (see below). Which of the two is the *data*-frame opcode in 2.22
is **UNKNOWN**; no `FF`-vs-`70` assignment is claimed here.

Other constants observed as list elements inside the closure (both decodings shown where the
tagged/plain status is not certain): `10`, `255`(`0xFF`), `1`, `0x0f`(15), `7`, `5`, `216`(=`0xD8`).
**`0xD8` as an element of a light list is unexplained (UNKNOWN)** — it is the macro opcode in the
`0xA4/D8` family, so either `writeLightConfig` re-uses it as a light sub-command or Blutter's
closure attribution spans two builders; flagged, not claimed.

**Checksum / framing helper:** `getCheckSum` @ `units/gamepadset.dart:87`, `getCRC` @ `:180`
(PROVEN STATIC, present as in later builds).

## 3. Colour representation and byte order

* `changeLightColorList` (`0x7a70d8`) is **byte-exact**: it reads the input list length (`sbfx`/tagged
  Smi) and builds a new `_GrowableList` of **`length × 3`** ints — `mov x16, #3 ; mul x1, x2, x16`
  @ `0x7a70fc-0x7a7100`. ⇒ **each colour is a 3-component triplet (RGB-style), 3 bytes per entry.**
  **PROVEN STATIC.**
* **RGB byte order inside the triplet is UNKNOWN.** The colours themselves travel as packed Dart
  `int`s (`LightColor.toList` @ `0x3d2664` is a `CompileFunction`-backed getter-generic and yields no
  byte order). The missing anchor is a `parseColor`/`toColor`-equivalent constant or a live frame;
  2.22 has no such helper exposed, so the verdict is **UNKNOWN with the anchor named**:
  `LightColor` field layout / the colour-int packing helper was not located.

## 4. Zones / LED sets, persistence, apply separation

* **No LED-id bitmask helpers exist in 2.22.** `encodeLedIdBit`, `lightIdsToMask`, `LightColorArea`
  (direction/fight/mapping/all-area) and the `0x3F` LED-mask constant are all **NOT PRESENT**
  (0 grep hits). 2.22's model is a plain two-zone one: the light JSON has `leftList` and `rightList`.
* **`LightData` JSON keys (PROVEN STATIC, from `LightData.fromJson` @ `0x7a448c` and
  `LightData.toJson` @ `0x16737`):** `leftList`, `rightList`, `mode`, `speed`, `bright`, `same`
  (6 keys; 4.0.8 has 7). ⇒ left zone colour list, right zone colour list, effect mode,
  animation speed, brightness, "same colour" flag.
* **Persistence / apply separation:** lighting is **not** part of the config buffer; it is sent as
  commands. In 2.22 the UI applies changes immediately via `writeLightConfig` and offers a separate
  `saveLightConfig` (`widgets/rainbow/rainbow_config_light.dart:4362`) / `resetLight`
  (`rainbow_tab_light.dart:4082`) / `getDefaultLight` (`rainbow_tab_light.dart:3963`) /
  `setDefaultLight` / `saveDefaultLight` / `setDefaultEffect` set — i.e. write-now vs
  read/write-default are separated at the UI level (PROVEN STATIC for the function set;
  device-side durability UNKNOWN).

## 5. Effect identifiers, brightness and speed ranges

* **Mode ids (effect ids).** The two `writeLightConfig` call sites in `rainbow_tab_light.dart`
  (`0x8da348`, `0x8da404`, …) set the mode argument to **`2`** and **`6`** at `0x8da2cc`
  (`mov x17, #2`) and `0x8da388` (`mov x17, #6`) into a scratch `field_f` before calling.
  ⇒ observed effect/mode values **{2, 6}** (PROVEN STATIC as observed; the full enum table is
  **UNKNOWN**, and mapping 2/6 to names is **not** justified).
* **Mode names present in the l10n catalog** (EN, from `messages_en.dart`): **`Normal`,
  `Breathing`, `Gradient`** (key `..._mode_colorful`), **`Flicker`** (key `..._mode_flashing`).
  ⇒ the 2.22 light-mode set is 4 named modes (PROVEN STATIC for the *names*; association to mode
  ids 2/6 etc. is UNKNOWN).
* **Colour presets** (EN): `Orange Red`, `Golden Age`, `Aqua Green`, `Light Azure`, `Rose Violet`,
  `Hot Pink`, plus `Customize` (`rainbow_newconfig_light_color00..05`, `_customize`).
* **Brightness / speed sliders** (`_RainbowLightLightState.build`, `rainbow_config_light.dart`):
  two `Slider` widgets are constructed (`0x941990` and `0x941d0c`):
  * Slider A: `min = double(50)`, `max = double(255)`, `divisions = 255`
    (`0x9419d8`/`0x9419e4` min, `0x9419e8`/`0x9419f4` max, `0x9419f8` divisions).
  * Slider B: `min = double(0)`, `max = double(255)`, `divisions = 255`
    (`0x941d54` min, `0x941cc4-0x941cd4` max, `0x941d64` divisions).
  * Assignment: Slider A ↔ `setLedBrightness` (`rainbow_config_light.dart:1452`, addr `0x8d64ac`),
  Slider B ↔ `setLedSpeed` (`:1571`, addr `0x8d61fc`) — by closure containment
  (A's closures `0x942368`/`0x942478` bracket the `setLedBrightness` call at `0x94240c`; B's closures
  `0x942104`/`0x942214` bracket the `setLedSpeed` call at `0x9421a8`). **INFERRED** (the two range
  pairs are PROVEN; which control is which is by closure order, not by a named argument).
  ⇒ **brightness range 50–255, speed range 0–255, both integer, 255 steps** (STRONG EVIDENCE).

## 6. `LightColorRainBow3` equivalent and byte-order verdict

2.22 has **no** `LightColorRainBow3` and **no** `LightColorArea`. The nearest equivalent is the
**`LightData` + 3-byte-colour-triplet** model (§3–§4). **Verdict on the colour triple:**
* the **arity is proven** (3 bytes per colour, `changeLightColorList`);
* the **field/byte order is UNKNOWN**, and the named missing anchor is the **colour-int packing
  helper** (equivalent of 4.0.8's `parseColor`/`toColor`), which does not exist in 2.22's asm tree.

## 7. Defaults found in assets / Dart literals

* `assets/flutter_assets/` in 2.22 contains **only 15 files** (`AssetManifest.json`,
  `FontManifest.json`, `NOTICES.Z`, 4 PNG/GIF images, fonts, cupertino/ toastify files) — **no
  default-config or default-lighting blob**.
* `pp.txt` has **no** `defaultConfig`/config-image literal and no `LightDataR3.lightColorMapInit`
  (that is a 4.0.8-only table).
* The only lighting defaults recoverable statically are the UI function pair
  `getDefaultLight`/`setDefaultLight`/`saveDefaultLight` (device/server-sourced); their **values are
  UNKNOWN** (they come from the device or `/dev/*` server response, not from the bundle).

## 8. What the Dart tree resolved vs what it blocked

* Resolved by the AOT tree: presence/absence of every builder, the `A5/A4/0x70` frame shape, the
  3-byte colour arity, the `LightData` key set, the slider ranges, the mode-name set.
* Still blocked (UNKNOWN, not hinted): **RGB byte order**, **mode-id ↔ name mapping**, **the `0xD8`
  list element's role**, and **device-side persistence**. None of these is reachable from static code
  alone in 2.22 — they need a live BLE capture.