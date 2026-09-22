#!/usr/bin/env python3
"""Unified ArmorX Toolkit command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from . import community as community_mod
from . import config as config_mod
from . import macro as macro_mod


def _write_json(path: str | None, obj, *, compact: bool = False) -> None:
    text = json.dumps(
        obj,
        ensure_ascii=False,
        indent=None if compact else 2,
        separators=(",", ":") if compact else None,
    )
    if path:
        Path(path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def cmd_config_decode(args: argparse.Namespace) -> int:
    buf = config_mod.load_config(args.input)
    _write_json(args.output, config_mod.decode(buf))
    return 0


def cmd_config_validate(args: argparse.Namespace) -> int:
    buf = config_mod.load_config(args.input)
    _write_json(None, config_mod.validate(buf, require_144=False))
    return 0


def cmd_config_keys(_: argparse.Namespace) -> int:
    rows = []
    for i in range(32):
        rows.append(
            {
                "id": i,
                "name": config_mod.CANONICAL_KEY_NAMES.get(i),
                "status": (
                    "proven_old_app"
                    if i in config_mod.CANONICAL_KEY_NAMES
                    else "unresolved_or_unexposed"
                ),
            }
        )
    _write_json(None, rows)
    return 0


def cmd_config_map(args: argparse.Namespace) -> int:
    buf = config_mod.load_config(args.input)
    if len(buf) != config_mod.CONFIG_LEN:
        raise ValueError(
            f"expected {config_mod.CONFIG_LEN}-byte template, got {len(buf)}"
        )

    for mapping in args.mappings:
        if "=" not in mapping:
            raise ValueError(
                f"mapping must be SOURCE=TARGET, for example M1=A: {mapping}"
            )
        source, target = mapping.split("=", 1)
        source = source.strip()
        target = target.strip()
        config_mod.apply_assignment(buf, f"mapKey[{source}]={target}")

    if args.keep_crc:
        config_mod.put_u16_be(buf, 2, config_mod.CONFIG_LEN)
    else:
        buf = config_mod.canonicalize(buf)

    _write_json(args.output, buf, compact=args.compact)
    return 0


def cmd_config_patch(args: argparse.Namespace) -> int:
    buf = config_mod.load_config(args.input)
    if len(buf) != config_mod.CONFIG_LEN:
        raise ValueError(
            f"expected {config_mod.CONFIG_LEN}-byte template, got {len(buf)}"
        )
    for assignment in args.sets:
        config_mod.apply_assignment(buf, assignment)
    if args.keep_crc:
        config_mod.put_u16_be(buf, 2, config_mod.CONFIG_LEN)
    else:
        buf = config_mod.canonicalize(buf)
    _write_json(args.output, buf, compact=args.compact)
    return 0


def cmd_config_create(args: argparse.Namespace) -> int:
    buf = (
        config_mod.load_config(args.template)
        if args.template
        else config_mod.fresh()
    )
    for assignment in args.sets:
        config_mod.apply_assignment(buf, assignment)
    buf = config_mod.canonicalize(buf)
    _write_json(args.output, buf, compact=args.compact)
    return 0


def cmd_config_configjson(args: argparse.Namespace) -> int:
    buf = config_mod.load_config(args.input)
    if args.canonical:
        buf = config_mod.canonicalize(buf)
    print(json.dumps(buf, separators=(",", ":")))
    return 0


# ---------------------------------------------------------------------------
# macro
# ---------------------------------------------------------------------------

def cmd_macro_build(args: argparse.Namespace) -> int:
    meta, steps = macro_mod.parse_dsl(args.dsl)
    if args.name is not None:
        meta["name"] = args.name
    if args.trigger is not None:
        meta["trigger"] = args.trigger
    if args.mode is not None:
        meta["mode"] = args.mode
    if args.repeat_time is not None:
        meta["repeat_time"] = args.repeat_time
    if args.active:
        meta["active"] = True

    obj = macro_mod.build_macro_object(
        name=meta["name"],
        trigger=meta["trigger"],
        mode=meta["mode"],
        repeat_time=meta["repeat_time"],
        active=meta["active"],
        steps=steps,
    )

    if args.phone_uuid is not None or args.dev_uuid is not None:
        if not (args.phone_uuid and args.dev_uuid):
            raise ValueError(
                "--phone-uuid and --dev-uuid must be supplied together"
            )
        obj = macro_mod.build_add_macro_payload(
            phone_uuid=args.phone_uuid,
            dev_uuid=args.dev_uuid,
            macro_obj=obj,
        )

    _write_json(args.output, obj)
    return 0


def cmd_macro_validate(args: argparse.Namespace) -> int:
    obj = json.loads(Path(args.file).read_text(encoding="utf-8"))
    errors = macro_mod.validate_macro_object(obj)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    rows = macro_mod.decode_macro_json(obj["macroJson"])
    print(
        "OK: "
        f"{len(rows)} step(s), "
        f"trigger={obj['runKeyName']}({obj['runKey']}), "
        f"mode={macro_mod.MODE_NAMES[obj['isRepeat']]}, "
        f"repeatTime={obj['repeatTime']} ms"
    )
    return 0


def cmd_macro_inspect(args: argparse.Namespace) -> int:
    obj = json.loads(Path(args.file).read_text(encoding="utf-8"))
    rows = macro_mod.decode_macro_json(obj["macroJson"])

    print(f"name: {obj.get('macroName', '')}")
    print(f"trigger: {obj.get('runKeyName')} ({obj.get('runKey')})")
    print(
        "mode: "
        f"{macro_mod.MODE_NAMES.get(obj.get('isRepeat'), 'UNKNOWN')} "
        f"({obj.get('isRepeat')})"
    )
    print(f"repeatTime: {obj.get('repeatTime')} ms")
    print(f"inUse: {obj.get('inUse')}")
    print(f"steps: {len(rows)}")

    for i, row in enumerate(rows, 1):
        names = row["keyNameListDecoded"]
        print(
            f"  {i:02d}. {'+'.join(names)}  "
            f"hold={row['duration']} ms  "
            f"interval={row['interval']} ms  "
            f"ids={row['mapListDecoded']}"
        )
    return 0


def cmd_macro_keys(_: argparse.Namespace) -> int:
    for key_id in sorted(macro_mod.CANONICAL_NAMES):
        name = macro_mod.CANONICAL_NAMES[key_id]
        if name in {"M1", "M2", "M3", "M4"}:
            note = " (macro trigger; not normally an action key)"
        elif 34 <= key_id <= 49:
            note = " (joystick pseudo-key; strong evidence mapping)"
        elif key_id == 12:
            note = " (Guide/Mode; strongly supported)"
        else:
            note = ""
        print(f"{key_id:2d}  {name}{note}")
    return 0


# ---------------------------------------------------------------------------
# community
# ---------------------------------------------------------------------------

def cmd_community_list(args: argparse.Namespace) -> int:
    payload = community_mod.build_list_payload(
        args.phone_uuid,
        args.dev_uuid,
        page_num=args.page_num,
        config_type=args.config_type,
    )
    if args.dry_run:
        _write_json(args.output, payload)
        return 0

    result = community_mod.post_json(
        args.base_url,
        "/dev/queryConfigList",
        payload,
        timeout=args.timeout,
    )
    _write_json(args.output, result)
    return 0


def cmd_community_import(args: argparse.Namespace) -> int:
    payload = community_mod.build_import_payload(
        args.share_code,
        phone_uuid=args.phone_uuid,
        dev_uuid=args.dev_uuid,
    )
    if args.dry_run:
        _write_json(args.output, payload)
        return 0

    result = community_mod.post_json(
        args.base_url,
        "/dev/importShareConfig",
        payload,
        timeout=args.timeout,
    )
    _write_json(args.output, result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="armorx",
        description=(
            "BIGBIG WON ARMORX Pro toolkit for Xbox controller configs, "
            "key mapping, macros, and community/config exchange."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    groups = parser.add_subparsers(dest="group", required=True)

    # config
    config = groups.add_parser(
        "config",
        help="decode, validate, create, and remap 144-byte controller configs",
    )
    config_sub = config.add_subparsers(dest="config_command", required=True)

    p = config_sub.add_parser("decode", help="decode a config into named fields")
    p.add_argument("input")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_config_decode)

    p = config_sub.add_parser("validate", help="validate config length and CRC")
    p.add_argument("input")
    p.set_defaults(func=cmd_config_validate)

    p = config_sub.add_parser("keys", help="show known mapKeys IDs")
    p.set_defaults(func=cmd_config_keys)

    p = config_sub.add_parser(
        "map",
        help="remap buttons using SOURCE=TARGET expressions",
    )
    p.add_argument("input")
    p.add_argument(
        "mappings",
        nargs="+",
        metavar="SOURCE=TARGET",
        help="for example M1=A or M2=DPAD_UP",
    )
    p.add_argument("-o", "--output")
    p.add_argument(
        "--keep-crc",
        action="store_true",
        help="preserve stored CRC instead of regenerating it",
    )
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_config_map)

    p = config_sub.add_parser(
        "patch",
        help="patch any known config field while preserving unknown bytes",
    )
    p.add_argument("input")
    p.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
    )
    p.add_argument("-o", "--output")
    p.add_argument("--keep-crc", action="store_true")
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_config_patch)

    p = config_sub.add_parser(
        "create",
        help="create a config; a known-good --template is recommended",
    )
    p.add_argument("--template")
    p.add_argument(
        "--set",
        dest="sets",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
    )
    p.add_argument("-o", "--output")
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_config_create)

    p = config_sub.add_parser(
        "configjson",
        help="print the literal compact configJson array",
    )
    p.add_argument("input")
    p.add_argument("--canonical", action="store_true")
    p.set_defaults(func=cmd_config_configjson)

    # macro
    macro = groups.add_parser(
        "macro",
        help="build, inspect, validate, and list macro key IDs",
    )
    macro_sub = macro.add_subparsers(dest="macro_command", required=True)

    p = macro_sub.add_parser("build", help="build macro JSON from a DSL file")
    p.add_argument("dsl")
    p.add_argument("-o", "--output")
    p.add_argument("--name")
    p.add_argument("--trigger", choices=list(macro_mod.RUN_KEYS))
    p.add_argument(
        "--mode",
        choices=["long_press", "tap", "long_press_cycle", "tap_cycle"],
    )
    p.add_argument("--repeat-time", type=int)
    p.add_argument("--active", action="store_true")
    p.add_argument("--phone-uuid")
    p.add_argument("--dev-uuid")
    p.set_defaults(func=cmd_macro_build)

    p = macro_sub.add_parser("validate", help="validate generated macro JSON")
    p.add_argument("file")
    p.set_defaults(func=cmd_macro_validate)

    p = macro_sub.add_parser("inspect", help="human-readable macro decode")
    p.add_argument("file")
    p.set_defaults(func=cmd_macro_inspect)

    p = macro_sub.add_parser("keys", help="show known macro key IDs")
    p.set_defaults(func=cmd_macro_keys)

    # community
    community = groups.add_parser(
        "community",
        help="read-oriented community/config exchange commands",
    )
    community.add_argument(
        "--base-url",
        default=community_mod.DEFAULT_BASE_URL,
    )
    community.add_argument("--timeout", type=float, default=10.0)
    community_sub = community.add_subparsers(
        dest="community_command",
        required=True,
    )

    p = community_sub.add_parser(
        "list",
        help="query configurations using the reproduced client request shape",
    )
    p.add_argument("--phone-uuid", required=True)
    p.add_argument("--dev-uuid", required=True)
    p.add_argument("--page-num", type=int, default=1)
    p.add_argument("--config-type", type=int, default=1)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_community_list)

    p = community_sub.add_parser(
        "import-code",
        help="import one known share code",
    )
    p.add_argument("share_code")
    p.add_argument("--phone-uuid")
    p.add_argument("--dev-uuid")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_community_import)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("aborted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
