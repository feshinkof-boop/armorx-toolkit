#!/usr/bin/env python3
"""q32s_switch.py - recover q32s `switch` dispatch tables (`tbb` / `tbh`).

q32s implements `switch` with a table-branch instruction (`tbb [rX]`, 2 bytes). The case table
follows the branch inline and is never executed, so a linear disassembly renders it as garbage
(and llvm-objdump marks some of it "<unkown instruction>"). Recovering the real structure gives
the dispatch tables that the ArmorX protocol parser uses.

Method: every table branch is preceded by a bounds check on the index register
(`if (rX > N) goto <default>`), which fixes the entry count. We read that many 16-bit entries
directly after the branch and decide empirically which base address they are relative to, by
scoring candidate bases on how many resolved targets land on real instruction boundaries.

Outputs: results/q32s/<tag>-switch-tables.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import q32s_lib  # noqa: E402

REPO = pathlib.Path("/home/salamanka/armorx-lab")
OUT = REPO / "results" / "q32s"
BOUND_RE = re.compile(r"if \(r(\d+) > (0x[0-9a-f]+|\d+)\) goto")
BOUND_GE_RE = re.compile(r"if \(r(\d+) >= (0x[0-9a-f]+|\d+)\) goto")
TBB_RE = re.compile(r"^(tbb|tbh)\s+\[r(\d+)\]$")


def find_tables(image: bytes, base: int, recs: list[dict]) -> list[dict]:
    addrs = {r["addr"] for r in recs}
    by_addr = {r["addr"]: r for r in recs}
    order = [r["addr"] for r in recs]
    pos = {a: i for i, a in enumerate(order)}
    lo, hi = base, base + len(image)
    tables = []
    for r in recs:
        m = TBB_RE.match(r["text"])
        if not m or r["size"] != 2:
            continue
        op, idx_reg = m.group(1), m.group(2)
        # walk back to the bounds check for this index register
        n, default = None, None
        i = pos[r["addr"]]
        for j in range(i - 1, max(-1, i - 12), -1):
            t = recs[j]["text"]
            bm = BOUND_RE.search(t) or BOUND_GE_RE.search(t)
            if bm and bm.group(1) == idx_reg:
                n = int(bm.group(2), 16) if bm.group(2).startswith("0x") else int(bm.group(2))
                n = n + (0 if ">=" in t else 1)          # "> N" -> N+1 entries
                default = recs[j]["target"] if ">=" in t else None
                break
        if n is None or n <= 0 or n > 512:
            continue
        tstart = r["addr"] + 2
        width = 2 if op == "tbb" else 4
        raw = image[tstart - base: tstart - base + n * width]
        if len(raw) < n * width:
            continue
        entries = [int.from_bytes(raw[k * width:(k + 1) * width], "little") for k in range(n)]
        after = tstart + n * width
        bases = {"tbb_addr": r["addr"], "table_start": tstart, "after_table": after,
                 "pc_next": r["addr"] + 2}
        best = None            # (score, model, base_name, base_value)
        for bname, bval in bases.items():
            for signed in (False, True):
                if signed:
                    ents = [e - (1 << (8 * width)) if e >= (1 << (8 * width - 1)) else e
                            for e in entries]
                else:
                    ents = entries
                for scale in (1, 2, 4):
                    tgts = [bval + e * scale for e in ents]
                    if not all(lo <= t < hi for t in tgts):
                        continue
                    score = sum(1 for t in tgts if t in addrs)
                    cand = (score, f"{'s' if signed else 'u'}*{scale}", bname, bval, tgts)
                    if best is None or cand[0] > best[0]:
                        best = cand
        tables.append({
            "tbb": f"{r['addr']:#x}", "op": op, "index_reg": f"r{idx_reg}", "entries": n,
            "table_start": f"{tstart:#x}", "table_end": f"{after:#x}",
            "raw_entries": entries,
            "model": best[1] if best else None,
            "base_guess": best[2] if best else None,
            "base_confidence": (round(best[0] / n, 3) if best else None),
            "cases": ([f"{t:#x}" for t in best[4]] if best else []),
            "unresolved": best is None,
        })
    return tables


def main(argv: list[str]) -> int:
    image_path = pathlib.Path(argv[1])
    base = int(argv[2], 16)
    tag = argv[3]
    image = image_path.read_bytes()
    recs = json.loads((OUT / f"{tag}-instructions.json").read_text())
    tables = find_tables(image, base, recs)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tag}-switch-tables.json").write_text(json.dumps(tables, indent=1) + "\n")
    resolved = [t for t in tables if not t["unresolved"]]
    conf = [t for t in resolved if (t["base_confidence"] or 0) >= 0.9]
    print(f"switch tables found: {len(tables)}  resolvable: {len(resolved)}  "
          f"high-confidence(>=0.9): {len(conf)}")
    from collections import Counter
    print("base guess histogram:", Counter(t["base_guess"] for t in resolved))
    print("entry-count histogram:", sorted(Counter(t["entries"] for t in tables).items())[:24])
    print("\nlargest / most confident tables:")
    for t in sorted(conf, key=lambda t: -t["entries"])[:12]:
        print(f"  tbb@{t['tbb']} n={t['entries']:3d} base={t['base_guess']:12} "
              f"conf={t['base_confidence']} cases={t['cases'][:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
