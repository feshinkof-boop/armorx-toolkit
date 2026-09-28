#!/usr/bin/env python3
"""q32s_dispatch.py - extract the ArmorX command dispatcher's opcode -> handler map.

The ArmorX frame handler (`armorx_cmd_dispatch` at 0x1e08772 in V41) validates the frame
(magic / length / checksum, reporting through dedicated error printers) and then dispatches on
the opcode byte with an if/else chain over one register. This tool walks that chain and recovers
the opcode -> handler relationship, together with the evidence for each entry.

Evidence rules:
  * `if (rOP == 0xNN) goto T`  -> opcode NN is handled, handler starts at T
  * `if (rOP != 0xNN) goto T`  -> the fall-through block after it handles NN
  * `ifs (rOP > 0xNN)`         -> range gate; opcodes above it leave the chain (default path)
Nothing is inferred from constants appearing outside a compare against the opcode register.

Outputs: results/firmware/armorx-command-dispatch.{json,md}
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import q32s_lib  # noqa: E402

REPO = pathlib.Path("/home/salamanka/armorx-lab")
OUT_Q = REPO / "results" / "q32s"
OUT_F = REPO / "results" / "firmware"

DEFAULT_FUNC = 0x1E08772
OPCODE_FAMILIES = {
    0x0B: "status / sanity query (live: A5 04 0B B4 -> A5 05 0B 30 E5)",
    0x2F: "unknown family seen in dispatch chain",
    0x70: "unknown family seen in dispatch chain",
    0xAB: "AB motion / gyro family (documented family, opcode not yet located in chain)",
    0xD2: "D2 input-report enable/disable (live: A5 05 D2 01 7D / A5 05 D2 00 7C)",
    0xD4: "D4 query (live: A5 04 D4 7D -> A5 07 D4 11 01 00 92)",
    0xD6: "D6 144-byte config read (10 fragments)",
    0xD7: "D7 configuration write",
    0xD8: "D8 macro download (A4 fragments + A4 05 D8 commit)",
    0xFC: "FC DPI write (live: A5 05 FC 80 26 -> A5 05 FF FC A5)",
    0xF6: "F6 DPI legacy/model-gated twin",
    0xF7: "F7 stick step-length / step accuracy",
    0xF8: "F8 brightness-compensation config (app: A5 04 F8)",
    0xF9: "unknown family seen in dispatch chain",
    0xFA: "unknown family seen in dispatch chain",
    0xFF: "FF response envelope family",
}
CMP_EQ = re.compile(r"if \(r(\d+) == (0x[0-9a-f]+|\d+)\) goto (-?0x[0-9a-f]+)")
CMP_NE = re.compile(r"if \(r(\d+) != (0x[0-9a-f]+|\d+)\) goto (-?0x[0-9a-f]+)")
CMP_GT = re.compile(r"ifs? \(r(\d+) > (0x[0-9a-f]+|\d+)\) goto")
ADDR_RE = re.compile(r"^\s*([0-9a-f]+):")


def num(tok: str) -> int:
    return int(tok, 16) if tok.startswith("0x") else int(tok)


def extract(image: bytes, base: int, func_start: int, func_end: int,
            recs: list[dict], opcode_reg: str = "r1") -> dict:
    inside = [r for r in recs if func_start <= r["addr"] < func_end]
    eq: dict[int, dict] = {}
    ne: list[dict] = []
    gates: list[dict] = []
    for r in inside:
        t = r["text"]
        m = CMP_EQ.search(t)
        if m and m.group(3):
            if f"r{m.group(1)}" != opcode_reg:
                continue
            v = num(m.group(2))
            if v <= 0xFF:
                eq.setdefault(v, {"opcode": v, "opcode_hex": f"{v:#04x}",
                                  "compare_at": f"{r['addr']:#x}", "reg": f"r{m.group(1)}",
                                  "test": "==", "handler": None, "handler_note": None})
                if r["target"]:
                    eq[v]["handler"] = f"{r['target']:#x}"
                    eq[v]["raw"] = t
            continue
        m = CMP_NE.search(t)
        if m and r["target"]:
            if f"r{m.group(1)}" != opcode_reg:
                continue
            v = num(m.group(2))
            if v <= 0xFF:
                ne.append({"opcode": v, "opcode_hex": f"{v:#04x}",
                           "compare_at": f"{r['addr']:#x}", "reg": f"r{m.group(1)}",
                           "branch_to": f"{r['target']:#x}", "raw": t})
            continue
        m = CMP_GT.search(t)
        if m:
            gates.append({"reg": f"r{m.group(1)}", "value": f"{num(m.group(2)):#x}",
                          "at": f"{r['addr']:#x}", "raw": t})
    # fall-through assignment for `!=` tests: the block after the compare handles that opcode
    for e in ne:
        a = int(e["compare_at"], 16)
        nxt = next((r["addr"] for r in inside if r["addr"] > a), None)
        e["fallthrough_handler"] = f"{nxt:#x}" if nxt else None
    entries = []
    for v, e in sorted(eq.items()):
        entries.append({**e, "family": OPCODE_FAMILIES.get(v, "UNKNOWN"),
                        "evidence": "PROVEN STATIC (opcode compared in the frame handler)"})
    for e in sorted(ne, key=lambda e: e["opcode"]):
        if e["opcode"] in eq:
            continue
        entries.append({"opcode": e["opcode"], "opcode_hex": e["opcode_hex"],
                        "compare_at": e["compare_at"], "reg": e["reg"], "test": "!=",
                        "handler": e["fallthrough_handler"],
                        "handler_note": "fall-through block after the != test",
                        "raw": e["raw"],
                        "family": OPCODE_FAMILIES.get(e["opcode"], "UNKNOWN"),
                        "evidence": "STRONG EVIDENCE (fell through the != test)"})
    entries.sort(key=lambda e: e["opcode"])
    return {"function": f"{func_start:#x}", "function_end": f"{func_end:#x}",
            "instructions_examined": len(inside), "range_gates": gates,
            "handlers": entries}


def main(argv: list[str]) -> int:
    tag = argv[1] if len(argv) > 1 else "v41"
    image_path = pathlib.Path(argv[2])
    base = int(argv[3], 16) if len(argv) > 3 else 0x01E00000
    func = int(argv[4], 16) if len(argv) > 4 else DEFAULT_FUNC
    image = image_path.read_bytes()
    recs = json.loads((OUT_Q / f"{tag}-instructions.json").read_text())
    funcs = json.loads((OUT_Q / f"{tag}-functions.json").read_text())
    f = next((f for f in funcs if f["start"] == func), None)
    end = f["end"] if f else func + 0x2000
    res = extract(image, base, func, end, recs)
    strings_by_func = {x["func"] for x in []}
    OUT_F.mkdir(parents=True, exist_ok=True)
    (OUT_F / "armorx-command-dispatch.json").write_text(json.dumps(res, indent=1) + "\n")
    lines = [f"# ARMOR-X command dispatcher (from V41 firmware, static)", "",
             f"Function `{res['function']}` .. `{res['function_end']}`  "
             f"({res['instructions_examined']} instructions examined).", "",
             "| opcode | compare at | test | handler | family / known meaning | evidence |",
             "|---|---|---|---|---|---|"]
    for e in res["handlers"]:
        lines.append(f"| {e['opcode_hex']} | {e['compare_at']} | {e['test']} | "
                     f"{e['handler']} | {e['family']} | {e['evidence']} |")
    lines += ["", "Range gates (opcodes above these leave the chain):"]
    for g in res["range_gates"]:
        lines.append(f"- `{g['at']}` {g['raw']}")
    (OUT_F / "armorx-command-dispatch.md").write_text("\n".join(lines) + "\n")
    print(f"dispatcher {res['function']}..{res['function_end']}: "
          f"{len(res['handlers'])} opcode entries, {len(res['range_gates'])} range gates")
    for e in res["handlers"]:
        print(f"  {e['opcode_hex']}  compare@{e['compare_at']:>10}  {e['test']:2}  "
              f"handler={str(e['handler']):>12}  {e['family'][:58]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
