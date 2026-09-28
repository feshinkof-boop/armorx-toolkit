#!/usr/bin/env python3
"""armorx_fw_compare.py - cross-version comparison of ArmorX/JieLi firmware images.

Unpacks every .bup slot, runs the JieLi new-firmware unpacker on each image, and
builds a per-image comparison table: chip, keys, entry point, app.bin identity,
string-set delta. Offline/read-only.

Usage: armorx_fw_compare.py <workspace-dir> <bup> [...]
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import armorx_bup  # noqa: E402

JI_TCC = "/home/salamanka/armorx-re/jieli-tools/jl-misctools/firmware"
JI_SHIM = "/home/salamanka/armorx-re/jieli-shim"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def jieli(image: pathlib.Path, out: pathlib.Path) -> dict:
    env = {"PYTHONPATH": f"{JI_SHIM}:{JI_TCC}", "PATH": "/usr/bin:/bin"}
    r = subprocess.run(["python3", "fwunpack_newfw.py", "--dirname", str(out.resolve()), str(image.resolve())],
                       cwd=JI_TCC, capture_output=True, text=True, env=env, timeout=900)
    res = {"returncode": r.returncode, "log": r.stdout[-4000:]}
    if out.exists():
        app = out / "files" / "app.bin"
        if app.exists():
            d = app.read_bytes()
            res["app"] = {"size": len(d), "sha256": sha(d),
                          "strings": sorted({s.decode("latin1") for s in re.findall(rb"[\x20-\x7e]{6,}", d)})}
        for extra in ("files/cfg_tool.bin", "files/p11_code.bin", "top/uboot.boot", "top/isd_config.ini",
                      "decrypted.bin"):
            p = out / extra
            if p.exists():
                res[pathlib.Path(extra).name] = {"size": p.stat().st_size,
                                                 "sha256": sha(p.read_bytes())}
        y = out / "jlfw.yaml"
        if y.exists():
            res["jlfw_yaml"] = y.read_text()
    return res


def main(argv: list[str]) -> int:
    ws = pathlib.Path(argv[1])
    outdir = ws / "unpacked"
    rows = []
    for src in map(pathlib.Path, argv[2:]):
        hdr, images, _ = armorx_bup.analyze(src)
        for idx, (name, image) in enumerate(images):
            tag = pathlib.Path(name).stem if name else f"slot{idx}"
            odir = outdir / f"cmp__{src.stem}__slot{idx}"
            odir.mkdir(parents=True, exist_ok=True)
            imgp = odir / f"{tag}.image.bin"
            imgp.write_bytes(image)
            rec = {"package": src.name, "slot": idx, "image_name": name, "image_size": len(image),
                   "image_sha256": sha(image), "board_code": hdr["board_code"],
                   "version_string": hdr["version_string"]}
            rec["jieli"] = jieli(imgp, odir / "ji")
            rows.append(rec)
            print(f"[{src.name} slot{idx}] {name} size={len(image):,} chip={rec['jieli'].get('jlfw_yaml','').count('AC')and'AC632N'} "
                  f"app={rec['jieli'].get('app',{}).get('size')}")
    (ws / "cross-version.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"\nwrote {ws/'cross-version.json'} ({len(rows)} images)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
