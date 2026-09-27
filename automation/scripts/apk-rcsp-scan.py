#!/usr/bin/env python3
"""apk-rcsp-scan.py -- look for JieLi RCSP fingerprints inside the local app packages.

The real device exposes a JieLi RCSP-compatible service (AE00/AE01/AE02) - PROVEN LIVE.
The open question is whether the official apps actually USE RCSP. This scans the APK
builds that exist locally and reports every hit with its location, so a negative result
is evidence rather than an impression.

Fingerprints (from JieLi SDK/OTA implementations and the device's own service table):
  service/write/notify UUIDs  ae00 ae01 ae02
  packet marker               FE DC BA
  JieLi namespaces/classes    com/jieli, jl_bt_ota, JL_OTA, RCSP, jieli
  auth/keys                   authkey, procode, JL_AUTH
  update artefacts            update.ufw, jl_isd.fw, isd_download
  the ArmorX config layer     ffe1 ffe2 (expected present - the app's own channel)

Run on APK copies only; nothing here touches the device.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import zipfile

PATTERNS = {
    "service_uuid_ae00": [b"ae00", b"AE00", b"0000ae00"],
    "service_uuid_ae01": [b"ae01", b"AE01", b"0000ae01"],
    "service_uuid_ae02": [b"ae02", b"AE02", b"0000ae02"],
    "rcsp_marker_fedcba": [b"\xfe\xdc\xba", b"FEDCBA", b"fe dc ba"],
    "jieli_ns": [b"com/jieli", b"com.jieli", b"jieli"],
    "jl_bt_ota": [b"jl_bt_ota", b"JL_OTA", b"JL_bt_ota", b"JLOta", b"jl_ota"],
    "rcsp_word": [b"RCSP", b"rcsp"],
    "auth": [b"authkey", b"AUTHKEY", b"procode", b"PROCODE", b"JL_AUTH"],
    "update_artefacts": [b"update.ufw", b"jl_isd.fw", b"isd_download", b".ufw"],
    "armorx_channel": [b"ffe1", b"FFE1", b"ffe2", b"FFE2"],
    "bd19_ac632": [b"BD19", b"bd19", b"AC632", b"ac632", b"AC632N"],
    "rcsp_ops": [b"JL_OP", b"cmdGetDeviceInfo", b"RCSP_CMD", b"rcspCommand"],
}
MAX_HITS_PER_PATTERN = 12


def scan_apk(path: pathlib.Path) -> dict:
    result = {"apk": str(path), "size": path.stat().st_size, "hits": {}, "entries_scanned": 0}
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        result["error"] = str(exc)
        return result
    with zf:
        for info in zf.infolist():
            if info.is_dir() or info.file_size > 80 * 1024 * 1024:
                continue
            name = info.filename
            if not (name.endswith((".dex", ".so", ".xml", ".json", ".arsc", ".txt", ".bin", ".dat"))
                    or "assets" in name):
                continue
            try:
                blob = zf.read(info)
            except (RuntimeError, zipfile.BadZipFile):
                continue
            result["entries_scanned"] += 1
            low = blob.lower()
            for pattern_name, needles in PATTERNS.items():
                for needle in needles:
                    idx = low.find(needle.lower())
                    if idx < 0:
                        continue
                    bucket = result["hits"].setdefault(pattern_name, [])
                    if len(bucket) >= MAX_HITS_PER_PATTERN:
                        break
                    bucket.append({"entry": name, "needle": needle.decode("latin-1"),
                                   "offset": idx,
                                   "context": blob[max(0, idx - 24):idx + 40]
                                   .decode("latin-1", "replace")})
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("apks", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    docs = [scan_apk(pathlib.Path(a)) for a in args.apks]
    summary = {}
    for d in docs:
        summary[pathlib.Path(d["apk"]).name] = {
            "rcsp_service_uuids": bool(d["hits"].get("service_uuid_ae00")
                                       or d["hits"].get("service_uuid_ae01")
                                       or d["hits"].get("service_uuid_ae02")),
            "jieli_namespace": bool(d["hits"].get("jieli_ns")),
            "rcsp_word": bool(d["hits"].get("rcsp_word")),
            "armorx_channel_ffe": bool(d["hits"].get("armorx_channel")),
            "pattern_names_hit": sorted(d["hits"]),
            "entries_scanned": d["entries_scanned"],
        }
    out = {"pattern_legend": {k: [n.decode("latin-1") for n in v] for k, v in PATTERNS.items()},
           "per_apk_summary": summary, "details": docs}
    pathlib.Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
