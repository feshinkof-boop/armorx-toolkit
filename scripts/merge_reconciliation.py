#!/usr/bin/env python3
"""Merge the reconciliation outputs into the per-build manifests, then rebuild the four-way matrix.

Reads (each optional; a missing file is reported, never invented):
  results/reconciliation/e2-ab-summary.json    per-version verdicts for E2 and the AB family, DPI/FC/F6
  results/reconciliation/d8-taxonomy.json      per-version D8 format, chunk rule, payload layout, commit frame
  results/reconciliation/smi-audit.json        tagged-Smi corrections that touch reported constants
  results/reconciliation/d4-reconstruction.json per-version D4 request/reply/parser status

Writes into apk/manifests/<version>.json the fields the four-way matrix reads, under a single
`reconciliation` block (so the original provenance of each field stays visible), and then invokes
scripts/compare_versions.py.

Design rules:
  * never overwrite an existing manifest field with a guess: only fields present in the
    reconciliation inputs are written, and each carries its source file and evidence label;
  * if an input is missing or a value is absent for a version, the matrix keeps saying UNKNOWN -
    "not checked" and "absent" must stay distinguishable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

LAB = "/home/salamanka/armorx-lab"
VERSIONS = ["2.22.0901", "2.23.0609", "2.24.0919", "4.0.8"]
MANIFEST_FILE = {"2.22.0901": "2.22.0901.json", "2.23.0609": "2.23.json",
                 "2.24.0919": "2.24.json", "4.0.8": "4.0.8.json"}
# version label -> the keys the reconciliation files may use for it
ALIASES = {
    "2.22.0901": ["2.22.0901", "2.22", "2220901"],
    "2.23.0609": ["2.23.0609", "2.23", "2230609"],
    "2.24.0919": ["2.24.0919", "2.24", "2240919"],
    "4.0.8": ["4.0.8", "408", "mygt-4.0.8"],
}


def load(path: str):
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print(f"WARN unparsable {path}: {exc}", file=sys.stderr)
        return None


def find_version_block(doc, version: str):
    """Locate the per-version block inside an arbitrary reconciliation JSON shape."""
    if not isinstance(doc, dict):
        return None
    names = ALIASES[version]
    for container_key in ("versions", "per_version", "by_version", "data", "results", "builds"):
        node = doc.get(container_key)
        if isinstance(node, dict):
            for n in names:
                if n in node:
                    return node[n]
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, dict):
                    v = str(item.get("version") or item.get("build") or "")
                    if v in names:
                        return item
    for n in names:
        if isinstance(doc.get(n), dict):
            return doc[n]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    inputs = {
        "e2_ab": os.path.join(LAB, "results/reconciliation/e2-ab-summary.json"),
        "d8": os.path.join(LAB, "results/reconciliation/d8-taxonomy.json"),
        "smi": os.path.join(LAB, "results/reconciliation/smi-audit.json"),
        "d4": os.path.join(LAB, "results/reconciliation/d4-reconstruction.json"),
    }
    docs = {k: load(v) for k, v in inputs.items()}
    for k, v in inputs.items():
        print(f"{'FOUND  ' if docs[k] else 'MISSING'} {k:6s} {v}")

    merged = 0
    for version in VERSIONS:
        mp = os.path.join(LAB, "apk/manifests", MANIFEST_FILE[version])
        if not os.path.isfile(mp):
            print(f"skip {version}: no manifest", file=sys.stderr)
            continue
        manifest = load(mp) or {}
        block = manifest.setdefault("reconciliation", {})
        for key, doc in docs.items():
            if not doc:
                continue
            vb = find_version_block(doc, version)
            if vb is None:
                continue
            block[key] = {"source": os.path.relpath(inputs[key], LAB), "data": vb}
            merged += 1
        if not args.dry_run and block:
            with open(mp, "w") as fh:
                json.dump(manifest, fh, indent=1)
    print(f"merged {merged} version blocks")

    if not args.dry_run:
        r = subprocess.run([sys.executable, os.path.join(LAB, "scripts/compare_versions.py")],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
