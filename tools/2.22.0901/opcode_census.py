#!/usr/bin/env python3
"""Census of protocol opcode bytes by Smi-immediate grep across a Blutter asm tree.

Blutter renders a Dart `int` immediate stored into a List<int> as `mov xN, #imm`
where the printed value is the Smi encoding:  byte B -> #0x(2B).
This script counts the Smi form of every candidate opcode and reports the
enclosing function + address (and a raw-`cmp #B` dispatch count separately,
because 2.17.5 dispatchers sometimes compare the RAW header byte).

Usage: python3 opcode_census.py <asm_dir> <out.json> [opcodes...]
"""
import json
import os
import re
import sys

FN_HEAD = re.compile(r'^\s{1,4}((?:static\s+|late\s+|final\s+|const\s+)*[A-Za-z_<>$\[][^\n]*?\()(.*?)\{\s*$')
ADDR = re.compile(r'// \*\* addr: (0x[0-9a-f]+)')
CLASS = re.compile(r'^class\s+(\S+)')
MOV = re.compile(r'^\s*//\s+0x([0-9a-f]+):\s+mov\s+(?:x|w)(\d+),\s+#(0x[0-9a-f]+)')
CMP = re.compile(r'^\s*//\s+0x([0-9a-f]+):\s+cmp\s+(?:x|w)(\d+),\s+#(0x[0-9a-f]+)')

DEFAULT = [0x04, 0x05, 0x06, 0x07, 0x0B, 0x0C, 0x0E, 0x1A, 0x1B, 0x25, 0x26,
           0x34, 0x70, 0x73, 0xD2, 0xD3, 0xD4, 0xD6, 0xD7, 0xD8, 0xDA, 0xDD,
           0xE1, 0xE2, 0xE3, 0xE4, 0xEF, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7,
           0xF8, 0xFC, 0xFD, 0xFF, 0xAB, 0xA5, 0xA4]


def main():
    root = sys.argv[1]
    out = sys.argv[2]
    ops = [int(x, 16) for x in sys.argv[3:]] or DEFAULT
    files = []
    if os.path.isfile(root):
        files = [root]
    else:
        for dp, _d, fs in os.walk(root):
            files += [os.path.join(dp, f) for f in sorted(fs) if f.endswith('.dart')]
    hits = {op: {'smi_mov': [], 'raw_cmp': []} for op in ops}
    for p in files:
        if '/generated/intl/' in p or p.endswith(('messages_en.dart', 'messages_ja_JP.dart', 'messages_ko_KR.dart', 'messages_zh_CN.dart', 'l10n.dart')):
            continue  # intl string-table ints: every value 0..~600 appears -> pure noise
        cur = None
        cls = None
        addr = None
        for line in open(p, errors='replace'):
            m = CLASS.match(line)
            if m:
                cls = m.group(1)
                continue
            m = FN_HEAD.match(line)
            if m:
                cur = (m.group(1) + m.group(2) + ')').strip()
                addr = None
                continue
            if addr is None:
                a = ADDR.search(line)
                if a:
                    addr = a.group(1)
                    continue
            m = MOV.match(line)
            if m:
                v = int(m.group(3), 16)
                if v % 2 == 0 and v // 2 in hits:
                    hits[v // 2]['smi_mov'].append(
                        {'file': p, 'class': cls, 'function': cur, 'addr': addr,
                         'line_addr': '0x' + m.group(1), 'reg': m.group(2),
                         'smi': v, 'byte': v // 2})
                continue
            m = CMP.match(line)
            if m:
                v = int(m.group(3), 16)
                if v in hits:
                    hits[v]['raw_cmp'].append(
                        {'file': p, 'class': cls, 'function': cur, 'addr': addr,
                         'line_addr': '0x' + m.group(1), 'byte': v})
                elif v % 2 == 0 and v // 2 in hits:
                    hits[v // 2]['smi_mov'].append(
                        {'file': p, 'class': cls, 'function': cur, 'addr': addr,
                         'line_addr': '0x' + m.group(1), 'reg': m.group(2),
                         'smi': v, 'byte': v // 2, 'via': 'cmp'})
    json.dump(hits, open(out, 'w'), indent=1)
    for op in ops:
        h = hits[op]
        print('0x%02X  smi_mov=%d  raw_cmp=%d' % (op, len(h['smi_mov']), len(h['raw_cmp'])))
        for x in h['smi_mov'][:8]:
            print('      MOV  %s  %s::%s @%s (%s)' % (
                os.path.relpath(x['file'], root), x['class'] or '', x['function'][:40],
                x['addr'], x['line_addr']))
        for x in h['raw_cmp'][:8]:
            print('      CMP  %s  %s::%s @%s (%s)' % (
                os.path.relpath(x['file'], root), x['class'] or '', x['function'][:40],
                x['addr'], x['line_addr']))


if __name__ == '__main__':
    main()