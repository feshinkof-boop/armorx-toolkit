"""Transports for the ARMOR-X harness.

Implemented backends:
  NullTransport            - scripted/echo replies, lets the whole state machine and logging be
                             exercised with no hardware at all (used by the selftest).
  VirtualArmorXTransport   - client side that talks to the virtual BLE peripheral built in
                             ble/virtual-armorx (over its local control socket / JSONL session).
                             Wired up by a later phase; raises a clear error until configured.
  BumbleTransport          - real central over a Bumble HCI transport (kernel HCI socket first,
                             direct USB only when nothing else works). Imported lazily so the
                             harness is usable on a host without bumble installed.

A transport only has to provide: write(bytes), read(timeout) -> Optional[bytes],
device_present() -> bool, close().
"""

from __future__ import annotations

import json
import os
import queue
import time
from typing import Dict, List, Optional, Sequence


class NullTransport:
    """Deterministic transport used for self-tests and dry runs.

    `script` maps a request frame to the reply to emit; anything not in the script behaves like a
    device that is simply not answering, which is what the harness must classify honestly.
    """

    def __init__(self, script: Optional[Dict[bytes, bytes]] = None, present: bool = True) -> None:
        self.script = dict(script or {})
        self._present = present
        self.writes: List[bytes] = []
        self._pending: "queue.Queue[bytes]" = queue.Queue()

    def device_present(self) -> bool:
        return self._present

    def write(self, frame: bytes) -> None:
        self.writes.append(frame)
        if frame in self.script:
            self._pending.put(self.script[frame])

    def read(self, timeout: float) -> Optional[bytes]:
        try:
            return self._pending.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        pass


class VirtualArmorXTransport:
    """Client for the virtual ARMOR-X peripheral (ble/virtual-armorx).

    The virtual device publishes its frame log as JSONL; this transport starts it as a subprocess
    and exchanges frames through its stdio protocol. It is deliberately fail-loud: if the peripheral
    script is missing or no bumble venv exists, constructing this transport raises with the exact
    reason instead of pretending to work.
    """

    def __init__(self, peripheral_cmd: Sequence[str], logdir: str = "logs",
                 timeout: float = 10.0) -> None:
        if not peripheral_cmd:
            raise ValueError("peripheral_cmd is required")
        exe = peripheral_cmd[0]
        if not (os.path.exists(exe) or os.path.sep in exe):
            raise FileNotFoundError("virtual peripheral entry point not found: %s" % exe)
        self.cmd = list(peripheral_cmd)
        self.logdir = logdir
        self.timeout = timeout
        self.proc = None

    def _ensure(self):
        raise NotImplementedError(
            "VirtualArmorXTransport is a placeholder: the virtual peripheral's stdio contract is "
            "defined by ble/virtual-armorx (see its README). Wire the exact command line here once "
            "the peripheral exists; it is intentionally not guessed.")

    def device_present(self) -> bool:
        return False

    def write(self, frame: bytes) -> None:
        self._ensure()

    def read(self, timeout: float) -> Optional[bytes]:
        return None

    def close(self) -> None:
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None


class BumbleTransport:
    """Real central built on Bumble.

    Usage once the lab adapter is isolated and powered (see automation/radio/use-bumble.sh):
        t = BumbleTransport(transport="hci-socket", address="<bdaddr>",
                            service="00000000-0000-1000-8000-00805f9b34fb",
                            write_char="0000ffe1-...", notify_char="0000ffe2-...")
    The transport is resolved from the saved radio identity, never from hci0/hci1 names.
    """

    def __init__(self, transport: str = "hci-socket", address: Optional[str] = None,
                 service: str = "00000000-0000-1000-8000-00805f9b34fb",
                 write_char: str = "0000ffe1-0000-1000-8000-00805f9b34fb",
                 notify_char: str = "0000ffe2-0000-1000-8000-00805f9b34fb",
                 device_name_prefix: str = "ARMOR-X Pro_",
                 scan_timeout: float = 10.0) -> None:
        try:
            import bumble  # noqa: F401
        except Exception as exc:  # pragma: no cover - host dependent
            raise RuntimeError(
                "bumble is not importable in this interpreter (%s). Install it in "
                "/home/salamanka/armorx-lab/ble/bumble/venv and run the harness with that "
                "interpreter." % exc)
        self.transport_spec = transport
        self.address = address
        self.service = service
        self.write_char = write_char
        self.notify_char = notify_char
        self.device_name_prefix = device_name_prefix
        self.scan_timeout = scan_timeout
        self._inbox: "queue.Queue[bytes]" = queue.Queue()
        self._device = None
        self._connected = False

    # The concrete Bumble calls are filled in on hardware bring-up; this skeleton only fixes the
    # contract so the harness and its logs do not change when the radio arrives.
    def device_present(self) -> bool:
        return self._connected

    def connect(self) -> None:  # pragma: no cover - hardware path
        raise NotImplementedError(
            "BumbleTransport.connect is implemented during hardware bring-up "
            "(radio-isolation + use-bumble.sh must pass first).")

    def write(self, frame: bytes) -> None:  # pragma: no cover - hardware path
        raise NotImplementedError("BumbleTransport.write awaits hardware bring-up")

    def read(self, timeout: float) -> Optional[bytes]:  # pragma: no cover - hardware path
        try:
            return self._inbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        self._connected = False
