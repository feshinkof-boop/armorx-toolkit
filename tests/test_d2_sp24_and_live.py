"""Tests for the sp+24 provenance and raw live D2 reconciliation artifacts."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SP = REPO / "results" / "firmware" / "d2-sp24-provenance.json"
REC = REPO / "results" / "firmware" / "d2-raw-live-reconciliation.json"


@pytest.mark.skipif(not SP.exists(), reason="artifact absent")
class TestSp24:
    def art(self):
        return json.loads(SP.read_text())

    def test_sp24_holds_an_address_not_a_tagged_value(self):
        a = self.art()
        assert "REFUTED" in a["headline"]
        assert "0x1e0aeba" in a["writers_of_sp24_in_region"][0]["addr"]

    def test_origin_is_the_state_record_at_0x1d4(self):
        o = self.art()["origin_of_the_d2_value"]
        assert any("r13 = r14 + 0x1d4" in s for s in o["sequence"])
        assert "state+0x1d4" in o["conclusion"]

    def test_object_has_its_own_change_detection(self):
        o = self.art()["object"]
        assert "0x2fbf4a" in o["own_change_detection"] and "0x2fbf36" in o["own_change_detection"]

    def test_byte_store_is_excluded(self):
        w = [x for x in self.art()["writers_of_sp24_in_region"] if x["addr"] == "0x1e0a082"]
        assert w and "excluded" in w[0]["note"]

    def test_open_items_are_recorded(self):
        assert "NOT proven" in self.art()["open"][0]


@pytest.mark.skipif(not REC.exists(), reason="artifact absent")
class TestLiveReconciliation:
    def art(self):
        return json.loads(REC.read_text())

    def test_frame_contract_matches_the_live_example(self):
        ex = self.art()["frame_contract_confirmed"]["worked_example"]
        hexpart = ex.split()[0]
        assert set(hexpart) <= set("0123456789abcdef")
        b = bytes.fromhex(hexpart)
        assert b[0] == 0xA5 and b[1] == 0x12 and b[2] == 0x02
        assert sum(b[:17]) & 0xFF == b[17]
        assert b[15] == 0x00 and b[16] == 0xFF

    def test_window_counts(self):
        d = self.art()["distributions"]
        assert d["W0"]["frames"] == 228 and d["W1"]["frames"] == 263 and d["W2"]["frames"] == 283

    def test_bit9_only_in_the_rt_window(self):
        d = self.art()["distributions"]
        assert d["W0"]["frames_with_bit9"] == 0 and d["W2"]["frames_with_bit9"] == 0
        assert d["W1"]["frames_with_bit9"] == 184

    def test_rt_byte_is_analogue(self):
        vals = sorted(int(k) for k in self.art()["distributions"]["W1"]["byte16"])
        assert vals == [0, 17, 27, 96, 255]

    def test_self_trigger_stays_open(self):
        v = self.art()["verdict"]
        assert "OPEN" in v["no_self_trigger"]
        assert "mode-dependent" in v["reconciliation_with_static"]
