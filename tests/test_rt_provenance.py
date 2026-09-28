"""Tests for the RT change-mask / analog / gate provenance (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

F = pathlib.Path(__file__).resolve().parents[1] / "results" / "firmware"


class TestChangeMask:
    def a(self):
        return json.loads((F / "rt-change-mask-provenance.json").read_text())

    def test_origins_are_memory_not_changes(self):
        rd = self.a()["reaching_definitions"]
        assert any("sp+1080" in x for x in rd["r4"])
        assert any("r15 + 0x1d0" in x for x in rd["r5"])

    def test_intersection_not_change(self):
        assert "INTERSECTION" in self.a()["correction"]

    def test_gate_recorded(self):
        assert "(r5 & r4) == 0" in self.a()["gate"]

    def test_field_is_not_named_without_proof(self):
        assert self.a()["persistent_field_0x1d0"]["semantics"].startswith("UNKNOWN")


class TestAnalog:
    def a(self):
        return json.loads((F / "rt-analog-provenance.json").read_text())

    def test_bit9_creator_recorded(self):
        j = json.dumps(self.a())
        assert "0xfffffdff" in j and "0x200" in j and "0x1e0a426" in j

    def test_predicate_not_overclaimed(self):
        assert self.a()["not_proven"]


class TestGate:
    def g(self):
        return json.loads((F / "rt-event-gate.json").read_text())

    def test_status_is_partial(self):
        assert self.g()["status"].startswith("PARTIALLY")

    def test_rt_explanation_is_a_candidate(self):
        assert "CANDIDATE, not a proof" in self.g()["consequence_for_the_rt_question"]


class TestLiveRecheck:
    def l(self):
        return json.loads((F / "rt-live-recheck.json").read_text())

    def test_still_unresolved(self):
        assert self.l()["status"].startswith("UNRESOLVED")

    def test_no_wrong_pairing_excuse(self):
        assert "cannot be explained by a wrong byte pairing" in self.l()["result"]["conclusion"]
