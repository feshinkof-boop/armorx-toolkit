#!/usr/bin/env python3
"""Default-config image archaeology across 2.22.0901 / 2.23 / 2.24 / 4.0.8.
Extracts every Dart-pool String literal that is a decimal byte-array, classifies it,
and computes CRC-16/MODBUS over bytes[2:] vs the stored big-endian CRC at bytes[0:2].
Read-only.
"""
import re, json, hashlib, glob, os

TREES = {
    "2.22.0901": "/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/pp.txt",
    "2.23": "/home/salamanka/armorx/re/blutter_out/pp.txt",
    "2.24": "/home/salamanka/armorx/re/v224/blutter_out/pp.txt",
    "4.0.8": "/home/salamanka/armorx-re/mygt408/blutter_out/pp.txt",
}

def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF

ARR = re.compile(rb'\[pp\+0x([0-9a-f]+)\] String: "\[([0-9]+(?:, ?[0-9]+)+)\]"')

out = {}
for build, path in TREES.items():
    data = open(path, "rb").read()
    entries = []
    for m in ARR.finditer(data):
        off, body = m.group(1).decode(), m.group(2)
        parts = [int(x) for x in body.split(b",")]
        if len(parts) < 8:
            continue
        b = bytes(parts)
        declared = (b[2] << 8) | b[3] if len(b) >= 4 else None
        stored_crc = (b[0] << 8) | b[1] if len(b) >= 2 else None
        calc_crc = crc16_modbus(b[2:]) if len(b) > 2 else None
        entries.append({
            "pp_off": "0x" + off, "len": len(b), "declared_len": declared,
            "sha256": hashlib.sha256(b).hexdigest(),
            "sha256_prefix": hashlib.sha256(b).hexdigest()[:16],
            "stored_crc": None if stored_crc is None else "0x%04X" % stored_crc,
            "recomputed_crc": None if calc_crc is None else "0x%04X" % calc_crc,
            "crc_self_valid": (stored_crc == calc_crc) if None not in (stored_crc, calc_crc) else None,
            "bytes": list(b),
        })
    # dedupe by sha
    seen, uniq = set(), []
    for e in entries:
        if e["sha256"] in seen:
            continue
        seen.add(e["sha256"])
        uniq.append(e)
    out[build] = uniq
    print(f"== {build}: {len(uniq)} unique config-like arrays")
    for e in uniq:
        print(f"   off={e['pp_off']} len={e['len']} decl={e['declared_len']} stored_crc={e['stored_crc']} calc={e['recomputed_crc']} selfvalid={e['crc_self_valid']} sha={e['sha256_prefix']}")

json.dump(out, open("/home/salamanka/.hermes/cache/scratch/armorx222/configs.json", "w"), indent=1)

# byte-for-byte compare 2.22 vs others by declared family length
print("\n=== byte-for-byte compare (2.22 vs siblings, same declared len) ===")
for e in out["2.22.0901"]:
    L = e["len"]
    for other in ("2.23", "2.24", "4.0.8"):
        for o in out[other]:
            if o["len"] == L:
                diffs = [i for i, (a, c) in enumerate(zip(e["bytes"], o["bytes"])) if a != c]
                print(f"  2.22 len{L} vs {other} len{o['len']} sha={o['sha256_prefix']}: {len(diffs)} differing bytes at {diffs[:20]}")
                break