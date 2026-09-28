# ARMOR-X Pro - master unknown ledger

Updated 2026-09-28 after the live C0 physical test. **20 entries.** Classifications: DEFERRED_REQUIRES_HARDWARE x9, DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE x3, DEFERRED_REQUIRES_OPERATOR x3, STATICALLY_EXHAUSTED x5.

Historical ids are preserved; resolved ones carry their evidence rather than being deleted. Offline steps executed in the overnight shift are marked DONE in `results/reconciliation/static-increments-ledger-loop.md`.

| id | question | status | classification | next offline step | next hardware step |
|---|---|---|---|---|---|
| **D2-U-001** | What write type does the official app use for D2? | RESOLVED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-002** | What is the 0x24 comparison in the 2.24 Button-Test parser? | RESOLVED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-007** | Why did the harness appear silent after a D2 enable? | RESOLVED | `STATICALLY_EXHAUSTED` | none - closed | none - closed |
| **D2-U-010** | Does a D2 OFF pre-clear before the D2 enable suppress streaming while a key IS pressed? | RESOLVED - C0_STREAMS_WITH_PRECLEAR | `STATICALLY_EXHAUSTED` | none - closed | none - closed |
| **D2-U-008** | Does the device require a bonded/encrypted link? | REFUTED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-009** | Do the connection parameters cause the difference? | NOT IMPLICATED (stays the weakest candidate; do not run unless a new failure appears) | `DEFERRED_REQUIRES_HARDWARE` | 11.25 ms mechanism documented (results/final/connection-params-11ms-experiment-11.25ms.md) | apply the documented OS-level mechanism, then repeat C0 |
| **KEY-U-001** | Which buttons are ids 2, 5, 21, 22, 31, 32, 33? | OPEN | `DEFERRED_REQUIRES_OPERATOR` | - | one button per popup, operator-acknowledged, no order assumption |
| **KEY-U-002** | Does RT (id 9) have a digital key id on this unit? | OPEN (proven negative as a digital bit) | `DEFERRED_REQUIRES_OPERATOR` | - | physical RT press with analog readback to decide analog-only vs absent |
| **DPI-U-001** | What real DPI value does selector N mean? | OPEN | `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE` | - | none useful without the vendor table |
| **DPI-U-002** | What is the shape of the DPI reply (live: a5 05 ff fc a5)? | OPEN | `DEFERRED_REQUIRES_HARDWARE` | a dedicated static search for the notification handler in all four builds - DONE this pass: no reply-side dispatch on 0xFC/0xF6 found (see results/reconciliation/static-increments-ledger-loop.md §4), so this route is cold; the productive route is a live selector sweep | re-read the query and vary the selector while capturing, to see which field moves |
| **MOT-U-001** | What do the AB motion/gyro payload fields mean (mode, sensitivity, deadzone, filter)? | OPEN | `DEFERRED_REQUIRES_HARDWARE` | static field trace around writeMotionDpiConfig @0x946158 | none until a reply exists |
| **LGT-U-001** | What is the RGB byte order and the lighting field layout? | OPEN | `DEFERRED_REQUIRES_OPERATOR` | static field trace through writeLightConfig and the 0x05/0x3F sub-commands | minimum reversible experiment: one zone, one known colour, visual confirm, restore |
| **D8-U-001** | What selects the D8 chunk class (15 / 43 / 67 payload sizes)? | OPEN (static step available) | `DEFERRED_REQUIRES_HARDWARE` | static branch analysis of the fragmenter in all four builds | read a macro back and observe which classes the device emits |
| **CFG-U-001** | What are the 10 UNKNOWN byte regions of the 144-byte configuration? | OPEN | `DEFERRED_REQUIRES_HARDWARE` | resolve more regions statically from the four builds' config codecs | controlled single-field diffs with readback + power-cycle verification |
| **WIN-U-001** | Why does the current Windows Assistant leave the ARMORX legacy device type inaccessible? | OPEN (static step available) | `DEFERRED_REQUIRES_HARDWARE` | PE xref pass mapping the classifier to the UI device list | attach the unit and observe which type the Assistant picks |
| **WIN-U-002** | Is there a latent ArmorX Pro factory/DFU path in the vendor software? | OPEN | `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE` | dedicated static pass over the DFU/upgrade DLLs | NOT to be attempted (no flash/firmware operations) |
| **WIN-U-003** | Does the pad re-enumerate differently in normal vs Xbox-compatible mode? | OPEN | `DEFERRED_REQUIRES_HARDWARE` | static prediction of which descriptors each mode would request | mode switch on real hardware with enumeration monitoring |
| **FW-U-001** | Which MCU is in the ARMOR-X Pro body? | OPEN | `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE` | static analysis of the vendor .ufw container/signature handling | a firmware dump (not attempted, and not proposed) |
| **SES-U-001** | Can an 11.25 ms connection interval be requested reproducibly on Linux? | OPEN | `DEFERRED_REQUIRES_HARDWARE` | done | apply and measure without a device first, then with |
| **OP-U-001** | What are opcodes 0xFD and 0xD3, and what does the app's per-opcode write-result dispatcher imply? | OPEN | `DEFERRED_REQUIRES_HARDWARE` | trace the 0xFD and 0xD3 builders and their consumers in all four builds | none until the builders are understood |

## Entries in detail

### D2-U-001 - RESOLVED

**Question:** What write type does the official app use for D2?

**Priority:** CLOSED

**Ruled out:** write-with-response

**Best evidence:** the official capture shows ATT Write Command (0x52) on handle 0x0075 = write WITHOUT response, identical to the harness

**Next offline step:** -

**Next hardware step:** -

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-002 - RESOLVED

**Question:** What is the 0x24 comparison in the 2.24 Button-Test parser?

**Priority:** CLOSED

**Ruled out:** 36-byte frame length; a container .length; an array index; a byte offset; an enum

**Best evidence:** 0x24 is the tagged Smi of 18 (18<<1); verified byte-level at 0x8b06e8 in 2.23 (LoadInt32Instr then cmp x1,#0x12) and corroborated by all 155 live frames carrying byte[1]=0x12

**Next offline step:** -

**Next hardware step:** -

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-007 - RESOLVED

**Question:** Why did the harness appear silent after a D2 enable?

**Priority:** CLOSED

**Ruled out:** a device-level difference between app and harness; a capability limit of the harness

**Best evidence:** Two independent facts. (1) The harness streams: 3,292 valid frames / 26 ids in the 2026-09-27 17:08 run under 0B -> D2 ON with no pre-clear. (2) PROVEN LIVE 2026-09-28: case C0 - WITH the D2 OFF pre-clear and a confirmed A-twice press - produced 167 valid frames including PRESS/RELEASE/PRESS/RELEASE on bit 0, while 0 frames arrived before the press and after the release. So the historical differential windows were silent because no physical press was requested in them, not because of any protocol state. EXPLANATION RECORDED, NOT ERASED: see results/reconciliation/d2-u007-harness-streaming-reconciliation.md and results/experiments/d2-c0-physical-20260928-054549/RESULT.md

**Next offline step:** none - closed

**Next hardware step:** none - closed

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-010 - RESOLVED - C0_STREAMS_WITH_PRECLEAR

**Question:** Does a D2 OFF pre-clear before the D2 enable suppress streaming while a key IS pressed?

**Priority:** CRITICAL

**Ruled out:** the D2 OFF pre-clear as a suppressor of button reports

**Best evidence:** PROVEN LIVE 2026-09-28: C0 (pre-clear present) + confirmed A-twice press = 167 valid frames, 4 transitions PRESS/RELEASE/PRESS/RELEASE on bit 0, only bit 0 set; 0 frames before the press and 0 after the release. C1/C2 were NOT run - the question was already answered.

**Next offline step:** none - closed

**Next hardware step:** none - closed

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-008 - REFUTED

**Question:** Does the device require a bonded/encrypted link?

**Priority:** CLOSED

**Ruled out:** bonding; encryption; SMP

**Best evidence:** BOND_NONE on the phone, zero SMP frames, zero encryption events on both sides

**Next offline step:** -

**Next hardware step:** -

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-009 - NOT IMPLICATED (stays the weakest candidate; do not run unless a new failure appears)

**Question:** Do the connection parameters cause the difference?

**Priority:** VERY LOW

**Ruled out:** causality (explicitly not claimed)

**Best evidence:** official 30 -> 7.5 -> 30 -> 11.25 ms (1 create + 3 update commands, verified) vs harness 7.5 ms; the app requests no interval profile at all 2026-09-28: C0 streamed 167 frames with the harness's own 7.5 ms interval, so no interval change is needed to receive button reports.

**Next offline step:** 11.25 ms mechanism documented (results/final/connection-params-11ms-experiment-11.25ms.md)

**Next hardware step:** apply the documented OS-level mechanism, then repeat C0

**Dependencies:** D2-U-010 must fail first

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### KEY-U-001 - OPEN

**Question:** Which buttons are ids 2, 5, 21, 22, 31, 32, 33?

**Priority:** MEDIUM

**Ruled out:** nothing yet

**Best evidence:** no physical button produced these bits in any capture; the static label inventories do not resolve them; define.dart getters are offset +1 and cannot be used to name wire bits

**Next offline step:** -

**Next hardware step:** one button per popup, operator-acknowledged, no order assumption

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_OPERATOR`

### KEY-U-002 - OPEN (proven negative as a digital bit)

**Question:** Does RT (id 9) have a digital key id on this unit?

**Priority:** MEDIUM

**Ruled out:** id 9 as RT's bit

**Best evidence:** requested in 4 windows + 3 dedicated retries; never appeared; analog byte [16] never left zero

**Next offline step:** -

**Next hardware step:** physical RT press with analog readback to decide analog-only vs absent

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_OPERATOR`

### DPI-U-001 - OPEN

**Question:** What real DPI value does selector N mean?

**Priority:** MEDIUM

**Ruled out:** any in-binary mapping table

**Best evidence:** the selector is a 4-bit mask; presets come from the vendor's server, so nothing in the APK maps selector->DPI App-side note: 0xFC appears in the write-result dispatcher (frame_config_macros.dart), so the app treats DPI writes as acknowledged.

**Next offline step:** -

**Next hardware step:** none useful without the vendor table

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE`

### DPI-U-002 - OPEN

**Question:** What is the shape of the DPI reply (live: a5 05 ff fc a5)?

**Priority:** MEDIUM

**Ruled out:** nothing yet

**Best evidence:** one live reply captured, checksum valid, semantics undecoded

**Next offline step:** a dedicated static search for the notification handler in all four builds - DONE this pass: no reply-side dispatch on 0xFC/0xF6 found (see results/reconciliation/static-increments-ledger-loop.md §4), so this route is cold; the productive route is a live selector sweep

**Next hardware step:** re-read the query and vary the selector while capturing, to see which field moves

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### MOT-U-001 - OPEN

**Question:** What do the AB motion/gyro payload fields mean (mode, sensitivity, deadzone, filter)?

**Priority:** LOW

**Ruled out:** nothing yet

**Best evidence:** the writer AB 07 05 25 <u16 LE> and the query shapes AB 05 05 25/26 are known; the queries return NOTHING on this firmware

**Next offline step:** static field trace around writeMotionDpiConfig @0x946158

**Next hardware step:** none until a reply exists

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### LGT-U-001 - OPEN

**Question:** What is the RGB byte order and the lighting field layout?

**Priority:** MEDIUM

**Ruled out:** conventional RGB ordering (no evidence)

**Best evidence:** the 0x70 writers exist in all builds but no read path exists; RGB order is UNKNOWN in all four builds

**Next offline step:** static field trace through writeLightConfig and the 0x05/0x3F sub-commands

**Next hardware step:** minimum reversible experiment: one zone, one known colour, visual confirm, restore

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_OPERATOR`

### D8-U-001 - OPEN (static step available)

**Question:** What selects the D8 chunk class (15 / 43 / 67 payload sizes)?

**Priority:** MEDIUM

**Ruled out:** A4 0A D8 as a commit frame (CONTRADICTED in all four builds)

**Best evidence:** commit is A4 05 D8 <nfrags+1> <cks>; the 10-byte TranscribeFrame model and subpackageLength-5 arithmetic are reconstructed; the class selector is not

**Next offline step:** static branch analysis of the fragmenter in all four builds

**Next hardware step:** read a macro back and observe which classes the device emits

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### CFG-U-001 - OPEN

**Question:** What are the 10 UNKNOWN byte regions of the 144-byte configuration?

**Priority:** HIGH

**Ruled out:** nothing yet

**Best evidence:** config-byte-evidence-map: 25 PROVEN STATIC / 10 UNKNOWN / 1 PROVEN LIVE; baseline and mutant images both exist and differ in {0,1,127}

**Next offline step:** resolve more regions statically from the four builds' config codecs

**Next hardware step:** controlled single-field diffs with readback + power-cycle verification

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### WIN-U-001 - OPEN (static step available)

**Question:** Why does the current Windows Assistant leave the ARMORX legacy device type inaccessible?

**Priority:** MEDIUM

**Ruled out:** conflating the two numbering systems (now explicitly separated)

**Best evidence:** DevMgr.dll has t_BBW_DevType and t_ProductType colliding at 5-7; the classifier switch is at 0x1003212f

**Next offline step:** PE xref pass mapping the classifier to the UI device list

**Next hardware step:** attach the unit and observe which type the Assistant picks

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### WIN-U-002 - OPEN

**Question:** Is there a latent ArmorX Pro factory/DFU path in the vendor software?

**Priority:** LOW

**Ruled out:** nothing yet

**Best evidence:** devmgr_dfu_analysis.json exists as a starting point; no factory entry point was identified

**Next offline step:** dedicated static pass over the DFU/upgrade DLLs

**Next hardware step:** NOT to be attempted (no flash/firmware operations)

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE`

### WIN-U-003 - OPEN

**Question:** Does the pad re-enumerate differently in normal vs Xbox-compatible mode?

**Priority:** MEDIUM

**Ruled out:** nothing yet

**Best evidence:** the Windows-side question is about device behaviour, not code

**Next offline step:** static prediction of which descriptors each mode would request

**Next hardware step:** mode switch on real hardware with enumeration monitoring

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### FW-U-001 - OPEN

**Question:** Which MCU is in the ARMOR-X Pro body?

**Priority:** LOW

**Ruled out:** nothing yet

**Best evidence:** RCSP-capable service layout + a JieLi AC632N .ufw upgrade library in the vendor Windows software => AC6321A/AC632N/BD19 is STRONG EVIDENCE, not proof; no firmware image exists locally

**Next offline step:** static analysis of the vendor .ufw container/signature handling

**Next hardware step:** a firmware dump (not attempted, and not proposed)

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE`

### SES-U-001 - OPEN

**Question:** Can an 11.25 ms connection interval be requested reproducibly on Linux?

**Priority:** LOW

**Ruled out:** nothing yet

**Best evidence:** mechanism research is documented (BlueZ/btmgmt/kernel vs raw HCI) with privileges, adapter requirements and rollback

**Next offline step:** done

**Next hardware step:** apply and measure without a device first, then with

**Dependencies:** D2-U-010 must fail

**Classification:** `DEFERRED_REQUIRES_HARDWARE`

### OP-U-001 - OPEN

**Question:** What are opcodes 0xFD and 0xD3, and what does the app's per-opcode write-result dispatcher imply?

**Priority:** MEDIUM

**Ruled out:** nothing yet

**Best evidence:** frame_config_macros.dart (4.0.8) dispatches write results on {0xFD, 0xFC, 0xD8, 0xD3}; 0xFD and 0xD3 were not previously in our opcode catalogue

**Next offline step:** trace the 0xFD and 0xD3 builders and their consumers in all four builds

**Next hardware step:** none until the builders are understood

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_HARDWARE`


---

## 2026-09-28 — key-ID closure session (append-only)

Session: `results/experiments/key-id-closure-20260928-060134/` (RESULT.md is authoritative for detail).

- **Phase 1 (before any popup):** the physical-control list was derived from what the operator was actually
  asked to press (`results/runtime/press-groups.jsonl`) cross-checked with the proven-live map.
  **26 controls requested, 26 proven live.** Only **RT** was requested and never proven. Two analog sticks
  had never been requested at all. Sources: `control-inventory.{json,md}` in the session directory.
- **KEY-U-002 (RT / id 9) → RESOLVED.** RT was requested again with two FULL pulls inside a popup open
  16.8 s, ACKed 06:05:49. **Zero frames of any kind** arrived; HCI shows exactly 3 notifications for that run
  (sanity reply, D2 enable echo, D2 disable echo). Digital: **PROVEN NEGATIVE**. Analog: **UNOBSERVABLE BY
  THIS METHOD** — the L-stick probe (full travel twice) also produced zero frames, proving the device emits no
  report frame for analog-axis-only changes. `RT_ANALOG_ONLY` is neither confirmed nor excluded, and no
  analog claim is made. The earlier wording "analog byte [16] never left zero" was wrong and is corrected:
  the byte was never *sampled* during RT movement.
- **KEY-U-001 (ids 2, 5, 21, 22, 31, 32, 33) → RESOLVED_FOR_THIS_UNIT** as
  `UNOBSERVED_RESERVED_OR_UNUSED`: no requested physical control maps to them, and no label exists for them
  in any of the four builds. The app's 32-slot `mapKeys` space is larger than the number of controls this
  unit reports. Observed negative on this hardware.
- Post-session read-only integrity read: `bdef9c61…` → `CONFIG_BASELINE_MATCH` (integrity readback only, not
  a durability proof). Final runtime write on the wire: `a5 05 d2 00 7c`.
- Harness defect found and fixed: the one-control runner resolved the dialog helper to a **non-existent
  path**, so the first RT popup never appeared and the harness **misreported it as `OPERATOR_CANCELLED`**.
  Fixed: the helper is resolved at its real path, a missing helper is a hard error, and only rc == 1 counts as
  an operator cancel (rc 2/3/127 are harness faults).

---

## 2026-09-28 — RT analog piggyback session (append-only)

- **KEY-U-002 → RESOLVED (analog) / SUPERSEDED (digital negative).** RT's analog travel is **PROVEN LIVE in
  D2 byte[16]**: 0 at rest, 255 at a full pull, in every frame whose transmission `A` caused (40/40 in P2,
  52/52 in the repeat), with byte[15] flat. The earlier `PROVEN_NEGATIVE` digital verdict is **retracted as
  method-limited** — RT alone emits no frame, so nothing could appear in those windows and `[16]` was never
  sampled (the old wording "never left zero" was wrong: unsampled ≠ measured zero). The LT positive control
  (`LT_ANALOG_PIGGYBACK_PROVEN`) validated the method before the RT window ran.
- **KEY-U-003 OPEN (new).** A digital mask bit **9** appeared only while RT was fully held (masks `513`/`512`;
  107 frames in P2, 144 in the repeat; absent from the baseline and LT windows). It is preserved as
  `NEW_BIT_9_OBSERVED_UNNAMED` and deliberately **not named**: the candidate is RT, but that needs its own
  one-variable confirmation.
- HCI: P1 and P2R corroborated exactly (189 / 208 notifications matching the harness record); P0 and P2 are
  **not** covered — btmon stopped writing mid-session. Stated, not hidden.
- State: `a5 05 d2 00 7c` last write, clean disconnect, no D7/D8/config write, read-only D6 integrity
  `bdef9c61…` → `CONFIG_BASELINE_MATCH` (`DURABLE_OK` unchanged).

---

## 2026-09-28 — KEY-U-003 RESOLVED: bit 9 is RT (append-only)

One-variable confirmation (`results/experiments/rt-bit9-confirmation-20260928-063300/`): `A` alone → **RT**
fully held + `A` → `A` alone, one connection, one D2 session.

| window | valid frames | A-caused | frames with bit 9 | byte[16] |
|---|---|---|---|---|
| W0 control | 228 | 78 | **0** | 0 |
| W1 RT held | 263 | 113 | **184** | 0 – 255 |
| W2 control | 283 | 132 | **0** | 0 |

All 8 criteria pass → **`RT_DIGITAL_ID_9_PROVEN_LIVE`**. Canonical RT: digital id **9**, mask
**`0x00000200`**, analog byte `[16]` range **0..255**; RT is **not** analog-only (its state is in D2 frames,
but RT alone does not trigger a report). **The key map is now complete: 27/27 proven live.** Remaining
unattributed ids: 2, 5, 21, 22, 31, 32, 33 (`UNOBSERVED_RESERVED_OR_UNUSED`).

Attempt 1 of this experiment was void (restarting btmon mid-connection kills the BLE link) and is preserved
under `attempt-1-link-lost/`.

---

## Addendum — 2026-09-28, F7 value-provenance pass (static-only, HEAD `0e59a66`)

Full trace: `results/reconciliation/f7-value-provenance.{md,json}`, graph `f7-dataflow.dot` (+ `.svg`/`.png`).

- **`TRG-U-003` → ANSWERED STATICALLY, `STATICALLY_EXHAUSTED`.** The step-length value can only arrive as an **inbound F7 *event* frame** (≥7 bytes, write-shaped: `A5 ≤len F7 <flag> <lo> <hi> [extra] <cks>`), delivered by the generic stream `BluetoothModel.notifyCharacteristicStream` (0x826814 over `AsyncBroadcastStreamController` `field_43`, fed by the notify callback 0xacb7f8) to `_handleConfigEvent` (0xab94fc), whose follow-up closure 0xab9764 stores state **`field_23`** — exactly the field `_requestStepLength` (0xa6e320) polls (max **3 attempts**) to stop retrying. **No other source exists**: `step_accuracy`/`stepLength` have 24/27 AOT hits and **0** hits in the app's assets (`SERVER_PROFILE_VALUE`: NOT OBSERVED).
- **`TRG-U-001` stays OPEN / `DEFERRED_REQUIRES_HARDWARE`.** Silence ranking: (1) an F7 event is expected and never arrived; (2) the read expects no reply on this model; (3) a state/page gate was missing — the earlier probe sent **2 of the app's 3 attempts** and omitted the handshake ordering. Verdict remains **`F7_NO_REPLY_LINK_HEALTHY`**; `F7_WRITE_ONLY` is still **not** concluded.
- **`TRG-U-004` ADDED** (does the device ever emit such an event?): not observed anywhere held — 3 decoded btmon captures (0 unsolicited RX) and the official app's 250-record live session (**zero** records containing `f7`); the latter was a D2/button session, so its absence is expected and is *not* evidence about F7. Next: the corrected **read-only** probe (3 attempts, ≥10 s tail, app handshake first) — prepared, **not run**.
- **`TRG-U-005` ADDED** (flag + optional byte): the flag selects frame length (`((flag & 2) + 14) / 2` → 7 or 8, `and x3,x3,#2` @0x944610), so it governs the optional byte; its feature meaning is unresolved.
- **`PRS-U-001`**: F7 shares the direct-write path; an F7 write is **`WRITE_TEST_NOT_YET_SAFE`** — no restoration value exists (no readback, no proven device event; `field_23` is filled only by that same event).
- **D6:** `F7_NOT_D6_GOVERNED_STATICALLY_OBSERVED` (STRONG EVIDENCE) — no offset, property, serializer or conversion path links F7 to the 144-byte config.
- **Cross-version:** the inbound config-event architecture (broadcast stream) is **absent in 2.22/2.23**, appears with F6/F7 in **2.24** (15 consumers), and is refactored to 2 root consumers in **4.0.8**.
