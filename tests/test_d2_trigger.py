"""Tests for the D2 trigger-path artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "d2-trigger-path.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestD2Trigger:
    def test_change_decision_is_the_memcmp(self):
        step = next(s for s in art()["trigger_path"] if s["addr"] == "0x1e0dad2")
        e = " ".join(step["evidence"])
        assert "0x2f92fa" in e and "r2 = 0xe" in e
        assert "0x4ecc" in e

    def test_send_if_is_an_expression_not_a_summary(self):
        expr = art()["d2_send_if"]["expression"]
        assert "b[state+0x10] != 0" in expr and "memcmp" in expr

    def test_no_time_unit_is_invented(self):
        assert "NO time unit is claimed" in art()["d2_send_if"]["unit"]

    def test_zero_idle_is_explained_but_rt_is_not_claimed(self):
        assert "PROVEN STATIC" in art()["zero_idle_explanation"]["grade"]
        assert art()["rt_no_self_trigger"]["status"].startswith("CONTRADICTION")

    def test_state_1b4_is_a_mode_selector(self):
        s = art()["state_0x1b4_meaning"]
        assert {v["value"] for v in s["values_seen"]} == {2, 3}
        assert "not a dirty flag" in s["conclusion"]

    def test_container_correction_is_recorded(self):
        head = next(s for s in art()["trigger_path"] if s["addr"] == "0x1e0ac14")
        assert "container" in head["role"]
