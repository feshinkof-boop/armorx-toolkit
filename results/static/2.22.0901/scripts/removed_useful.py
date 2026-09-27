#!/usr/bin/env python3
"""Strings present in 2.22's Dart pool but ABSENT from 2.23/2.24/4.0.8 pools."""
import re, json

POOLS = {
    "2.22.0901": "/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/pp.txt",
    "2.23": "/home/salamanka/armorx/re/blutter_out/pp.txt",
    "2.24": "/home/salamanka/armorx/re/v224/blutter_out/pp.txt",
    "4.0.8": "/home/salamanka/armorx-re/mygt408/blutter_out/pp.txt",
}
def pool(path):
    data = open(path, "rb").read().decode("latin1")
    s = set()
    for m in re.finditer(r'String: "(.*)"', data):
        s.add(m.group(1))
    return s

P = {k: pool(v) for k, v in POOLS.items()}
print({k: len(v) for k, v in P.items()})
later = P["2.23"] | P["2.24"] | P["4.0.8"]
only222 = sorted(P["2.22.0901"] - later)
print("2.22-only pool strings:", len(only222))

# filter for protocol / field meaning
def meaningful(s):
    if re.search(r'\b(A5|A4|A8)[0-9a-fA-F ]', s): return True
    if re.search(r'(opcode|cmd|command|frame|checksum|cks|writeDevice|readDevice|getConfig|setConfig|writeConfig|queryDefault|queryGame|macro|dpi|light|turbo|motor|trigger|stick|gyro|curve|deadzone|calibrat|firmware|version|uuid|Macro|Config|Light|Turbo|Dpi|DPI|Report|report)', s): return True
    if re.fullmatch(r'[0-9A-F]{2}( [0-9A-F]{2}){2,}', s): return True
    return False

interesting = [s for s in only222 if meaningful(s)]
print("meaningful 2.22-only:", len(interesting))
json.dump({"only_2_22": only222, "meaningful": interesting}, open("/home/salamanka/.hermes/cache/scratch/armorx222/removed.json", "w"), indent=1)
for s in interesting[:200]:
    print(repr(s))