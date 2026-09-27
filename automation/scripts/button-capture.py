#!/usr/bin/env python3
"""button-capture.py -- ONE physical button, ONE popup, TWO presses, analysed.

Implements the per-button workflow the operator asked for:

  connect -> 0B link health -> D2 test mode ON -> flush old notifications
  -> mark START -> show the ONE popup and BLOCK until the operator clicks
  -> drain -> mark END -> D2 OFF -> analyse only the frames inside that window

The popup click bounds the capture window, so there is no button timer and
nothing advances on its own: the operator decides when the action is finished.

Two-press rule (a single noisy frame must never become PROVEN LIVE):
  exactly two press runs of the SAME key id inside the window, each ending in a
  release (mask back to idle) -> PROVEN LIVE
  anything else (0, 1, 3+ presses, two different ids, no release) -> RETRY

Usage:
  button-capture.py --button RT --title "ARMOR-X BUTTON TEST - RT" \
      --message "Fully press RT and release it TWICE, then click DONE." \
      --expect-id 9 --session-dir results/experiments/<sess> \
      --transport hci-socket
Exit: 0 PROVEN LIVE / 1 operator cancelled or stop / 2 no usable capture /
      4 RETRY (inconsistent) / 5 device not reachable
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parent.parent
sys.path.insert(0, str(LAB / "automation" / "scripts"))
sys.path.insert(0, str(LAB / "ble" / "virtual-armorx"))

from armorx_lab.transport import BumbleTransport  # noqa: E402

F_0B = bytes.fromhex("A5040BB4")
F_D2_ON = bytes.fromhex("A505D2017D")
F_D2_OFF = bytes.fromhex("A505D2007C")
BYTE_BASE = {6: 0, 5: 8, 4: 16, 3: 24}


def ids_of(raw: bytes) -> list[int]:
    if len(raw) != 18 or raw[0] != 0xA5 or raw[2] != 0x02:
        return []
    out = []
    for byte_idx, base in BYTE_BASE.items():
        for bit in range(8):
            if raw[byte_idx] >> bit & 1:
                out.append(base + bit)
    return out


class Reader(threading.Thread):
    """Continuous rx buffer with timestamps; runs while the popup is open."""

    def __init__(self, tr) -> None:
        super().__init__(daemon=True)
        self.tr, self.frames, self.stop = tr, [], threading.Event()

    def run(self) -> None:
        while not self.stop.is_set():
            chunk = self.tr.read(0.3)
            if chunk:
                self.frames.append((dt.datetime.now().astimezone(), chunk))


def analyse(frames, t0, t1) -> dict:
    window = [(ts, raw) for ts, raw in frames if t0 <= ts <= t1]
    runs, idle_frames = [], 0
    for ts, raw in window:
        ids = ids_of(raw)
        if not ids:
            idle_frames += 1
            if runs and runs[-1]["released_at"] is None:
                runs[-1]["released_at"] = ts.isoformat()
            continue
        key = tuple(ids)
        if runs and runs[-1]["ids"] == list(key) and runs[-1]["released_at"] is None:
            runs[-1]["repeats"] += 1
            runs[-1]["last_ts"] = ts.isoformat()
            runs[-1]["raws"].append(raw.hex())
            continue
        runs.append({"ids": list(key), "pressed_at": ts.isoformat(), "last_ts": ts.isoformat(),
                     "repeats": 1, "released_at": None, "raws": [raw.hex()]})
    presses = [r for r in runs if len(r["ids"]) == 1]
    multi = [r for r in runs if len(r["ids"]) != 1]
    result = {
        "frames_in_window": len(window), "idle_frames": idle_frames,
        "press_runs": presses, "multi_bit_runs": multi,
        "analog_lt_values": sorted({bytes.fromhex(raw)[15] for _, raw in window
                                    if len(raw) == 18 and bytes.fromhex(raw)[15]}),
        "analog_rt_values": sorted({bytes.fromhex(raw)[16] for _, raw in window
                                    if len(raw) == 18 and bytes.fromhex(raw)[16]}),
    }
    ids = [r["ids"][0] for r in presses]
    resolved = []
    for r in presses:
        if r["released_at"] is not None:
            resolved.append(r["ids"][0])
    if len(presses) == 2 and len(set(ids)) == 1 and len(resolved) == 2 and not multi:
        result.update(verdict="PROVEN LIVE", rule="two presses of the same id, both with a release",
                      key_id=ids[0])
    elif len(presses) == 2 and len(set(ids)) == 1:
        result.update(verdict="RETRY", rule="two presses of the same id but a release was not observed",
                      key_id=ids[0])
    else:
        result.update(verdict="RETRY",
                      rule=f"{len(presses)} single-bit press run(s) {ids}"
                           + (f" plus {len(multi)} multi-bit run(s)" if multi else ""),
                      key_id=None)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--button", required=True, help="physical button name, e.g. RT")
    ap.add_argument("--title", default=None)
    ap.add_argument("--message", default=None)
    ap.add_argument("--expect-id", type=int, default=None, help="static expectation, for comparison only")
    ap.add_argument("--session-dir", required=True)
    ap.add_argument("--transport", default="hci-socket:1",
                    help="the lab adapter is hci1; a bare 'hci-socket' means hci0 "
                         "which is not ours (Errno 16 busy)")
    ap.add_argument("--address", default=None)
    ap.add_argument("--popup-timeout", type=float, default=900.0)
    ap.add_argument("--drain", type=float, default=0.6)
    # use-bumble.sh appends its own transport spec as trailing args, so tolerate them
    args, extra = ap.parse_known_args()

    sess = pathlib.Path(args.session_dir)
    outdir = sess / "button-tests"
    outdir.mkdir(parents=True, exist_ok=True)
    title = args.title or f"ARMOR-X BUTTON TEST - {args.button.upper()}"
    message = args.message or (
        f"Make sure the ARMOR-X is ON and awake (tap it once now), then press the "
        f"{args.button.upper()} button TWICE:\n\n"
        "PRESS - RELEASE\nshort pause\nPRESS - RELEASE\n\n"
        "Then click DONE - PRESSED TWICE.")

    tr = BumbleTransport(transport=args.transport, address=args.address)
    try:
        tr.connect()
    except Exception as exc:                      # noqa: BLE001 - report, never guess
        print(json.dumps({"verdict": "DEVICE_NOT_REACHABLE", "button": args.button,
                          "error": str(exc)}, indent=1))
        return 5

    tr.write(F_0B)
    health = tr.read(4.0)
    if not health:
        print(json.dumps({"verdict": "DEVICE_NOT_REACHABLE", "button": args.button,
                          "error": "0B link-health query got no reply"}, indent=1))
        tr.close()
        return 5
    print(f"link health 0B -> {health.hex()}")

    tr.write(F_D2_ON)
    d2_ack = tr.read(3.0)
    print(f"D2 ON -> {d2_ack.hex() if d2_ack else 'NO REPLY'}")

    # In D2 test mode the unit streams 0x02 status frames CONTINUOUSLY (the earlier
    # 900 s capture logged 3295 of them). Counting what the flush sees is therefore a
    # direct probe of "is D2 mode really streaming" - a zero here means the mode/link
    # is dead and the button must not be blamed for it.
    flush_frames = 0
    flush_end = time.monotonic() + 1.5
    while time.monotonic() < flush_end:
        if tr.read(0.2):
            flush_frames += 1
    d2_streaming = flush_frames > 0
    print(f"D2 streaming probe: {flush_frames} frame(s) in 1.5s flush -> "
          f"{'STREAMING' if d2_streaming else 'NOT STREAMING'}")

    reader = Reader(tr)
    reader.start()
    t0 = dt.datetime.now().astimezone()
    print(f"CAPTURE START {t0.isoformat()} -- waiting for the operator's click")

    ack_path = LAB / "results" / "runtime" / "operator-actions" / f"button_{args.button.lower()}.json"
    ack_path.unlink(missing_ok=True)
    req = subprocess.run(
        # run the dialog as the desktop user: these tools may execute under sudo
        # (use-bumble re-execs as root), and the popup + ack files must belong to
        # the interactive user, not to root.
        ["sudo", "-n", "-u", os.environ.get("ARMORX_DESKTOP_USER", "salamanka"),
         "python3", str(LAB / "automation" / "request_physical_action.py"),
         "--id", f"button_{args.button.lower()}", "--title", title, "--message", message,
         "--status", f"button: {args.button.upper()}  |  two presses required  |  "
                     + (f"static expectation: id {args.expect_id}" if args.expect_id is not None
                        else "static expectation: none recorded"),
         "--button", "DONE - PRESSED TWICE=done", "--button", "RETRY=retry",
         "--button", "STOP TESTING=cancel", "--timeout", str(args.popup_timeout)],
        capture_output=True, text=True)
    print(req.stdout.strip()[-400:])
    try:
        ack = json.loads(req.stdout)
    except json.JSONDecodeError:
        ack = {"status": "UNKNOWN", "response": "unknown"}

    time.sleep(args.drain)                                 # let the last frames land
    t1 = dt.datetime.now().astimezone()
    reader.stop.set()
    reader.join(timeout=2.0)
    # link-liveness re-check AFTER the operator's window: distinguishes "the button
    # produced nothing" from "the unit slept / the link died mid-test"
    tr.write(F_0B)
    post = tr.read(4.0)
    tr.write(F_D2_OFF)
    tr.read(2.0)
    tr.close()

    analysis = analyse(reader.frames, t0, t1)
    analysis.update({
        "button": args.button, "expect_id": args.expect_id,
        "window": {"start": t0.isoformat(), "end": t1.isoformat()},
        "operator_response": ack.get("response"), "operator_status": ack.get("status"),
        "operator_clicked_at": ack.get("clicked_at"),
        "d2_on_ack": d2_ack.hex() if d2_ack else None, "link_health_reply": health.hex(),
        "d2_streaming_probe_frames": flush_frames, "d2_streaming": d2_streaming,
        "link_alive_after_capture": post.hex() if post else None,
        "harness_extra_args": extra,
        "ts": time.time(),
    })
    out = LAB / "results" / "runtime" / "button-tests.jsonl"
    with out.open("a") as f:
        f.write(json.dumps(analysis) + "\n")
    (outdir / f"{args.button.lower()}.json").write_text(json.dumps(analysis, indent=1) + "\n")
    (sess / "session.jsonl").open("a").write(json.dumps({"event": "button_test", **analysis}) + "\n")

    print(json.dumps({k: analysis[k] for k in
                      ("button", "verdict", "rule", "key_id", "expect_id",
                       "operator_response", "analog_lt_values", "analog_rt_values",
                       "frames_in_window")}, indent=1))
    if ack.get("status") == "CANCEL":
        return 1
    if not d2_streaming or not post:
        print(json.dumps({"verdict": "DEVICE_NOT_STREAMING_OR_SLEPT", "button": args.button,
                          "d2_streaming_frames": flush_frames,
                          "link_alive_after_capture": post.hex() if post else None}, indent=1))
        return 5
    return 0 if analysis["verdict"] == "PROVEN LIVE" else 4


if __name__ == "__main__":
    raise SystemExit(main())
