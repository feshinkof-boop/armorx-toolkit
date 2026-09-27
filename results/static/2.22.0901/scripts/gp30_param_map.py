#!/usr/bin/env python3
"""Extract the parameter-block index -> source-field map from GamepadSet30::toList.

In the 2.17.5 tree the serializer stores each field into the 108-element
parameter list with the literal pattern

    LoadField: r11 = r10->field_xx     ; read a GamepadParam30 (or nested) field
    ...
    ArrayStore: r1[N] = r0             ; param[N] = value

so the *destination index* is printed literally and the *source* is the nearest
preceding LoadField on the same register chain.  param[N] lands at config byte
4+N because toList does replaceRange(4, 112, paramList).

Usage: gp30_param_map.py <gamepadset.dart> <out.json> [--start 0x7a1f60 --end 0x7a3fb0]
"""
import json
import re
import sys

LINE = re.compile(r'^\s*//\s*0x([0-9a-f]+):\s+(.*)$')
LOADF = re.compile(r'LoadField: (r\d+) = (r\d+)->field_([0-9a-f]+)')
STORE = re.compile(r'ArrayStore: (r\d+)\[(\d+)\] = (r\d+)')


def main():
    path = sys.argv[1]
    out = sys.argv[2]
    start = 0x7a1f60 if '--start' not in sys.argv else int(sys.argv[sys.argv.index('--start') + 1], 16)
    end = 0x7a3fb0 if '--end' not in sys.argv else int(sys.argv[sys.argv.index('--end') + 1], 16)
    src = open(path, errors='replace').read().split('\n')
    rows = []
    inrange = False
    last_load = {}     # reg -> (srcreg, fieldname)
    pending = []       # (reg, src, field) recent loads
    for l in src:
        m = LINE.match(l)
        if not m:
            continue
        a = int(m.group(1), 16)
        if a < start or a >= end:
            continue
        t = m.group(2)
        lm = LOADF.search(t)
        if lm:
            last_load[lm.group(1)] = (lm.group(2), 'field_' + lm.group(3))
            pending.append((a, lm.group(1), lm.group(2), 'field_' + lm.group(3)))
            pending = [p for p in pending if a - p[0] < 600]
            continue
        sm = STORE.search(t)
        if sm:
            dst, idx, valreg = sm.group(1), int(sm.group(2)), sm.group(3)
            src_expr = last_load.get(valreg)
            rows.append({'site': '0x%x' % a, 'param_index': idx, 'config_byte': 4 + idx,
                         'value_reg': valreg,
                         'source_reg': src_expr[0] if src_expr else None,
                         'source_field': src_expr[1] if src_expr else None})
    json.dump(rows, open(out, 'w'), indent=1)
    seen = {}
    for r in rows:
        seen.setdefault(r['param_index'], r)
    for idx in sorted(seen):
        r = seen[idx]
        print('param[%3d] -> config byte %3d   <- %s (%s) @%s' % (
            idx, r['config_byte'], r['source_field'], r['source_reg'], r['site']))


if __name__ == '__main__':
    main()