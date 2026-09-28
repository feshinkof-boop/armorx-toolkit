#!/usr/bin/env python3
"""q32s_validate.py - validate the vendor q32s disassembler against the vendor ROM listing.

The AC63 SDK ships `cpu/bd19/tools/rom.lst`, a full `llvm-objdump` disassembly of the BD19 mask
ROM annotated with symbols and source lines. Because that listing prints the raw instruction
bytes, the ROM image can be reconstructed exactly and then re-disassembled by our own toolchain
invocation. Agreement between the two listings is independent evidence that our wrap/link/
disassemble pipeline addresses the same ISA and produces the same decoding.

Outputs: results/q32s/rom-validation.json
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import q32s_lib  # noqa: E402

SDK_ROM_LST = pathlib.Path(
    "/home/salamanka/armorx-re/jieli-tools/fw-AC63_BT_SDK/cpu/bd19/tools/rom.lst")
OUT = pathlib.Path("/home/salamanka/armorx-lab/results/q32s")
ROM_BASE = 0x100000

LST_RE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*\t(.*)$")


def parse_vendor_listing(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        m = LST_RE.match(line)
        if not m:
            continue
        body = m.group(3)
        body = re.split(r"\s+##", body)[0].strip()
        out.append({"addr": int(m.group(1), 16), "raw": bytes.fromhex(m.group(2)), "text": body})
    return out


def normalize(text: str) -> str:
    """Compare on the instruction semantics, not on symbol annotations."""
    t = re.sub(r"<[^>]*>", "", text)          # strip "<symbol+0xNN : addr>"
    t = re.sub(r"\s+", " ", t).strip()
    return t


def main() -> int:
    lst = SDK_ROM_LST.read_text(errors="replace")
    vendor = parse_vendor_listing(lst)

    result: dict = {
        "vendor_listing": str(SDK_ROM_LST),
        "vendor_instructions": len(vendor),
        "vendor_bytes": sum(len(v["raw"]) for v in vendor),
        "toolchain": q32s_lib.toolchain_info(),
    }
    # 1. split the listing into contiguous runs (the ROM listing has data holes)
    runs: list[list[dict]] = []
    cur = [vendor[0]]
    for prev, nxt in zip(vendor, vendor[1:]):
        if nxt["addr"] == prev["addr"] + len(prev["raw"]):
            cur.append(nxt)
        else:
            runs.append(cur)
            cur = [nxt]
    runs.append(cur)

    compare = 0
    exact = mnem = size_ok = 0
    disagreements: list[dict] = []
    work = pathlib.Path("/home/salamanka/.hermes/cache/scratch/q32s/romval")
    for i, run in enumerate(runs):
        image = b"".join(v["raw"] for v in run)
        base = run[0]["addr"]
        try:
            elf = q32s_lib.wrap_and_link(image, base, work, tag=f"rom{i}")
            text = q32s_lib.disassemble(elf)
        except q32s_lib.ToolchainError as e:
            disagreements.append({"run": f"{base:#x}", "error": str(e)[:200]})
            continue
        mine = {r["addr"]: r for r in q32s_lib.parse_listing(text, base)}
        for v in run:
            m = mine.get(v["addr"])
            if m is None:
                continue
            compare += 1
            size_ok += (m["size"] == len(v["raw"]))
            first_v = v["text"].split()[0] if v["text"].split() else ""
            first_m = m["text"].split()[0] if m["text"].split() else ""
            mnem += (first_m == first_v)
            same = normalize(m["text"]) == normalize(v["text"])
            exact += same
            if not same and len(disagreements) < 25:
                disagreements.append({"addr": f"{v['addr']:#x}", "vendor": v["text"],
                                      "ours": m["text"]})
    result.update({
        "runs": len(runs),
        "compared": compare,
        "exact_text_match": exact,
        "exact_pct": round(100.0 * exact / max(compare, 1), 3),
        "first_token_match": mnem,
        "first_token_pct": round(100.0 * mnem / max(compare, 1), 3),
        "length_match": size_ok,
        "length_pct": round(100.0 * size_ok / max(compare, 1), 3),
        "disagreement_samples": disagreements,
        "verdict": ("AGREES with the vendor listing" if compare and exact == compare else
                    "PARTIAL agreement - see samples"),
    })
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "rom-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    for k in ("vendor_instructions", "vendor_bytes", "contiguous", "compared",
              "exact_pct", "first_token_pct", "length_pct", "verdict"):
        print(f"{k}: {result.get(k)}")
    print("\nfirst disagreements:")
    for d in result.get("disagreement_samples", [])[:8]:
        print(f"  {d['addr']}  vendor={d['vendor']!r}\n            ours={d['ours']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
