# Virtual ARMOR-X Pro BLE peripheral

A software-only Bumble peripheral that reproduces the ARMOR-X Pro GATT surface
and the **evidence-backed** subset of the MYGT 4.0.8 A5/A4 command protocol.
It is used to exercise client implementations (the Android app, test harnesses)
without any physical controller and **without touching the host's Bluetooth
adapter**.

Everything here is grounded in the canonical 4.0.8 research:

* `/home/salamanka/armorx-re/mygt408/research/mygt-4.0.8/` (choices of frame,
  UUID, config image, CRC),
* `/home/salamanka/armorx-re/repo/docs/android-protocol.md`,
  `.../docs/usb-protocol.md` (live-captured replies),
* `/home/salamanka/armorx-re/repo/research/apk-2.23.0609/ef-dataflow.md`
  (live-captured `0B`/`EF` reply shapes).

A mirror under `/home/salamanka/armorx-lab/baselines/imported-research/` is used
automatically when present.

## Files

| file | purpose |
|---|---|
| `armorx_protocol.py` | frame parsing/building, checksum, CRC-16/MODBUS, config image loader, opcode + reply evidence table |
| `virtual_armorx.py` | the peripheral process (GATT server, advertising, frame handling, logging) |
| `armorx_central_client.py` | Bumble central that drives the first-contact sequence and verifies every reply |
| `selftest.py` | starts the peripheral as one process and the client as a second, over a local TCP transport |
| `tests/test_protocol.py` | pytest pins for the byte-exact frames, CRC and reply table |
| `logs/` | per-session raw captures and structured logs |

## Install

Bumble lives in a dedicated venv (shared with the rest of the lab's BLE work):

```bash
/home/salamanka/armorx-lab/ble/bumble/venv/bin/python -m pip install bumble pytest
```

Observed in this environment:

* `/usr/bin/python3` (3.14) had no `ensurepip` when this task started, so the
  venv was first created with a 3.11 interpreter
  (`/home/salamanka/.local/bin/python3.11`), then a sibling lab task replaced
  the venv with one built by the system **Python 3.14.4**. Bumble 0.0.235
  installed cleanly under 3.11 and 3.14 alike; the venv currently holds
  **bumble 0.0.218** (also installed by the sibling task).
* The virtual-armorx code has been run green against both **0.0.235** and
  **0.0.218**; it only uses stable Bumble public API (`Device.with_hci`,
  `Controller`, `LocalLink`, `open_transport`, `Peer`, `AdvertisingData`).
* `pytest` 9.x is installed for `tests/`.

## Start the peripheral

```bash
/home/salamanka/armorx-lab/ble/bumble/venv/bin/python \
  /home/salamanka/armorx-lab/ble/virtual-armorx/virtual_armorx.py \
  --transport tcp-server:127.0.0.1:9510 \
  --local-transport /tmp/armorx_periph_hci.sock \
  --session-id my-session
```

It advertises as `ARMOR-X Pro_<suffix>` (default `ARMOR-X Pro_0001`) and exposes:

* vendor service `00000000-0000-1000-8000-00805f9b34fb`
  * `FFE1` — write / write-without-response
  * `FFE2` — read / notify
* `180A` device information — `2A24` model (`ZJ-XT`), `2A26` firmware revision (`41`)
* `180F` battery — `2A19` battery level

Useful flags: `--name-suffix`, `--device-uuid <16 hex>`, `--zkm-version`,
`--model-number`, `--firmware-revision`, `--battery-level`, `--config-file`,
`--address`, `--app-version`, `--log-dir`, `--session-id`. See
`virtual_armorx.py --help`.

## Connect a central (second Bumble process)

```bash
/home/salamanka/armorx-lab/ble/bumble/venv/bin/python \
  /home/salamanka/armorx-lab/ble/virtual-armorx/armorx_central_client.py \
  --transport tcp-client:127.0.0.1:9510
```

Or, run the whole loop as an automated selftest:

```bash
cd /home/salamanka/armorx-lab/ble/virtual-armorx
/home/salamanka/armorx-lab/ble/bumble/venv/bin/python selftest.py
```

and the unit tests:

```bash
/home/salamanka/armorx-lab/ble/bumble/venv/bin/python -m pytest -q
```

## Transport: how the physical adapter is kept out of the loop

The peripheral is a complete virtual device made of **two Bumble `Controller`
instances on one in-process `LocalLink`**:

```
        peripheral process                          client process
  ┌───────────────────────────────┐          ┌───────────────────────────┐
  │  Host (GATT server, advertiser)│          │  Host (central)           │
  │        ▲  unix-socket HCI pipe │          │        ▲ tcp-client       │
  │  C_PERIPH ── LocalLink ── C_PEER ── tcp-server ──────────┘             │
  └───────────────────────────────┘          └───────────────────────────┘
```

* The peripheral's own radio (`C_PERIPH`) is wired to its Host through a local
  UNIX-socket HCI pipe (`--local-transport`).
* A peer radio (`C_PEER`) on the **same link** exposes HCI over
  `tcp-server:127.0.0.1:<port>`; the second Bumble process attaches to it with
  `tcp-client`.
* No `usb`, `hci-socket`, `vhci` or `/dev/hci*` transport is used, so `hci0`/
  `hci1`, the USB radios and BlueZ state are never opened or modified. No
  `rfkill`, no driver unbind, no `hciconfig`. The primary Wi-Fi (`wlp3s0`) is
  untouched.

## Logging

Each peripheral session writes three files under `logs/` (or `--log-dir`):

* `<session>.bin` — raw capture. Record = `<dir><u16 BE length><payload>`, where
  `dir` is `<` (host → peripheral) or `>` (peripheral → host). Concatenated
  records can be replayed/parsed mechanically.
* `<session>.hex` — human-readable hex dump of the same records, with UTC
  timestamps, direction and byte offset.
* `<session>.jsonl` — structured events, one JSON object per line:
  `session_start`, `advertising_started`, `connect`, `disconnect`, `mtu`,
  `subscription`, `gatt_read`, `frame_in`, `reply_out`, `config_write`,
  `macro_terminator`, `command_unknown`, `frame_error`, `session_end`. Every
  record carries `app_version` (the app version under test, default `4.0.8`),
  the raw bytes, the parsed opcode and a checksum pass/fail flag.

The central client writes a matching `<session>.jsonl` (its session id is
`selftest-client` in the selftest).

## Evidence-backed handling vs UNKNOWN

Implemented replies (see `results/final/virtual-armorx-status.md` for citations):

| request | reply | status |
|---|---|---|
| `A5 04 0B B4` | `A5 05 0B <VV> <sum>` | EVIDENCE-BACKED |
| `A5 0C EF 00×8 A0` | `A5 0C EF <8 uuid bytes> <sum>` | EVIDENCE-BACKED |
| `A5 04 D6 7F` | ten `A4/D6` fragments → 144-byte config, valid CRC-16/MODBUS | EVIDENCE-BACKED |
| `A4…D7` + 144-byte image | `A5 05 D7 00 81` | EVIDENCE-BACKED |
| `A5 05 0E 00 B8` | echoed verbatim | EVIDENCE-BACKED |

Every other opcode (including `E4` MTU query, `E2` firmware read and `04`
battery) is logged as `command_unknown` with `reply_bytes_sent: 0` — **no bytes
are invented**. `D8` macro writes are accepted/reassembled and the terminator is
logged; the device reply is UNKNOWN and none is sent.
