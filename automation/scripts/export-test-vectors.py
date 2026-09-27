#!/usr/bin/env python3
"""export-test-vectors.py -- build tests/vectors/real-device-vectors.json from the
REAL capture files, so the regression suite never relies on hand-typed byte
strings (a hand-typed baseline is a fabricated baseline).

Sources:
  * the immutable D6 baseline  -> baselines/device/<id>/baseline-as-found.bin
  * every single-bit status frame observed during the live D2 press groups
  * the live read-only replies (0B / EF / D4 / E2) from the live session's
    ble/*.jsonl

Output: tests/vectors/real-device-vectors.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib

BYTE_BASE = {6: 0, 5: 8, 4: 16, 3: 24}
WANT_OPCODES = {0x0B, 0xEF, 0xD4, 0xE2, 0xD7}


def parse(ts: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def ids_of(raw: bytes) -> list[int]:
    if len(raw) < 18 or raw[2] != 0x02:
        return []
    out = []
    for byte_idx, base in BYTE_BASE.items():
        val = raw[byte_idx]
        for bit in range(8):
            if val >> bit & 1:
                out.append(base + bit)
    return out


def iter_rx(path: pathlib.Path):
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("event") == "rx" and e.get("raw"):
            try:
                yield parse(e["ts"]), bytes.fromhex(e["raw"])
            except (ValueError, KeyError):
                continue


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--d2-session-jsonl", required=True)
    ap.add_argument("--press-groups", required=True)
    ap.add_argument("--live-session-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = pathlib.Path(args.baseline).read_bytes()

    groups = {}
    for line in pathlib.Path(args.press_groups).read_text().splitlines():
        if line.strip():
            g = json.loads(line)
            groups[g["action_id"]] = g

    frames, seen_raw = [], set()
    for group_id, g in groups.items():
        t0 = parse(g["requested_timestamp"])
        t1 = parse(g["acknowledged_timestamp"]) + dt.timedelta(seconds=20)
        for ts, raw in iter_rx(pathlib.Path(args.d2_session_jsonl)):
            if not (t0 <= ts <= t1):
                continue
            ids = ids_of(raw)
            if not ids or raw.hex() in seen_raw:
                continue
            seen_raw.add(raw.hex())
            frames.append({"raw": raw.hex(), "ids": ids, "group": group_id,
                           "observed_at": ts.isoformat()})

    replies = {}
    for jf in sorted(pathlib.Path(args.live_session_dir).rglob("*.jsonl")):
        for _, raw in iter_rx(jf):
            if len(raw) >= 3 and raw[0] == 0xA5 and raw[2] in WANT_OPCODES:
                replies.setdefault(f"opcode_0x{raw[2]:02X}", []).append(
                    {"raw": raw.hex(), "source": str(jf.relative_to(pathlib.Path(args.live_session_dir)))})

    out = {
        "generated_from": {"baseline": args.baseline, "d2_session": args.d2_session_jsonl,
                           "live_session": args.live_session_dir},
        "baseline": {"sha256": hashlib.sha256(base).hexdigest(), "length": len(base),
                     "declared_length": int.from_bytes(base[2:4], "big"),
                     "byte127_source_slot_15": base[127],
                     "hex": base.hex()},
        "status_frames": frames,
        "replies": replies,
        "note": "vectors exported from real captures; do not hand-edit",
    }
    op = pathlib.Path(args.out)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"baseline_sha256": out["baseline"]["sha256"],
                      "status_frames": len(frames),
                      "opcodes": {k: len(v) for k, v in replies.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
