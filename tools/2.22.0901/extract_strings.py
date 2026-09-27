#!/usr/bin/env python3
"""Extract printable strings from a binary with file offsets (reproducible).

Usage: python3 scripts/extract_strings.py <binary> <out.txt> [min_len]
"""
import re
import sys

PAT = re.compile(rb'[\x20-\x7e]{%d,}')


def main():
    path, out = sys.argv[1], sys.argv[2]
    minlen = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    data = open(path, 'rb').read()
    pat = re.compile(rb'[\x20-\x7e]{%d,}' % minlen)
    with open(out, 'w') as f:
        for m in pat.finditer(data):
            f.write('0x%08x\t%s\n' % (m.start(), m.group().decode('ascii')))
    print('wrote', out)


if __name__ == '__main__':
    main()
