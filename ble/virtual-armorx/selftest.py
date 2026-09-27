#!/usr/bin/env python3
"""End-to-end selftest for the virtual ARMOR-X Pro peripheral.

Runs *two* Bumble processes over a purely virtual transport:

  1. `virtual_armorx.py` -- the peripheral, advertising on
     tcp-server:127.0.0.1:<port>;
  2. `armorx_central_client.py` -- a Bumble central that scans for the
     'ARMOR-X Pro_' name prefix, connects, and exchanges the evidence-backed
     frames.

No physical Bluetooth adapter is touched: the transport is a local TCP socket
between the two processes, and the peripheral's own radio is a Bumble virtual
Controller on an in-process LocalLink.

Exit code 0 iff the client passes every expectation and the peripheral's logs
contain the expected evidence-backed / UNKNOWN events.
"""

from __future__ import annotations

import argparse
import json
import queue
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_LOG_ROOT = HERE / "logs"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LineReader(threading.Thread):
    """Read a subprocess' stdout line-by-line into a queue."""

    def __init__(self, stream, sink: queue.Queue):
        super().__init__(daemon=True)
        self.stream = stream
        self.sink = sink

    def run(self) -> None:
        for line in self.stream:
            self.sink.put(line.rstrip("\n"))


def wait_for_advertising(proc, lines: queue.Queue, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            line = lines.get(timeout=0.2)
        except queue.Empty:
            continue
        print(f"  [peripheral] {line}")
        if "advertising as" in line:
            return True
    return False


def load_jsonl(path: Path) -> list[dict]:
    events = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return events


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="interpreter for both processes")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--log-root", default=str(DEFAULT_LOG_ROOT))
    parser.add_argument("--keep-logs", action="store_true", default=True)
    args = parser.parse_args(argv)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_dir = Path(args.log_root) / f"selftest-{stamp}"
    log_dir.mkdir(parents=True, exist_ok=True)
    port = free_port()
    sock_path = f"/tmp/armorx_selftest_{port}.sock"

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)

    print(f"=== selftest: logs in {log_dir}, port {port} ===", flush=True)

    periph_cmd = [
        args.python,
        str(HERE / "virtual_armorx.py"),
        "--transport",
        f"tcp-server:127.0.0.1:{port}",
        "--local-transport",
        sock_path,
        "--session-id",
        "selftest-peripheral",
        "--log-dir",
        str(log_dir),
    ]
    periph = subprocess.Popen(
        periph_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    lines: queue.Queue = queue.Queue()
    LineReader(periph.stdout, lines).start()

    client_ok = False
    try:
        if not wait_for_advertising(periph, lines, timeout=min(args.timeout, 30.0)):
            check("peripheral_started", False, "peripheral never reported advertising")
            return 1
        check("peripheral_started", True, f"tcp-server:127.0.0.1:{port}")

        client_cmd = [
            args.python,
            str(HERE / "armorx_central_client.py"),
            "--transport",
            f"tcp-client:127.0.0.1:{port}",
            "--session-id",
            "selftest-client",
            "--log-dir",
            str(log_dir),
        ]
        print("=== running central client ===", flush=True)
        client = subprocess.run(
            client_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=args.timeout,
        )
        print(client.stdout, flush=True)
        client_ok = client.returncode == 0
        check("central_client_exit_0", client_ok, f"returncode={client.returncode}")
    finally:
        # Give the peripheral a moment to flush logs, then stop it.
        time.sleep(0.5)
        periph.terminate()
        try:
            periph.wait(timeout=10)
        except subprocess.TimeoutExpired:
            periph.kill()
        # drain any remaining peripheral output
        while True:
            try:
                print(f"  [peripheral] {lines.get_nowait()}")
            except queue.Empty:
                break

    # --- verify the peripheral's structured log ---------------------------
    periph_jsonl = log_dir / "selftest-peripheral.jsonl"
    events = load_jsonl(periph_jsonl)
    kinds = [event["event"] for event in events]
    check("peripheral_jsonl_written", periph_jsonl.is_file() and len(events) > 0,
          f"{len(events)} events")

    def count(event_name: str) -> int:
        return kinds.count(event_name)

    check("logged_connect", count("connect") >= 1, f"{count('connect')} connect events")
    check("logged_gatt_writes", count("frame_in") >= 4, f"{count('frame_in')} inbound frames")
    check(
        "logged_config_read_10_fragments",
        sum(1 for e in events if e["event"] == "reply_out" and e.get("tag") == "config_read") >= 10,
        "config read fragments notified",
    )
    check(
        "logged_d7_config_write",
        any(e["event"] == "config_write" and e.get("crc_valid") for e in events),
        "config write accepted with valid CRC",
    )
    unknown = [e for e in events if e["event"] == "command_unknown"]
    unknown_opcodes = sorted(
        code for code in {e.get("parsed_opcode") for e in unknown} if code
    )
    check(
        "logged_unknown_e4_e2",
        {e.get("parsed_opcode") for e in unknown} >= {"0xE4", "0xE2"},
        f"UNKNOWN opcodes logged: {unknown_opcodes}",
    )
    check(
        "unknown_sent_no_bytes",
        all(e.get("reply_bytes_sent") == 0 for e in unknown),
        "every UNKNOWN command logged with reply_bytes_sent=0",
    )
    check(
        "checksum_pass_rate",
        all(e.get("checksum_ok") for e in events if e["event"] == "frame_in"),
        "all parsed inbound frames had a valid checksum",
    )

    # --- raw capture artefacts -------------------------------------------
    bin_path = log_dir / "selftest-peripheral.bin"
    hex_path = log_dir / "selftest-peripheral.hex"
    check("raw_capture_bin", bin_path.is_file() and bin_path.stat().st_size > 0,
          f"{bin_path.stat().st_size if bin_path.is_file() else 0} bytes")
    check("raw_capture_hex", hex_path.is_file() and hex_path.stat().st_size > 0,
          f"{hex_path.stat().st_size if hex_path.is_file() else 0} bytes")

    print("", flush=True)
    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"=== selftest summary: {passed}/{len(checks)} checks passed ===", flush=True)
    print(f"=== logs: {log_dir} ===", flush=True)
    return 0 if passed == len(checks) and client_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
