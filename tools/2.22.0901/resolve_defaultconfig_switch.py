#!/usr/bin/env python3
"""Resolve `Define::defaultConfig()`'s enum -> default-image mapping by simulating the branch tree.

The function is a switch on `curDevice.field_7` (the device-type enum), compiled as a chain of
`cmp x2, #N` / `b.gt` tests. Each case returns a JSON array literal that is parsed into the
device's default configuration image.

Usage: python3 scripts/resolve_defaultconfig_switch.py <define.dart> <out.json>
"""
import json
import re
import sys

LINE = re.compile(r'^\s*//\s*(0x[0-9a-f]+):\s*(.+?)\s*$')
ARR = re.compile(r'r0 = "(\[[0-9,\s]+\])"')
CMPX = re.compile(r'^cmp\s+x2,\s*#(\d+)$')
BGT = re.compile(r'^b\.gt\s+#(0x[0-9a-f]+)$')
BNE = re.compile(r'^b\.ne\s+#(0x[0-9a-f]+)$')
BEQ = re.compile(r'^b\.eq\s+#(0x[0-9a-f]+)$')
B = re.compile(r'^b\s+#(0x[0-9a-f]+)$')


def main():
    path, outp = sys.argv[1], sys.argv[2]
    raw = open(path).read().split('\n')
    start = next(i for i, l in enumerate(raw) if re.match(r'\s*String defaultConfig\(\)', l))
    end = start
    for j in range(start, len(raw)):
        if re.match(r'^\s*\}\s*$', raw[j]):
            end = j
            break
    code = {}
    for l in raw[start:end + 1]:
        m = LINE.match(l)
        if m and m.group(2) and not m.group(2).startswith('//'):
            code.setdefault(m.group(1), m.group(2))  # first (real instruction) wins

    results = []
    seen = set()

    def sim(addr, lo, hi, stack, depth=0):
        if depth > 400 or addr is None:
            return
        key = (addr, lo, hi)
        if key in seen:
            return
        seen.add(key)
        for _ in range(2000):
            text = code.get(addr)
            if text is None:
                if stack:
                    addr, lo, hi = stack.pop()
                    continue
                return
            am = ARR.search(text)
            if am:
                vals = [int(x) for x in am.group(1).strip('[]').split(',')]
                results.append({'addr': addr, 'enum_lo': lo, 'enum_hi': hi,
                                'length': len(vals),
                                'declared_length': int.from_bytes(bytes(vals[2:4]), 'big') if len(vals) >= 4 else None,
                                'values': vals})
            m = CMPX.match(text)
            if m:
                addr = next_addr(addr)
                continue
            m = BGT.match(text)
            if m:
                # taken: x2 > last cmp value ; fallthrough: x2 <= value
                v = pending_cmp
                sim(m.group(1), max(lo, v + 1), hi, stack, depth + 1)
                hi = min(hi, v)
                addr = next_addr(addr)
                continue
            m = BNE.match(text) or BEQ.match(text)
            if m:
                sim(m.group(1), lo, hi, stack, depth + 1)
                addr = next_addr(addr)
                continue
            m = B.match(text)
            if m:
                addr = m.group(1)
                continue
            if text.startswith('ret') or 'return' in text.lower():
                if stack:
                    addr, lo, hi = stack.pop()
                    continue
                return
            addr = next_addr(addr)
        return

    addrs = sorted(code)
    def next_addr(a):
        i = addrs.index(a)
        return addrs[i + 1] if i + 1 < len(addrs) else None

    # entry: after `LoadField: r2 = r0->field_7`
    entry = None
    for a in addrs:
        if code[a].startswith('LoadField') and 'field_7' in code[a]:
            entry = a
            break
    pending_cmp = 0
    # set pending_cmp when CMPX matched: emulate by a mutable holder
    class Holder:
        v = 0
    sim(entry, 1, 64, [])
    json.dump(results, open(outp, 'w'), indent=1)
    for r in results:
        print('enum %s..%s -> len=%-4s decl=%-5s @%s' % (
            r['enum_lo'], r['enum_hi'], r['length'], r['declared_length'], r['addr']))


if __name__ == '__main__':
    main()
