"""Tests for the V41 input-state struct artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "input-state-v41.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestInputState:
    def test_helper_is_a_three_s16_swapper(self):
        assert "THREE-s16 swapper" in art()["serializer_layout"]["helper_proof"]

    def test_lt_rt_are_inside_the_compared_range(self):
        f = {x["offset"]: x for x in art()["struct_28B"]["fields"]}
        assert f["0x0c"]["semantic"].startswith("LT") and f["0x0c"]["in_compared_14"] is True
        assert f["0x0d"]["semantic"].startswith("RT") and f["0x0d"]["in_compared_14"] is True

    def test_struct_sums_to_28(self):
        total = 0
        for x in art()["struct_28B"]["fields"]:
            w = x["width"]
            total += 3 * 2 if isinstance(w, str) and "3x2" in w else int(w)
        assert total == 28

    def test_hypothesis_is_refuted_with_reason(self):
        h = art()["hypothesis_verdict"]
        assert h["verdict"] == "REFUTED"
        assert "+0x0c" in h["why"] and "INSIDE" in h["why"]

    def test_rt_is_not_declared_explained(self):
        r = art()["rt_contradiction"]
        assert r["status"].startswith("STILL OPEN")
        assert "do not report RT as explained" in r["must_not_claim"]

    def test_ledger_agrees_with_the_report(self):
        led = json.loads((REPO / "results/reconciliation/firmware-unknown-ledger.json").read_text())
        e = {x["id"]: x for x in led["entries"]}["FW-U-026"]
        assert e["status"] == "PARTIALLY_RESOLVED"
        assert "REFUTED" in " ".join(e["evidence"])
