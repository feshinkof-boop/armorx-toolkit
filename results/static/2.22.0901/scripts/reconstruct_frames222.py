#!/usr/bin/env python3
"""Byte-exact A5/A4/AB frame reconstruction from a Blutter asm tree (Dart 2.17.5 dialect).

Adapted from the 4.0.8 reconstruct_frames.py.  The 2.17.5 tree differs in two ways
that broke the original scanner:

  1. In 2.22 a builder stores the frame length into the list object, and *later*
     the same `field_f` name is reused on OTHER objects (state structs).  The
     original scanner keyed only on the field name, so those later stores
     clobbered the frame's element 0.  Fix: restrict store collection to the
     window that starts at `r0 = AllocateArray()` and ends at the
     `bl ... getCheckSum` call, and only accept stores whose *target register*
     is the array register (r0).
  2. Element position is derived from the actual field offset (field_f=0xf is
     element 0, every further element is +4 bytes) rather than from a fixed
     name list, so field_17/field_1b/... are all handled.

Usage: python3 reconstruct_frames222.py <asm_dir_or_file> <out.json> [--md out.md]
"""
import json
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CLASS = re.compile(r'^class\s+(\S+)')
SETREG = re.compile(r'^\s*//\s+(?:0x[0-9a-f]+:\s+)?(r\d+|x\d+) = (-?\d+)\s*$')
STORE = re.compile(r'^\s*//\s+0x[0-9a-f]+:\s+(?:StoreField: (r\d+)->(field_([0-9a-f]+)) = (r\d+|rZR)|ArrayStore: (r\d+)\[(\d+)\] = (r\d+|rZR))')
ALLOC = re.compile(r'^\s*//\s+(?:0x[0-9a-f]+:\s+)?(r\d+) = AllocateArray\(\)')
CALL = re.compile(r'bl\s+#(0x[0-9a-f]+)\s+; (.*)$')

STARTERS = {0xA5, 0xA4, 0xAB}


def scan_file(path):
    fns = []
    cur = None
    cls = None

    def newfn(name):
        return {'class': cls, 'name': name, 'addr': None, 'regs': {},
                'alloc_len': None, 'stores': [], 'calls': []}

    with open(path, errors='replace') as f:
        for line in f:
            m = CLASS.match(line)
            if m:
                cls = m.group(1)
                continue
            m = FN_HEAD.match(line)
            if m:
                cur = newfn((m.group(1) + m.group(2) + ')').strip())
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
            m = ALLOC.match(line)
            if m:
                cur['alloc_len'] = cur['regs'].get('x2') or cur['regs'].get('r2')
                cur['arr_reg'] = m.group(1)
                cur['in_frame'] = True
                continue
            m = STORE.match(line)
            if m and cur.get('in_frame'):
                if m.group(1):  # StoreField: rTarget->field_XX = rSrc
                    treg, fld, foff, src = m.group(1), m.group(2), int(m.group(3), 16), m.group(4)
                    if treg != cur.get('arr_reg'):
                        cur['in_frame'] = False  # different object -> frame ended
                        continue
                    pos = (foff - 0xf) // 4 if foff >= 0xf else None
                else:  # ArrayStore: rTarget[i] = rSrc
                    treg, idx, src = m.group(5), int(m.group(6)), m.group(7)
                    if treg != cur.get('arr_reg'):
                        cur['in_frame'] = False
                        continue
                    pos = idx + 2
                val = 0 if src == 'rZR' else cur['regs'].get(src)
                if val is None or pos is None:
                    continue
                cur['stores'].append((pos, val))
                continue
            if cur.get('in_frame'):
                c = CALL.search(line)
                if c and 'getCheckSum' in c.group(2):
                    cur['in_frame'] = False
    return fns


def frame_from_stores(fn):
    arr = {}
    for pos, val in fn['stores']:
        if val % 2 or val > 0x800:
            continue
        arr[pos] = val // 2
    if not arr:
        return None
    n = max(arr) + 1
    return [arr.get(i) for i in range(n)]


def extract_frames(arr):
    if not arr or len(arr) < 3 or arr[0] not in STARTERS:
        return []
    flen = arr[1]
    if not flen or not (3 <= flen <= 512):
        return []
    if len(arr) < flen:
        arr = arr + [0] * (flen - len(arr))
    if any(b is None for b in arr[:flen]):
        return []
    if arr[0] == 0xA4:
        op, idx = arr[2], arr[3]
        chk = sum(arr[:flen - 1]) & 0xFF
        return [{'start': 0xA4, 'len': flen, 'opcode': op, 'fragment_index': idx,
                 'data': arr[4:flen - 1], 'stored_checksum': arr[flen - 1],
                 'computed_checksum': chk, 'checksum_ok': arr[flen - 1] in (0, chk)}]
    op = arr[2]
    chk = sum(arr[:flen - 1]) & 0xFF
    return [{'start': arr[0], 'len': flen, 'opcode': op, 'data': arr[3:flen - 1],
             'stored_checksum': arr[flen - 1], 'computed_checksum': chk,
             'checksum_ok': arr[flen - 1] in (0, chk)}]


def main():
    root, out = sys.argv[1], sys.argv[2]
    md = sys.argv[sys.argv.index('--md') + 1] if '--md' in sys.argv else None
    files = []
    if os.path.isfile(root):
        files = [root]
    else:
        for dp, _d, fs in os.walk(root):
            files += [os.path.join(dp, f) for f in sorted(fs) if f.endswith('.dart')]
    rows = []
    for p in files:
        for fn in scan_file(p):
            arr = frame_from_stores(fn)
            frames = extract_frames(arr)
            if frames:
                rows.append({'file': p, 'class': fn['class'], 'function': fn['name'],
                             'addr': fn['addr'], 'array': arr, 'calls': fn['calls'],
                             'frames': frames})
    json.dump(rows, open(out, 'w'), indent=1)
    if md:
        with open(md, 'w') as f:
            f.write('| file | class | function | addr | raw array | frame(s) | ck |\n')
            f.write('|---|---|---|---|---|---|---|\n')
            for r in rows:
                for fr in r['frames']:
                    f.write('| %s | %s | %s | %s | %s | %02X %02X %02X %s | %02X %s |\n' % (
                        r['file'].split('asm/')[-1], r['class'] or '', r['function'], r['addr'],
                        r['array'], fr['start'], fr['len'], fr['opcode'],
                        ' '.join('%02X' % b for b in fr['data']),
                        fr['computed_checksum'], 'OK' if fr['checksum_ok'] else 'MISMATCH'))
    print('%d builders with byte-exact frames -> %s' % (len(rows), out))
    for r in rows:
        for fr in r['frames']:
            print('  %-52s @%s  %02X %02X %02X %s ck=%02X %s' % (
                (r['class'] or '') + '::' + r['function'][:34], r['addr'],
                fr['start'], fr['len'], fr['opcode'],
                ' '.join('%02X' % b for b in fr['data']),
                fr['computed_checksum'], 'OK' if fr['checksum_ok'] else 'MISMATCH'))


if __name__ == '__main__':
    main()