"""Tests for the D2 report-engine artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "d2-report-engine.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestD2ReportEngine:
    def test_frame_length_arithmetic_matches_the_live_frame(self):
        d = art()["frame_construction"]["d2_18B"]
        assert d["payload_len"] == "0x0e (14)"
        assert d["frame_len"].startswith("14 + 4 = 0x12")

    def test_payload_layout_reproduces_the_live_field_map(self):
        fields = art()["payload_layout_proven"]["fields"]
        offs = [f["offset"] for f in fields]
        assert offs[:6] == ["0x00", "0x04", "0x06", "0x08", "0x0a", "0x0e"]
        assert sum(1 for f in fields if f["width"] == 2) == 4
        assert fields[0]["matches_live"] == "frame [3..6] = 32-bit digital mask"

    def test_two_report_variants_and_two_flags(self):
        g = art()["send_gate"]
        assert g["enable_flag"] == "b[cfg+0x10]"
        assert "0x1e0db38" in g["gate_3"]["addr"]
        assert "0x11" in g["gate_3"]["code"]

    def test_repeat_counter_is_recorded(self):
        loop = art()["send_gate"]["repeat_loop"]
        assert "0x3a" in "".join(loop["code"])
        assert loop["addrs"][0] == "0x1e0db1c"
        assert "100" in art()["send_gate"]["gate_2"]["effect"]

    def test_handler_writes_both_flags(self):
        h = art()["d2_handler_flag_write"]
        assert h["addr"] == "0x1e08d24"
        assert any("0x11" in c for c in h["code"])
        assert "REPORT VARIANT" in h["conclusion"]

    def test_open_trigger_is_stated_not_hidden(self):
        f = art()["fw_u_026"]
        assert f["status"] == "PARTIALLY_RESOLVED"
        assert "0x1e0a9b4" in f["next"]
        assert "not traced in this window" in art()["send_gate"]["not_proven"]
