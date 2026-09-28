"""Tests for the D2 candidate-reference closure artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "d2-candidate-reference-closure.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestCandidateRefs:
    def test_all_four_reference_groups_are_present(self):
        r = art()["references"]
        assert set(r) == {"0x1e0e29c_0x1e0e2c2", "0x1e0e3c6_0x1e0e3d6", "0x1e0db90", "0x1e0cd24_0x1e0cd2e"}

    def test_second_variant_sends_the_candidate_directly(self):
        c = art()["references"]["0x1e0e29c_0x1e0e2c2"]["conclusion"]
        assert "CANDIDATE ITSELF" in c

    def test_option_b_is_refuted(self):
        assert "option B REFUTED" in art()["lt_rt_verdict"]["status"]

    def test_option_a_is_supported_but_not_overclaimed(self):
        v = art()["lt_rt_verdict"]
        assert "option A SUPPORTED" in v["status"]
        assert "PROVEN STATIC" in v["grade"] and "NOT proven" in v["grade"]

    def test_stack_decimal_trap_is_recorded(self):
        assert "DECIMAL" in art()["write_timeline"]["tool_caveat"]

    def test_usb_trio_is_not_claimed_as_done(self):
        assert art()["usb_trio"]["status"].startswith("HEAD ONLY")
