#!/usr/bin/env python3
"""Audit a real harness session record and report what it actually proves.

Why this exists
---------------
The project carried a conclusion - "OFFICIAL_WORKS_HARNESS_SILENT" - that compared an official
Android window in which a physical press WAS requested against harness windows in which no press
was ever requested. Under the corrected event-driven model that comparison cannot distinguish
"the device stayed silent" from "nothing was pressed", so it is not evidence about the device.

The harness's own 2026-09-27 17:08 session record proves the harness receives button frames
normally. This script re-derives that from the raw record rather than trusting the prose, and
reports the control plane, the frame counts, the key ids and whether a press was requested.

Usage:
    harness-streaming-audit.py <session.jsonl> [--json out.json]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

BUTTON_HEADER = "a51202"


def audit(path: str) -> dict:
    recs = [json.loads(l) for l in pathlib.Path(path).read_text(errors="replace").splitlines() if l.strip()]
    tx = [r for r in recs if r.get("event") == "tx"]
    rx = [r for r in recs if r.get("event") == "rx"]

    def raw(r) -> str:
        return str(r.get("raw") or r.get("hex") or "").lower()

    buttons = [r for r in rx if raw(r).startswith(BUTTON_HEADER)]
    masks = collections.Counter(raw(r)[6:14] for r in buttons)
    ids = collections.Counter()
    for m, n in masks.items():
        for i in range(32):
            if int(m, 16) >> i & 1:
                ids[i] += n

    lengths = collections.Counter(len(raw(r)) // 2 for r in buttons)
    checks = collections.Counter(bool(r.get("checksum_ok")) for r in buttons)

    # a pre-clear is a D2-OFF write issued BEFORE the D2 enable, not the normal trailing disable
    planes = [raw(r) for r in tx]
    enable_at = planes.index("a505d2017d") if "a505d2017d" in planes else None
    pre_clear = bool(enable_at is not None and any(f.startswith("a505d200") for f in planes[:enable_at]))

    return {
        "session": path,
        "records": len(recs),
        "control_plane": [{"ts": r.get("ts"), "frame": raw(r), "label": r.get("label")} for r in tx],
        "d2_enable_preceded_by_pre_clear": pre_clear,
        "rx_records": len(rx),
        "button_frames": len(buttons),
        "button_frame_lengths": dict(lengths),
        "checksums_all_valid": len(checks) == 1 and True in checks,
        "zero_mask_frames": masks.get("00000000", 0),
        "nonzero_mask_frames": sum(n for m, n in masks.items() if m != "00000000"),
        "key_ids_seen": dict(sorted(ids.items())),
        "key_id_count": len(ids),
        "first_button_frame": raw(buttons[0]) if buttons else None,
        "last_button_frame": raw(buttons[-1]) if buttons else None,
        "first_button_ts": buttons[0].get("ts") if buttons else None,
        "last_button_ts": buttons[-1].get("ts") if buttons else None,
        "press_evidence_in_window": bool(buttons),
        "conclusion": ("harness_receives_button_frames" if buttons else
                       "no_press_was_observed_in_this_window__not_evidence_of_device_silence"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("session")
    ap.add_argument("--json")
    a = ap.parse_args()
    out = audit(a.session)
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
