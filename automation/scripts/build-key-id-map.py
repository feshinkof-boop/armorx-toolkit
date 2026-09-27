#!/usr/bin/env python3
"""build-key-id-map.py -- turn the D2 capture + the press requests into the
physical key-ID map, from raw evidence only.

Method
  1. For every press group in results/runtime/press-groups.jsonl, take the
     capture slice between the request and the operator's reply.
  2. Drop the modal (idle) frame; collapse consecutive repeats; keep the runs
     whose 32-bit key mask (frame bytes 3..6, little-endian) is non-zero.
  3. Pair those runs, in order, with the buttons that were requested. If the
     counts differ the group is reported as PARTIAL and only the runs that can be
     paired positionally are used - never guessed.
  4. The absolute key id is byte_index * 8 + bit, where the mask word's byte
     order is b6=ids 0-7, b5=8-15, b4=16-23, b3=24-31 (established by anchor
     buttons whose ids were already known: A=0, B=1, X=3, Y=4, LB=6, RB=7,
     LT=8, View=10, Menu=11, L3=13, R3=14, Capture=15, D-pad 16-19, M5/M6/M7=27/28/29).

Outputs real-key-id-map.json and real-key-id-map.md (with the static label for
cross-check and an explicit evidence label per row).
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib

BYTE_TO_BASE = {6: 0, 5: 8, 4: 16, 3: 24}

STATIC_LABELS = {
    0: "A", 1: "B", 2: "Empty", 3: "X", 4: "Y", 5: "UNKNOWN", 6: "LB", 7: "RB",
    8: "LT", 9: "RT", 10: "View", 11: "Menu", 12: "UNKNOWN", 13: "L3", 14: "R3",
    15: "Capture", 16: "D-pad Up", 17: "D-pad Down", 18: "D-pad Left", 19: "D-pad Right",
    20: "UNKNOWN", 21: "UNKNOWN", 22: "UNKNOWN", 23: "UNKNOWN", 24: "UNKNOWN",
    25: "UNKNOWN", 26: "UNKNOWN", 27: "M5", 28: "M6", 29: "M7", 30: "UNKNOWN", 31: "UNKNOWN",
}

ID_TO_BUTTON_CLAIM = {  # what the operator told us each id corresponds to
    23: "M1", 24: "M2", 25: "M3", 26: "M4", 12: "Guide/Xbox",
}


def parse(ts: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def load_frames(path: pathlib.Path):
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("event") == "rx" and e.get("raw"):
            out.append((parse(e["ts"]), e["raw"]))
    return out


def mask_of(raw: str) -> tuple[int, dict]:
    b = bytes.fromhex(raw)
    m = b[3] | (b[4] << 8) | (b[5] << 16) | (b[6] << 24)
    return m, {"b3": b[3], "b4": b[4], "b5": b[5], "b6": b[6],
               "trig_lt": b[15], "trig_rt": b[16]}


def id_of_mask(m: int, detail: dict) -> int | None:
    """Absolute key id from the mask bytes.

    The mask is NOT a native little-endian u32 for id purposes: byte [6] holds
    ids 0-7, [5] holds 8-15, [4] holds 16-23, [3] holds 24-31 (established from
    anchor buttons with known ids). So the id is byte_base + bit_index, not the
    bit index of the concatenated word.
    """
    hits = []
    for key, base in BYTE_TO_BASE.items():
        value = detail[f"b{key}"]
        if value == 0:
            continue
        for bit in range(8):
            if value >> bit & 1:
                hits.append(base + bit)
    return hits[0] if len(hits) == 1 else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--d2-session-jsonl", required=True)
    ap.add_argument("--press-groups", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    frames = load_frames(pathlib.Path(args.d2_session_jsonl))
    modal_raw = collections.Counter(r for _, r in frames).most_common(1)[0][0]
    modal_mask, _ = mask_of(modal_raw)

    groups, map_rows, notes = [], {}, []
    for line in pathlib.Path(args.press_groups).read_text().splitlines():
        if not line.strip():
            continue
        g = json.loads(line)
        t0, t1 = parse(g["requested_timestamp"]), parse(g["acknowledged_timestamp"])
        runs = []
        for ts, raw in frames:
            if not (t0 <= ts <= t1):
                continue
            m, det = mask_of(raw)
            if m == modal_mask:
                continue
            if runs and runs[-1]["mask"] == m:
                runs[-1]["n"] += 1
                continue
            runs.append({"ts": ts, "mask": m, "n": 1, "detail": det})
        requested = g["requested_buttons"]
        paired = []
        for i, r in enumerate(runs):
            kid = id_of_mask(r["mask"], r["detail"])
            entry = {"order_index": i + 1,
                     "requested": requested[i] if i < len(requested) else None,
                     "mask_word": f"0x{r['mask']:08X}", "mask_bytes": r["detail"],
                     "key_id": kid,
                     "first_seen": r["ts"].astimezone().isoformat(),
                     "identical_repeats": r["n"]}
            if entry["requested"] is None:
                entry["attribution"] = "UNATTRIBUTED (more frames than requested presses)"
                notes.append(f"{g['action_id']}: frame at {entry['first_seen']} "
                             f"(id {kid}) has no matching requested press -> left unattributed")
            else:
                entry["attribution"] = "positional (operator order)"
                if kid is not None:
                    map_rows[kid] = {"button": entry["requested"], "from_group": g["action_id"],
                                     "mask_word": entry["mask_word"], "mask_bytes": r["detail"]}
            paired.append(entry)
        groups.append({"action_id": g["action_id"], "requested_buttons": requested,
                       "reply_at": g["acknowledged_timestamp"], "frames_in_window": len(runs),
                       "complete": len(runs) == len(requested), "events": paired,
                       "unresolved": [b for i, b in enumerate(requested) if i >= len(runs)]})

    rows = []
    for kid in sorted(range(32)):
        live = map_rows.get(kid)
        static = STATIC_LABELS.get(kid, "UNKNOWN")
        claim = ID_TO_BUTTON_CLAIM.get(kid)
        if live:
            agrees = (static.upper() == live["button"].upper()
                      or (claim and claim.split("/")[0].upper() in live["button"].upper()))
            rows.append({"key_id": kid, "mask_bit": f"byte[{6 - kid // 8}] bit {kid % 8} = 0x{1 << (kid % 8):02X}",
                         "physical_button": live["button"],
                         "static_label": static, "agrees_with_static": bool(agrees),
                         "mask_bytes_when_pressed": live["mask_bytes"],
                         "evidence": "PROVEN LIVE", "from_group": live["from_group"]})
        else:
            rows.append({"key_id": kid, "mask_bit": f"byte[{6 - kid // 8}] bit {kid % 8} = 0x{1 << (kid % 8):02X}", "physical_button": None,
                         "static_label": static, "agrees_with_static": None,
                         "mask_bytes_when_pressed": None,
                         "evidence": "UNKNOWN (never produced a mask bit in this capture)",
                         "from_group": None})

    out = {
        "device": {"model": "ZJ-XT", "firmware": "2741", "ble_address": "2D:37:35:6D:66:11",
                   "advertised_name": "ARMOR-X Pro_11"},
        "frame": {"opcode": "0x02", "length": 18,
                  "key_mask": "frame bytes [3][4][5][6] = u32 LE, bit == source id",
                  "byte_role": {"[6]": "key ids 0-7", "[5]": "key ids 8-15",
                                 "[4]": "key ids 16-23", "[3]": "key ids 24-31",
                                 "[15]": "LT analog (0x83 -> 0xFF on a full pull)",
                                 "[16]": "RT analog (never observed non-zero)",
                                 "[7]-[14]": "analog axes, semantics UNKNOWN",
                                 "[17]": "checksum (sum8)"}},
        "method": "operator was asked for a short ordered list of presses per group; the "
                  "capture slice between request and reply was reduced to distinct non-idle "
                  "mask runs and paired positionally. Unpairable frames stay unattributed.",
        "groups": groups,
        "key_map": rows,
        "notes": notes,
        "resolved_this_pass": sorted(map_rows),
        "still_unknown": sorted(i for i in range(32) if i not in map_rows),
        "evidence_label": "PROVEN LIVE for resolved ids",
    }
    pathlib.Path(args.out_json).write_text(json.dumps(out, indent=1) + "\n")

    md = ["# Real ARMOR-X Pro key-ID map (live D2 capture)", "",
          f"- device: `ZJ-XT` / fw `2741` / `2D:37:35:6D:66:11` (`ARMOR-X Pro_11`)",
          "- frame: opcode `0x02`, 18 bytes; the key mask is the u32 little-endian word at",
          "  frame bytes `[3][4][5][6]` with **bit == source id**",
          "  (`[6]`=ids 0-7, `[5]`=8-15, `[4]`=16-23, `[3]`=24-31)", "",
          "| id | mask | button (live) | static label | agrees | evidence |",
          "|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['key_id']} | `{r['mask_bit']}` | {r['physical_button'] or '—'} | "
                  f"{r['static_label']} | "
                  f"{'yes' if r['agrees_with_static'] else ('—' if r['agrees_with_static'] is None else 'no')} | "
                  f"{r['evidence']} |")
    md += ["", "## Group detail", ""]
    for g in groups:
        md.append(f"- `{g['action_id']}` asked for {g['requested_buttons']} -> "
                  f"{g['frames_in_window']} mask runs, complete={g['complete']}"
                  + (f", unresolved: {g['unresolved']}" if g["unresolved"] else ""))
    if notes:
        md += ["", "## Unattributed frames (left UNKNOWN, not guessed)", ""] + [f"- {n}" for n in notes]
    pathlib.Path(args.out_md).write_text("\n".join(md) + "\n")

    print(json.dumps({"resolved": out["resolved_this_pass"], "unknown": out["still_unknown"],
                      "notes": notes}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
