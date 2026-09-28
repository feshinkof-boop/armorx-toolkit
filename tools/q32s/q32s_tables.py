#!/usr/bin/env python3
"""q32s_tables.py - recover q32s range-gated table branches (the real dispatch mechanism).

q32s `switch` on a *range* of an integer compiles to:

    ifs (rOP > HI) goto <other>          ; range split
    rIDX = rOP + -LO                     ; rebase the index
    if (rIDX > N) goto <default>         ; bounds check -> entry count = N+1
    rIDX = rIDX << 1                     ; halfword stride
    tbh [rIDX]                           ; table branch, table follows inline
    <N+1 halfword entries>

Each entry is a halfword in **halfword units relative to the table start**, i.e.
``target = table_start + entry * 2`` where ``table_start`` is the instruction immediately after
the branch. That encoding was verified on two independent tables in the V41 command dispatcher
(``0x1e089c4`` covering opcodes 0x0B..0x1B, and ``0x1e08a04`` covering 0xE1..0xE5): both resolve
to instruction boundaries inside the parser and the first entry of each lands exactly on the first
instruction after its table.

`tbb` uses a byte stride and byte entries (``target = table_start + entry``) with an unscaled
index; both forms are handled.

Outputs: results/firmware/<tag>-table-branches.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

REPO = pathlib.Path("/home/salamanka/armorx-lab")
OUT = REPO / "results" / "q32s"

TB_RE = re.compile(r"^(tbb|tbh)\s+\[r(\d+)\]$")
SUB_RE = re.compile(r"^r(\d+) = r(\d+) \+ (-?(?:0x[0-9a-f]+|\d+))$")
SUBI_RE = re.compile(r"^r(\d+) \+= (-?(?:0x[0-9a-f]+|\d+))$")
SHL_RE = re.compile(r"^r(\d+) = r(\d+) << 0x1$")
GT_RE = re.compile(r"^ifs? \(r(\d+) > (0x[0-9a-f]+|\d+)\) goto")
LE_RE = re.compile(r"^ifs? \(r(\d+) <= (0x[0-9a-f]+|\d+)\) goto")


def _num(t: str) -> int:
    return int(t, 16) if t.lstrip("-").startswith("0x") else int(t)


def find_range_tables(image: bytes, base: int, recs: list[dict],
                      lo_addr: int | None = None, hi_addr: int | None = None) -> list[dict]:
    addrs = {r["addr"] for r in recs}
    pos = {r["addr"]: i for i, r in enumerate(recs)}
    end = base + len(image)

    def raw(a: int, n: int) -> bytes:
        return image[a - base: a - base + n]

    out = []
    for r in recs:
        m = TB_RE.match(r["text"])
        if not m or r["size"] != 2:
            continue
        if lo_addr is not None and not (lo_addr <= r["addr"] < hi_addr):
            continue
        op, idx_reg = m.group(1), f"r{m.group(2)}"
        stride, scale = (1, 1) if op == "tbb" else (2, 2)
        i = pos[r["addr"]]
        # Walk back through the index computation to the bounds check:
        #   rB = rA << 1 ; tbh [rB]
        #   rA = rOP + -LO ; if (rA > N) goto <default> ; tbh [rB]
        n_cases = None
        gate = None
        reg = idx_reg
        idx_src = idx_reg
        for j in range(i - 1, max(-1, i - 8), -1):
            t = recs[j]["text"]
            sh = SHL_RE.match(t)
            if sh and f"r{sh.group(1)}" == reg:
                reg = f"r{sh.group(2)}"          # drop the index scaling
                continue
            gm = GT_RE.match(t) or LE_RE.match(t)
            if gm and f"r{gm.group(1)}" == reg:
                v = _num(gm.group(2))
                n_cases = v + 1 if ">" in t else v
                gate = {"addr": f"{recs[j]['addr']:#x}", "text": t}
                # keep walking past the gate to find the rebase instruction; its source register
                # is the raw opcode/selector register, which is what a reader actually wants
                for k in range(j - 1, max(-1, j - 4), -1):
                    sm2 = SUB_RE.match(recs[k]["text"])
                    if sm2 and f"r{sm2.group(1)}" == reg:
                        idx_src = f"r{sm2.group(2)}"
                        break
                break
            sm = SUB_RE.match(t)
            if sm and f"r{sm.group(1)}" == reg:
                idx_src = f"r{sm.group(2)}"
                continue
            si = SUBI_RE.match(t)
            if si and f"r{si.group(1)}" == reg:
                continue
        if n_cases is None or not (1 <= n_cases <= 256):
            continue
        tstart = r["addr"] + 2
        rawbytes = raw(tstart, n_cases * stride)
        if len(rawbytes) < n_cases * stride:
            continue
        entries = [int.from_bytes(rawbytes[k * stride:(k + 1) * stride], "little")
                   for k in range(n_cases)]
        after = tstart + n_cases * stride
        cands = {"table_start": (tstart, scale), "tbb_addr": (r["addr"], scale),
                 "after_table": (after, scale)}
        best = None
        for name, (b, s) in cands.items():
            tg = [b + e * s for e in entries]
            if not all(base <= t < end for t in tg):
                continue
            score = sum(1 for t in tg if t in addrs)
            if best is None or score > best[0]:
                best = (score, name, tg, s)
        out.append({
            "branch": f"{r['addr']:#x}", "op": op, "index_reg": idx_reg, "index_src": idx_src,
            "gate": gate, "cases": n_cases, "table_start": f"{tstart:#x}",
            "table_end": f"{after:#x}", "raw_entries": entries,
            "base_model": best[1] if best else None, "entry_scale": best[3] if best else None,
            "aligned": best[0] if best else None,
            "targets": [f"{t:#x}" for t in best[2]] if best else [],
            "confidence": (round(best[0] / n_cases, 3) if best else None),
        })
    return out


def main(argv: list[str]) -> int:
    tag = argv[1]
    image_path = pathlib.Path(argv[2])
    base = int(argv[3], 16)
    lo = int(argv[4], 16) if len(argv) > 4 else None
    hi = int(argv[5], 16) if len(argv) > 5 else None
    image = image_path.read_bytes()
    recs = json.loads((OUT / f"{tag}-instructions.json").read_text())
    tabs = find_range_tables(image, base, recs, lo, hi)
    OUT.mkdir(parents=True, exist_ok=True)
    name = f"{tag}-table-branches.json"
    (OUT / name).write_text(json.dumps(tabs, indent=1) + "\n")
    good = [t for t in tabs if (t["confidence"] or 0) == 1.0]
    print(f"{len(tabs)} range-gated table branches found; {len(good)} fully aligned")
    for t in tabs:
        print(f"  {t['branch']:>10} {t['op']} on {t['index_src']} cases={t['cases']:3d} "
              f"base={str(t['base_model']):12} conf={t['confidence']} "
              f"-> {t['targets'][:6]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
