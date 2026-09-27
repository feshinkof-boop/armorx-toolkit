# Tool reconnaissance inventory

Project rule: **search for a maintained existing tool before writing custom code.** Custom code
should fill real gaps, not re-implement mature tooling. Machine-readable copy:
`tools/tool-inventory.json` (each entry carries upstream repo, license, install method,
privileges, hardware, usefulness, installed/tested flags, risk and notes).

## Installed and already exercised in this pass

| tool | upstream | why it matters here | evidence of use |
|---|---|---|---|
| `bluetoothctl` / `btmgmt` | bluez/bluez | resolve the lab adapter dynamically instead of hardcoding `hci1` | adapter identity checks in `automation/radio/*` |
| `btmon` | bluez/bluez | canonical btsnoop HCI evidence (capture path B) | ran against the earlier session into `$SES/hci` |
| `bumble` (google/bumble) | github.com/google/bumble | pure-Python BLE stack for the direct HCI-socket sessions (capture path A) | every live read/write in this project |
| `tshark` / `dumpcap` | wireshark/wireshark | decode btsnoop and (planned) usbmon captures | present, offline decode not yet exercised |
| `usbhid-dump` | DIGImend/usbhid-dump | raw HID report descriptors without a driver | staged for the receiver/F20 step |
| `7z`, `unzip`, `xxd`, `strings`, `objdump`, `readelf` | distro | firmware/updater triage | used for static searches |
| `AC632Nuke`, `jl-misctools` | tpunix/AC632Nuke, kagaimiq/jl-misctools | **vendored already** under `tools/vendor/` — JieLi format/ROM research | not yet run; AC632Nuke carries write/erase paths and is therefore read-only-only by policy |
| `bleak` (hbldh/bleak, 3.0.2) | github.com/hbldh/bleak | independent GATT path through bluetoothd/D-Bus for cross-validation | installed this pass; first dump found no advertisement (unit asleep) |

## Present but not yet needed

`bluetoothctl`, `jq`, `sudo -n` (NOPASSWD available), `spectacle` (screenshot proof).

## Deliberately NOT installed yet (and why)

| tool | would be used for | why deferred |
|---|---|---|
| `hid-tools` (hid-recorder/decode/parse/feature/replay) | HID report-descriptor decode + record/replay | highest-value addition **for the Linux-driver/F20 track**, pointless until a HID device is on the bench |
| `hidapitester` (todbot) | independent HID read/write probe | cross-check partner for our own HID code; same trigger as above |
| `binwalk` | firmware image triage (JLFS/uboot.boot hunt) | no firmware image exists yet; `7z`/`xxd`/`strings` cover the current searches |
| `ghidra` / `rizin` / `radare2` | static binary analysis | no binary is under analysis; `objdump`+`strings` suffice for now |
| `pyusb` / `libusb` bindings | future userspace driver | can detach kernel drivers — only introduced when the USB step starts |
| `kaitai-struct-compiler` | declarative `.ksy` for the config layout | the 144-byte layout is already reproducible in `parse-baseline.py`; a `.ksy` is a later refactor |
| `kagaimiq/jl-uboot-tool` | JieLi uboot read/write/erase | **excluded by project rule**: it can erase/program, and BD19/AC632N support is historically UNKNOWN — an unverified loader must never be pointed at the device |

## Installation policy honoured

- distro packages preferred; nothing installed with `curl … | sudo sh`
- no installer executed as root without reading its instructions
- Python bindings live in isolated venvs (`.venv-bumble`, `.venv-operator-ui`), never in the system Python
- no major system component upgraded or downgraded

## Custom code kept, and the gap it fills

| custom artefact | why no upstream tool fits |
|---|---|
| `automation/scripts/armorx_lab/{transport,frames}.py`, `ble/virtual-armorx/armorx_protocol.py` | the `A5`/`A4` framing, `mapKeys` layout and checksum scheme are vendor-specific; no upstream parser exists |
| `automation/scripts/parse-baseline.py` | decodes *this* 144-byte config image reproducibly from raw bytes |
| `automation/scripts/verify-key-id-map.py` | claim-verified key map built from real captures (no hand-typed vectors) |
| `automation/scripts/button-capture-harness.py` | operator-synchronised capture that **wraps** the proven harness instead of re-implementing BLE |
| `automation/operator_action_gui.py`, `automation/request_physical_action.py` | one-shot click-acknowledged operator dialogs (no upstream equivalent for this contract) |

## Unresolved environment note

`bluetoothd` was found wedged (a `bluetoothctl show` hung for >90 s while holding the lab
controller). It was restarted with `systemctl restart bluetooth` — a mgmt-layer restart that
does not touch the Wi-Fi side of the combo adapter. Primary network re-verified **PASS**
afterwards. Worth remembering when a BlueZ-based tool appears to hang.
