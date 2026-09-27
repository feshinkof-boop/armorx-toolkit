# Lighting implementation history — BIGBIG WON 2.22.0901 → 2.23.0609 → 2.24.0919 → 4.0.8

The **2.22** column is PROVEN STATIC from this pass (`static/blutter/2.22.0901/blutter_out`).
The 2.23/2.24/4.0.8 columns are **historical evidence** quoted from
`results/version-diff/static-version-matrix.md` and `baselines/imported-research/ff-lighting.md`
(**not** re-derived in this pass, except where noted as re-checked against
`/home/salamanka/armorx-re/mygt408/blutter_out`).

| aspect | 2.22.0901 | 2.23.0609 *(hist.)* | 2.24.0919 *(hist.)* | 4.0.8 *(hist.)* |
|---|---|---|---|---|
| writer(s) | **`writeLightConfig` only** | `writeLightConfig` (`A5`+`A4/FF`) | same + `0x0D writeLogoColorConfig` | `writeLightConfig`, `writeLightConfigR3` (`A5 10 70`), `writeApplyLightR3Common` (`A5 04 70`) |
| `0x70` opcode | **present** (inside generic `writeLightConfig`) | not stated | not stated | present (R3 paths) |
| `0x05`/`0x3F` sub-command constants | not found | — | — | present in main `writeLightConfig` |
| `0xF8` brightness comp | **NOT PRESENT** | not stated | **present** | present (7/8-byte frame) |
| `0xDD` charging light | **NOT PRESENT** | — | **present** | present |
| `0xF7` step/trigger travel | **NOT PRESENT** | — | **present** | present |
| `0xE1` connect mode | **NOT PRESENT** | — | present | present |
| `0x73`/`0xF5` | **NOT PRESENT** | — | — | present |
| LED-id bitmask helpers (`encodeLedIdBit`, `lightIdsToMask`) | **NOT PRESENT** | not stated | not stated | present |
| zone model | **two lists**: `LightData.leftList` / `.rightList` | — | — | 4 areas (`LightColorArea`: direction/fight/mapping/all-area) + LED-id bitmasks, `0x3F` 6-bit LED space |
| `LightColorRainBow3` / `LightDataR3` / `lightColorMapInit` | **NOT PRESENT** | — | present (`LightDataR3`) | present |
| colour arity | **3 bytes/colour** (`changeLightColorList` `mul ×3`) | not stated | not stated | 3-element groups (`changeLightColorList` present) |
| `LightData` JSON keys | **6**: `leftList rightList mode speed bright same` | — | — | **7** (per `ff-lighting.md`) |
| RGB byte order | **UNKNOWN** | UNKNOWN | UNKNOWN | UNKNOWN |
| effect ids | observed **{2, 6}** at 2 call sites; enum table UNKNOWN | — | — | UNKNOWN (mode indices 2/4/6 observed per-zone) |
| mode names (l10n) | `Normal`, `Breathing`, `Gradient`, `Flicker` (4) | — | — | UI lives in `rainbow3_*` |
| brightness range | slider **50–255** (divisions 255) | — | — | **no `double(50)`** in 4.0.8's gamepad light files (re-checked) — the 50-floor looks 2.22-specific |
| speed range | slider **0–255** (divisions 255) | — | — | UNKNOWN |
| persistence | not in config buffer; UI `saveLightConfig`/`getDefaultLight`/`setDefaultLight`/`resetLight` | — | — | not in config buffer; command-queued |
| defaults in assets | **none** (2.22 has 15 asset files, no config/light blob) | default-config literals in `pp.txt` | same | 12 default images, 6 CRC-validated |

## Evolution summary

1. **2.22.0901** — minimal single-writer lighting: one generic `writeLightConfig`
   (`A5 <len> 70 …` control frame + `A4` data frame), 3-byte RGB triplets, a 6-key `LightData`
   model with `leftList`/`rightList` (2 zones), 4 named modes, 6 colour presets, brightness 50–255,
   speed 0–255. No bitmask helpers, no R3 API, no brightness-comp/charging/step/connect-light ops.
2. **2.24.0919** — adds `0x0D`, `0xF6/F7/F8`, `0xE1` and the R3 light model (`LightDataR3`,
   `LightColorRainBow3`); LED sets become **bitmasks** with a `0x3F` (64-entry) LED id space.
   *(historical)*
3. **4.0.8** — full R3 API: `A5 10 70` / `A5 04 70`, `LightColorArea` 4-colour-group zone model,
   7-key `LightData`, `0xDD` charging light, `0x73`/`0xF5`, `0x0D` logo colour. *(historical)*

**Nothing that was UNKNOWN in the later builds is resolved by 2.22.** In particular the **RGB byte
order** and the **effect-id enum** remain UNKNOWN in *all four* builds; 2.22 adds no anchor for
either (it has no `parseColor`/`toColor` equivalent). 2.22 does add one new, independently useful
fact: the **brightness floor of 50/255** on the ARMOR-X Pro light slider, which is *absent* from
4.0.8's gamepad light code (re-checked: `double(50)` occurs only in 4.0.8's keyboard / curve-editor
widgets, not in its gamepad light tabs → the gamepad slider there appears to be 0–255).