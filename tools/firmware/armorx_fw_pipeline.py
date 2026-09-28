#!/usr/bin/env python3
"""armorx_fw_pipeline.py - one-command offline firmware analysis pipeline.

  hash originals -> unpack .bup containers -> JieLi-unpack each flash image ->
  collect metadata -> firmware-manifest.json

Everything is read-only with respect to the inputs; nothing touches hardware.

Usage:
  armorx_fw_pipeline.py <workspace-dir> <package-or-bup> [...]
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import struct
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import armorx_bup  # noqa: E402

JI_TCC = pathlib.Path("/home/salamanka/armorx-re/jieli-tools/jl-misctools/firmware")
JI_SHIM = pathlib.Path("/home/salamanka/armorx-re/jieli-shim")


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def jieli_unpack(image: pathlib.Path, outdir: pathlib.Path) -> dict:
    """Run the JieLi new-firmware unpacker on one flash image; return what it produced."""
    outdir.mkdir(parents=True, exist_ok=True)
    env = {"PYTHONPATH": f"{JI_SHIM}:{JI_TCC}", "PATH": "/usr/bin:/bin"}
    r = subprocess.run(["python3", "fwunpack_newfw.py", "--dirname", str(outdir / "jieli"), str(image)],
                       cwd=str(JI_TCC), capture_output=True, text=True, env=env, timeout=900)
    info = {"stdout": r.stdout[-8000:], "returncode": r.returncode}
    jdir = outdir / "jieli"
    if jdir.exists():
        info["files"] = {str(p.relative_to(jdir)): {"size": p.stat().st_size, "sha256": sha256_file(p)}
                         for p in sorted(jdir.rglob("*")) if p.is_file()}
        y = jdir / "jlfw.yaml"
        if y.exists():
            info["jlfw_yaml"] = y.read_text()
    return info


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    ws = pathlib.Path(argv[1])
    outdir = ws / "unpacked"
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "packages": []}
    for src in argv[2:]:
        srcp = pathlib.Path(src)
        entry: dict = {"source": str(srcp), "size": srcp.stat().st_size, "sha256": sha256_file(srcp)}
        try:
            hdr, images, table = armorx_bup.analyze(srcp)
            entry["bup_header"] = hdr
            entry["chunks"] = len(table)
            entry["images"] = []
            for idx, (name, image) in enumerate(images):
                tag = pathlib.Path(name).stem if name else f"slot{idx}"
                dst = outdir / f"{srcp.stem}__slot{idx}_{tag}.image.bin"
                dst.write_bytes(image)
                img_rec = {"slot": idx, "name": name, "path": str(dst), "size": len(image),
                           "sha256": hashlib.sha256(image).hexdigest()}
                if idx == 0:  # only fully unpack slot 0 (they are near-duplicates)
                    img_rec["jieli"] = jieli_unpack(dst, outdir / f"{srcp.stem}__slot{idx}")
                entry["images"].append(img_rec)
        except Exception as e:
            entry["error"] = f"{type(e).__name__}: {e}"
        manifest["packages"].append(entry)
        print(f"[ok] {srcp.name}: {len(entry.get('images', []))} image(s) {entry.get('error','')}")
    (ws / "firmware-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nmanifest -> {ws/'firmware-manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
