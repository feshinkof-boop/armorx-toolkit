#!/usr/bin/env python3
"""request_physical_action.py -- ask the operator for ONE physical action and WAIT
for the GUI click.

The click is the acknowledgement channel; Hermes chat is not. This command:

  1. refuses if an ack for this ACTION_ID is already pending (one action at a time),
  2. launches the one-shot Qt dialog inside the LIVE Plasma session
     (via automation/run-in-plasma-session.sh, so DISPLAY/WAYLAND_DISPLAY/DBUS are
     the interactive desktop's, not this shell's),
  3. blocks until the ack JSON appears or --timeout expires,
  4. prints the ack as machine-readable JSON.

Exit codes:  0 ACK / 1 OPERATOR_CANCELLED / 2 TIMEOUT / 3 usage error.

Example:
  request_physical_action.py --id press_capture --title "ARMOR-X BUTTON TEST - CAPTURE" \
    --message "Press CAPTURE twice, then click DONE." \
    --button "DONE - PRESSED TWICE=done" --button "RETRY=retry" --button "STOP TESTING=cancel"
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

LAB_ROOT = pathlib.Path(os.environ.get("LAB_ROOT", "/home/salamanka/armorx-lab"))
ACK_DIR = LAB_ROOT / "results" / "runtime" / "operator-actions"
VENV_PY = LAB_ROOT / ".venv-operator-ui" / "bin" / "python"
GUI = LAB_ROOT / "automation" / "operator_action_gui.py"
RUN_IN_PLASMA = LAB_ROOT / "automation" / "run-in-plasma-session.sh"
EVENT_LOG = LAB_ROOT / "results" / "runtime" / "operator-actions.jsonl"


def record(event: dict) -> None:
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a") as f:
        f.write(json.dumps(event) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="one-shot operator action with GUI-click ack")
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", default="ARMOR-X ACTION REQUIRED")
    ap.add_argument("--message", required=True)
    ap.add_argument("--status", default="")
    ap.add_argument("--button", action="append", default=[], metavar="LABEL=value")
    ap.add_argument("--timeout", type=float, default=1800.0,
                    help="seconds to wait for the click (default 1800)")
    ap.add_argument("--no-wait", action="store_true", help="launch and return immediately")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--print-launch", action="store_true")
    args = ap.parse_args()

    ack_path = ACK_DIR / f"{args.id}.json"
    if ack_path.exists():
        print(f"refusing: an acknowledgement for {args.id} already exists "
              f"({ack_path}); one action at a time", file=sys.stderr)
        return 3
    if not VENV_PY.exists():
        print(f"refusing: {VENV_PY} missing (create the operator UI venv first)", file=sys.stderr)
        return 3

    gui_argv = [str(VENV_PY), str(GUI), "--id", args.id, "--title", args.title,
                "--message", args.message]
    if args.status:
        gui_argv += ["--status", args.status]
    for spec in (args.button or ["DONE=done"]):
        gui_argv += ["--button", spec]
    if args.no_sound:
        gui_argv += ["--no-sound"]

    # launch inside the interactive Plasma session, detached from this shell
    launch_argv = ["bash", str(RUN_IN_PLASMA), *gui_argv]
    if args.print_launch:
        print("launch: " + " ".join(gui_argv))
    proc = subprocess.Popen(launch_argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True)
    requested_at = subprocess.run(["date", "-Is"], capture_output=True, text=True).stdout.strip()
    record({"action_id": args.id, "event": "requested", "requested_at": requested_at,
            "title": args.title, "message": args.message, "buttons": args.button,
            "gui_pid": proc.pid})
    if args.no_wait:
        print(json.dumps({"status": "LAUNCHED", "action_id": args.id, "gui_pid": proc.pid}))
        return 0

    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        if ack_path.exists():
            try:
                doc = json.loads(ack_path.read_text())
            except json.JSONDecodeError:
                time.sleep(0.2)
                continue
            record({"action_id": args.id, "event": "acknowledged",
                    "acknowledged_at": doc.get("clicked_at"), "response": doc.get("response"),
                    "status": doc.get("status"), "gui_pid": doc.get("pid")})
            print(json.dumps(doc, indent=1))
            return 0 if doc.get("status") == "ACK" else 1
        time.sleep(0.25)

    record({"action_id": args.id, "event": "timeout", "timeout_s": args.timeout})
    print(json.dumps({"status": "TIMEOUT", "action_id": args.id,
                      "waited_s": args.timeout}, indent=1))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
