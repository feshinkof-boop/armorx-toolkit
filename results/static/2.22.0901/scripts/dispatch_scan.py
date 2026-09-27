#!/usr/bin/env python3
"""Inventory opcode dispatch sites (response parsers) in Blutter asm.

Finds `cmp wN, #imm` comparisons whose immediate is an Smi-encoded opcode
(even, imm/2 in 0x01..0xFF) and reports them with the enclosing function.

Usage: python3 scripts/dispatch_scan.py <asm_dir> <out.md>
"""
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>\$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CLASS = re.compile(r'^class\s+(\S+)')
CMP = re.compile(r'cmp\s+w\d+, #(0x[0-9a-f]+)')


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = []
    for dp, _d, fs in os.walk(root):
        for fn in sorted(fs):
            if not fn.endswith('.dart'):
                continue
            p = os.path.join(dp, fn)
            cur = cls = addr = None
            seen = set()
            for i, line in enumerate(open(p, errors='replace'), 1):
                m = CLASS.match(line)
                if m:
                    cls = m.group(1)
                    continue
                m = FN_HEAD.match(line)
                if m:
                    cur = (m.group(1) + m.group(2) + ')').strip()
                    addr = None
                    seen = set()
                    continue
                if addr is None:
                    a = ADDR.search(line)
                    if a:
                        addr = a.group(1)
                m = CMP.search(line)
                if m and cur:
                    v = int(m.group(1), 16)
                    if v % 2 == 0 and 2 <= v <= 0x200:
                        b = v // 2
                        key = (p, cur, b)
                        if key not in seen:
                            seen.add(key)
                            rows.append((p, cls, cur, addr, b, i))
    rows.sort(key=lambda r: (r[0], r[3] or '', r[4]))
    with open(out, 'w') as f:
        f.write('| file | class | function | addr | opcode | line |\n|---|---|---|---|---|---:|\n')
        for p, cls, cur, addr, b, ln in rows:
            f.write('| %s | %s | %s | %s | 0x%02X | %d |\n' % (p, cls or '', cur, addr or '', b, ln))
    print('%d dispatch comparisons across %d files -> %s' % (len(rows), len({r[0] for r in rows}), out))


if __name__ == '__main__':
    main()
