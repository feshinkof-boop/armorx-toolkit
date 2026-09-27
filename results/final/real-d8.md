# Real D8 (macro commit) — state of evidence

## 1. Corrected frame facts (already established, not re-proven here)

`A4` fragment layout: byte 0 = `A4`, byte 1 = **total frame length**, byte 2 = opcode,
byte 3 = ordinal, then payload, then checksum. The D8 commit frame is
`A4 05 D8 <nfrags+1> <checksum>`. `A4 0A D8` is the old erroneous terminator and must not be used.

Generations:

| generation | firmware | record | payload class |
|---|---|---|---|
| OLD | 2.22 / 2.23 | 7-byte `GamepadDefMap` | 15-byte segment payload |
| MODERN | 2.24 / 4.0.8 | 10-byte `TranscribeFrame` | 15 / 43 / 67 |

## 2. Real fragment class for THIS unit — determined from evidence, not from MTU

**Answer: 15-byte payload (20-byte `A4` frames).** Evidence:

1. **Static (PROVEN STATIC).** `moojiang/define.dart::subpackageLength()` at `0x819190` in the
   4.0.8 Dart AOT image is a switch on `curDevice` field `field_7` that returns exactly three
   frame sizes: **`0x14` = 20**, **`0x30` = 48**, **`0x48` = 72**. With the project's proven rule
   `payload = subpackageLength() - 5`, those are payloads of **15 / 43 / 67** — the exact triple the
   newer-generation serializer supports. The alternatives (43 / 67) exist for other device codes,
   so MTU alone could never have selected between them.
2. **Live (PROVEN LIVE).** On this unit, every `A4` frame actually accepted and answered used the
   **20-byte** form — e.g. the D7 write fragments `a4 14 d7 01 …` (10 fragments for the 144-byte
   image) and the D6 read fragments `a4 14 d6 …` (9 × 20 + 1 × 14 bytes, i.e. the 144-byte image).
   The same 20-byte class carried the earlier validated no-op D7 round trip.

So the smallest legal D8 test on this unit must use **15-byte payloads**, which is also the
historically minimum-supported class — the safest starting point if a D8 test is ever attempted.

## 3. What is NOT done

- No D8 write has been attempted. `results/final/d8` readback/macro-state work needs the unit
  awake and connected, and macro preservation (§30) must be established first: a target slot has
  to be provably empty, or the operator must pick one through a GUI dialog. Overwriting unknown
  user macro state is not acceptable.
- `A4 0A D8` remains forbidden; serializers must not be mixed between generations.

## 4. Provenance

- static: `armorx-re/mygt408/blutter_out/asm/moojiang/define.dart` lines 316–399
  (`subpackageLength`), Dart 3.12.2 AOT for build 4.0.8
- live: recorded `A4` frames in `results/experiments/physical-20260927-*/session.jsonl`
- rule `payload = subpackageLength() - 5`: `automation/scripts/emergency-restore/emergency-restore.py`
  (`--chunk` default 15, documented as `subpackageLength()-5` = 15/43/67)
