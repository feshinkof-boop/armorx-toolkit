# ARMOR-X Pro — MASTER REPORT (supersedes all earlier handoffs)

Updated 2026-09-27/28 by the autonomous overnight shift (no hardware touched). This document is
intended to be the **only** thing a reader needs: every claim carries a grade and a pointer, and where
this shift changed an earlier conclusion the change is stated in place.

Grades: **PROVEN LIVE / PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN / CONTRADICTED /
NOT PRESENT**.

The previous physical-pass report is preserved at
`results/final/archive/real-armorx-master-report-physical-pass-2026-09-27.md`.

---

## 0a. LIVE CLOSURE - 2026-09-28: the pre-clear is not a gate (C0 answered)

Case **C0** was run on the real unit with the D2 OFF pre-clear **present** and a confirmed physical
A-twice press: **167 valid 18-byte frames**, four transitions `PRESS → RELEASE → PRESS → RELEASE` on bit 0,
only bit 0 set, 208 ms / 172 ms held, 1.021 s between presses, median held cadence 15.0 ms, and **0**
frames before the press and after the release. Verdict **`C0_STREAMS_WITH_PRECLEAR`**. Per the decision
tree the causal matrix stopped: **C1 and C2 were not run.** Post-test D6 read →
**`CONFIG_BASELINE_MATCH`** (integrity readback only; durability is unchanged at `DURABLE_OK`).
Full result: `results/experiments/d2-c0-physical-20260928-054549/RESULT.md`.

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
| harness streaming | **3,292 frames / 26 ids** with `0B → D2 ON`, no pre-clear (2026-09-27 17:08) | PROVEN LIVE |
| **C0 with pre-clear** | **167 frames / 4 transitions on bit 0** with the pre-clear present and a confirmed press (2026-09-28 05:50) | **PROVEN LIVE** |
| `D2-U-007` | **RESOLVED — explained.** Historical silent windows lacked a matched physical press; D2 is event-driven. Recorded with dated corrections, old reports preserved | PROVEN LIVE |
| `D2-U-010` (pre-clear as a suppressor) | **RESOLVED — `C0_STREAMS_WITH_PRECLEAR`**: the pre-clear does not suppress reports. C1/C2 not needed | PROVEN LIVE |
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

`results/reconciliation/master-unknown-ledger.{md,json}` - **20 entries**, each with what is ruled out,
the best evidence, the next offline step, the next hardware step and dependencies, classified
`DEFERRED_REQUIRES_HARDWARE` / `DEFERRED_REQUIRES_OPERATOR` / `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE`
/ `STATICALLY_EXHAUSTED` (4 / 4 / 3 / 9). The continuation loop was then run over it and its executed
steps are recorded in `results/reconciliation/static-increments-ledger-loop.md`: `E2`/`readFirmware`
proven to be **4.0.8-only** (the 2.2x hits are localization table indices), the app's **write-result
dispatcher** found to enumerate write-capable opcodes `{0xFD, 0xFC, 0xD8, 0xD3}` (surfacing two opcodes
new to our catalogue), and the DPI **reply**-parser search executed with a negative result so it is not
repeated.

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

---

## 2026-09-28 — physical key map closed (append-only)

**Starting state:** HEAD `2916b84`, 214 passed / 12 subtests / 0 failed, worktree clean.
Branch `research/physical-armorx-live-2026-09-27`.

**Control inventory derivation (done before any popup was raised).** From what the operator was actually
asked to press: **26 controls requested, all 26 proven live except RT.** Unresolved numeric ids
(2, 5, 9, 21, 22, 31, 32, 33) have **no** corresponding requested control, so they are not "unnamed buttons"
waiting to be found — see the classification below.

**Physical result.**

| control | popup / ACK | valid frames | bits | transitions | classification |
|---|---|---|---|---|---|
| RT | `ArmorX Key Map — RT`, open 16.8 s, ACKed 06:05:49 | **0** | none | none | `RT_NO_REPORT_OBSERVED` |
| L stick | `ArmorX Key Map — L stick`, ACKed | **0** | none | none | `STICK_NO_REPORT_OBSERVED` |
| R stick | — | — | — | — | **skipped** (L-stick probe already determined the outcome) |

HCI capture covered the whole session this time (2,049 decoded lines, 2 connect/disconnect pairs, CCCD write
to `0x0078` in both runs, 6 Write Commands on `0x0075`, and exactly **6 notifications = 3 per run**, i.e. the
sanity reply and the two D2 echoes and **no button frames at all**). Read with `btmon -r`: tshark reads 0
frames from these files, a tooling quirk, not a capture failure.

**Final id classifications:** `9` = **PROVEN_NEGATIVE** as a digital bit (analog channel unobservable by this
method); `2, 5, 21, 22, 31, 32, 33` = **UNOBSERVED_RESERVED_OR_UNUSED** (no requested control maps to them, no
label exists in any build, not emitted by this unit).

**D2-U-007 and D2-U-010 remain CLOSED** (`C0_STREAMS_WITH_PRECLEAR`, 167 frames). C1/C2 and the 11.25 ms
experiment were **not** run, per the brief.

**Config:** unchanged. Post-session read-only integrity read `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6`
→ `CONFIG_BASELINE_MATCH`. `DURABLE_OK` unchanged; `STAGED_OK != DURABLE_OK`. No D7/D8/DPI/lighting/macro
write was sent.

**Highest-value next physical step:** read the trigger from the **official app's own trigger/DPI view** while
RT is pulled (app-side readback works regardless of the wire format), since the frame stream is now proven
not to carry analog-only changes.

---

## 2026-09-28 — RT analog proven through D2 piggyback sampling (append-only)

**Question:** is RT's analog state present in D2 frames when a *digital* control forces transmission?

**Method:** analog-only movement emits no frame (proven: full stick travel and full RT travel both produced
zero frames), so the analog fields were read from frames whose transmission `A` caused. Offsets verified
first: `[15]` LT, `[16]` RT.

| window | valid frames | bits | A-caused | byte[15] on A-caused | byte[16] on A-caused |
|---|---|---|---|---|---|
| P0 baseline | 204 | {0} | 56 | 0 | 0 |
| P1 LT held | 186 | {0, 8} | 36 | **255** | 0 |
| P2 RT held | 191 | {0, 9} | 40 | 0 | **255** |
| P2R RT held (repeat) | 203 | {0, 9} | 52 | 0 | **255** |

**Verdicts:** `LT_ANALOG_PIGGYBACK_PROVEN` (the method works and is selective) and
`RT_ANALOG_PROVEN_LIVE__PLUS_DIGITAL_BIT_OBSERVED` — criteria 1,3,4,5,6 met; criterion 2 of the brief
("RT still produces no independent digital bit") is **NOT met**, because a bit 9 *did* appear, so the
result is deliberately not labelled "analog only".

**Correction carried forward:** the earlier "RT = PROVEN_NEGATIVE as a digital bit" is superseded as
method-limited (no frame is emitted while RT alone moves, so no bit could appear). The bit is preserved as
`NEW_BIT_9_OBSERVED_UNNAMED` and is not named here.

**HCI:** P1 and P2R are corroborated exactly (189 and 208 notifications matching the harness record); P0 and
P2 are not covered because btmon stopped writing mid-session — stated as a limitation, not hidden.

**State:** last write `a5 05 d2 00 7c` (D2 OFF) in every window, clean disconnect, no D7/D8/config write.
Read-only D6 integrity returns `bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` →
`CONFIG_BASELINE_MATCH`. `DURABLE_OK` unchanged.

**Next action:** one confirmation window (`A` bursts alone vs `A` bursts with RT held, one control only) to
name bit 9, or read RT's value in the official app's trigger/DPI view.

---

## 2026-09-28T06:38:30-04:00 — RT digital id 9 PROVEN LIVE; the key map is complete (append-only)

**One-variable experiment**, one connection, one D2 session, three operator windows:

| window | valid frames | A-caused | frames with bit 9 | byte[16] |
|---|---|---|---|---|
| W0 — A only (control) | 228 | 78 | **0** | 0 |
| W1 — RT fully held + A | 263 | 113 | **184** | 0 – 255 |
| W2 — A only (control) | 283 | 132 | **0** | 0 |

Temporal **ABSENT → PRESENT-WITH-RT → ABSENT**, all 8 criteria pass →
**`RT_DIGITAL_ID_9_PROVEN_LIVE`**, `KEY-U-003` **RESOLVED**. Canonical: RT = digital id **9**, mask
**`0x00000200`**, analog byte `[16]` range **0..255**; RT is **not** analog-only — its state is in D2 frames
but RT alone does not trigger a report, so it becomes observable when another digital event forces frames.

**Key map status: 27 of 27 physical controls proven live.** The only ids that remain unattributed are
2, 5, 21, 22, 31, 32, 33 — `UNOBSERVED_RESERVED_OR_UNUSED`, with no label in any build and no requested
control mapping to them.

**HCI:** one capture for the whole run (started before the connection, never restarted); coverage verified
per window by file growth, and 780 notifications decoded = 777 harness records + 2 liveness replies + the
D2-OFF echo, with 6 writes on `0x0075` and the CCCD on `0x0078`.

**Attempt 1 was void and is kept** (`attempt-1-link-lost/`): restarting btmon mid-connection kills the BLE
link (btmon takes the HCI user channel), so W1/W2 captured nothing. Fixed with a single external capture,
per-window buckets, and an active `0B` liveness probe between windows (all three returned alive).

**State:** `a5 05 d2 00 7c` last write, clean disconnect, no D7/D8/config write; read-only D6 integrity
`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` → `CONFIG_BASELINE_MATCH`
(`DURABLE_OK` unchanged).


## DATED ADDENDUM — 2026-09-28T07:05:00-04:00: DPI / trigger-command phase (static only)

New deliverables: `results/reconciliation/dpi-trigger-command-corpus.{json,md}`,
`dpi-trigger-callgraph.{json,md,dot}`, `results/final/real-trigger-travel.md`, and the tool
`automation/scripts/frame-literal-scan.py`.

Three headline results:

1. **`F7` is the stick step-length / "step accuracy" setting, not trigger travel.** The UI strings are
   「步长精度设置」/「Step accuracy setting」 with the tip 「步长精度影响**摇杆**的精确度」 — it affects the
   **stick**. The brief's trigger-travel hypothesis is recorded as **CONTRADICTED**, not silently dropped.
2. **`FC` has three distinct roles**, now separated explicitly: DPI read (`A5 05 FC 80 26`, live-proven),
   DPI write (`A5 05 FC <sel&0x0F>`), and macro transcription control (`A5 0B FC 00/01`).
3. **`F6` is the legacy-DPI twin of `FC`**, selected by device model + firmware version inside a single
   `getDpi` function — not a separate feature.

Cross-version: **2.22.0901 has none of F7/F6/FC**; `FC` arrives in 2.23, `F6` and `F7` in 2.24.
The frame-literal tool independently reproduces every live-known frame (`A5 05 FC 80 26`,
`A5 05 D2 01 7D`, `A5 05 D2 00 7C`, `A5 04 0B B4`), which validates both the tool and the `sum8`
checksum rule. No hardware was touched in this pass.


## DATED ADDENDUM — 2026-09-28T07:49:00-04:00: F7 read probed live, read-only

The app's own `getStepLength` request, `A5 04 F7 A0`, was sent twice under a single pre-connection
HCI capture. **Verdict `F7_NO_REPLY_LINK_HEALTHY`:** no notification of any kind followed either
attempt, while the `0B` sanity control answered before, between and after and the FC DPI control
passed before and after — all five replies in 23-30 ms. HCI decoded with `btmon -r` independently
shows 7 writes / 5 notifications with the two F7 writes followed by nothing. Config integrity:
`bdef9c61...` `CONFIG_BASELINE_MATCH` (read-only, not a new durability proof; `DURABLE_OK` stands).

`F7_WRITE_ONLY` is **not** claimed - see `results/experiments/f7-read-live-20260928-074652/RESULT.md` for the alternative explanations that
silence leaves open. No mutating command was sent.
