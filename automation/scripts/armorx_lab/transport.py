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
    """Real central built on Bumble, driven synchronously.

    The BLE stack is asyncio; this class runs one event loop in a daemon thread and exposes the
    blocking contract the harness (`write` / `read`) already assumes, so no harness code changes
    when hardware arrives.

    Verified on the real ARMOR-X Pro (2026-09-27): the lab adapter is resolved by USB path + BDADDR
    (never by hci index), Bumble owns the kernel HCI socket (`hci-socket:<index>`), and the target is
    found by the advertised name prefix unless an address is given.
    """

    def __init__(self, transport: str = "hci-socket:1", address: Optional[str] = None,
                 service: str = "00000000-0000-1000-8000-00805f9b34fb",
                 write_char: str = "0000ffe1-0000-1000-8000-00805f9b34fb",
                 notify_char: str = "0000ffe2-0000-1000-8000-00805f9b34fb",
                 device_name_prefix: str = "ARMOR-X Pro_",
                 scan_timeout: float = 15.0, local_address: str = "F0:0A:A5:00:00:09") -> None:
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
        self.local_address = local_address
        self._inbox: "queue.Queue[bytes]" = queue.Queue()
        self._device = None
        self._peer = None
        self._connected = False
        self._loop = None
        self._thread = None
        self._transport_ctx = None
        self._chars: dict = {}
        self.events: list = []

    # -- internals --------------------------------------------------------------
    def _run(self, coro, timeout: float = 60.0):
        import asyncio
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result(timeout)

    def device_present(self) -> bool:
        return self._connected

    async def _aconnect(self) -> None:
        import asyncio as _a

        from bumble.core import AdvertisingData
        from bumble.device import Device, Peer
        from bumble.transport import open_transport

        def adv_name(adv) -> str:
            for ad_type in (AdvertisingData.COMPLETE_LOCAL_NAME,
                            AdvertisingData.SHORTENED_LOCAL_NAME):
                value = adv.data.get(ad_type, raw=True)
                if value:
                    return bytes(value).decode("utf-8", "replace")
            return ""

        self._transport_ctx = await open_transport(self.transport_spec)
        hci_source, hci_sink = await self._transport_ctx.__aenter__()
        device = Device.with_hci("armorx-harness", self.local_address, hci_source, hci_sink)
        await device.power_on()
        self._device = device
        found: dict = {}

        def on_adv(adv):
            name = adv_name(adv)
            if name and name.startswith(self.device_name_prefix):
                found[str(adv.address)] = name

        device.on(Device.EVENT_ADVERTISEMENT, on_adv)
        await device.start_scanning()
        deadline = self._loop.time() + self.scan_timeout
        while self._loop.time() < deadline and not found:
            await _a.sleep(0.25)
        await device.stop_scanning()
        target = self.address or (next(iter(found)) if found else None)
        if not target:
            raise RuntimeError("no device advertising prefix %r within %.1fs"
                               % (self.device_name_prefix, self.scan_timeout))
        connection = await device.connect(target)
        peer = Peer(connection)
        self._peer = peer
        try:
            await peer.request_mtu(247)
        except Exception:
            pass
        services = await peer.discover_services()
        for service in services:
            try:
                await peer.discover_characteristics(service=service)
            except Exception:
                continue
            for ch in service.characteristics:
                self._chars[self._norm(str(ch.uuid))] = ch

        write_ch = self._chars.get(self._norm(self.write_char))
        notify_ch = self._chars.get(self._norm(self.notify_char))
        if write_ch is None or notify_ch is None:
            raise RuntimeError("FFE1/FFE2 not found on %s (have %s)"
                               % (target, sorted(self._chars)))
        self._write_ch = write_ch
        self._notify_ch = notify_ch

        def on_notify(value):
            self._inbox.put(bytes(value))

        await notify_ch.subscribe(on_notify)
        self._connected = True
        self.events.append({"event": "connected", "address": target,
                            "att_mtu": getattr(connection, "att_mtu", None)})

    @staticmethod
    def _norm(uuid_str: str) -> str:
        text = uuid_str.lower()
        if text.startswith("uuid-16:"):
            short = text.split(":", 1)[1].strip().split(" ", 1)[0]
            return "0000%s-0000-1000-8000-00805f9b34fb" % short
        if len(text) == 4:
            return "0000%s-0000-1000-8000-00805f9b34fb" % text
        return text

    async def _awrite(self, frame: bytes) -> None:
        await self._write_ch.write_value(frame, with_response=False)
        self.events.append({"event": "tx", "raw": frame.hex()})

    async def _aread_uuid(self, uuid_short: str):
        ch = self._chars.get(self._norm(uuid_short))
        if ch is None:
            return None
        try:
            return bytes(await self._peer.gatt_client.read_value(ch))
        except Exception:
            return None

    def read_identity(self) -> dict:
        """Read the device identity characteristics raw: 2A24, 2A26, 2A19.

        Used to bind a restore/experiment to the physical unit it was captured
        from: a baseline from a different model/firmware must never be written.
        """
        out: dict = {}
        for key in ("2a24", "2a26", "2a19"):
            value = self._run(self._aread_uuid(key), timeout=20.0)
            out[key] = {
                "raw_hex": value.hex() if value else None,
                "ascii": value.decode("latin-1") if value else None,
                "length": len(value) if value else 0,
            }
        self.events.append({"event": "identity_read", **out})
        return out

    async def _aclose(self) -> None:
        try:
            if self._transport_ctx is not None:
                await self._transport_ctx.__aexit__(None, None, None)
        except Exception:
            pass
        self._connected = False

    # -- blocking contract ------------------------------------------------------
    def connect(self) -> None:
        import asyncio
        import threading
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._run(self._aconnect())

    def write(self, frame: bytes) -> None:
        self._run(self._awrite(frame), timeout=20.0)

    def read(self, timeout: float) -> Optional[bytes]:
        try:
            value = self._inbox.get(timeout=timeout)
            self.events.append({"event": "rx", "raw": value.hex()})
            return value
        except queue.Empty:
            return None

    def read_fragments(self, fragments: int, timeout: float = 3.0) -> list:
        """Collect up to *fragments* notifications, stopping early on a timeout."""
        out: list = []
        while len(out) < fragments:
            value = self.read(timeout)
            if value is None:
                break
            out.append(value)
        return out

    def close(self) -> None:
        try:
            if self._loop is not None:
                self._run(self._aclose(), timeout=15.0)
        except Exception:
            pass
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._connected = False
