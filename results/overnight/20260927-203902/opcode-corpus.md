# ArmorX opcode corpus

Built /home/salamanka/armorx-lab/results/overnight/20260927-203902 from every capture in the project. **615 ATT records** decoded; **260 protocol frames** in 14 opcode groups; **0 checksum failures**.

## Classification rule (matters: most ATT traffic is not protocol traffic)

| category | rule |
|---|---|
| `protocol_frame` | an `A5`/`A4`/`AB` frame written to FFE1 (`0x0075`) or notified from FFE2 (`0x0077`) |
| `gatt_cccd_write` | a 2-byte descriptor write (notify enable) - not a protocol frame |
| `gatt_attribute_data` | attribute values fetched by GATT (device name, connection parameters, manufacturer data) |
| `gatt_control_or_empty` | ATT operations carrying no value |

## Protocol frames observed

| opcode | direction | ATT op | count | lengths | checksum ok/bad | example |
|---|---|---|---|---|---|---|
| `0x02` | DEVICE->HOST | Handle Value Notification | 155 | ['18'] | 155/0 | `a5120200000001fd6500b6fc4f0158000076` |
| `0xD2` | DEVICE->HOST | Handle Value Notification | 35 | ['5'] | 35/0 | `a505d2017d` |
| `0xD2` | HOST->DEVICE | Write Command | 31 | ['5'] | 31/0 | `a505d2017d` |
| `0x0B` | HOST->DEVICE | Write Command | 10 | ['4'] | 10/0 | `a5040bb4` |
| `0x0B` | DEVICE->HOST | Handle Value Notification | 10 | ['5'] | 10/0 | `a5050b30e5` |
| `0xD6` | DEVICE->HOST | Handle Value Notification | 10 | ['14', '20'] | 10/0 | `a414d6012c40009033ff000000000000000000bd` |
| `0xD2` | HOST->DEVICE | Write Request | 2 | ['5'] | 2/0 | `a505d2017d` |
| `0xEF` | HOST->DEVICE | Write Command | 1 | ['12'] | 1/0 | `a50cef0000000000000000a0` |
| `0xEF` | DEVICE->HOST | Handle Value Notification | 1 | ['12'] | 1/0 | `a50cefbb921542f21f55802a` |
| `0xE2` | HOST->DEVICE | Write Command | 1 | ['4'] | 1/0 | `a504e28b` |
| `0xE2` | DEVICE->HOST | Handle Value Notification | 1 | ['16'] | 1/0 | `a510e22741025a4a2d5854000000007e` |
| `0xD4` | HOST->DEVICE | Write Command | 1 | ['4'] | 1/0 | `a504d47d` |
| `0xD4` | DEVICE->HOST | Handle Value Notification | 1 | ['7'] | 1/0 | `a507d411010092` |
| `0xD6` | HOST->DEVICE | Write Command | 1 | ['4'] | 1/0 | `a504d67f` |

## Everything else (kept, but not protocol frames)

| category | ATT op | direction | count |
|---|---|---|---|
| gatt_control_or_empty | Read Request | HOST->DEVICE | 73 |
| gatt_control_or_empty | Read Response | DEVICE->HOST | 65 |
| gatt_control_or_empty | Write Response | DEVICE->HOST | 40 |
| gatt_control_or_empty | Error Response | DEVICE->HOST | 37 |
| gatt_control_or_empty | Read By Group Type Response | DEVICE->HOST | 31 |
| gatt_control_or_empty | Write Request | HOST->DEVICE | 22 |
| gatt_control_or_empty | Read By Group Type Request | HOST->DEVICE | 21 |
| gatt_control_or_empty | Read By Type Response | DEVICE->HOST | 17 |
| gatt_cccd_write | Write Request | HOST->DEVICE | 16 |
| gatt_control_or_empty | Read By Type Request | HOST->DEVICE | 11 |
| gatt_attribute_data | Read Response | DEVICE->HOST | 8 |
| gatt_control_or_empty | MTU Request | HOST->DEVICE | 5 |

## Source coverage (records contributed)

| capture | records |
|---|---|
| `armorx-lab/results/experiments/official-vs-harness-session-20260927-190741/official-session/transport-attempt-20260927-193109/official-session-live/raw/android-official-session.cfa` | 216 |
| `armorx-lab/results/experiments/d2-live-differential-20260927-184643/raw/btmon.txt` | 151 |
| `armorx-lab/results/experiments/d2-live-differential-20260927-184643/raw/btmon.btsnoop` | 123 |
| `armorx-lab/results/experiments/official-vs-harness-session-20260927-190741/harness-session/raw/btmon-live.txt` | 44 |
| `armorx-lab/results/experiments/official-vs-harness-session-20260927-190741/harness-session/raw/btmon.txt` | 44 |
| `armorx-lab/results/experiments/official-vs-harness-session-20260927-190741/harness-session/raw/btmon.btsnoop` | 37 |

## Honest notes

- Five `PCAPdroid_*.pcap` files contain **no BLE traffic at all** (app/server network captures) and contribute 0 records. Preserved for Part 24 work, not for this corpus.
- Two captures decode to 0 ATT records (`bluez-pass.btsnoop` and a harness btsnoop copy) - recorded, not hidden.
- **Parser correction (this pass):** the first attempt used a greedy `btmon` text parser that attached the next `Data:` buffer to the previous ATT record, producing phantom 'opcodes' from the device name (`ARMOR-X Pro_11`) and connection parameters, plus 7 false checksum failures. The parser now requires strict Handle-then-Data adjacency, and the classification separates GATT attribute values from protocol frames. Result: 0 checksum failures across 260 protocol frames.
- This is a *coverage* view: an opcode missing here means 'not captured yet', NOT 'not supported'.
