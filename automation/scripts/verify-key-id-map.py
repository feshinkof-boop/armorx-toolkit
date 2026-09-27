#!/usr/bin/env python3
"""verify-key-id-map.py -- build the live key-ID map by VERIFYING explicit claims.

Why not positional pairing: the operator does not always press exactly what was
asked, in the exact order, inside the exact window (repeat presses, a skipped
button, a button that never registers). Pairing frames to presses by position
then silently mislabels ids.

Instead each claim {button, id, group} must be corroborated by the capture:
inside that group's request window there must be at least one frame whose key
mask has EXACTLY that bit set (single-bit masks only). A claim that is not
corroborated is reported as NOT VERIFIED and excluded from the map.

The key mask lives in frame bytes [3][4][5][6] of the opcode 0x02 status frame,
with byte [6] = ids 0-7, [5] = 8-15, [4] = 16-23, [3] = 24-31 and bit == id.

Usage:
  verify-key-id-map.py --d2-session-jsonl F --claims F --out-json F --out-md F
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib

BYTE_BASE = {6: 0, 5: 8, 4: 16, 3: 24}

# The operator sometimes finishes a press a few seconds after they reply (the
# helper stamps the ack when IT runs, not when the message was sent). Evidence is
# collected with a bounded grace window, and each such frame is flagged, so the
# reader can see exactly how tight the match is.
GRACE_SECONDS = 20


def parse(ts: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def frame_bits(raw: str) -> tuple[list[int], dict]:
    b = bytes.fromhex(raw)
    # only the 18-byte opcode 0x02 status frame carries the key mask
    if len(b) < 18 or b[2] != 0x02:
        return [], {}
    detail = {"b3": b[3], "b4": b[4], "b5": b[5], "b6": b[6],
              "lt_analog": b[15], "rt_analog": b[16]}
    ids = []
    for byte_idx, base in BYTE_BASE.items():
        value = detail[f"b{byte_idx}"]
        for bit in range(8):
            if value >> bit & 1:
                ids.append(base + bit)
    return ids, detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2-session-jsonl", required=True)
    ap.add_argument("--claims", required=True)
    ap.add_argument("--press-groups", default=None)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    frames = []
    for line in pathlib.Path(args.d2_session_jsonl).read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("event") == "rx" and e.get("raw"):
            frames.append((parse(e["ts"]), e["raw"], *frame_bits(e["raw"])))
    modal_raw = collections.Counter(f[1] for f in frames).most_common(1)[0][0]

    groups = {}
    if args.press_groups:
        for line in pathlib.Path(args.press_groups).read_text().splitlines():
            if line.strip():
                g = json.loads(line)
                groups[g["action_id"]] = g

    claims_doc = json.loads(pathlib.Path(args.claims).read_text())
    rows, rejected = {}, []
    for claim in claims_doc["claims"]:
        gid, kid = claim["group"], claim["id"]
        g = groups.get(gid)
        evidence = []
        if g:
            t0 = parse(g["requested_timestamp"])
            t1 = parse(g["acknowledged_timestamp"]) + dt.timedelta(seconds=GRACE_SECONDS)
            for ts, raw, ids, detail in frames:
                if not (t0 <= ts <= t1):
                    continue
                if ids == [kid]:
                    evidence.append({"ts": ts.astimezone().isoformat(), "raw": raw,
                                     "mask_bytes": detail,
                                     "after_recorded_reply": ts > parse(g["acknowledged_timestamp"])})
        if evidence:
            rows[kid] = {**claim, "evidence": "PROVEN LIVE",
                         "corroborating_frames": len(evidence),
                         "first_evidence": evidence[0], "last_evidence": evidence[-1],
                         "window": {"from": g["requested_timestamp"], "to": g["acknowledged_timestamp"]}}
        else:
            rejected.append({**claim, "evidence": "NOT VERIFIED",
                             "reason": "no single-bit frame with this id inside the group window"})

    # observations that are real but unattributed (id 20 in group F, group B repeats)
    observations = []
    for gid, g in groups.items():
        t0, t1 = parse(g["requested_timestamp"]), parse(g["acknowledged_timestamp"])
        seen = []
        for ts, raw, ids, detail in frames:
            if not (t0 <= ts <= t1) or not ids:
                continue
            key = tuple(ids)
            if seen and seen[-1]["ids"] == list(key):
                seen[-1]["repeats"] += 1
                continue
            seen.append({"ids": list(key), "ts": ts.astimezone().isoformat(), "repeats": 1,
                         "mask_bytes": detail})
        observations.append({"group": gid, "requested": g.get("requested_buttons"),
                             "distinct_single_bit_events": seen})

    out = {
        "device": {"model": "ZJ-XT", "firmware": "2741", "ble_address": "2D:37:35:6D:66:11",
                   "advertised_name": "ARMOR-X Pro_11"},
        "capture": {"session_jsonl": args.d2_session_jsonl, "frames": len(frames),
                    "modal_idle_frame": modal_raw},
        "frame_layout": {
            "opcode": "0x02", "length": 18,
            "key_mask_bytes": "[3][4][5][6] -> ids 24-31 / 16-23 / 8-15 / 0-7 (bit == source id)",
            "lt_analog_byte": "[15] (0x83 -> 0xFF on a full pull)", "rt_analog_byte": "[16]",
            "analog_axis_bytes": "[7]-[14] semantics UNKNOWN", "checksum_byte": "[17] sum8"},
        "method": "explicit claims verified against the capture (single-bit mask inside the "
                  "group's request window); positional pairing is deliberately NOT used",
        "verified_map": {str(k): v for k, v in sorted(rows.items())},
        "rejected_claims": rejected,
        "grace_window_seconds": GRACE_SECONDS,
        "unresolved": claims_doc.get("unresolved_by_request", {}),
        "group_observations": observations,
        "resolved_ids": sorted(rows),
        "still_unknown_ids": [i for i in range(32) if i not in rows],
    }
    pathlib.Path(args.out_json).write_text(json.dumps(out, indent=1) + "\n")

    md = ["# Real ARMOR-X Pro key-ID map (live D2 capture, claim-verified)", "",
          "Frame `opcode 0x02`, 18 bytes. Key mask = bytes `[3][4][5][6]` with **bit == source id**",
          "(`[6]`→ids 0-7, `[5]`→8-15, `[4]`→16-23, `[3]`→24-31). Every row below is corroborated",
          "by a capture frame with exactly that bit set, inside the window of the request that",
          "asked for that button.", "",
          "| id | mask | physical button (live) | static label | evidence | frames |",
          "|---|---|---|---|---|---|"]
    for kid, r in sorted(rows.items()):
        byte_idx = 6 - kid // 8   # [6]=ids0-7 [5]=8-15 [4]=16-23 [3]=24-31
        md.append(f"| {kid} | byte[{byte_idx}] bit {kid % 8} = `0x{1 << (kid % 8):02X}` | "
                  f"{r['button']} | {r['static']} | PROVEN LIVE | {r['corroborating_frames']} |")
    md += ["", f"Resolved ids ({len(rows)}): `{sorted(rows)}`", "",
           f"Still UNKNOWN after this pass: `{[i for i in range(32) if i not in rows]}`", ""]
    if rejected:
        md += ["## NOT VERIFIED claims (excluded from the map)", ""]
        md += [f"- id {r['id']} / {r['button']} ({r['group']}): {r['reason']}" for r in rejected]
    md += ["", "## What could not be resolved", ""]
    for k, v in claims_doc.get("unresolved_by_request", {}).items():
        md.append(f"- **{k}**: {v}")
    pathlib.Path(args.out_md).write_text("\n".join(md) + "\n")

    print(json.dumps({"resolved_ids": sorted(rows), "rejected": [r["button"] for r in rejected],
                      "still_unknown": out["still_unknown_ids"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
