# ArmorX unified CLI

ArmorX Toolkit installs one command:

```text
armorx
```

It groups the existing functionality under three namespaces:

```text
armorx config ...
armorx macro ...
armorx community ...
```

The original scripts under `tools/` are intentionally kept for backward compatibility and direct use.

## Installation

From a clone:

```bash
git clone https://github.com/feshinkof-boop/armorx-toolkit.git
cd armorx-toolkit
python -m pip install -e .
```

Verify:

```bash
armorx --version
armorx --help
```

## Config commands

Decode:

```bash
armorx config decode config.json
```

Validate CRC and length:

```bash
armorx config validate config.json
```

List known key IDs:

```bash
armorx config keys
```

Map one or more buttons:

```bash
armorx config map config.json M1=A M2=B -o mapped.json
```

Patch other known fields:

```bash
armorx config patch config.json \
  --set triggerMode=1 \
  --set stickLeftDZCenter=5 \
  -o patched.json
```

Create a config from a known-good template:

```bash
armorx config create \
  --template config.json \
  --set 'mapKey[M1]=A' \
  -o new.json
```

Print compact `configJson`:

```bash
armorx config configjson config.json --canonical
```

## Macro commands

Build:

```bash
armorx macro build combo.txt -o macro.json
```

Inspect:

```bash
armorx macro inspect macro.json
```

Validate:

```bash
armorx macro validate macro.json
```

Show macro key IDs:

```bash
armorx macro keys
```

## Community commands

Preview the known config-list request shape:

```bash
armorx community list \
  --phone-uuid YOUR_PHONE_ID \
  --dev-uuid YOUR_CONTROLLER_ID \
  --dry-run
```

Use another compatible service base URL:

```bash
armorx community --base-url http://HOST:PORT list \
  --phone-uuid YOUR_PHONE_ID \
  --dev-uuid YOUR_CONTROLLER_ID
```

Import one known share code:

```bash
armorx community import-code SHARECODE --dry-run
```

The community commands remain intentionally narrow and do not brute-force share codes or enumerate identifiers.

## Legacy scripts

These remain available and are not removed:

```text
tools/armorx_config.py
tools/armorx_macro.py
tools/armorx_community.py
```

The package modules live under:

```text
src/armorx/
```

## v0.3.0 offline groups

```text
armorx device list [--known-only]
armorx device inspect <sysfs-path | usb-path | vid:pid>
armorx device doctor

armorx protocol decode "<hex>" [--stream]
armorx protocol build --opcode <hex> [--payload <hex>] [--fragment <n>]
armorx protocol opcodes
armorx protocol describe-image --image "<144 hex bytes>" [--opcode D7]

armorx gip decode "<hex>"
armorx gip forms
```

None of these commands talk to a device. `armorx device doctor` is expected to
exit 0 on a machine with no hardware and to say so.

## Complete command surface after the offline work

```text
armorx config    decode | validate | keys | map | patch | create | configjson
armorx macro     build | validate | inspect | keys
armorx community list | import-code
armorx device    list | inspect | doctor
armorx protocol  decode | build | opcodes | describe-image
armorx gip       decode | forms
armorx capture   inspect | formats
armorx exchange  export | inspect | verify | schema
```

Behaviour contract for the new groups:

| situation | result |
| --- | --- |
| `--help` on any group | exit 0, no hardware touched |
| no device present | `armorx device list` and `device doctor` exit 0 and say so |
| malformed input | exit 2, one-line message on stderr, never a traceback |
| content-id mismatch | `armorx exchange verify` exits 3 |
| unknown opcode | reported as unknown, never guessed |

Diagnostics bundle:

```bash
armorx device doctor --bundle diagnostics.json          # JSON, sanitised
armorx device doctor --bundle diagnostics.txt --text     # human readable
armorx device doctor --bundle d.json --include-hostname  # opt in to the hostname
```

The bundle omits usernames, home paths, the hostname, USB serial numbers and
MAC/Bluetooth addresses unless explicitly requested, and the omission list is
recorded inside the bundle itself.

## `armorx live` (development branch)

| command | purpose |
| --- | --- |
| `armorx live scan` | scan locally for ARMOR-X advertisements; conservative classification with a `candidate_reason` |
| `armorx live info --address A` | read standard identity characteristics (model, firmware, battery) |
| `armorx live read-config --address A` | read the 144-byte configuration over the proven `D6` read |
| `armorx live backup --address A -o f.json` | read and save the configuration before any future write |
| `armorx live plan base.json target.json` | compare two saved images offline (no device) |
| `armorx live apply TARGET --address A` | write a configuration: automatic backup, decoded diff, confirmation, `D7`, one `0E`, two `D6` verifications |
| `armorx live rollback PREFIX --address A` | write back the exact bytes of a saved backup |
| `armorx live validate-write-gate --address A` | supervised byte-identical no-op write (experimental) |
| `armorx live validate-reversible-m1 --address A` | supervised reversible M1 -> A experiment (experimental) |

These commands exist only on the development branch and are not part of a
released version. See `docs/v0.4.0-live-apply.md` for the write path and its
safety model. There is no raw opcode or payload console, and none is planned.
