"""In-memory GATT client and recorder so the real causal executor can run with no BLE stack.

`d2_runner.run_steps` takes any duck-typed client with `write_gatt_char`, `start_notify` and
`stop_notify`, and any recorder with `.frames`, `.mark()` and `.log()`. This module supplies both
against a `VirtualArmorX`, which means the exact code path used on hardware is the code path under
test - not a re-implementation of it.
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, List, Optional

from armorx_lab.frames import parse_button_frame
from armorx_lab.virtual_device import VirtualArmorX


class OfflineRecorder:
    """Records TX/RX in the same shape the live recorder uses, so verdict logic is shared."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.frames: List[dict] = []
        self.events: List[dict] = []
        self.t0 = time.monotonic()
        self._fh = open(path, "w") if path else None

    def mark(self, event: str, detail: str = "") -> float:
        t = round(time.monotonic() - self.t0, 4)
        rec = {"t": t, "event": event, "detail": detail}
        self.events.append(rec)
        self._write(rec)
        return t

    def log(self, direction: str, uuid: str, payload: bytes, **extra: Any) -> float:
        t = round(time.monotonic() - self.t0, 4)
        raw = bytes(payload)
        rec = {"t": t, "dir": direction, "uuid": uuid, "hex": raw.hex(), **extra}
        self._write(rec)
        return t

    def on_notify(self, _char: Any, data: Any) -> None:
        raw = bytes(data)
        parsed = parse_button_frame(raw)
        self.frames.append({
            "hex": raw.hex(),
            "length": len(raw),
            "kind": "valid_status" if parsed else "other",
            "mask": f"0x{parsed.mask:08X}" if parsed else None,
            "keys": parsed.keys if parsed else None,
            "t": round(time.monotonic() - self.t0, 4),
        })
        self._write({"event": "rx", "raw": raw.hex(), "kind": "valid_status" if parsed else "other"})

    def _write(self, rec: dict) -> None:
        if self._fh:
            self._fh.write(json.dumps(rec) + "\n")
            self._fh.flush()

    def close(self) -> None:
        if self._fh:
            self._fh.close()

    def summary(self) -> dict:
        valid = [f for f in self.frames if f["kind"] == "valid_status"]
        return {"rx_total": len(self.frames), "valid_status": len(valid),
                "keys": sorted({k for f in valid for k in (f["keys"] or [])})}


class MockGattClient:
    """Bleak-like client bound to a virtual device. No adapter, no discovery, no radio."""

    FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
    FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"

    def __init__(self, device: VirtualArmorX, mtu: int = 64) -> None:
        self.device = device
        self.mtu = mtu
        self.writes: List[tuple] = []
        self.subscribed = False
        self._cb: Optional[Callable] = None
        device.attach_notify(self._deliver)

    def _deliver(self, frame: bytes) -> None:
        if self._cb is not None:
            self._cb(self.FFE2, frame)

    async def start_notify(self, uuid: str, cb: Callable) -> None:
        self._cb = cb
        self.subscribed = True
        self.device.on_link_up()

    async def stop_notify(self, uuid: str) -> None:
        self._cb = None
        self.subscribed = False

    async def write_gatt_char(self, uuid: str, data: Any, response: bool = False) -> None:
        frame = bytes(data)
        self.writes.append((uuid, frame, response))
        self.device.handle_write(frame)

    async def disconnect(self) -> None:
        self.subscribed = False
        self._cb = None

    # convenience for tests / offline experiments
    def press_a_twice(self) -> None:
        self.device.press_a_twice()
