# JieLi / RCSP fingerprint verdict (Phase S) — CORRECTED

**Date:** 2026-09-27 · **Pass:** `research/physical-armorx-live-2026-09-27`
**Status of this document:** this file replaces an earlier draft written minutes earlier in the same
pass. The draft asserted *"the real unit advertises 6 services and none of them is AE00"*. **That
claim was WRONG** and is corrected below with the raw discovery record. Per project convention the
old claim is preserved rather than erased (see §7 "Dated correction").

---

## 0. Verdict

| Where | RCSP verdict | Evidence level |
|---|---|---|
| Android app, all four builds (2.22.0901 / 2.23.0609 / 2.24.0919 / 4.0.8) | **ABSENT** — no RCSP client, no AE00/AE01/AE02 UUID, no `FE DC BA`, no `com.jieli`/`jl_bt_ota`/`jl_ota` | PROVEN STATIC (control-verified) |
| **Real ARMOR-X Pro (physical unit, `ZJ-XT_2741_2D-37-35-6D-66-11`)** | **SECONDARY_SERVICE — PRESENT** | **PROVEN LIVE** |
| Real device's normal **configuration** path | **NOT RCSP** — the custom `00000000-…` service with FFE1 (write) / FFE2 (notify) carries the entire A5/A4 conversation | PROVEN LIVE |
| Vendor **Windows PC updater** (`DevMgr.dll`, `BTUpgrade*.dll`, `NetMgr.dll`, `WndMgr.dll`) | **OTA_ONLY** — JieLi AC632N `.ufw` upgrade library | PROVEN STATIC |

**One-sentence answer:** RCSP is *present on the hardware* (so this is a JieLi-stack device) but is
*unused by the ARMOR-X configuration protocol* — the app never speaks it, and the proven live
protocol is the custom FFE1/FFE2 A5/A4 one. RCSP's role is the vendor OTA/upgrade toolchain.

---

## 1. Real-device evidence (PROVEN LIVE)

From `results/experiments/physical-20260927-162448/session.jsonl`, `event: "services"`, produced by
`await peer.discover_services()` in `ble/real-device/armorx_real.py:284` — i.e. **read from the
device**, not from any hard-coded list (verified: the string `ae00` appears nowhere in the lab
client or helper code):

```json
{"event": "services", "uuids": [
  "00001800-0000-1000-8000-00805f9b34fb",   // Gap
  "00001801-0000-1000-8000-00805f9b34fb",   // Gatt
  "0000180a-0000-1000-8000-00805f9b34fb",   // Device Information
  "0000180f-0000-1000-8000-00805f9b34fb",   // Battery
  "00000000-0000-1000-8000-00805f9b34fb",   // vendor configuration service (FFE1/FFE2)
  "0000ae00-0000-1000-8000-00805f9b34fb"    // <-- JieLi RCSP primary service  ***PRESENT***
]}
```

Characteristics discovered in the same connection (`event: "characteristics"`) include:

```
0000ae01-0000-1000-8000-00805f9b34fb   <-- RCSP write characteristic
0000ae02-0000-1000-8000-00805f9b34fb   <-- RCSP notify characteristic
0000ffe1-0000-1000-8000-00805f9b34fb   <-- vendor config write (the one the app uses)
0000ffe2-0000-1000-8000-00805f9b34fb   <-- vendor config notify
```

Reproduced in **7 independent connections** on the real unit
(`physical-20260927-162427`, `-162448`, `-162545`, `-162602`, `-162815`, `-162846`, `-button-test3`).

**Why the earlier draft got it wrong:** the *advertisement* carries `"service_uuids": []` — the
device advertises no service UUIDs (only manufacturer data `fe ff 5a 4a 2d 58 54` = company
`0xFEFF` + ASCII `ZJ-XT`, and local name `ARMOR-X Pro_11`). AE00 appears only after **connection +
service discovery**. Reading advertisement data and concluding "no AE00 service" is invalid.

### 1.1 Consequence for the platform claim

A device exposing AE00/AE01/AE02 is running the **JieLi RCSP-capable stack**, which is independent
support for the JieLi/AC632N platform conclusion. It is still **not** a firmware dump: AC6321A /
AC632N / BD19 for the body remains **STRONG EVIDENCE**, not PROVEN (see §5).

---

## 2. Android-app verdicts (PROVEN STATIC, control-verified)

| Build | RCSP client | AE00/AE01/AE02 UUID | `FE DC BA` | `jieli`/`com.jieli`/`jl_ota`/`jl_bt_ota` |
|---|---|---|---|---|
| 2.22.0901 | ABSENT | ABSENT | ABSENT | 0 |
| 2.23.0609 | ABSENT | ABSENT | ABSENT | 0 |
| 2.24.0919 | ABSENT | ABSENT | ABSENT | 0 |
| 4.0.8 | ABSENT | ABSENT | ABSENT | 0 |

Searched corpus (absolute paths):

```
/home/salamanka/armorx-lab/apk/extracted/{2.22.0901,2.23,2.24,4.0.8,4.0.8-apkm-splits}
/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out    (Dart 2.17.5)
/home/salamanka/armorx/re/blutter_out                              (2.23, Dart 2.19.6)
/home/salamanka/armorx/re/v224/blutter_out                         (2.24, Dart 3.2.3)
/home/salamanka/armorx-re/mygt408/blutter_out                      (4.0.8, Dart 3.12.2)
/home/salamanka/armorx_research/dongle_baseline_v13/artifacts       (vendor Windows binaries)
/home/salamanka/armorx-re/repo                                      (toolkit; secondary source)
```

Interpretation: **the app's absence of RCSP code does not contradict the device's AE00 exposure.**
The app simply never uses that service; RCSP is driven by the vendor's PC/OTA toolchain.

---

## 3. Positive controls (a zero is only meaningful if these are non-zero)

Every tree was control-tested with `-uu` (see §4) before its zeros were accepted:

| Tree | `moojiang` | `ffe1` | Zeros trustworthy |
|---|---|---|---|
| apk-2.22.0901 | 160 | 3 | yes |
| apk-2.23 | 174 | 6 | yes |
| apk-2.24 | 62 | 2 | yes |
| apk-4.0.8 | 163 | 1 | yes |
| asm-2.22.0901 | 1369 | 57 | yes |
| asm-2.23 | 1432 | 81 | yes |
| asm-2.24 | 2295 | 80 | yes |
| asm-4.0.8 | 5186 | 121 | yes |
| win-updater | — (not a Dart tree) | 3 | yes |

**Correction to the earlier draft's control table:** it reported `moojiang = 0` on all five APK
trees and marked the controls `ok=False`, i.e. it *knew* its APK scans were dead and published the
ABSENT verdicts anyway. Its `2.22 asm = 0` control was also a dead scan. Those zeros were artifacts
of the two bugs in §4, not evidence; they have been re-run and are now valid.

---

## 4. Two scan bugs found (recorded so they are never repeated)

1. **ripgrep silently honours `.gitignore`.** The extracted APK trees are `.gitignore`d inside the
   lab repo, so the first pass returned zero hits even for `moojiang`. Fixed with `-uu`
   (no-ignore + hidden). Any negative claim about an ignored tree must be re-run with `-uu`.
2. **With `-a`, ripgrep prints `file:match` for binary matches (no `line:` field).** A parser
   requiring three colon-separated fields reported false zeros even for a known-present control
   (`ffe1`). Fixed by parsing the last field.

Both bugs produced plausible-looking zeros — the exact false-ABSENT trap this pass warns about.

---

## 5. False-positive appendix (every loose hit, classified)

| Raw hit | Where | Actual context | Classification |
|---|---|---|---|
| `rcsp` | APK trees, win-updater | the C symbol `strcspn` (`…strspn.strcspn.mkdir…) | NOT EVIDENCE |
| `FEDCBA` | all APK trees | the base64 alphabet literal `9876543210/.-,+*` in Flutter AOT data | NOT EVIDENCE |
| `fe dc ba` | APK assets | binary GIF/`XMP` metadata bytes | NOT EVIDENCE |
| `AE00`/`AE01`/`AE02` | all asm trees | code addresses / object ids (`0xae017c`, `Obj!XmlAttributeType@b2ae01`, `0x6ae02c`) | NOT EVIDENCE |
| `key_mac` ×54 | 4.0.8 asm | Flutter widget `view_key_macro_selector.dart` (`key_mac` inside `key_macro`) | NOT EVIDENCE |
| `bd19` | asm trees | `ldurb` mnemonics / instruction addresses (`0x9bd19c`) | NOT EVIDENCE |
| `ac632` | 2.24 / 4.0.8 asm | instruction addresses (`0xac6320:`, `0xac6324:`) | NOT EVIDENCE |
| `jieli`/`rcsp`/`uboot.boot`/`isd_config.ini`/`ac632n`/`ae00`… in `/home/salamanka/armorx_research` | legacy tree | vendor Windows binaries + our own older notes | genuine but PC-side / documentary |

**Genuine JieLi positives in the local corpus are exactly one family:** `JL_*` exports,
`CUpgradeUFW`, `AC632N_TRANS`, `AC632N_update`, `isd_config.ini` (×28), `uboot.boot` (×8), `.ufw`
(×12) inside the vendor **Windows** updater binaries; plus a real JLFS container in the third-party
positive-control tooling. Full inventory: `results/final/real-firmware-mode.md`,
`results/final/firmware-inventory.json`.

---

## 6. Answers to the Phase S questions

1. **RCSP in any Android build?** — **ABSENT** in all four (PROVEN STATIC). On the **real device**:
   **PRESENT as a secondary service** (PROVEN LIVE). In the **PC toolchain**: OTA_ONLY.
2. **Any build reference AE00/AE01/AE02?** — **No** (all forms absent; matches were addresses).
   **The real device exposes all three** (AE00 service; AE01 write; AE02 notify).
3. **OTA/DFU path and transport?** — No RCSP/DFU client in any Android build. The app has firmware
   *version* reads (`info_firmware`, `firmwareVer`, `readFirmware`) and a firmware *download*
   reference (`Firmware-Download-Adresse`, `Controller-Firmware`); the in-protocol firmware read is
   the custom `A5 04 E2 8B` opcode (4.0.8 only). Actual flashing is the vendor PC tool's JieLi
   `.ufw` path (runtime download via `http://m.bigbigwon.com:8080/dev/queryFirewareList`).
4. **What does a generic JieLi string prove?** — It proves the *upgrade toolchain* is JieLi
   AC632N-class, and now the device itself proves an RCSP-capable JieLi stack is running. It still
   does **not** make normal configuration RCSP: the live configuration conversation is A5/A4 over
   FFE1/FFE2 (PROVEN LIVE, byte-anchored). Nothing here contradicts the FFE1/FFE2 protocol.

---

## 7. Dated correction (append-only record of the superseded claim)

```
OLD CLAIM      (this file's earlier draft, 2026-09-27, Phase S subagent):
               "the real unit advertises 6 services and none of them is AE00"
               "...AE00/AE01/AE02 ... 0 lines"  → used to justify an app-wide ABSENT verdict.

NEW EVIDENCE   (REAL ARMOR-X, session physical-20260927-162448 and 6 sibling sessions):
               event "services" from live `discover_services()` lists
               0000ae00-0000-1000-8000-00805f9b34fb among the six services, and
               event "characteristics" lists 0000ae01 / 0000ae02.

CORRECTED      RCSP is ABSENT from the Android app but PRESENT on the hardware as a
INTERPRETATION secondary service. The draft conflated ADVERTISEMENT service UUIDs
               (which ARE empty: `"service_uuids": []`) with DISCOVERED GATT services.
               Verdict changed from "ABSENT everywhere" to "SECONDARY_SERVICE on device".

AFFECTED       results/final/jieli-rcsp-verdict.md/.json (this file), the Phase S
FILES          summary line in any report quoting it.

EVIDENCE LEVEL Android-side ABSENT: PROVEN STATIC (control-verified).
               Device-side AE00/AE01/AE02 presence: PROVEN LIVE.
               Platform AC6321A/AC632N/BD19: STRONG EVIDENCE (unchanged).
```

---

## 8. Residual unknowns (not upgraded)

- No ARMOR-X **body firmware image** was ever available → AC6321A stays STRONG EVIDENCE.
  Upgrading it needs a read-only firmware dump (bootloader mode; requires USB + device off-state).
- No RCSP byte conversation was ever captured from the unit (only service presence). Whether the
  firmware answers RCSP `FE DC BA` auth/procode frames is **UNKNOWN** — and testing it would mean
  speaking a vendor upgrade protocol to the device, which this pass deliberately did not do.
- Whether `E2` (`A5 04 E2 8B`) is the *equivalent* of an RCSP firmware-read is **UNKNOWN**.

---

## 9. Independent re-confirmation (later in the same pass) — APPEND-ONLY

Re-ran the app-side question with a **different method** from §2/§3, to make sure the earlier
verdict was not an artifact of the earlier tooling:

- Tool: `automation/scripts/apk-rcsp-scan.py` — reads the APK **zip containers directly**
  (`.dex`, `.so`, `.xml`, `.json`, `.arsc`, `assets/*`), so it cannot be affected by the
  `.gitignore`/ripgrep trap recorded in §4, and it does not depend on extracted trees.
- Corpus: `BIGBIG_WON.apk`, `BIGBIG_WON_2.22.0901.apk`, `armorx-re/mygt408/apks/base.apk`,
  `armorx/base_apk/base.apk`. Output: `results/final/jieli-rcsp-app-scan.json`.
- Result: `ae00`/`ae01`/`ae02` (in any representation) **absent**; `com.jieli` / `com/jieli`
  **absent**; `jl_bt_ota` / `JL_OTA` / `JLOta` **absent**; `authkey` / `procode` / `JL_AUTH`
  **absent**; `update.ufw` / `jl_isd.fw` / `isd_download` **absent**; `BD19` / `AC632`
  **absent**; `FFE1` / `FFE2` **present** (the app's own configuration channel).
- The only `rcsp` / `FE DC BA` hits were checked in context and are identical in nature to the
  §5 false-positive appendix: `rcsp` inside `strcspn` in the zlib ASCII table of
  `libflutter.so`, and `FE DC BA` as the tail of the `01 23 45 67 89 ab cd ef fe dc ba 98 76 54
  32 10` compiler constant table.

**Verdict unchanged:** RCSP ABSENT in the Android app (PROVEN STATIC), PRESENT on the real
device as a secondary service (PROVEN LIVE), OTA_ONLY in the vendor PC toolchain. The device's
configuration protocol remains A5/A4 over FFE1/FFE2.

Vendored tool provenance re-checked this pass: `tools/vendor/AC632Nuke` @
`6f179f2b0ae5b3d6bc9885ec4f3d7cb82d0bdee9`, `tools/vendor/jl-misctools` @
`0a5b12db0ef38f3042acffbe2452730a37fd2405`. Neither was executed; `jl-uboot-tool` remains
deliberately uninstalled (§3 of `tools/TOOL_INVENTORY.md`).

