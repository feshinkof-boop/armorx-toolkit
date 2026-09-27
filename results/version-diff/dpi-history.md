# DPI implementation history — BIGBIG WON 2.22.0901 → 2.23.0609 → 2.24.0919 → 4.0.8

Cross-version archaeology. The **2.22** column is PROVEN STATIC from this pass (Blutter tree
`static/blutter/2.22.0901/blutter_out`). The 2.23/2.24/4.0.8 columns are **historical evidence**
quoted from `results/version-diff/static-version-matrix.md` and
`baselines/imported-research/fc-dpi.md`; they were **not** re-derived in this pass and are marked
*(historical)*.

| aspect | 2.22.0901 | 2.23.0609 *(historical)* | 2.24.0919 *(historical)* | 4.0.8 *(historical)* |
|---|---|---|---|---|
| normal-DPI builder | **NOT PRESENT** | `writeDpiConfig` → `A5 05 FC <sel&0x0F> <cks>` | `A5 05 FC …` w/ `F6` branch | `A5 05 FC <sel&0x0F> <cks>` |
| legacy `F6` opcode | **not present** | **no F6 branch at all** | `F6` for `{devRainbow2Pro, devC2SL}` when version `>= 0x35` | `F6` for `{devRainbow2Pro, devRainbow3, devGale2, devC2SL}` when version `>= 0x35` |
| threshold test | n/a | n/a | `cmp x1,#0x35 ; b.lt <skip F6 store>` — **F6 when version >= 0x35** (corrected direction) | same, on static `0xb6c` |
| DPI query (`getDpi`) | **not present** | `A5 05 FC 80 00` *(historical)* | present | present |
| motion / gyro DPI (`AB`) | **not present** | **not present** | **not present** | `AB 07 05 25 <u16 LE> <cks>` (`writeMotionDpiConfig` @`0x946158`), query `getMotionDpi` |
| DPI UI control | **none** | none stated | none stated | `rainbow_more.dart` `selectDpi` / motion-report-rate picker (~line 8557) |
| DPI opcodes present in the app | none (`0xFC/F6/AB` all absent) | `FC` | `FC`,`F6` | `FC`,`F6`,`AB` |
| selector→DPI mapping | n/a | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** (payload is a 4-bit selector; values are app/server-side presets) |
| reply parser | n/a | **UNKNOWN** | **UNKNOWN** | **UNKNOWN** (notification handler never located) |

## Evolution summary

1. **2.22.0901 — no DPI at all.** Whole-app searches (`grep -rin dpi`, opcode-immediate scans,
   complete method inventory) return nothing; only `0xA5`/`0xA4`/`0x70` light opcodes exist.
   → **NOT PRESENT** (PROVEN STATIC).
2. **2.23.0609 — DPI introduced, single opcode.** `A5 05 FC <selector&0x0F>`, no `F6`, no device gate,
   no motion DPI. (historical)
3. **2.24.0919 — legacy path added.** `FC` default, `F6` substituted for two named devices when the
   version field `>= 0x35`; payload and framing unchanged. (historical)
4. **4.0.8 — two more devices gated, motion DPI added.** 4-device `F6` gate plus the `AB 07 05 25`
   16-bit-LE motion path, own UI picker. (historical, and note the corrected direction: F6 when
   version `>= 0x35`, not `<`).

**Nothing about the selector→DPI mapping or the reply parser is resolved in any build.** Both are
still UNKNOWN and are the two genuinely open DPI items; they are not recoverable
statically (server-supplied table + un-located notification handler).

## What is missing (evidence needed)

* selector → real DPI value table: needs the server `/dev/*` response (or a live UI→frame capture).
* DPI reply parser: needs the notification handler (a breakpoint on the BLE notify path) — the
  write frames are byte-exact in 2.23/2.24/4.0.8, the answer is not.
* 2.22: nothing static to recover — the feature is absent; a live capture on 2.22-era firmware is
  the only route.