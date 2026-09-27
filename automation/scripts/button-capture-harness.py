#!/usr/bin/env python3
"""button-capture-harness.py -- ONE button, ONE popup, TWO presses, using the
PROVEN capture path.

Why this exists: a hand-rolled re-implementation of the BLE session got
"D2 ON acknowledged" but captured zero frames, while the harness path
(ble/real-device/armorx_real.py --phase d2, the code that produced the validated
3295-frame capture) streams continuously. So this tool drives that proven path
and uses the one-shot GUI only to synchronise with the operator.

Sequence:
  1. launch the harness D2 capture into a session dir (proven mode-enable sequence:
     connect -> GATT identity reads -> 0B -> D2 ON -> stream)
  2. wait until the stream is genuinely live (>= --min-frames 0x02 frames inside a
     short probe window). Failure here = DEVICE_NOT_STREAMING, the button is NOT blamed
  3. show ONE popup, block until the operator clicks
  4. drain, stop the capture, analyse ONLY the frames inside [start, end]
  5. two-press rule: exactly two press runs of the same key id, each with a release
     -> PROVEN LIVE; anything else -> RETRY

Exit: 0 PROVEN LIVE / 1 cancelled / 2 capture never streamed / 4 RETRY
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
LAB = HERE.parent.parent
BYTE_BASE = {6: 0, 5: 8, 4: 16, 3: 24}


def parse_ts(ts: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def ids_of(raw: bytes) -> list[int]:
    if len(raw) != 18 or raw[0] != 0xA5 or raw[2] != 0x02:
        return []
    out = []
    for byte_idx, base in BYTE_BASE.items():
        for bit in range(8):
            if raw[byte_idx] >> bit & 1:
                out.append(base + bit)
    return out


def read_rx(jsonl: pathlib.Path) -> list[tuple[dt.datetime, bytes]]:
    """All rx frames recorded by the harness so far."""
    if not jsonl.exists():
        return []
    out = []
    for line in jsonl.read_text(errors="replace").splitlines():
        if '"event": "rx"' not in line:
            continue
        try:
            e = json.loads(line)
            out.append((parse_ts(e["ts"]), bytes.fromhex(e["raw"])))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue
    return out


def analyse(frames, t0: dt.datetime, t1: dt.datetime) -> dict:
    window = [(ts, raw) for ts, raw in frames if t0 <= ts <= t1]
    status = [(ts, raw) for ts, raw in window if len(raw) == 18 and raw[2] == 0x02]
    runs = []
    for ts, raw in status:
        ids = ids_of(raw)
        if not ids:
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
    ids = [r["ids"][0] for r in presses]
    released = [r for r in presses if r["released_at"] is not None]
    analog_lt = sorted({raw[15] for _, raw in status if raw[15]})
    analog_rt = sorted({raw[16] for _, raw in status if raw[16]})
    res = {
        "frames_in_window": len(window), "status_frames": len(status),
        "idle_status_frames": len(status) - sum(r["repeats"] for r in runs),
        "press_runs": presses, "multi_bit_runs": multi,
        "analog_lt_values": analog_lt, "analog_rt_values": analog_rt,
    }
    if len(presses) == 2 and len(set(ids)) == 1 and len(released) == 2 and not multi:
        res.update(verdict="PROVEN LIVE", key_id=ids[0],
                   rule="two presses of the same id, each followed by a release")
    elif len(presses) == 2 and len(set(ids)) == 1:
        res.update(verdict="RETRY", key_id=ids[0],
                   rule="two presses of the same id but a release transition was not observed")
    else:
        res.update(verdict="RETRY", key_id=None,
                   rule=f"{len(presses)} single-bit press run(s) {ids}"
                        + (f", {len(multi)} multi-bit run(s)" if multi else ""))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--button", required=True)
    ap.add_argument("--expect-id", type=int, default=None)
    ap.add_argument("--session-dir", required=True)
    ap.add_argument("--transport", default="hci-socket:1")
    ap.add_argument("--min-frames", type=int, default=8,
                    help="0x02 frames required in the probe window to call the stream live")
    ap.add_argument("--probe-seconds", type=float, default=3.0)
    ap.add_argument("--popup-timeout", type=float, default=900.0)
    ap.add_argument("--drain", type=float, default=0.7)
    ap.add_argument("--capture-seconds", type=float, default=600.0)
    args, extra = ap.parse_known_args()

    sess = pathlib.Path(args.session_dir)
    sess.mkdir(parents=True, exist_ok=True)
    outdir = sess / "button-tests"
    outdir.mkdir(parents=True, exist_ok=True)
    cap_log = sess / f"capture-{args.button.lower()}.log"

    env = dict(os.environ)
    env["BUMBLE_PY"] = os.environ.get("BUMBLE_PY", str(LAB / "automation" / "scripts" / "py-bumble"))
    harness_cmd = [
        "bash", str(LAB / "automation" / "radio" / "use-bumble.sh"),
        "--transport", "hci-socket",
        "--command", f"{env['BUMBLE_PY']} ble/real-device/armorx_real.py "
                     f"--session-dir {sess} --seconds {int(args.capture_seconds)} "
                     f"--transport {args.transport} d2",
    ]
    print("starting proven D2 capture ...")
    cap = subprocess.Popen(harness_cmd, cwd=str(LAB), env=env,
                           stdout=cap_log.open("w"), stderr=subprocess.STDOUT,
                           start_new_session=True)

    # wait for a genuinely live D2 stream (this is the mode-engaged proof)
    jsonl = sess / "session.jsonl"
    before = len(read_rx(jsonl))
    deadline = time.monotonic() + 90
    live = False
    while time.monotonic() < deadline:
        time.sleep(args.probe_seconds)
        frames = read_rx(jsonl)
        fresh = frames[before:]
        status_fresh = [f for f in fresh if len(f[1]) == 18 and f[1][2] == 0x02]
        print(f"  stream probe: {len(status_fresh)} new 0x02 frame(s)")
        if len(status_fresh) >= args.min_frames:
            live = True
            break
        if cap.poll() is not None:
            print(f"  capture process exited early rc={cap.returncode}")
            break
    if not live:
        cap.terminate()
        print(json.dumps({"verdict": "DEVICE_NOT_STREAMING", "button": args.button,
                          "note": "D2 mode never produced a continuous status stream; "
                                  "the button is not blamed - check power/awake state",
                          "capture_log": str(cap_log)}, indent=1))
        return 2

    t0 = dt.datetime.now().astimezone()
    print(f"CAPTURE START {t0.isoformat()} -- showing the popup")
    req = subprocess.run(
        # run the dialog as the desktop user: these tools may execute under sudo
        # (use-bumble re-execs as root), and the popup + ack files must belong to
        # the interactive user, not to root.
        ["sudo", "-n", "-u", os.environ.get("ARMORX_DESKTOP_USER", "salamanka"),
         "python3", str(LAB / "automation" / "request_physical_action.py"),
         "--id", f"button_{args.button.lower()}",
         "--title", f"ARMOR-X BUTTON TEST - {args.button.upper()}",
         "--message", f"Press the {args.button.upper()} button TWICE:  PRESS - RELEASE, "
                      f"short pause, PRESS - RELEASE.  Then click DONE.",
         "--status", f"button: {args.button.upper()} | two presses required | "
                     + (f"static expectation: id {args.expect_id}" if args.expect_id is not None
                        else "static expectation: none recorded"),
         "--button", "DONE - PRESSED TWICE=done", "--button", "RETRY=retry",
         "--button", "STOP TESTING=cancel", "--timeout", str(args.popup_timeout)],
        capture_output=True, text=True)
    try:
        ack = json.loads(req.stdout)
    except json.JSONDecodeError:
        ack = {"status": "UNKNOWN", "response": "unknown"}

    time.sleep(args.drain)
    t1 = dt.datetime.now().astimezone()
    frames = read_rx(jsonl)
    cap.send_signal(signal.SIGTERM)
    try:
        cap.wait(timeout=20)
    except subprocess.TimeoutExpired:
        cap.kill()

    analysis = analyse(frames, t0, t1)
    analysis.update({
        "button": args.button, "expect_id": args.expect_id,
        "window": {"start": t0.isoformat(), "end": t1.isoformat()},
        "operator_response": ack.get("response"), "operator_status": ack.get("status"),
        "operator_clicked_at": ack.get("clicked_at"),
        "capture_backend": "armorx_real.py --phase d2 (proven path)",
        "harness_extra_args": extra, "ts": time.time(),
    })
    with (LAB / "results" / "runtime" / "button-tests.jsonl").open("a") as f:
        f.write(json.dumps(analysis) + "\n")
    (outdir / f"{args.button.lower()}.json").write_text(json.dumps(analysis, indent=1) + "\n")

    print(json.dumps({k: analysis[k] for k in
                      ("button", "verdict", "rule", "key_id", "expect_id", "operator_response",
                       "status_frames", "frames_in_window", "analog_lt_values",
                       "analog_rt_values")}, indent=1))
    if ack.get("status") == "CANCEL":
        return 1
    return 0 if analysis["verdict"] == "PROVEN LIVE" else 4


if __name__ == "__main__":
    raise SystemExit(main())
