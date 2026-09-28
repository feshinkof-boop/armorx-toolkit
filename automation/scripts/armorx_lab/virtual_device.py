"""A virtual ARMOR-X Pro whose every byte of ground truth comes from the official capture.

Purpose: let the C0/C1/C2 causal cases be executed end to end with no adapter, no device and no
operator, so that (a) the harness plumbing is proven before it is used on hardware, and (b) the
result of tomorrow's real run is interpretable in advance - we know what each hypothesis looks like.

Every frame this device emits is taken from
`tests/vectors/official-button-test-fixtures.json`, which was extracted from the official 4.0.8
Android HCI snoop. Nothing is invented here. What IS a modelling choice is exposed as a named
hypothesis flag (`preclear_is_fatal`) rather than buried in the code.

Event-driven by construction: while nothing is pressed the device emits NOTHING, exactly as the
official app behaved (0 frames across a 61 s idle window).
"""

from __future__ import annotations

import json
import pathlib
from typing import Callable, List, Optional

FIXTURES = pathlib.Path(__file__).resolve().parents[3] / "tests/vectors/official-button-test-fixtures.json"


class VirtualArmorX:
    """Protocol-faithful ARMOR-X Pro model driven by the official fixtures."""

    def __init__(self, fixtures_path: Optional[pathlib.Path] = None, *, preclear_is_fatal: bool = False,
                 held_reports: int = 3) -> None:
        f = json.loads(pathlib.Path(fixtures_path or FIXTURES).read_text())
        self.fixtures = f
        self.preclear_is_fatal = preclear_is_fatal
        self.held_reports = held_reports

        c = f["commands"]
        # read-only query -> the reply the real device gave
        self._replies = {
            bytes.fromhex(c[k]["bytes"]): bytes.fromhex(c[k.replace("_query", "_reply")]["bytes"])
            for k in ("EF_query", "0B_query", "E2_query", "D4_query")
        }
        self.D6_QUERY = bytes.fromhex(c["D6_query"]["bytes"])
        self.D2_ENABLE = bytes.fromhex(c["D2_enable"]["bytes"])
        self.D2_DISABLE = bytes.fromhex(c["D2_disable"]["bytes"])

        self.d6_frames = [bytes.fromhex(x["bytes"]) for x in f["d6_fragments"]]
        self.d2_echoes = [bytes.fromhex(e["bytes"]) for e in f["d2_echoes"]]
        b = f["button"]
        self.press = bytes.fromhex(b["a_initial_press"]["bytes"])
        self.release = bytes.fromhex(b["a_release"]["bytes"])
        self.held = [bytes.fromhex(x["bytes"]) for x in b["a_held_frames"]] or [self.press]

        # state
        self.d2_enabled = False
        self.muted_by_preclear = False
        self.saw_d2_disable_this_link = False
        self.config_bytes = self._reassemble_config()
        self.tx: List[bytes] = []
        self.emitted: List[bytes] = []
        self._notify: Optional[Callable[[bytes], None]] = None

    # ------------------------------------------------------------------ wiring
    def attach_notify(self, cb: Callable[[bytes], None]) -> None:
        self._notify = cb

    def on_link_up(self) -> None:
        self.saw_d2_disable_this_link = False
        self.muted_by_preclear = False
        self.d2_enabled = False

    def _emit(self, frame: bytes) -> None:
        self.emitted.append(frame)
        if self._notify:
            self._notify(frame)

    def _reassemble_config(self) -> bytes:
        """Payload reassembly: byte1 is the frame length, byte3 the ordinal, last byte the checksum."""
        out = bytearray()
        for fr in self.d6_frames:
            out += fr[4:-1]
        return bytes(out)

    # ------------------------------------------------------------------ protocol
    def handle_write(self, frame: bytes) -> None:
        """Apply one host write; emit whatever notification(s) the real device emitted."""
        self.tx.append(frame)
        if frame in self._replies:
            self._emit(self._replies[frame])
            return
        if frame == self.D6_QUERY:
            for f in self.d6_frames:
                self._emit(f)
            return
        if frame == self.D2_ENABLE:
            if self.preclear_is_fatal and self.saw_d2_disable_this_link:
                self.muted_by_preclear = True      # hypothesis: the pre-clear suppresses streaming
            self.d2_enabled = True
            for e in self.d2_echoes:
                self._emit(e)
            return
        if frame == self.D2_DISABLE:
            self.d2_enabled = False
            self.muted_by_preclear = False
            self.saw_d2_disable_this_link = True
            for e in self.d2_echoes:
                self._emit(e)
            return
        # anything else: the real device ignored unknown writes in every capture we hold
        return

    # ------------------------------------------------------------------ operator
    def press_a_once(self) -> None:
        """One physical A press: press frame, held repeats, release — or nothing at all."""
        if not (self.d2_enabled and not self.muted_by_preclear):
            return
        self._emit(self.press)
        for h in self.held[: self.held_reports]:
            self._emit(h)
        self._emit(self.release)

    def press_a_twice(self) -> None:
        self.press_a_once()
        self.press_a_once()

    # ------------------------------------------------------------------ facts
    @property
    def idle_frame_count(self) -> int:
        return sum(1 for f in self.emitted if f[:3] == b"\xa5\x12\x02")

    def describe(self) -> dict:
        return {
            "d2_enabled": self.d2_enabled,
            "muted_by_preclear": self.muted_by_preclear,
            "preclear_is_fatal": self.preclear_is_fatal,
            "config_bytes": len(self.config_bytes),
            "d6_frames": len(self.d6_frames),
            "d6_frame_lengths": [len(f) for f in self.d6_frames],
            "writes": [f.hex() for f in self.tx],
            "emitted": [f.hex() for f in self.emitted],
            "button_frames_emitted": self.idle_frame_count,
        }
