#!/usr/bin/env python3
"""probe-d2.py -- why did D2 test mode stop streaming?

At 17:08 the same device, same frames, streamed 3295 status frames in D2 mode.
At 17:48/17:50 the identical sequence (GATT reads -> 0B -> D2 ON acked) produced
exactly one frame. This probe tries the cheap variations in order and reports the
frame count for each, so the difference is measured instead of guessed:

  A. plain D2 ON
  B. D2 OFF, pause, D2 ON
  C. D2 ON twice in a row
  D. 0B interleaved, then D2 ON again
  E. D2 ON then a long 10 s listen

Read-only apart from the D2 mode toggle itself, which is restored to OFF at the end.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LAB / "ble" / "virtual-armorx"))

from armorx_lab.transport import BumbleTransport  # noqa: E402

F_0B = bytes.fromhex("A5040BB4")
F_D2_ON = bytes.fromhex("A505D2017D")
F_D2_OFF = bytes.fromhex("A505D2007C")


def drain(tr, seconds: float) -> list[str]:
    out, end = [], time.monotonic() + seconds
    while time.monotonic() < end:
        chunk = tr.read(0.25)
        if chunk:
            out.append(chunk.hex())
    return out


def main() -> int:
    tr = BumbleTransport(transport="hci-socket:1")
    tr.connect()
    ident = tr.read_identity()
    print("identity:", {k: v.get("ascii") for k, v in ident.items()})
    results = {}

    tr.write(F_0B); print("0B ->", (tr.read(4.0) or b"").hex())
    tr.write(F_D2_ON); print("A: D2 ON ->", (tr.read(3.0) or b"").hex())
    results["A_plain_on"] = drain(tr, 3.0)
    print(f"   A frames: {len(results['A_plain_on'])}")

    tr.write(F_D2_OFF); tr.read(2.0); time.sleep(1.0)
    tr.write(F_D2_ON); print("B: OFF->ON ->", (tr.read(3.0) or b"").hex())
    results["B_off_then_on"] = drain(tr, 3.0)
    print(f"   B frames: {len(results['B_off_then_on'])}")

    tr.write(F_D2_ON); tr.read(2.0); tr.write(F_D2_ON); print("C: D2 ON twice")
    results["C_on_twice"] = drain(tr, 3.0)
    print(f"   C frames: {len(results['C_on_twice'])}")

    tr.write(F_0B); tr.read(3.0); tr.write(F_D2_ON); print("D: 0B then D2 ON")
    results["D_0b_then_on"] = drain(tr, 3.0)
    print(f"   D frames: {len(results['D_0b_then_on'])}")

    print("E: long 10 s listen ...")
    results["E_long_listen"] = drain(tr, 10.0)
    print(f"   E frames: {len(results['E_long_listen'])}")

    tr.write(F_D2_OFF); tr.read(2.0)
    tr.close()

    out = {k: {"frames": len(v), "first": v[:3]} for k, v in results.items()}
    out["identity"] = {k: v.get("ascii") for k, v in ident.items()}
    out["verdict"] = ("STREAMING" if any(len(v) > 5 for v in results.values())
                      else "NO_STREAM_IN_ANY_VARIANT")
    path = LAB / "results" / "runtime" / "d2-stream-probe.json"
    path.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
