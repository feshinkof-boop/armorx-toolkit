# BIGBIG WON 2.22.0901 — executive report

Autonomous static + dynamic pass, 2026-09-27. Evidence labels: **PROVEN LIVE** / **PROVEN STATIC** /
**STRONG EVIDENCE** / **INFERRED** / **UNKNOWN** / **CONTRADICTED**. Nothing from a later build is
reported here as a 2.22 fact without independent 2.22 evidence.

## 1–7. Identity

| # | Item | Value |
|---|---|---|
| 1 | Path | `/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk` (origin `~/Downloads/BIGBIG_WON_2.22.0901.apk`, byte-identical, `cmp` clean — the lab copy was created with `cp`, the original untouched) |
| 2 | SHA-256 | `785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c` (sha1 `b499545b…`, md5 `e3af489d…`, 27,608,134 B, mtime 2026-09-27 10:51:41 −04:00) |
| 3 | Package / version | `com.moojiang.bigbigwon`, versionName **2.22.0901**, versionCode **3**, minSdk 21, targetSdk 32, compileSdk 33, application class = default `android.app.Application`, 0 services / receivers / providers |
| 4 | Signer | CN=moojiang (C=cn/ST=sz/L=sz/O=moojiang/OU=moojiang), serial `5EA0DB29`, SHA-256 `54:72:58:CA:…:C7:8C` — **the same key as 2.23.0609** (v1 + v2, identical cert), *not* the debug key of 2.24 and not Play App Signing of 4.0.8. This extends the release-key lineage back to the earliest build analysed. |
| 5 | ABIs | `arm64-v8a`, `armeabi-v7a`, **`x86_64`** — so the build runs natively on an x86_64 host |
| 6 | Dart / Flutter | Dart **2.17.5 (stable)** in `libflutter.so` (PROVEN STATIC); Flutter **3.3.x** (INFERRED from the Dart/marker pairing — no version string in the bundle) |
| 7 | BLE library | **flutter_reactive_ble** — PROVEN STATIC (`bledata.proto` with `java_package com.signify.hue.flutterreactiveble`) and PROVEN LIVE (44 plugin classes found, 35 overloads hooked) |

## 8–10. ARMOR-X Pro and the device enum

* **8. Implemented — PROVEN STATIC, five anchors:** `asm/moojiang/widgets/armor-x_pro/{armorx_pro_root,armorx_pro_config_config,armorx_pro_config_macro,armorx_pro_more}.dart`; classes `ArmorXProScreen` / `ArmorXProWidget` / `ArmorXProConfigWidgetState` / `ArmorXProMacroWidgetState` / `ArmorXProMoreWidgetState`; object-pool literal `armor-x_pro` (102 hits); **scan prefix `"ARMOR-X Pro_"`**; the 144-byte serializer exists only in `armorx_pro_config_config.dart`. Earliest ARMOR-X-specific code: `_ArmorXProWidgetState::deviceConnected` @ `0x7a9e40`.
* **9. ARMOR-X enum id = 3** (PROVEN STATIC, `objs.txt` `off_8: int(0x3)`), i.e. history **3 → 6 → 8 → 10**.
* **10. Complete 2.22 enum (4 members):** `devNone=0`, `devRainbow=1` ("RAINBOW"), `devRainbowS=2`, `devArmorX=3` ("ARMOR-X Pro"). Everything else (BLITZ, CHOCO, C2SL, Gale, MSY, Rainbow2/3, keyboard) does not exist in this build.

## 11–13. BLE and startup sequence

* **11. UUID set:** vendor service `00000000-0000-1000-8000-00805f9b34fb` with **FFE1 write / FFE2 read+notify** (`CCCD 01 00` subscribed on FFE2), standard `0x180F` battery `2A19`, `0x180A` device-info `2A24`/`2A26`. Same as the later builds.
* **12. Startup sequence — PROVEN LIVE, two independent paths** (Frida platform hooks + peripheral raw log), session `ble/virtual-armorx/logs/2220901-fw2741/`:
  1. scan (`startScan`, **`filters: null`** — no name or service-UUID filter at the platform layer), 2. connect, 3. subscribe FFE2, 4. **`A5 04 0B B4`** → reply `A5 05 0B 30 E5`, 5. GATT reads `2A24`, `2A26`, `2A19`, 6. **`A5 0C EF 00×8 A0`** → device-UUID reply, 7. unsubscribe/re-subscribe FFE2, 8. **`A5 04 D4 7D`**, 9. **`A5 04 D6 7F`** → 144-byte config, 10. **`A5 04 D6 7F`** a second time, 11. `0xD2 01`/`D2 00` available from Button Test.
  The order `0B → identity reads → EF → D4 → D6` is **not** the order I would have assumed from the later builds — it is a 2.22-specific finding.
* **13. Full opcode inventory:** `results/static/2.22.0901/command-index.{md,json}` — 38 rows. Present: `0B`, `0E`, `70`, `D2`, `D4`, `D6`, `D7`, `D8`, `EF` (+ `A4` fragmentation). Absent (with the search that proves each): `04`, `05`, `06`, `07`, `1A`, `1B`, `25`, `26`, `34`, `73`, `A9`, `D3`, `DA`, `DD`, `E1`, **`E2`**, `E3`, `E4`, `F2`–`F8`, `FC`, `FD`, and the entire **`AB` family**.

## 14–16. Config and CRC

* **14. Config families in 2.22: only 88 and 144** (240/280/335/456/484/508 have zero hits). Family growth: **2 → 3 → 5 → 8** across the four builds.
* **15. ARMOR-X Pro config = 144 bytes**, serializer `GamepadSet30` / `GamepadParam30`; layout **identical to 4.0.8**: CRC 0–1 BE, length 2–3 BE (`0x0090`), parameters 4–111 (`replaceRange(4,112,…)`), **mapKeys 112–143**. Verified positions matching 4.0.8 exactly: byte 5 motorMax, 69–72 sensorSwitch u32 BE, 80 turbo speed, 81–84 turboKey u32 BE.
* **16. CRC: the later rule already existed unchanged — PROVEN STATIC.** Poly `0xA001`, init `0xFFFF`, over `sublist(2, len)`, output big-endian at bytes 0–1; three inlined sites (`changeGamepadDef` @`0x79c894`, `GamepadSet::toList` @`0x7a0c50`, `GamepadSet30::toList` @`0x7a1f60`). Honest caveat: 2.22's two embedded default images store **`0x0000` placeholders**, so those images validate by declared length only, not by self-check.

## 17–19. Key IDs

* **17. Table:** `results/static/2.22.0901/key-id-table.{md,json}`. Labelled ids: **0–4, 6–11, 13, 14, 16–19, 23–26, 34–49**. Evidence: two map builders (`component.dart:3909 _ChangeKeyButtonState.initState` @`0x895878`; `theme.dart:5286 _CircleButtonState.initState` @`0x8994f8`) plus the complete 23-name `key_*` l10n catalogue.
* **18. Previously-UNKNOWN ids — mostly NOT resolved by 2.22:** ids **5, 12, 15, 20, 21, 22, 27, 28, 29, 30, 31, 32, 33 carry no label in 2.22** (exhaustively checked against both maps and the whole l10n catalogue). The genuinely new result is the **bit-mask rule**, below.
* **19. Id 15 terminology in 2.22 = none** — it is neither "Capture" nor "Share" (the only "Share" string is a privacy-policy sentence). So id 15 was **unnamed in 2.22 and acquired its Capture label later**, which now dates that label to ≥2.23.

### ⚠ CONTRADICTED — and a methodology correction worth more than the finding

The imported research asserted *"`keyCapture = 0x10000`, bit index = key id + 1"*. That is **wrong**, and
I verified the error's origin in the 4.0.8 asm myself:

```
4.0.8 define.dart:1583  static int keyCapture() { mov x0, #0x10000 }
4.0.8 define.dart:1632  static int keyUp()      { mov x0, #0x20000 }
4.0.8 define.dart:1660  static int keyL1()      { mov x0, #0x80    }
```

Those immediates are **Smis**, which the project's own convention says are doubled. Halving them gives
`keyCapture = 0x8000` (bit 15 = id 15 ✓), `keyUp = 0x10000` (bit 16 = id 16 = D-pad up ✓),
`keyL1 = 0x40` (bit 6 = id 6 = LB ✓) — i.e. **`bit == id`, no +1 offset**, confirmed by 2.22's own
18 static getters, a powers-of-two `List(32)` at `pp.txt:27316`, and `lsl 1<<id` in `turboClick`
@`0x8c9724`. The earlier reading failed to halve a `mov` immediate. The id-15 = **Capture** conclusion
itself survives, but only on its independent map-literal chain — it never rested on the mask.

## 20–24. D8 macro

* **20. Encode format (2.22 = the OLD format — this is the pass's biggest structural finding):**
  payload `[crc16 BE][len BE][att.type][runKey][runKey|5][isRepeat][repeatTime BE]` + n × **7-byte
  `GamepadDefMap` records** `[type=0x80][time = duration/8 as u16 BE][key as u32 BE]`;
  `runKey` default **46** ("M1"), `repeatTime` default **200**; 8 ms timing granularity; CRC-16/MODBUS
  over `[2:]`.
* **21. Readback format: STILL UNKNOWN** — no D8 *parser* exists in 2.22; only fixed-offset blob
  parsers (`sublist(43,102)`, `sublist(70,216)`).
* **22. Chunk size — RESOLVED, and the 15/43/67 puzzle is explained:** `subpackageLength()` returns
  **20/48/72** per `curDevice.field_7`; minus the 5-byte A4 overhead that is exactly **15/43/67**.
  2.22/2.23 hard-code the 20-class (=15) and have **no `subpackageLength`, no MTU logic**; the
  per-device table only appears in **2.24**. Confirmed live: every fragment in the captured config
  read was `A4 14 D6 <ordinal> <15 bytes>` (0x14 = 20 = 15 + 5), 9×15 + 9 = 144.
* **23. repeatTime unit: PARTIALLY RESOLVED (ms)** — from UI-dialog evidence only; not proven at the
  wire level.
* **24. Commit semantics: the `0x0A` terminator is CONTRADICTED for 2.22.** The commit frame is
  `A4 05 D8 <nfrags+1> <csum>` (5 bytes, value appended @`0x79ec24`/`0x79eca8`); no `0x0A` byte exists
  anywhere in the fragmentation body. Also resolved: the `len = payload+5` vs `payload+4` dispute —
  there **is** an ordinal byte at frame offset 3, so **`payload + 5` is correct**, matching the lab's
  `frames.build_frag()`.

## 25–28. DPI and AB

* **25. FC/F6: NOT PRESENT in 2.22** — no `0xFC`, no `0xF6`, no `writeDpiConfig`, indeed **no DPI
  implementation of any kind** (`dpi` = 0 hits app-wide). FC arrives by 2.23; F6 is a later legacy
  branch.
* **26. DPI selector table: not applicable / UNKNOWN** — the selector→DPI mapping exists in no build
  statically (2.22 has no DPI at all; later builds send a 4-bit selector whose meaning was never
  recovered). Still a live-only question.
* **27. DPI reply parser: UNKNOWN** in all four builds.
* **28. AB family: ABSENT in 2.22** — no `0xAB` builder or dispatcher. The `AB 07 05 25 <u16 LE>`
  motion-DPI frames are a 4.0.8-era addition.

## 29–31. Lighting

* **29. RGB byte order: STILL UNKNOWN** — the missing anchor (a colour-int packing helper) does not
  exist in 2.22.
* **30. Structure and effects (PARTIALLY RESOLVED, PROVEN STATIC):** one generic
  `writeLightConfig` (`A5 <len> 70 …` control frame + `A4` data). Colours are **3 bytes each**
  (`changeLightColorList`, `mul ×3` @`0x7a70fc`); `LightData` keys `leftList/rightList/mode/speed/
  bright/same` → **2 zones**, no LED bitmask sets; modes **Normal / Breathing / Gradient / Flicker**.
  The later `0xF8/0xDD/0xF7/0xE1/0x73/0xF5/0x0D` commands, the R3 API and `LightColorRainBow3` all
  **do not exist** in 2.22.
* **31. Ranges:** brightness slider **50–255**, speed **0–255** (PROVEN STATIC, UI constants).

## 32. Turbo — RESOLVED

Config-resident, exactly as in 4.0.8: `GamepadParam30.turboKey` (hex string → u32, object offset `0x5c`)
serialised at parameter indices **77–80 (MSB first)** and `turboSpeedIdx` at index **76** → **config
byte 80 = speed, bytes 81–84 = turboKey u32 BE**. No `sendAllTurboKeySpeed`, no `writeTurboClick`, no
keyboard subsystem in 2.22 — all turbo here is controller turbo.

## 33–35. Server, ZJ-XT, removed strings

* **33. Server/API:** host `http://m.bigbigwon.com:8080` (same as every later build), **13 `/dev/*`
  endpoints**, plus OSS buckets. **Has `queryDefaultConfig`** (present through 2.23/2.24, dropped only
  in 4.0.8); **lacks `shareConfig`/`importShareConfig`** (added in 2.23) and **`queryGameList`**.
  This **contradicts the brief**, which said the later builds lost `queryDefaultConfig` *and*
  `queryGameList` — in fact `queryGameList` exists in **2.24 only**. `bledata.proto` is the unmodified
  28-message flutter_reactive_ble bridge with no vendor messages.
* **34. ZJ-XT: ABSENT from every artifact** of the APK (resources, resources.arsc, dex, all three
  ABIs' `libapp.so`/`libflutter.so`, assets, Dart pool, asm tree); no `ZJ-` token either. Warning
  recorded: grepping the *container* is a trap — 89/123 zip members are deflated.
  **PROVEN LIVE corroboration:** the app *reads* the mark over GATT `2A24` rather than knowing it. The
  value it read (`ZJ-XT`) is the virtual peripheral's configured identity, so this proves the channel,
  not what real hardware reports.
* **35. Removed-but-useful strings: none of protocol significance** — the 310-string 2.22-only set is
  Flutter-framework noise; only `"RAINBOW"`, `"ArmorX Pro"` and dropped manual URLs carry meaning.
  **No currently-UNKNOWN field is named by 2.22-only strings.**

## 36–38. Differences versus the later builds

| Field | 2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 |
|---|---|---|---|---|
| versionCode | 3 | 12 | 24 | 409 |
| signer | moojiang release (serial 5EA0DB29) | **same key** | Android Debug | Play App Signing |
| ABI | arm64 + armeabi-v7a + **x86_64** | same | arm64 only | arm64 only |
| Dart | 2.17.5 | 2.19.6 | 3.2.3 | 3.12.2 |
| BLE lib | flutter_reactive_ble | flutter_reactive_ble | flutter_reactive_ble | flutter_blue_plus |
| Device enum | **4** (ARMOR-X = 3) | 7 (= 6) | 9 (= 8) | 13 (= 10) |
| Config families | **88, 144** | +240 | +280, 484 | +335, 456, 508 |
| D8 macro | 7-byte records, chunk 15 | chunk 15 | per-device chunk table | 10-byte frames, chunk 15/43/67 |
| DPI (FC/F6/AB) | **absent entirely** | FC | FC + F6 legacy | FC + F6 + AB motion |
| E2 | **absent** | absent | absent | present |
| Lighting | 1 generic builder, 2 zones | +FF-family | +R3 | R3 + F8/DD/F7/E1 |
| `queryDefaultConfig` | **present** | present | present | **removed** |

## 39–42. Dynamic execution

* **39. Runs natively — PROVEN LIVE.** The APK ships `x86_64`; installed unmodified on the existing
  `armorx_res_api33` AVD: `pidof` non-empty, `topResumedActivity = com.moojiang.bigbigwon/.MainActivity`,
  `versionName=2.22.0901`, `versionCode=3`, Flutter engine booted. APK hash re-verified unchanged
  after the session; no re-signing anywhere.
* **40. Dynamic startup sequence:** see §12. Extras: the app talks to `47.116.43.253:8080` and posts
  `{"phoneModel","phoneVersion","phoneUuid","appVersion":"2.22.0901","phoneLocation"}`; the server
  answers `{"code":0,"msg":"ok","data":{"result":true,…}}`. Scan is issued with **no filters**.
* **41. Virtual ARMOR-X compatibility** (`results/static/2.22.0901/virtual-armorx-compat.md`):
  implemented-and-answered `0B`, `EF`, `D6`, `D7`, `0E`; **requested but missing: `D4` and `D2`** —
  both logged `command_unknown` with `reply_bytes_sent: 0`, no bytes invented. Two real bugs were
  found in the lab peripheral (not the APK) and fixed: its default netsim wiring never delivered HCI
  (fixed with `--mode direct`), and its advertising payload exceeded 31 bytes (vendor UUID moved to
  the scan response).
* **42. Frida findings:** pinned 16.7.19 (17 cannot run the Java hooks); platform BLE hooks +
  `flutter_reactive_ble` plugin probe both fired; the 2.22-specific permission gate was defeated with
  a surgical override. **Protocol finding:** 2.22's Dart parser throws
  `RangeError (end): Invalid value: Only valid value is 2: 4` at `armorx_pro_root.dart:129` when `2A26`
  is 2 bytes; serving **`2741` (4 bytes) removes the exception and lets the flow reach `EF`/`D4`/`D6`**
  — first hard evidence of 2.22's expected `2A26` length.

## 43–44. UNKNOWN resolution ledger

**Resolved by 2.22:** the D8 fragment-chunk mechanism (20/48/72 − 5 = 15/43/67) and the `payload+5`
form; the `0x0A` commit byte (CONTRADICTED for 2.22); the bit-mask rule (`bit == id`, correcting
imported research); DPI dating (absent before 2.23); E2 dating (absent before 4.0.8); the pre-2.24 D8
payload shape; 2.22's exact startup order; the required `2A26` length (≥4 bytes, live); the turbo
byte mapping back to 2.22; family-count history; endpoint history (`queryGameList` = 2.24 only).

**Still UNKNOWN:** D8 readback format and offsets; D8 receive-ordinal semantics; whether a zeroed
record means "disable"; `repeatTime` unit at the wire level; DPI selector→DPI map and reply parser
(all builds, live-only); lighting RGB byte order and effect ids; ids 5/12/20/21/22/27–33 labels;
2.22's name for its key-remap slice (0 `mapKeys` hits); A4 interior field order and checksum rule;
`devRainbowS` display/screen; which 144-byte default image binds to ArmorX (2.22 ships only the
ARMOR-X-labelled one, differing from later builds by a single byte at offset 4: `0x00` vs `0x33`);
4.0.8's Flutter framework version.

## 45. Files generated

`apk/manifests/2.22.0901.json` (+ `PROVENANCE.md` section) · `results/static/2.22.0901/`: `command-index.{md,json}`, `e2-verdict.md`, `config-map.{md,json}`, `crc.md`, `device-enum.md`, `d8-macro.{md,json}`, `fc-dpi.md`, `lighting.md`, `turbo.md`, `key-id-table.{md,json}`, `dynamic-run.md`, `virtual-armorx-compat.md`, `strings-inventory.md`, `device-mark-search.md`, `default-config-archaeology.md`, `removed-useful-strings.md`, `server-api.md`, `default-configs/`, `screenshots/` (24 PNGs), `logcat-full.txt`, raw dumps · `results/version-diff/`: `device-enum-history.json`, `d8-history.md`, `dpi-history.md`, `lighting-history.md`, `server-api-history.md`, **`2.22-vs-2.23-vs-2.24-vs-4.0.8.{md,json}`** (built by `scripts/compare_versions.py`) · `static/blutter/2.22.0901/blutter_out/` (new Dart 2.17.5 Blutter build) · `frida/traces/2.22.0901/` (5 traces) + 2.22 hooks · peripheral logs.

## 46. Git state

Lab repo `/home/salamanka/armorx-lab` — new branch **`research/mygt-2.22.0901`**, commit recorded in
the final status message; `research/mygt-4.0.8` in the toolkit repo remains untouched at `dbe2ce7`
and `research/ble-lab-multiversion` at `6f0acd5`. Push remains **AUTH_BLOCKED**; patch + bundle
produced. No force pushes, nothing rewritten.

## 47. The ONE highest-value follow-up

**Implement `0xD4` (getInputModel) in the virtual ARMOR-X peripheral and re-run 2.22 to completion.**
It is the last unknown in the observed startup handshake (2.22 sends it, nothing answers), it is a
one-frame addition to already-working tooling, and its reply format is the missing link between the
2.22 and 4.0.8 identity flows. Second in line: the live test that would finally close D8 readback —
write a one-frame macro with `0xD8` and diff what the device returns.

---

# What 2.22 taught us that 4.0.8 could not

**1. The D8 chunk-size question was a version trap, and 2.22 is what exposes it.**
`subpackageLength()` returning 20/48/72 exists only from **2.24**. Applied to 2.22 it produces a
plausible-looking "15/43/67 candidates" list, which is exactly the confusion in the imported notes.
2.22 shows the mechanism's *origin*: a hard-coded 15, no MTU logic, no per-device table — so the
"candidate list" is a later abstraction, not an old mystery. And the live capture settled the framing
independently: `A4 14 D6 <ordinal> <15 bytes>` with `0x14 = 15 + 5`.

**2. It kills the `0x0A` commit byte.** The 4.0.8-era reconstruction carried a terminator byte `0x0A`;
2.22's commit frame is `A4 05 D8 <nfrags+1> <csum>`, with no `0x0A` anywhere in the fragmentation body.
That both **CONTRADICTS** the documented terminator and explains why the lab's `frames.build_frag()`
needed two length forms.

**3. It corrects the project's key-ID arithmetic — a Smi bug, not a data gap.** The imported rule
"bit = id + 1" came from reading `mov x0, #0x10000` without halving it. 2.22's own tables
(`bit == id`, `keyL1 = bit 6 = LB`) expose the inconsistency, and re-reading 4.0.8 with the Smi rule
gives `keyCapture = 0x8000` (bit 15) — self-consistent for the first time. The `Capture` label survives
on its independent chain, but the mask rule used elsewhere in the toolkit had to change.

**4. It dates three protocol features by *absence*.** E2 (`A5 04 E2 8B`), the whole AB motion family,
and DPI (FC *and* F6) simply do not exist in 2.22 — so E2 and motion-DPI are 4.0.8-era, DPI is
2.23-era, and any spec that presents them as ancient ARMOR-X behaviour is anachronistic.

**5. It reconstructs the older, simpler D8 payload.** 7-byte `GamepadDefMap` records with
`[type=0x80][duration/8 u16 BE][key u32 BE]`, `runKey` default 46, `repeatTime` default 200. The
10-byte frame layout in the 4.0.8 notes must not be projected backwards, and the two formats can now
be labelled by version.

**6. It produced the first complete live handshake for the family.** 2.22 is the only build that both
carries `x86_64` (so it runs on this host) and speaks the vendor protocol, giving a fully observed
`0B → identity reads → EF → D4 → D6` sequence with byte-exact frames, two independent capture paths,
and a live proof that the model mark (`ZJ-XT`) is *read from the device* rather than compiled in —
including the honest note that the value came from our own virtual peripheral.

**7. It found a parser contract nobody had.** Serving a 2-byte `2A26` crashes 2.22 with a
`RangeError` at `armorx_pro_root.dart:129`; 4 bytes fixes it. That is a firmware-string length
requirement discovered by fuzzing the *virtual* device — and it also produced two genuine bug fixes
in the lab's peripheral (HCI wiring, 31-byte advertising limit).
