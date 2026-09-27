# 2.22.0901 ↔ virtual ARMOR-X peripheral — per-opcode compatibility

Scope: the **2.22.0901** build driven against
`ble/virtual-armorx/virtual_armorx.py` over the API 33 emulator's netsim radio
(session `ble/virtual-armorx/logs/2220901-fw2741/` and `…/2220901-api33e/`).
"Requested" = actually observed leaving the app in this pass (PROVEN LIVE, raw hex in
`dynamic-run.md` §4). "Implemented" = the peripheral has an evidence-backed reply
(`armorx_protocol.py:329-356`).

## A. Opcodes the peripheral implements

| opcode | name | peripheral behaviour | requested by 2.22.0901 this session | outcome |
|---|---|---|---|---|
| `0x0B` | getZKMVer | reply `A5 05 0B <VV> <sum>` | **yes** — `A5 04 0B B4` | replied `A5 05 0B 30 E5` ✅ |
| `0xEF` | getDeviceUUID | reply `A5 0C EF <8 bytes> <sum>` | **yes** — `A5 0C EF 00×8 A0` | replied `A5 0C EF 00 01 02 03 04 05 06 07 BC` ✅ |
| `0xD6` | getDeviceConfig | 10 `A4/D6` fragments → 144-byte config | **yes, twice** — `A5 04 D6 7F` | replied 10 fragments, 144 bytes ✅ |
| `0xD7` | writeDeviceConfig | ack `A5 05 D7 00 81` | **no** | implemented, never exercised |
| `0x0E` | writeDevice | echoes the frame verbatim | **no** | implemented, never exercised |

## B. Opcodes the app DID request that the peripheral does NOT implement

Both were logged `command_unknown` with **`reply_bytes_sent: 0`** — no bytes are invented.

| opcode | name | raw frame sent by the app | peripheral | effect on the app |
|---|---|---|---|---|
| `0xD4` | getInputModel | `A5 04 D4 7D` | **UNKNOWN-by-design** — no reply | app continued to `0xD6` regardless; no crash |
| `0xD2` | testModeSwitch | `A5 05 D2 01 7D` (Button Test entry), `A5 05 D2 00 7C` (exit) | **UNKNOWN-by-design** — no reply | no visible effect; the Button Test page rendered and stayed usable |

Verbatim peripheral record:
```
{"event":"frame_in","raw":"a504d47d","parsed_opcode":"0xD4","opcode_name":"getInputModel","checksum_ok":true}
{"event":"command_unknown","raw":"a504d47d","parsed_opcode":"0xD4","reason":"no evidence-backed short reply",
 "research_status":"UNKNOWN","reply_bytes_sent":0}
```

## C. Everything else — UNKNOWN-by-design, not requested this session

The peripheral answers **none** of these (`reply_bytes_sent: 0`) and 2.22.0901 did not
send any of them in this pass:

`0x04` getBattery · `0x05` · `0x06` · `0x1A` reset · `0x1B` calibration ·
`0x25` getMotionDpi · `0x26` getMotionList · `0x70` lighting (R3) ·
`0x73` light enable state · `0xA6` · `0xA9` · `0xAB` · `0xD3` getMaxSize ·
`0xD8` macro device protocol (accepted/reassembled, **reply UNKNOWN, none sent**) ·
`0xDA` · `0xDD` charging light · `0xE1` connect mode · `0xE2` readFirmware ·
`0xE4` getMTU · `0xF5`/`0xF6`/`0xF7`/`0xF8` · `0xFC`/`0xFD` · `0xFF` lighting marker.

## D. Compatibility summary for this build

* 3 of the 5 implemented opcodes were exercised and all 3 behaved correctly
  (`0x0B`, `0xEF`, `0xD6`).
* 2 of 5 implemented opcodes were never reached (`0xD7`, `0x0E`) because 2.22.0901 only
  **read** in this pass — the config/lighting/macro editors were unreachable (§6 of
  `dynamic-run.md`), so no write path was ever entered.
* 2 opcodes were requested and deliberately left unanswered (`0xD4`, `0xD2`). The app
  tolerates both.
* The peripheral is therefore **sufficient** to get 2.22.0901 through discovery,
  identity (`0x0B`/`0xEF`) and config read (`0xD6`), but it **cannot** support any
  config write, lighting change, macro edit or DPI change with this build — those paths
  were not reachable and their opcodes were never sent.
* The only protocol incompatibility that actually **broke** the app was not an opcode at
  all: it was the **characteristic payload length of 2A26** (2.22's parser throws
  `RangeError` on a 2-byte value; `2741` (4 bytes) works). See `dynamic-run.md` §5.
