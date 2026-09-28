# Protocol closure: FC/DPI, AB/motion, lighting (Parts D, E, F)

Consolidated 2026-09-27/28 during the autonomous shift. Nothing here was tested on hardware; this
document closes what can be closed statically, states what stays UNKNOWN, and pre-commits the first
safe step for each family. Grades: PROVEN LIVE / PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN /
NOT PRESENT / CONTRADICTED.

Source evidence (not re-derived here): `results/version-diff/dpi-history.md`,
`results/version-diff/lighting-history.md`, `results/static/2.22.0901/{fc-dpi,lighting}.md`,
`results/final/real-dpi.md`, `results/final/real-lighting.md`, `automation/scripts/armorx_lab/frames.py`.

## D — FC / DPI

| question | answer | grade |
|---|---|---|
| query vs write | there are **two** paths: a query (`A5 05 FC 80` on the wire) and a writer (`writeDpiConfig` → `A5 05 FC <selector & 0x0F> <cks>`) | PROVEN STATIC |
| the live query | TX `a5 05 fc 80 26` → RX `a5 05 ff fc a5`, both checksum-valid | **PROVEN LIVE** |
| selector meaning | a **4-bit selector**; the app's presets are server-side, so the selector→DPI table is not in the binary | UNKNOWN |
| response shape | the live reply is `a5 05 ff fc a5`; its field semantics are not decoded | UNKNOWN |
| bounds / validation | no bound check found in the builder beyond the `& 0x0F` mask | UNKNOWN |
| per-axis / per-profile | not established | UNKNOWN |
| version history | 2.22: **NOT PRESENT** (proven negative, exhaustive search); 2.23: `FC` introduced; 2.24: `FC`+`F6`; 4.0.8: `FC`+`F6`+`AB` family | PROVEN STATIC |

**Do not** assign a numeric DPI value: the selector mapping is not evidenced and the app derives it
from its own server-side presets.

**Read-first future experiment:** on the next live connection, re-read `A5 05 FC 80 26` and compare with
the recorded `a5 05 ff fc a5`. Only if that reply is decoded should a same-value no-op write be
considered, with the original selector captured first and a restore path proven.

## E — Motion / gyro (AB family)

| question | answer | grade |
|---|---|---|
| frame family | **`AB`**, not `A5` — `AB 05 05 25 DA` and `AB 05 05 26 DB` are the query shapes (checksum-valid) | PROVEN STATIC + the earlier live TX rows, corrected |
| writer | `writeMotionDpiConfig` @ `0x946158`, `AB 07 05 25 <u16 LE> <cks>` | PROVEN STATIC |
| corresponding reads | `getMotionDpi` (`AB 05 05 25`) and `getMotionList` (`AB 05 05 26`) | PROVEN STATIC |
| live result | both queries returned **NOTHING** while an immediately following `0B` was answered — i.e. no reply on this firmware | **PROVEN LIVE** (negative) |
| payload fields (mode / sensitivity / deadzone / filter) | the writer's `<u16 LE>` is a value field; which mode/axis it belongs to is not established | UNKNOWN |
| version gates | the whole `AB` family is **absent in 2.22 and 2.23 and 2.24**; it appears in 4.0.8 | PROVEN STATIC |

**Consequence:** "the device ignores the AB query" and "the AB query is not implemented on this
firmware" are both consistent with the capture; the module may simply be absent. That is why the
negative is recorded as a live negative and not as a device fault.

**Future plan (unchanged in spirit):** query original → same-value no-op → a single controlled
mutation → restore. Nothing before a reply is obtained, because without a reply there is no readback
and therefore no safe write.

## F — Lighting / RGB

| question | answer | grade |
|---|---|---|
| writer(s) in 4.0.8 | `writeLightConfig` (`A5` short + `A4` long/data frames, opcode `0x70`), plus `writeLightConfigR3` (`A5 10 70`) and `writeApplyLightR3Common` (`A5 04 70`) | PROVEN STATIC |
| writer in 2.22 | a single generic `writeLightConfig` present @ `0x7a72fc`; R3 paths **NOT PRESENT** | PROVEN STATIC |
| zone / RGB bytes / brightness / effect / speed / enable | the builders exist and carry sub-commands (`0x05`/`0x3F` constants in 4.0.8) but the **field layout is not established** | UNKNOWN |
| **RGB byte order** | **UNKNOWN in all four builds** — no anchor exists in the code | UNKNOWN |
| effect ids | `{2, 6}` observed at two 2.22 call sites; the enum table is UNKNOWN; 4.0.8 shows mode indices 2/4/6 per zone | UNKNOWN |
| speed range | a 0–255 slider in 2.22; wire encoding UNKNOWN | UNKNOWN |
| persistence | not established: no readback path was found for lighting, so a write's durability cannot be verified by readback today | UNKNOWN |
| read/query path | **none found** in any build | NOT PRESENT (proven negative) |

**Consequence and honest limit:** because no lighting read/query exists, a lighting write cannot be
verified by readback. Any future lighting experiment must therefore be **visually** verified by the
operator and must change exactly one field that can be reverted, with the original value captured
first.

**Minimum future reversible experiment:** with the original state recorded, set one zone to a single
known colour via the smallest writer path, confirm the *visible* effect, then restore the original and
confirm restoration visibly. No RGB-order claim may come out of this until two different colours
discriminate the channel order.

## Cross-family summary

| family | wire family | query exists | writer exists | live evidence | biggest UNKNOWN |
|---|---|---|---|---|---|
| DPI | `A5 05 FC ..` | yes (`FC 80`) | yes (`FC <sel&0x0F>`) | reply captured | selector→DPI mapping |
| motion/gyro | `AB 05 05 25/26` | yes (static) | yes (`AB 07 05 25`) | **no reply** | payload field semantics |
| lighting | `A5`/`A4` opcode `0x70` | **no** | yes | none | RGB byte order + field layout |
