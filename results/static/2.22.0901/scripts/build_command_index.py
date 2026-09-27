#!/usr/bin/env python3
"""Merge the frame/dispatch scans into command-index.json (curated view).

Inputs (all produced by the sibling scripts in this directory):
  research/mygt-4.0.8/_frames_exact.json   byte-exact short frames
  research/mygt-4.0.8/_frame_index_raw.json  candidate frames (noisier)
  research/mygt-4.0.8/_dispatch_scan_raw.md  opcode comparisons (response side)

Usage: python3 scripts/build_command_index.py <research_dir>
"""
import json
import os
import re
import sys
from collections import defaultdict

# Curated semantics: only entries with a direct evidence link are named.
CURATED = {
    0x0B: ('getZKMVer', 'request firmware/mcu version string; reply drives the GATT 2A24/2A26 reads'),
    0x0E: ('writeDevice', 'post-write command emitted after config/macro/DPI writes (echoed by device)'),
    0x1A: ('reset', 'reset command from the settings page'),
    0x1B: ('startCalibration/stopCalibration', 'stick+gyro calibration start/stop'),
    0x25: ('getMotionDpi', 'AB-family motion (gyro) DPI read'),
    0x26: ('getMotionList', 'AB-family motion/gyro list read'),
    0x04: ('getBattery', 'battery request on the vendor characteristic'),
    0x70: ('lighting config (R3)', 'A5 10 70 ... / A5 04 70 03 lighting family used by Rainbow R3 widgets'),
    0x73: ('light enable state', 'A5 04 73 get / A5 05 73 xx set'),
    0xA9: ('(doujiang keyboard) empty packet', 'KbDouJiangManager::_emptyPack'),
    0xD2: ('testModeSwitch', 'controller test-mode toggle (A5 05 D2 00 / A5 05 D2 01)'),
    0xD3: ('getMaxSize', 'macro page size query (A5 04 D3)'),
    0xD4: ('getInputModel', 'input mode query (A5 04 D4)'),
    0xD6: ('getDeviceConfig', 'full configuration read (A5 04 D6) - ARMOR-X Pro 144-byte image'),
    0xD7: ('writeDeviceConfig', 'full configuration write (A4 fragmentation)'),
    0xD8: ('macro device protocol', 'macro write/read family (A4 fragmentation)'),
    0xDD: ('charging light effect', 'A5 04 DD get / A5 07 DD .. set'),
    0xE1: ('connect mode', 'A5 04 E1 get / A5 06 E1 .. set'),
    0xE2: ('readFirmware', 'firmware revision read - reachable in 4.0.8 (absent in 2.23/2.24)'),
    0xE4: ('getMTU', 'MTU query (A5 04 E4)'),
    0xEF: ('getDeviceUUID', 'A5 0C EF + 8 zero bytes; reply bytes 3..10 -> devUuid -> /dev/register'),
    0xF2: ('keyboard/doujiang light - config mode', 'hitbox_light_sender_manager'),
    0xF3: ('keyboard/doujiang light - brightness', 'hitbox_light_sender_manager'),
    0xF4: ('keyboard/doujiang light - normal mode', 'hitbox_light_sender_manager'),
    0xF5: ('keyboard/doujiang light - click mode / logo colour', 'hitbox_light_sender_manager + Rainbow logo colour'),
    0xF6: ('keyboard/doujiang light - charging mode / step length', 'ambivalent: two distinct builders'),
    0xF7: ('step length / SOCD', 'BluetoothModel::getStepLength and hitbox SOCD builder'),
    0xF8: ('brightness compensation', 'A5 04 F8 get / write family'),
    0xFC: ('DPI / transcribe control', 'A5 05 FC 80 DPI request; A5 0B FC .. macro transcribe start/stop'),
    0xFD: ('macro/transcribe response', 'frame_config_macros dispatch'),
    0xFF: ('lighting payload marker', 'appears inside writeLightConfig payloads'),
}


def load_exact(d):
    p = os.path.join(d, '_frames_exact.json')
    return json.load(open(p)) if os.path.exists(p) else []


def load_candidates(d):
    p = os.path.join(d, '_frame_index_raw.json')
    return json.load(open(p)) if os.path.exists(p) else []


def load_dispatch(d):
    p = os.path.join(d, '_dispatch_scan_raw.md')
    rows = []
    if os.path.exists(p):
        for l in open(p):
            if not l.startswith('| bl'):
                continue
            c = [x.strip() for x in l.strip().strip('|').split('|')]
            rows.append({'file': c[0], 'class': c[1], 'function': c[2], 'addr': c[3],
                         'opcode': c[4], 'line': c[5]})
    return rows


def main():
    d = sys.argv[1]
    exact = load_exact(d)
    cand = load_candidates(d)
    disp = load_dispatch(d)

    builders = defaultdict(list)
    for r in exact:
        for f in r['frames']:
            builders[f['opcode']].append({
                'file': r['file'].split('asm/')[-1], 'class': r['class'], 'function': r['function'],
                'addr': r['addr'], 'frame': '%02X %02X %02X %s %02X' % (
                    f['start'], f['len'], f['opcode'],
                    ' '.join('%02X' % b for b in f['data']), f['computed_checksum']),
                'byte_exact': True})
    for r in cand:
        for f in r['frames']:
            if any(b['addr'] == r['addr'] for b in builders.get(f['opcode'], [])):
                continue
            builders[f['opcode']].append({
                'file': r['file'].split('asm/')[-1], 'class': r['class'], 'function': r['function'],
                'addr': r['addr'],
                'frame_candidate': '%s %s %s %s' % (f['start'], f['len'], f['opcode'],
                                                     ' '.join(str(b) for b in f['data'])),
                'byte_exact': False})

    dispatchers = defaultdict(list)
    for r in disp:
        op = int(r['opcode'], 16)
        dispatchers[op].append(r)

    out = {'generated_from': ['_frames_exact.json', '_frame_index_raw.json', '_dispatch_scan_raw.md'],
           'opcodes': []}
    for op in sorted(set(list(builders) + list(dispatchers))):
        name, note = CURATED.get(op, ('UNKNOWN', 'no curated semantics'))
        out['opcodes'].append({
            'opcode': '0x%02X' % op,
            'semantics': name, 'notes': note,
            'builders': builders.get(op, []),
            'dispatchers': dispatchers.get(op, []),
            'evidence': 'PROVEN STATIC' if builders.get(op) else 'STRONG EVIDENCE',
        })
    json.dump(out, open(os.path.join(d, 'command-index.json'), 'w'), indent=1)

    # markdown
    with open(os.path.join(d, 'command-index.md'), 'w') as f:
        f.write('# MYGT 4.0.8 command index (static)\n\n')
        f.write('Byte-exact frames are reconstructed from the AOT builder bodies '
                '(scripts/reconstruct_frames.py); candidate rows come from the looser '
                'scanner (scripts/frame_index.py) and must be read as leads.\n\n')
        f.write('| opcode | semantics | builder (byte-exact) | dispatcher |\n|---|---|---|---|\n')
        for e in out['opcodes']:
            b = e['builders'][0] if e['builders'] else None
            dsp = e['dispatchers'][0] if e['dispatchers'] else None
            bt = ''
            if b:
                bt = '%s `%s` @%s %s' % (b['function'], b['file'], b['addr'],
                                         b.get('frame') or b.get('frame_candidate') or '')
            dt = ''
            if dsp:
                dt = '%s (%s) line %s' % (dsp['function'], dsp['file'].split('/')[-1], dsp['line'])
            f.write('| %s | %s | %s | %s |\n' % (e['opcode'], e['semantics'], bt, dt))
    print('%d opcodes -> command-index.json/.md' % len(out['opcodes']))


if __name__ == '__main__':
    main()
