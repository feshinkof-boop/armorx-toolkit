#!/usr/bin/env python3
"""parse_btsnoop.py - extract ATT frames from HCI btsnoop captures, with no prose in between.

The ArmorX protocol frames are ATT Write Command (0x52) / Write Request (0x12) payloads on the write
characteristic (FFE1 / handle 0x0075) and ATT Handle Value Notification (0x1B) payloads on FFE2
(handle 0x0077). This tool walks the raw btsnoop records and emits exactly what was on the wire.

btsnoop record layout (RFC-ish, Symbian/BlueZ flavour):

    file header: "btsnoop\\0" + version(4) + datalink(4) + pad(8)   -> 16 bytes
    record:      orig_len(4) incl_len(4) ts_usec(8) flags(4) data(incl_len)
    flags bit0:  0 = sent (host->controller), 1 = received

HCI ACL data: handle_and_flags(2) + total_len(2) + payload. For a non-flush packet the payload is
L2CAP: length(2) + cid(2) + data. cid 0x0004 = ATT.

Usage:
  parse_btsnoop.py <capture-or-dir>... [--opcode D6,D7,...] [--json out.json]
Prints one line per frame: capture<TAB>dir<TAB>time<TAB>att<TAB>handle<TAB>hex
"""
from __future__ import annotations

import argparse
import json
import pathlib
import struct
import sys
from datetime import datetime, timezone

ATT_WRITE_CMD = 0x52
ATT_WRITE_REQ = 0x12
ATT_NOTIFY = 0x1B
ATT_INDICATE = 0x1D
L2CAP_CID_ATT = 0x0004


def records(path: pathlib.Path):
    b = path.read_bytes()
    if not b.startswith(b"btsnoop\x00"):
        return
    pos = 16
    while pos + 24 <= len(b):
        # btmon writes the Symbian/BlueZ record shape: orig_len, incl_len, flags, drops, ts(usec)
        orig, incl, flags, drops, ts = struct.unpack_from(">IIIIq", b, pos)
        pos += 24
        data = b[pos:pos + incl]
        pos += incl
        yield ts, flags, data


def att_frames(path: pathlib.Path):
    """Yield (ts, direction, att_opcode, handle, payload) for ATT traffic."""
    for ts, flags, data in records(path):
        direction = "R" if (flags & 1) else "T"          # R = received by host, T = transmitted
        if len(data) < 5:
            continue
        hci = struct.unpack_from("<H", data, 0)[0]
        pb = (hci >> 12) & 0x3
        if pb not in (0x2, 0x0):                          # first fragment of an L2CAP PDU
            continue
        acl_len = struct.unpack_from("<H", data, 2)[0]
        body = data[4:4 + acl_len]
        if len(body) < 4:
            continue
        l2_len, cid = struct.unpack_from("<HH", body, 0)
        if cid != L2CAP_CID_ATT:
            continue
        att = body[4:4 + l2_len]
        if len(att) < 3:
            continue
        op = att[0]
        if op in (ATT_WRITE_CMD, ATT_WRITE_REQ, ATT_NOTIFY, ATT_INDICATE):
            handle = struct.unpack_from("<H", att, 1)[0]
            yield ts, direction, op, handle, att[3:]


def is_protocol_frame(p: bytes) -> bool:
    return len(p) >= 3 and p[0] in (0xA5, 0xA4, 0xAB)


def walk(paths: list[pathlib.Path]):
    for p in paths:
        files = sorted(p.rglob("*.btsnoop")) if p.is_dir() else [p]
        for f in files:
            for ts, direction, op, handle, payload in att_frames(f):
                if is_protocol_frame(payload):
                    yield f, ts, direction, op, handle, payload


def fmt_ts(ts: int) -> str:
    """BlueZ/btmon writes microseconds; calibrate the epoch by requiring a plausible year."""
    for offset in (0, 946684800):                         # unix epoch, then the 2000-01-01 base
        try:
            dt = datetime.fromtimestamp(ts / 1e6 + offset, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            continue
        if 2015 <= dt.year <= 2035:
            return dt.isoformat()
    return str(ts)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--opcode", default="")
    ap.add_argument("--family", default="")
    ap.add_argument("--json")
    a = ap.parse_args(argv[1:])
    wanted = {int(x, 16) for x in a.opcode.split(",") if x}
    rows = []
    for f, ts, direction, op, handle, payload in walk([pathlib.Path(x) for x in a.paths]):
        if wanted and payload[2] not in wanted:
            continue
        if a.family and chr(payload[0]) != a.family:
            continue
        rows.append(dict(capture=str(f), time=fmt_ts(ts), dir=direction,
                         att=f"{op:#04x}", handle=f"{handle:#06x}",
                         magic=f"{payload[0]:02x}", length=payload[1],
                         opcode=f"{payload[2]:02x}", hex=payload.hex(" ")))
    for r in rows:
        print(f"{r['capture']}\t{r['dir']}\t{r['time']}\t{r['att']}\t{r['handle']}\t{r['hex']}")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(rows, indent=1) + "\n")
    print(f"# {len(rows)} protocol frames", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
