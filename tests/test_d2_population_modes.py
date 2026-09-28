"""Tests for the D2 population-mode artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "d2-population-modes.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestPopulationModes:
    def test_r13_origin_is_the_stack_slot(self):
        r = art()["r13"]
        assert "0x1e0baa0" in r["assignment_before_the_copy"]
        assert "sp+24" in r["assignment_before_the_copy"]

    def test_copy_is_gated(self):
        assert "0x1e0cd1e" in art()["r13"]["linked_branch"]

    def test_no_precedence_is_claimed(self):
        c = art()["cfg_answer"]
        assert c["precedence"].startswith("UNDETERMINED")
        assert "NOT a proven" in c["verdict"]

    def test_f6_evidence_recorded_without_time_unit(self):
        f = art()["side_findings"]["F6_emission_found"]
        assert "0x00 or 0x01" in f["conclusion"]
        assert "No time unit is claimed" in f["conclusion"]

    def test_lt_rt_consumer_recorded(self):
        assert "0x1e0a114" in art()["side_findings"]["candidate_LT_RT_consumer"]
