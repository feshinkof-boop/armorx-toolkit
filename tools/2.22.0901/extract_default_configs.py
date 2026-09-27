#!/usr/bin/env python3
"""Extract the code-literal default configuration images from define.dart.

`Define::defaultConfig()` returns a JSON-ish array literal (as a Dart String) that is parsed
into the byte image for a device. The literals are the app's *embedded* default configs:
this is the only place a complete config image exists statically (no binary asset holds one).

Usage: python3 scripts/extract_default_configs.py <define.dart> <outdir>
"""
import json
import os
import re
import sys


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def main():
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    lines = open(src).read().split('\n')

    # device-name context: track the most recent string constant compared/loaded per function
    found = []
    ctx = []
    for i, l in enumerate(lines):
        m = re.search(r'r0 = "([^"]{1,64})"', l)
        if m and not m.group(1).startswith('['):
            ctx.append((i, m.group(1)))
            ctx = ctx[-8:]
        arr = re.search(r'r0 = "(\[[0-9,\s]+\])"', l)
        if not arr:
            continue
        vals = [int(x) for x in arr.group(1).strip('[]').split(',') if x.strip() != '']
        if len(vals) < 40:
            continue
        near = [c for c in ctx if c[0] >= i - 60]
        dev = near[-1][1] if near else '?'
        found.append({'line': i + 1, 'device_context': dev, 'bytes': vals})

    # the same literal repeats across branches; keep unique byte strings
    seen, uniq = set(), []
    for f in found:
        key = bytes(f['bytes'])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)

    index = []
    for n, f in enumerate(uniq):
        b = bytes(f['bytes'])
        declared = int.from_bytes(b[2:4], 'big') if len(b) >= 4 else None
        info = {
            'file': os.path.basename(src), 'line': f['line'],
            'device_context': f['device_context'],
            'length': len(b), 'declared_length_bytes_2_3': declared,
            'declared_matches_total': declared == len(b),
            'crc16_field_bytes_0_1': '0x%04X' % int.from_bytes(b[0:2], 'big'),
            'crc16_over_2_143_style': '0x%04X' % crc16_modbus(b[2:]),
            'mapKeys_first16': list(b[-32:-16]) if len(b) >= 32 else None,
            'mapKeys_last16': list(b[-16:]) if len(b) >= 32 else None,
        }
        name = 'default_%03d_device_%s_len_%d.json' % (
            n, re.sub(r'[^A-Za-z0-9_-]', '_', f['device_context'])[:24], len(b))
        info['raw_name'] = name
        with open(os.path.join(outdir, name), 'w') as fh:
            json.dump({'meta': info, 'bytes': f['bytes'],
                       'hex': b.hex(' '),
                       'as_c_array': ', '.join('0x%02X' % x for x in b)}, fh, indent=1)
        index.append(info)

    with open(os.path.join(outdir, 'index.json'), 'w') as fh:
        json.dump({'count': len(index), 'images': index}, fh, indent=1)
    for info in index:
        print('%-46s len=%-4d decl=%-4s crc=%-6s ctx=%s' % (
            info['raw_name'], info['length'], info['declared_matches_total'],
            info['crc16_field_bytes_0_1'], info['device_context']))


if __name__ == '__main__':
    main()
