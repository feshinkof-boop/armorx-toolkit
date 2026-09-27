# Virtual ARMOR-X Pro peripheral — status report

Phase 6 of armorx-lab. A software-only Bumble peripheral that reproduces the
ARMOR-X Pro GATT surface and implements **only evidence-backed** command
handling from the canonical MYGT 4.0.8 research. No physical radio is used.

* Directory: `/home/salamanka/armorx-lab/ble/virtual-armorx/`
* Interpreter / Bumble: `/home/salamanka/armorx-lab/ble/bumble/venv`
  (Python 3.14.4; bumble **0.0.218** currently installed; code was also verified
  green on bumble 0.0.235)
* Selftest result: **client 14/14 checks, selftest 12/12 checks, exit 0**
* Unit tests: **18 passed**

---

## 1. Transport and safety

The peripheral is a complete virtual device built from **two Bumble `Controller`
instances on one in-process `LocalLink`**:

* `C_PERIPH` — the peripheral's own radio, wired to the peripheral Host through
  a local UNIX-socket HCI pipe (`--local-transport`).
* `C_PEER` — a peer radio on the same link whose HCI is exposed over
  `tcp-server:127.0.0.1:<port>`. A **second Bumble process** attaches with
  `tcp-client` and acts as the central.

No `usb`, `pyusb`, `hci-socket`, `vhci` or `/dev/hci*` transport is opened. The
host's `hci0`/`hci1`, the USB radios, BlueZ state, `rfkill` and the Wi-Fi
interface `wlp3s0` are never touched. No `rfkill`, driver-unbind or `hciconfig`
command is run.

## 2. GATT surface (all UUIDs from `ble-architecture.md`)

| role | UUID | properties |
|---|---|---|
| vendor service | `00000000-0000-1000-8000-00805f9b34fb` | — |
| FFE1 write channel | `0000ffe1-0000-1000-8000-00805f9b34fb` | WRITE, WRITE_WITHOUT_RESPONSE |
| FFE2 notify channel | `0000ffe2-0000-1000-8000-00805f9b34fb` | READ, NOTIFY |
| 180A device information | `0000180a-…` | — |
| 2A24 model number | `00002a24-…` | READ (`ZJ-XT`) |
| 2A26 firmware revision | `00002a26-…` | READ (`41`) |
| 180F battery | `0000180f-…` | — |
| 2A19 battery level | `00002a19-…` | READ, NOTIFY |

Advertising name is the exact scan prefix **`ARMOR-X Pro_` + suffix**
(`ble-architecture.md`:106 `_DeviceBottomSheetState::startScanBySdk` device list
`"Rainbow2_"`, `"CHOCO_"`, `"ARMOR-X Pro_"`); default suffix `0001`.

`2A24 = ZJ-XT` is evidence-backed: `unresolved.md`:60-63 (the mark string is not
in the app bundle and therefore comes from the device / GATT 2A24 / advertisement)
and `docs/research-status-2026-09-25.md`:97 (the live capture read `ZJ-XT` via the
standard Model Number String). `2A26 = "41"` reflects the live-captured
`firmwareVersion = 41` (`docs/usb-protocol.md`:171). Both are overridable flags.

## 3. Frame handling

Parsing covers both families and validates the checksum
`(sum of all preceding bytes) & 0xFF` (`config-144-reconstruction.md` §6
`getCheckSum`; `docs/android-protocol.md`; `d8-macro.md` §3.4):

* **A5 short** — `A5 | total_len | opcode | data… | sum8`
* **A4 fragment** — `A4 | total_len | opcode | fragment_index | data… | sum8`
  (`docs/android-protocol.md` "A4 fragmentation"; `docs/usb-protocol.md`:142)
* **D8 terminator** — `A4 0A D8 <nfrags+1> <sum8>` (`d8-macro.md` §3.3), the
  constant `0x0A` length byte is special-cased.

Every inbound frame is logged (raw + JSONL) with its parsed opcode and a
checksum pass/fail flag; checksum/length failures are logged as `frame_error`
and dropped.

## 4. Opcodes with implemented (evidence-backed) replies — 5

| opcode | semantics | request (byte-exact) | reply emitted | research evidence |
|---|---|---|---|---|
| `0x0B` | getZKMVer | `A5 04 0B B4` | `A5 05 0B <VV> <sum>` (default VV=`0x30`) | `research/apk-2.23.0609/ef-dataflow.md`:20 (`A5 05 0B VV CC`); `docs/usb-protocol.md`:162 parser accepts `A5 05 0B VV CC`; live `A5 05 0B 30 E5` in `docs/android-frame-builder-reconciliation.md`:49 |
| `0xEF` | getDeviceUUID | `A5 0C EF 00×8 A0` | `A5 0C EF <8 uuid bytes> <sum>` (bytes 3..10 → devUuid) | `ef-dataflow.md`:39 `IN: A5 0C EF <8 device-uuid bytes> <checksum> [PROVEN_LIVE]`; `ble-architecture.md`:85 "bytes 3..10 of the reply → 16-char hex devUuid" |
| `0xD6` | getDeviceConfig | `A5 04 D6 7F` | ten `A4/D6` fragments (idx 1..10; 15+15+…+9 bytes) → 144-byte image, big-endian CRC-16/MODBUS over bytes 2..143 | `docs/android-protocol.md`:126-143 (D6 = ten A4 fragments → 144 bytes); `config-144-reconstruction.md` §6/§7; `default-configs/README.md` (image + CRC rule) |
| `0xD7` | writeDeviceConfig | ten `A4/D7` fragments + 144 bytes | `A5 05 D7 00 81` | `docs/android-protocol.md`:153-159; `docs/usb-protocol.md`:166 |
| `0x0E` | writeDevice (post-write) | `A5 05 0E 00 B8` | frames echoed verbatim | `docs/android-protocol.md`:230 "The device echoes the 5-byte frame verbatim" |

The D6 image is the byte-exact 144-byte ARMOR-X Pro default
(`default-configs/default_001_device___len_144.json`, `define.dart:512`), with the
placeholder `0x0000` CRC field replaced by the recomputed value **`0x848A`**
(verified equal to `default-configs/README.md`'s own-CRC column). The
peripheral recomputes the CRC on load and re-validates any D7 image it receives.

## 5. UNKNOWN-by-design opcodes — 28 (all logged, **no bytes sent**)

Every opcode not in the table above is logged as `command_unknown` with
`reply_bytes_sent: 0`. Nothing is invented. The full inventory of known opcodes
is in `command-index.md`/`.json`; the ones explicitly documented here:

| opcode | semantics | why no reply | evidence |
|---|---|---|---|
| `0xE4` | getMTU | request byte-exact, device reply never captured | `command-index.md` 0xE4; `live-test-plan.md`:10 |
| `0xE2` | readFirmware | decoder *shape* known (min 16 bytes, opcode `E2`, checksum at byte 15, 9-byte marker at bytes 6..14) but marker CONTENT is UNKNOWN | `docs/research-status-2026-09-25.md`:116-121; `unresolved.md` §8 |
| `0x04` | getBattery | no byte-exact device reply; app reads battery via GATT `2A19` | `command-index.md` 0x04; `ble-architecture.md` |
| `0xD8` | macro protocol | fragments + terminator are accepted and reassembled, terminator logged as `macro_terminator`; device reply UNKNOWN | `d8-macro.md` |
| remaining 24: `05 06 1A 1B 25 26 70 73 A6 A9 AB D2 D3 D4 DA DD E1 F5 F6 F7 F8 FC FD FF` | mixed (`command-index.md`) | no device reply recovered in the research | `command-index.md` |

## 6. Files created

```
/home/salamanka/armorx-lab/ble/virtual-armorx/
├── armorx_protocol.py          frame parse/build, checksum, CRC-16/MODBUS,
│                               config loader, opcode + reply evidence table
├── virtual_armorx.py           the peripheral process (GATT, advertising, logging)
├── armorx_central_client.py    Bumble central driving the first-contact sequence
├── selftest.py                 two-process end-to-end selftest
├── README.md                   start/serve/verify instructions
├── tests/test_protocol.py      18 pytest pins for framing/CRC/reply table
└── logs/                       per-session <id>.bin, <id>.hex, <id>.jsonl
/home/salamanka/armorx-lab/results/final/virtual-armorx-status.md  (this file)
```

## 7. How to prove the loop works (commands + observed output)

Unit tests:

```
$ /home/salamanka/armorx-lab/ble/bumble/venv/bin/python -m pytest -q
18 passed in 0.02s
```

End-to-end selftest (two Bumble processes over a local TCP transport):

```
$ cd /home/salamanka/armorx-lab/ble/virtual-armorx
$ /home/salamanka/armorx-lab/ble/bumble/venv/bin/python selftest.py
=== selftest: logs in .../logs/selftest-..., port <port> ===
  [peripheral] [virtual-armorx] advertising as 'ARMOR-X Pro_0001'
               (F0:0A:A5:00:00:01) | peer HCI on tcp-server:127.0.0.1:<port>
[PASS] peripheral_started
[scan] found 'ARMOR-X Pro_0001' at F0:0A:A5:00:00:01
[PASS] scan_found_prefix
[PASS] connected: att_mtu=247
[PASS] vendor_service_present: services=[00000000-…, 1800, 1801, 180a, 180f]
[PASS] ffe1_ffe2_present
[PASS] read_2A24_model: b'ZJ-XT'
[PASS] read_2A26_firmware: b'41'
[PASS] read_2A19_battery: b'd'
[PASS] subscribe_ffe2
[PASS] reply_0B_version: got a5050b30e5
[PASS] reply_EF_device_uuid: got a50cef0001020304050607bc
[PASS] reply_D6_config_read: fragments=10 bytes=144 crc_valid=True
[PASS] reply_D7_config_write_ack: got a505d70081
[PASS] unknown_E4_MTU_no_bytes: got None (expected none)
[PASS] unknown_E2_readFirmware_no_bytes: got None (expected none)
=== client summary: 14/14 checks passed ===
[PASS] central_client_exit_0: returncode=0
[PASS] peripheral_jsonl_written: 42 events
[PASS] logged_connect: 1 connect events
[PASS] logged_gatt_writes: 15 inbound frames
[PASS] logged_config_read_10_fragments
[PASS] logged_d7_config_write
[PASS] logged_unknown_e4_e2: UNKNOWN opcodes logged: ['0xE2', '0xE4']
[PASS] unknown_sent_no_bytes: every UNKNOWN command logged with reply_bytes_sent=0
[PASS] checksum_pass_rate: all parsed inbound frames had a valid checksum
[PASS] raw_capture_bin: 522 bytes
[PASS] raw_capture_hex: 3198 bytes
=== selftest summary: 12/12 checks passed ===
```

Manual run (documented in README.md):

```
# terminal 1 — peripheral (tcp-server side)
python virtual_armorx.py --transport tcp-server:127.0.0.1:9510 \
    --local-transport /tmp/armorx_periph_hci.sock --session-id manual
# terminal 2 — central (tcp-client side, second Bumble process)
python armorx_central_client.py --transport tcp-client:127.0.0.1:9510
```

## 8. Logging produced

Per session, under `logs/`:

* `<session>.bin` — raw capture, record = `<dir><u16 BE length><payload>` with
  `dir ∈ {<, >}` (host→peripheral / peripheral→host).
* `<session>.hex` — timestamped hex dump of the same records.
* `<session>.jsonl` — structured JSONL: `session_start`, `advertising_started`,
  `connect`, `disconnect`, `mtu`, `subscription`, `gatt_read`, `frame_in`,
  `reply_out`, `config_write`, `macro_terminator`, `command_unknown`,
  `frame_error`, `session_end`. Each record carries `app_version` (default
  `4.0.8`, the app version under test), raw bytes, parsed opcode and
  checksum pass/fail.

## 9. Blockers / caveats

* **None blocking.** The peripheral runs and the loop is proven.
* `2A26` / `2A19` values (`41` / `100`) and the EF UUID value are *device
  identity data*, not research constants — the research fixes the `EF` reply
  *layout* (bytes 3..10 = UUID) but not the value, so all three are flag-overridable
  and documented as identity, not protocol semantics.
* The Bumble venv is shared with sibling lab tasks and was recreated twice during
  this task (3.14-only, then bumble 0.0.218). The virtual-armorx code only uses
  stable Bumble public API and was verified green on both 0.0.235 and 0.0.218.
* The `A4` fragment index byte is taken from the live-captured layout
  (`docs/android-protocol.md`, `docs/usb-protocol.md`); `d8-macro.md` §3.3
  describes the D8 data fragments without an index — both are accepted on the
  receive path and the index form is used for D6/D7.
