#!/usr/bin/env python3
"""Extract embedded default configuration images from a Blutter asm tree.

In the 2.22 tree the per-device default config images are NOT produced by a
`defaultConfig()` switch in define.dart (that function does not exist here).
They appear as JSON-array STRING literals stored into a register right before a
JSON parse / List conversion, inside the widget files (`configs_config.dart`,
`armorx_pro_config_config.dart`, `rainbow_tab_config.dart`).

Each literal is a full config image: bytes 0-1 = CRC (0x0000 placeholder in the
shipped image; the app recomputes it in toList()), bytes 2-3 = total length
big-endian, then the parameter block and mapKeys.

Usage: python3 extract_default_configs222.py <asm_dir> <outdir>
"""
import hashlib
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


ARR = re.compile(r'r0 = "\[([0-9]+(?:, ?[0-9]+){39,})\]"')
FN_HEAD = re.compile(r'^  \S.*\{\s*$')
CLASS = re.compile(r'^class\s+(\S+)')


def main():
    root, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    found = []
    for dp, _d, fs in os.walk(root):
        for fn in sorted(fs):
            if not fn.endswith('.dart') or '/generated/' in dp:
                continue
            p = os.path.join(dp, fn)
            src = open(p, errors='replace').read().split('\n')
            cls = '?'
            for i, l in enumerate(src):
                if l.startswith('class '):
                    cls = l.split()[1]
                m = ARR.search(l)
                if not m:
                    continue
                vals = [int(x) for x in m.group(1).split(',')]
                fnname = '?'
                for j in range(i, -1, -1):
                    if FN_HEAD.match(src[j]) and 'addr:' not in src[j]:
                        fnname = src[j].strip()[:-1].strip()
                        break
                addr = None
                for j in range(i, min(len(src), i + 6)):
                    mm = re.search(r'// \*\* addr: (0x[0-9a-f]+)', src[j])
                    if mm:
                        addr = mm.group(1)
                found.append({'file': os.path.relpath(p, root), 'line': i + 1,
                              'class': cls, 'function': fnname, 'addr': addr,
                              'bytes': vals})
    seen, uniq = set(), []
    for f in found:
        k = bytes(f['bytes'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    index = []
    for n, f in enumerate(uniq):
        b = bytes(f['bytes'])
        declared = int.from_bytes(b[2:4], 'big') if len(b) >= 4 else None
        stored_crc = int.from_bytes(b[0:2], 'big') if len(b) >= 2 else None
        calc = crc16_modbus(b[2:])
        info = {
            'file': f['file'], 'line': f['line'], 'class': f['class'],
            'function': f['function'], 'addr': f['addr'],
            'length': len(b), 'declared_length_bytes_2_3': declared,
            'declared_matches_total': declared == len(b),
            'stored_crc_bytes_0_1': '0x%04X' % stored_crc if stored_crc is not None else None,
            'crc16_modbus_over_2_end': '0x%04X' % calc,
            'crc_matches_stored': stored_crc == calc,
            'sha256': hashlib.sha256(b).hexdigest(),
            'mapKeys_first16': list(b[-32:-16]) if len(b) >= 32 else None,
            'mapKeys_last16': list(b[-16:]) if len(b) >= 32 else None,
        }
        name = 'default_%03d_len_%s_%s.json' % (
            n, len(b), re.sub(r'[^A-Za-z0-9]', '_', f['file'].split('/')[-1])[:30])
        info['raw_name'] = name
        with open(os.path.join(outdir, name), 'w') as fh:
            json.dump({'meta': info, 'bytes': f['bytes'], 'hex': b.hex(' ')}, fh, indent=1)
        index.append(info)
    with open(os.path.join(outdir, 'index.json'), 'w') as fh:
        json.dump({'source_root': root, 'count': len(index), 'images': index}, fh, indent=1)
    for info in index:
        print('%-44s len=%-4d decl=%-5s stored=%-7s calc=%-7s match=%-5s %s@%s: %s' % (
            info['raw_name'], info['length'], info['declared_matches_total'],
            info['stored_crc_bytes_0_1'], info['crc16_modbus_over_2_end'],
            info['crc_matches_stored'], info['file'], info['addr'], info['function'][:36]))


if __name__ == '__main__':
    main()