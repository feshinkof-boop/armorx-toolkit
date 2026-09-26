#!/usr/bin/env python3
"""Extract and verify ArmorX default configuration templates from Blutter pp.txt.

Templates are embedded in the Dart AOT snapshot as JSON list-string constants
("[0,0,0,144,51,255,...]" parsed by defaultConfig() at runtime).

A template is recognized by its envelope: bytes 0..1 = CRC16 (big-endian),
bytes 2..3 = declared length (big-endian) matching the list's own length.

Usage:
    python3 scripts/extract_default_configs.py --pp <blutter_out>/pp.txt \
        --out research/default-config-templates.json [--version 2.23.0609]

Deterministic; exits non-zero if no templates are found.
"""
import argparse, hashlib, json, re, sys


def crc16_modbus(data: bytes, init: int = 0xFFFF, poly: int = 0xA001) -> int:
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ poly if crc & 1 else crc >> 1
    return crc


def extract_templates(pp_text: str):
    """Return [(pool_offset, [ints])] for every default-config template string."""
    out = []
    # Blutter renders each String: constant on a single line; template strings
    # are pure comma/space-separated decimal int lists of >= 80 elements.
    for m in re.finditer(r'^\[pp\+(0x[0-9a-f]+)\] String: "(\[[\d, ]+\])"\s*$', pp_text, re.M):
        try:
            nums = json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        if not isinstance(nums, list) or len(nums) < 80:
            continue
        if not all(isinstance(n, int) and 0 <= n <= 255 for n in nums):
            continue
        if len(nums) >= 4 and ((nums[2] << 8) | nums[3]) == len(nums):
            out.append((m.group(1), nums))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pp', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--version', default='unknown')
    args = ap.parse_args()

    pp_text = open(args.pp, encoding='utf-8', errors='replace').read()
    templates = extract_templates(pp_text)
    if not templates:
        print(f'ERROR: no default-config templates found in {args.pp}', file=sys.stderr)
        sys.exit(1)

    entries = []
    for off, nums in templates:
        data = bytes(nums)
        declared = (data[2] << 8) | data[3]
        stored = (data[0] << 8) | data[1]
        recomputed = crc16_modbus(data[2:])
        entries.append({
            'evidence': f'pp.txt [pp+{off}] String constant, JSON list parsed by defaultConfig()',
            'length': len(data),
            'declared_length': declared,
            'stored_crc': stored,
            'recomputed_crc': recomputed,
            'crc_valid': stored == recomputed,
            'sha256': hashlib.sha256(data).hexdigest(),
            'hex': data.hex(),
        })
    entries.sort(key=lambda e: e['length'])
    result = {
        'version': args.version,
        'crc_algorithm': 'CRC-16/MODBUS: init 0xFFFF, poly 0xA001, reflected input/output; computed over bytes 2..end; stored big-endian at bytes 0..1',
        'template_count': len(entries),
        'templates': entries,
    }
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
        f.write('\n')
    print(f"extracted {len(entries)} templates -> {args.out}")
    for e in entries:
        print(f"  {e['length']:3d}B declared={e['declared_length']:3d} stored_crc=0x{e['stored_crc']:04x} recomputed=0x{e['recomputed_crc']:04x} valid={e['crc_valid']} sha256={e['sha256'][:16]}...")


if __name__ == '__main__':
    main()
