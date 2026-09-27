#!/usr/bin/env python3
"""Reconstruct A5/AB/A4 short frames from Blutter asm and emit a command index.

Frame builders in this app follow one template:

    list = [0xA5, total_len, opcode, data..., 0x00 placeholder]
    list[len-1] = getCheckSum(list)          # sum of preceding bytes & 0xFF

Blutter renders the stored Smi values; because Smi immediates are doubled, every
even immediate <= 0x200 in the builder body is decoded as /2 (odd values are
plain ints such as loop bounds / checksum indexes and are ignored).

Usage: python3 scripts/frame_index.py <asm_dir> <out.json> [--md out.md]
"""
import json
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>\$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CLASS = re.compile(r'^class\s+(\S+)')
ANN = re.compile(r'^\s*//\s+r\d+ = -?(\d+)\s*$')
MOV = re.compile(r'^\s*//\s+(0x[0-9a-f]+):\s+mov\s+x\d+, #(-?0x[0-9a-f]+|\d+)')
CALL = re.compile(r'bl\s+#(0x[0-9a-f]+)\s+; (.*)$')

STARTERS = {165: 'A5', 171: 'AB', 164: 'A4'}


def build_frames(seq):
    """seq: list of logical byte candidates in program order."""
    frames = []
    i = 0
    while i < len(seq):
        if seq[i] in STARTERS:
            start = STARTERS[seq[i]]
            if i + 2 < len(seq):
                flen = seq[i + 1]
                op = seq[i + 2]
                if 2 <= flen <= 200:
                    data = seq[i + 3:i + flen]
                    chk = (seq[i] + flen + op + sum(data)) & 0xFF
                    frames.append({'start': start, 'len': flen, 'opcode': op,
                                   'data': data, 'checksum': chk})
                    i += 3
                    continue
        i += 1
    return frames


def scan_file(path):
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
                cur = {'class': cls, 'name': (m.group(1) + m.group(2) + ')').strip(),
                       'addr': None, 'seq': [], 'calls': []}
                out.append(cur)
                continue
            if cur is None:
                continue
            if cur['addr'] is None:
                a = ADDR.search(line)
                if a:
                    cur['addr'] = a.group(1)
                    continue
            m = MOV.match(line)
            if m:
                v = int(m.group(2), 16) if m.group(2).startswith(('0x', '-0x')) else int(m.group(2))
                if v > 0 and v % 2 == 0 and v <= 0x200:
                    cur['seq'].append(v // 2)
                continue
            c = CALL.search(line)
            if c and 'Stub' not in c.group(2):
                nm = c.group(2).split(';')[-1].strip().split(']')[-1].strip()
                nm = re.sub(r'\s*\(0x[0-9a-f]+\)\s*$', '', nm)
                if nm and (not cur['calls'] or cur['calls'][-1] != nm):
                    cur['calls'].append(nm)
    res = []
    for c in out:
        fr = build_frames(c['seq'])
        if fr:
            c['frames'] = fr
            res.append(c)
    return res


def main():
    root, out = sys.argv[1], sys.argv[2]
    md = None
    if '--md' in sys.argv:
        md = sys.argv[sys.argv.index('--md') + 1]
    files = []
    for dp, _d, fs in os.walk(root):
        files += [os.path.join(dp, f) for f in sorted(fs) if f.endswith('.dart')]
    rows = []
    for p in files:
        for fn in scan_file(p):
            rows.append({'file': p, 'class': fn['class'], 'function': fn['name'],
                         'addr': fn['addr'], 'calls': fn['calls'], 'frames': fn['frames']})
    json.dump(rows, open(out, 'w'), indent=1)
    if md:
        with open(md, 'w') as f:
            f.write('# Frame-builder inventory (MYGT 4.0.8, static)\n\n')
            f.write('| file | class | function | addr | frames (checksum recomputed) |\n')
            f.write('|---|---|---|---|---|\n')
            for r in rows:
                fr = ' '.join('[%s len=%d op=%02X d=%s ck=%02X]' % (
                    x['start'], x['len'], x['opcode'],
                    ','.join('%02X' % b for b in x['data']), x['checksum']) for x in r['frames'])
                f.write('| %s | %s | %s | %s | %s |\n' % (r['file'].split('asm/')[-1], r['class'] or '',
                                                          r['function'], r['addr'], fr))
    print('%d frame-builder functions -> %s' % (len(rows), out))


if __name__ == '__main__':
    main()