"""Authoritative C0 / C1 / C2 D2 case definitions (declarative, no hardware access).

Why this module exists
----------------------
The 2026-09-27 official-session capture proved that the official 4.0.8 app sends a device-info and
full-configuration read burst (EF, 0B, E2, D4, D6) before enabling D2, and that it does NOT pre-clear
D2 the way our harness has been doing. Three candidate causes therefore remain for our harness's
silence during D2:

    1. the harness's D2 OFF pre-clear (the app never does this);
    2. the missing EF / 0B / E2 / D4 / full-D6-read sequence;
    3. connection/session parameter differences (official 11.25 ms vs harness 7.50 ms).

C0 isolates (nothing changed), C1 removes the pre-clear, C2 removes the pre-clear and adds the
official read burst. One variable at a time.

CRITICAL semantic rule (2026-09-27 correction)
----------------------------------------------
D2 input is EVENT-DRIVEN. The official app produced ZERO valid A5 12 02 frames while nothing was
pressed and 155 while A was pressed. Therefore:

    zero idle frames is NORMAL, not failure.

The success criterion for these cases is a button frame received DURING a real physical press,
ideally PRESS/RELEASE/PRESS/RELEASE for an A-twice action. Case definitions and their tests must
never treat an empty observation window as a failure signal.

Frames are built by armorx_lab.frames (checksums computed, never hard-coded).
"""

from __future__ import annotations

import copy
from typing import Dict, List

from armorx_lab.frames import build_short

# The five pre-D2 requests observed from the official app, in wire order.
EF_QUERY = build_short(0xEF, bytes(8))   # A5 0C EF 00 00 00 00 00 00 00 00 A0
GET_VERSION = build_short(0x0B)          # A5 04 0B B4
E2_QUERY = build_short(0xE2)             # A5 04 E2 8B
D4_QUERY = build_short(0xD4)             # A5 04 D4 7D
D6_QUERY = build_short(0xD6)             # A5 04 D6 7F

D2_ON = build_short(0xD2, b"\x01")       # A5 05 D2 01 7D
D2_OFF = build_short(0xD2, b"\x00")      # A5 05 D2 00 7C

# How long to wait for the eight 20-byte D6 reply fragments before proceeding. The official session
# answered all eight within ~400 ms; 4 s is a generous ceiling that does not change the connection.
D6_READ_WAIT_S = 4.0


def _write(frame: bytes, label: str) -> Dict[str, object]:
    return {"op": "write", "frame": frame.hex(), "label": label, "response": False}


def _sleep(seconds: float, why: str) -> Dict[str, object]:
    return {"op": "sleep", "seconds": seconds, "why": why}


def _cccd_renew() -> Dict[str, object]:
    return {"op": "cccd_renew"}


A_TWICE_MESSAGE = """Press the A button TWICE.

Do not press any other controller button.

After the second press, click DONE."""


def _a_twice_prompt(case: str) -> Dict[str, object]:
    """The one and only operator interaction for a causal case.

    Contract (unchanged since the operator UI was validated):
      ONE popup, ONE sound, ONE requested physical action, the popup persists until clicked, and the
      popup BUTTON CLICK is the acknowledgement channel - never chat.
    """
    return {"op": "operator_prompt",
            "action_id": f"armorx_d2_causal_{case.lower()}_a_twice",
            "title": "ArmorX D2 Causal Test",
            "message": A_TWICE_MESSAGE,
            "button": "DONE",
            "cancel_button": "CANCEL"}


def _observe() -> Dict[str, object]:
    return {"op": "observe", "seconds_env": "D2_OBSERVE_S", "default_s": 10.0}


PREFLIGHT = [
    {"op": "sanity", "frame": GET_VERSION.hex(), "why": "prove the control channel answers before changing D2"},
]

# The official pre-D2 burst, exactly as captured (order matters: it is the observed order).
OFFICIAL_READ_BURST = [
    _write(EF_QUERY, "EF query (official pre-D2, PROVEN LIVE 2026-09-27)"),
    _write(GET_VERSION, "0B version query (official pre-D2)"),
    _write(E2_QUERY, "E2 firmware query (official pre-D2)"),
    _write(D4_QUERY, "D4 query (official pre-D2)"),
    _write(D6_QUERY, "D6 configuration read request (official pre-D2; expect 8 x A4 14 D6 NN fragments)"),
    {"op": "wait_fragments", "prefix": "a414d6", "expect_min": 8, "seconds": D6_READ_WAIT_S},
]


def sequence(case: str) -> List[Dict[str, object]]:  # noqa: UP006
    """Return the ordered step list for a case. Pure function: no I/O, no hardware.

    Deep-copied on every call: callers may annotate or mutate the list they receive, and that must
    never be able to corrupt the authoritative definition (a unit test enforces this).
    """
    return copy.deepcopy(_sequence(case))


def _sequence(case: str) -> List[Dict[str, object]]:  # noqa: UP006
    """The definitions themselves - always go through sequence() instead of calling this."""
    if case == "C0":
        # Unchanged harness behaviour: pre-clear D2 OFF, then enable, then observe.
        return [*PREFLIGHT,  # type: ignore[list-item]
                _write(D2_OFF, "D2 disable (harness pre-clear)"),
                _sleep(1.5, "let the pre-clear settle"),
                _write(D2_ON, "D2 enable"),
                _a_twice_prompt(case),
                _observe()]
    if case == "C1":
        # Remove the pre-clear only. Everything else identical to C0.
        return [*PREFLIGHT,
                _write(D2_ON, "D2 enable (no pre-clear)"),
                _a_twice_prompt(case),
                _observe()]
    if case == "C2":
        # No pre-clear, plus the full official read burst before enabling D2.
        return [*PREFLIGHT,
                *OFFICIAL_READ_BURST,
                _write(D2_ON, "D2 enable (after official read burst, no pre-clear)"),
                _a_twice_prompt(case),
                _observe()]
    raise ValueError(f"unknown case {case!r}")


CASES: Dict[str, Dict[str, object]] = {
    "C0": {"description": "harness baseline: 0B -> D2 OFF -> D2 ON -> observe",
           "isolates": "nothing (control)",
           "pre_clear": True, "read_burst": False},
    "C1": {"description": "0B -> D2 ON (no pre-clear) -> observe",
           "isolates": "the D2 OFF pre-clear",
           "pre_clear": False, "read_burst": False},
    "C2": {"description": "EF -> 0B -> E2 -> D4 -> full D6 read -> D2 ON (no pre-clear) -> observe",
           "isolates": "the official device-info + configuration read burst",
           "pre_clear": False, "read_burst": True},
}

# Success criteria, in the corrected event-driven vocabulary.
SUCCESS_CRITERIA = {
    "minimum": "one or more valid 18-byte A5 12 02 frames received while the operator holds/changes a key",
    "strong": "PRESS, RELEASE, PRESS, RELEASE for an A-twice action (key id 0)",
    "zero_idle_frames": "NORMAL - the stream is event-driven; it is not a failure",
    "physical_action_required": True,
    "operator_prompt": "exactly one popup, one sound, one physical action, click = ACK; never chat",
}


def truth_table() -> Dict[str, Dict[str, bool]]:
    """Small helper for tests/CLI: which features each case turns on."""
    return {c: {"pre_clear": bool(v["pre_clear"]), "read_burst": bool(v["read_burst"])}
            for c, v in CASES.items()}


def _selfcheck() -> None:
    assert EF_QUERY.hex() == "a50cef0000000000000000a0"
    assert GET_VERSION.hex() == "a5040bb4"
    assert E2_QUERY.hex() == "a504e28b"
    assert D4_QUERY.hex() == "a504d47d"
    assert D6_QUERY.hex() == "a504d67f"
    assert D2_ON.hex() == "a505d2017d"
    assert D2_OFF.hex() == "a505d2007c"
    for c in CASES:
        seq = sequence(c)
        assert seq and seq[-1]["op"] == "observe"
        writes = [s for s in seq if s["op"] == "write"]
        assert writes[-1]["frame"] == D2_ON.hex(), "the last write of every case must be D2 enable"


_selfcheck()
