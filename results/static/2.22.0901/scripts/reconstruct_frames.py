#!/usr/bin/env python3
"""Byte-exact A5/A4/AB frame reconstruction from Blutter asm.

Model of the template used throughout this app:

    l = AllocateArray(n)              # n = total frame length (Smi, encoded 2n)
    l[0] = 0xA5 ; l[1] = n ; l[2] = opcode ; l[3..n-2] = data ; l[n-1] = 0
    l[n-1] = getCheckSum(l)           # (sum of preceding bytes) & 0xFF

Blutter prints array element stores as `StoreField: rX->field_f = rN`,
`StoreField: rX->field_13 = rN` and `ArrayStore: rX[i] = rN`, where the value of
`rN` comes from the nearest preceding annotation (`rN = 123` = Smi, so the byte
is 123/2) or from `rZR` (=0).  Register-map based extraction makes the byte
sequence exact, including the zero checksum placeholder.

Usage: python3 scripts/reconstruct_frames.py <asm_dir> <out.json> [--md out.md]
"""
import json
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>\$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CLASS = re.compile(r'^class\s+(\S+)')
SETREG = re.compile(r'^\s*//\s+(?:0x[0-9a-f]+:\s+)?(r\d+|x\d+) = (-?\d+)\s*$')
SETREG_TA = re.compile(r'^\s*//\s+(r\d+|x\d+) = <')
STORE = re.compile(r'^\s*//\s+0x[0-9a-f]+:\s+(StoreField: (r\d+)->(field_\w+) = (r\d+|rZR)|ArrayStore: (r\d+)\[(\d+)\] = (r\d+|rZR))')
ALLOC = re.compile(r'^\s*//\s+r\d+ = AllocateArray\(\)')
CALL = re.compile(r'bl\s+#(0x[0-9a-f]+)\s+; (.*)$')

STARTERS = {0xA5, 0xA4, 0xAB}


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
                       'addr': None, 'stores': [], 'calls': [], 'alloc': None, 'regs': {}}
                fns.append(cur)
                continue
            if cur is None:
                continue
            if cur['addr'] is None:
                a = ADDR.search(line)
                if a:
                    cur['addr'] = a.group(1)
                    continue
            m = SETREG.match(line)
            if m:
                cur['regs'][m.group(1)] = int(m.group(2))
                continue
            if ALLOC.search(line):
                cur['alloc'] = cur['regs'].get('r2') or cur['regs'].get('x2')
                continue
            m = STORE.match(line)
            if m:
                src = m.group(4) or m.group(7)
                idx = m.group(6)
                field = m.group(3)
                if src == 'rZR':
                    val = 0
                else:
                    val = cur['regs'].get(src)
                if val is None:
                    continue
                cur['stores'].append((field, idx, val))
                continue
            c = CALL.search(line)
            if c and 'Stub' not in c.group(2):
                nm = c.group(2).split(';')[-1].strip().split(']')[-1].strip()
                nm = re.sub(r'\s*\(0x[0-9a-f]+\)\s*$', '', nm)
                if nm and (not cur['calls'] or cur['calls'][-1] != nm):
                    cur['calls'].append(nm)
    return fns


def frame_from_stores(stores, alloc):
    """Map store order to list positions (0xf/0x13 = idx0/1, ArrayStore i -> idx i+2)."""
    vals = []
    for field, idx, val in stores:
        if val % 2 or val > 0x400:
            continue  # not an Smi byte value
        byte = val // 2
        if field in ('field_f',):
            pos = 0
        elif field in ('field_13',):
            pos = 1
        elif field == 'field_1b':
            pos = 3
        elif idx is not None:
            pos = int(idx) + 2
        else:
            pos = None
        vals.append((pos, byte))
    vals = [v for v in vals if v[0] is not None]
    if not vals:
        return None
    n = max(p for p, _ in vals) + 1
    arr = [None] * n
    for p, b in vals:
        arr[p] = b
    return arr


def extract_frames(arr, alloc):
    if not arr or len(arr) < 3 or arr[0] not in STARTERS:
        return []
    flen = arr[1]
    if not flen or not (3 <= flen <= 210):
        return []
    if len(arr) < flen:
        # tolerate a missing trailing placeholder (rZR store not observed)
        arr = arr + [0] * (flen - len(arr))
    if any(b is None for b in arr[:flen]):
        return []
    if arr[0] == 0xA4:
        op, idx = arr[2], arr[3]
        payload = arr[4:flen - 1]
        chk = sum(arr[:flen - 1]) & 0xFF
        return [{'start': 0xA4, 'len': flen, 'opcode': op, 'fragment_index': idx,
                 'data': payload, 'stored_checksum': arr[flen - 1],
                 'computed_checksum': chk, 'checksum_ok': arr[flen - 1] in (0, chk)}]
    op = arr[2]
    data = arr[3:flen - 1]
    chk = (sum(arr[:flen - 1])) & 0xFF
    return [{'start': arr[0], 'len': flen, 'opcode': op, 'data': data,
             'stored_checksum': arr[flen - 1], 'computed_checksum': chk,
             'checksum_ok': arr[flen - 1] in (0, chk)}]


def main():
    root, out = sys.argv[1], sys.argv[2]
    md = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
    files = []
    for dp, _d, fs in os.walk(root):
        files += [os.path.join(dp, f) for f in sorted(fs) if f.endswith('.dart')]
    rows = []
    for p in files:
        for fn in scan_file(p):
            arr = frame_from_stores(fn['stores'], fn['alloc'])
            frames = extract_frames(arr, fn['alloc'])
            if frames:
                rows.append({'file': p, 'class': fn['class'], 'function': fn['name'],
                             'addr': fn['addr'], 'calls': fn['calls'], 'frames': frames})
    json.dump(rows, open(out, 'w'), indent=1)
    if md:
        with open(md, 'w') as f:
            f.write('| file | function | addr | frame | checksum |\n|---|---|---|---|---|\n')
            for r in rows:
                for fr in r['frames']:
                    f.write('| %s | %s::%s | %s | %02X %02X %02X %s | %02X %s |\n' % (
                        r['file'].split('asm/')[-1], r['class'] or '', r['function'], r['addr'],
                        fr['start'], fr['len'], fr['opcode'],
                        ' '.join('%02X' % b for b in fr['data']),
                        fr['computed_checksum'], 'OK' if fr['checksum_ok'] else 'MISMATCH'))
    print('%d builders with byte-exact frames -> %s' % (len(rows), out))


if __name__ == '__main__':
    main()
