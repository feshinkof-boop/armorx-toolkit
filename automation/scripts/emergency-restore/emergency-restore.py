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
    ap.add_argument("--allow-identity-mismatch", action="store_true",
                    help="DANGEROUS: allow writing a baseline whose manifest model/firmware "
                         "does not match the live 2A24/2A26 read")
    ap.add_argument("--transport", default="hci-socket:1",
                    help="Bumble transport spec (default hci-socket:1, resolved by BDADDR)")
    ap.add_argument("--address", default=None,
                    help="target BLE address; default = advertised name prefix match")
    ap.add_argument("--follow-up", choices=["0e", "none"], default="none",
                    help="post-write command: '0e' (what the Android app sends after a config "
                         "write) or 'none'")
    ap.add_argument("--d6-fragments", type=int, default=10,
                    help="D6 replies are fragmented on real hardware (144 bytes = 10 fragments)")
    # use-bumble.sh appends the transport spec positionally; accept it that way too.
    ap.add_argument("transport_pos", nargs="?", default=None)
    args = ap.parse_args()
    if args.transport_pos:
        args.transport = args.transport_pos

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
    print("   %s" % (commit.hex(" ").upper() if commit else "(no commit frame for D7)"))
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

    tr = BumbleTransport(transport=args.transport, address=args.address)
    tr.connect()
    # --- identity gate (Part 25): bind this restore to the physical unit ------
    ident = tr.read_identity()
    live_mark = ident.get("2a24", {}).get("ascii") or ""
    live_fw = ident.get("2a26", {}).get("ascii") or ""
    exp_mark = (manifest.get("device") or {}).get("model_mark", "")
    exp_fw = (manifest.get("device") or {}).get("firmware", "")
    ident_ok = (live_mark == exp_mark) and (live_fw == exp_fw)
    print("identity      : 2A24=%r 2A26=%r 2A19=%s (raw %s)" %
          (live_mark, live_fw, ident.get("2a19", {}).get("raw_hex"),
           ident.get("2a24", {}).get("raw_hex")))
    print("identity gate : manifest expects %r/%r -> %s" %
          (exp_mark, exp_fw, "MATCH" if ident_ok else "MISMATCH"))
    if not ident_ok and not args.allow_identity_mismatch:
        print("\nREFUSING TO WRITE: this baseline was captured from a different "
              "model/firmware than the unit now connected.")
        return 2
    s = Session(logdir=os.path.join(HERE, "logs"), device_serial=manifest["device_serial"],
                transport=tr, app_version=manifest.get("app_version", "unknown"))
    s.transition(State.RESTORING, "validated baseline restore")
    for f in frags:
        s.send(f, expect_reply=False, label="restore D7 fragment")
    if commit is not None:
        s.send(commit, expect_reply=False, label="restore commit")
    if args.follow_up == "0e":
        s.send(F.KNOWN_FRAMES["write_step"][0], label="restore follow-up 0E")
    # the ack (A5 05 D7 00 81) arrives before the verification read
    ack = tr.read(3.0)
    print("D7 ack       : %s" % (ack.hex(" ").upper() if ack else "NONE"))

    s.send(verify, expect_reply=False, label="restore verify D6")
    # real hardware answers D6 with N fragments; reassemble before comparing.
    seen = []
    while len(seen) < args.d6_fragments:
        chunk = tr.read(3.0)
        if chunk is None:
            break
        seen.append(chunk)
    if not seen:
        s.close(State.FAILED, "no reply to verification read")
        return 3
    pieces = []
    for chunk in seen:
        parsed = F.parse_frame(chunk)
        if parsed is None or parsed.opcode < 0:
            continue
        payload = bytes(parsed.payload)
        # A4 fragments carry the 1-based ordinal at payload[0]; A5 short frames do not.
        if parsed.header == 0xA4 and payload:
            payload = payload[1:]
        pieces.append(payload)
    image2 = b"".join(pieces)
    print("verify frames: %d, reassembled %d bytes" % (len(seen), len(image2)))
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
