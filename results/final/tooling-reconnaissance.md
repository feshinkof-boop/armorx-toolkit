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

---

## D2 static pass — tools actually used (and deliberately not used)

| Tool | Version | Repository | Commit/tag | Purpose | Input | Output | Why chosen | Custom code avoided |
|---|---|---|---|---|---|---|---|---|
| Blutter | as vendored for each build | github.com/worawit/blutter | trees already generated | Dart AOT symbol recovery (function names, addresses, cross-file call annotations) | `libapp.so` per build | `out/asm/**.dart`, `objs.txt`, `pp.txt` | the AOT image already carries Dart-level names; nothing lower level is needed for a protocol question | no custom disassembler |
| GNU grep / sed / coreutils | distro | GNU project | distro version | locating constants, call sites, UTF-8 UI strings (按键测试) across the asm trees | `asm/**.dart` | matching lines with addresses | fastest path to a symbol in a 40k-line tree | no indexer written |
| Python 3.14 (stdlib only) | 3.14.7 | python.org | — | aggregating per-build findings into the JSON contracts, cross-version matrix and evidence index | agent JSON + verification greps | `results/reconciliation/*.json/.md` | the artifacts are derived data; a bespoke parser was not warranted | no bespoke parser |
| Graphviz `dot` | distro | graphviz.org | distro version | rendering the call graph | `d2-callgraph.dot` | `d2-callgraph.svg` | already installed; `.dot` alone would have sufficed | no custom renderer |
| pytest | distro | pytest.org | distro version | D2 contract regression tests | `tests/test_d2_static_contract.py` | 12 tests | existing project test runner | none |

**Deliberately NOT used, and why:**

- **Ghidra / rizin / radare2 / Cutter** — not used. The D2 question is a Dart-level protocol
  question and Blutter already provides names, addresses and callers; a decompiler pass would have
  added cost without adding evidence.
- **binwalk / Kaitai / strings** — not used in this pass.
- **Ghost/derived parsers** — no new custom parser was written for the static work; the only new
  code is the small contract implementation inside the regression tests.

Per-task file/commit/command provenance for every anchor is in
`results/reconciliation/d2-evidence-index.json`, and each artifact states its own source paths.
