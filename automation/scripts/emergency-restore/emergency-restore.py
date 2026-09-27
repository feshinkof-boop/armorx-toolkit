#!/usr/bin/env python3
"""Emergency restore: write a previously captured known-good ARMOR-X config image back to the device.

This script REFUSES to run unless the baseline it is given is provably a real capture AND has been
validated by an actual restore round-trip on hardware. That gate is deliberate: an "emergency
restore" that was never tested is worse than none at all.

Validation gate (all must hold):
  baselines/device/<serial>/validated.json exists and contains {"restore_verified": true,
  "roundtrip_sha256": "<sha256 of the image after the verified D7 write + D6 re-read>"}
  the referenced .bin exists and its sha256 equals manifest["sha256"]
  manifest["crc_ok"] is true and manifest["declared_matches"] is true

Usage:
  /usr/bin/python3 emergency-restore.py --baseline <file.bin|dir> [--chunk 15] [--dry-run]
                                        [--i-have-read-the-readme]

Run with --dry-run first: it prints the exact frames it would send (D7 fragments + commit + D6
verify) without touching the device.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
from armorx_lab import frames as F                                  # noqa: E402


def load_baseline(path: str):
    if os.path.isdir(path):
        cands = sorted(f for f in os.listdir(path) if f.endswith(".bin"))
        if not cands:
            sys.exit("no .bin baseline in %s" % path)
        path = os.path.join(path, cands[-1])
    manifest_path = path[:-4] + ".json"
    if not os.path.exists(manifest_path):
        sys.exit("refusing: %s has no manifest (must be produced by the harness baseline capture)"
                 % path)
    image = open(path, "rb").read()
    manifest = json.load(open(manifest_path))
    return image, manifest, path, manifest_path


def validate(image: bytes, manifest: dict, path: str) -> list:
    problems = []
    sha = hashlib.sha256(image).hexdigest()
    if sha != manifest.get("sha256"):
        problems.append("sha256 mismatch: file %s vs manifest %s" % (sha, manifest.get("sha256")))
    ok, stored, computed = F.config_verify(image)
    if not manifest.get("crc_ok"):
        problems.append("manifest says the captured CRC never verified")
    if not ok:
        problems.append("CRC does not verify now: stored 0x%04X computed 0x%04X" % (stored, computed))
    if F.config_length(image) != len(image):
        problems.append("declared length %d != image length %d"
                        % (F.config_length(image), len(image)))
    if len(image) < 4 + 32:
        problems.append("image too small to be a config (%d bytes)" % len(image))
    validated = manifest.get("restore_verified") is True
    if not validated:
        problems.append("manifest has no successful restore round-trip "
                        "(restore_verified != true): the restore path has NOT been validated on "
                        "hardware yet, so this script will not write")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help=".bin file or directory containing one")
    ap.add_argument("--chunk", type=int, default=15,
                    help="fragment payload size = subpackageLength()-5 (15/43/67); default 15")
    ap.add_argument("--dry-run", action="store_true", help="print frames only")
    ap.add_argument("--i-have-read-the-readme", action="store_true")
    args = ap.parse_args()

    image, manifest, path, mpath = load_baseline(args.baseline)
    problems = validate(image, manifest, path)
    frags, commit = F.fragment_config(0xD7, image, args.chunk)
    verify = F.KNOWN_FRAMES["get_device_config"][0]

    print("baseline      : %s" % path)
    print("manifest      : %s" % mpath)
    print("image length  : %d bytes (declared %d)" % (len(image), F.config_length(image)))
    print("sha256        : %s" % hashlib.sha256(image).hexdigest())
    print("mapKeys       : %s" % (F.mapkeys(image) if len(image) >= 32 else "n/a"))
    print("frames        : %d D7 fragment(s) of %d bytes + commit" % (len(frags), args.chunk))
    for f in frags:
        print("   %s" % f.hex(" ").upper())
    print("   %s" % commit.hex(" ").upper())
    print("verify with   : %s (D6 re-read, compare sha256)" % verify.hex(" ").upper())

    if problems:
        print("\nREFUSING TO WRITE:")
        for p in problems:
            print("  - %s" % p)
        return 2
    if args.dry_run:
        print("\nDRY RUN: nothing was written.")
        return 0
    if not args.i_have_read_the_readme:
        print("\nRefusing: pass --i-have-read-the-readme after reading README.md")
        return 2

    from armorx_lab.transport import BumbleTransport       # imported late on purpose
    from armorx_lab.device import Session, State

    tr = BumbleTransport()
    tr.connect()
    s = Session(logdir=os.path.join(HERE, "logs"), device_serial=manifest["device_serial"],
                transport=tr, app_version=manifest.get("app_version", "unknown"))
    s.transition(State.RESTORING, "validated baseline restore")
    for f in frags:
        s.send(f, expect_reply=False, label="restore D7 fragment")
    s.send(commit, expect_reply=False, label="restore commit")
    s.send(F.KNOWN_FRAMES["write_step"][0], label="restore follow-up 0E")
    reply = s.send(verify, label="restore verify D6")
    if reply is None:
        s.close(State.FAILED, "no reply to verification read")
        return 3
    image2 = F.parse_frame(reply).payload
    sha2 = hashlib.sha256(image2).hexdigest()
    if sha2 == manifest["sha256"]:
        s.close(State.COMPLETE, "restore verified")
        print("\nRESTORE VERIFIED: sha256 %s" % sha2)
        return 0
    s.close(State.FAILED, "restore mismatch")
    print("\nRESTORE MISMATCH: got %s expected %s - device left in an unknown config state, "
          "re-run with the other saved baseline or restore from the app" % (sha2, manifest["sha256"]))
    return 4


if __name__ == "__main__":
    sys.exit(main())
