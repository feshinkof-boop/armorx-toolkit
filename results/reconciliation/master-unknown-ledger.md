# ARMOR-X Pro - master unknown ledger

Updated 2026-09-27/28. **20 entries.** Classifications: DEFERRED_REQUIRES_HARDWARE x9, DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE x3, DEFERRED_REQUIRES_OPERATOR x4, STATICALLY_EXHAUSTED x4.

Historical ids are preserved; resolved ones are marked RESOLVED with their evidence rather than deleted. Where an offline step was actually executed this pass it is marked DONE and points at `results/reconciliation/static-increments-ledger-loop.md`.

| id | question | status | classification | next offline step | next hardware step |
|---|---|---|---|---|---|
| **D2-U-001** | What write type does the official app use for D2? | RESOLVED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-002** | What is the 0x24 comparison in the 2.24 Button-Test parser? | RESOLVED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-007** | Why did the harness appear silent after a D2 enable? | RESOLVED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-010** | Does a D2 OFF pre-clear before the D2 enable suppress streaming while a key IS pressed? | OPEN - the single first physical action | `DEFERRED_REQUIRES_OPERATOR` | done: C0/C1/C2 defined, executor tested, offline matrix committed | case C0 with a CONFIRMED A-twice press |
| **D2-U-008** | Does the device require a bonded/encrypted link? | REFUTED | `STATICALLY_EXHAUSTED` | - | - |
| **D2-U-009** | Do the connection parameters cause the difference? | OPEN (weakest candidate) | `DEFERRED_REQUIRES_HARDWARE` | 11.25 ms mechanism documented (results/final/connection-params-11ms-experiment-11.25ms.md) | apply the documented OS-level mechanism, then repeat C0 |
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

**Best evidence:** the harness captured 3,292 valid 18-byte frames across 26 ids with control plane 0B -> D2 ON (no pre-clear); every 'silent' window had no press requested

**Next offline step:** -

**Next hardware step:** -

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-010 - OPEN - the single first physical action

**Question:** Does a D2 OFF pre-clear before the D2 enable suppress streaming while a key IS pressed?

**Priority:** CRITICAL

**Ruled out:** nothing yet

**Best evidence:** every streaming window lacked a pre-clear; every pre-cleared window lacked a press, so the two have never been separated. The offline virtual-device matrix shows case C0 discriminates the hypotheses

**Next offline step:** done: C0/C1/C2 defined, executor tested, offline matrix committed

**Next hardware step:** case C0 with a CONFIRMED A-twice press

**Dependencies:** none

**Classification:** `DEFERRED_REQUIRES_OPERATOR`

### D2-U-008 - REFUTED

**Question:** Does the device require a bonded/encrypted link?

**Priority:** CLOSED

**Ruled out:** bonding; encryption; SMP

**Best evidence:** BOND_NONE on the phone, zero SMP frames, zero encryption events on both sides

**Next offline step:** -

**Next hardware step:** -

**Dependencies:** none

**Classification:** `STATICALLY_EXHAUSTED`

### D2-U-009 - OPEN (weakest candidate)

**Question:** Do the connection parameters cause the difference?

**Priority:** LOW

**Ruled out:** causality (explicitly not claimed)

**Best evidence:** official 30 -> 7.5 -> 30 -> 11.25 ms (1 create + 3 update commands, verified) vs harness 7.5 ms; the app requests no interval profile at all

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

