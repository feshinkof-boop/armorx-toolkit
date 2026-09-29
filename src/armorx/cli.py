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
from . import capture as capture_mod
from . import device as device_mod
from . import exchange as exchange_mod
from . import gip as gip_mod
from . import macro as macro_mod
from . import protocol as protocol_mod


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
                    "proven_live"
                    if i == 12
                    else "proven_old_app"
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
            note = " (Guide/Xbox/Mode; proven live)"
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



def _toolkit_version() -> str:
    return __version__


# ---------------------------------------------------------------------------
# device (read-only discovery and diagnostics)
# ---------------------------------------------------------------------------

def cmd_device_list(args: argparse.Namespace) -> int:
    candidates = device_mod.scan_devices(known_only=args.known_only)
    payload = {
        "count": len(candidates),
        "supported_count": sum(1 for c in candidates if c.identity.known),
        "devices": [c.to_dict() for c in candidates],
        "note": ("No supported device found is a normal result; discovery is read-only "
                 "and never sends anything to a device."),
    }
    _write_json(args.output, payload)
    if not args.output and not candidates:
        print("no USB devices discovered", file=sys.stderr)
    return 0


def cmd_device_inspect(args: argparse.Namespace) -> int:
    candidates = device_mod.scan_devices(known_only=False)
    target = device_mod.find_by_path(candidates, args.device)
    if target is None:
        _write_json(args.output, {
            "found": False,
            "selected": args.device,
            "candidates": [c.identity.to_dict() for c in candidates],
            "message": "the requested device is not present; this is a normal result",
        })
        return 0
    _write_json(args.output, {"found": True, **device_mod.explain_device(target)})
    return 0


def cmd_device_doctor(args: argparse.Namespace) -> int:
    if args.bundle:
        bundle = device_mod.diagnostics_bundle(include_hostname=args.include_hostname,
                                               toolkit_version=_toolkit_version())
        Path(args.bundle).write_text(
            device_mod.render_bundle_text(bundle) if args.text
            else json.dumps(bundle, indent=2, sort_keys=True)
        )
        _write_json(args.output, {"bundle": args.bundle, "text": bool(args.text),
                                  "privacy": bundle["privacy"]})
        return 0
    result = device_mod.doctor()
    _write_json(args.output, result)
    return 0


# ---------------------------------------------------------------------------
# protocol (offline framing)
# ---------------------------------------------------------------------------

def cmd_protocol_decode(args: argparse.Namespace) -> int:
    data = protocol_mod.decode_hex(args.hex)
    frames = protocol_mod.split_stream(data) if args.stream else [data]
    parsed = [protocol_mod.parse_frame(f) for f in frames]
    report = protocol_mod.DecodeReport(frames=parsed)
    _write_json(args.output, report.to_dict())
    return 0


def cmd_protocol_build(args: argparse.Namespace) -> int:
    try:
        opcode = int(args.opcode, 16)
    except ValueError:
        print(f"error: opcode must be hex, got {args.opcode!r}", file=sys.stderr)
        return 2
    payload = protocol_mod.decode_hex(args.payload) if args.payload else b""
    try:
        if args.fragment is not None:
            frame = protocol_mod.build_a4(opcode, args.fragment, payload)
        else:
            frame = protocol_mod.build_a5(opcode, payload)
    except protocol_mod.FrameError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.output:
        Path(args.output).write_bytes(frame)
        _write_json(None, {"wrote": args.output, "bytes": len(frame),
                           "hex": " ".join(f"{b:02X}" for b in frame)})
    else:
        print(" ".join(f"{b:02X}" for b in frame))
    return 0


def cmd_protocol_opcodes(args: argparse.Namespace) -> int:
    rows = [protocol_mod.describe_opcode(code) for code in sorted(protocol_mod.OPCODES)]
    _write_json(args.output, {"count": len(rows), "opcodes": rows,
                              "note": "opcodes absent from this table are unknown, not silent"})
    return 0


def cmd_protocol_describe(args: argparse.Namespace) -> int:
    image = protocol_mod.decode_hex(args.image)
    frames = protocol_mod.fragment_config_image(int(args.opcode, 16), image)
    payload = {
        "opcode": args.opcode,
        "image_bytes": len(image),
        "fragment_count": len(frames),
        "fragments": [" ".join(f"{b:02X}" for b in f) for f in frames],
        "note": "offline construction only; nothing is transmitted",
    }
    _write_json(args.output, payload)
    return 0


# ---------------------------------------------------------------------------
# gip (offline Xbox GIP input parsing)
# ---------------------------------------------------------------------------

def cmd_gip_decode(args: argparse.Namespace) -> int:
    data = protocol_mod.decode_hex(args.hex)
    try:
        report = gip_mod.parse_gip_input(data, strict=not args.lax)
    except gip_mod.GipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _write_json(args.output, report.to_dict())
    return 0


def cmd_gip_forms(_: argparse.Namespace) -> int:
    _write_json(None, {
        "forms": device_mod.GIP_REPORT_FORMS,
        "fields": {
            "sequence": "byte 2",
            "A": "byte 4 bit 0x10",
            "M1": "byte 4 bit 0x20",
            "M2": "byte 5 bit 0x40",
            "LT": "bytes 6-7, 16-bit little-endian",
            "RT": "bytes 8-9, 16-bit little-endian",
            "left_stick": "bytes 10-13",
            "right_stick": "bytes 14-17",
            "counters": "bytes 40-47 in the 48-byte form; semantics unknown",
        },
        "note": "every offset above was established by differential analysis of live captures",
    })
    return 0


def _add_device_commands(groups) -> None:
    device = groups.add_parser("device", help="read-only device discovery and diagnostics")
    device_sub = device.add_subparsers(dest="device_command", required=True)

    p = device_sub.add_parser("list", help="scan the USB bus without touching any device")
    p.add_argument("--known-only", action="store_true", help="only recognized identities")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_device_list)

    p = device_sub.add_parser("inspect", help="explain one device in detail")
    p.add_argument("device", help="sysfs path, usb path (e.g. 1-7) or vid:pid")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_device_inspect)

    p = device_sub.add_parser("doctor", help="diagnose whether this machine can talk to hardware")
    p.add_argument("--compact", action="store_true")
    p.add_argument("--bundle", help="write a sanitised diagnostics bundle to this file")
    p.add_argument("--include-hostname", action="store_true",
                   help="include the machine hostname in the bundle (off by default)")
    p.add_argument("--text", action="store_true", help="print the bundle as text instead of JSON")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_device_doctor)


def _add_protocol_commands(groups) -> None:
    protocol = groups.add_parser("protocol", help="offline ARMORX frame tools")
    protocol_sub = protocol.add_subparsers(dest="protocol_command", required=True)

    p = protocol_sub.add_parser("decode", help="decode one frame or a whole byte stream")
    p.add_argument("hex", help="hex bytes, e.g. 'A5 04 0B B4'")
    p.add_argument("--stream", action="store_true", help="treat the input as pipelined frames")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_protocol_decode)

    p = protocol_sub.add_parser("build", help="build a frame offline (nothing is transmitted)")
    p.add_argument("--opcode", required=True, help="hex opcode, e.g. D6")
    p.add_argument("--payload", help="hex payload")
    p.add_argument("--fragment", type=int, help="build an A4 fragment with this index")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_protocol_build)

    p = protocol_sub.add_parser("opcodes", help="list recovered opcodes and their evidence")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_protocol_opcodes)

    p = protocol_sub.add_parser("describe-image", help="fragment a 144-byte config image (offline)")
    p.add_argument("--opcode", default="D7", help="hex opcode, default D7")
    p.add_argument("--image", required=True, help="144 hex bytes")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_protocol_describe)


def _add_gip_commands(groups) -> None:
    gip = groups.add_parser("gip", help="offline Xbox GIP input parsing")
    gip_sub = gip.add_subparsers(dest="gip_command", required=True)

    p = gip_sub.add_parser("decode", help="decode one type-0x20 input report")
    p.add_argument("hex", help="hex bytes of the report")
    p.add_argument("--lax", action="store_true", help="do not enforce observed prefix bytes")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_gip_decode)

    p = gip_sub.add_parser("forms", help="show the observed report forms and field offsets")
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_gip_forms)



# ---------------------------------------------------------------------------
# capture (offline inspection of saved captures)
# ---------------------------------------------------------------------------

def cmd_capture_inspect(args: argparse.Namespace) -> int:
    try:
        report = capture_mod.inspect_file(args.file, usb_limit=args.limit)
    except capture_mod.CaptureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except protocol_mod.FrameError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.summary:
        print(capture_mod.summarise(report))
        hint = capture_mod.external_reader_hint()
        if hint:
            print(hint)
        return 0
    _write_json(args.output, report.to_dict())
    return 0


def cmd_capture_formats(_: argparse.Namespace) -> int:
    _write_json(None, {
        "supported": {
            "hex-text": "whitespace, comma or colon separated hex bytes",
            "raw": "binary bytes containing A5/A4 frames",
            "usbmon-pcap": f"classic pcap with link type {capture_mod.DLT_USB_LINUX} or {capture_mod.DLT_USB_LINUX_MMAPPED}",
        },
        "unsupported": {"pcapng": "save as classic pcap, e.g. tshark -F pcap"},
        "note": "no packet-processing dependency is required for any supported format",
    })
    return 0


# ---------------------------------------------------------------------------
# exchange (shareable local envelope)
# ---------------------------------------------------------------------------

def cmd_exchange_export(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(Path(args.payload).read_text())
    except FileNotFoundError:
        print(f"error: {args.payload} does not exist", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {args.payload} is not valid JSON: {exc.msg}", file=sys.stderr)
        return 2
    device_meta = json.loads(args.device) if args.device else {}
    firmware_meta = json.loads(args.firmware) if args.firmware else {}
    provenance = json.loads(args.provenance) if args.provenance else {}
    try:
        env = exchange_mod.create(args.content_type, payload, device=device_meta,
                                  firmware=firmware_meta, provenance=provenance,
                                  created=args.created, notes=args.notes,
                                  toolkit_format=_toolkit_version())
    except exchange_mod.ExchangeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.output and args.output.endswith(".json"):
        exchange_mod.save(env, args.output)
        _write_json(None, {"wrote": args.output, "content_id": env.content_id})
    else:
        print(env.to_json(indent=None if args.compact else 2), end="")
    return 0


def cmd_exchange_inspect(args: argparse.Namespace) -> int:
    try:
        env = exchange_mod.load(args.file)
    except exchange_mod.ExchangeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _write_json(args.output, {"envelope": env.to_dict(), **exchange_mod.verify(env)})
    return 0


def cmd_exchange_verify(args: argparse.Namespace) -> int:
    try:
        env = exchange_mod.load(args.file)
    except exchange_mod.ExchangeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = exchange_mod.verify(env)
    _write_json(args.output, result)
    return 0 if result["content_id_ok"] else 3


def cmd_exchange_schema(_: argparse.Namespace) -> int:
    _write_json(None, {
        "schema": exchange_mod.SCHEMA,
        "content_types": list(exchange_mod.CONTENT_TYPES),
        "evidence_levels": list(exchange_mod.EVIDENCE_LEVELS),
        "max_payload_bytes": exchange_mod.MAX_PAYLOAD_BYTES,
        "fields": {
            "schema": "envelope schema identifier",
            "content_type": "config or macro",
            "toolkit_format": "toolkit version that wrote the envelope",
            "device": "model and identity metadata, never serial numbers",
            "firmware": "firmware metadata where known",
            "provenance": "where the payload came from and its evidence level",
            "created": "optional UTC timestamp",
            "payload": "the configuration or macro content",
            "content_id": "sha256 over the canonical body, excluding this field",
        },
        "note": "the content id is stable across whitespace and key ordering",
    })
    return 0


def _add_capture_commands(groups) -> None:
    capture = groups.add_parser("capture", help="inspect saved captures offline")
    sub = capture.add_subparsers(dest="capture_command", required=True)
    p = sub.add_parser("inspect", help="inspect a hex dump, raw stream or usbmon pcap")
    p.add_argument("file")
    p.add_argument("--limit", type=int, help="stop after this many usbmon records")
    p.add_argument("--summary", action="store_true", help="one line summary instead of JSON")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_capture_inspect)
    p = sub.add_parser("formats", help="list the supported capture formats")
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_capture_formats)


def _add_exchange_commands(groups) -> None:
    exchange = groups.add_parser("exchange", help="shareable configuration and macro envelopes")
    sub = exchange.add_subparsers(dest="exchange_command", required=True)
    p = sub.add_parser("export", help="wrap a JSON payload in an envelope")
    p.add_argument("payload", help="path to a JSON file to wrap")
    p.add_argument("--content-type", required=True, choices=list(exchange_mod.CONTENT_TYPES))
    p.add_argument("--device", help="JSON object with device metadata")
    p.add_argument("--firmware", help="JSON object with firmware metadata")
    p.add_argument("--provenance", help="JSON object describing where the payload came from")
    p.add_argument("--created", help="ISO-8601 UTC timestamp; omit to leave it unset")
    p.add_argument("--notes")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output", help="write to this .json file instead of stdout")
    p.set_defaults(func=cmd_exchange_export)
    p = sub.add_parser("inspect", help="show an envelope with its verification result")
    p.add_argument("file")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_exchange_inspect)
    p = sub.add_parser("verify", help="verify the content id of an envelope")
    p.add_argument("file")
    p.add_argument("--compact", action="store_true")
    p.add_argument("-o", "--output")
    p.set_defaults(func=cmd_exchange_verify)
    p = sub.add_parser("schema", help="describe the envelope schema")
    p.add_argument("--compact", action="store_true")
    p.set_defaults(func=cmd_exchange_schema)

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

    _add_device_commands(groups)
    _add_protocol_commands(groups)
    _add_gip_commands(groups)
    _add_capture_commands(groups)
    _add_exchange_commands(groups)

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
