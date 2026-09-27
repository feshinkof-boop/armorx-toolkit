#!/usr/bin/env python3
"""operator_action_gui.py -- the ONE-SHOT physical-action dialog.

Contract (see results/final/operator-ui-validation.md):
  * appears ONCE, stays visible until a button is clicked
  * plays ONE short sound, exactly once, never repeats, never on focus
  * the BUTTON CLICK is the acknowledgement - chat is never the channel
  * on click: atomically write results/runtime/operator-actions/<ID>.json and
    print the same object as machine-readable JSON on stdout
  * exit 0 = ACK, 1 = CANCEL/STOP (or the window was closed), 3 = usage error

Never reports success because a window existed, a sound played or a shell
returned 0: the JSON is only written from the button's clicked handler.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

LAB_ROOT = pathlib.Path(os.environ.get("LAB_ROOT", "/home/salamanka/armorx-lab"))
ACK_DIR = LAB_ROOT / "results" / "runtime" / "operator-actions"
DEFAULT_SOUND = LAB_ROOT / "automation" / "armorx-alert.wav"
LOG = LAB_ROOT / "logs" / "operator-gui.log"

CANCEL_VALUES = {"cancel", "stop", "abort", "operator_cancelled", "cancelled"}


def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as f:
            f.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except OSError:
        pass


def play_once(wav: pathlib.Path) -> str:
    """Play the alert sound ONE time. Returns the backend used (for the record)."""
    for backend, argv in (
        ("pw-play", ["pw-play", str(wav)]),
        ("paplay", ["paplay", str(wav)]),
        ("canberra-gtk-play", ["canberra-gtk-play", "-f", str(wav)]),
        ("aplay", ["aplay", "-q", str(wav)]),
    ):
        if shutil.which(backend):
            try:
                subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return backend
            except OSError:
                continue
    return "none"


def write_ack(path: pathlib.Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-ack-")
    with os.fdopen(fd, "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)          # atomic: readers never see a partial file


def main() -> int:
    ap = argparse.ArgumentParser(description="one-shot ARMOR-X operator action dialog")
    ap.add_argument("--id", required=True, help="ACTION_ID, also the ack file name")
    ap.add_argument("--title", default="ARMOR-X ACTION REQUIRED")
    ap.add_argument("--message", required=True)
    ap.add_argument("--status", default="", help="optional status block shown under the message")
    ap.add_argument("--button", action="append", default=[],
                    metavar="LABEL=value", help="repeatable; first is the primary action")
    ap.add_argument("--sound", default=str(DEFAULT_SOUND))
    ap.add_argument("--sound-loop", action="store_true",
                    help="NOT SUPPORTED any more - the retired alert looped; kept to fail loudly")
    ap.add_argument("--qt-platform", default=os.environ.get("QT_QPA_PLATFORM", ""))
    ap.add_argument("--no-sound", action="store_true")
    args = ap.parse_args()

    if args.sound_loop:
        print("refusing: --sound-loop was retired with the old alert design "
              "(one popup, one sound, click to acknowledge)", file=sys.stderr)
        return 3
    buttons = []
    for spec in args.button:
        if "=" not in spec:
            print(f"refusing: --button {spec!r} must be LABEL=value", file=sys.stderr)
            return 3
        label, value = spec.split("=", 1)
        buttons.append((label.strip(), value.strip()))
    if not buttons:
        buttons = [("DONE", "done")]

    if args.qt_platform:
        os.environ["QT_QPA_PLATFORM"] = args.qt_platform

    from PySide6 import QtCore, QtWidgets

    ack_path = ACK_DIR / f"{args.id}.json"
    # any stale ack for this id must never be mistaken for a fresh click
    ack_path.unlink(missing_ok=True)
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName("armorx-operator-action")

    win = QtWidgets.QWidget()
    win.setWindowTitle(args.title)
    win.setWindowFlags(win.windowFlags()
                       | QtCore.Qt.WindowType.WindowStaysOnTopHint
                       | QtCore.Qt.WindowType.Window)
    win.setMinimumWidth(620)
    lay = QtWidgets.QVBoxLayout(win)

    head = QtWidgets.QLabel(args.title)
    head.setStyleSheet("font-size:20px;font-weight:700;")
    lay.addWidget(head)

    body = QtWidgets.QLabel(args.message)
    body.setWordWrap(True)
    body.setStyleSheet("font-size:15px;")
    lay.addWidget(body)

    if args.status:
        st = QtWidgets.QLabel(args.status)
        st.setWordWrap(True)
        st.setStyleSheet("font-size:12px;color:#888;")
        lay.addWidget(st)

    row = QtWidgets.QHBoxLayout()
    for i, (label, value) in enumerate(buttons):
        btn = QtWidgets.QPushButton(label)
        btn.setMinimumHeight(46)
        if i == 0:
            btn.setStyleSheet("font-size:16px;font-weight:600;")
        else:
            btn.setStyleSheet("font-size:14px;")
        btn.setDefault(i == 0)
        btn.setAutoDefault(i == 0)
        row.addWidget(btn)

    def make_handler(value: str):
        def handler() -> None:
            doc = {
                "status": "CANCEL" if value.lower() in CANCEL_VALUES else "ACK",
                "action_id": args.id,
                "response": value,
                "clicked_at": dt.datetime.now().astimezone().isoformat(),
                "pid": os.getpid(),
                "title": args.title,
                "gui": "PySide6",
            }
            write_ack(ack_path, doc)
            print(json.dumps(doc), flush=True)
            log(f"clicked action={args.id} response={value} status={doc['status']}")
            app.exit(1 if doc["status"] == "CANCEL" else 0)
        return handler

    for i, (label, value) in enumerate(buttons):
        row.itemAt(i).widget().clicked.connect(make_handler(value))
    lay.addLayout(row)

    def on_close() -> None:
        # closing the window is a cancel, never an ACK
        doc = {"status": "CANCEL", "action_id": args.id, "response": "window_closed",
               "clicked_at": dt.datetime.now().astimezone().isoformat(), "pid": os.getpid(),
               "title": args.title, "gui": "PySide6"}
        write_ack(ack_path, doc)
        print(json.dumps(doc), flush=True)
        log(f"window closed action={args.id}")
        app.exit(1)

    win.closeEvent = lambda event: (on_close(), event.accept())

    backend = "none" if args.no_sound else play_once(pathlib.Path(args.sound))
    log(f"shown action={args.id} sound={backend} platform={os.environ.get('QT_QPA_PLATFORM', 'auto')}")

    win.show()
    win.raise_()
    win.activateWindow()          # a single raise; not a focus-stealing loop
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
