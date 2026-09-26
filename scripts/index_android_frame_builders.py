#!/usr/bin/env python3
"""Index Android FFE1 frame-builder functions from a Blutter asm tree.

Scans package:moojiang asm files for functions that construct A5-family short
frames (or A4 long frames): a Smi-tagged 0xA5 header (330) stored into a
freshly allocated List<int>, together with Smi-tagged opcode immediates.

Smis are Dart-tagged integers: raw immediate = value << 1 in `mov xN, #imm`
or in Blutter's `rN = <dec>` comment form.

Usage:
    python3 scripts/index_android_frame_builders.py --asm <blutter_out>/asm \
        --out research/android-frame-builders.json [--version 2.23.0609]

The scan is conservative (moojiang package only, A5-Smi required), so
cross-version structural changes may require list additions below.
"""
import argparse, json, os, re, sys

# opcode byte -> label (protocol names follow docs/protocol-opcode-index.md)
OPCODES = {
    0x0B: '0B', 0xEF: 'EF', 0xD6: 'D6', 0xD7: 'D7', 0xE2: 'E2', 0x0E: '0E',
    0xD2: 'D2', 0xFC: 'FC', 0xD4: 'D4', 0xD8: 'D8', 0xFF: 'FF', 0xAB: 'AB',
    0xA4: 'A4', 0xD3: 'D3', 0xD5: 'D5', 0x19: '19',
}
HEADER_SMI = 330  # 0xA5 << 1


def smi(v):
    return v << 1


def iter_functions(asm_root):
    for root, _dirs, files in os.walk(asm_root):
        for f in files:
            path = os.path.join(root, f)
            try:
                text = open(path, encoding='utf-8', errors='replace').read()
            except OSError:
                continue
            if 'package:moojiang' not in text and 'moojiang' not in root:
                continue
            for m in re.finditer(r'^  (.+?)\{\n    // \*\* addr: (0x[0-9a-f]+), size', text, re.M):
                sig, addr = m.group(1).strip(), m.group(2)
                start = m.end()
                nxt = re.search(r'^  .+?\{\n    // \*\* addr:', text[start:], re.M)
                end = start + nxt.start() if nxt else len(text)
                yield os.path.relpath(path, asm_root), sig, addr, text[start:end]


def index_builders(asm_root):
    results = []
    for relpath, sig, addr, body in iter_functions(asm_root):
        has_a5 = 'mov             x17, #0x14a' in body or re.search(r'r\d+ = 330\b', body)
        if not has_a5:
            continue
        ops = []
        for op, name in OPCODES.items():
            if (f'mov             x17, #0x{smi(op):x}' in body
                    or re.search(rf'r17 = {smi(op)}\b', body)):
                ops.append(name)
        if ops:
            results.append({
                'file': relpath, 'function': sig, 'addr': addr, 'opcodes': sorted(ops),
                'evidence': 'A5-Smi(330) header store + opcode Smi stores in one function',
            })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--asm', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--version', default='unknown')
    args = ap.parse_args()

    results = index_builders(args.asm)
    if not results:
        print('ERROR: no frame builders found', file=sys.stderr)
        sys.exit(1)
    payload = {
        'version': args.version,
        'scan_rule': 'functions in package:moojiang containing Smi 330 (0xA5) plus at least one known opcode Smi store',
        'frame_builder_count': len(results),
        'frame_builders': results,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, 'w') as f:
        json.dump(payload, f, indent=1)
        f.write('\n')
    print(f'{len(results)} frame builders -> {args.out}')
    for r in results:
        print(f"  {r['file']}: {r['function'][:70]} @ {r['addr']}: {','.join(r['opcodes'])}")


if __name__ == '__main__':
    main()
