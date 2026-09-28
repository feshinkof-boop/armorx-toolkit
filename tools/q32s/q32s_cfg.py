"""CFG builder for the V41 firmware with a decimal/hex-aware operand parser.

Two traps motivated this module and are regression-tested in tests/test_q32s_cfg.py:

1. The vendor q32s disassembly renders STACK offsets in DECIMAL (``b[sp+1092]``) while
   global offsets are HEX.  A hex-only scanner silently misses every stack-based write.
2. ``tbh``/``tbb`` tables are emitted inline, and the payload after the branch is
   linear-swept as if it were code.  Those phantom "instructions" add bogus control-flow
   edges, so table byte ranges must be masked out before a CFG is built.

Usage:
    python3 tools/q32s/q32s_cfg.py [--region 0x1e0ac14:0x1e0e414] [--out results/firmware/d2-candidate-cfg.json]
"""

from __future__ import annotations

import argparse
import bisect
import collections
import json
import pathlib
import re
import sys

INS_RE = re.compile(r"\s*([0-9a-f]{6,8}):\s+([0-9a-f ]+?)\s{2,}\t(.*)$")
HEX = re.compile(r"0x[0-9a-f]+")
STACK = re.compile(r"\[\s*sp\s*\+\s*(0x[0-9a-f]+|\d+)\s*\]")
BRANCH = re.compile(r"^(goto|if .*goto|tb[bh] |rts)")


def parse_int(text: str) -> int:
    """Decimal or 0x-hex, as the vendor disassembly mixes both."""
    return int(text, 16) if text.strip().lower().startswith("0x") else int(text, 10)


def stack_off(text: str):
    """Byte offset of a [sp+N] reference, or None.  Handles decimal and hex."""
    m = STACK.search(text)
    return parse_int(m.group(1)) if m else None


def load_instructions(path: pathlib.Path):
    out = []
    for line in path.read_text(errors="replace").splitlines():
        m = INS_RE.match(line)
        if m:
            out.append((int(m.group(1), 16), m.group(3).strip()))
    out.sort()
    return out


def table_ranges(tables_json: pathlib.Path):
    if not tables_json.exists():
        return []
    entries = json.loads(tables_json.read_text())
    return [(int(e["table_start"], 16), int(e["table_end"], 16))
            for e in entries if e.get("table_start") and e.get("table_end")]


def table_targets(tables_json: pathlib.Path):
    if not tables_json.exists():
        return {}
    entries = json.loads(tables_json.read_text())
    return {int(e["branch"], 16): [int(x, 16) for x in e["targets"]] for e in entries}


def target_of(text: str):
    m = re.findall(r"([0-9a-f]{6,8})", text)
    return int(m[-1], 16) if m else None


class Cfg:
    def __init__(self, instructions, tables_json, region):
        self.lo, self.hi = region
        masked = table_ranges(tables_json)
        self.tabmap = table_targets(tables_json)
        ins = [(a, t) for a, t in instructions
               if self.lo <= a < self.hi and not any(s <= a < e for s, e in masked)]
        self.ins = ins
        leaders = set()
        for i, (a, t) in enumerate(ins):
            leaders.add(a)
            if BRANCH.match(t):
                if not t.startswith("rts"):
                    x = target_of(t)
                    if self.in_region(x):
                        leaders.add(x)
                if i + 1 < len(ins):
                    leaders.add(ins[i + 1][0])
                if t.startswith("tb"):
                    for x in self.tabmap.get(a, []):
                        if self.in_region(x):
                            leaders.add(x)
        blocks, cur = [], []
        for a, t in ins:
            if a in leaders and cur:
                blocks.append(cur)
                cur = []
            cur.append((a, t))
        if cur:
            blocks.append(cur)
        self.blocks = blocks
        self.starts = [b[0][0] for b in blocks]
        self.term = {}
        self.succ = collections.defaultdict(set)
        self.pred = collections.defaultdict(set)
        for i, b in enumerate(blocks):
            a, t = b[-1]
            targets = []
            if t.startswith("rts"):
                self.term[i] = ("rts", t)
            elif re.match(r"tb[bh] ", t):
                targets = [x for x in self.tabmap.get(a, []) if self.in_region(x)]
                self.term[i] = ("tbb", t)
            elif t.startswith("goto"):
                targets = [target_of(t)]
                self.term[i] = ("goto", t)
            elif t.startswith("if") and "goto" in t:
                targets = [target_of(t)]
                self.term[i] = ("if", t)
                if i + 1 < len(blocks):
                    self.succ[i].add(i + 1)
            else:
                self.term[i] = ("fall", t)
                if i + 1 < len(blocks):
                    self.succ[i].add(i + 1)
            for x in targets:
                j = self.block_of(x)
                if j is not None:
                    self.succ[i].add(j)
        # NOTE: edge targets are region-guarded.  Block indices are never clamped from
        # out-of-region addresses: that produced a phantom super-hub in an earlier pass.
        for i in list(self.succ):
            for j in self.succ[i]:
                self.pred[j].add(i)

    def in_region(self, x):
        return x is not None and self.lo <= x < self.hi

    def block_of(self, addr):
        i = bisect.bisect_right(self.starts, addr) - 1
        if i < 0 or not self.in_region(self.starts[i]):
            return None
        return i

    @property
    def entry(self):
        return self.block_of(self.lo)

    def reach(self, start):
        seen, stack = {start}, [start]
        while stack:
            x = stack.pop()
            for y in self.succ.get(x, ()):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        return seen

    def dominators(self, reachable):
        ent = self.entry
        dom = {x: set(reachable) for x in reachable}
        dom[ent] = {ent}
        changed = True
        while changed:
            changed = False
            for x in reachable:
                if x == ent:
                    continue
                preds = [p for p in self.pred[x] if p in reachable]
                new = {x} | (set.intersection(*[dom[p] for p in preds]) if preds else set(reachable))
                if new != dom[x]:
                    dom[x] = new
                    changed = True
        return dom

    def path(self, start, goal):
        queue, parent = [start], {start: None}
        while queue:
            cur = queue.pop(0)
            if cur == goal:
                break
            for y in self.succ.get(cur, ()):
                if y not in parent:
                    parent[y] = cur
                    queue.append(y)
        if goal not in parent:
            return None
        out, cur = [], goal
        while cur is not None:
            out.append(cur)
            cur = parent[cur]
        return out[::-1]

    def ordered_verdict(self, a, b):
        """Sequential / exclusive / unreachable for two block indices."""
        ent = self.entry
        reachable = self.reach(ent)
        if a not in reachable or b not in reachable:
            return "UNREACHABLE"
        if a == b:
            return "SAME_BLOCK"
        a2b = b in self.reach(a)
        b2a = a in self.reach(b)
        if a2b and b2a:
            return "CYCLIC_BOTH_ORDERS_POSSIBLE"
        if a2b:
            return "SEQUENTIAL_A_BEFORE_B"
        if b2a:
            return "SEQUENTIAL_B_BEFORE_A"
        return "MUTUALLY_EXCLUSIVE"


MARKERS = {
    "C_copy_r13_into_candidate": 0x1E0CD24,
    "B14_compare_gate": 0x1E0DAD2,
    "B14_build": 0x1E0DAFE,
    "B14_builder_entry": 0x1E0DB0C,
    "packed_bit_seed_14B": 0x1E0DA54,
    "packed_bit_seed_28B": 0x1E0E3AE,
    "D28_build": 0x1E0E2C2,
}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--asm", default="results/q32s/v41-disassembly.asm")
    ap.add_argument("--tables", default="results/q32s/v41-table-branches-image-wide.json")
    ap.add_argument("--region", default="0x1e0ac14:0x1e0e414")
    ap.add_argument("--out", default="results/firmware/d2-candidate-cfg.json")
    args = ap.parse_args(argv)
    lo, hi = (int(x, 16) for x in args.region.split(":"))
    instructions = load_instructions(pathlib.Path(args.asm))
    cfg = Cfg(instructions, pathlib.Path(args.tables), (lo, hi))
    reachable = cfg.reach(cfg.entry)
    marks = {k: cfg.block_of(v) for k, v in MARKERS.items()}
    verdicts = {}
    for name, blk in marks.items():
        verdicts[f"C_copy_r13 vs {name}"] = ("UNREACHABLE" if blk is None
                                             else cfg.ordered_verdict(marks["C_copy_r13_into_candidate"], blk))
    paths = {}
    for name, blk in marks.items():
        if blk is None:
            paths[name] = None
            continue
        p = cfg.path(cfg.entry, blk)
        paths[name] = [hex(cfg.starts[x]) for x in p] if p else None
    dom = cfg.dominators(reachable)
    root = None
    if reachable:
        counts = collections.Counter()
        for blk in reachable:
            for d in dom[blk]:
                counts[d] += 1
        root = cfg.starts[counts.most_common(1)[0][0]]
    report = {
        "artifact": "armorx-d2-candidate-cfg",
        "region": [hex(lo), hex(hi)],
        "instruction_count": len(cfg.ins),
        "block_count": len(cfg.blocks),
        "reachable_blocks": len(reachable),
        "dominator_root": hex(root) if root is not None else None,
        "table_data_masked": len(table_ranges(pathlib.Path(args.tables))),
        "markers": {k: (None if v is None else {"addr": hex(MARKERS[k]), "block": v, "reachable": v in reachable})
                    for k, v in marks.items()},
        "verdicts": verdicts,
        "dominance": {name: sorted(k for k, v in marks.items()
                                  if v is not None and v in dom.get(marks[name], set()))
                      for name in marks if marks[name] is not None},
        "forward_order_note": ("Reachability alone cannot order these blocks: the function contains "
                               "loops (in-degree-0 entry at 0x1e0ac14, with internal back edges), so "
                               "both orders are reachable. Forward order is therefore argued from "
                               "DOMINANCE: a marker that dominates another executes before it on every "
                               "pass through the function."),
        "paths_from_entry": paths,
        "doc": ("Ordering is derived from reachability and shortest paths on the FULL graph, "
                "not from an acyclic reduction: removing all back edges destroyed reachability "
                "and is not a valid way to order blocks in this function."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"blocks": report["block_count"], "reachable": report["reachable_blocks"],
                      "verdicts": verdicts}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
