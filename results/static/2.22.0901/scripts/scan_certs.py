#!/usr/bin/env python3
"""Extract every X.509 cert candidate from the APK Signing Block pairs by DER scan."""
import struct, os, subprocess, hashlib

APK = "/home/salamanka/armorx-lab/apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk"
OUT = "/home/salamanka/.hermes/cache/scratch/armorx222"
data = open(APK, "rb").read()
magic_pos = data.rfind(b"APK Sig Block 42", 0, data.rfind(b"PK\x05\x06"))
blk_size = struct.unpack_from("<Q", data, magic_pos-8)[0]
sb_start = magic_pos + 16 - 8 - blk_size
pos, end = sb_start + 8, magic_pos - 8
IDS = {0x7109871a: "v2", 0xf05368c0: "v3", 0x42726577: "v3.1", 0x1b93ad61: "verity",
       0x504b4453: "PKDS(source-stamp/sdk)", 0x2b09189e: "srcstamp", 0x6dff800d: "srcstamp2"}

def try_openssl(der, tag):
    p = os.path.join(OUT, f"cand-{tag}.der")
    open(p, "wb").write(der)
    r = subprocess.run(["openssl", "x509", "-inform", "DER", "-noout", "-subject", "-issuer",
                        "-serial", "-fingerprint", "-sha256", "-dates", "-text"],
                       input=der, capture_output=True)
    return r.returncode == 0, r.stdout.decode(errors="replace")

seen = {}
while pos < end:
    plen = struct.unpack_from("<Q", data, pos)[0]
    pid = struct.unpack_from("<I", data, pos+8)[0]
    val = data[pos+12: pos+8+plen]
    name = IDS.get(pid, hex(pid))
    print(f"pair 0x{pid:08x} {name} len={plen}")
    # DER scan: 30 82 LL LL
    i = 0
    found = []
    while i < len(val)-4:
        if val[i] == 0x30 and val[i+1] == 0x82:
            clen = struct.unpack_from(">H", val, i+2)[0] + 4
            if i + clen <= len(val):
                ok, txt = try_openssl(val[i:i+clen], f"{name}-{i}")
                if ok:
                    fp = [l for l in txt.splitlines() if "Fingerprint" in l or "SHA256 Fingerprint" in l]
                    found.append((i, clen, fp))
                    seen[(name, i, clen)] = txt
        i += 1
    for i, clen, fp in found:
        print(f"   cert @ {i} len={clen} {fp}")
    pos += 8 + plen

print("\n=== unique cert texts ===")
uniq = {}
for (name, i, clen), txt in seen.items():
    subj = [l for l in txt.splitlines() if l.startswith("subject=")]
    key = (txt.count("subject="), subj[0] if subj else "")
    uniq.setdefault(subj[0] if subj else txt[:60], []).append((name, i, clen))
for k, v in uniq.items():
    print(k, "->", v)