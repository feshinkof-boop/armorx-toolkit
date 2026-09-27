#!/usr/bin/env python3
"""Decode a real ARMOR-X Pro 144-byte config image into a semantic snapshot.

Field names come from the canonical 4.0.8 reconstruction
(baselines/imported-research/config-144-reconstruction.md); offsets with no proven
name are reported as UNKNOWN with raw values only - nothing is invented here.

Usage: real_baseline_decode.py <image.bin> [--json out.json] [--md out.md]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

LAB = Path("/home/salamanka/armorx-lab")
sys.path.insert(0, str(LAB / "ble" / "virtual-armorx"))
import armorx_protocol as proto  # noqa: E402

# (offset_start, offset_end_inclusive, size, endian, field name, evidence level)
FIELDS = [
    (0, 1, 2, "raw", "header (semantics UNKNOWN)", "STRONG EVIDENCE"),
    (2, 3, 2, "BE", "len = total config length", "PROVEN STATIC"),
    (4, 4, 1, "byte", "UNKNOWN (global static written)", "STRONG EVIDENCE"),
    (5, 5, 1, "byte", "motorMax", "PROVEN STATIC"),
    (6, 8, 3, "3 bytes", "UNKNOWN", "UNKNOWN"),
    (9, 9, 1, "byte", "triggerMode", "PROVEN STATIC"),
    (10, 11, 2, "2 bytes", "triggerLeftDeadzone (center,side)", "PROVEN STATIC"),
    (12, 13, 2, "2 bytes", "triggerRightDeadzone", "PROVEN STATIC"),
    (14, 14, 1, "byte", "joystickCircleLimit", "PROVEN STATIC"),
    (15, 15, 1, "byte", "stickTurn", "PROVEN STATIC"),
    (16, 17, 2, "2 bytes", "stickLeftDeadzone", "PROVEN STATIC"),
    (18, 19, 2, "2 bytes", "stickRightDeadzone", "PROVEN STATIC"),
    (20, 25, 6, "3 x Axis2", "stickLeftCurve", "PROVEN STATIC"),
    (26, 27, 2, "2 bytes", "UNKNOWN", "UNKNOWN"),
    (28, 33, 6, "StickCurve", "stickRightCurve", "PROVEN STATIC"),
    (34, 35, 2, "2 bytes", "UNKNOWN", "UNKNOWN"),
    (36, 36, 1, "byte", "sensorMode", "PROVEN STATIC"),
    (37, 37, 1, "byte", "sensorDir", "PROVEN STATIC"),
    (38, 38, 1, "byte", "sensorRightKey0", "PROVEN STATIC"),
    (39, 39, 1, "byte", "sensorRightKey1", "PROVEN STATIC"),
    (40, 43, 4, "u32 BE", "sensorRightKeyBit", "PROVEN STATIC"),
    (44, 49, 6, "StickCurve", "sensorRightCurve0", "PROVEN STATIC"),
    (50, 51, 2, "-", "UNKNOWN", "UNKNOWN"),
    (52, 57, 6, "StickCurve", "sensorRightCurve1", "PROVEN STATIC"),
    (58, 59, 2, "-", "UNKNOWN", "UNKNOWN"),
    (60, 65, 6, "StickCurve", "sensorRightCurve2", "PROVEN STATIC"),
    (66, 67, 2, "-", "UNKNOWN", "UNKNOWN"),
    (68, 68, 1, "byte", "sensorMin", "PROVEN STATIC"),
    (69, 72, 4, "u32 BE", "sensorSwitch", "PROVEN STATIC"),
    (73, 75, 3, "-", "UNKNOWN", "UNKNOWN"),
    (76, 76, 1, "byte", "UNKNOWN (global static written) - turboSpeedIdx (name unproven)", "STRONG EVIDENCE"),
    (77, 80, 4, "u32 BE", "turboKey", "PROVEN STATIC"),
    (81, 93, 13, "-", "UNKNOWN for 0x90 (written only in the 0xF0 branch)", "UNKNOWN"),
    (94, 111, 18, "-", "UNKNOWN", "UNKNOWN"),
    (112, 143, 32, "1 byte/key", "mapKeys[32]", "STRONG EVIDENCE"),
]

# Key-id labels proven elsewhere in the project (bit == id rule; id 15 = Capture).
KEY_LABELS = {
    0: "A", 1: "B", 2: "Empty", 3: "X", 4: "Y", 5: "UNKNOWN", 6: "LB", 7: "RB",
    8: "LT", 9: "RT", 10: "View", 11: "Menu", 12: "UNKNOWN", 13: "L3", 14: "R3",
    15: "Capture", 16: "D-pad Up", 17: "D-pad Down", 18: "D-pad Left",
    19: "D-pad Right", 20: "UNKNOWN", 21: "UNKNOWN", 22: "UNKNOWN", 23: "UNKNOWN",
    24: "UNKNOWN", 25: "UNKNOWN", 26: "UNKNOWN", 27: "M5", 28: "M6", 29: "M7",
    30: "UNKNOWN", 31: "UNKNOWN",
}


def decode(image: bytes) -> dict:
    if len(image) < 144:
        raise SystemExit(f"image is {len(image)} bytes, expected >= 144")
    stored_crc = int.from_bytes(image[0:2], "big")
    declared = int.from_bytes(image[2:4], "big")
    out: dict = {
        "length": len(image),
        "sha256": hashlib.sha256(image).hexdigest(),
        "stored_crc_be": f"0x{stored_crc:04X}",
        "declared_length": f"0x{declared:04X} ({declared})",
        "crc_valid": proto.config_crc_valid(image),
        "fields": [],
    }
    for start, end, size, endian, name, evidence in FIELDS:
        raw = image[start:end + 1]
        value: object = raw.hex(" ")
        if endian == "u32 BE":
            value = int.from_bytes(raw, "big")
        elif endian == "byte":
            value = raw[0]
        entry = {"offset": f"{start}-{end}", "size": size, "endian": endian,
                 "field": name, "raw": raw.hex(" "), "value": value,
                 "evidence": evidence}
        if name.startswith("mapKeys"):
            keys = []
            for i, b in enumerate(raw):
                keys.append({
                    "source_id": i, "source_label": KEY_LABELS.get(i, "UNKNOWN"),
                    "target_id": b, "absolute_offset": 112 + i,
                    "raw_byte": f"0x{b:02X}",
                })
            entry["keys"] = keys
            entry["identity_mapping"] = all(k["target_id"] == k["source_id"] for k in keys)
            entry["source_15_offset_127"] = keys[15]
        out["fields"].append(entry)
    out["map_keys"] = next(f["keys"] for f in out["fields"] if f["field"].startswith("mapKeys"))
    return out


def to_md(d: dict) -> str:
    lines = [f"# Real ARMOR-X Pro baseline decode", "",
             f"- length: {d['length']}",
             f"- sha256: `{d['sha256']}`",
             f"- stored CRC (bytes 0-1 BE): {d['stored_crc_be']}",
             f"- declared length (bytes 2-3 BE): {d['declared_length']}",
             f"- CRC-16/MODBUS over bytes 2..end verifies: **{d['crc_valid']}**", "",
             "| offset | size | endian | field | raw | value | evidence |",
             "|---|---|---|---|---|---|---|"]
    for f in d["fields"]:
        if f["field"].startswith("mapKeys"):
            continue
        lines.append(f"| {f['offset']} | {f['size']} | {f['endian']} | {f['field']} | "
                     f"`{f['raw']}` | `{f['value']}` | {f['evidence']} |")
    lines += ["", "## mapKeys[0..31] (config bytes 112..143)", "",
              "| src id | src label | target id | abs offset | raw byte |", "|---|---|---|---|---|"]
    for k in d["map_keys"]:
        lines.append(f"| {k['source_id']} | {k['source_label']} | {k['target_id']} | "
                     f"{k['absolute_offset']} | {k['raw_byte']} |")
    lines += ["", f"identity mapping (target == source for all 32): "
              f"**{d['fields'][-1]['identity_mapping']}**",
              f"mapKeys[15] at absolute offset 127: {json.dumps(d['fields'][-1]['source_15_offset_127'])}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args()
    image = Path(args.image).read_bytes()
    d = decode(image)
    if args.json:
        Path(args.json).write_text(json.dumps(d, indent=1))
    if args.md:
        Path(args.md).write_text(to_md(d))
    print(to_md(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
