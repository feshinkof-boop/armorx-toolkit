#!/usr/bin/env python3
"""Static disassembly of selected libapp.so regions (no hardware, no network)."""
import sys, struct, subprocess
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

def load_segments(path):
    out = subprocess.run(["readelf", "-lW", path], capture_output=True, text=True).stdout
    segs = []
    for line in out.splitlines():
        if line.strip().startswith("LOAD"):
            p = line.split()
            # Type Offset VirtAddr PhysAddr FileSiz MemSiz Flg Align
            off = int(p[1], 16); va = int(p[2], 16); fs = int(p[4], 16); fl = p[6]
            segs.append((va, off, fs, fl))
    return segs

def va_to_off(segs, va):
    for (sva, soff, fs, fl) in segs:
        if sva <= va < sva + fs:
            return soff + (va - sva)
    return None

def disas(path, va, length):
    segs = load_segments(path)
    off = va_to_off(segs, va)
    if off is None:
        print(f"  !! va {va:#x} not in any LOAD segment"); return
    with open(path, "rb") as f:
        f.seek(off); code = f.read(length)
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    for ins in md.disasm(code, va):
        b = code[ins.address - va: ins.address - va + ins.size]
        print(f"  {ins.address:#010x}: {b.hex():<8} {ins.mnemonic:<10} {ins.op_str}")

if __name__ == "__main__":
    path, va, length = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
    print(f"# {path} @ {va:#x} (+{length:#x})")
    disas(path, va, length)
