#!/usr/bin/env python3
"""parse-baseline.py -- decode an ARMOR-X Pro 144-byte D6 configuration image.

Reproducible decode of the immutable baseline (never re-typed by hand):
  * header / declared length / CRC-16/MODBUS (poly 0xA001, init 0xFFFF, over bytes 2..end)
  * the known field offsets
  * mapKeys[0..31] = config bytes 112..143  (mapKeys[source] = target)
      - source id 15 (Capture) lives at ABSOLUTE BYTE 127
      - key-mask rule: bit == ID, NOT ID+1   (6 -> 0x40, 15 -> 0x8000, 16 -> 0x10000)

Usage:
  parse-baseline.py <baseline.bin> [--out-json FILE] [--out-md FILE]
  parse-baseline.py <baseline.bin> --fragments <baseline-fragments.jsonl> [--out-json ...]

Exits non-zero (and prints why) when the image is not the expected family/length or
the CRC fails: configuration writes must not proceed on an unverified image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

FIELDS = [
    (0, 2, "header (semantics UNKNOWN)", "STRONG EVIDENCE"),
    (2, 2, "len = total config length (BE)", "PROVEN STATIC"),
    (4, 1, "UNKNOWN (global static written)", "STRONG EVIDENCE"),
    (5, 1, "motorMax", "PROVEN STATIC"),
    (6, 3, "UNKNOWN", "UNKNOWN"),
    (9, 1, "triggerMode", "PROVEN STATIC"),
    (10, 2, "triggerLeftDeadzone (center,side)", "PROVEN STATIC"),
    (12, 2, "triggerRightDeadzone", "PROVEN STATIC"),
    (14, 1, "joystickCircleLimit", "PROVEN STATIC"),
    (15, 1, "stickTurn", "PROVEN STATIC"),
    (16, 2, "stickLeftDeadzone", "PROVEN STATIC"),
    (18, 2, "stickRightDeadzone", "PROVEN STATIC"),
    (20, 6, "stickLeftCurve", "PROVEN STATIC"),
    (26, 2, "UNKNOWN", "UNKNOWN"),
    (28, 6, "stickRightCurve", "PROVEN STATIC"),
    (34, 2, "UNKNOWN", "UNKNOWN"),
    (36, 1, "sensorMode", "PROVEN STATIC"),
    (37, 1, "sensorDir", "PROVEN STATIC"),
    (38, 1, "sensorRightKey0", "PROVEN STATIC"),
    (39, 1, "sensorRightKey1", "PROVEN STATIC"),
    (40, 4, "sensorRightKeyBit (u32 BE)", "PROVEN STATIC"),
    (44, 6, "sensorRightCurve0", "PROVEN STATIC"),
    (50, 2, "UNKNOWN", "UNKNOWN"),
    (52, 6, "sensorRightCurve1", "PROVEN STATIC"),
    (58, 2, "UNKNOWN", "UNKNOWN"),
    (60, 6, "sensorRightCurve2", "PROVEN STATIC"),
    (66, 2, "UNKNOWN", "UNKNOWN"),
    (68, 1, "sensorMin", "PROVEN STATIC"),
    (69, 4, "sensorSwitch (u32 BE)", "PROVEN STATIC"),
    (73, 3, "UNKNOWN", "UNKNOWN"),
    (76, 1, "UNKNOWN (global static written)", "STRONG EVIDENCE"),
    (77, 4, "turboKey (u32 BE)", "PROVEN STATIC"),
    (81, 13, "UNKNOWN for 0x90 (written only in the 0xF0 branch)", "UNKNOWN"),
    (94, 18, "UNKNOWN", "UNKNOWN"),
]

# Source-slot labels established by static analysis; ids 5/12/20/21/22/23/24/25/30/31
# stay UNKNOWN until the physical D2 button capture names them.
SRC_LABELS = {
    0: "A", 1: "B", 2: "Empty", 3: "X", 4: "Y", 6: "LB", 7: "RB", 8: "LT", 9: "RT",
    10: "View", 11: "Menu", 13: "L3", 14: "R3", 15: "Capture",
    16: "D-pad Up", 17: "D-pad Down", 18: "D-pad Left", 19: "D-pad Right",
    27: "M5", 28: "M6", 29: "M7",
}


def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def key_mask(bit_id: int) -> int:
    """bit == ID (NOT ID+1): 6 -> 0x40, 15 -> 0x8000, 16 -> 0x10000."""
    return 1 << bit_id


def decode(raw: bytes) -> dict:
    length = len(raw)
    declared = int.from_bytes(raw[2:4], "big") if length >= 4 else None
    stored_crc = int.from_bytes(raw[0:2], "big") if length >= 2 else None
    calc_crc = crc16_modbus(raw[2:]) if length >= 4 else None
    fields = []
    for off, size, name, ev in FIELDS:
        if off + size > length:
            continue
        seg = raw[off:off + size]
        fields.append({"offset": off, "size": size, "field": name, "raw": seg.hex(" "),
                       "value": f"0x{seg.hex()}" if size > 1 else seg[0],
                       "evidence": ev})
    mapkeys = []
    ident = True
    for src in range(32):
        off = 112 + src
        if off >= length:
            break
        target = raw[off]
        ident = ident and (target == src)
        mapkeys.append({
            "source_id": src,
            "source_label": SRC_LABELS.get(src, "UNKNOWN"),
            "target_id": target,
            "absolute_offset": off,
            "raw_byte": f"0x{target:02X}",
            "key_mask": f"0x{key_mask(src):X}",
        })
    return {
        "length": length,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "declared_length_be": f"{declared:04x}" if declared is not None else None,
        "declared_length_int": declared,
        "stored_crc_be": f"{stored_crc:04x}" if stored_crc is not None else None,
        "computed_crc": f"{calc_crc:04x}" if calc_crc is not None else None,
        "crc_valid": (calc_crc == stored_crc) if calc_crc is not None else False,
        "family_144": length == 144,
        "fields": fields,
        "mapKeys": mapkeys,
        "mapKeys_identity": ident,
        "id15": next((m for m in mapkeys if m["source_id"] == 15), None),
        "key_mask_examples": {"6": f"0x{key_mask(6):X}", "15": f"0x{key_mask(15):X}",
                              "16": f"0x{key_mask(16):X}"},
    }


def to_markdown(d: dict) -> str:
    out = [f"# ARMOR-X baseline decode", "",
           f"- length: {d['length']}", f"- sha256: `{d['sha256']}`",
           f"- stored CRC (bytes 0-1 BE): 0x{d['stored_crc_be'].upper()}",
           f"- declared length (bytes 2-3 BE): 0x{d['declared_length_be'].upper()} "
           f"({d['declared_length_int']})",
           f"- CRC-16/MODBUS over bytes 2..end verifies: **{d['crc_valid']}**", "",
           "| offset | size | field | raw | value | evidence |", "|---|---|---|---|---|---|"]
    for f in d["fields"]:
        out.append(f"| {f['offset']}-{f['offset'] + f['size'] - 1} | {f['size']} | {f['field']} | "
                   f"`{f['raw']}` | `{f['value']}` | {f['evidence']} |")
    out += ["", "## mapKeys[0..31] (config bytes 112..143)", "",
            "| src id | src label | target id | abs offset | raw byte | key mask (bit==ID) |",
            "|---|---|---|---|---|---|"]
    for m in d["mapKeys"]:
        out.append(f"| {m['source_id']} | {m['source_label']} | {m['target_id']} | "
                   f"{m['absolute_offset']} | {m['raw_byte']} | {m['key_mask']} |")
    out += ["", f"identity mapping (target == source for all 32): **{d['mapKeys_identity']}**",
            f"mapKeys[15]: {json.dumps(d['id15'])}", "",
            f"key-mask rule examples (bit == ID): {json.dumps(d['key_mask_examples'])}"]
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline")
    ap.add_argument("--out-json")
    ap.add_argument("--out-md")
    ap.add_argument("--fragments", help="baseline-fragments.jsonl to cross-check "
                                        "(concatenated payload must equal the image)")
    args = ap.parse_args()

    raw = pathlib.Path(args.baseline).read_bytes()
    d = decode(raw)

    if args.fragments and pathlib.Path(args.fragments).exists():
        frags, payload = [], bytearray()
        for line in pathlib.Path(args.fragments).read_text().splitlines():
            if not line.strip():
                continue
            f = json.loads(line)
            frags.append({"index": f.get("index"), "len": f.get("length", f.get("len")),
                          "checksum_ok": f.get("checksum_ok")})
            payload += bytes.fromhex(f.get("payload_hex", f.get("payload", "")))
        d["fragments"] = frags
        d["fragments_count"] = len(frags)
        d["fragments_reassemble_equal_baseline"] = bytes(payload) == raw

    print(json.dumps({k: d[k] for k in
                      ("length", "sha256", "declared_length_be", "stored_crc_be",
                       "computed_crc", "crc_valid", "family_144", "mapKeys_identity",
                       "id15", "key_mask_examples") if k in d}, indent=1))

    if args.out_json:
        pathlib.Path(args.out_json).write_text(json.dumps(d, indent=1) + "\n")
    if args.out_md:
        pathlib.Path(args.out_md).write_text(to_markdown(d))

    if not d["family_144"]:
        print(f"FAIL: length {d['length']} != 144 -- not the known family", file=sys.stderr)
        return 2
    if not d["crc_valid"]:
        print("FAIL: CRC-16/MODBUS does not verify", file=sys.stderr)
        return 3
    print("OK: 144-byte family, CRC valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
