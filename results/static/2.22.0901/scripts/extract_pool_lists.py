#!/usr/bin/env python3
"""Extract Dart ObjectPool list/string literals from Blutter's pp.txt.

Blutter writes one object per line in pp.txt. Growing Arrays are printed as
indexed elements, e.g.

    0x... [ 4] #List (2 elements) [ 0]: 0x... #63 (Smi: 4)
                                                  [ 1]: 0x... #1ac (Smi: 214)

This script recovers every list literal (integers / strings) deterministically so
byte templates and opcode tables never have to be transcribed by hand.

Usage:
    python3 scripts/extract_pool_lists.py <pp.txt> <out.json> [--min N]
"""
import argparse
import collections
import json
import re

# line shapes seen in blutter pp.txt
RE_ELEM = re.compile(r'\[ *(\d+)\]:\s*(.*)$')
RE_SMI = re.compile(r'#([0-9a-f]+) \(Smi: (-?\d+)\)')
RE_STR = re.compile(r'#(?:String|OneByteString|TwoByteString)\s+"(.*)"\s*\(length: (\d+)\)')
RE_HEAPOBJ = re.compile(r'#(?:String|OneByteString|TwoByteString)\b')
RE_LISTHEAD = re.compile(r'#List \((\d+) elements\)')
RE_ARRAYHEAD = re.compile(r'#Array \((\d+) elements\)')


def parse_inline(text):
    """Parse blutter's single-line form:  [pp+0x48] List(5) [0x1, 0x2, Null]"""
    out = []
    for m in re.finditer(r'^\[(pp\+0x[0-9a-f]+)\]\s+(List|Array)\((\d+)\)\s+\[(.*)\]\s*$', text, re.M):
        addr, kind, n, body = m.groups()
        items = []
        for tok in body.split(','):
            tok = tok.strip()
            if not tok:
                continue
            if tok in ('Null', 'null'):
                items.append(None)
            elif tok.startswith('0x') and re.fullmatch(r'0x[0-9a-f]+', tok):
                items.append(int(tok, 16))
            else:
                mm = re.match(r'0x([0-9a-f]+)\s+\(Smi:\s*(-?\d+)\)', tok)
                if mm:
                    items.append(int(mm.group(2)))
                else:
                    items.append({'raw': tok})
        out.append({'addr': addr, 'kind': kind, 'count': int(n), 'len': len(items), 'items': items})
    return out


def parse(path, min_len=1):
    text = open(path, 'r', errors='replace').read()
    inline = parse_inline(text)
    if inline:
        return [r for r in inline if r['len'] >= min_len]
    lists = collections.OrderedDict()
    cur = None
    head = None
    with open(path, 'r', errors='replace') as f:
        for line in f:
            m = RE_LISTHEAD.search(line) or RE_ARRAYHEAD.search(line)
            if m:
                head = int(m.group(1))
                cur = collections.OrderedDict()
                key = line.split('#')[0].strip()
                lists[key] = {'count': head, 'items': cur}
                continue
            m = RE_ELEM.search(line)
            if m and cur is not None:
                idx, rest = int(m.group(1)), m.group(2)
                smi = RE_SMI.search(rest)
                if smi:
                    cur[idx] = int(smi.group(2))
                    continue
                s = RE_STR.search(rest)
                if s:
                    cur[idx] = {'str': s.group(1)}
                    continue
                cur[idx] = {'raw': rest.strip()}
    out = []
    for k, v in lists.items():
        items = [v['items'][i] for i in sorted(v['items'])]
        if len(items) < min_len:
            continue
        out.append({'addr': k, 'count': v['count'], 'len': len(items), 'items': items})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pp')
    ap.add_argument('out')
    ap.add_argument('--min', type=int, default=1)
    a = ap.parse_args()
    res = parse(a.pp, a.min)
    json.dump(res, open(a.out, 'w'), indent=1)
    ints = [r for r in res if all(isinstance(i, int) for i in r['items'])]
    print('lists=%d  all-int lists=%d  bytes-like=%d' % (
        len(res), len(ints), len([r for r in ints if r['len'] >= 4 and max(r['items']) <= 255])))


if __name__ == '__main__':
    main()
