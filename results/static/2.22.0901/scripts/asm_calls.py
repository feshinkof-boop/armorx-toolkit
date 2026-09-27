#!/usr/bin/env python3
"""Distil a Blutter asm file into a compact per-function call/immediate trace.

Usage: python3 scripts/asm_calls.py <file.dart> [--grep PATTERN] [--max-fns N]

Output per function:
    function name  @addr
      calls:   names of called Dart functions (in order, deduped)
      imms:    distinct immediate constants (printed as raw decimal and hex)
      pool:    object-pool references touched ([pp+0x...])
"""
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>\$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CALL = re.compile(r'; (?:\[[^\]]+\] )?::?([A-Za-z_$][\w$.<>]*)')
CALL2 = re.compile(r'bl\s+#(0x[0-9a-f]+)\s+; (.*)$')
POOL = re.compile(r'\[(pp\+0x[0-9a-f]+)\]')
IMM = re.compile(r'\bmov\s+x\d+, #(-?0x[0-9a-f]+|\d+)')
CLASS = re.compile(r'^class\s+(\S+)')


def trace(path, only=None, max_fns=None):
    out = []
    cur = None
    cls = None
    with open(path, errors='replace') as f:
        for line in f:
            m = CLASS.match(line)
            if m:
                cls = m.group(1)
                continue
            m = FN_HEAD.match(line)
            if m:
                cur = {'cls': cls, 'name': (m.group(1) + m.group(2) + ')').strip(), 'addr': None,
                       'calls': [], 'imms': [], 'pool': []}
                out.append(cur)
                continue
            if cur is None:
                continue
            if cur['addr'] is None:
                a = ADDR.search(line)
                if a:
                    cur['addr'] = a.group(1)
                    continue
            c = CALL2.search(line)
            if c and 'Stub' not in c.group(2):
                nm = c.group(2).split(';')[-1].strip()
                if '[' in nm:
                    nm = nm.split(']')[-1].strip()
                nm = re.sub(r'\s*\(0x[0-9a-f]+\)\s*$', '', nm)
                if nm and (not cur['calls'] or cur['calls'][-1] != nm):
                    cur['calls'].append(nm)
            for p in POOL.findall(line):
                if p not in cur['pool']:
                    cur['pool'].append(p)
            for i in IMM.findall(line):
                v = int(i, 16) if i.startswith(('0x', '-0x')) else int(i)
                if v not in cur['imms']:
                    cur['imms'].append(v)
                # ordered immediate stream from blutter annotations.
                # Annotation value == instruction immediate. Smi values are even
                # (encoded == 2 x logical value); odd values are plain ints.
                if re.match(r'^\s*//\s+r\d+ = -?\d+\s*$', line):
                    m2 = re.match(r'^\s*//\s+r\d+ = (-?\d+)\s*$', line)
                    v2 = int(m2.group(1))
                    if abs(v2) <= 0x400:
                        cur.setdefault('seq', []).append(
                            '%d' % (v2 // 2) if v2 % 2 == 0 else '%d(raw)' % v2)
    return [c for c in out if c['calls'] or c.get('seq')]


def main():
    path = sys.argv[1]
    only = None
    maxf = None
    if '--grep' in sys.argv:
        only = sys.argv[sys.argv.index('--grep') + 1]
    if '--max-fns' in sys.argv:
        maxf = int(sys.argv[sys.argv.index('--max-fns') + 1])
    res = trace(path)
    n = 0
    for c in res:
        if only and not re.search(only, c['name'], re.I):
            continue
        n += 1
        if maxf and n > maxf:
            break
        print('%s :: %s  @%s' % (c['cls'] or '?', c['name'], c['addr']))
        print('   calls: %s' % '; '.join(c['calls'][:24]))
        imms = ', '.join('%d/0x%x' % (v, v & 0xffffffff) for v in c['imms'][:24])
        if imms:
            print('   imms:  %s' % imms)
        if c['pool']:
            print('   pool:  %s' % ' '.join(c['pool'][:12]))


if __name__ == '__main__':
    main()
