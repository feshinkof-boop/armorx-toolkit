#!/usr/bin/env python3
"""ArmorX Pro macroJson / addMacro payload builder.

Reverse-engineered from the legacy MOJHON/BIGBIG WON Flutter app.
This tool intentionally does NOT send network requests. It only builds,
validates, and inspects payloads compatible with the proven app format.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Proven ordinary key IDs used by the app's macro engine.
KEY_IDS: dict[str, int] = {
    "A": 0,
    "B": 1,
    "X": 3,
    "Y": 4,
    "LB": 6,
    "RB": 7,
    "LT": 8,
    "RT": 9,
    "VIEW": 10,
    "SELECT": 10,
    "MENU": 11,
    "START": 11,
    "GUIDE": 12,  # live-proven on ARMOR-X Pro firmware 2741; old macro picker normally doesn't expose it
    "MODE": 12,
    "L3": 13,
    "LS": 13,
    "R3": 14,
    "RS": 14,
    "DPAD_UP": 16,
    "UP": 16,
    "DPAD_DOWN": 17,
    "DOWN": 17,
    "DPAD_LEFT": 18,
    "LEFT": 18,
    "DPAD_RIGHT": 19,
    "RIGHT": 19,
    "M1": 23,
    "M2": 24,
    "M3": 25,
    "M4": 26,

    # 34..49 are the app's joystick-direction pseudo-key switch table.
    # Direction names are strongly supported by the packed axis constants + localization strings.
    "L_LEFT": 34,
    "L_RIGHT": 35,
    "L_DOWN": 36,
    "L_UP": 37,
    "L_LEFT_DOWN": 42,
    "L_RIGHT_DOWN": 43,
    "L_LEFT_UP": 44,
    "L_RIGHT_UP": 45,
    "R_LEFT": 38,
    "R_RIGHT": 39,
    "R_DOWN": 40,
    "R_UP": 41,
    "R_LEFT_DOWN": 46,
    "R_RIGHT_DOWN": 47,
    "R_LEFT_UP": 48,
    "R_RIGHT_UP": 49,
}

# Canonical names for serialization / pretty-printing.
CANONICAL_NAMES: dict[int, str] = {
    0: "A", 1: "B", 3: "X", 4: "Y", 6: "LB", 7: "RB", 8: "LT", 9: "RT",
    10: "VIEW", 11: "MENU", 12: "GUIDE", 13: "L3", 14: "R3",
    16: "DPAD_UP", 17: "DPAD_DOWN", 18: "DPAD_LEFT", 19: "DPAD_RIGHT",
    23: "M1", 24: "M2", 25: "M3", 26: "M4",
    34: "L_LEFT", 35: "L_RIGHT", 36: "L_DOWN", 37: "L_UP",
    38: "R_LEFT", 39: "R_RIGHT", 40: "R_DOWN", 41: "R_UP",
    42: "L_LEFT_DOWN", 43: "L_RIGHT_DOWN", 44: "L_LEFT_UP", 45: "L_RIGHT_UP",
    46: "R_LEFT_DOWN", 47: "R_RIGHT_DOWN", 48: "R_LEFT_UP", 49: "R_RIGHT_UP",
}

RUN_KEYS = {"M1": 23, "M2": 24, "M3": 25, "M4": 26}

# Directly proven by the old app's four-item execution-mode list.
EXECUTION_MODES = {
    "long_press": 0,
    "long-press": 0,
    "hold": 0,
    "tap": 1,
    "long_press_cycle": 2,
    "long-press-cycle": 2,
    "hold_cycle": 2,
    "tap_cycle": 3,
    "tap-cycle": 3,
}
MODE_NAMES = {0: "long_press", 1: "tap", 2: "long_press_cycle", 3: "tap_cycle"}

V41_MAX_STEPS = 16
LEGACY_MAX_STEPS = 15


def compact_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def norm_key_name(name: str) -> str:
    return name.strip().upper().replace("-", "_").replace(" ", "_")


def parse_key(token: str) -> tuple[int, str]:
    token = norm_key_name(token)
    if token.isdigit():
        kid = int(token)
        if not (0 <= kid <= 63):
            raise ValueError(f"key id out of range: {kid}")
        return kid, CANONICAL_NAMES.get(kid, f"KEY_{kid}")
    if token not in KEY_IDS:
        raise ValueError(f"unknown key '{token}'")
    kid = KEY_IDS[token]
    return kid, CANONICAL_NAMES.get(kid, token)


def parse_chord(expr: str) -> tuple[list[int], list[str]]:
    parts = [p for p in re.split(r"\s*\+\s*", expr.strip()) if p]
    if not parts:
        raise ValueError("empty key/chord")
    ids: list[int] = []
    names: list[str] = []
    for part in parts:
        kid, name = parse_key(part)
        if kid not in ids:
            ids.append(kid)
            names.append(name)
    return ids, names


def make_row(index: int, key_expr: str, duration: int = 200, interval: int = 100,
             *, total_rows: int | None = None) -> dict[str, Any]:
    if duration < 0 or interval < 0:
        raise ValueError("duration and interval must be >= 0 ms")
    ids, names = parse_chord(key_expr)
    n = total_rows if total_rows is not None else index + 1
    is_first = index == 0
    is_last = index == n - 1

    # The four show* fields are editor/UI metadata. applicationMacro consumes
    # mapList, duration and interval for device execution. We keep coherent
    # timeline flags for round-tripping through the editor.
    return {
        "index": index,
        "keyText": "+".join(names),
        "mapList": compact_json(ids),
        "keyNameList": compact_json(names),
        "duration": int(duration),
        "interval": int(interval),
        "showUpLine": not is_first,
        "showDownLine": not is_last,
        "showInterval": not is_last,
        # Captured V41 client traffic serializes showAdd=true for every row.
        "showAdd": True,
    }


def build_rows(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(steps)
    return [make_row(i, s["keys"], int(s.get("duration", 200)), int(s.get("interval", 100)), total_rows=total)
            for i, s in enumerate(steps)]


def build_macro_json(steps: list[dict[str, Any]]) -> str:
    """Build the exact captured V41 wire representation.

    The app serializes macroJson as a JSON list of JSON-encoded row strings,
    not as a direct list of row objects.
    """
    return compact_json([compact_json(row) for row in build_rows(steps)])


def build_macro_object(*, name: str, trigger: str = "M1", mode: str = "long_press",
                       repeat_time: int = 200, active: bool = False,
                       steps: list[dict[str, Any]], macro_id: int = -1) -> dict[str, Any]:
    trig = norm_key_name(trigger)
    if trig not in RUN_KEYS:
        raise ValueError("macro trigger must be M1, M2, M3 or M4")
    mode_key = mode.strip().lower().replace(" ", "_")
    if mode_key not in EXECUTION_MODES:
        raise ValueError(f"unknown execution mode '{mode}'")
    if repeat_time < 0:
        raise ValueError("repeat_time must be >= 0 ms")
    if not steps:
        raise ValueError("macro must contain at least one step")
    if len(steps) > V41_MAX_STEPS:
        raise ValueError(f"firmware V41 app macros support at most {V41_MAX_STEPS} steps")
    return {
        "changed": True,
        "id": int(macro_id),
        "inUse": bool(active),
        "runKey": RUN_KEYS[trig],
        "runKeyName": trig,
        "isRepeat": EXECUTION_MODES[mode_key],
        "repeatTime": int(repeat_time),
        "macroName": name,
        "macroJson": build_macro_json(steps),
    }


def build_add_macro_payload(*, phone_uuid: str, dev_uuid: str, macro_obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "phoneUuid": phone_uuid,
        "devUuid": dev_uuid,
        # /dev/addMacro uses 0/1 on the wire even though share objects may use bool.
        "inUse": int(bool(macro_obj["inUse"])),
        "runKey": macro_obj["runKey"],
        "runKeyName": macro_obj["runKeyName"],
        "isRepeat": macro_obj["isRepeat"],
        "repeatTime": macro_obj["repeatTime"],
        "macroName": macro_obj["macroName"],
        "macroJson": macro_obj["macroJson"],
    }


def parse_bool(v: str) -> bool:
    v = v.strip().lower()
    if v in {"1", "true", "yes", "on"}: return True
    if v in {"0", "false", "no", "off"}: return False
    raise ValueError(f"invalid boolean '{v}'")


def parse_dsl(path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta: dict[str, Any] = {
        "name": "ArmorX Macro",
        "trigger": "M1",
        "mode": "long_press",
        "repeat_time": 200,
        "active": False,
    }
    steps: list[dict[str, Any]] = []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            try:
                k, v = line[1:].split(None, 1)
            except ValueError:
                raise ValueError(f"{path}:{lineno}: directive requires a value")
            k = k.lower().replace("-", "_")
            if k == "name": meta["name"] = v
            elif k == "trigger": meta["trigger"] = v
            elif k == "mode": meta["mode"] = v
            elif k in {"repeat", "repeat_time"}: meta["repeat_time"] = int(v)
            elif k in {"active", "inuse", "in_use"}: meta["active"] = parse_bool(v)
            else: raise ValueError(f"{path}:{lineno}: unknown directive @{k}")
            continue

        # Step grammar: KEYS DURATION_MS [INTERVAL_MS]
        # e.g. A 80 50   or   LT+RT 120 70
        parts = line.split()
        if len(parts) not in (2, 3):
            raise ValueError(f"{path}:{lineno}: expected 'KEYS DURATION_MS [INTERVAL_MS]'")
        keys = parts[0]
        duration = int(parts[1])
        interval = int(parts[2]) if len(parts) == 3 else 100
        # validate chord now for useful line-numbered errors
        parse_chord(keys)
        if duration < 0 or interval < 0:
            raise ValueError(f"{path}:{lineno}: times must be >= 0")
        steps.append({"keys": keys, "duration": duration, "interval": interval})
    return meta, steps


def decode_macro_json(s: str) -> list[dict[str, Any]]:
    rows = json.loads(s)
    if not isinstance(rows, list):
        raise ValueError("macroJson top-level value must decode to a list")
    out = []
    for i, row in enumerate(rows):
        # Captured V41 traffic uses List<String>, where each string is a
        # JSON-encoded row. Accept direct objects too for backward compatibility.
        if isinstance(row, str):
            row = json.loads(row)
        if not isinstance(row, dict):
            raise ValueError(f"row {i} must be an object or a JSON-encoded object string")
        r = dict(row)
        for key in ("mapList", "keyNameList"):
            if key not in r or not isinstance(r[key], str):
                raise ValueError(f"row {i}.{key} must be a JSON-encoded string")
            r[key + "Decoded"] = json.loads(r[key])
        out.append(r)
    return out


def validate_macro_object(obj: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = ["inUse", "runKey", "runKeyName", "isRepeat", "repeatTime", "macroName", "macroJson"]
    for k in required:
        if k not in obj: errors.append(f"missing field: {k}")
    if errors: return errors
    if obj["runKey"] not in RUN_KEYS.values(): errors.append("runKey must be 23..26 (M1..M4)")
    if obj["isRepeat"] not in MODE_NAMES: errors.append("isRepeat must be 0..3")
    try:
        rows = decode_macro_json(obj["macroJson"])
        if not (1 <= len(rows) <= V41_MAX_STEPS):
            errors.append(f"macroJson must contain 1..{V41_MAX_STEPS} rows for V41")
        for i, row in enumerate(rows):
            ids = row.get("mapListDecoded")
            if not isinstance(ids, list) or not all(isinstance(x, int) for x in ids):
                errors.append(f"row {i}.mapList must decode to List<int>")
            for k in ("duration", "interval"):
                if not isinstance(row.get(k), int) or row[k] < 0:
                    errors.append(f"row {i}.{k} must be a non-negative integer")
    except Exception as e:
        errors.append(str(e))
    return errors


def cmd_build(args: argparse.Namespace) -> int:
    meta, steps = parse_dsl(args.dsl)
    if args.name is not None: meta["name"] = args.name
    if args.trigger is not None: meta["trigger"] = args.trigger
    if args.mode is not None: meta["mode"] = args.mode
    if args.repeat_time is not None: meta["repeat_time"] = args.repeat_time
    if args.active: meta["active"] = True

    obj = build_macro_object(name=meta["name"], trigger=meta["trigger"], mode=meta["mode"],
                             repeat_time=meta["repeat_time"], active=meta["active"], steps=steps)
    if args.phone_uuid is not None or args.dev_uuid is not None:
        if not (args.phone_uuid and args.dev_uuid):
            raise ValueError("--phone-uuid and --dev-uuid must be supplied together")
        result = build_add_macro_payload(phone_uuid=args.phone_uuid, dev_uuid=args.dev_uuid, macro_obj=obj)
    else:
        result = obj

    txt = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(txt + "\n", encoding="utf-8")
    else:
        print(txt)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    obj = json.loads(Path(args.file).read_text(encoding="utf-8"))
    # addMacro payload and editor object share all fields validated below.
    errs = validate_macro_object(obj)
    if errs:
        for e in errs: print("ERROR:", e, file=sys.stderr)
        return 1
    rows = decode_macro_json(obj["macroJson"])
    print(f"OK: {len(rows)} step(s), trigger={obj['runKeyName']}({obj['runKey']}), mode={MODE_NAMES[obj['isRepeat']]}, repeatTime={obj['repeatTime']} ms")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    obj = json.loads(Path(args.file).read_text(encoding="utf-8"))
    rows = decode_macro_json(obj["macroJson"])
    print(f"name: {obj.get('macroName','')}")
    print(f"trigger: {obj.get('runKeyName')} ({obj.get('runKey')})")
    print(f"mode: {MODE_NAMES.get(obj.get('isRepeat'), 'UNKNOWN')} ({obj.get('isRepeat')})")
    print(f"repeatTime: {obj.get('repeatTime')} ms")
    print(f"inUse: {obj.get('inUse')}")
    print(f"steps: {len(rows)}")
    for i, r in enumerate(rows, 1):
        names = r["keyNameListDecoded"]
        print(f"  {i:02d}. {'+'.join(names)}  hold={r['duration']} ms  interval={r['interval']} ms  ids={r['mapListDecoded']}")
    return 0


def cmd_keys(_: argparse.Namespace) -> int:
    seen = set()
    for kid in sorted(CANONICAL_NAMES):
        name = CANONICAL_NAMES[kid]
        if name in {"M1", "M2", "M3", "M4"}:
            note = " (macro trigger; not normally an action key)"
        elif 34 <= kid <= 49:
            note = " (joystick pseudo-key; strong evidence mapping)"
        elif kid == 12:
            note = " (Guide/Xbox/Mode; proven live)"
        else:
            note = ""
        print(f"{kid:2d}  {name}{note}")
        seen.add(kid)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build/inspect ArmorX Pro app macroJson payloads")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="build macro editor object or /dev/addMacro JSON from a DSL file")
    b.add_argument("dsl")
    b.add_argument("-o", "--output")
    b.add_argument("--name")
    b.add_argument("--trigger", choices=list(RUN_KEYS))
    b.add_argument("--mode", choices=["long_press", "tap", "long_press_cycle", "tap_cycle"])
    b.add_argument("--repeat-time", type=int)
    b.add_argument("--active", action="store_true")
    b.add_argument("--phone-uuid")
    b.add_argument("--dev-uuid")
    b.set_defaults(func=cmd_build)

    v = sub.add_parser("validate", help="validate generated editor/addMacro JSON")
    v.add_argument("file")
    v.set_defaults(func=cmd_validate)

    i = sub.add_parser("inspect", help="human-readable decode of generated/server macro JSON")
    i.add_argument("file")
    i.set_defaults(func=cmd_inspect)

    k = sub.add_parser("keys", help="print known macro key IDs")
    k.set_defaults(func=cmd_keys)
    return p


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.func(args)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())