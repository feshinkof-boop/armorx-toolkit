# ARMOR-X Pro — MASTER REPORT (supersedes all earlier handoffs)

Updated 2026-09-27/28 by the autonomous overnight shift (no hardware touched). This document is
intended to be the **only** thing a reader needs: every claim carries a grade and a pointer, and where
this shift changed an earlier conclusion the change is stated in place.

Grades: **PROVEN LIVE / PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN / CONTRADICTED /
NOT PRESENT**.

The previous physical-pass report is preserved at
`results/final/archive/real-armorx-master-report-physical-pass-2026-09-27.md`.

---

## 0. The headline correction (read this first)

`OFFICIAL_WORKS_HARNESS_SILENT` - the finding that the harness receives nothing while the official app
streams - is **CONTRADICTED as a statement about the device**. The harness received **3,292 valid
18-byte `A5 12 02` frames across 26 key ids** on 2026-09-27 at 17:08, over the control plane
`0B → D2 ON` with **no pre-clear**. The windows previously read as "harness silent" had **no physical
press requested at all**; the official window did. Under the corrected event-driven model that is a
comparison of *pressed* vs *not pressed*.

Reclassified: `HARNESS_STREAMS_UNDER_PRESS__DIFFERENTIAL_WINDOWS_WERE_NOT_PRESS-MATCHED`.
Full working: `results/reconciliation/d2-u007-harness-streaming-reconciliation.md`.

---

## 1. Hardware

| item | value | grade |
|---|---|---|
| unit | ARMOR-X Pro, `ARMOR-X Pro_11`, `2D:37:35:6D:66:11` | PROVEN LIVE |
| identity | model `ZJ-XT`, firmware `2741`, id `ZJ-XT_2741_2D-37-35-6D-66-11` | PROVEN LIVE |
| manufacturer data | `fe ff` + `5a4a2d5854` (`ZJ-XT` ASCII) | PROVEN LIVE |
| config baseline | 144 bytes, `sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` | **PROVEN LIVE, DURABLE_OK** |
| state at end of shift | unit off/asleep; **no hardware has been touched since** | - |

## 2. BLE transport and GATT

| item | value | grade |
|---|---|---|
| services | 6 services / 18 characteristics, including the custom service carrying FFE1/FFE2 | PROVEN LIVE |
| control write | FFE1 = `0000ffe1-…` handle `0x0075` | PROVEN LIVE |
| notify | FFE2 = `0000ffe2-…` handle `0x0077`; CCCD `0x0078` | PROVEN LIVE |
| RCSP services | `AE00`/`AE01`/`AE02` **present on the real unit** (JieLi-capable stack) but **not** used for configuration | PROVEN LIVE |
| ATT MTU | both the official app and the harness end at **64** (official: 23 then 512→64) | PROVEN LIVE |
| security | official and harness are both **UNBONDED + UNENCRYPTED**; zero SMP frames, zero encryption events | PROVEN LIVE |
| connection interval | official `30 → 7.5 → 30 → 11.25 ms` over 4 link states; harness `7.50 ms`; latency 0; supervision 5 s → 2000 ms | PROVEN LIVE |

The four official interval states are accounted for by **1 LE Extended Create Connection + exactly 3 LE
Connection Update commands** (frames 4297/4402/4421, with 3 Complete events) - verified independently.
The app **never calls `requestConnectionPriority`, `setPreferredPhy` or an MTU-request API**, so the
interval history is stack/OS-driven, not app-requested (**PROVEN STATIC**).

## 3. Official Android app

| item | value | grade |
|---|---|---|
| phone | vivo V2304A / iQOO 11S, Android 16 / SDK 36, serial `10AD730KL6001AY` | PROVEN LIVE |
| package | `com.moojiang.bigbigwon.mygt` **4.0.8 / versionCode 409**, targetSdk 36, not debuggable | PROVEN LIVE |
| integrity | installed `base.apk` byte-identical to the repository's 4.0.8 (`64e0832b…9378e2`); no Frida/Xposed | PROVEN LIVE |
| capture | Android HCI snoop (`.cfa`, plain BTSnoop v1) 3,777,571 B, `sha256 bbaf10bd…` | PROVEN LIVE |
| ADB | established over USB (blocker resolved); transport available | PROVEN LIVE |

## 4. D2 (Button Test / test mode)

| item | value | grade |
|---|---|---|
| official enable | `A5 05 D2 01 7D`, ATT **Write Command (0x52)**, handle `0x0075` | PROVEN LIVE |
| harness enable | **byte-identical** - same value, same opcode, same handle, echoed twice | PROVEN LIVE |
| official disable | `A5 05 D2 00 7C` at +129.5 s | PROVEN LIVE |
| input model | **event-driven**: 0 frames while idle (61 s window), 155 frames during a press window | PROVEN LIVE |
| frame | 18 bytes `A5 12 02 <mask u32 BE> <axes> <LT> <RT> <cks>`; bit index == key id | PROVEN LIVE |
| A-twice proof | PRESS 580.293 → RELEASE 580.518 → PRESS 581.361 → RELEASE 581.598 (225/237 ms, gap 843 ms), only bit 0 | PROVEN LIVE |
| held cadence | median ≈ 11.7 ms while held | PROVEN LIVE |
| harness streaming | **3,292 frames / 26 ids** with `0B → D2 ON`, no pre-clear | PROVEN LIVE |
| `D2-U-007` | **RESOLVED** (harness is not silent); residual = is the D2 **pre-clear** harmful *when a key is pressed*? never tested together | residual UNKNOWN |
| `D2-U-008` (bonding/encryption required) | **REFUTED** - both sides unbonded/unencrypted | PROVEN LIVE |
| `D2-U-009` (connection params differ) | **SUPPORTED, not causal** - intervals differ, app requests no profile | PROVEN LIVE / PROVEN STATIC |
| `D2-U-002` (2.24 `0x24`) | **RESOLVED**: `0x24` is the tagged Smi of 18, compared against `data[1]` (`=0x12`) | PROVEN STATIC (verified byte-level) |

## 5. The pre-D2 burst, and its origin (static)

The official app sends, before D2: `EF → 0B → E2 → D4 → D6 (ten frames)`. Static origin (**PROVEN STATIC**,
addresses verified against the 4.0.8 AOT tree):

| request | emitter | address | dart line |
|---|---|---|---|
| `EF` | `BluetoothModel::getDeviceUUID` | `0xacf618` | 3973 |
| `0B` | `BluetoothModel::getZKMVer` | `0x8b61fc` | 1042 |
| `E2` | `BluetoothModel::readFirmware` | `0x8b6860` | 1263 |
| `D4` | `BluetoothModel::getInputModel` | `0xa84258` | 1850 |
| `D6` | `BluetoothModel::getDeviceConfig` | `0x80dbfc` | 12 |
| `D2` | `BluetoothModel::testModeSwitch` | `0xabaef4` | 1954 |

**They are NOT one ordered initialisation pipeline.** `EF → 0B → E2` is a genuinely reply-gated chain
(each request is emitted from the previous opcode's reply handler); `D4 → D6` is a *separate* sequence
fired from the configuration tab's own state, gated on nothing. The cross-version branch adds the
decisive context: the burst is **generic application initialisation**, present across builds, and is
**not D2-specific**.

**D6 → application state:** `D6_APP_STATE_DEPENDENCY_NOT_FOUND` for the 4.0.8 Button-Test/D2 path
(scope stated): the configuration read populates app state that Button Test does not consult. A
read-only *device* operation still initialises *app* state - but nothing gates D2 on it.

## 6. D4

Official live: TX `A5 04 D4 7D` → RX `A5 07 D4 11 01 00 92`. The exhaustive matrix
(`results/reconciliation/d4-matrix.md`) reconciles the older conflicting readings: the primary
explanations are **an old assumption** and **an early virtual-peripheral run**, with device-mode state
also supported; a genuine protocol variant across the four app versions is **not** supported.
Old evidence was preserved, not erased.

## 7. D6 / D7 and configuration durability

| item | value | grade |
|---|---|---|
| D6 read shape | **TEN reply frames**: nine 20-byte fragments + one 14-byte tail = **144 bytes** | PROVEN LIVE |
| **correction** | earlier documents said "eight fragments"; the real read is ten (ordinals 01–09 plus a shorter ordinal 10) | CONTRADICTED → corrected with dated notes |
| cross-check | the reassembled read is **byte-identical to our durable baseline** `bdef9c61…` | **PROVEN LIVE** |
| D7 immediate readback | **STAGED_OK only** | PROVEN LIVE |
| durable restore | `write → readback → idle/settle → power cycle → D6 exact SHA match` = **DURABLE_OK** | PROVEN LIVE |
| rule | `STAGED_OK != DURABLE_OK` - never report an immediate readback as persistence | authoritative |

## 8. Configuration format (144 bytes)

Per-byte evidence map: `results/final/config-byte-evidence-map.{md,json,csv}` - 36 rows,
25 PROVEN STATIC / 10 UNKNOWN / 1 PROVEN LIVE, with CRC, length field, stick/trigger/gyro/turbo/profile
regions and the trailing 32-byte `mapKeys` region (a **source→target remap**, not a name table).
Unknown bytes stay UNKNOWN.

## 9. Key map

`results/final/key-map-confidence.{md,json,csv}`: **26 ids PROVEN LIVE** (0,1,3,4,6,7,8,10,11,12,13,14,
15,16,17,18,19,20,23,24,25,26,27,28,29,30), **8 UNKNOWN** (2,5,9,21,22,31,32,33). RT (9) is a proven
**negative**. New finding: the app's own `define.dart` key getters sit **exactly one bit above** the
wire for the same names, so they are a separate enumeration and must not be used to name a wire bit.

## 10. D8 / macros

Fragment layout `A4 | total_len | opcode | ordinal | payload | csum`, and the **commit frame is
`A4 05 D8 <nfrags+1> <cks>`**, not `A4 0A D8` (PROVEN STATIC in all four builds). The older
7-byte `GamepadDefMap` / 15-byte-segment model coexists with the modern 10-byte `TranscribeFrame`
model whose payload classes are 15/43/67; the exact chunk-class selector is unresolved.
`automation/scripts/armorx_lab/frames.py::build_d8_terminator` already emits `0x05`. No macro write was
performed. Scope note: the A4 framing rule was derived from the ten live A4/**D6** config frames (same
framing, legitimate) and must not be read as a live D8 macro capture.

## 11. DPI, motion, lighting

Consolidated in `results/final/protocol-closure-fc-dpi-motion-lighting.md`. Headlines: DPI query is
`A5 05 FC 80 26` → live reply `a5 05 ff fc a5` (**PROVEN LIVE**); the selector→DPI table is **not in the
binary** (server-side presets) so no numeric DPI is claimed; the motion family is **`AB`**
(`AB 05 05 25 DA` / `AB 05 05 26 DB`, checksum-valid - a repo transcription error was corrected this
shift) and it produced **no reply** on this firmware; lighting has **no read path at all**, so a write
cannot be verified by readback, and **RGB byte order is UNKNOWN in all four builds**.

## 12. USB / F20 receiver, Windows Assistant

`results/final/windows-usb-static-closure.md`. Settled: `VID_413D&PID_2106`, Usage Page `FF7A`, Usage
`0001`, N = 64, 65-byte Windows buffers with the report ID in slot 0, persistent/pre-posted IN, IOCP
(`CreateIoCompletionPort`), `CUsbCmd::ToPacket`/`FromPacket`, and `request+0x10` aliasing
`transfer_base+0x68`. Also settled: DevMgr.dll contains **two independent numbering systems**
(`t_BBW_DevType` vs `t_ProductType`) that collide at 5–7 - they must never be conflated. Read symmetry,
buffer ownership and the mark/model classifier stay UNKNOWN; the normal-vs-Xbox re-enumeration question
is **hardware-bound**.

## 13. JieLi / firmware

`results/reconciliation/jieli-firmware-static.md`. The app contains **no RCSP client** and **no firmware
download path** (proven negative, so nobody needs to re-search); the real unit exposes an RCSP-capable
service layout but configures through the custom service; the vendor **Windows** updater carries a JieLi
AC632N `.ufw` upgrade library. **No firmware image exists anywhere in the local artifacts**, so the MCU
part number stays **STRONG EVIDENCE, not proven**. No OTA, no firmware write, no bootloader interaction.

## 14. Linux support and community platform (design)

- `docs/linux-support-architecture.md`: configuration support belongs in a **userspace BlueZ client**
  behind a transport interface, with a thin state daemon and the GUI as a consumer. **No kernel driver**
  - nothing needs one. **`uinput` is only relevant to input remapping**, not configuration. The F20/USB
  path is a **separate** component.
- `docs/community-platform-{architecture,api-draft,schema}.md`: design only, not deployed. Content is
  content-addressed and **validated before listing**; diffs are **field-level** and surface
  `unknown_regions_changed`; no firmware distribution; private by default; tombstones instead of hard
  deletes.

## 15. Unknowns (canonical ledger)

`results/reconciliation/master-unknown-ledger.{md,json}` - every open item with what is ruled out, the
best evidence, the next offline step, the next hardware step, and its classification
(`DEFERRED_REQUIRES_HARDWARE` / `DEFERRED_REQUIRES_OPERATOR` / `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE`
/ `STATICALLY_EXHAUSTED`).

## 16. Next physical tests (shortest path, in order)

**First and only first action: case `C0` - the current harness *with a real A press*.**

1. Wake the unit; confirm identity (`2A24`/`2A26`) before anything else.
2. Run `C0` (`automation/scripts/d2-cases`/`d2-differential.py variant --case C0`, `D2_OBSERVE_S=15`)
   with a **confirmed** A-twice press during the observation window.
   - **Zero idle frames is NORMAL.** Success is frames *during the press*.
   - If C0 streams → **STOP.** The pre-clear was never the problem; reconcile the diff register and move
     to the next family (unresolved key ids one button per popup).
   - If C0 is silent **and the press is confirmed** → run `C1` (no pre-clear). If C1 streams → the
     pre-clear is the gate; STOP. If C1 also fails → run `C2` (official burst + no pre-clear).
   - Only if all three fail during confirmed presses: the connection-interval experiment (11.25 ms),
     which is the weakest remaining candidate.
3. Always issue D2 disable before disconnecting, and re-read D6 afterwards to confirm the baseline
   (`bdef9c61…`) is intact.
