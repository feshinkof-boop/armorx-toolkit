"""Tests for the precise-transition, length-variant and RT-synthesis artifacts."""
from __future__ import annotations

import json
import pathlib

R = pathlib.Path(__file__).resolve().parents[1] / "results"


class TestLengthVariants:
    def a(self):
        return json.loads((R / "linux-driver" / "gip-length-variants.json").read_text())

    def test_resolved_with_retraction(self):
        a = self.a()
        assert a["resolved"] is True and "generalised" in a["retraction"]

    def test_switchover_order(self):
        e = self.a()["evidence"]["power_button_pcap"]
        assert e["last_32B_frame_t_s"] < e["first_48B_frame_t_s"]

    def test_steady_state_is_48(self):
        assert self.a()["evidence"]["control_map_pcap"]["frames_32B"] == 0


class TestPreciseTransitions:
    def p(self):
        return json.loads((R / "linux-driver" / "gip-precise-transitions.json").read_text())

    def test_a_causality(self):
        assert "LEADS" in self.p()["A"]["interpretation"]

    def test_rt_discrepancy_reported(self):
        assert self.p()["RT"]["interpretation"].startswith("OPEN DISCREPANCY")

    def test_reader_skew_excluded(self):
        assert self.p()["delivery_lag_s"].startswith("0.000")


class TestRtSynthesis:
    def s(self):
        return json.loads((R / "firmware" / "rt-digital-synthesis.json").read_text())

    def test_status_scoped(self):
        assert self.s()["status"].startswith("PROVEN STATIC") and self.s()["not_proven"]

    def test_bits_and_bytes(self):
        j = json.dumps(self.s())
        assert "0x100" in j and "0x200" in j and "sp+1092" in j and "sp+1093" in j

    def test_search_result_recorded(self):
        assert "only two tests" in self.s()["search"]


class TestProducerCorrection:
    def p(self):
        return json.loads((R / "firmware" / "state-1d4-producer.json").read_text())

    def test_classifier_not_copier(self):
        assert self.p()["size"] == 134 and self.p()["threshold"] == 12000
        assert "superseded" in self.p()["correction"]


class TestEnumStateMachine:
    def e(self):
        return json.loads((R / "firmware" / "xbox-host-enum-state-machine.json").read_text())

    def test_seven_cases_and_default(self):
        c = self.e()["cases"]
        assert len(c) == 5  # 0, 1, 2/3/4, 5/6, default

    def test_case1_is_a_transmit_arm(self):
        assert "0x1e0675c" in self.e()["cases"]["1"]

    def test_gap_not_hidden(self):
        assert self.e()["not_proven"]
