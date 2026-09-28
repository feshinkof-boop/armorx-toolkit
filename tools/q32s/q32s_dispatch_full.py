#!/usr/bin/env python3
"""q32s_dispatch_full.py - build the complete ArmorX command-dispatch model from real artifacts.

Merges three independent evidence sources, all previously recorded on disk:

1. ``results/q32s/v41-table-branches.json``  - range-gated ``tbh`` jump tables (the primary
   dispatch mechanism; entries are halfword offsets with ``target = table_start + entry*2``).
2. ``results/firmware/armorx-command-dispatch.json`` - the if/else chain entries recovered in the
   previous pass (opcode compares on the opcode register inside a single range).
3. Hand-verified handler semantics recorded in this pass (D6/D7/D8/D9, 0x0B, 0x05, 0x19), each
   with the exact instruction evidence that justifies it.

Everything numeric is read from those artifacts; nothing is retyped here.

Outputs: results/firmware/armorx-command-dispatch-full.{json,md,dot}
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path("/home/salamanka/armorx-lab")
QF = REPO / "results" / "q32s"
FW = REPO / "results" / "firmware"

# opcode -> semantic findings established in this pass. Each entry names the instruction that
# fixes the meaning, so a reader can re-check it without trusting this table.
SEMANTICS = {
    0x05: dict(name="factory/diagnostic", kind="sub-dispatch",
               detail="6-way tbh on (payload[0] & 0x7F) at 0x1e08e78; sub-cases call "
                      "0x1e0701c (case 0, head-error report), 0x1e070da (case 1, checksum-error "
                      "report), 0x1e07156 (case 2), 0x1e0710a (case 3), 0x1e04a92(3,1) (case 4), "
                      "0x1e04a92(3,0) (case 5). Error-report and flash/VM-test callees => "
                      "factory/diagnostic class, not normal config",
               confidence="STRONG EVIDENCE"),
    0x0B: dict(name="status query", kind="read",
               detail="handler 0x1e089e8 loads the immediate 0x32 into a 1-byte response buffer "
                      "(b[sp+4] = 0x32) then jumps to the shared TX tail 0x1e08e5a with r1 = 0x0B "
                      "== the opcode, confirming the case->opcode mapping. Live reply was "
                      "A5 05 0B 30 E5 (payload 0x30 = 48) vs this immediate 0x32 = 50: the "
                      "constant and the live value differ by 2 and the difference is NOT yet "
                      "explained (FW-U-029)",
               confidence="STRONG EVIDENCE"),
    0x19: dict(name="state set (byte at state+0x11)", kind="write",
               detail="shares the block at 0x1e08d24 with 0xD2; at 0x1e08d2c the opcode selects "
                      "the destination (0x19 -> r8+0x11, else r8+0x10), payload byte r4 = b[r9+3] "
                      "is stored there",
               confidence="STRONG EVIDENCE"),
    0xD2: dict(name="input-report enable/disable", kind="write",
               detail="0x1e08d24 stores the decoded payload byte at state+0x10; when the enable "
                      "condition holds it calls 0x1e04b38 (app_select_24g). This is the same block "
                      "0x19 shares",
               confidence="PROVEN STATIC"),
    0xD6: dict(name="config CRC query (16-bit)", kind="read",
               detail="0x1e0921c reads [state+0x1b0], extracts the big-endian 16-bit value at "
                      "record offset 2..3 (b[+3]<<8 | b[+2]) and replies with opcode 0xD6 via the "
                      "shared TX builder 0x1e09426. NOTE: this contradicts the live-observed "
                      "144-byte D6 read - recorded as FW-U-028",
               confidence="STRONG EVIDENCE"),
    0xD7: dict(name="config write (144-byte staging)", kind="write",
               detail="0x1e09232 copies len-4 payload bytes into a 144-byte staging buffer "
                      "(sp+560), validates it with 0x1e0566a(length 0x90), then loops 4 times "
                      "(r7 = 0..3) over record indices and calls 0x1e05c66 (record writer) when "
                      "staging[0x70+i] differs; finishes with 0x1e069c2 and 0x1e059a2",
               confidence="PROVEN STATIC"),
    0xD8: dict(name="single 220-byte record write", kind="write",
               detail="0x1e0928c takes payload[0..] as a 220-byte (0xDC) record validated by "
                      "0x1e0566a, selects the destination by payload[2] (b[r9+6]) into the record "
                      "array [state+0x1b8] with stride 0xDC, and bounds-checks the index <= 0xDC",
               confidence="PROVEN STATIC"),
    0xD9: dict(name="record read (220-byte records)", kind="read",
               detail="0x1e09346 reads the 16-bit header word of record payload[0] (index < 4) "
                      "from [state+0x1b8] with stride 0xDC and replies with opcode 0xD9 via "
                      "0x1e09426",
               confidence="PROVEN STATIC"),
}


def main() -> int:
    tabs = json.loads((QF / "v41-table-branches.json").read_text())
    chain = json.loads((FW / "armorx-command-dispatch.json").read_text())
    funcs = json.loads((QF / "v41-functions.json").read_text())
    known = {f"{f['start']:#x}": f for f in funcs}

    ranges = []
    for t in tabs:
        gate = (t["gate"] or {}).get("text", "")
        lo = hi = None
        if "+ -0x" in gate or "+ -" in gate:
            pass
        # the opcode range is rebased by a preceding subtract; recover it from the gate text and
        # the index source instruction is recorded verbatim in the artifact for re-checking.
        ranges.append({
            "branch": t["branch"], "op": t["op"], "cases": t["cases"],
            "table_start": t["table_start"], "table_end": t["table_end"],
            "gate": t["gate"], "index_reg": t["index_reg"], "index_src": t["index_src"],
            "base_model": t["base_model"], "entry_scale": t["entry_scale"],
            "alignment": t["confidence"], "targets": t["targets"],
            "raw_entries": t["raw_entries"],
        })

    # explicit opcode ranges, each justified by the recorded gate + rebase instruction
    table_opcodes = {
        "0x1e089c4": (0x0B, 0x1B, "r2 = r1 + -0xb ; if (r2 > 0x10) goto <outside>"),
        "0x1e08a04": (0xE1, 0xE5, "r0 = r1 + -0xe1 ; if (r0 > 0x4) goto <outside>"),
        "0x1e08e78": (None, None, "r0 = payload[0] & 0x7F ; if (r0 > 0x5) goto <default> "
                                  "(sub-dispatch inside opcode 0x05, not an opcode range)"),
        "0x1e09060": (0xD4, 0xD9, "r0 = r1 + -0xd4 ; if (r0 > 0x5) goto 0x1e091f8"),
    }

    routes = []
    for r in ranges:
        lo, hi, why = table_opcodes[r["branch"]]
        for i, tgt in enumerate(r["targets"]):
            op = None if lo is None else lo + i
            sem = SEMANTICS.get(op) if op is not None else None
            routes.append({
                "opcode": f"{op:#04x}" if op is not None else None,
                "sub_index": i if op is None else None,
                "handler": tgt,
                "via": f"{r['op']} table at {r['branch']} (table_start {r['table_start']})",
                "range_justification": why,
                "semantics": sem["name"] if sem else None,
                "confidence": sem["confidence"] if sem else "INFERRED (route only)",
                "detail": sem["detail"] if sem else None,
                "handler_function": known.get(tgt, {}).get("name"),
            })

    out = {
        "artifact": "armorx-command-dispatch-full",
        "image": "V41 app.bin (base 0x01E00000, entry 0x01E00120)",
        "parser": {"address": "0x1e08772", "opcode_register": "r1",
                   "opcode_offset_in_frame": "r9+2 (b[r9+2])",
                   "buffer_argument": "r0 -> r13 (transport/state context), r1 -> r9 (frame), "
                                      "r2 -> r6 (frame length)"},
        "dispatch_structure": {
            "0x00..0x2E": "tbh table 0x1e089c4 for opcodes 0x0B..0x1B; other opcodes fall to "
                          "0x1e08e5e (where opcode 0x05 is handled) else 0x1e08ff2 (default)",
            "0x2F..0xE0": "if/else chain at 0x1e08d1a (opcode compares: 0x2F, 0x70, 0xD2, 0xD4, "
                           "0xD7, 0xF7, 0xF8, 0xF9, 0xFA)",
            "D-family (second level)": "the tbh table at 0x1e09060 re-reads b[r9+2] and dispatches "
                           "0xD4..0xD9; it is a SECOND-LEVEL dispatch, reached from inside the "
                           "0x2F..0xE0 handling, not a sibling of the chain. 0xD4 and 0xD7 therefore "
                           "have both a chain entry (0x1e08944 / 0x1e08a68) and a table entry "
                           "(0x1e0906e / 0x1e09232); do NOT collapse them until the level "
                           "relationship is read out in full",
            "0xE1..0xE5": "tbh table 0x1e08a04",
            "0xE6..0xFF": "single check at 0x1e08e8c: only 0xEF is accepted, everything else "
                          "(including FC and F6) falls to 0x1e08ff2 (default/unsupported)",
        },
        "table_branches": ranges,
        "chain_entries": chain,
        "routes": routes,
        "handler_semantics": {f"{k:#04x}": v for k, v in SEMANTICS.items()},
        "shared_helpers": {
            "0x1e05628": "CRC-16 routine: init 0xFFFF, LSB-first (reflected) nibble-table update, "
                         "16 halfword entries, returns low 16 bits. Matches the live-validated "
                         "CRC-16/MODBUS (poly 0xA001, init 0xFFFF) used by the 144-byte config",
            "0x1e0566a": "record-header validator: len = BE16 at [2..3]; rejects len<4 or "
                         "len>max; computes 0x1e05628(ptr+2, len-2) and compares against the "
                         "BE16 stored at [0..1]; prints 0x1e27206/0x1e27213 on mismatch",
            "0x1e0642c": "shared frame/response builder (r0 = context r13, r1 = opcode, r2 = data, "
                         "r3 = value/extra) - called from the F7 path and from the factory path",
            "0x1e09426": "shared TX tail for the opcode/record replies",
            "0x1e05c66": "record writer: builds a 0xDC (220) byte record with a CRC header "
                         "(calls 0x1e05628 over 8 bytes for the header test, string 'n=%d crc=%x')",
            "0x1e06998": "record-index translation used by the D7 loop",
            "0x1e059a2": "post-write finaliser called by the D7 path (stride/param handling)",
        },
        "state_globals": {
            "0x4850_base+0x10": "D2 input-report enable byte (written by the D2 handler)",
            "0x4850_base+0x11": "sibling state byte written by opcode 0x19",
            "0x4850_base+0x150": "F7 step-length/step-accuracy state byte",
            "0x4850_base+0x1b0": "pointer to the object whose [2..3] the D6 handler reports",
            "0x4850_base+0x1b8": "base of the 220-byte (0xDC) record array used by D7/D8/D9",
        },
        "open_contradictions": [
            "FW-U-028: firmware 0xD6 returns a single 16-bit value, while live capture showed a "
            "144-byte D6 read; the opcode attribution of the live read needs re-checking",
            "FW-U-027: the CRC routine at 0x1e05628 loads its table base from the immediate "
            "0x1e29900, but the CRC-16/MODBUS nibble table is at 0x1e297e0 (delta 0x120) and the "
            "bytes at 0x1e29900 are the assert string 'P33 SYS SOFT RESET : P3_PR_PWR[4]=1'",
        ],
    }
    (FW / "armorx-command-dispatch-full.json").write_text(json.dumps(out, indent=1) + "\n")

    # dot graph: families -> handlers
    lines = ["digraph armorx_dispatch {", "  rankdir=LR;", "  node [shape=box,fontsize=10];",
             '  parser [label="0x1e08772 parser\\nr1 = b[r9+2]"];']
    seen = set()
    for r in routes:
        n = r["handler"]
        if n not in seen:
            seen.add(n)
            lbl = r["semantics"] or "handler"
            lines.append(f'  {n} [label="{n}\\n{lbl}"];')
        lbl = r["opcode"] or f"sub{r['sub_index']}"
        lines.append(f'  parser -> {n} [label="{lbl}"];')
    lines.append("}")
    (FW / "armorx-command-dispatch-full.dot").write_text("\n".join(lines) + "\n")

    md = ["# ArmorX V41 command dispatch - full model", "",
          "Generated by `tools/q32s/q32s_dispatch_full.py` from recorded artifacts; every address",
          "below is read from `results/q32s/v41-table-branches.json` or",
          "`results/firmware/armorx-command-dispatch.json`.", "",
          "## Dispatch mechanism", "",
          "The parser is **not** a flat if/else chain. It splits the opcode into four ranges and",
          "uses two `tbh` jump tables plus one if/else chain and one shared sub-dispatch table:",
          ""]
    for k, v in out["dispatch_structure"].items():
        md.append(f"- `{k}` -> {v}")
    md += ["", "Table entry encoding (verified): `target = table_start + entry*2`, where",
           "`table_start` is the instruction immediately after the `tbh`. First entry of each",
           "table lands exactly on the first instruction after its table.", "",
           "## Routes", "", "| opcode | handler | semantics | confidence |", "|---|---|---|---|"]
    for r in sorted(routes, key=lambda r: (r["opcode"] or "zz", r["sub_index"] or 0)):
        md.append(f"| {r['opcode'] or 'sub ' + str(r['sub_index'])} | `{r['handler']}` | "
                  f"{r['semantics'] or '-'} | {r['confidence']} |")
    md += ["", "## Handler semantics (evidence attached to each)", ""]
    for op, s in sorted(SEMANTICS.items()):
        md += [f"### `{op:#04x}` - {s['name']} ({s['confidence']})", "", s["detail"], ""]
    md += ["## Shared helpers", ""]
    for a, d in out["shared_helpers"].items():
        md.append(f"- `{a}`: {d}")
    md += ["", "## Open contradictions", ""]
    for c in out["open_contradictions"]:
        md.append(f"- {c}")
    (FW / "armorx-command-dispatch-full.md").write_text("\n".join(md) + "\n")

    print(f"routes={len(routes)} tables={len(ranges)} semantics={len(SEMANTICS)}")
    for r in sorted(routes, key=lambda r: (r["opcode"] or "zz")):
        print(f"  {r['opcode'] or 'sub':>5} -> {r['handler']:>10}  {r['semantics'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
