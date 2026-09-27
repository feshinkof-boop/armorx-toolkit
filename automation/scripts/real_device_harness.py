#!/usr/bin/env python3
"""Real-device harness CLI for the ARMOR-X lab (Phases 10/11/13).

Subcommands
  status                      show what the harness can do right now (transport availability)
  identify                    read 0B / EF / E4 and record the identity block
  baseline                    capture the 144-byte config, hash it, verify its CRC, save it
  verify-restore              perform the D7 write -> D6 re-read cycle and mark the baseline
                              manifest restore_verified:true when it round-trips byte-identically
  experiment <ID>             run one experiment from automation/experiment-matrix/matrix.json
                              (one variable per run; restores the baseline afterwards)
  prompt                      print the physical-state questions for the operator and record the
                              answers into the session JSONL

Device-presence discipline (Phase 13): every wait is bounded, link loss is classified as
DEVICE_SLEEP_OR_LINK_LOSS, and nothing runs until `--serial` names an existing baseline directory
for `experiment`/`verify-restore`. The ARMOR-X auto power-off timer is treated as a first-class
failure mode, never as "the protocol rejected our frame".

Usage examples
  /usr/bin/python3 real_device_harness.py status
  /usr/bin/python3 real_device_harness.py --serial armorx01 --dry-run baseline
  /usr/bin/python3 real_device_harness.py --serial armorx01 identify
  /usr/bin/python3 real_device_harness.py --serial armorx01 experiment L01
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from armorx_lab import frames as F                                # noqa: E402
from armorx_lab import transport as T                             # noqa: E402
from armorx_lab.device import Session, State                       # noqa: E402

LAB = os.path.abspath(os.path.join(HERE, "..", ".."))
DEVICE_BASE = os.path.join(LAB, "baselines", "device")
MATRIX = os.path.join(LAB, "automation", "experiment-matrix", "matrix.json")
LOGSDIR = os.path.join(LAB, "logs", "device")
PHYSICAL_QUESTIONS = ["Receiver LED:", "ARMOR-X LED:", "Controller attached:",
                      "ARMOR-X awake:"]


def resolve_transport(args):
    if args.transport == "null":
        return T.NullTransport({}), "null"
    if args.transport == "bumble":
        tr = T.BumbleTransport(transport=args.bumble_transport)
        tr.connect()
        return tr, "bumble"
    # default: bumble if importable, else fail loudly (never silently swap transports)
    try:
        import bumble  # noqa: F401
    except Exception as exc:
        sys.exit("no usable transport: bumble is not importable (%s). Use --transport null for a "
                 "logic-only run, or install bumble (see ble/bumble/)." % exc)
    tr = T.BumbleTransport(transport=args.bumble_transport)
    tr.connect()
    return tr, "bumble"


def baseline_dir(serial: str) -> str:
    return os.path.join(DEVICE_BASE, serial)


def latest_baseline(serial: str):
    d = baseline_dir(serial)
    if not os.path.isdir(d):
        return None
    bins = sorted(f for f in os.listdir(d) if f.endswith(".bin"))
    return os.path.join(d, bins[-1]) if bins else None


def cmd_status(args) -> int:
    rep = {"lab": LAB, "matrix": os.path.exists(MATRIX), "device_baselines": {},
           "transports": {}}
    if os.path.isdir(DEVICE_BASE):
        for s in sorted(os.listdir(DEVICE_BASE)):
            b = latest_baseline(s)
            rep["device_baselines"][s] = b or "no baseline yet"
    try:
        import bumble  # noqa: F401
        rep["transports"]["bumble"] = "available"
    except Exception as exc:
        rep["transports"]["bumble"] = "unavailable: %s" % exc
    rep["transports"]["null"] = "available (logic only)"
    print(json.dumps(rep, indent=1))
    return 0


def cmd_identify(args) -> int:
    tr, name = resolve_transport(args)
    s = Session(logdir=LOGSDIR, device_serial=args.serial, transport=tr,
                app_version=args.app_version)
    if not s.wait_for_device(timeout=args.wait):
        s.close(State.FAILED, "device never appeared")
        return 3
    out = {}
    for key in ("get_version", "get_device_uuid", "get_mtu"):
        r = s.send(F.KNOWN_FRAMES[key][0], label=key)
        out[key] = None if r is None else {"hex": r.hex(" ").upper(),
                                           "payload": F.parse_frame(r).payload.hex(" ").upper()}
    s.close(State.COMPLETE, "identify done")
    print(json.dumps(out, indent=1))
    return 0 if out["get_version"] else 4


def cmd_baseline(args) -> int:
    tr, name = resolve_transport(args)
    s = Session(logdir=LOGSDIR, device_serial=args.serial, transport=tr,
                app_version=args.app_version)
    if not s.wait_for_device(timeout=args.wait):
        s.close(State.FAILED, "device never appeared")
        return 3
    try:
        meta = s.capture_baseline(baseline_dir(args.serial))
    except RuntimeError as exc:
        s.close(State.FAILED, str(exc))
        print("FAILED: %s" % exc)
        return 4
    s.close(State.COMPLETE, "baseline captured")
    print(json.dumps(meta, indent=1))
    return 0


def cmd_verify_restore(args) -> int:
    """D7 write of the saved baseline, then D6 re-read; marks restore_verified on exact match."""
    if args.transport == "null" or args.dry_run:
        print("verify-restore needs real hardware; refusing to mark anything as verified in a "
              "dry run or with the null transport.")
        return 2
    b = latest_baseline(args.serial)
    if not b:
        print("no baseline for %s" % args.serial)
        return 2
    image = open(b, "rb").read()
    manifest_path = b[:-4] + ".json"
    manifest = json.load(open(manifest_path))
    if manifest.get("sha256") != hashlib.sha256(image).hexdigest():
        print("baseline file does not match its manifest; recapture it")
        return 2

    tr, name = resolve_transport(args)
    s = Session(logdir=LOGSDIR, device_serial=args.serial, transport=tr,
                app_version=args.app_version)
    if not s.wait_for_device(timeout=args.wait):
        s.close(State.FAILED, "device never appeared")
        return 3
    s.transition(State.RESTORING, "verify-restore round trip")
    frags, commit = F.fragment_config(0xD7, image, args.chunk)
    for f in frags:
        s.send(f, expect_reply=False, label="verify-restore D7 fragment")
    s.send(commit, expect_reply=False, label="verify-restore commit")
    s.send(F.KNOWN_FRAMES["write_step"][0], label="verify-restore 0E")
    reply = s.send(F.KNOWN_FRAMES["get_device_config"][0], label="verify-restore D6")
    if reply is None:
        s.close(State.DEVICE_SLEEP_OR_LINK_LOSS, "no reply to verification read")
        print("NO REPLY to D6 - device may have powered off (DEVICE_SLEEP_OR_LINK_LOSS), or the "
              "write sequence is wrong. Manifest NOT marked as verified.")
        return 3
    image2 = F.parse_frame(reply).payload
    sha2 = hashlib.sha256(image2).hexdigest()
    if sha2 != manifest["sha256"]:
        s.close(State.FAILED, "round trip mismatch")
        print("MISMATCH: device now returns %s, baseline is %s" % (sha2, manifest["sha256"]))
        return 4
    manifest["restore_verified"] = True
    manifest["roundtrip_sha256"] = sha2
    manifest["restore_verified_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    manifest["restore_chunk"] = args.chunk
    json.dump(manifest, open(manifest_path, "w"), indent=1)
    s.close(State.COMPLETE, "restore verified")
    print("RESTORE VERIFIED; manifest updated: %s" % manifest_path)
    return 0


def cmd_experiment(args) -> int:
    matrix = json.load(open(MATRIX))
    exp = next((e for e in matrix["experiments"] if e["id"] == args.exp.upper()), None)
    if exp is None:
        print("unknown experiment %s; available: %s"
              % (args.exp, ", ".join(e["id"] for e in matrix["experiments"])))
        return 2
    b = latest_baseline(args.serial)
    if exp["id"] != "L01" and not b:
        print("refusing: experiment %s needs a captured baseline for %s (run 'baseline' first)"
              % (exp["id"], args.serial))
        return 2
    print(json.dumps(exp, indent=1))
    print("\nThis command is a runbook driver, not an autonomous writer. It will only perform the "
          "requests listed above, one variable at a time, and it restores the baseline afterwards.\n"
          "Implementation of the individual write experiments is gated on the validated baseline "
          "(see baselines/device/README.md).")
    tr, name = resolve_transport(args)
    s = Session(logdir=LOGSDIR, device_serial=args.serial, transport=tr,
                app_version=args.app_version)
    if not s.wait_for_device(timeout=args.wait):
        s.close(State.FAILED, "device never appeared")
        return 3
    s.transition(State.RUNNING_EXPERIMENT, "experiment %s" % exp["id"], experiment=exp["id"])
    if exp["id"] == "L01":
        for key in ("get_version", "get_device_uuid", "get_mtu"):
            s.send(F.KNOWN_FRAMES[key][0], label=key)
        try:
            s.capture_baseline(baseline_dir(args.serial))
        except RuntimeError as exc:
            s.close(State.FAILED, str(exc))
            return 4
    elif exp["id"] == "L02":
        s.send(F.KNOWN_FRAMES["read_firmware"][0], label="read_firmware")
    else:
        print("experiment %s requires the validated-baseline workflow; see "
              "results/final/real-hardware-readiness.md" % exp["id"])
    s.close(State.COMPLETE, "experiment %s finished" % exp["id"])
    return 0


def cmd_prompt(args) -> int:
    print("Answer for the operator record (device serial %s):" % args.serial)
    answers = {"asked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    for q in PHYSICAL_QUESTIONS:
        answers[q] = input("  %-22s " % q).strip() or "UNKNOWN"
    p = os.path.join(LOGSDIR, "physical-state-%s.jsonl" % args.serial)
    os.makedirs(LOGSDIR, exist_ok=True)
    with open(p, "a") as fh:
        fh.write(json.dumps(answers) + "\n")
    print("recorded in %s" % p)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "identify", "baseline", "verify-restore",
                                        "experiment", "prompt"])
    ap.add_argument("exp", nargs="?", help="experiment id for the 'experiment' command")
    ap.add_argument("--serial", default="armorx01")
    ap.add_argument("--transport", default="auto", choices=["auto", "null", "bumble"])
    ap.add_argument("--bumble-transport", default="hci-socket")
    ap.add_argument("--app-version", default="unknown")
    ap.add_argument("--chunk", type=int, default=15)
    ap.add_argument("--wait", type=float, default=45.0, help="seconds to wait for the device")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run and args.transport == "auto":
        args.transport = "null"
    return {"status": cmd_status, "identify": cmd_identify, "baseline": cmd_baseline,
            "verify-restore": cmd_verify_restore, "experiment": cmd_experiment,
            "prompt": cmd_prompt}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
