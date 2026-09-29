"""Regression tests built from real live captures of physical actions.

Every report in tests/fixtures/live-interactive-2026-09-29.json was recorded on
2026-09-29 from a real ARMOR-X Pro attached by USB, with one physical action per
capture: button A, M1, M2, a left-trigger sweep and a right-trigger sweep. The
evdev record taken at the same time agreed with the wire value for every control.
"""
import json
import pathlib

import pytest

from armorx import gip

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "live-interactive-2026-09-29.json"
REPORTS = json.loads(FIXTURE.read_text())["reports"]


def decode(name):
    return gip.parse_gip_input(bytes.fromhex(REPORTS[name])).to_dict()


def test_idle_report_has_no_control_active():
    d = decode("idle")
    assert d["length"] == 48 and d["form"] == "steady"
    assert d["buttons"]["A"] is False
    assert d["buttons"]["M1"] is False
    assert d["buttons"]["M2"] is False
    assert d["triggers"]["LT"] == 0 and d["triggers"]["RT"] == 0


@pytest.mark.parametrize("name,bit", [("button_a", "A"), ("button_m1", "M1"), ("button_m2", "M2")])
def test_pressed_buttons_match_the_wire_bit(name, bit):
    d = decode(name)
    assert d["buttons"][bit] is True
    for other in ("A", "M1", "M2"):
        if other != bit:
            assert d["buttons"][other] is False


def test_button_a_is_byte4_bit_0x10_and_m1_bit_0x20_and_m2_is_byte5_bit_0x40():
    a = bytes.fromhex(REPORTS["button_a"])
    m1 = bytes.fromhex(REPORTS["button_m1"])
    m2 = bytes.fromhex(REPORTS["button_m2"])
    assert a[4] & 0x10 and not a[4] & 0x20 and not a[5] & 0x40
    assert m1[4] & 0x20 and not m1[5] & 0x40
    assert m2[5] & 0x40 and not m2[4] & 0x10 and not m2[4] & 0x20


def test_trigger_values_are_the_live_wire_values():
    assert decode("lt_680")["triggers"]["LT"] == 680
    assert decode("rt_828")["triggers"]["RT"] == 828
    assert decode("lt_680")["triggers"]["RT"] == 0
    assert decode("rt_828")["triggers"]["LT"] == 0


def test_trigger_sweep_is_coarsely_quantised_on_the_wire():
    """A two second physical pull produced only three rising samples in ~20 ms."""
    assert decode("lt_680")["buttons"]["A"] is False
    assert decode("rt_828")["buttons"]["M1"] is False


def test_sticks_are_reported_raw_and_the_signedness_is_not_claimed():
    d = decode("idle")
    sticks = d["sticks"]
    assert len(sticks["left"]) == 2 and len(sticks["right"]) == 2
    assert len(sticks["left_s16"]) == 2 and len(sticks["right_s16"]) == 2
    for raw, signed in zip(sticks["left"], sticks["left_s16"]):
        assert raw - 0x10000 == signed if raw >= 0x8000 else raw == signed
    assert "Neither the signedness" in sticks["note"]
    assert "not as an axis position" in sticks["note"]


def test_unknown_spans_are_still_reported_for_live_reports():
    d = decode("idle")
    assert d["counters"] is not None and len(d["counters"]) == 2
