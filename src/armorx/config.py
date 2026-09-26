#!/usr/bin/env python3
"""ArmorX Pro 144-byte configuration decoder/builder.

Derived from the old Flutter/Dart AOT implementation (GamepadSet30 / GeneralGamepadSet).
The 144-byte format is:
  0..1   CRC16 (MODBUS bit algorithm), stored big-endian
  2..3   length, big-endian (144 == 0x0090)
  4..111 108-byte parameter block
  112..143 mapKeys[32]

Unknown/reserved bytes are preserved when patching a template.
"""
from __future__ import annotations
import argparse, json, pathlib, sys
from typing import Any, Dict, List, Tuple

CONFIG_LEN = 144
PARAM_START = 4
MAPKEYS_START = 112

# Captured /dev/shareConfig traffic exposes a 38-byte structured field named
# res2 that mirrors raw config bytes 74..111 exactly. It overlaps known turbo
# fields and therefore must not be treated as an ordinary reserved-only range.
SHARE_RES2_START = 74
SHARE_RES2_END = 112

# ArmorX key IDs recovered from the old app AOT remap UI plus controlled
# live BLE remap tests. ID 12 (Guide/Mode) is now live-proven. ID 15 remains
# provisional because the autonomous run recorded a conflicting chooser value
# plus an operator note of "screenshot". Values 5/15/20-22/27-31 therefore
# remain unnamed in the stable CLI until their semantics are cleanly confirmed.
MAP_KEY_CODES = {
    "A": 0, "B": 1, "EMPTY": 2, "NONE": 2, "CLEAR": 2,
    "X": 3, "Y": 4,
    "LB": 6, "RB": 7, "LT": 8, "RT": 9,
    "VIEW": 10, "SELECT": 10,
    "MENU": 11, "START": 11,
    "GUIDE": 12, "MODE": 12, "XBOX": 12, "HOME": 12,
    "L3": 13, "LS": 13, "LS_CLICK": 13,
    "R3": 14, "RS": 14, "RS_CLICK": 14,
    "DPAD_UP": 16, "UP": 16,
    "DPAD_DOWN": 17, "DOWN": 17,
    "DPAD_LEFT": 18, "LEFT": 18,
    "DPAD_RIGHT": 19, "RIGHT": 19,
    "M1": 23, "M2": 24, "M3": 25, "M4": 26,
}

CANONICAL_KEY_NAMES = {
    0:"A", 1:"B", 2:"EMPTY", 3:"X", 4:"Y",
    6:"LB", 7:"RB", 8:"LT", 9:"RT", 10:"VIEW", 11:"MENU", 12:"GUIDE",
    13:"L3", 14:"R3", 16:"DPAD_UP", 17:"DPAD_DOWN",
    18:"DPAD_LEFT", 19:"DPAD_RIGHT",
    23:"M1", 24:"M2", 25:"M3", 26:"M4",
}

def parse_key_code(text: str) -> int:
    t = text.strip().upper().replace("-", "_").replace(" ", "_")
    if t in MAP_KEY_CODES:
        return MAP_KEY_CODES[t]
    try:
        v = int(text, 0)
    except ValueError:
        raise ValueError(f"unknown ArmorX key name/code: {text}")
    if not 0 <= v <= 255:
        raise ValueError(f"key code out of range: {v}")
    return v


BYTE_FIELDS = {
    "motorSpeedIdx": 4,
    "motorMax": 5,
    "triggerMode": 9,
    "triggerLeftDZCenter": 10,
    "triggerLeftDZSide": 11,
    "triggerRightDZCenter": 12,
    "triggerRightDZSide": 13,
    "joystickCircleLimit": 14,
    "stickTurn": 15,
    "stickLeftDZCenter": 16,
    "stickLeftDZSide": 17,
    "stickRightDZCenter": 18,
    "stickRightDZSide": 19,
    "stickLeftCurveModeb": 20,
    "stickLeftCurveYDivx": 21,
    "stickLeftCurveSpeedORpt1x": 22,
    "stickLeftCurveSmootORpt1y": 23,
    "stickLeftCurveCurveORpt2x": 24,
    "stickLeftCurveRes0ORpt2y": 25,
    "stickRightCurveModeb": 28,
    "stickRightCurveYDivx": 29,
    "stickRightCurveSpeedORpt1x": 30,
    "stickRightCurveSmootORpt1y": 31,
    "stickRightCurveCurveORpt2x": 32,
    "stickRightCurveRes0ORpt2y": 33,
    "sensorMode": 36,
    "sensorDir": 37,
    "sensorRightKey0": 38,
    "sensorRightKey1": 39,
    "sensorRightCurve0Modeb": 44,
    "sensorRightCurve0YDivx": 45,
    "sensorRightCurve0SpeedORpt1x": 46,
    "sensorRightCurve0SmootORpt1y": 47,
    "sensorRightCurve0CurveORpt2x": 48,
    "sensorRightCurve0Res0ORpt2y": 49,
    "sensorRightCurve1Modeb": 52,
    "sensorRightCurve1YDivx": 53,
    "sensorRightCurve1SpeedORpt1x": 54,
    "sensorRightCurve1SmootORpt1y": 55,
    "sensorRightCurve1CurveORpt2x": 56,
    "sensorRightCurve1Res0ORpt2y": 57,
    "sensorRightCurve2Modeb": 60,
    "sensorRightCurve2YDivx": 61,
    "sensorRightCurve2SpeedORpt1x": 62,
    "sensorRightCurve2SmootORpt1y": 63,
    "sensorRightCurve2CurveORpt2x": 64,
    "sensorRightCurve2Res0ORpt2y": 65,
    "sensorMin": 68,
    "turboSpeedIdx": 80,
}

U32_FIELDS = {
    "sensorRightKeyBit": 40,
    "sensorSwitch": 69,
    "turboKey": 81,
}

GROUP_FIELDS = {
    "stickLeftCurve": [20, 21, 22, 23, 24, 25],
    "stickRightCurve": [28, 29, 30, 31, 32, 33],
    "sensorRightCurve0": [44, 45, 46, 47, 48, 49],
    "sensorRightCurve1": [52, 53, 54, 55, 56, 57],
    "sensorRightCurve2": [60, 61, 62, 63, 64, 65],
    "mapKeys": list(range(112, 144)),
}

# Unassigned bytes in the 144-byte constructor path. These are intentionally
# preserved during patch operations and default to zero for a fresh image.
RESERVED_RANGES = [
    (6, 8, "motorRes"),
    (26, 27, "reserved_after_left_curve"),
    (34, 35, "reserved_after_right_curve"),
    (50, 51, "reserved_after_sensor_curve0"),
    (58, 59, "reserved_after_sensor_curve1"),
    (66, 67, "reserved_after_sensor_curve2"),
    (73, 79, "reserved_73_79"),
    (85, 111, "reserved_after_turbo"),
]


def crc16_gamepad(data: List[int]) -> int:
    """CRC used by GamepadSet30::toList over config bytes[2:]."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            crc &= 0xFFFF
    return crc


def get_u16_be(buf: List[int], off: int) -> int:
    return (buf[off] << 8) | buf[off + 1]


def put_u16_be(buf: List[int], off: int, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"u16 out of range: {value}")
    buf[off] = (value >> 8) & 0xFF
    buf[off + 1] = value & 0xFF


def get_u32_be(buf: List[int], off: int) -> int:
    return ((buf[off] << 24) | (buf[off+1] << 16) |
            (buf[off+2] << 8) | buf[off+3])


def put_u32_be(buf: List[int], off: int, value: int) -> None:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"u32 out of range: {value}")
    buf[off] = (value >> 24) & 0xFF
    buf[off+1] = (value >> 16) & 0xFF
    buf[off+2] = (value >> 8) & 0xFF
    buf[off+3] = value & 0xFF


def _normalize_list(obj: Any) -> List[int]:
    # Accept a server record, a configJson string, or a raw byte list.
    if isinstance(obj, dict):
        if "configJson" in obj:
            obj = obj["configJson"]
        elif "data" in obj and isinstance(obj["data"], dict) and "configJson" in obj["data"]:
            obj = obj["data"]["configJson"]
        elif "bytes" in obj:
            obj = obj["bytes"]
        else:
            raise ValueError("JSON object does not contain configJson or bytes")
    if isinstance(obj, str):
        obj = json.loads(obj)
    if not isinstance(obj, list):
        raise ValueError("config must resolve to a JSON list")
    out = []
    for i, x in enumerate(obj):
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError(f"byte {i} is not an integer: {x!r}")
        if not 0 <= x <= 255:
            raise ValueError(f"byte {i} out of range: {x}")
        out.append(x)
    return out


def load_config(path: str) -> List[int]:
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return _normalize_list(json.loads(text))


def validate(buf: List[int], require_144: bool = True) -> Dict[str, Any]:
    if require_144 and len(buf) != CONFIG_LEN:
        raise ValueError(f"expected {CONFIG_LEN} bytes, got {len(buf)}")
    declared = get_u16_be(buf, 2) if len(buf) >= 4 else None
    stored_crc = get_u16_be(buf, 0) if len(buf) >= 2 else None
    computed_crc = crc16_gamepad(buf[2:]) if len(buf) >= 2 else None
    return {
        "actual_length": len(buf),
        "declared_length": declared,
        "stored_crc": stored_crc,
        "stored_crc_hex": f"0x{stored_crc:04X}" if stored_crc is not None else None,
        "computed_crc": computed_crc,
        "computed_crc_hex": f"0x{computed_crc:04X}" if computed_crc is not None else None,
        "crc_matches": stored_crc == computed_crc,
    }


def decode(buf: List[int]) -> Dict[str, Any]:
    v = validate(buf)
    d: Dict[str, Any] = {
        "format": "ArmorX Pro GamepadSet30 144-byte",
        **v,
        "fields": {},
        "groups": {},
        "reserved": {},
        "share_regions": {
            "res2": {
                "offsets": [SHARE_RES2_START, SHARE_RES2_END - 1],
                "bytes": buf[SHARE_RES2_START:SHARE_RES2_END],
            }
        },
    }
    f = d["fields"]
    for name, off in BYTE_FIELDS.items():
        f[name] = buf[off]
    for name, off in U32_FIELDS.items():
        f[name] = get_u32_be(buf, off)
    for name, offs in GROUP_FIELDS.items():
        d["groups"][name] = [buf[o] for o in offs]
    d["mapKeys_named"] = [
        {"source_id": i,
         "source_name": CANONICAL_KEY_NAMES.get(i),
         "target_id": buf[MAPKEYS_START+i],
         "target_name": CANONICAL_KEY_NAMES.get(buf[MAPKEYS_START+i])}
        for i in range(32)
    ]
    for start, end, name in RESERVED_RANGES:
        d["reserved"][name] = {
            "offsets": [start, end],
            "bytes": buf[start:end+1],
        }
    d["raw_bytes"] = buf
    return d


def parse_value(text: str) -> Any:
    s = text.strip()
    if "," in s:
        vals = []
        for part in s.split(","):
            vals.append(int(part.strip(), 0))
        return vals
    return int(s, 0)


def apply_assignment(buf: List[int], assignment: str) -> None:
    if "=" not in assignment:
        raise ValueError(f"assignment must be FIELD=VALUE: {assignment}")
    key, raw = assignment.split("=", 1)
    key = key.strip()
    if key.startswith("mapKey[") and key.endswith("]"):
        value = parse_key_code(raw)
    else:
        value = parse_value(raw)
    if key in BYTE_FIELDS:
        if isinstance(value, list) or not 0 <= value <= 255:
            raise ValueError(f"{key} requires one byte (0..255)")
        buf[BYTE_FIELDS[key]] = value
    elif key in U32_FIELDS:
        if isinstance(value, list):
            raise ValueError(f"{key} requires one u32 value")
        put_u32_be(buf, U32_FIELDS[key], value)
    elif key in GROUP_FIELDS:
        offs = GROUP_FIELDS[key]
        if not isinstance(value, list) or len(value) != len(offs):
            raise ValueError(f"{key} requires {len(offs)} comma-separated byte values")
        for off, val in zip(offs, value):
            if not 0 <= val <= 255:
                raise ValueError(f"{key}: byte out of range: {val}")
            buf[off] = val
    elif key.startswith("byte[") and key.endswith("]"):
        off = int(key[5:-1], 0)
        if not 0 <= off < len(buf):
            raise ValueError(f"byte offset out of range: {off}")
        if isinstance(value, list) or not 0 <= value <= 255:
            raise ValueError("raw byte requires one value 0..255")
        buf[off] = value
    elif key.startswith("mapKey[") and key.endswith("]"):
        # Supports both numeric and named syntax, e.g. mapKey[23]=0 or mapKey[M1]=A.
        src_text = key[7:-1].strip()
        idx = parse_key_code(src_text)
        if not 0 <= idx < 32:
            raise ValueError("mapKey source index must resolve to 0..31")
        # parse_value() handles numeric values; if it was not numeric, retry as a key name.
        if isinstance(value, list):
            raise ValueError("mapKey target requires one key code/name")
        buf[MAPKEYS_START + idx] = value
    else:
        raise ValueError(f"unknown field: {key}")


def canonicalize(buf: List[int], recompute_crc: bool = True) -> List[int]:
    if len(buf) != CONFIG_LEN:
        raise ValueError(f"expected {CONFIG_LEN} bytes")
    out = list(buf)
    put_u16_be(out, 2, CONFIG_LEN)
    if recompute_crc:
        crc = crc16_gamepad(out[2:])
        put_u16_be(out, 0, crc)
    return out


def fresh() -> List[int]:
    out = [0] * CONFIG_LEN
    put_u16_be(out, 2, CONFIG_LEN)
    # Identity map is the least-assumptive default seen in the sample, but
    # callers should prefer patching a known-good template.
    out[MAPKEYS_START:MAPKEYS_START+32] = list(range(32))
    return canonicalize(out)


def write_json(path: str | None, obj: Any, compact: bool = False) -> None:
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":") if compact else None,
                   indent=None if compact else 2)
    if path:
        pathlib.Path(path).write_text(s + "\n", encoding="utf-8")
    else:
        print(s)


def cmd_decode(args: argparse.Namespace) -> None:
    buf = load_config(args.input)
    write_json(args.output, decode(buf))


def cmd_patch(args: argparse.Namespace) -> None:
    buf = load_config(args.input)
    if len(buf) != CONFIG_LEN:
        raise ValueError(f"expected 144-byte template, got {len(buf)}")
    for a in args.sets:
        apply_assignment(buf, a)
    if args.keep_crc:
        put_u16_be(buf, 2, CONFIG_LEN)
    else:
        buf = canonicalize(buf)
    write_json(args.output, buf, compact=args.compact)


def cmd_create(args: argparse.Namespace) -> None:
    buf = load_config(args.template) if args.template else fresh()
    for a in args.sets:
        apply_assignment(buf, a)
    buf = canonicalize(buf)
    write_json(args.output, buf, compact=args.compact)


def cmd_validate(args: argparse.Namespace) -> None:
    buf = load_config(args.input)
    write_json(None, validate(buf, require_144=False))


def cmd_keys(args: argparse.Namespace) -> None:
    rows = []
    for i in range(32):
        rows.append({
            "id": i,
            "name": CANONICAL_KEY_NAMES.get(i),
            "status": ("proven_live" if i == 12 else
                       "proven_old_app" if i in CANONICAL_KEY_NAMES else
                       "unresolved_or_unexposed"),
        })
    write_json(None, rows)


def cmd_configjson(args: argparse.Namespace) -> None:
    buf = load_config(args.input)
    if args.canonical:
        buf = canonicalize(buf)
    # This is the literal JSON string suitable as the configJson field value.
    print(json.dumps(buf, separators=(",", ":")))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    q = sp.add_parser("keys", help="show recovered ArmorX mapKeys IDs")
    q.set_defaults(func=cmd_keys)
    q = sp.add_parser("decode", help="decode a raw/server config into named fields")
    q.add_argument("input"); q.add_argument("-o", "--output"); q.set_defaults(func=cmd_decode)
    q = sp.add_parser("validate", help="show length and CRC status")
    q.add_argument("input"); q.set_defaults(func=cmd_validate)
    q = sp.add_parser("patch", help="patch a known-good 144-byte config, preserving unknown bytes")
    q.add_argument("input"); q.add_argument("--set", dest="sets", action="append", default=[], metavar="FIELD=VALUE")
    q.add_argument("-o", "--output"); q.add_argument("--keep-crc", action="store_true", help="do not regenerate bytes 0..1")
    q.add_argument("--compact", action="store_true"); q.set_defaults(func=cmd_patch)
    q = sp.add_parser("create", help="create a config (prefer --template for hardware-safe defaults)")
    q.add_argument("--template"); q.add_argument("--set", dest="sets", action="append", default=[], metavar="FIELD=VALUE")
    q.add_argument("-o", "--output"); q.add_argument("--compact", action="store_true"); q.set_defaults(func=cmd_create)
    q = sp.add_parser("configjson", help="print the literal configJson array string")
    q.add_argument("input"); q.add_argument("--canonical", action="store_true"); q.set_defaults(func=cmd_configjson)
    return p


def main() -> int:
    try:
        args = build_parser().parse_args()
        args.func(args)
        return 0
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())