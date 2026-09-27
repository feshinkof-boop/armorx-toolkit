#!/usr/bin/env python3
"""Write the canonical four-way-matrix fields into each per-build manifest, from the reconciliation
outputs, then regenerate the matrix.

The matrix (scripts/compare_versions.py) reads named fields; this script is the only place that
decides how a reconciliation artefact maps onto them, so the mapping is auditable in one file.

Inputs (all optional; absent input => the field is left untouched and the matrix keeps saying
UNKNOWN, so "not checked" never silently becomes "absent"):
  results/reconciliation/e2-ab-summary.json   -> e2, ab_family, dpi_timeline
  results/reconciliation/d8-taxonomy.json     -> d8_format, d8_commit_frame, d8_readback
  results/reconciliation/d4-reconstruction.json -> d4_request, d4_reply, d4_semantics
  results/reconciliation/smi-audit.json       -> key_mask_rule + the corrected-constant ledger
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

LAB = "/home/salamanka/armorx-lab"
VERSIONS = ["2.22.0901", "2.23.0609", "2.24.0919", "4.0.8"]
MANIFEST_FILE = {"2.22.0901": "2.22.0901.json", "2.23.0609": "2.23.json",
                 "2.24.0919": "2.24.json", "4.0.8": "4.0.8.json"}


def load(name):
    p = os.path.join(LAB, "results/reconciliation", name)
    if not os.path.isfile(p):
        print(f"MISSING {p}", file=sys.stderr)
        return None
    with open(p) as fh:
        return json.load(fh)


def main() -> int:
    e2ab = load("e2-ab-summary.json")
    d8 = load("d8-taxonomy.json")
    d4 = load("d4-reconstruction.json")
    smi = load("smi-audit.json")

    # acks for the run log
    for v in VERSIONS:
        mp = os.path.join(LAB, "apk/manifests", MANIFEST_FILE[v])
        with open(mp) as fh:
            m = json.load(fh)

        # --- E2 / AB / DPI timeline
        if e2ab:
            for op, field in (("E2", "e2"), ("AB", "ab_family"), ("FC", "fc"), ("F6", "f6")):
                node = (e2ab.get("opcodes") or {}).get(op)
                if not node:
                    continue
                pv = (node.get("per_version") or {}).get(v)
                if pv:
                    m[field] = {"verdict": pv.get("verdict"), "evidence": pv.get("evidence"),
                                "source": "results/reconciliation/e2-ab-summary.json"}
            tl = (e2ab.get("opcode_presence_timeline") or {}).get(v)
            if tl is not None:
                m["dpi_timeline"] = tl

        # --- D8 taxonomy
        if d8:
            node = (d8.get("versions") or {}).get(v)
            if node:
                m["d8_format"] = {
                    "format_family": node.get("format_family"),
                    "record_size": node.get("record_size"),
                    "payload_length": node.get("payload_length"),
                    "chunk_rule": node.get("chunk") or node.get("chunk_rule"),
                    "defaults": node.get("defaults"),
                    "source": "results/reconciliation/d8-taxonomy.json",
                }
                m["d8_commit_frame"] = node.get("commit_frame") or node.get("commit")
                m["d8_readback"] = node.get("receive") or node.get("readback") or node.get("readback_status")
            if d8.get("zero_x0a_question"):
                m["d8_zero_x0a"] = d8["zero_x0a_question"]

        # --- D4
        if d4:
            node = (d4.get("versions") or {}).get(v)
            if node:
                m["d4_request"] = (node.get("sender") or {}).get("frame_bytes")
                m["d4_semantics"] = {
                    "function_name": node.get("function_name"),
                    "sender": node.get("sender"), "receiver": node.get("receiver"),
                    "source": "results/reconciliation/d4-reconstruction.json",
                }
            if d4.get("reply_format"):
                m["d4_reply"] = d4["reply_format"]
            if d4.get("semantics_conclusion"):
                m["d4_conclusion"] = d4["semantics_conclusion"]

        # --- Smi corrections (project-wide; version rows carry the version they were found in)
        if smi:
            items = smi.get("items") or []
            def _mentions(it, ver):
                field = str(it.get("version", ""))
                short = ver.split(".")[0]
                return ver in field or short in field

            mine = [it for it in items if _mentions(it, v)]
            corrected = [it for it in mine if "CORRECTED" in str(it.get("classification", ""))]
            if corrected:
                m["smi_corrections"] = [
                    {"id": it.get("id"), "claim": it.get("claim"),
                     "original": it.get("original_interpretation"),
                     "corrected_value": it.get("corrected_value"),
                     "evidence": it.get("raw_evidence"),
                     "anchors": it.get("independent_anchors"),
                     "label": it.get("evidence_label")}
                    for it in corrected
                ]
            km = [it for it in corrected if "K" in str(it.get("id", "")) or "mask" in str(it.get("category", "")).lower()]
            if km:
                m["key_mask_rule"] = {"rule": km[0].get("corrected_value"),
                                      "evidence": km[0].get("raw_evidence"),
                                      "source": "results/reconciliation/smi-audit.json"}

        with open(mp, "w") as fh:
            json.dump(m, fh, indent=1)
        print(f"updated {MANIFEST_FILE[v]}")

    r = subprocess.run([sys.executable, os.path.join(LAB, "scripts/compare_versions.py")],
                       capture_output=True, text=True)
    print((r.stdout or r.stderr).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
