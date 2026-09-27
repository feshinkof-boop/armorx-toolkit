#!/usr/bin/env python3
"""Phase 2 metadata collector: AndroidManifest + signing cert + ABI/split layout.

Reads ONLY the untouched originals. Emits JSON per build.
Run with the pyaxmlparser/androguard venv python.
"""
import hashlib
import json
import os
import struct
import sys
import zipfile

from pyaxmlparser import APK
from pyaxmlparser.axmlprinter import AXMLPrinter

BASE = "/home/salamanka/armorx-lab/apk/original"
OUT = "/home/salamanka/armorx-lab/apk/manifests/_raw"
os.makedirs(OUT, exist_ok=True)

BUILDS = {
    "2.23": ["2.23/base.apk"],
    "2.24": ["2.24/BIGBIGWON-2.24.0919.apk"],
    "4.0.8": ["4.0.8/BIGBIGWON-4.0.8.apkm", "4.0.8/base.apk"],
}

# attribute extraction direct from the binary AXML (cross-check against pyaxmlparser)
sys.path.insert(0, "/home/salamanka/armorx-re/mygt408/scripts")


def sha1_file(p, buf=1 << 20):
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()


def sha256_file(p, buf=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()


def cert_info(apk_path):
    a = APK(apk_path)
    out = []
    try:
        certs = a.get_certificates()
    except Exception as e:
        return [{"error": repr(e)}]
    for c in certs or []:
        out.append({
            "subject": str(c.subject.human_friendly),
            "issuer": str(c.issuer.human_friendly),
            "serial": "%X" % c.serial_number,
            "not_before": str(c["tbs_certificate"]["validity"]["not_before"].native),
            "not_after": str(c["tbs_certificate"]["validity"]["not_after"].native),
            "sha1": c.sha1.hex().upper(),
            "sha256": c.sha256.hex().upper(),
        })
    # v1 file present?
    names = []
    with zipfile.ZipFile(apk_path) as z:
        names = z.namelist()
    v1 = [n for n in names if n.upper().startswith("META-INF/") and
          n.upper().endswith((".RSA", ".DSA", ".EC"))]
    return {"certs": out, "v1_signature_files": v1}


def manifest_attrs(apk_path):
    """Read every attribute of <manifest> from the binary AXML directly."""
    with zipfile.ZipFile(apk_path) as z:
        raw = z.read("AndroidManifest.xml")
    p = AXMLPrinter(raw)
    # AXMLPrinter.xml is the decoded XML string; use the lower-level parser here.
    import xml.etree.ElementTree as ET
    root = ET.fromstring(p.get_xml())
    return root


def direct_axml(apk_path):
    """Direct binary read of manifest-level attrs + uses-sdk + split + permissions."""
    with zipfile.ZipFile(apk_path) as z:
        raw = z.read("AndroidManifest.xml")
    # minimal binary AXML parser
    # header
    res = {}
    string_pool = []
    i = 8  # skip type/headerSize
    # walk chunks
    while i < len(raw):
        ctype, hsize, csize = struct.unpack_from("<HHI", raw, i)
        chunk = raw[i:i + csize]
        if ctype == 0x0001:  # string pool
            scount, stylecount, flags, sstart, stystart = struct.unpack_from("<IIIII", chunk, 8)
            utf8 = (flags & (1 << 8)) != 0
            offs = struct.unpack_from("<%dI" % scount, chunk, 28)
            for off in offs:
                pos = sstart + off
                if utf8:
                    # two varint-ish length bytes
                    p = pos
                    # utf16 length
                    l1 = chunk[p]; p += 1
                    if l1 & 0x80:
                        l1 = ((l1 & 0x7F) << 8) | chunk[p]; p += 1
                    l2 = chunk[p]; p += 1
                    if l2 & 0x80:
                        l2 = ((l2 & 0x7F) << 8) | chunk[p]; p += 1
                    s = chunk[p:p + l2 * 2].decode("utf-16-le", "replace")
                else:
                    p = pos
                    l = struct.unpack_from("<H", chunk, p)[0]; p += 2
                    if l & 0x8000:
                        l = ((l & 0x7FFF) << 16) | struct.unpack_from("<H", chunk, p)[0]; p += 2
                    s = chunk[p:p + l * 2].decode("utf-16-le", "replace")
                string_pool.append(s)
        elif ctype == 0x0102:  # XML start element (resource map chunk precedes it)
            pass
        if csize == 0:
            break
        i += csize

    # second pass: elements
    elems = []
    i = 8
    resmap = None
    while i < len(raw):
        ctype, hsize, csize = struct.unpack_from("<HHI", raw, i)
        chunk = raw[i:i + csize]
        if ctype == 0x0180:  # resource map
            n = (csize - hsize) // 4
            resmap = struct.unpack_from("<%dI" % n, chunk, hsize)
        elif ctype == 0x0102:  # start element
            line, comment = struct.unpack_from("<II", chunk, 8)
            ns, name = struct.unpack_from("<ii", chunk, 16)
            attrstart, attrsize, attrcount = struct.unpack_from("<HHH", chunk, 24)
            attrs = []
            base = 16 + (attrstart - 16) if False else 16  # attrExt begins at chunk+16
            aoff = 16 + attrstart - 16 + 20 - 20  # placeholder
            # official: attrExt at chunk+16; attributeStart relative to attrExt
            attr_ext = 16
            a0 = attr_ext + attrstart
            for k in range(attrcount):
                ap = a0 + k * attrsize
                ans, aname, araw, atyp, adata = struct.unpack_from("<iiiII", chunk, ap)
                # name may be a resource-map string
                nm_s = string_pool[aname] if 0 <= aname < len(string_pool) else str(aname)
                attrs.append((nm_s, atyp, adata, araw))
            elems.append((string_pool[name] if 0 <= name < len(string_pool) else str(name), attrs))
        if csize == 0:
            break
        i += csize
    res["elements"] = elems
    res["strings"] = string_pool
    return res


def typval(atyp, adata):
    if atyp == 0x03:  # string
        return adata
    if atyp == 0x10:  # int dec
        return adata
    if atyp == 0x11:  # hex
        return adata
    if atyp == 0x12:
        return bool(adata)
    return adata


report = {}
for ver, files in BUILDS.items():
    entry = {"originals": []}
    for rel in files:
        p = os.path.join(BASE, rel)
        entry["originals"].append({
            "path": p, "size": os.path.getsize(p),
            "sha256": sha256_file(p), "sha1": sha1_file(p),
        })
    # primary = the APK that carries the manifest (for APKM use the base split)
    primary = os.path.join(BASE, files[-1] if ver == "4.0.8" else files[0])
    entry["primary_apk"] = primary
    a = APK(primary)
    entry["package"] = a.package
    entry["versionName"] = a.version_name
    entry["versionCode"] = a.version_code
    entry["app_name"] = a.get_app_name()
    entry["minSdk"] = a.get_min_sdk_version()
    entry["targetSdk"] = a.get_target_sdk_version()
    entry["permissions"] = sorted(a.get_permissions() or [])
    entry["activities"] = a.get_activities() or []
    entry["services"] = a.get_services() or []
    entry["receivers"] = a.get_receivers() or []
    entry["providers"] = a.get_providers() or []
    try:
        entry["cert"] = cert_info(primary)
    except Exception as e:
        entry["cert"] = {"error": repr(e)}
    # ABI set + split layout
    with zipfile.ZipFile(primary) as z:
        names = z.namelist()
    entry["abis_primary"] = sorted({n.split("/")[1] for n in names if n.startswith("lib/")})
    # for APKM: split inventory
    if ver == "4.0.8":
        apkm = os.path.join(BASE, "4.0.8/BIGBIGWON-4.0.8.apkm")
        with zipfile.ZipFile(apkm) as z:
            entry["splits"] = sorted(z.namelist())
            entry["split_meta"] = {}
            for n in z.namelist():
                data = z.read(n)
                entry["split_meta"][n] = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        # check split markers in each split manifest
        splitmark = {}
        with zipfile.ZipFile(apkm) as z:
            for n in z.namelist():
                sm = z.read(n)
                if "split=" in str(sm)[:200] or b"split" in sm[:4096]:
                    splitmark[n] = True
                with zipfile.ZipFile(__import__("io").BytesIO(sm)) as zz:
                    try:
                        mn = zz.read("AndroidManifest.xml")
                        idx = mn.find(b"config.")
                        splitmark[n] = str(mn[max(0, idx - 40):idx + 40]) if idx > 0 else "none"
                    except Exception as e:
                        splitmark[n] = "err " + repr(e)
        entry["split_markers"] = splitmark
    report[ver] = entry

with open(os.path.join(OUT, "meta.json"), "w") as f:
    json.dump(report, f, indent=1)
print(json.dumps(report, indent=1)[:4000])
