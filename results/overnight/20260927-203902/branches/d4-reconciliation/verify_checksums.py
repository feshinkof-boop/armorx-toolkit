#!/usr/bin/env python3
"""
D4 evidence reconciliation — arithmetic checksum verification + matrix build.
Read-only over existing evidence; writes only into this output dir.
Frame convention (as proven by the corpus): A5 <LEN> <OP> <payload...> <CKS>,
  LEN   = TOTAL frame length in bytes (evidence: every A5/A4 frame has LEN == len(frame))
  CKS   = sum(frame_bytes[:-1]) & 0xFF
"""
import json, os, hashlib

OUT = "/home/salamanka/armorx-lab/results/overnight/20260927-203902/branches/d4-reconciliation"

def cks(frame_bytes):
    return sum(frame_bytes[:-1]) & 0xFF

def parse(h):
    h = h.replace(" ", "").replace("0x", "")
    return [int(h[i:i+2], 16) for i in range(0, len(h), 2)]

# (id, hex, recorded_cks or None, note, provenance)
FRAMES = [
    # ---- D4 requests ----
    ("D4-REQ", "a504d47d", 0x7D, "D4 request (all builds)", "static: 2.22/2.23/2.24/4.0.8 Blutter; live: 2.22 AVD virtual; live: 4.0.8 official HCI snoop; live: Linux harness x3 physical"),
    # ---- D4 replies: virtual (constructed) ----
    ("D4-REP-VIRT-DEFAULT", "a506d400007f", 0x7F, "virtual peripheral default reply (chosen state 0x00/0x00)", "live: 2.22 AVD vs virtual_armorx.py; also frozen in manifests & docs"),
    ("D4-REP-TV-1", "a506d4060388", 0x88, "static test vector g=6 o=3 (never on wire)", "constructed test vector d4-reconstruction.json"),
    ("D4-REP-TV-2", "a506d4060085", 0x85, "static test vector g=6 o=0 (never on wire)", "constructed test vector d4-reconstruction.json"),
    ("D4-REP-TV-3", "a506d4010181", 0x81, "static test vector g=1 o=1 (never on wire)", "constructed test vector d4-reconstruction.json"),
    ("D4-REP-BADCKSUM", "a506d4000080", 0x80, "2.22 robustnes probe: deliberately wrong checksum", "live: 2.22 AVD virtual, reply_mode=bad-checksum"),
    ("D4-REP-TRUNCATED", "a504d400", None, "2.22 robustnes probe: truncated 4-byte reply (no checksum)", "live: 2.22 AVD virtual, reply_mode=truncated"),
    # ---- D4 replies: REAL hardware ----
    ("D4-REP-REAL", "a507d411010092", 0x92, "REAL device D4 reply (g=0x11 o=0x01 extra=0x00)", "live: 4.0.8 official HCI snoop (logcat prints 板载mode = 1); live: Linux harness physical x3 (162448/165347/174445); frozen vector tests/vectors/real-device-vectors.json"),
    # ---- reference anchors (framing / length convention) ----
    ("0B-REQ", "a5040bb4", 0xB4, "0B liveness query", "live official + physical"),
    ("0B-REP", "a5050b30e5", 0xE5, "0B reply (version byte 0x30)", "live official + physical"),
    ("EF-REQ", "a50cef0000000000000000a0", 0xA0, "EF uuid query (zeroed)", "live official + physical"),
    ("EF-REP", "a50cefbb921542f21f55802a", 0x2A, "EF uuid reply (8 raw bytes)", "live official + physical"),
    ("E2-REQ", "a504e28b", 0x8B, "E2 firmware query (4.0.8 only)", "live official"),
    ("E2-REP", "a510e22741025a4a2d5854000000007e", 0x7E, "E2 reply: BCD fw 2741 + model ZJ-XT", "live official + physical"),
    ("D6-REQ", "a504d67f", 0x7F, "D6 config read request", "live official + physical"),
    ("D7-ACK", "a505d70081", 0x81, "D7 write ack (documented)", "static/documented"),
    ("D8-COMMIT-NEW", "a405d80384", 0x84, "D8 commit frame, CORRECTED length byte 0x05 (was 0x0A)", "static corrected by Smi audit"),
    ("D2-ENABLE", "a505d2017d", 0x7D, "D2 test-mode enable (Button Test entry)", "live official + physical"),
    ("D2-DISABLE", "a505d2007c", 0x7C, "D2 test-mode disable", "live official + physical"),
    ("D2-BUTTON", "a5120200000001fd6500b6fc4f0158000076", 0x76, "D2 status frame (A pressed)", "live official HCI snoop"),
    ("D6-FRAG1", "a414d6012c40009033ff000000000000000000bd", 0xBD, "D6 config fragment 1/10", "live physical 162448"),
    ("D6-FRAG2", "a414d602000000000001001e1e4646000001005a", 0x5A, "D6 config fragment 2/10", "live physical 162448"),
    ("D6-FRAG10", "a40ed60a010d191a1b1c1d1e1f64", 0x64, "D6 config fragment 10/10 (last)", "live physical 162448"),
]

rows = []
mismatches = []
for fid, h, rec, note, prov in FRAMES:
    b = parse(h)
    LEN = b[1]
    total = len(b)
    comp = cks(b) if rec is not None else None
    if rec is None:
        status = "N/A (no checksum byte)"
    elif comp == rec:
        status = "MATCH"
    else:
        status = "MISMATCH"
        mismatches.append((fid, h, rec, comp))
    rows.append({
        "id": fid, "hex": " ".join(f"{x:02X}" for x in b),
        "len_byte": LEN, "total_bytes": total, "len_byte_is_total": LEN == total,
        "recomputed_cks": (f"0x{comp:02X}" if comp is not None else None),
        "recorded_cks": (f"0x{rec:02X}" if rec is not None else None),
        "status": status, "note": note, "provenance": prov,
    })

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "checksums-raw.json"), "w") as f:
    json.dump({"convention": "A5 <LEN> <OP> <payload> <CKS>; LEN==total frame length; CKS=sum(bytes[:-1])&0xFF",
               "rows": rows, "mismatches": [{"id": m[0], "hex": m[1], "recorded": f"0x{m[2]:02X}", "recomputed": f"0x{m[3]:02X}"} for m in mismatches]}, f, indent=2)

print("FRAMES:", len(rows))
print("MISMATCHES:", len(mismatches))
for m in mismatches:
    print("  ", m[0], m[1], f"recorded=0x{m[2]:02X}", f"recomputed=0x{m[3]:02X}")
print("LEN!=total rows:", [r["id"] for r in rows if not r["len_byte_is_total"]])
