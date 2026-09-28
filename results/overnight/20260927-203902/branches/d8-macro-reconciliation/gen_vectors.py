#!/usr/bin/env python3
"""Deterministic generator for results/overnight/.../d8-macro-reconciliation/vectors/d8-vectors.json

STATIC ONLY. No device, no radio, no APK run. Every vector is either
  * captured  -> byte-exact live frame transcribed from results/ (framing anchors), or
  * derived   -> recomputed here from the statically reconstructed layout.
Nothing is hand-typed: the D8 vectors are produced by the builder functions below, and the
framing anchors are read out of the live capture file.
"""
from __future__ import annotations
import json, os, hashlib

OUT = os.path.dirname(os.path.abspath(__file__))
CAPTURE = ("/home/salamanka/armorx-lab/results/experiments/physical-20260927-165347/"
           "baseline-fragments.jsonl")

FRAG_HEADER = 0xA4
OPCODE_D8 = 0xD8
COMMIT_LEN_BYTE = 0x05

def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF

def sum8(bs) -> int:
    return sum(bs) & 0xFF

def build_frag(seg: bytes, ordinal: int) -> bytes:
    body = bytes([FRAG_HEADER, len(seg) + 5, OPCODE_D8, ordinal]) + bytes(seg)
    return body + bytes([sum8(body)])

def build_commit(nfrags: int) -> bytes:
    body = bytes([FRAG_HEADER, COMMIT_LEN_BYTE, OPCODE_D8, nfrags + 1])
    return body + bytes([sum8(body)])

def fragment(payload: bytes, chunk: int):
    n = max(1, (len(payload) + chunk - 1) // chunk)
    return [build_frag(payload[i * chunk:(i + 1) * chunk], i + 1) for i in range(n)]

STICK = {0x22: 0x80000000, 0x23: 0x7f000000, 0x24: 0x007f0000, 0x25: 0x00800000,
         0x26: 0x00008000, 0x27: 0x00007f00, 0x28: 0x0000007f, 0x29: 0x00000080,
         0x2a: 0xa55a0000, 0x2b: 0x5a5a0000, 0x2c: 0xa5a50000, 0x2d: 0x5aa50000,
         0x2e: 0x0000a55a, 0x2f: 0x00005a5a, 0x30: 0x0000a5a5, 0x31: 0x00005aa5}

def old_record(duration_ms, keys, type_byte=0x80):
    km = 0
    for k in keys:
        if k <= 0x21: km |= 1 << k
        elif 0x22 <= k <= 0x31: km |= STICK[k]
    return bytes([type_byte]) + ((duration_ms // 8) & 0xFFFF).to_bytes(2, "big") \
           + (km & 0xFFFFFFFF).to_bytes(4, "big")

def old_payload(records, runkey=46, repeat=200, isrepeat=0, att_type=0):
    n = 10 + 7 * len(records)
    h = bytearray(10)
    h[2], h[3] = (n >> 8) & 0xFF, n & 0xFF
    h[4] = att_type; h[5] = runkey; h[6] = runkey if runkey else 5
    h[7] = isrepeat; h[8], h[9] = (repeat >> 8) & 0xFF, repeat & 0xFF
    body = bytes(h) + b"".join(records)
    crc = crc16_modbus(body[2:])
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF]) + body[2:]

def modern_frame(duration_ms, keys):
    t8 = (duration_ms // 8) & 0xFFF
    km = stk = 0
    for k in keys:
        if k <= 0x20: km |= 1 << k
        elif 0x22 <= k <= 0x31: stk |= STICK[k]
    return bytes([(t8 & 0x0F) << 4, (t8 >> 4) & 0xFF,
                  (km >> 24) & 0xFF, (km >> 16) & 0xFF, (km >> 8) & 0xFF, km & 0xFF,
                  (stk >> 24) & 0xFF, (stk >> 16) & 0xFF, (stk >> 8) & 0xFF, stk & 0xFF])

def modern_payload(frames, runkey=23, repeat=0, isrepeat=0):
    n = 10 + 10 * len(frames)
    h = bytearray(10)
    h[2], h[3] = (n >> 8) & 0xFF, n & 0xFF
    h[4] = 0x00; h[5] = runkey; h[6] = runkey if runkey else 5
    h[7] = isrepeat; h[8], h[9] = (repeat >> 8) & 0xFF, repeat & 0xFF
    body = bytes(h) + b"".join(frames)
    crc = crc16_modbus(body[2:])
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF]) + body[2:]

def hx(b): return b.hex(" ").upper()

def frag_meta(f: bytes):
    return {"hex": hx(f), "byte0": f[0], "length_byte": f[1], "opcode": f[2],
            "ordinal": f[3], "payload_len": len(f) - 5, "total_len": len(f),
            "len_byte_equals_total": f[1] == len(f),
            "len_byte_equals_payload_plus_5": f[1] == (len(f) - 5) + 5,
            "checksum_stored": f[-1], "checksum_calc": sum8(f[:-1]),
            "checksum_ok": f[-1] == sum8(f[:-1])}

vectors = []

# ---- 1. LIVE framing anchors (byte-exact, transcribed from the capture file) ----
live = []
with open(CAPTURE) as fh:
    for line in fh:
        line = line.strip()
        if line:
            live.append(json.loads(line))
for rec in live:
    raw = bytes.fromhex(rec["raw_hex"])
    vectors.append({
        "id": "LIVE-D6-FRAG-%02d" % rec["index"],
        "kind": "framing_anchor",
        "provenance": "CAPTURED (live BLE, %s)" % rec["source"],
        "source_file": CAPTURE,
        "source_line_raw_hex": rec["raw_hex"],
        "version_scope": "framing is shared by all four builds; capture taken against the 2.22 unit",
        "claimed_layout": "A4 | total_len | opcode | ordinal | payload | csum",
        "frame": frag_meta(raw),
    })

# ---- 2. Derived encode vectors ----
def encode_vec(vid, ver, family, chunk, payload, note):
    frs = fragment(payload, chunk)
    return {
        "id": vid, "kind": "encode", "provenance": "DERIVED (static reconstruction; CRC + csum recomputed here)",
        "version": ver, "family": family, "chunk": chunk, "note": note,
        "payload_len": len(payload),
        "payload_crc16_modbus": "%04X" % int.from_bytes(payload[:2], "big"),
        "payload_crc16_recomputed": "%04X" % crc16_modbus(payload[2:]),
        "payload_crc_ok": int.from_bytes(payload[:2], "big") == crc16_modbus(payload[2:]),
        "payload_hex": hx(payload),
        "fragment_count": len(frs),
        "frames": [frag_meta(f) for f in frs],
        "commit": frag_meta(build_commit(len(frs))),
    }

vectors.append(encode_vec(
    "ENC-222-1STEP", "2.22.0901", "OLD/GamepadDefMap(7B)", 15,
    old_payload([old_record(100, [0])]),
    "1 step, 100 ms, key bit0, runKey=46 (default, PROVEN 0x92aabc), repeatTime=200, att.type=0"))
vectors.append(encode_vec(
    "ENC-223-2STEP", "2.23.0609", "OLD/GamepadDefMap(7B)", 15,
    old_payload([old_record(200, [0]), old_record(400, [1])]),
    "2 steps 200/400 ms, keys bit0/bit1, runKey=46, repeatTime=200"))
vectors.append(encode_vec(
    "ENC-224-2FRAME", "2.24.0919", "MODERN/TranscribeFrame(10B)", 15,
    modern_payload([modern_frame(500, [1]), modern_frame(100, [])]),
    "step 500 ms key-id 1 + gap frame 100 ms; runKey=23; reached only when macrosItemLen()==10"))
vectors.append(encode_vec(
    "ENC-408-MAXTIME", "4.0.8", "MODERN/TranscribeFrame(10B)", 15,
    modern_payload([modern_frame(32760, [24])]),
    "single step, 12-bit max t8=0xFFF (32760 ms), key-id 24; shows byte0/byte1 nibble split"))

# ---- 3. Chunk-class vectors (selector evidence) ----
for subpkg, chunk, dev in ((20, 15, "subpackageLength()==20 (devArmorX, 4.0.8 id 10 / 2.24 id 8)"),
                           (48, 43, "subpackageLength()==48"),
                           (72, 67, "subpackageLength()==72")):
    p = modern_payload([modern_frame(500, [1]), modern_frame(100, [])])  # 30 bytes
    frs = fragment(p, chunk)
    vectors.append({
        "id": "CHUNK-%02d" % chunk, "kind": "chunk_class",
        "provenance": "DERIVED from subpackageLength() body (static)",
        "subpackageLength": subpkg, "chunk": chunk, "chunk_formula": "subpackageLength() - 5",
        "device_class_note": dev, "payload_len": len(p),
        "fragment_count": len(frs),
        "frames": [frag_meta(f) for f in frs],
        "commit": frag_meta(build_commit(len(frs))),
    })

# ---- 4. Commit-frame vectors ----
for n in (0, 1, 2, 3, 9, 10):
    c = build_commit(n)
    vectors.append({
        "id": "COMMIT-nfrags%d" % n, "kind": "commit",
        "provenance": "DERIVED (A4|05|D8|nfrags+1|csum, static)",
        "nfrags": n, "count_byte": n + 1,
        "frame": frag_meta(c),
    })

# ---- 5. REJECTED / counter-example vectors ----
imp = bytes.fromhex("A414D89758001E001717000000E003000000" + "AE")
w0a = bytes.fromhex("A40AD80389")
vectors.append({
    "id": "REJECT-imported-19byte-ordinal-less", "kind": "rejected",
    "provenance": "transcribed from baselines/imported-research/d8-test-vectors.json (V1 frame 1)",
    "why_rejected": ("declared length byte 0x14=20 but the frame is only %d bytes; the frame omits the "
                     "ordinal byte at offset 3, so len!=total and byte 3 is not an ordinal" % len(imp)),
    "frame_hex": hx(imp), "length_byte": imp[1], "actual_len": len(imp),
    "len_byte_equals_total": imp[1] == len(imp),
    "corrected_frame_hex": hx(build_frag(b"\x97\x58\x00\x1E\x00\x17\x17\x00\x00\x00\xE0\x03\x00\x00\x00", 1)),
    "corrected_note": "inserting the ordinal (0x01) makes byte1==total==20 and byte3 the ordinal",
})
vectors.append({
    "id": "REJECT-a40ad8-commit", "kind": "rejected",
    "provenance": "transcribed from baselines/imported-research/d8-test-vectors.json (commit of every V*)",
    "why_rejected": ("byte1=0x0A=10 would declare a 10-byte frame, i.e. a DATA fragment carrying 5 "
                     "payload bytes under the proven layout; the commit frame is 5 bytes total so its "
                     "length byte must be 0x05"),
    "frame_hex": hx(w0a), "length_byte": w0a[1],
    "would_len_byte_equals_total": w0a[1] == len(w0a),
    "corrected_frame_hex": hx(build_commit(2)),
})

doc = {
    "schema": "armorx-lab/d8-macro-vectors/1",
    "generated": "2026-09-27",
    "scope": "static only; no device, no radio, no APK execution",
    "framing_conventions": {
        "data_fragment": "A4 | (segLen+5) | D8 | (i+1) | seg | csum   total = segLen+5 bytes",
        "commit_frame": "A4 | 05 | D8 | (nfrags+1) | csum              total = 5 bytes",
        "checksum": "sum(all preceding bytes) & 0xFF",
        "ordinal": "1-based fragment index at frame offset 3 (present in ALL four builds)",
        "length_byte": "equals the TOTAL frame length (== payload + 5)",
        "payload_crc": "CRC-16/MODBUS init 0xFFFF poly 0xA001 over payload[2:], stored big-endian at 0..1",
        "chunk": "payload bytes per fragment; full fragments are always 20/48/72-byte A4 frames",
    },
    "format_description": {
        "note": "explicit field description (no external schema language)",
        "vector_fields": {
            "id": "string, unique",
            "kind": "framing_anchor | encode | commit | chunk_class | rejected",
            "provenance": "CAPTURED | DERIVED + citation",
            "version": "2.22.0901 | 2.23.0609 | 2.24.0919 | 4.0.8 | null",
            "family": "OLD/GamepadDefMap(7B) | MODERN/TranscribeFrame(10B) | null",
            "chunk": "int payload bytes/fragment",
            "frame(s)": "{hex, byte0, length_byte, opcode, ordinal, payload_len, total_len, len_byte_equals_total, len_byte_equals_payload_plus_5, checksum_stored, checksum_calc, checksum_ok}",
        },
        "invariants_every_vector_must_satisfy": [
            "frame[0] == 0xA4",
            "frame[1] == len(frame)              (length byte == total frame length)",
            "frame[2] == 0xD8",
            "frame[3] == fragment index (1-based); for a commit frame frame[3] == nfrags+1",
            "frame[-1] == sum(frame[:-1]) & 0xFF",
            "commit frame: len(frame)==5 and frame[1]==0x05",
        ],
    },
    "vectors": vectors,
    "summary": {
        "vector_count": len(vectors),
        "by_kind": {k: sum(1 for v in vectors if v["kind"] == k)
                    for k in sorted({v["kind"] for v in vectors})},
    },
}

path = os.path.join(OUT, "vectors", "d8-vectors.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w") as fh:
    json.dump(doc, fh, indent=2)
    fh.write("\n")

# ---- self-verification: every vector must satisfy the invariants ----
bad = []
for v in vectors:
    frs = ([v["frame"]] if "frame" in v else v.get("frames", []))
    if "commit" in v: frs = frs + [v["commit"]]
    expected_op = 0xD6 if v["kind"] == "framing_anchor" else 0xD8
    for fr in frs:
        raw = bytes.fromhex(fr["hex"])
        if raw[0] != 0xA4 or raw[2] != expected_op: bad.append((v["id"], "header/opcode"))
        if raw[1] != len(raw): bad.append((v["id"], "len!=total"))
        if raw[-1] != sum8(raw[:-1]): bad.append((v["id"], "checksum"))
        if fr.get("len_byte_equals_total") is False: bad.append((v["id"], "meta says len!=total"))
    if v["kind"] == "framing_anchor" and not v["frame"]["len_byte_equals_payload_plus_5"]:
        bad.append((v["id"], "payload+5"))
    if v["kind"] == "commit" and (len(bytes.fromhex(v["frame"]["hex"])) != 5
                                  or bytes.fromhex(v["frame"]["hex"])[1] != 0x05):
        bad.append((v["id"], "commit not A4 05 ..."))
    if v["kind"] == "rejected":
        if v["id"] == "REJECT-imported-19byte-ordinal-less":
            if v["len_byte_equals_total"]: bad.append((v["id"], "expected inconsistency"))
        if v["id"] == "REJECT-a40ad8-commit":
            if v["would_len_byte_equals_total"]: bad.append((v["id"], "A4 0A D8 89 would be a data frag"))
print("vectors:", len(vectors), "by_kind:", doc["summary"]["by_kind"])
print("invariant violations:", bad if bad else "NONE")
print("sha256:", hashlib.sha256(open(path,'rb').read()).hexdigest())
print("wrote", path)
