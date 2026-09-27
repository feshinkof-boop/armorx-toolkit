"""Real-device session harness: state machine, JSONL state log, watchdogs, baseline capture.

Design rules taken from the project brief:
  * a session must never sit silently after the idle capture - every state transition is logged
  * the ARMOR-X has an automatic power-off timer, so link loss must be detected promptly and
    classified as DEVICE_SLEEP_OR_LINK_LOSS rather than "protocol rejected"
  * no experimental write happens before a known-good baseline is saved, hashed and CRC-verified
  * every timeout is explicit

The module is transport-agnostic: pass any object implementing the `Transport` protocol
(`armorx_lab.transport`). The NullTransport lets the state machine and logging be tested without
hardware.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from . import frames as F


class State(str, Enum):
    WAITING_FOR_DEVICE = "WAITING_FOR_DEVICE"
    DEVICE_AWAKE = "DEVICE_AWAKE"
    CAPTURING_IDLE = "CAPTURING_IDLE"
    RUNNING_EXPERIMENT = "RUNNING_EXPERIMENT"
    WAITING_FOR_REPLY = "WAITING_FOR_REPLY"
    DEVICE_SLEEP_OR_LINK_LOSS = "DEVICE_SLEEP_OR_LINK_LOSS"
    RESTORING = "RESTORING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


@dataclass
class Session:
    """One experiment session; owns the state machine, the log and the watchdogs."""

    logdir: str
    device_serial: str
    transport: object
    app_version: str = "unknown"
    notify_timeout: float = 3.0
    device_watchdog: float = 120.0        # ARMOR-X auto-off safety margin
    jsonl_path: str = field(init=False)
    raw_path: str = field(init=False)
    state: State = field(init=False, default=State.WAITING_FOR_DEVICE)
    last_seen: float = field(init=False, default=0.0)
    tx: List[bytes] = field(init=False, default_factory=list)
    rx: List[bytes] = field(init=False, default_factory=list)
    notes: List[str] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        os.makedirs(self.logdir, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        # a device identity like "ZJ-XT/2741/2D:37:35:..." must not become a path
        safe = "".join(c if (c.isalnum() or c in "-_.") else "-" for c in self.device_serial)
        base = os.path.join(self.logdir, "%s_%s" % (safe, stamp))
        self.jsonl_path = base + ".jsonl"
        self.raw_path = base + ".bin"
        self._raw = open(self.raw_path, "wb")
        self._jsonl = open(self.jsonl_path, "a", buffering=1)
        self.transition(State.WAITING_FOR_DEVICE, "session start", app_version=self.app_version)

    # ------------------------------------------------------------------ logging
    def log(self, event: str, **fields) -> None:
        rec = {"ts": time.time(), "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "device": self.device_serial, "app_version": self.app_version,
               "state": self.state.value, "event": event}
        rec.update(fields)
        self._jsonl.write(json.dumps(rec, separators=(",", ":")) + "\n")

    def transition(self, new: State, reason: str, **fields) -> None:
        old, self.state = self.state, new
        self.log("state_transition", from_state=old.value, to_state=new.value, reason=reason,
                 **fields)

    # ------------------------------------------------------------------ transport glue
    def mark_seen(self, why: str = "reply") -> None:
        self.last_seen = time.monotonic()
        if self.state is State.WAITING_FOR_DEVICE:
            self.transition(State.DEVICE_AWAKE, why)

    def check_watchdog(self) -> Optional[State]:
        """Returns the failure state if the device has been silent past the watchdog."""
        if self.last_seen and time.monotonic() - self.last_seen > self.device_watchdog:
            self.transition(State.DEVICE_SLEEP_OR_LINK_LOSS,
                            "no traffic for %.0fs (ARMOR-X auto-off or link loss)"
                            % (time.monotonic() - self.last_seen))
            return State.DEVICE_SLEEP_OR_LINK_LOSS
        return None

    def send(self, frame: bytes, expect_reply: bool = True, label: str = "") -> Optional[bytes]:
        self.tx.append(frame)
        self._raw.write(b"TX " + frame + b"\n")
        self.log("tx", label=label, hex=frame.hex(" ").upper(), expect_reply=expect_reply)
        self.transport.write(frame)
        if not expect_reply:
            return None
        self.transition(State.WAITING_FOR_REPLY, "tx %s" % (label or frame.hex(" ").upper()))
        reply = self.transport.read(self.notify_timeout)
        if reply is None:
            self.log("no_reply", label=label, timeout=self.notify_timeout)
            self.check_watchdog()
            return None
        self.rx.append(reply)
        self._raw.write(b"RX " + reply + b"\n")
        parsed = F.parse_frame(reply)
        self.mark_seen("reply")
        self.log("rx", label=label, hex=reply.hex(" ").upper(), header="0x%02X" % parsed.header,
                 opcode="0x%02X" % parsed.opcode if parsed.opcode >= 0 else None,
                 checksum_ok=parsed.checksum_ok, payload=parsed.payload.hex(" ").upper())
        return reply

    # ------------------------------------------------------------------ baseline work
    def capture_baseline(self, outdir: str) -> Dict[str, object]:
        """Read the 144-byte config with D6, save it, hash it and verify the CRC."""
        self.transition(State.CAPTURING_IDLE, "baseline read")
        reply = self.send(F.KNOWN_FRAMES["get_device_config"][0], label="get_device_config")
        if reply is None:
            self.transition(State.FAILED, "no reply to D6")
            raise RuntimeError("baseline read failed: no reply to A5 04 D6 7F")
        parsed = F.parse_frame(reply)
        image = bytes.fromhex(parsed.payload.hex()) if parsed.payload else b""
        if len(image) < 4:
            self.transition(State.FAILED, "D6 reply too short (%d bytes)" % len(image))
            raise RuntimeError("D6 reply too short: %s" % reply.hex(" "))
        os.makedirs(outdir, exist_ok=True)
        decl = F.config_length(image)
        binpath = os.path.join(outdir, "baseline_%s_%d.bin" % (self.device_serial, len(image)))
        with open(binpath, "wb") as fh:
            fh.write(image)
        ok, stored, computed = F.config_verify(image)
        meta = {
            "device_serial": self.device_serial, "app_version": self.app_version,
            "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "request": F.KNOWN_FRAMES["get_device_config"][0].hex(" ").upper(),
            "reply_hex": reply.hex(" ").upper(),
            "config_len": len(image), "declared_len": decl,
            "declared_matches": decl == len(image),
            "crc_ok": ok, "crc_stored": "0x%04X" % stored, "crc_computed": "0x%04X" % computed,
            "sha256": hashlib.sha256(image).hexdigest(),
            "mapkeys": F.mapkeys(image) if len(image) >= 32 else None,
            "file": binpath,
            "evidence": "PROVEN LIVE (this capture)",
        }
        with open(binpath.replace(".bin", ".json"), "w") as fh:
            json.dump(meta, fh, indent=1)
        self.log("baseline_saved", **{k: v for k, v in meta.items() if k != "reply_hex"})
        if not ok:
            self.notes.append("baseline CRC did not verify (stored %s vs computed %s) - do not "
                              "treat this image as a restore source until resolved"
                              % (meta["crc_stored"], meta["crc_computed"]))
            self.log("baseline_crc_mismatch", stored=meta["crc_stored"],
                     computed=meta["crc_computed"])
        return meta

    def close(self, state: State = State.COMPLETE, reason: str = "session end") -> None:
        self.transition(state, reason)
        self._raw.close()
        self._jsonl.close()

    # ------------------------------------------------------------------ convenience
    def wait_for_device(self, on_prompt: Optional[Callable[[], None]] = None,
                        timeout: float = 60.0) -> bool:
        """Poll until the transport reports the device is present/connected."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.transport.device_present():
                self.mark_seen("device present")
                return True
            if on_prompt is not None:
                on_prompt()
            time.sleep(1.0)
        self.transition(State.DEVICE_SLEEP_OR_LINK_LOSS, "device not detected within %.0fs" % timeout)
        return False
