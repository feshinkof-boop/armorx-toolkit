#!/usr/bin/env python3
"""armorx_bup.py - offline parser/unpacker for BigBigWon "Upgrade Pack" (.bup) containers.

Format (reverse-engineered 2026-09-28, read-only):

  offset  size  field
  0x00    22    b"BigBigWon Upgrade Pack" + 2 NULs
  0x16     4    u32 LE  = 0x00010000 (format revision 1.0)
  0x1A     1    0x01
  0x1B     4    u32 LE  board/model code, low byte 0x01: 0x001d0100 -> V41, 0x001e0100 -> dongle V3600,
                         0x00160100 -> V32, 0x00170100 -> dongle V3000, 0x00000100 -> V2224
  0x21     4    ASCII board version string ("V41", "V32", "2224", ...)
  0x2B    32    image slot A name, NUL padded ("null.bin" when the slot is empty)
  0x5B    32    image slot B name, NUL padded
  ...      1    zero padding
  then, for each slot: a small u32 header (compressed size, uncompressed size)
  then        payload = a sequence of INDEPENDENT zlib streams, each inflating to
              0x8000 (32768) bytes, stored back to back.  The stream walk is
              self-synchronising: zlib reports unused_data, so the next chunk starts
              at off + (len - len(unused_data)).

Usage:
  armorx_bup.py info  <file.bup> [...]
  armorx_bup.py unpack <file.bup> <outdir>       # writes <slotname>.bin + a JSON sidecar
  armorx_bup.py walk  <file.bup>                 # chunk table only

Read-only: never writes to the input, never needs a device.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import sys
import zlib

MAGIC = b"BigBigWon Upgrade Pack"
CHUNK = 0x8000
SLOT_A = 0x2B
SLOT_B = 0x5B
NAME_LEN = 32


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_header(data: bytes) -> dict:
    if data[:len(MAGIC)] != MAGIC:
        raise ValueError(f"not a BigBigWon Upgrade Pack (magic={data[:22]!r})")
    fmt_rev = struct.unpack_from("<I", data, 0x16)[0]
    board_code = struct.unpack_from("<I", data, 0x1B)[0]
    version = data[0x21:0x25].rstrip(b"\0").decode("latin1")
    slot_a = data[SLOT_A:SLOT_A + NAME_LEN].split(b"\0")[0].decode("latin1")
    slot_b = data[SLOT_B:SLOT_B + NAME_LEN].split(b"\0")[0].decode("latin1")
    return {
        "magic": MAGIC.decode(),
        "format_revision": f"0x{fmt_rev:08x}",
        "board_code": f"0x{board_code:08x}",
        "board_code_raw": data[0x1B:0x1F].hex(),
        # the product identifier is the byte at 0x1D; 0x1B/0x1C/0x1E are constant
        # (00 01 ?? 00): 0x1d = ArmorX Pro body, 0x1e = V3600 dongle, 0x16 = V32,
        # 0x17 = V3000 dongle, 0x00 = V2224.
        "board_code_id": data[0x1D],
        "board_code_low": board_code & 0xFF,
        "board_code_model": (board_code >> 8) & 0xFF,
        "version_string": version,
        "slot_a_name": slot_a,
        "slot_b_name": slot_b,
    }


def find_first_record(data: bytes, start: int = 0x60) -> int:
    """First offset holding a (compressed, uncompressed) u32 pair followed by a zlib stream.

    A candidate is accepted only if the stream actually inflates to the declared length —
    the header's own span field can otherwise masquerade as a record pair.
    """
    for off in range(start, min(len(data) - 10, start + 0x400)):
        comp, unc = struct.unpack_from("<II", data, off)
        if not (8 <= comp <= 0x40000 and 0 < unc <= 0x20000):
            continue
        if data[off + 8:off + 10] != b"\x78\x9c":
            continue
        try:
            if len(zlib.decompress(data[off + 8:off + 8 + comp])) == unc:
                return off
        except zlib.error:
            continue
    raise ValueError("no chunk record found in the header region")


def walk_chunks(data: bytes, pos: int) -> tuple[bytes, list[dict]]:
    """Walk the (compressed, uncompressed) record sequence; returns (image, chunk table)."""
    out = bytearray()
    table: list[dict] = []
    while pos + 8 <= len(data):
        comp, unc = struct.unpack_from("<II", data, pos)
        # sanity bounds: refuse anything that is not a plausible zlib block record
        if not (8 <= comp <= 0x40000 and 0 < unc <= 0x20000) or pos + 8 + comp > len(data):
            break
        try:
            chunk = zlib.decompress(data[pos + 8:pos + 8 + comp])
        except zlib.error:
            break
        if len(chunk) != unc:
            break
        table.append({"record_offset": pos, "compressed": comp, "uncompressed": unc,
                      "sha256": sha256(chunk)})
        out += chunk
        pos += 8 + comp
    return bytes(out), table


def analyze(path: pathlib.Path) -> tuple[dict, list[tuple[str, bytes]], list[dict]]:
    """Returns (header info, [(slot_name, image_bytes)], chunk table of slot A)."""
    data = path.read_bytes()
    hdr = parse_header(data)
    first = find_first_record(data)
    # the header holds a u32 span for slot A just before the first record
    span_a, = struct.unpack_from("<I", data, first - 4)
    img_a, table = walk_chunks(data, first)
    hdr.update({
        "file": str(path),
        "file_size": len(data),
        "first_record_offset": first,
        "slot_a_span": span_a,
        "slot_a_span_matches": (first - 4) + 4 + span_a <= len(data),
        "chunk_count": len(table),
        "image_size": len(img_a),
        "image_sha256": sha256(img_a),
    })
    images = [(hdr["slot_a_name"], img_a)]
    # slot B, if the header declares another span after slot A
    pos_b = first + span_a
    if pos_b + 4 <= len(data):
        span_b, = struct.unpack_from("<I", data, pos_b)
        if 8 <= span_b <= len(data) - pos_b - 4:
            try:
                img_b, _ = walk_chunks(data, pos_b + 4)
                if img_b:
                    images.append((hdr["slot_b_name"], img_b))
                    hdr["slot_b_span"] = span_b
            except ValueError:
                pass
    hdr["slots_with_data"] = [n for n, i in images if i]
    return hdr, images, table


def _entropy(b: bytes) -> float:
    import collections
    import math
    if not b:
        return 0.0
    c = collections.Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd in ("walk", "info"):
        for f in argv[2:]:
            hdr, images, table = analyze(pathlib.Path(f))
            hdr["chunks"] = len(table)
            hdr["slots"] = [{"name": n, "size": len(i), "sha256": sha256(i)} for n, i in images]
            print(json.dumps(hdr, indent=2))
        return 0
    if cmd == "unpack":
        src = pathlib.Path(argv[2])
        outdir = pathlib.Path(argv[3])
        outdir.mkdir(parents=True, exist_ok=True)
        hdr, images, table = analyze(src)
        written = []
        for idx, (name, image) in enumerate(images):
            tag = pathlib.Path(name).stem if name else f"slot{idx}"
            dst = outdir / f"{src.stem}__slot{idx}_{tag}.image.bin"
            dst.write_bytes(image)
            written.append(str(dst))
            print(f"{src.name} slot{idx} {name!r} -> {dst.name}  ({len(image):,} B, sha256 {sha256(image)[:16]})")
        (outdir / f"{src.stem}.unpack.json").write_text(json.dumps({**hdr, "chunks": table}, indent=2) + "\n")
        return 0 if written else 1
    print(f"unknown command {cmd!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
