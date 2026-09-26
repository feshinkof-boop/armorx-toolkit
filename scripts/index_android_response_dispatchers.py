#!/usr/bin/env python3
"""Index Android FFE2 response-dispatcher functions from a Blutter asm tree.

A response dispatcher is a function that inspects incoming notification data:
  - raw byte comparisons:  cmp xN, #0xa5 / #0xa4  (frame header checks)
  - Smi-tagged opcode compares:  cmp wN, #<opcode<<1>  (data[2] opcode checks)

The scanner finds package:moojiang functions containing both an A5-family
header compare AND at least one known opcode compare.

Usage:
    python3 scripts/index_android_response_dispatchers.py --asm <asm> --out out.json [--version X]
"""
import argparse, json, os, re, sys

OPCODES = {
    0x0B: '0B', 0xEF: 'EF', 0xD6: 'D6', 0xD7: 'D7', 0xE2: 'E2', 0x0E: '0E',
    0xD2: 'D2', 0xFC: 'FC', 0xD4: 'D4', 0xD8: 'D8', 0xFF: 'FF', 0xAB: 'AB',
    0xA4: 'A4', 0xD3: 'D3', 0xD5: 'D5', 0x19: '19',
}
HEADER_RAW = (0xa5, 0xa4, 0xab)  # frame header bytes; matched raw or Smi-tagged


def iter_functions(asm_root, package_filter='moojiang'):
    for root, _dirs, files in os.walk(asm_root):
        for f in files:
            path = os.path.join(root, f)
            try:
                text = open(path, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            if package_filter not in root and package_filter not in text[:200]:
                continue
            for m in re.finditer(r'^  (.+?)\{\n    // \*\* addr: (0x[0-9a-f]+), size', text, re.M):
                sig, addr = m.group(1).strip(), m.group(2)
                start = m.end()
                nxt = re.search(r'^  .+?\{\n    // \*\* addr:', text[start:], re.M)
                end = start + nxt.start() if nxt else len(text)
                yield os.path.relpath(path, asm_root), sig, addr, text[start:end]


def index_dispatchers(asm_root):
    results = []
    for relpath, sig, addr, body in iter_functions(asm_root):
        # header compares: raw byte (2.23: cmp x1, #0xa5) or Smi-tagged (2.24: cmp w0, #0x14a)
        headers = []
        for h in HEADER_RAW:
            if (re.search(rf'cmp\s+x\d+, #0x{h:x}\b', body)
                    or re.search(rf'cmp\s+w\d+, #0x{h << 1:x}\b', body)):
                headers.append(h)
        if not headers:
            continue
        # opcode compares: Smi-tagged (opcode<<1) or raw
        ops = []
        for op, name in OPCODES.items():
            smi = op << 1
            if (re.search(rf'cmp\s+w\d+, #0x{smi:x}\b', body)
                    or re.search(rf'cmp\s+x\d+, #0x{op:x}\b', body)
                    or re.search(rf'cmp\s+w\d+, #0x{op:x}\b', body)):
                ops.append(name)
        if ops:
            results.append({
                'file': relpath, 'function': sig, 'addr': addr,
                'header_checks': [f'0x{h:02X}' for h in headers],
                'opcodes_compared': sorted(ops),
                'evidence': 'raw cmp against 0xA5/0xA4 + Smi-tagged opcode cmp in one function',
            })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asm', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--version', default='unknown')
    args = ap.parse_args()
    results = index_dispatchers(args.asm)
    if not results:
        print('ERROR: no response dispatchers found', file=sys.stderr)
        sys.exit(1)
    payload = {
        'version': args.version,
        'scan_rule': 'package:moojiang functions with raw 0xA5/0xA4/0xAB compares plus known opcode compares',
        'dispatcher_count': len(results),
        'dispatchers': results,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(payload, f, indent=1)
        f.write('\n')
    print(f'{len(results)} dispatchers -> {args.out}')
    for r in results:
        print(f"  {r['file']}: {r['function'][:60]} @ {r['addr']}: headers={r['header_checks']} ops={r['opcodes_compared']}")


if __name__ == '__main__':
    main()
