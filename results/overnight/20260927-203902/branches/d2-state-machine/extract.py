#!/usr/bin/env python3
"""Extract function blocks + key facts from blutter asm .dart files."""
import re, sys, json, os

FILES = {
 "4.0.8-rainbow":  "/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart",
 "4.0.8-bt":       "/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/units/ble/bluetooth_mode.dart",
 "2.24-rainbow":   "/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart",
 "2.23-rainbow":   "/home/salamanka/armorx/re/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart",
 "2.22-rainbow":   "/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/asm/moojiang/widgets/rainbow/rainbow_test.dart",
}

def blocks(path):
    lines = open(path, encoding='utf-8', errors='replace').read().split('\n')
    out = []
    cur = None
    for i, ln in enumerate(lines):
        m = re.match(r'\s*// \*\* addr: (0x[0-9a-f]+), size: (0x[0-9a-f]+)', ln)
        if m:
            if cur: out.append(cur)
            # find the declaration line above (the line before the addr comment that has '{')
            j = i-1
            while j >= 0 and not lines[j].rstrip().endswith('{'):
                j -= 1
            decl = lines[j].strip() if j>=0 else '?'
            cur = {'addr': m.group(1), 'size': int(m.group(2),16), 'decl': decl, 'lines': [], 'start': i+1}
        if cur is not None:
            cur['lines'].append(ln)
    if cur: out.append(cur)
    return out

def facts(b):
    L = b['lines']
    txt = '\n'.join(L)
    f = {}
    f['calls'] = sorted(set(re.findall(r'; \[([^\]]+)\] ([A-Za-z_][\w:.#]*)', txt)))
    f['stubs'] = sorted(set(re.findall(r'; ([A-Za-z_][\w]*)Stub', txt)))
    f['fields'] = sorted(set(re.findall(r'LoadField: r\d+ = r\d+->(field_[0-9a-f]+)', txt) + re.findall(r'StoreField: r\d+->(field_[0-9a-f]+)', txt)))
    f['arrays'] = sorted(set(re.findall(r'r(\d+) = (\d+)\n', txt)))
    f['cmp'] = re.findall(r'cmp\s+w\d+,\s*(#?\w+)', txt)
    f['frame_bytes'] = re.findall(r'mov\s+x\d+, #(0x[0-9a-f]+|0x0)\b', txt)
    f['instance'] = sorted(set(re.findall(r'Obj!(\w+)@([0-9a-f]+)', txt)))
    f['strings'] = sorted(set(re.findall(r'"([^"]{1,60})"', txt)))
    f['awaits'] = txt.count('AwaitStub') + txt.count('_awaitHelper')
    return f

mode = sys.argv[1] if len(sys.argv)>1 else 'list'
target = sys.argv[2] if len(sys.argv)>2 else None

for name, path in FILES.items():
    if target and target not in name: continue
    if not os.path.exists(path):
        print(f"== {name}: MISSING {path}"); continue
    bs = blocks(path)
    print(f"\n===== {name} ({len(bs)} blocks) =====")
    if mode=='list':
        for b in bs:
            print(f"  {b['addr']} size={b['size']:#x}  {b['decl']}")
    else:
        for b in bs:
            if target and target not in b['addr'] and 'ALL' not in (sys.argv[3] if len(sys.argv)>3 else ''):
                pass
            f = facts(b)
            print(f"\n--- {b['addr']} size={b['size']:#x} {b['decl']}")
            print("  calls:", f['calls'])
            print("  fields:", f['fields'])
            print("  instance:", f['instance'])
            print("  cmp:", f['cmp'])
            print("  awaits:", f['awaits'])
            print("  strings:", f['strings'])
