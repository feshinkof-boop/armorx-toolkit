#!/usr/bin/env python3
"""fw_ledger_report.py - render results/reconciliation/firmware-unknown-ledger.json to markdown.

Deterministic: the markdown is built only from the JSON, so the two can never disagree.
"""
from __future__ import annotations
import json, pathlib, sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SRC = REPO / "results" / "reconciliation" / "firmware-unknown-ledger.json"
DST = REPO / "results" / "reconciliation" / "firmware-unknown-ledger.md"


def main() -> int:
    d = json.loads(SRC.read_text())
    ent = d["entries"]
    counts: dict[str, int] = {}
    for e in ent:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    out = ["# Firmware unknown ledger", "",
           f"Generated from `{SRC.relative_to(REPO)}` by `tools/firmware/fw_ledger_report.py`.",
           "", f"Scope: {d.get('scope','')}", "",
           "| id | status | priority | question |", "|---|---|---|---|"]
    for e in sorted(ent, key=lambda e: e["id"]):
        out.append(f"| {e['id']} | {e['status']} | {e.get('priority','-')} | {e['question']} |")
    out += ["", "## Counts", ""]
    for k, v in sorted(counts.items()):
        out.append(f"- {k}: {v}")
    out += ["", "## Entries", ""]
    for e in sorted(ent, key=lambda e: e["id"]):
        out += [f"### {e['id']} - {e['question']}", "",
                f"**Status:** {e['status']} | **Priority:** {e.get('priority','-')}", "",
                f"**Answer:** {e.get('answer','')}", ""]
        if e.get("evidence"):
            out.append("**Evidence:**"); out.append("")
            for ev in e["evidence"]:
                out.append(f"- {ev}")
            out.append("")
        if e.get("ruled_out"):
            out.append("**Ruled out:** " + "; ".join(e["ruled_out"])); out.append("")
        if e.get("next_offline_step"):
            out.append(f"**Next offline step:** {e['next_offline_step']}"); out.append("")
    DST.write_text("\n".join(out) + "\n")
    print(f"wrote {DST.relative_to(REPO)} ({len(ent)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
