"""Tests for the normalized-producer artifacts (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "normalized-producers-ab.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestProducers:
    def test_neither_producer_writes_lt_or_rt(self):
        a, b = art()["producer_A"], art()["producer_B"]
        for p in (a, b):
            assert p["fields_NOT_written"].startswith("LT (+0x0c) and RT (+0x0d)")
            assert all("r1 + 0x4" in w["code"] or "r1 + 0x6" in w["code"] or "r1 + 0x8" in w["code"]
                       or "r1 + 0xa" in w["code"] or "goto" in w["code"] or "call" in w["code"]
                       for w in p["writes"])

    def test_selectors_are_mode_ids_not_device_ids(self):
        assert "r0 & 0xf" in art()["producer_A"]["selector"]
        assert "HIGH nibble" in art()["producer_B"]["selector"]

    def test_synthetic_value_set_is_recorded(self):
        vs = art()["producer_A"]["value_set"]
        assert "0x8000" in vs and "0x7fff" in vs and "0x2582" in vs

    def test_mux_misreading_is_corrected(self):
        c = art()["answers_to_the_brief"]["architectural_conclusion"]
        assert "misreading" in c and "SYNTHETIC" in c

    def test_rt_is_not_declared_solved_or_flipped(self):
        assert art()["rt_status"]["status"].startswith("OPEN")
        assert "NOT proven" in art()["rt_status"]["implication"]
