<!--
Keywords: BIGBIG WON, BIGBIGWON, ARMORX Pro, ArmorX Pro, Xbox, Xbox controller,
controller, gamepad, controller remapping, key mapping, controller macro, M1 M2 M3 M4
-->

<div align="center">

# BIGBIG WON ARMORX Pro — Xbox Controller Toolkit

**Open-source configuration, key-mapping, macro, and community tools for the BIGBIG WON ARMORX Pro controller ecosystem.**

Build, inspect, remap, validate, and research **ARMORX Pro** configurations and macros for **Xbox controllers**.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-2ea44f)
![Status](https://img.shields.io/badge/status-active%20research-f59e0b)
![Platform](https://img.shields.io/badge/platform-Xbox%20controller-107C10?logo=xbox&logoColor=white)
![Tests](https://github.com/feshinkof-boop/armorx-toolkit/actions/workflows/tests.yml/badge.svg)

</div>

---

## Overview

**ArmorX Toolkit** is a community-driven interoperability project for the **BIGBIG WON ARMORX Pro**, an accessory for **Xbox controllers**.

The project focuses on:

- decoding and generating ARMORX Pro controller configuration data;
- building and validating controller macros;
- documenting **Xbox controller key mapping** and rear-button remapping;
- documenting config structure, CRC, timing behavior, and unknown fields;
- reproducing read-oriented community/config exchange behavior;
- providing a clean base for future GUI and automation tools.

The goal is to give controller enthusiasts, developers, and researchers a solid foundation for building better tools around **BIGBIG WON**, **ARMORX Pro**, **Xbox**, and controller customization.

> **Unofficial project.** Not affiliated with or endorsed by BIGBIG WON, MOJHON, Microsoft, or Xbox.

## Features

| Area | Current support |
|---|---|
| Config format | 144-byte decoder / builder |
| Integrity | CRC16 validation + regeneration |
| Key mapping | Named Xbox / ARMORX Pro IDs |
| Rear buttons | M1-M4 remapping |
| Macros | Timed steps, chords, cycle modes |
| Config safety | Unknown/reserved bytes preserved when patching |
| Community | Read-oriented config-list and share-code client |
| Research | Evidence levels: PROVEN / STRONG EVIDENCE / UNKNOWN |
| Quality | Pytest suite + GitHub Actions |

## ARMORX Pro / Xbox key mapping

The following IDs are directly supported by the recovered ARMORX Pro mapping model.

| ID | ARMORX Pro / Xbox control | Aliases |
|---:|---|---|
| 0 | **A** | South |
| 1 | **B** | East |
| 2 | **Empty / Clear** | None |
| 3 | **X** | North |
| 4 | **Y** | West |
| 6 | **LB** | Left Bumper |
| 7 | **RB** | Right Bumper |
| 8 | **LT** | Left Trigger |
| 9 | **RT** | Right Trigger |
| 10 | **View** | Select |
| 11 | **Menu** | Start |
| 13 | **L3** | Left Stick Click |
| 14 | **R3** | Right Stick Click |
| 16 | **D-pad Up** | Up |
| 17 | **D-pad Down** | Down |
| 18 | **D-pad Left** | Left |
| 19 | **D-pad Right** | Right |
| 23 | **M1** | Rear button |
| 24 | **M2** | Rear button |
| 25 | **M3** | Rear button |
| 26 | **M4** | Rear button |

The serialized mapping direction is:

```text
mapKeys[source_button_id] = target_button_id
```

Example:

```text
mapKeys[23] = 0
M1 -> A
```

Some IDs remain intentionally unresolved until directly verified. See [docs/keymapping.md](docs/keymapping.md).

## Config format

A controller config is **144 bytes**:

```text
0..1      CRC16
2..3      length (0x0090 / 144)
4..111    controller parameter block
112..143  mapKeys[32]
```

Known fields include trigger settings, left/right stick deadzones, response curves, motion/sensor settings, turbo settings, and button mapping.

Full reference: [docs/config-format.md](docs/config-format.md)

## Macro format

Macros currently support:

- M1-M4 as trigger buttons;
- tap and long-press activation;
- cycle modes;
- multi-button chords;
- per-step hold duration;
- per-step interval;
- up to 16 steps in the current V41-era model.

Example:

```text
@name Example Combo
@trigger M1
@mode tap
@repeat 200

A       80   50
X      100   60
B+RT   120   70
Y       90  100
```

Full reference: [docs/macro-format.md](docs/macro-format.md)

## Quick start

Clone and install the package:

```bash
git clone https://github.com/feshinkof-boop/armorx-toolkit.git
cd armorx-toolkit
python -m pip install -e .
```

This installs one unified command:

```bash
armorx --help
```

### Inspect a config

```bash
armorx config decode config.json
```

### Validate CRC and length

```bash
armorx config validate config.json
```

### Remap M1 to A and M2 to B

```bash
armorx config map config.json M1=A M2=B -o patched_config.json
```

### Show known key IDs

```bash
armorx config keys
```

### Build and inspect a macro

```bash
armorx macro build examples/example_macro.txt -o macro.json
armorx macro inspect macro.json
```

### Community/config exchange client

Preview a config-list request without sending it:

```bash
armorx community list \
  --phone-uuid YOUR_PHONE_ID \
  --dev-uuid YOUR_CONTROLLER_ID \
  --dry-run
```

See [docs/cli.md](docs/cli.md) for the full command reference and [docs/community-api.md](docs/community-api.md) for the current community scope.

### Legacy scripts remain available

The original standalone scripts are intentionally preserved:

```text
tools/armorx_config.py
tools/armorx_macro.py
tools/armorx_community.py
```

They are not being removed; the new `armorx` command is the preferred interface.

### Run tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Evidence standard

Protocol claims in this repository are classified as:

- **PROVEN** — directly reproduced or independently confirmed.
- **STRONG EVIDENCE** — multiple signals agree, but one final confirmation is missing.
- **UNKNOWN** — deliberately unresolved.

Unknown bytes and IDs are **not guessed**.

## Repository layout

```text
armorx-toolkit/
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── CITATION.cff
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── armorx/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── macro.py
│       └── community.py
├── docs/
│   ├── cli.md
│   ├── config-format.md
│   ├── keymapping.md
│   ├── macro-format.md
│   └── community-api.md
├── examples/
│   └── example_macro.txt
├── tools/                 # preserved standalone scripts
│   ├── armorx_config.py
│   ├── armorx_macro.py
│   └── armorx_community.py
├── tests/
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_macro.py
│   └── test_community.py
└── .github/
    ├── ISSUE_TEMPLATE/
    ├── PULL_REQUEST_TEMPLATE.md
    └── workflows/
```

## Community/config exchange client

Preview a config-list request without sending it:

```bash
armorx community list \
  --phone-uuid YOUR_PHONE_ID \
  --dev-uuid YOUR_CONTROLLER_ID \
  --dry-run
```

See [docs/cli.md](docs/cli.md) for the full command reference and [docs/community-api.md](docs/community-api.md) for the current community scope.

### Legacy scripts remain available

The original standalone scripts are intentionally preserved:

```text
tools/armorx_config.py
tools/armorx_macro.py
tools/armorx_community.py
```

They are not being removed; the new `armorx` command is the preferred interface.

### Run tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## Evidence standard

Protocol claims in this repository are classified as:

- **PROVEN** — directly reproduced or independently confirmed.
- **STRONG EVIDENCE** — multiple signals agree, but one final confirmation is missing.
- **UNKNOWN** — deliberately unresolved.

Unknown bytes and IDs are **not guessed**.

## Repository layout

```text
armorx-toolkit/
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── CITATION.cff
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── LICENSE
├── docs/
│   ├── config-format.md
│   ├── keymapping.md
│   ├── macro-format.md
│   └── community-api.md
├── examples/
│   └── example_macro.txt
├── tools/
│   ├── armorx_config.py
│   ├── armorx_macro.py
│   └── armorx_community.py
├── tests/
│   ├── test_config.py
│   ├── test_macro.py
│   └── test_community.py
└── .github/
    ├── ISSUE_TEMPLATE/
    ├── PULL_REQUEST_TEMPLATE.md
    └── workflows/
```

## Community

Contributions are welcome, especially:

- controlled config diffs;
- confirmation of unknown key IDs;
- additional firmware behavior;
- anonymized captures from user-owned hardware;
- **Xbox controller** mapping validation;
- GUI ideas;
- test fixtures;
- documentation improvements.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Roadmap](ROADMAP.md).

## Search / discovery keywords

**BIGBIG WON** · **BIGBIGWON** · **ARMORX Pro** · **ArmorX Pro** · **Xbox** · **Xbox controller** · **controller** · gamepad · controller remapping · controller macro · key mapping · M1 M2 M3 M4 · controller configuration

## License

MIT — see [LICENSE](LICENSE).
