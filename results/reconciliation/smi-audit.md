# Dart Smi / tagged-integer audit — correction ledger

**Date:** 2026-09-27. **Appends; never rewrites history.** Machine-readable twin: `smi-audit.json`.
Method: `dart-smi-methodology.md`. Executable guard: `../../tests/test_smi_constants.py`.

Scope: the four Blutter Dart-AOT trees (2.22.0901/2.17.5, 2.23.0609/2.19.6, 2.24.0919/3.2.3, 4.0.8/3.12.2)
plus the imported-research baselines, `results/static/2.22.0901/*`, `results/final/*` and the toolkit docs.
No APK was modified; no radio/hardware operations were performed; nothing was committed to the toolkit repo.

## Totals

| classification | count |
|---|---:|
| RAW INTEGER — NO CHANGE | 26 |
| CORRECT AS DOCUMENTED | 13 |
| TAGGED SMI — CORRECTED | 6 |
| AMBIGUOUS | 1 |
| **total items audited** | **46** |

## Corrections at a glance (each with >= 2 independent anchors)

| id | item | version | was | is | label |
|---|---|---|---|---|---|
| K1 | key masks | 4.0.8 (also stated for | The static key-mask getters return the literal instruction i | bit == key id (no +1): keyL1=0x40 (bit 6=LB), keyCapture=0x8 | PROVEN STATIC |
| L3 | light per-zone mode ordinals | 4.0.8 | 2,4,6 read as the raw immediates | 1, 2, 3 | replace the '2,4,6' note with '1,2,3' |
| L4 | 2.22 light mode arg | 2.22.0901 | observed effect/mode values {2,6} | 1 and 3 (mode-name mapping still UNKNOWN) | replace '{2,6}' with '{1,3}'; keep the id->name mapping UNKNOWN |
| D1 | D8 commit byte | 4.0.8 and 2.24 (import | second byte = 0x0A, a constant that is not a computed length | A4 05 D8 <nfrags+1> <csum> (5 bytes; length byte == total fr | Change the terminator byte to 0x05 in d8-macro.md, the executive report, the virtual-peripheral parser and the lab harness; delete the 0x0A special case and use the general 'length byte = total frame' rule; remove the open question. |
| D5 | 2.22 runKey default | 2.22.0901 | "runKey": 46 | 23 (= config key id of M1) | Change to runKey = 23 (M1); note that client-side envelope values are tagged. |
| D6 | 2.22 repeatTime default | 2.22.0901 | "repeatTime": 200 | 100 (ms) | Change to repeatTime = 100; keep ms as STRONG EVIDENCE |
| D4 | subpackageLength id sets (non-Smi decode error) | 4.0.8 | id 11 in the ->20 group | id 11 (devGale2) -> 72 | PROVEN STATIC |

---

## Full ledger

### K1 — keyCapture = 0x10000 and 'bit index = key id + 1'

* **Category:** key bit masks
* **Version:** 4.0.8 (also stated for 2.22/2.23/2.24 in imported notes)
* **Original interpretation:** The static key-mask getters return the literal instruction immediate; keyCapture=0x10000, keyUp=0x20000, keyL1=0x80, so bit = id+1 (Capture id 15 -> bit 16).
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x94cb70` — `mov x0, #0x10000  (Blutter annotates r0 = 65536)` [4.0.8 / 3.12.2]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x94cba8` — `mov x0, #0x20000  (keyUp)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x94cbc8` — `mov x0, #0x80     (keyL1)` [4.0.8]
  * `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/define.dart:0x7c42ac` — `mov x0, #0x10000  (keyCapture)` [2.24.0919 / 3.2.3]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a91c4` — `mov x0, #0x80     (keyL1)` [2.22.0901 / 2.17.5]
  * `/home/salamanka/armorx/re/blutter_out/asm/moojiang/units/gamepadset.dart:0x7ad700` — `mov x0, #0x80     (keyL1)` [2.23.0609 / 2.19.6]
* **Smi-vs-raw determination:** TAGGED SMI. x0 is the int-return register of a Dart int getter; the value leaving the frame is a Smi, logical value = imm/2.
* **Corrected value:** bit == key id (no +1): keyL1=0x40 (bit 6=LB), keyCapture=0x8000 (bit 15=Capture), keyUp=0x10000 (bit 16=D-pad up), keyM1=0x800000 (bit 23), keyM6=0x10000000 (bit 28).
* **Independent anchors:**
  * 24-getter set closes gaplessly onto ids 0..26+28 only when halved (unhalved collides: 0x80 would duplicate RB, keyY 0x20 would be bit 5 = no key)
  * 2.22 pp.txt:27316 [pp+0x28950] List<int>(32) [0x1,0x2,...,0x80000000] = [1<<i], printed already-decoded
  * 4.0.8 key_remap_t.dart:635 @0x92d69c map literal raw-30 -> "Capture" with sbfiz #1 boxing => id 15 == keyCapture bit after halving
  * 4.0.8 key_remap_t.dart:37 @0x92cfc8 switch case 0xf (=15) on the real int id
* **Affected docs/code:** baselines/imported-research/executive-report.md:84; baselines/imported-research/docs/mygt-4.0.8-reconciliation.md:30; armorx-re/repo/docs/mygt-4.0.8-reconciliation.md:30; results/static/2.22.0901/key-id-table.md:210 (already corrected there)
* **Evidence label:** PROVEN STATIC
* **Action required:** Rewrite the rule as bit==id everywhere. Lab 2.22 pass already corrected its copy. Do NOT commit to the toolkit repo.
* **Classification:** **TAGGED SMI — CORRECTED**

### K2 — 2.22 key-mask constants (keyL1=0x40 ...) and the bit==id rule

* **Category:** key bit masks
* **Version:** 2.22.0901
* **Original interpretation:** as documented: value = 1 << id
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a91c4` — `mov x0, #0x80 -> 0x40` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a70d0` — `mov x0, #0x20000 -> 0x10000 (keyUp)` [2.22]
* **Smi-vs-raw determination:** TAGGED SMI, correctly halved by the 2.22 pass.
* **Corrected value:** unchanged
* **Independent anchors:**
  * all 18 extracted 2.22 getters
  * pp.txt List<int>(32) powers-of-two
* **Affected docs/code:** results/static/2.22.0901/key-id-table.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### K3 — 2.23 key-mask constants

* **Category:** key bit masks
* **Version:** 2.23.0609
* **Original interpretation:** historical rows: keyL1=0x40, keyM1=0x800000, keyM6=0x10000000
* **Raw evidence:**
  * `/home/salamanka/armorx/re/blutter_out/asm/moojiang/units/gamepadset.dart:0x7ad700` — `mov x0, #0x80 -> 0x40` [2.23]
  * `/home/salamanka/armorx/re/blutter_out/asm/moojiang/units/gamepadset.dart:0x8b1d28` — `mov x0, #0x20000000 -> 0x10000000 (keyM6)` [2.23]
* **Smi-vs-raw determination:** TAGGED SMI, consistent with bit==id.
* **Corrected value:** unchanged
* **Independent anchors:**
  * same gapless getter set
  * 2.23 device check uses lsl #1 + cmp #0xc = id 6 (the tagged form)
* **Affected docs/code:** results/version-diff/static-version-matrix.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### K4 — 2.24 key-mask constants incl. keyCapture=0x8000

* **Category:** key bit masks
* **Version:** 2.24.0919
* **Original interpretation:** not previously itemised for 2.24
* **Raw evidence:**
  * `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/define.dart:0x7c42ac` — `mov x0, #0x10000 -> 0x8000 (bit 15)` [2.24]
  * `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/define.dart:0x7c42b4` — `mov x0, #0x1000 -> 0x800 (keyStart bit 11)` [2.24]
* **Smi-vs-raw determination:** TAGGED SMI.
* **Corrected value:** unchanged (bit==id holds identically)
* **Independent anchors:**
  * full 2.24 getter extraction == 2.22 set plus keyCapture
  * objs.txt Device index for devArmorX in 2.24 = 8
* **Affected docs/code:** results/version-diff/*
* **Evidence label:** check any 2.24 mask statement against this table
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### K5 — _keyByte key bitmask: mask |= 1 << k for k <= 0x20

* **Category:** key bit masks
* **Version:** 4.0.8 / 2.24
* **Original interpretation:** as documented in d8-macro.md 3.2
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85dd88` — `r1 = LoadInt32Instr(r0)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85dd94` — `cmp x1, #0x20` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85dda4` — `cmp x1, #0x3f` [4.0.8]
* **Smi-vs-raw determination:** RAW bit index (un-tagged via sbfx).
* **Corrected value:** unchanged
* **Independent anchors:**
  * cmp operand is raw after LoadInt32Instr (rule N3)
  * 1<<k ORed into an unboxed accumulator
* **Affected docs/code:** baselines/imported-research/d8-macro.md 3.2
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### K6 — 2.22 turbo-eligible id list List(20) = {23,24,25,26,0,1,3,4,16,17,18,19,6,8,7,9,13,14,10,11}

* **Category:** key bit masks
* **Version:** 2.22.0901
* **Original interpretation:** ids read straight from the pp.txt literal
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/pp.txt:57877:pp+0x4bc80` — `List<int>(20) [0x17,0x18,0x19,0x1a,0,0x1,0x3,0x4,0x10,...]` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/general/config_mapkey.dart:0x8c96b0` — `cmp x1,#0x3f ; lsl x0,x2,x1 (turboClick)` [2.22]
* **Smi-vs-raw determination:** pp.txt List<int> entries are ALREADY DECODED (proved by the powers-of-two table containing 0x80000000); the asm operand is raw after LoadInt32Instr. No halving.
* **Corrected value:** unchanged
* **Independent anchors:**
  * pp.txt decoding proof
  * asm cmp x1,#0x3f on the un-tagged element
* **Affected docs/code:** results/static/2.22.0901/turbo.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### K7 — D8 chord = key bitmask with bit = key id

* **Category:** key bit masks
* **Version:** 4.0.8 / 2.24
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85d7a4` — `slot2=(kb>>24)&0xff ... slot5=kb&0xff` [4.0.8]
* **Smi-vs-raw determination:** RAW (bit arithmetic on unboxed accumulator).
* **Corrected value:** unchanged
* **Independent anchors:**
  * same _keyByte un-tag as K5
  * docs derive k=1 -> 00 00 00 02, i.e. bit k
* **Affected docs/code:** baselines/imported-research/d8-macro.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### M1 — stick pseudo-key pattern table 0x22..0x31 -> 0x80000000,0x7f000000,...

* **Category:** macro key masks / pseudo-keys 34..49
* **Version:** 4.0.8 / 2.24
* **Original interpretation:** masks as documented (16 patterns)
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85dbc8` — `orr x2, x1, #0x80000000` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85dc28` — `mov x16, #0xa55a0000 (Blutter annotates r16 = 2774138880)` [4.0.8]
  * `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x800670` — `asr #0x18 / asr #0x10 / asr #8 / and #0xff on the stick word` [2.24]
* **Smi-vs-raw determination:** RAW. orr operands applied to an unboxed 32-bit accumulator; 0xa55a0000 printed as its decimal 2774138880 proves no tagging.
* **Corrected value:** unchanged
* **Independent anchors:**
  * orr/and on raw registers (rule N2)
  * id operands compared raw right after LoadInt32Instr (rule N3)
* **Affected docs/code:** baselines/imported-research/d8-macro.md 3.2
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### M2 — pseudo-key id range 34..49 (0x22..0x31)

* **Category:** macro key masks / pseudo-keys 34..49
* **Version:** 4.0.8
* **Original interpretation:** range as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85db78` — `cmp x2, #0x22` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85db88` — `cmp x2, #0x31` [4.0.8]
* **Smi-vs-raw determination:** RAW ids 34..49 (compare is on the value un-tagged by sbfx #1).
* **Corrected value:** unchanged
* **Independent anchors:**
  * LoadInt32Instr sbfx #1 precedes
  * 4.0.8 TranscribeFrame.getNameMapping raw 68..98 -> ids 34..49
* **Affected docs/code:** key-id-table.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### M3 — 2.22 stick pattern table

* **Category:** macro key masks
* **Version:** 2.22.0901
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a5ad0-0x7a5c14` — `orr into a 32-bit accumulator` [2.22]
* **Smi-vs-raw determination:** RAW.
* **Corrected value:** unchanged
* **Independent anchors:**
  * same raw orr signature as 4.0.8
* **Affected docs/code:** results/static/2.22.0901/d8-macro.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### L1 — encodeLedIdBit / lightIdsToMask: bit index = LED id, range 0..0x3F

* **Category:** LED/lighting masks and zone constants
* **Version:** 4.0.8
* **Original interpretation:** as documented (0x3F as a 6-bit LED id-space bound)
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x845258` — `r3 = LoadInt32Instr(r5)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x845268` — `cmp x3, #0x20` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x845270` — `cmp x3, #0x3f` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x845278` — `lsl x5, x1, x3 ; orr x7, x4, x5` [4.0.8]
* **Smi-vs-raw determination:** RAW (id un-tagged; 0x3f is a raw range bound, not a Smi literal).
* **Corrected value:** unchanged
* **Independent anchors:**
  * LoadInt32Instr precedes
  * lsl/orr on an unboxed register (rule N2)
* **Affected docs/code:** baselines/imported-research/ff-lighting.md 2
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### L2 — writeLightConfig uses 0x3F (63) as a mask/count byte

* **Category:** LED/lighting masks
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x8495c4` — `mov x16, #0x7e -> 63, stored at 4-byte stride into a List<int> element` [4.0.8]
* **Smi-vs-raw determination:** TAGGED SMI, correctly halved in the doc (0x7e -> 0x3F).
* **Corrected value:** 0x3F confirmed
* **Independent anchors:**
  * #0x1fe -> 255 in the same byte-list family proves the list is tagged
  * stride-4 stur = List<int>, not typed data (rule N5)
* **Affected docs/code:** baselines/imported-research/ff-lighting.md 1
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### L3 — writeLightConfig per-zone colour-mode index sequence is 2,4,6

* **Category:** lighting modes/effects
* **Version:** 4.0.8
* **Original interpretation:** 2,4,6 read as the raw immediates
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x849824` — `mov x16, #2 (StoreField r4->field_f, List<int> element)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x849888` — `mov x16, #4` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x8498ec` — `mov x16, #6` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x84987c` — `growable append: LoadField r3 = r0->field_f ; add x4,x3,x1,lsl #2 ; stur w16,[x4,#0xf]` [4.0.8]
* **Smi-vs-raw determination:** TAGGED SMI: element slot of a List<int> whose length field is maintained as a Smi (add x2,x1,#1; lsl x3,x2,#1; stur w3,[x0,#0xb]).
* **Corrected value:** 1, 2, 3
* **Independent anchors:**
  * Smi-encoded growable length proves List<int> (not typed data)
  * values fold onto the app's 4 named light modes as ordinals 1..3
* **Affected docs/code:** baselines/imported-research/ff-lighting.md 1
* **Evidence label:** replace the '2,4,6' note with '1,2,3'
* **Action required:** PROVEN STATIC
* **Classification:** **TAGGED SMI — CORRECTED**

### L4 — 2.22 writeLightConfig call sites set the mode argument to 2 and 6

* **Category:** lighting modes/effects
* **Version:** 2.22.0901
* **Original interpretation:** observed effect/mode values {2,6}
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_tab_light.dart:0x8da2cc` — `mov x17, #2 ; StoreField r3->field_f = r17` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_tab_light.dart:0x8da388` — `mov x17, #6 ; StoreField r3->field_f = r17` [2.22]
* **Smi-vs-raw determination:** TAGGED SMI (store into a Dart object int field). Values are 1 and 3.
* **Corrected value:** 1 and 3 (mode-name mapping still UNKNOWN)
* **Independent anchors:**
  * both stores are stur w17,[x3,#0xf] immediately before the writeLightConfig call at 0x8da348
  * consistent with the 4.0.8 per-zone mode ordinals 1,2,3 (item L3)
* **Affected docs/code:** results/static/2.22.0901/lighting.md 5
* **Evidence label:** replace '{2,6}' with '{1,3}'; keep the id->name mapping UNKNOWN
* **Action required:** STRONG EVIDENCE
* **Classification:** **TAGGED SMI — CORRECTED**

### L5 — light opcode 0x70 and headers A5/A4 (0x14a/0x148)

* **Category:** lighting masks/opcodes
* **Version:** 2.22/2.24/4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a7ba0` — `mov x17, #0xe0 -> 0x70` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a7b90` — `mov x17, #0x14a -> 0xA5` [2.22]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x84a1e0` — `mov x16, #0x14a -> 0xA5` [4.0.8]
* **Smi-vs-raw determination:** TAGGED SMI, correctly halved.
* **Corrected value:** unchanged
* **Independent anchors:**
  * same List<int> element-store signature as the D8 builder
  * live anchors A5 04 0B B4 confirm byte A5
* **Affected docs/code:** ff-lighting.md, lighting.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### L6 — Slider min=50, max=255, divisions=255

* **Category:** lighting brightness/speed
* **Version:** 2.22.0901
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_config_light.dart:0x9419d8` — `IMM: double(50) from 0x4049000000000000` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_config_light.dart:0x9419e8` — `IMM: double(255) from 0x406FE00000000000` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_config_light.dart:0x9419f8` — `mov x1, #0xff ; StoreField r0->field_2f = r1 ; stur x1,[x0,#0x2f]` [2.22]
* **Smi-vs-raw determination:** RAW: 0xff is ODD so it cannot be a Smi (rule N1); the store uses the full 64-bit stur x form while neighbouring double fields use stur d0 (rule N7).
* **Corrected value:** 255 (not 127)
* **Independent anchors:**
  * parity test (an odd immediate can never be 2n)
  * double bit patterns decode to exactly 50.0 and 255.0
* **Affected docs/code:** results/static/2.22.0901/lighting.md 5
* **Evidence label:** none; do not halve this one
* **Action required:** STRONG EVIDENCE
* **Classification:** **RAW INTEGER — NO CHANGE**

### L7 — LightColorRainBow3 colour/speed fields (field_1f/27/2f)

* **Category:** lighting/LED fields
* **Version:** 4.0.8
* **Original interpretation:** documented as STRONG EVIDENCE, field order not proven
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/widgets/rainbow/rainbow3_config_light.dart:0x9ebddc` — `mov x1, #-1 ; StoreField r0->field_1f` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/widgets/rainbow/rainbow3_config_light.dart:0x9ebde4` — `mov x1, #0xff ; StoreField r0->field_1f and r0->field_2f` [4.0.8]
* **Smi-vs-raw determination:** RAW: -1 and 0xff are not valid Smi encodings (odd / full 64-bit store) -> these fields hold untagged ints. Do NOT halve when reading them.
* **Corrected value:** unchanged
* **Independent anchors:**
  * parity rule N1 + stur-x rule N7
  * same signature as the slider divisions (item L6)
* **Affected docs/code:** baselines/imported-research/ff-lighting.md 2
* **Evidence label:** add a note that these fields are untagged
* **Action required:** STRONG EVIDENCE
* **Classification:** **RAW INTEGER — NO CHANGE**

### L8 — F8 brightness-comp (len 7/8), DD charging-light (7), F7 step-length (7/8), E1 connect-mode (6)

* **Category:** lighting opcodes/lengths
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x943d80` — `mov x16, #0x14a -> 0xA5 ; 0x943e30 #0x1f0 -> 0xF8` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x943cf0` — `cmp x1, #7 ; 0x943cb0 cmp x1, #8 (raw length compares)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x94421c` — `mov x16, #0xe -> 7 (charging-light length byte)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x9474c4` — `mov x16, #0xc -> 6 (connect-mode length byte)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x944678` — `mov x16, #0x1ee -> 0xF7` [4.0.8]
* **Smi-vs-raw determination:** opcode/length bytes are TAGGED SMI and were correctly halved; the length comparisons are RAW (cmp x1,#7 cannot be a tagged compare).
* **Corrected value:** unchanged
* **Independent anchors:**
  * A5 header 0x14a in every builder
  * 7 has no Smi encoding, so the length compares must be raw
* **Affected docs/code:** baselines/imported-research/ff-lighting.md 1
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### D1 — The D8 commit/terminator frame is A4 0A D8 <nfrags+1> <csum>

* **Category:** D8 constants and the 0x0A question
* **Version:** 4.0.8 and 2.24 (imported note also used by lab code)
* **Original interpretation:** second byte = 0x0A, a constant that is not a computed length
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85aba8` — `mov x16, #0xa ; StoreField r4->field_f (List<int> element)` [4.0.8]
  * `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/units/gamepadset.dart:0x80012c` — `mov x17, #0xa ; same store form` [2.24]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85aaf8` — `mov x16, #0x148 -> 0xA4 in the SAME list` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85abf0` — `mov x16, #0x1b0 -> 0xD8 in the SAME list` [4.0.8]
* **Smi-vs-raw determination:** TAGGED SMI. The value 5 is written; 0x0A was the un-halved immediate.
* **Corrected value:** A4 05 D8 <nfrags+1> <csum> (5 bytes; length byte == total frame bytes, so no special case is needed)
* **Independent anchors:**
  * sibling immediates in the same List<int> only make sense halved (0x148->0xA4, 0x1b0->0xD8)
  * live/deduced wire frame A4 05 D8 <nfrags+1> <csum>
  * 2.22's independent terminator immediate r17 = 10 at 0x79eb7c was already read as Dart 5
* **Affected docs/code:** baselines/imported-research/d8-macro.md 3.3 and 7 table; baselines/imported-research/executive-report.md 8; results/final/open-questions.md:12; results/final/virtual-armorx-status.md:65; ble/virtual-armorx/armorx_protocol.py:183,207; armorx-re/repo/tools/lab/harness/armorx_lab/frames.py:76
* **Evidence label:** Change the terminator byte to 0x05 in d8-macro.md, the executive report, the virtual-peripheral parser and the lab harness; delete the 0x0A special case and use the general 'length byte = total frame' rule; remove the open question.
* **Action required:** PROVEN STATIC
* **Classification:** **TAGGED SMI — CORRECTED**

### D2 — D8 payload length N = 10 + 10*nFrames; 10-byte step frames

* **Category:** D8 constants
* **Version:** 4.0.8 / 2.24 / 2.22 (7-byte frame variant)
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85cf98` — `mul by 10 for the buffer length` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85d46c` — `replaceRange(10+10i, 20+10i, toFrameCmd())` [4.0.8]
* **Smi-vs-raw determination:** RAW (multipliers/indices).
* **Corrected value:** unchanged
* **Independent anchors:**
  * arithmetic on unboxed values (rules N2/N4)
  * 2.22 uses mul by 7 + add #0xa (same raw class)
* **Affected docs/code:** d8-macro.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### D3 — fragment chunk = 15 (2.22) / subpackageLength()-5 = 15/43/67 (4.0.8)

* **Category:** D8 constants
* **Version:** 2.22 / 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x79e3b0` — `r17 = 30 (Smi 30 = Dart 15)` [2.22]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85a6f4` — `sub x1, x0, #5 after subpackageLength()` [4.0.8]
* **Smi-vs-raw determination:** RAW (immediate arithmetic; the 2.22 r17 = 30 is a tagged 15, already read correctly).
* **Corrected value:** unchanged
* **Independent anchors:**
  * live fragment length bytes 0x14/0x0E match chunk+5
  * cmp/index arithmetic on the same registers
* **Affected docs/code:** d8-macro.md 3.3
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### D4 — subpackageLength() switch on curDevice.field_7 -> 20 / 48 / 72

* **Category:** D8 constants
* **Version:** 4.0.8
* **Original interpretation:** docs read the switch ids as {1,2,3,9,10,11}->20, {4,7}->72, else 48
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x8191c4` — `ldur x2, [x0, #7] (raw field load)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x8191c8` — `cmp x2, #4 ; 0x8191d0 cmp #2 ; 0x8191d8 cmp #1` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x819200` — `cmp x2, #3` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x81920c` — `cmp x2, #7 ; 0x819214 cmp #9 ; 0x819230 cmp #0xa` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x819238` — `mov x0, #0x14 -> 20 (returned as Smi)` [4.0.8]
* **Smi-vs-raw determination:** RAW switch operand AND raw case labels (they include odd values 1,3,7,9 which could not be tagged). The returned 20/48/72 are Smis (mov x0,#0x14 etc.).
* **Corrected value:** 20 for raw ids {1,2,3,9,10}; 72 for {4,7,11}; 48 for {0,5,6,8,>11}
* **Independent anchors:**
  * odd case labels 1/3/7/9 (rule N1)
  * device-model-matrix.md's independent per-device table agrees for every id, and id 11 = devGale2 -> 72 (objs.txt)
* **Affected docs/code:** baselines/imported-research/d8-macro.md 3.3 table (lists 11 in the ->20 set)
* **Evidence label:** Fix the d8-macro.md row: 11 belongs to the 72 group (devGale2); the ->20 set is {1,2,3,9,10}.
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### D5 — runKey default in the 2.22 macro envelope literal = 46

* **Category:** D8 constants
* **Version:** 2.22.0901
* **Original interpretation:** "runKey": 46
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/armor-x_pro/armorx_pro_config_macro.dart:0x92aabc` — `mov x16, #0x2e ; Map<String,dynamic> value via LinkedHashMap []= at 0x92aac4` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/armor-x_pro/armorx_pro_config_macro.dart:0x92aadc` — `"M1" stored as runKeyName in the adjacent entry` [2.22]
* **Smi-vs-raw determination:** TAGGED SMI (Map<String,dynamic> value slot).
* **Corrected value:** 23 (= config key id of M1)
* **Independent anchors:**
  * the same literal immediate 0x2e is the app's own map key for id 23 -> "M1" (2.22 key-id-table)
  * runKeyName in the very same map literal is the string "M1"
* **Affected docs/code:** results/static/2.22.0901/d8-macro.md 1 Hop 1 ("default runKey = 46")
* **Evidence label:** Change to runKey = 23 (M1); note that client-side envelope values are tagged.
* **Action required:** PROVEN STATIC
* **Classification:** **TAGGED SMI — CORRECTED**

### D6 — repeatTime default in the 2.22 macro envelope literal = 200

* **Category:** D8 constants
* **Version:** 2.22.0901
* **Original interpretation:** "repeatTime": 200
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/armor-x_pro/armorx_pro_config_macro.dart:0x92ab20` — `mov x16, #0xc8 ; Map<String,dynamic> value via []= at 0x92ab28` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/armor-x_pro/armorx_pro_config_macro.dart:0x92ab18` — `key "repeatTime" from pp+0x45428` [2.22]
* **Smi-vs-raw determination:** TAGGED SMI.
* **Corrected value:** 100 (ms)
* **Independent anchors:**
  * same Map<String,dynamic> []= store form as the runKey entry (item D5)
  * 0xc8 is even and 400 > 255 so it cannot be a raw byte here
* **Affected docs/code:** results/static/2.22.0901/d8-macro.md 1 Hop 1
* **Evidence label:** Change to repeatTime = 100; keep ms as STRONG EVIDENCE
* **Action required:** STRONG EVIDENCE
* **Classification:** **TAGGED SMI — CORRECTED**

### D7 — D8 inter-fragment delay is 4 ms (Duration 0xfa0 us)

* **Category:** D8 constants
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85aac0` — `Obj!Duration@b34461 referenced` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/pp.txt:62489:pp+0x56188` — `Obj!Duration@b34461 : { off_8: int(0xfa0) }` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/pp.txt:4181:pp+...` — `Obj!Duration : { off_8: int(0x7a120) } = 500000 us = the live-proven 500 ms` [4.0.8]
* **Smi-vs-raw determination:** pp.txt prints DECODED Smi field values, so 0xfa0 = 4000 us. No halving needed.
* **Corrected value:** 4 ms confirmed
* **Independent anchors:**
  * the isolated 500 ms anchor (0x7a120) proves pp.txt decoding
  * int(0x30d40)=200 ms and int(0xf4240)=1 s are all plausible round durations
* **Affected docs/code:** d8-macro.md 3.3
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### D8 — 8 ms timing granularity, 12-bit time field, repeatTime as BE16

* **Category:** D8 constants
* **Version:** 4.0.8 / 2.24
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85d74c` — `sdiv x6, x5, #8` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85d758` — `and w3, w1, #0xf ; lsl #4 ; lsl #1` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85d770` — `and w1, w4, #0xff0 ; asr #4` [4.0.8]
* **Smi-vs-raw determination:** RAW (shifts/masks on unboxed values; the trailing lsl #1 is the re-tag).
* **Corrected value:** unchanged
* **Independent anchors:**
  * the explicit lsl #1 after the nibble packing is the Smi re-tag (rule P3)
  * 2.24 carries explicit mov x2,#0xf / mov x1,#0xff0 immediates
* **Affected docs/code:** d8-macro.md 3.2; macro-format.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### D9 — CRC-16/MODBUS init 0xFFFF, poly 0xA001, stored BE; fragment checksum = sum & 0xFF

* **Category:** D8 constants
* **Version:** 2.22/2.24/4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85d4bc` — `init 0xFFFF ; eor ; 8 rounds ; poly #0xa001` [4.0.8]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x79cf10` — `r6 = 65535 ; r16 = 40961 (0xA001)` [2.22]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x819078` — `getCheckSum: add chain + and #0xff` [4.0.8]
* **Smi-vs-raw determination:** RAW (unboxed arithmetic; 65535/40961 annotated as raw values).
* **Corrected value:** unchanged
* **Independent anchors:**
  * embedded default templates self-validate under the same parameter set
  * every captured outbound D7 image validated
* **Affected docs/code:** d8-macro.md 3.4; config-format.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### D10 — GamepadAtt.key runKey 0 -> 5 substitution

* **Category:** D8 constants
* **Version:** 2.22 / 4.0.8
* **Original interpretation:** byte 6 = runKey (0 -> 5 default)
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85d314` — `cbnz x1 / r3 = 5` [4.0.8]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x79ca70` — `r9 = 5 (0 -> 5 substitution)` [2.22]
* **Smi-vs-raw determination:** RAW byte value 5 (small plain int used as a byte value).
* **Corrected value:** unchanged
* **Independent anchors:**
  * the same 5 appears as a plain literal in both builds
  * no Smi doubling visible in the compare/cbnz
* **Affected docs/code:** d8-macro.md 3.1
* **Evidence label:** none
* **Action required:** STRONG EVIDENCE
* **Classification:** **RAW INTEGER — NO CHANGE**

### D11 — stick readback id table literals 0x4e/0x50/0x52/0x5e/0x62/0xfe

* **Category:** D8 constants (readback)
* **Version:** 4.0.8
* **Original interpretation:** listed as ids 78/80/82/94/98
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/transcribe_frame.dart:0x85e5d4-0x85e5f8` — `and #0xffff / and #0xffff0000 vs a 16-entry constant table` [4.0.8]
* **Smi-vs-raw determination:** AMBIGUOUS: the 16-bit halves are compared against table constants whose encoding was not established in this pass; 0xfe and the high halves could be raw patterns rather than ids.
* **Corrected value:** UNKNOWN (do not promote the 78/80/82/94/98 reading yet)
* **Independent anchors:**
  * none established in this pass
* **Affected docs/code:** d8-macro.md 5.3
* **Evidence label:** leave UNKNOWN; record the two hypotheses (raw pattern vs Smi id 39/40/41/47/49)
* **Action required:** AMBIGUOUS
* **Classification:** **AMBIGUOUS**

### E1 — devArmorX = 6 (2.23), 8 (2.24), 10 (4.0.8)

* **Category:** device enum ids
* **Version:** 2.23/2.24/4.0.8
* **Original interpretation:** as documented; 4.0.8 index 10 (0xa)
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x8103a4` — `ldur x2, [x0, #7] (Device index, raw load)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x8104c0` — `BoxInt64Instr ; cmp w0, #0x14 (= tagged 20) -> index 10` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/widgets/home/pages/config/widgets/device_card.dart:0x9cca84` — `cmp x2, #0xa (raw compare) -> devArmorX branch` [4.0.8]
* **Smi-vs-raw determination:** RAW index (raw comparands 1..9 plus one boxed compare for 10).
* **Corrected value:** unchanged
* **Independent anchors:**
  * objs.txt name/index pairs
  * deviceName() raw switch reproduces every documented name
* **Affected docs/code:** device-model-matrix.md 1/7; static-version-diff.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### E2 — macrosItemLen 6/7/10 and firmware thresholds 40/49/53/54/57/96/97

* **Category:** device enum ids
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x859014` — `macrosItemLen body; version compares` [4.0.8]
* **Smi-vs-raw determination:** RAW thresholds (version integers compared directly).
* **Corrected value:** unchanged
* **Independent anchors:**
  * the same numbers appear as raw compares (0x28/0x31/0x35/0x36/0x39/0x60/0x61)
* **Affected docs/code:** device-model-matrix.md 6.3
* **Evidence label:** none
* **Action required:** STRONG EVIDENCE
* **Classification:** **RAW INTEGER — NO CHANGE**

### C1 — config families 88/144/240/280/335/456/484/508

* **Category:** config sizes
* **Version:** all four
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x811be4` — `r2 = 144 ; mov x2, #0x90 (AllocateArray size, annotated '= 144')` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x811c50` — `cmp x4, #0x90 (raw length compare)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/objs.txt` — `ProtocolType v88/v144/v240/v280/v335/v456/v484/v508` [4.0.8]
* **Smi-vs-raw determination:** RAW (allocation sizes, array bounds and raw compares). The annotation '= 144' with mov x2,#0x90 is decisive: Blutter prints the operand and 0x90 is used as an allocation count.
* **Corrected value:** unchanged
* **Independent anchors:**
  * AllocateArray size args are plain (rule N4)
  * objs.txt enum table
  * the default template strings declare their own length bytes
* **Affected docs/code:** config-format.md; config-144-reconstruction.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### C2 — 144 = 4 header + 108 parameter block + 32 mapKeys; byte = GamepadParam30 index + 4

* **Category:** config sizes
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x813844` — `ListBase::replaceRange(start=4, end=112, paramList)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x8142a4` — `ctor sublist(0,4) header; sublist(112,144) mapKeys` [4.0.8]
* **Smi-vs-raw determination:** RAW (ReplaceRange bounds and sublist indices are plain ints).
* **Corrected value:** unchanged
* **Independent anchors:**
  * 20/20 named-offset agreement against the toolkit baseline
  * mapKeys default identity 0..31 in the embedded template
* **Affected docs/code:** config-144-reconstruction.md; config-format.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### C3 — embedded factory default template strings (JSON int lists)

* **Category:** config sizes
* **Version:** 2.22/2.24/4.0.8
* **Original interpretation:** as documented; self-validating CRCs
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x83867c` — `r0 = "[25,139,0,240,...]" (String literal, not a List<int>)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x838668` — `r0 = "[0,0,0,144,51,255,...]"` [4.0.8]
* **Smi-vs-raw determination:** RAW (JSON/string data decoded at runtime; no immediates to halve).
* **Corrected value:** unchanged
* **Independent anchors:**
  * CRC-16/MODBUS validates over bytes[2:] of the decoded image
  * byte-exact match with the live-captured device image apart from the recomputed CRC
* **Affected docs/code:** default-config-archaeology.md; config-format.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### P1 — normal DPI frame A5 05 FC <dpi&0x0F> <cks> (legacy F6)

* **Category:** DPI selectors
* **Version:** 4.0.8
* **Original interpretation:** as documented; 4-bit selector
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x94686c` — `ubfx x1, x1, #0, #0x20` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x946870` — `and w2, w1, #0xf` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x946874` — `lsl w1, w2, #1 (re-tag)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x9467b8` — `mov x16, #0x14a -> 0xA5 ; #0xa -> 5 ; #0x1f8 -> 0xFC` [4.0.8]
* **Smi-vs-raw determination:** the 0x0F is a RAW mask on an unboxed value; the header/length/opcode stores are TAGGED SMI and were correctly halved.
* **Corrected value:** unchanged (selector 0..15; F6 = 0xF6)
* **Independent anchors:**
  * mask applied after an explicit unbox (rule N2)
  * the builder's immediate pool (330/10/504/492) only makes sense halved
* **Affected docs/code:** fc-dpi.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### P2 — motion DPI frame AB 07 05 25 <lo> <hi> <cks>, u16 little-endian

* **Category:** DPI selectors
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x946158` — `342 -> 0xAB ; 14 -> 7 ; 10 -> 5 ; 74 -> 0x25` [4.0.8]
* **Smi-vs-raw determination:** TAGGED SMI, correctly halved.
* **Corrected value:** unchanged
* **Independent anchors:**
  * all four pool immediates are even (rule N1: an odd value could not be a Smi)
  * the AB family is absent in 2.22, dating the feature
* **Affected docs/code:** fc-dpi.md 3
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### P3 — legacy opcode F6 when firmware < 0x35 (53)

* **Category:** DPI selectors
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x946850` — `mov x16, #0x1ec -> 0xF6` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x9467f0` — `4 hard-coded Device objects compared` [4.0.8]
* **Smi-vs-raw determination:** TAGGED SMI for the opcode; the firmware threshold 0x35 is a RAW compare.
* **Corrected value:** unchanged (F6 = 0xF6, threshold 53)
* **Independent anchors:**
  * 0x1ec is even and >0xFF in a byte context
  * the same threshold appears raw in macrosItemLen
* **Affected docs/code:** fc-dpi.md 2
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### T1 — turbo is config-resident: byte 80 = speed index, bytes 81..84 = turboKey u32 BE

* **Category:** turbo constants
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x81325c` — `toList idx76 <- LoadStaticField(0xb60)` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x8132a4` — `idx77 <- value>>24 (and 78/79/80)` [4.0.8]
* **Smi-vs-raw determination:** RAW shifts/masks (24/16/8/0xFF) and plain parameter indices.
* **Corrected value:** unchanged
* **Independent anchors:**
  * idx addresses are plain indices (rule N4)
  * the 144-byte default template maps index+4 to bytes 80/81..84
* **Affected docs/code:** turbo.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### T2 — turbo bit index == key id

* **Category:** turbo constants
* **Version:** 2.22 / 4.0.8
* **Original interpretation:** as documented (2.22) and re-verified for 4.0.8
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/general/config_mapkey.dart:0x8c96b0` — `LoadInt32Instr(list[i]) ; cmp x1,#0x3f ; lsl x0,x2,x1 (x2=1)` [2.22]
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/pp.txt:57877:pp+0x4bc80` — `List<int>(20) [0x17,0x18,...] (decoded)` [2.22]
* **Smi-vs-raw determination:** RAW bit index = key id.
* **Corrected value:** unchanged
* **Independent anchors:**
  * LoadInt32Instr shows the list values are used un-tagged
  * the 20 ids coincide with the config key-id space
* **Affected docs/code:** turbo.md (2.22 and 4.0.8)
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **CORRECT AS DOCUMENTED**

### T3 — turboKey serializer shifts/masks (>>24, >>16, >>8, &0xFF, 0xFF000000)

* **Category:** turbo constants
* **Version:** 2.22 / 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/units/gamepadset.dart:0x7a3540` — `r1 = 0xFF000000 ; and ; lsr #24` [2.22]
* **Smi-vs-raw determination:** RAW (shift counts and masks).
* **Corrected value:** unchanged
* **Independent anchors:**
  * ops on unboxed registers (rule N2)
  * 0xFF000000 annotated as a raw register value
* **Affected docs/code:** turbo.md
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### S1 — sensorRightKeyBit / sensorSwitch u32 BE from hex strings

* **Category:** sensor/button masks
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x814ef0` — `ctor u32 BE read of the field` [4.0.8]
* **Smi-vs-raw determination:** RAW (byte-level u32 serialization; no Smi immediate involved).
* **Corrected value:** unchanged
* **Independent anchors:**
  * round-trips against live 144-byte images
  * serialized as lowercase hex by the captured client
* **Affected docs/code:** config-144-reconstruction.md 4
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### S2 — sensorRightKey0/1 defaults 2,2

* **Category:** sensor/button masks
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x838668` — `embedded default string "[0,0,0,144,...,0,0,2,2,...]"` [4.0.8]
* **Smi-vs-raw determination:** RAW (bytes 38/39 of a JSON template).
* **Corrected value:** unchanged
* **Independent anchors:**
  * index 38/39 = 2,2 in the decoded template
  * live 144-byte image matches the template except the CRC
* **Affected docs/code:** config-144-reconstruction.md 3
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### S3 — byte 45 sensorRightCurve0YDivx 0x0A -> 0x28 on profile switch

* **Category:** sensor/button masks
* **Version:** live firmware
* **Original interpretation:** as documented from a live capture
* **Raw evidence:**
  * `armorx-re/repo/docs/config-format.md:109:live pcap` — `wire bytes 0x0A -> 0x28` [live]
* **Smi-vs-raw determination:** RAW wire bytes from a capture (never a decompiler immediate).
* **Corrected value:** unchanged
* **Independent anchors:**
  * live pcap diff
  * raw byte identity of the changed offset
* **Affected docs/code:** config-format.md; research-status-2026-09-25.md
* **Evidence label:** none
* **Action required:** PROVEN (LIVE)
* **Classification:** **RAW INTEGER — NO CHANGE**

### S4 — mapKeys[source]=target; M1 (id 23) remap changes byte 135

* **Category:** sensor/button masks
* **Version:** live
* **Original interpretation:** as documented
* **Raw evidence:**
  * `armorx-re/repo/docs/config-format.md:110:live pcap` — `byte 135 0x17 -> 0x00 for M1 -> A; 112 + 23 = 135` [live]
* **Smi-vs-raw determination:** RAW wire bytes; confirms mapKeys element = target key id as a byte, consistent with bit==id for the id space.
* **Corrected value:** unchanged (mapKeys region 112..143)
* **Independent anchors:**
  * l
  * i
  * v
  * e
  *  
  * c
  * a
  * p
  * t
  * u
  * r
  * e
  * ;
  *  
  * 1
  * 4
  * 4
  *  
  * =
  *  
  * 1
  * 1
  * 2
  *  
  * +
  *  
  * 3
  * 2
  *  
  * b
  * o
  * u
  * n
  * d
  * a
  * r
  * y
* **Affected docs/code:** config-format.md; keymapping.md
* **Evidence label:** none
* **Action required:** PROVEN (LIVE)
* **Classification:** **RAW INTEGER — NO CHANGE**

### F1 — isRepeat / inUse / isSwitchModel / onlyM1M2 flags

* **Category:** configuration flags
* **Version:** all four
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x85d3a4` — `buf[7] from the isRepeat getter` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x85f88c` — `isSwitchModel compares booleans` [4.0.8]
* **Smi-vs-raw determination:** RAW/boolean (0/1 bytes; no integer constants to halve).
* **Corrected value:** unchanged
* **Independent anchors:**
  * live isRepeat round-trips as 0/1
  * booleans compare against NULL+#0x30 (false)
* **Affected docs/code:** d8-macro.md 3.1
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

### F2 — mapKeys[32] default identity sequence 0..31

* **Category:** configuration flags
* **Version:** 4.0.8
* **Original interpretation:** as documented
* **Raw evidence:**
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart:0x838668` — `template tail 00 01 02 ... 1f` [4.0.8]
  * `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/gamepadset.dart:0x811c50` — `size check cmp x4, #0x90` [4.0.8]
* **Smi-vs-raw determination:** RAW (template bytes). The identity mapping is itself the independent confirmation that the id space is one byte per slot.
* **Corrected value:** unchanged
* **Independent anchors:**
  * the tail of the embedded 144-byte template
  * live M1 remap changed exactly byte 135
* **Affected docs/code:** config-144-reconstruction.md 7
* **Evidence label:** none
* **Action required:** PROVEN STATIC
* **Classification:** **RAW INTEGER — NO CHANGE**

---

## Secondary (non-Smi) decode error found while auditing

`baselines/imported-research/d8-macro.md` §3.3's `subpackageLength()` table puts device id **11 in the
`->20` group**. Re-reading `define.dart:0x819230 cmp x2,#0xa / b.gt` shows 11 leaves through the
boxed-compare path (`cmp w0,#0x16` = tagged 22) to the `-> 72` arm. This agrees with the independent
per-device table in `device-model-matrix.md` §6.1 (id 11 = `devGale2` → 72) and with `objs.txt`.
The switch operand and its case labels are **raw** (odd labels 1,3,7,9 cannot be Smis), so the method
itself is not affected — only the table row is. Classified `RAW INTEGER — NO CHANGE` (item D4).

## Standing ambiguities (do not promote)

* **D11** — stick readback id table literals 0x4e/0x50/0x52/0x5e/0x62/0xfe: UNKNOWN (do not promote the 78/80/82/94/98 reading yet)

