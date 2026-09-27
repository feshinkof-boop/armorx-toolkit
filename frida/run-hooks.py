#!/usr/bin/env python3
"""
armorx-lab :: Frida capture driver
-----------------------------------
Spawns (or attaches to) a target package, loads the shared platform hooks plus a
per-version entry script, and records every message the scripts emit to a JSONL
trace file under frida/traces/<version>/.

Usage:
    .venv-frida/bin/python frida/run-hooks.py \
        --version 2.23 \
        --package com.moojiang.bigbigwon \
        --seconds 45 \
        [--attach] [--device emulator-5554] [--with-net]

This exists so captures are reproducible and machine-readable; the plain
interactive command is documented in frida/hooks/README.md.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime

import frida

LAB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(LAB, "frida", "hooks")

VERSION_PKG = {
    "2.23": "com.moojiang.bigbigwon",
    "2.24": "com.moojiang.bigbigwon",
    "4.0.8": "com.moojiang.bigbigwon.mygt",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, choices=list(VERSION_PKG))
    ap.add_argument("--package", default=None)
    ap.add_argument("--seconds", type=int, default=45)
    ap.add_argument("--attach", action="store_true", help="attach instead of spawn")
    ap.add_argument("--device", default=None, help="device id, e.g. emulator-5554")
    ap.add_argument("--with-net", action="store_true", help="also load network hooks")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    pkg = args.package or VERSION_PKG[args.version]
    entry = os.path.join(HOOKS, args.version, f"entry-{args.version}.js")

    outdir = os.path.join(LAB, "frida", "traces", args.version)
    os.makedirs(outdir, exist_ok=True)
    out = args.out or os.path.join(
        outdir, f"trace-{args.version}-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    )

    dev = frida.get_device(args.device) if args.device else frida.get_usb_device(timeout=10)

    sources = []
    if args.with_net:
        sources.append(os.path.join(HOOKS, "shared", "network-http-hooks.js"))
    sources.append(os.path.join(HOOKS, "shared", "bt-platform-hooks.js"))
    sources.append(os.path.join(HOOKS, "shared", "flutter-plugin-probe.js"))
    sources.append(entry)

    script_src = "\n;\n".join(open(s, "r", encoding="utf-8").read() for s in sources)

    mode = "attach" if args.attach else "spawn"
    print(f"[driver] device={dev.id} mode={mode} pkg={pkg}")
    print(f"[driver] scripts: {[os.path.relpath(s, LAB) for s in sources]}")
    print(f"[driver] trace -> {out}")

    if args.attach:
        session = dev.attach(pkg)
        pid = None
    else:
        pid = dev.spawn([pkg])
        session = dev.attach(pid)
    print(f"[driver] attached (pid={pid})")

    n = {"bt": 0, "net": 0, "other": 0}
    fh = open(out, "w", encoding="utf-8")

    def on_message(message, data):
        rec = {"message": message}
        kind = message.get("payload", {}).get("kind") if isinstance(message, dict) else None
        if kind == "armorx-bt":
            n["bt"] += 1
        elif kind == "armorx-net":
            n["net"] += 1
        else:
            n["other"] += 1
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        t = message.get("type")
        if t == "send":
            print("[msg]", json.dumps(message["payload"]))
        elif t == "error":
            print("[error]", message.get("description"))
            print(message.get("stack", ""))

    script = session.create_script(script_src)
    script.on("message", on_message)
    script.load()

    if not args.attach and pid is not None:
        dev.resume(pid)
        print("[driver] resumed target")

    print(f"[driver] capturing {args.seconds}s ...")
    try:
        time.sleep(args.seconds)
    except KeyboardInterrupt:
        pass

    fh.close()
    print(f"[driver] done: bt={n['bt']} net={n['net']} other={n['other']} -> {out}")

    # leave the app running only if attached; spawned apps keep running
    return 0


if __name__ == "__main__":
    sys.exit(main())
