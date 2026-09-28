#!/usr/bin/env python3
"""q32s_analyze.py - disassemble and navigate a raw q32s firmware image.

Pipeline: raw image -> ELF at its true base (vendor clang+ld) -> vendor llvm-objdump ->
structured records -> function recovery (call targets + entry + code after returns) ->
string xrefs -> call graph.

Outputs (default under results/q32s/):
  <tag>-disassembly.asm   raw listing
  <tag>-instructions.json structured instruction records
  <tag>-functions.json    recovered functions with calls / callers / strings
  <tag>-string-xrefs.json every absolute reference into the image, with the string it hits
  <tag>-coverage.json     code/data split and confidence metrics

Usage: q32s_analyze.py <image.bin> <base-hex> <tag> [strings.json]
"""
from __future__ import annotations

import bisect
import json
import pathlib
import re
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import q32s_lib  # noqa: E402

REPO = pathlib.Path("/home/salamanka/armorx-lab")
OUT = REPO / "results" / "q32s"
STRINGS_DEFAULT = REPO / "research/firmware/2026-09-28/string-corpus.json"


def load_strings(path: pathlib.Path, tag: str) -> dict[int, str]:
    """Map absolute address -> string, using the recorded string corpus."""
    data = json.loads(path.read_text())
    best, bestlen = None, -1
    for key, val in data["images"].items():
        n = len(val.get("ascii", []))
        if tag.replace("-", "") in key.replace("-", "").replace("_", "") or n > bestlen:
            if tag.split("-")[0] in key or n > bestlen:
                best, bestlen = val, n
    # prefer an exact-ish match on the tag, else the largest corpus
    for key, val in data["images"].items():
        if all(tok.lower() in key.lower() for tok in tag.lower().split("-")[:2]):
            best = val
            break
    out = {}
    for e in best.get("ascii", []):
        out[int(e["off"])] = e["s"]
    return out


def main(argv: list[str]) -> int:
    image_path = pathlib.Path(argv[1])
    base = int(argv[2], 16)
    tag = argv[3]
    strings_path = pathlib.Path(argv[4]) if len(argv) > 4 else STRINGS_DEFAULT
    image = image_path.read_bytes()
    work = pathlib.Path("/home/salamanka/.hermes/cache/scratch/q32s") / tag
    res = q32s_lib.analyze_image(image, base, work, tag=tag)
    recs = res["instructions"]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{tag}-disassembly.asm").write_text(res["raw_listing"])

    strings = load_strings(strings_path, tag) if strings_path.exists() else {}
    lo, hi = base, base + len(image)

    # The compiler frequently points *into* a string literal (ANSI-escaped format strings are
    # referenced past their escape prefix, and trailing text shares a run). So resolve a
    # reference to the literal that *contains* it and keep the suffix that the pointer sees.
    spans = sorted(((base + off, base + off + len(s), s) for off, s in strings.items()))
    span_starts = [a for a, _b, _s in spans]

    def resolve(v: int):
        """Return (literal_start, literal, suffix_seen) if v points inside a known literal."""
        i = bisect.bisect_right(span_starts, v) - 1
        if i < 0:
            return None
        a, b, lit = spans[i]
        if a <= v < b:
            return a, lit, lit[v - a:]
        return None

    str_addr = {base + off: s for off, s in strings.items()}

    # ---- functions: entry, call targets, and code following a return ----------
    entry = 0x01E00120
    marks: set[int] = {entry, base}
    callers: dict[int, set[int]] = defaultdict(set)
    calls_out: dict[int, set[int]] = defaultdict(set)
    for r in recs:
        if r["kind"] == "call" and r["target"] and lo <= r["target"] < hi:
            marks.add(r["target"])
            calls_out[r["addr"]].add(r["target"])
    addr_set = {r["addr"] for r in recs}
    for r in recs:
        if r["kind"] == "ret":
            nxt = r["addr"] + r["size"]
            if nxt in addr_set:
                marks.add(nxt)
    starts = sorted(m for m in marks if m in addr_set)
    order = [r["addr"] for r in recs]
    pos = {a: i for i, a in enumerate(order)}
    funcs = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else hi
        funcs.append({"start": s, "end": e, "size": e - s,
                      "entry_point": s == entry,
                      "calls": sorted(calls_out.get(s, [])), "strings": [], "callers": []})
    fmap = {f["start"]: f for f in funcs}
    fstart_sorted = starts

    def owner(a: int) -> int | None:
        import bisect
        i = bisect.bisect_right(fstart_sorted, a) - 1
        return fstart_sorted[i] if i >= 0 else None

    for r in recs:
        if r["kind"] == "call" and r["target"] and lo <= r["target"] < hi:
            st = owner(r["addr"])
            if st and r["target"] in fmap and r["target"] != st:
                fmap[r["target"]]["callers"].append(st)

    # ---- string / data xrefs --------------------------------------------------
    xrefs: dict[int, list[dict]] = defaultdict(list)
    data_hits: dict[int, list[dict]] = defaultdict(list)
    for r in recs:
        st = owner(r["addr"])
        for v in r["refs"]:
            if lo <= v < hi:
                hit = resolve(v)
                if hit is not None:
                    lit_start, lit, suffix = hit
                    xrefs[v].append({"insn": r["addr"], "text": r["text"], "func": st,
                                     "literal": lit, "literal_start": f"{lit_start:#x}",
                                     "suffix": suffix})
                    if st is not None:
                        fmap[st]["strings"].append(suffix)
                else:
                    data_hits[v].append({"insn": r["addr"], "text": r["text"], "func": st})

    code_bytes = sum(r["size"] for r in recs)
    coverage = {
        "image": str(image_path), "base": f"{base:#x}", "image_size": len(image),
        "instructions": len(recs),
        "code_bytes": code_bytes, "code_pct": round(100.0 * code_bytes / len(image), 2),
        "functions_recovered": len(funcs),
        "distinct_call_targets": len(marks),
        "calls_resolved": sum(len(v) for v in calls_out.values()),
        "string_refs": sum(len(v) for v in xrefs.values()),
        "distinct_strings_referenced": len(xrefs),
        "data_refs_in_image": sum(len(v) for v in data_hits.values()),
        "distinct_data_targets": len(data_hits),
        "insn_size_histogram": {str(s): sum(1 for r in recs if r["size"] == s)
                                for s in sorted({r["size"] for r in recs})},
        "kind_histogram": {},
    }
    for r in recs:
        coverage["kind_histogram"][r["kind"]] = coverage["kind_histogram"].get(r["kind"], 0) + 1

    (OUT / f"{tag}-instructions.json").write_text(json.dumps(recs) + "\n")
    (OUT / f"{tag}-functions.json").write_text(json.dumps(funcs, indent=1) + "\n")
    (OUT / f"{tag}-string-xrefs.json").write_text(json.dumps(
        [{"ptr": f"{a:#x}", "seen": v[0]["suffix"], "literal": v[0]["literal"],
          "literal_start": v[0]["literal_start"], "n_xrefs": len(v), "xrefs": v}
         for a, v in sorted(xrefs.items())], indent=1, ensure_ascii=False) + "\n")
    # deduplicate per-function string lists
    for f in funcs:
        f["strings"] = sorted(set(f["strings"]))
    (OUT / f"{tag}-coverage.json").write_text(json.dumps(coverage, indent=2) + "\n")

    print(json.dumps(coverage, indent=2))
    print("\n=== protocol / vendor strings with code xrefs ===")
    keys = ("cmd", "gpad", "GAMEPAD", "recort", "curve", "IMU", "ZJ-XT", "ZIKWAY", "24g",
            "xbox", "usbh", "flash", "macro", "joystick", "trigger", "cfg", "DPI", "dpi",
            "key", "battery", "profile")
    shown = 0
    for a, v in sorted(xrefs.items()):
        s = v[0]["literal"]
        seen = v[0]["suffix"]
        if any(k.lower() in s.lower() or k.lower() in seen.lower() for k in keys) and len(seen) >= 5:
            f = v[0]["func"]
            print(f"  {a:#010x} {seen[:56]!r:58} xrefs={len(v)} func={f and hex(f)}")
            shown += 1
            if shown >= 45:
                break
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
