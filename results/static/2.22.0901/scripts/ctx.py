#!/usr/bin/env python3
"""Print the asm context around one or more code addresses in a Blutter asm tree.

Usage: ctx.py <asm_dir> <0xaddr> [<0xaddr> ...] [--before N] [--after N]
"""
import os
import re
import sys

FN_HEAD = re.compile(r'^  \S.*\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
LINE = re.compile(r'^\s*//\s*(0x[0-9a-f]+):')


def find(root, want, before, after):
    seen = set()
    for dp, _d, fs in os.walk(root):
        for f in sorted(fs):
            if not f.endswith('.dart'):
                continue
            p = os.path.join(dp, f)
            if '/generated/' in p:
                continue
            src = open(p, errors='replace').read().split('\n')
            for i, l in enumerate(src):
                m = LINE.match(l)
                if not m or m.group(1) not in want:
                    continue
                if '** addr' in l:
                    continue
                key = (p, m.group(1))
                if key in seen:
                    continue
                seen.add(key)
                # enclosing function header
                fname = '?'
                for j in range(i, -1, -1):
                    if FN_HEAD.match(src[j]) and 'addr:' not in src[j]:
                        fname = src[j].strip()[:-1].strip()
                        break
                print('=' * 100)
                print('%s  %s  -> %s' % (p.split('asm/')[-1], m.group(1), fname))
                print('=' * 100)
                for k in range(max(0, i - before), min(len(src), i + after)):
                    mark = '>>' if k == i else '  '
                    m2 = LINE.match(src[k])
                    if m2 and m2.group(1) in want and k != i:
                        print('%s ---- target %s ----' % (mark, m2.group(1)))
                    print('%s%s' % (mark, src[k].replace('    // ', '')[:150]))


if __name__ == '__main__':
    root = sys.argv[1]
    args = sys.argv[2:]
    before, after = 18, 22
    if '--before' in args:
        before = int(args[args.index('--before') + 1])
    if '--after' in args:
        after = int(args[args.index('--after') + 1])
    want = set(a for a in args if a.startswith('0x'))
    find(root, want, before, after)