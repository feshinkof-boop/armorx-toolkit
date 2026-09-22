<div align="center">

# ArmorX Toolkit

**Open-source tools and protocol documentation for the BIGBIG WON ARMORX Pro controller ecosystem.**

Build, inspect, remap, and research **ARMORX Pro** configurations and macros for **Xbox** controllers.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/status-active%20research-orange)
![Platform](https://img.shields.io/badge/platform-Xbox%20%7C%20ARMORX%20Pro-black)

</div>

---

## Overview

**ArmorX Toolkit** is a community-driven interoperability project for the **BIGBIG WON ARMORX Pro**, an accessory for **Xbox** controllers.

The project focuses on three things:

- decoding and generating ARMORX Pro controller configuration data;
- building and validating controller macros;
- documenting key mapping, config structure, timing behavior, and community/config exchange formats.

The goal is to give controller enthusiasts, developers, and researchers a clean foundation for building better tools around **BIGBIG WON**, **ARMORX Pro**, **Xbox**, and controller customization.

> This is an independent community project. It is not affiliated with or endorsed by BIGBIG WON, MOJHON, Microsoft, or Xbox.

## Features

- **144-byte config decoder and builder**
- **CRC16 validation/recalculation**
- **Xbox / ARMORX Pro key mapping**
- **M1-M4 remapping support**
- **Macro builder with timing and chords**
- **Macro execution modes**
- **Documented unknown/reserved fields**
- **Community/config API research notes**
- **Tests and reproducible examples**

## ARMORX Pro key mapping

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

Some IDs remain intentionally undocumented until they are verified. See [docs/keymapping.md](docs/keymapping.md).

## Config format

A controller config is **144 bytes**:

```text
0..1      CRC16
2..3      length (0x0090 / 144)
4..111    controller parameter block
112..143  mapKeys[32]
```

Known fields include trigger settings, left/right stick deadzones, response curves, motion/sensor settings, turbo settings, and button mapping.

See [docs/config-format.md](docs/config-format.md).

## Macro format

Macros support:

- M1-M4 as trigger buttons
- tap and long-press activation
- cycle modes
- multi-button chords
- per-step hold duration
- per-step interval
- up to 16 steps on firmware V41-era behavior

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

See [docs/macro-format.md](docs/macro-format.md).

## Quick start

Clone the repository:

```bash
git clone https://github.com/feshinkof-boop/armorx-toolkit.git
cd armorx-toolkit
```

Inspect a config:

```bash
python tools/armorx_config.py decode config.json
```

Patch a mapping:

```bash
python tools/armorx_config.py patch config.json \
  --map M1=A \
  --map M2=B \
  -o patched_config.json
```

Build a macro:

```bash
python tools/armorx_macro.py build examples/example_macro.txt -o macro.json
```

Run tests:

```bash
python -m pytest -q
```

## Evidence standard

Protocol claims in this repository are classified as:

- **PROVEN** — directly reproduced or verified by multiple consistent observations.
- **STRONG EVIDENCE** — highly consistent with protocol behavior but still awaiting one independent confirmation.
- **UNKNOWN** — deliberately left unresolved.

Unknown bytes and IDs are not guessed.

## Repository layout

```text
armorx-toolkit/
├── README.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── SECURITY.md
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
│   └── armorx_macro.py
├── tests/
│   ├── test_config.py
│   └── test_macro.py
└── .github/
    ├── ISSUE_TEMPLATE/
    └── workflows/
```

## Community

Contributions are welcome, especially:

- controlled config diffs;
- confirmation of unknown key IDs;
- additional firmware behavior;
- controller captures from user-owned hardware;
- GUI ideas;
- test fixtures;
- documentation improvements.

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Search terms

BIGBIG WON · BIGBIGWON · ARMORX Pro · ArmorX Pro · Xbox · Xbox controller · controller remapping · controller macro · gamepad · key mapping · M1 M2 M3 M4 · controller configuration

## License

MIT — see [LICENSE](LICENSE).
