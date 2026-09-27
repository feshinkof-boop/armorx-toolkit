# Tooling reconnaissance (§22–§25)

Full inventory: `tools/TOOL_INVENTORY.md` (human) and `tools/tool-inventory.json` (machine).

## Summary of this pass

- **Policy honoured:** mature upstream tooling was searched for first; custom code was written
  only where no upstream parser/tool exists (the vendor `A5`/`A4` framing, the 144-byte config
  decode, the operator click-ack dialog contract).
- **Used and exercised on real hardware:** Bumble (capture path A), `bluetoothctl`/`btmgmt`
  (adapter resolution), `btmon` (btsnoop capture path B).
- **Installed this pass:** `bleak` 3.0.2 in `.venv-bumble` (independent BlueZ/D-Bus GATT path)
  and PySide6 6.11.2 in `.venv-operator-ui` (operator dialog). Both in isolated venvs; system
  Python untouched.
- **Present, staged for the USB/HID track:** `tshark`, `dumpcap`, `usbhid-dump`, `7z`, `unzip`,
  `xxd`, `objdump`, `readelf`, `strings`, `jq`.
- **Already vendored:** `tools/vendor/AC632Nuke` @ `6f179f2b0ae5b3d6bc9885ec4f3d7cb82d0bdee9`,
  `tools/vendor/jl-misctools` @ `0a5b12db0ef38f3042acffbe2452730a37fd2405` — inspected, not executed.
- **Deliberately excluded:** `kagaimiq/jl-uboot-tool` (write/erase, unverified loader for this
  family) and, for now, `hid-tools` / `hidapitester` / `binwalk` / `ghidra` — each deferred to the
  bench step that actually needs it, since installing them early would not have saved work.

## Environment lesson worth keeping

`bluetoothd` was found wedged (a `bluetoothctl show` hung >90 s while holding the lab controller);
`systemctl restart bluetooth` cleared it. That is a mgmt-layer restart: it does **not** touch the
Wi-Fi side of the composite adapter. Primary network was re-verified PASS afterwards.
