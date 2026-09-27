#!/usr/bin/env python3
"""Scan Blutter asm for frame-builder functions and decode their opcode bytes.

A frame-builder is a function whose immediate stream contains the Smi-encoded
value of 0xA5 (330), 0xA4 (328) or 0xAB (342).  Smi immediates are stored
doubled, so every EVEN immediate <= 0x200 is shown decoded (/2); odd values are
plain ints (loop bounds, indexes) and are marked raw.

Usage: python3 scripts/opcode_scan.py <asm_dart_file_or_dir> <out.json> [--md out.md]
"""
import json
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>\$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CALL2 = re.compile(r'bl\s+#(0x[0-9a-f]+)\s+; (.*)$')
CLASS = re.compile(r'^class\s+(\S+)')
IMM = re.compile(r'\bmov\s+x\d+, #(-?0x[0-9a-f]+|\d+)')
ANN = re.compile(r'^\s*//\s+r\d+ = -?(\d+)\s*$')
MARK = {165: 'A5', 164: 'A4', 171: 'AB'}


def decode(v):
    if v % 2 == 0 and 0 <= v <= 0x200:
        return v // 2
    return None


def scan_file(path):
    fns = []
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
                cur = {'class': cls, 'name': (m.group(1) + m.group(2) + ')').strip(),
                       'addr': None, 'bytes': [], 'calls': [], 'raw': []}
                fns.append(cur)
                continue
            if cur is None:
                continue
            if cur['addr'] is None:
                a = ADDR.search(line)
                if a:
                    cur['addr'] = a.group(1)
                    continue
            for i in IMM.findall(line):
                v = int(i, 16) if i.startswith(('0x', '-0x')) else int(i)
                if abs(v) > 0x400 or v < 0:
                    continue
                d = decode(v)
                if d is None:
                    cur['raw'].append(v)
                elif not cur['bytes'] or cur['bytes'][-1] != d:
                    cur['bytes'].append(d)
            c = CALL2.search(line)
            if c and 'Stub' not in c.group(2):
                nm = c.group(2).split(';')[-1].strip()
                nm = nm.split(']')[-1].strip()
                nm = re.sub(r'\s*\(0x[0-9a-f]+\)\s*$', '', nm)
                if nm and (not cur['calls'] or cur['calls'][-1] != nm):
                    cur['calls'].append(nm)
    return [f for f in fns if f['addr'] and any(b in MARK for b in f['bytes'])]


def scan(root):
    res = {}
    if os.path.isfile(root):
        files = [root]
    else:
        files = []
        for dp, _d, fs in os.walk(root):
            files += [os.path.join(dp, f) for f in sorted(fs) if f.endswith('.dart')]
    for p in files:
        fns = scan_file(p)
        if fns:
            res[p] = fns
    return res


def main():
    root, out = sys.argv[1], sys.argv[2]
    res = scan(root)
    json.dump(res, open(out, 'w'), indent=1)
    n = sum(len(v) for v in res.values())
    print('%d frame-builder functions in %d files -> %s' % (n, len(res), out))
    for p, fns in sorted(res.items()):
        print('\n## %s' % p)
        for f in fns:
            head = ' '.join('%02X' % b if b in MARK else '%02X' % b for b in f['bytes'][:14])
            print('  %-58s @%s  [%s]' % (f['name'][:58], f['addr'], head))


if __name__ == '__main__':
    main()
