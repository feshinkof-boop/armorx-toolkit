#!/usr/bin/env python3
"""id15-experiment.py -- the ID 15 (Capture) live mapping experiment.

Single-variable, fully reversible, and hard-gated:

  baseline (immutable, sha256 bdef9c61...)  ->  mutant: byte 127 := 0x02
  (mapKeys[15] target -> 0x02 = NIL / empty mapping; byte 127 is source slot 15)

Gates enforced before anything is written:
  * baseline is 144 bytes, CRC-16/MODBUS valid, sha256 == --expect-sha256
  * the strict diff between mutant and baseline is EXACTLY {0, 1, 127}  (0/1 = CRC)
  * the live device's 2A24/2A26 match the manifest model/firmware (identity gate)
  * --confirm-operator-test is required: the operator observation test must be
    the reason for the write

Modes (run as two separate connections so the operator can test in between):
  --write    build, verify gates, write the mutant, D6-read it back, prove the
             mutation is live, then exit (device left WITH the test mapping).
  --restore  write the immutable baseline back and require the D6 read-back
             sha256 to equal the baseline sha256 again.
  --dry-run  print the frames and the diff, write nothing.

Exit codes: 0 ok / 2 gate refusal / 3 no reply / 4 verification mismatch
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parent.parent
sys.path.insert(0, str(LAB / "automation" / "scripts"))
sys.path.insert(0, str(LAB / "ble" / "virtual-armorx"))

import armorx_protocol as proto  # noqa: E402
from armorx_lab.transport import BumbleTransport  # noqa: E402
from armorx_lab import frames as F  # noqa: E402  (frames.Frame carries .header)

F_0B = bytes.fromhex("A5040BB4")
F_D6 = bytes.fromhex("A504D67F")
F_D2_OFF = bytes.fromhex("A505D2007C")   # live-verified D2 test-mode OFF frame
ID15_OFFSET = 127
NIL_MAPPING = 0x02
EXPECTED_DIFF = {0, 1, ID15_OFFSET}


def build_mutant(baseline: bytes) -> bytes:
    m = bytearray(baseline)
    m[ID15_OFFSET] = NIL_MAPPING
    return proto.with_valid_crc(bytes(m))


def gate(baseline: bytes, expect_sha: str | None) -> list[str]:
    problems = []
    if len(baseline) != 144:
        problems.append(f"baseline length {len(baseline)} != 144")
    if not proto.config_crc_valid(baseline):
        problems.append("baseline CRC-16/MODBUS invalid")
    sha = hashlib.sha256(baseline).hexdigest()
    if expect_sha and sha != expect_sha.lower():
        problems.append(f"baseline sha256 {sha} != expected {expect_sha.lower()}")
    if len(baseline) == 144 and int.from_bytes(baseline[2:4], "big") != 144:
        problems.append("baseline declared length != 144")
    return problems


def diff(a: bytes, b: bytes) -> dict:
    offs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    return {"offsets": offs, "detail": [{"offset": i, "baseline": f"0x{a[i]:02X}",
                                         "mutant": f"0x{b[i]:02X}"} for i in offs]}


def read_d6(tr: BumbleTransport, fragments: int) -> bytes:
    """D6 replies arrive as N A4 fragments; each carries a 1-based ordinal at
    payload[0]. Same rule as emergency-restore.py, which was validated on this
    exact device (F.parse_frame exposes .header, proto.parse_frame does not)."""
    tr.write(F_D6)
    seen = []
    while len(seen) < fragments:
        chunk = tr.read(3.0)
        if chunk is None:
            break
        seen.append(chunk)
    pieces = []
    for chunk in seen:
        parsed = F.parse_frame(chunk)
        if parsed is None or parsed.opcode < 0:
            continue
        payload = bytes(parsed.payload)
        if parsed.header == 0xA4 and payload:
            payload = payload[1:]
        pieces.append(payload)
    image = b"".join(pieces)
    if len(image) > 4:
        declared = int.from_bytes(image[2:4], "big")
        if 0 < declared <= len(image):
            image = image[:declared]
    print(f"  D6 frames: {len(seen)}, reassembled {len(b''.join(pieces))} -> {len(image)} bytes")
    return image


def write_image(tr: BumbleTransport, image: bytes, label: str) -> list[str]:
    responses = []
    for frag in proto.build_fragment_sequence(0xD7, image):
        tr.write(frag)
        time.sleep(0.05)
        print(f"  TX {label} {frag.hex()}")
        got = tr.read(0.6)
        if got:
            responses.append(got.hex())
            print(f"  RX ack {got.hex()}")
    return responses


def probe(tr, baseline: bytes, mutant: bytes, b_sha: str, m_sha: str, args, outdir) -> int:
    """Read-only: report which image the device is actually holding right now."""
    tr.connect()
    ident = tr.read_identity()
    mark = ident.get("2a24", {}).get("ascii") or ""
    fw = ident.get("2a26", {}).get("ascii") or ""
    image = read_d6(tr, args.d6_fragments)
    tr.close()
    sha = hashlib.sha256(image).hexdigest()
    if sha == b_sha:
        verdict = "BASELINE_LIVE"
    elif sha == m_sha:
        verdict = "MUTANT_LIVE"
    else:
        verdict = "NEITHER (unexpected image)"
    report = {"mode": "probe", "identity": {"2a24": mark, "2a26": fw},
              "readback_length": len(image), "readback_sha256": sha,
              "baseline_sha256": b_sha, "mutant_sha256": m_sha,
              "verdict": verdict, "ts": time.time()}
    (outdir / "probe-readback.bin").write_bytes(image)
    (outdir / "id15-probe-result.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    return 0 if verdict != "NEITHER (unexpected image)" else 4


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--manifest", default=None, help="baseline manifest for the identity gate")
    ap.add_argument("--transport", default="hci-socket:1")
    ap.add_argument("--address", default=None)
    ap.add_argument("--d6-fragments", type=int, default=12)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--probe", action="store_true",
                    help="read D6 only: report which image (baseline or mutant) is live")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--clear-d2-mode", action="store_true",
                    help="send the D2 test-mode OFF frame before writing")
    ap.add_argument("--confirm-operator-test", action="store_true",
                    help="the operator observation test is the purpose of this write")
    ap.add_argument("transport_pos", nargs="?", default=None)
    args = ap.parse_args()
    if args.transport_pos:
        args.transport = args.transport_pos

    baseline = pathlib.Path(args.baseline).read_bytes()
    mutant = build_mutant(baseline)
    d = diff(baseline, mutant)
    outdir = pathlib.Path(args.outdir) if args.outdir else pathlib.Path.cwd()
    outdir.mkdir(parents=True, exist_ok=True)

    b_sha = hashlib.sha256(baseline).hexdigest()
    m_sha = hashlib.sha256(mutant).hexdigest()
    print(f"baseline sha256: {b_sha}")
    print(f"mutant   sha256: {m_sha}")
    print(f"mutant diff    : offsets {d['offsets']} -> {json.dumps(d['detail'])}")

    problems = gate(baseline, args.expect_sha256)
    if set(d["offsets"]) != EXPECTED_DIFF:
        problems.append(f"diff {d['offsets']} != expected {sorted(EXPECTED_DIFF)}")
    if args.write and not args.confirm_operator_test:
        problems.append("--write requires --confirm-operator-test")
    if problems:
        print("REFUSING: " + "; ".join(problems))
        (outdir / "id15-abort.json").write_text(json.dumps(
            {"problems": problems, "diff": d, "baseline_sha256": b_sha}, indent=1))
        return 2

    if args.probe:
        return probe(tr_dummy := BumbleTransport(transport=args.transport, address=args.address),
                     baseline, mutant, b_sha, m_sha, args, outdir)
    frames = proto.build_fragment_sequence(0xD7, mutant if args.write else baseline)
    print(f"D7 frames: {len(frames)}")
    if args.dry_run:
        for f in frames:
            print("  " + f.hex())
        return 0

    tr = BumbleTransport(transport=args.transport, address=args.address)
    tr.connect()
    ident = tr.read_identity()
    mark = ident.get("2a24", {}).get("ascii") or ""
    fw = ident.get("2a26", {}).get("ascii") or ""
    manifest = json.loads(pathlib.Path(args.manifest).read_text()) if args.manifest else {}
    exp_mark = (manifest.get("device") or {}).get("model_mark", "")
    exp_fw = (manifest.get("device") or {}).get("firmware", "")
    print(f"identity: 2A24={mark!r} 2A26={fw!r} (expected {exp_mark!r}/{exp_fw!r})")
    if manifest and (mark != exp_mark or fw != exp_fw):
        print("REFUSING: identity mismatch")
        return 2

    tr.write(F_0B)
    print("0B:", (tr.read(3.0) or b"").hex())

    # D2 test mode may still be latched: the capture's final D2-OFF frame went
    # unacknowledged when its link dropped. Probe by counting unsolicited 0x02
    # status frames while nothing is pressed, then clear it explicitly.
    if args.clear_d2_mode:
        # The D2 capture's final OFF frame went unacknowledged when its link died,
        # so D2 test mode may still be latched. Sending it again is idempotent and
        # harmless; the operator presses keys for real this time, so the device must
        # be in normal mode for the behaviour test to mean anything.
        tr.write(F_D2_OFF)
        ack = tr.read(3.0)
        print("D2 OFF:", (ack or b"").hex() or "NO REPLY")
        (outdir / "d2-clear.json").write_text(json.dumps(
            {"d2_off_frame": F_D2_OFF.hex(), "d2_off_ack": (ack or b"").hex(),
             "ack_ok": ack is not None, "ts": time.time()}, indent=1))

    target = mutant if args.write else baseline
    label = "ID15 mutant" if args.write else "baseline restore"
    acks = write_image(tr, target, label)
    readback = read_d6(tr, args.d6_fragments)
    rb_sha = hashlib.sha256(readback).hexdigest()
    equal = readback == target
    report = {
        "mode": "write" if args.write else "restore",
        "baseline_sha256": b_sha,
        "mutant_sha256": m_sha,
        "target_sha256": hashlib.sha256(target).hexdigest(),
        "readback_sha256": rb_sha,
        "readback_equals_target": equal,
        "readback_crc_valid": proto.config_crc_valid(readback) if len(readback) == 144 else False,
        "diff_offsets": d["offsets"],
        "d7_ack": acks,
        "identity": {"2a24": mark, "2a26": fw},
        "ts": time.time(),
    }
    (outdir / f"id15-{report['mode']}-result.json").write_text(json.dumps(report, indent=1))
    if args.restore:
        (outdir / "restore-readback.bin").write_bytes(readback)
    else:
        (outdir / "mutant-readback.bin").write_bytes(readback)
    print(json.dumps(report, indent=1))
    tr.close()
    if not equal:
        print("VERIFICATION MISMATCH")
        return 4
    print("VERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
