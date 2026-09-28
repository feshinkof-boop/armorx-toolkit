"""Tests for the RT/LT writer enumeration artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "rt-writers-v41.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestRtWriters:
    def test_no_direct_writers_and_one_copy_writer(self):
        w = art()["writer_enumeration"]
        assert "ZERO direct stores" in w["result_for_0x4ed8_0x4ed9"]
        assert w["only_writer"]["addr"] == "0x1e0dadc"
        assert "0x2f92e4" in w["only_writer"]["code"]

    def test_copy_is_change_gated(self):
        assert "DIFFERENT" in art()["writer_enumeration"]["only_writer"]["condition"]

    def test_producers_and_the_bit_order_are_cited(self):
        p = art()["normalized_state_producers"]
        assert "0x1e0a5f2" in " ".join(p["sequence"]) and "0x1e0a656" in " ".join(p["sequence"])
        assert "BIT 8" in p["sequence"][2] and "BIT 9" in p["sequence"][3]

    def test_analogue_overwrite_warning_is_present(self):
        assert "overwrite" in art()["normalized_state_producers"]["critical_detail"]
        assert "do not infer" in art()["rt_pipeline"]["warning"]

    def test_rt_is_not_claimed_solved(self):
        assert art()["rt_pipeline"]["status"].startswith("NOT YET PROVEN")
