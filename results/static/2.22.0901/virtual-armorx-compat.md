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

---

## E. 0xD4 status change — 2026-09-27 (four-build reconstruction)

`0xD4` is no longer UNKNOWN-by-design. The receive/parser side was reconstructed from the
Blutter disassembly of all four builds; the full trace lives in
`results/reconciliation/d4-reconstruction.md` (+ `.json`).

| version | D4 sender (builder) | D4 receiver evidence | frame the peripheral now answers |
|---|---|---|---|
| 2.22.0901 | `getOnBoardConfig` closure `@0x89adac` | `0x89bcac` reads whole-frame index 4 (arg `#8`, halved) → `field_1f` | `A5 04 D4 7D` → `A5 06 D4 <gamepad_mode> <onboard_mode> <sum>` |
| 2.23.0609 | `getInputModel` `@0x8afa98` | `0x8af690` reads index 3 == 6 → `getDpi()`; `0x8097cc` reads index 4 | same request, same reply |
| 2.24.0919 | `getOnBoardConfig` `@0x91b988` | `0x91a528` index 3 == 6 → `getDpi()`; `0x8a9824` prints `"板载mode = "` + index 4 | same request, same reply |
| 4.0.8 | `BluetoothModel::getInputModel` `@0xa84258` | `0x8b3c84` reads index 3 (**and** index 4 == 3); `0x826ecc` prints `"板载mode = "` + index 4 | same request, same reply |

**What changed in the peripheral**

* `armorx_central_client.py` / `selftest.py` now exercise `A5 04 D4 7D` and assert the reply
  (selftest `reply_D4_input_model`).
* `armorx_protocol.py`: `D4_REQUEST`, `build_d4_reply()`, `parse_d4_reply()` (structured:
  `gamepad_mode`, `onboard_mode`, indices, `checksum_ok`), `REPLY_TABLE[0xD4]` =
  EVIDENCE-BACKED (structure).
* `virtual_armorx.py`: the `0xD4` branch logs a structured `d4_reply` event and notifies
  the frame; raw TX/RX logging unchanged. New options `--d4-gamepad-mode` /
  `--d4-onboard-mode`.
* Unit tests added for: the byte-exact request, the reply layout/checksum, four test
  vectors, a bad checksum, a truncated reply, and a wrong opcode. `pytest` 29 passed;
  `selftest.py` 12/12 + 15/15 passed.

**What is still NOT proven (and therefore not fabricated)**

The reply **structure** is proven; the **value domain of the two payload bytes is
UNKNOWN**. Byte 3 (`手柄模式`/gamepad mode) is only known to be distinguished at value `6`
(it gates a `getDpi()` follow-up); byte 4 (`板载mode`/onboard mode) is never compared to
anything except the constant `3` in 4.0.8's rainbow_more. The peripheral therefore sends
CLI-chosen values (defaults `0x00`/`0x00`), documented as chosen device state in the same
way as `--device-uuid` / `--zkm-version` — **no device value is claimed as researched**.
The exact real reply total length (≥ 6 proven) is likewise still UNKNOWN, as is whether the
app verifies an inbound D4 checksum.

**Effect on the 2.22.0901 live outcome recorded above (§B):** the app previously continued
to `0xD6` with no reply and tolerated it. A reply now exists, but because its payload
values are chosen rather than device-authentic, §B's conclusion stands for 2.22.0901 until
a run with `--d4-gamepad-mode 0x06` (or a captured real frame) is done. No live run was
performed in this pass (static + peripheral edits only); no real hardware was touched.

