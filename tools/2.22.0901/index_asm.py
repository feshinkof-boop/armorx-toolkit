#!/usr/bin/env python3
"""Build a compact class/function index from a Blutter asm tree.

Usage: python3 scripts/index_asm.py <asm_dir> <out.md>
"""
import os
import re
import sys

CLS = re.compile(r'^class\s+(\S+)\s+extends\s+(\S+)')
FN = re.compile(r'^\s{2}(?:static\s+|late\s+|final\s+|const\s+)*([A-Za-z_<>\$\[][^\n]*?)\s*\(.*\)\s*\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+), size: (0x[0-9a-f]+)')


def scan(path):
    out = []
    cur = None
    pending = None
    with open(path, errors='replace') as f:
        for i, line in enumerate(f, 1):
            m = CLS.match(line)
            if m:
                cur = m.group(1)
                out.append(('class', cur, m.group(2), i, None, None))
                continue
            m = FN.match(line)
            if m:
                pending = (m.group(1).strip(), i)
                continue
            m = ADDR.search(line)
            if m and pending:
                out.append(('fn', cur, pending[0], pending[1], m.group(1), m.group(2)))
                pending = None
    return out


def main():
    root, out = sys.argv[1], sys.argv[2]
    lines = []
    n = 0
    for dirpath, _dirs, files in os.walk(root):
        for fn in sorted(files):
            if not fn.endswith('.dart'):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            items = scan(p)
            if not items:
                continue
            lines.append('## %s\n' % rel)
            for kind, cls, name, ln, addr, size in items:
                if kind == 'class':
                    lines.append('- class **%s** extends %s (line %d)' % (name, cls, ln))
                else:
                    lines.append('  - `%s` @%s size %s (line %d)%s' % (
                        name, addr, size, ln, (' [in %s]' % cls) if cls else ''))
            lines.append('')
            n += len(items)
    open(out, 'w').write('\n'.join(lines))
    print('indexed %d items from %s -> %s' % (n, root, out))


if __name__ == '__main__':
    main()
