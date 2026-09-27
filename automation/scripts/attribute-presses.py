#!/usr/bin/env python3
"""attribute-presses.py -- attribute D2 button captures to the requested presses.

The operator is asked for a short ordered list of presses; the harness records
every notification with a timestamp. This tool slices the capture by the request
window (alert raised -> operator replied), drops the periodic idle frame, and
prints the non-idle frames in order with their inter-event spacing, so every
press is attributed by BOTH its raw bytes and its time window.

Usage:
  attribute-presses.py <d2-session.jsonl> --from <ISO> --to <ISO> \
      --expect A B X Y [--json-out FILE] [--idle-min-fraction 0.3]

Evidence discipline: an idle frame is only dropped when it dominates the *whole*
capture (fraction of all frames >= --idle-min-fraction); otherwise nothing is
dropped and the report says so.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import pathlib
import sys


def parse_iso(text: str) -> dt.datetime:
    t = text.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(t)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session_jsonl")
    ap.add_argument("--from", dest="t_from", required=True)
    ap.add_argument("--to", dest="t_to", required=True)
    ap.add_argument("--expect", nargs="*", default=[])
    ap.add_argument("--json-out")
    ap.add_argument("--idle-min-fraction", type=float, default=0.3)
    args = ap.parse_args()

    events = []
    for line in pathlib.Path(args.session_jsonl).read_text().splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        if e.get("event") != "rx" or not e.get("raw"):
            continue
        events.append({"ts": parse_iso(e["ts"]), "raw": e["raw"]})

    if not events:
        print("no rx events in the capture", file=sys.stderr)
        return 2

    total = collections.Counter(e["raw"] for e in events)
    idle_raw, idle_n = total.most_common(1)[0]
    idle_fraction = idle_n / len(events)
    idle_dropped = idle_fraction >= args.idle_min_fraction

    t0, t1 = parse_iso(args.t_from), parse_iso(args.t_to)
    window = [e for e in events if t0 <= e["ts"] <= t1]
    presses = [e for e in window if not (idle_dropped and e["raw"] == idle_raw)]

    # collapse repeats of the same frame (a held/duplicated notification)
    collapsed = []
    for e in presses:
        if collapsed and collapsed[-1]["raw"] == e["raw"]:
            collapsed[-1]["repeat"] += 1
            collapsed[-1]["ts_last"] = e["ts"]
            continue
        collapsed.append({"ts": e["ts"], "ts_last": e["ts"], "raw": e["raw"], "repeat": 1})

    report = {
        "session_jsonl": args.session_jsonl,
        "window": {"from": args.t_from, "to": args.t_to},
        "capture_frames_total": len(events),
        "idle_frame": {"raw": idle_raw, "count": idle_n, "fraction": round(idle_fraction, 3),
                       "dropped": idle_dropped},
        "window_frames": len(window),
        "press_candidates": len(collapsed),
        "expected_buttons": args.expect,
        "attribution_complete": len(collapsed) == len(args.expect),
        "events": [
            {"index": i + 1,
             "button": args.expect[i] if i < len(args.expect) else None,
             "raw": c["raw"], "raw_len": len(c["raw"]) // 2,
             "first_seen": c["ts"].astimezone().isoformat(),
             "last_seen": c["ts_last"].astimezone().isoformat(),
             "identical_repeats": c["repeat"],
             "delta_s_from_previous": round((c["ts"] - collapsed[i - 1]["ts"]).total_seconds(), 2)
                                      if i else None}
            for i, c in enumerate(collapsed)
        ],
    }
    print(json.dumps(report, indent=1))
    if args.json_out:
        pathlib.Path(args.json_out).write_text(json.dumps(report, indent=1) + "\n")
    return 0 if report["attribution_complete"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
