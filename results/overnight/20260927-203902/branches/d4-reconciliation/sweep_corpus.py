#!/usr/bin/env python3
"""Sweep the evidence corpus for A5/A4 frame-like hex strings and validate checksums.
Read-only. Flags any frame whose trailing byte != sum(rest)&0xFF (deliberate probes excluded)."""
import re, os, json, glob

ROOTS = [
    "/home/salamanka/armorx-lab/results",
    "/home/salamanka/armorx-lab/baselines",
    "/home/salamanka/armorx-lab/ble/virtual-armorx/logs",
    "/home/salamanka/armorx-lab/tests/vectors",
    "/home/salamanka/armorx-lab/frida/traces",
    "/home/salamanka/armorx-research" if False else "/home/salamanka/armorx_research",
    "/home/salamanka/armorx-re/repo",
]
EXCLUDE = ("d4-reconciliation",)  # don't scan our own outputs
pat = re.compile(r'\b(a5|a4)([0-9a-fA-F]{6,40})\b')

seen = {}
for root in ROOTS:
    for dirpath, _, files in os.walk(root):
        if any(x in dirpath for x in EXCLUDE):
            continue
        for fn in files:
            if not fn.lower().endswith(('.md','.json','.jsonl','.txt','.log','.csv','.hex')):
                continue
            p = os.path.join(dirpath, fn)
            try:
                txt = open(p, encoding='utf-8', errors='ignore').read()
            except Exception:
                continue
            for m in pat.finditer(txt):
                h = (m.group(1) + m.group(2)).lower()
                if len(h) % 2:
                    continue
                b = [int(h[i:i+2], 16) for i in range(0, len(h), 2)]
                total = len(b)
                # treat as a frame only if the LEN byte == total length (project convention)
                if b[1] != total or total < 3:
                    continue
                cks = sum(b[:-1]) & 0xFF
                stored = b[-1]
                seen.setdefault(h, {"ok": cks == stored, "recomputed": f"0x{cks:02X}",
                                    "stored": f"0x{stored:02X}", "paths": []})
                if p not in seen[h]["paths"]:
                    seen[h]["paths"].append(p)

bad = {h: v for h, v in seen.items() if not v["ok"]}
print("frames recognized:", len(seen))
print("checksum MISMATCHES:", len(bad))
for h, v in sorted(bad.items()):
    print(f"  {h}  stored={v['stored']} recomputed={v['recomputed']}  ({len(v['paths'])} files) e.g. {v['paths'][0]}")
json.dump({"recognized": len(seen), "mismatches": bad}, open(
    "/home/salamanka/armorx-lab/results/overnight/20260927-203902/branches/d4-reconciliation/corpus-sweep.json","w"), indent=2)
