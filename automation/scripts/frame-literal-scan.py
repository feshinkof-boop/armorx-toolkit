#!/usr/bin/env python3
"""Reconstruct wire frames from Blutter Dart-AOT assembly frame literals.

A frame in this app is built as a Dart `List<int>` literal, which the AOT image materialises as
AllocateArray + StoreField-per-element. Every stored element is a *tagged Smi*, so the byte value
is the printed immediate halved:

    0xA5 -> `r16 = 330`   (330 >> 1 = 165 = 0xA5)
    0xFC -> `r17 = 504`,  0xF7 -> `494`,  0xF6 -> `492`,  0x80 -> `256`

Blutter prints the Smi either as `mov x16, #0x14a` (4.0.8) or as a pool load `r17 = 504`
(2.2x builds); both are handled. Field offsets map to indices as `index = (offset - 0xF) / 4`,
because index 0 lives at field_f.

Usage:  frame-literal-scan.py <blutter_out/asm/moojiang> [more trees...]
Output: JSON on stdout: one record per reconstructed frame literal.
"""

import json
import pathlib
import re
import sys

# opcode byte -> feature, for filtering/annotation only (never for inference)
OPCODES = {0xF7: "F7", 0xF6: "F6", 0xFC: "FC", 0xD2: "D2", 0xD6: "D6", 0x0B: "0B", 0xD8: "D8"}

RE_IMM = re.compile(r"^\s*//\s*0x[0-9a-f]+:\s*r(\d+) = (\d+)\s*$")
RE_MOV = re.compile(r"^\s*//\s*0x[0-9a-f]+:\s*mov\s+x(\d+), #(0x[0-9a-f]+|\d+)")
RE_STORE = re.compile(r"^\s*//\s*0x([0-9a-f]+):\s*StoreField: r(\d+)->field_([0-9a-f]+) = r(\d+)")
RE_ZR = re.compile(r"^\s*//\s*0x([0-9a-f]+):\s*StoreField: r(\d+)->field_([0-9a-f]+) = rZR")
RE_ARR = re.compile(r"^\s*//\s*0x[0-9a-f]+:\s*ArrayStore: r(\d+)\[(\d+)\] = r(\d+)")
RE_STUR_OFF = re.compile(r"^\s*//\s*0x[0-9a-f]+:\s*stur\s+w\d+, \[x(\d+), #(0x[0-9a-f]+)\]")
RE_ADDR = re.compile(r"^\s*//\s*0x([0-9a-f]+):")


def funcs_of(lines):
    out = []
    for i, l in enumerate(lines):
        if l.rstrip().endswith("{") and not l.strip().startswith("//") and l.startswith("  "):
            for j in (i + 1, i + 2):
                if j < len(lines) and "addr: 0x" in lines[j]:
                    out.append((int(re.search(r"addr: (0x[0-9a-f]+)", lines[j]).group(1), 16),
                                l.strip()[:-1].strip()))
                    break
    out.sort()
    return out


def owner(fs, addr):
    prev = None
    for a, n in fs:
        if a <= addr:
            prev = (a, n)
        else:
            break
    return prev


def reconstruct(lines, start, span=90):
    """Walk forward from an AllocateArrayStub line, collecting element stores."""
    regs = {}
    elems = {}
    for i in range(start, min(start + span, len(lines))):
        l = lines[i]
        mi = RE_IMM.match(l)                     # pool load: the printed number IS the Smi
        if mi:
            regs[mi.group(1)] = int(mi.group(2))
            continue
        mm = RE_MOV.match(l)                     # immediate move: parse hex or decimal
        if mm:
            raw = mm.group(2)
            regs[mm.group(1)] = int(raw, 16) if raw.startswith("0x") else int(raw)
            continue
        m = RE_STORE.match(l)
        if m:
            addr, _base, off, reg = m.group(1), m.group(2), int(m.group(3), 16), m.group(4)
            if reg in regs:
                elems[(off - 0xF) // 4] = regs[reg] // 2
            continue
        m = RE_ZR.match(l)
        if m:
            elems[(int(m.group(3), 16) - 0xF) // 4] = 0
            continue
        ma = RE_ARR.match(l)
        if ma and i + 1 < len(lines):
            ms = RE_STUR_OFF.match(lines[i + 1])
            if ms and ms.group(1) == ma.group(1) and ma.group(3) in regs:
                elems[(int(ms.group(2), 16) - 0xF) // 4] = regs[ma.group(3)] // 2
            continue
        if "getCheckSum" in l or "write(" in l or "AllocateGrowableArray" in l:
            saw_checksum = "getCheckSum" in l
            break
        if i > start and RE_ADDR.match(l) and "ret" in l:
            break
    return elems


def scan_tree(root):
    root = pathlib.Path(root)
    records = []
    for f in sorted(root.rglob("*.dart")):
        lines = f.read_text(errors="ignore").splitlines()
        if "AllocateArrayStub" not in "\n".join(lines):
            continue
        fs = funcs_of(lines)
        for ln, l in enumerate(lines, 1):
            if "AllocateArrayStub" not in l:
                continue
            elems = reconstruct(lines, ln - 1)
            if len(elems) < 3 or 2 not in elems:
                continue
            n = elems.get(1)
            frames = [elems[i] for i in sorted(elems)]
            if n is not None and len(frames) > n:
                frames = frames[:n]
            cks = None
            complete = (n is not None and len(frames) == n)
            if complete and n >= 4:
                cks = sum(frames[:n - 1]) & 0xFF     # sum8 over every byte before the trailer
                frames[n - 1] = cks
            ops = owners = None
            addrs = re.findall(r"0x[0-9a-f]{6,}", l)
            owners = owner(fs, int(addrs[0], 16)) if addrs else None
            records.append({
                "file": str(f.relative_to(root)),
                "line": ln,
                "func": owners[1] if owners else None,
                "func_addr": hex(owners[0]) if owners else None,
                "length_byte": n,
                "bytes": " ".join("%02X" % b for b in frames),
                "checksum": ("%02X" % cks) if cks is not None else None,
                "complete": complete,   # every payload byte was a static literal
                "opcode": OPCODES.get(elems.get(2)),
            })
    return records


if __name__ == "__main__":
    out = []
    for tree in sys.argv[1:]:
        for r in scan_tree(tree):
            r["tree"] = tree
            out.append(r)
    print(json.dumps(out, indent=1))
