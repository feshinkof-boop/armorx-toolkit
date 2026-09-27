#!/usr/bin/env python3
"""Opcode dispatch census for a Blutter asm tree (Dart 2.17.5 dialect).

Two dispatch idioms appear in the 2.17.5 tree:

  A. integer equality:      r16 = 478 ... bl _IntegerImplementation::==
     (Smi-encoded opcode; 478/2 = 239 = 0xEF)
  B. direct compare:        cmp w0, #0x1de   (Smi) or  cmp x1, #0xa5  (RAW byte)

Both are reported, with the enclosing class/function/address so each comparison
can be attributed to the handler it belongs to.  intl string-table files are
skipped (they contain every small integer as noise).

Usage: python3 dispatch_census.py <asm_dir> <out.json> [--md out.md]
"""
import json
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CLASS = re.compile(r'^class\s+(\S+)')
SETR16 = re.compile(r'^\s*//\s+0x([0-9a-f]+):\s+r16 = (-?\d+)\s*$')
EQ = re.compile(r'^\s*//\s+0x[0-9a-f]+:\s+r0 = ==\(\)')
CMP = re.compile(r'^\s*//\s+0x([0-9a-f]+):\s+cmp\s+(?:x|w)(\d+),\s+#(0x[0-9a-f]+)')
IMMANN = re.compile(r'^\s*//\s+0x([0-9a-f]+):\s+r(\d+) = (-?\d+)\s*$')


def files_of(root):
    if os.path.isfile(root):
        return [root]
    out = []
    for dp, _d, fs in os.walk(root):
        for f in sorted(fs):
            if not f.endswith('.dart'):
                continue
            p = os.path.join(dp, f)
            if '/generated/' in p:
                continue
            out.append(p)
    return out


def main():
    root, outp = sys.argv[1], sys.argv[2]
    md = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
    rows = []
    for p in files_of(root):
        cur = cls = addr = None
        pend = None      # pending r16 = N
        pend_line = None
        for line in open(p, errors='replace'):
            m = CLASS.match(line)
            if m:
                cls = m.group(1)
                continue
            m = FN_HEAD.match(line)
            if m:
                cur = (m.group(1) + m.group(2) + ')').strip()
                addr = None
                pend = None
                continue
            if addr is None:
                a = ADDR.search(line)
                if a:
                    addr = a.group(1)
                    continue
            m = SETR16.match(line)
            if m:
                pend = int(m.group(2))
                pend_line = '0x' + m.group(1)
                continue
            if pend is not None and EQ.search(line):
                v = pend
                if v % 2 == 0 and 0 < v // 2 <= 0xFF:
                    rows.append({'file': os.path.relpath(p, root), 'class': cls,
                                 'function': cur, 'addr': addr, 'kind': 'eq_smi',
                                 'opcode': '0x%02X' % (v // 2), 'site': pend_line})
                pend = None
                continue
            m = CMP.match(line)
            if m:
                v = int(m.group(3), 16)
                if v % 2 == 0 and 0 < v // 2 <= 0xFF and v >= 2:
                    rows.append({'file': os.path.relpath(p, root), 'class': cls,
                                 'function': cur, 'addr': addr, 'kind': 'cmp_smi_or_raw',
                                 'opcode': '0x%02X' % (v // 2), 'site': '0x' + m.group(1),
                                 'raw': v})
                elif 0 < v <= 0xFF:
                    rows.append({'file': os.path.relpath(p, root), 'class': cls,
                                 'function': cur, 'addr': addr, 'kind': 'cmp_raw',
                                 'opcode': '0x%02X' % v, 'site': '0x' + m.group(1),
                                 'raw': v})
                continue
    json.dump(rows, open(outp, 'w'), indent=1)
    if md:
        with open(md, 'w') as f:
            f.write('| opcode | kind | raw imm | file | class | function | addr | site |\n')
            f.write('|---|---|---|---|---|---|---|---|\n')
            for r in rows:
                f.write('| %s | %s | %d | %s | %s | %s | %s | %s |\n' % (
                    r['opcode'], r['kind'], r.get('raw', 0), r['file'], r['class'] or '',
                    r['function'], r['addr'], r['site']))
    from collections import Counter
    c = Counter(r['opcode'] for r in rows)
    print('%d dispatch comparisons; %d distinct opcodes' % (len(rows), len(c)))
    for op, n in sorted(c.items()):
        print('  %s  x%d' % (op, n))
    return rows


if __name__ == '__main__':
    main()