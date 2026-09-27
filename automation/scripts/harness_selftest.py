#!/usr/bin/env python3
"""Self-test for the real-device harness (no hardware required).

Proves, with a NullTransport, that:
  1. the state machine reaches the required states and logs every transition as JSONL,
  2. the watchdog classifies silence as DEVICE_SLEEP_OR_LINK_LOSS instead of "protocol rejected",
  3. a baseline capture writes a byte-exact .bin + metadata with a verified CRC and sha256,
  4. a missing reply is recorded as no_reply (never as a fabricated success),
  5. the frames module still matches the live-captured anchors.

Exit code 0 = all checks passed. Run:  python3 automation/scripts/harness_selftest.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "armorx_lab"))

from armorx_lab import frames as F                     # noqa: E402
from armorx_lab import transport as T                  # noqa: E402
from armorx_lab.device import Session, State           # noqa: E402

FAILURES = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print("%-58s %s%s" % (name, "PASS" if cond else "FAIL", (" - " + detail) if detail else ""))
    if not cond:
        FAILURES.append(name)


def make_config_reply(length: int = 144) -> bytes:
    """A synthetic but format-correct 144-byte ARMOR-X Pro image inside a D6 reply frame."""
    image = bytearray(length)
    image[2:4] = length.to_bytes(2, "big")
    for i in range(108):                      # plausible parameter block
        image[4 + i] = (i * 7) & 0xFF
    image[112:144] = bytes(range(32))         # identity mapKeys
    image = F.config_with_crc(bytes(image))
    return F.build_short(0xD6, image, length=4 + length)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="armorx-harness-selftest-")
    try:
        # ---- 1. frames still match the live anchors
        for name, anchor in F.LIVE_ANCHORS.items():
            got = F.KNOWN_FRAMES[name][0].hex(" ").upper()
            check("anchor %s == %s" % (name, anchor), got == anchor, got)

        cfg_reply = make_config_reply()
        script = {
            F.KNOWN_FRAMES["get_version"][0]: F.build_short(0x0B, b"2741"),
            F.KNOWN_FRAMES["get_device_uuid"][0]: F.build_short(0xEF, bytes(range(8))),
            F.KNOWN_FRAMES["get_device_config"][0]: cfg_reply,
        }
        tr = T.NullTransport(script)
        s = Session(logdir=tmp, device_serial="SELFTEST", transport=tr, notify_timeout=0.4,
                    device_watchdog=2.0)
        check("initial state WAITING_FOR_DEVICE", s.state is State.WAITING_FOR_DEVICE, s.state.value)
        check("wait_for_device finds the scripted device", s.wait_for_device(timeout=2.0))
        check("state after detection DEVICE_AWAKE", s.state is State.DEVICE_AWAKE, s.state.value)

        v = s.send(F.KNOWN_FRAMES["get_version"][0], label="get_version")
        check("0B reply received", v is not None)
        check("0B reply parsed & checksum ok", v is not None and F.parse_frame(v).checksum_ok)

        meta = s.capture_baseline(os.path.join(tmp, "baselines"))
        check("baseline .bin written", os.path.exists(meta["file"]))
        check("baseline sha256 recorded", len(meta["sha256"]) == 64, meta["sha256"][:16] + "...")
        check("baseline CRC verified", bool(meta["crc_ok"]),
              "stored %s computed %s" % (meta["crc_stored"], meta["crc_computed"]))
        check("baseline declared length == file length", meta["declared_matches"],
              "%s vs %s" % (meta["declared_len"], meta["config_len"]))
        check("mapKeys tail recovered", meta["mapkeys"] == list(range(32)))

        # ---- 4. silence must not be recorded as success
        unknown = F.build_short(0xDD)          # not in the script -> no reply
        r = s.send(unknown, label="unknown_cmd")
        check("unknown command returns None (no fabricated reply)", r is None)

        # ---- 2. watchdog fires on silence
        s.transition(State.DEVICE_AWAKE, "resume for watchdog test")
        import time
        s.last_seen = time.monotonic() - 99
        st = s.check_watchdog()
        check("watchdog -> DEVICE_SLEEP_OR_LINK_LOSS",
              st is State.DEVICE_SLEEP_OR_LINK_LOSS and s.state is st, str(st))

        s.close(State.COMPLETE, "selftest done")

        # ---- 1b. JSONL audit
        recs = [json.loads(l) for l in open(s.jsonl_path)]
        states = [r["to_state"] for r in recs if r["event"] == "state_transition"]
        check("JSONL has state transitions", len(states) >= 5, " -> ".join(states))
        check("all states are valid enum members",
              all(x in {e.value for e in State} for x in states))
        check("no_reply event recorded", any(r["event"] == "no_reply" for r in recs))
        check("raw capture file has TX/RX lines", os.path.getsize(s.raw_path) > 0,
              "%d bytes" % os.path.getsize(s.raw_path))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d check(s) failed" % len(FAILURES) if FAILURES else "\nALL CHECKS PASSED")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
