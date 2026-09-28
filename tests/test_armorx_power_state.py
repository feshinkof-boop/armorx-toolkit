"""Tests for the power-state/identity transition (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

ART = pathlib.Path(__file__).resolve().parents[1] / "results" / "f20" / "armorx-power-button-transition.json"


class TestPowerStateIdentity:
    def art(self):
        return json.loads(ART.read_text())

    def test_baseline_is_the_vendor_personality(self):
        assert self.art()["baseline_state"]["vid_pid"].startswith("413d:2106")

    def test_press_switches_to_the_xbox_personality(self):
        assert self.art()["resulting_state"]["vid_pid"] == "045e:0b12"
        assert "xpad" in self.art()["resulting_state"]["driver"]

    def test_same_port_throughout(self):
        assert "no cable movement" in self.art()["transition"]["device_path"]

    def test_operator_answer_is_recorded_not_invented(self):
        a = self.art()["operator_action"]
        assert a["response"] == "other" and a["ack"].startswith("2026-09-28T16:10:38")

    def test_serial_ambiguity_is_declared_open(self):
        assert "cannot be distinguished" in self.art()["open_question"]

    def test_agent_writes_are_separated_from_kernel_writes(self):
        s = self.art()["safety"]
        assert "none" in s["agent_writes"] and "xpadd" not in s["automatic_host_writes"].lower()
        assert "xpad" in s["automatic_host_writes"]
