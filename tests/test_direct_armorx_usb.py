"""Tests for the direct ARMOR-X USB artifacts (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
ART = REPO / "results" / "f20" / "direct-armorx-identity.json"
F20 = REPO / "results" / "f20" / "f20-dual-identity.json"

VENDOR_DESC_SHA = "f0e418decf688e7409ccebc1beb79a8d8c8c60e5c70150c5de7b056575bb366f"


@pytest.mark.skipif(not ART.exists(), reason="artifact absent")
class TestDirectArmorX:
    def art(self):
        return json.loads(ART.read_text())

    def test_direct_identity_matches_the_f20_vendor_personality(self):
        d = self.art()["direct_enumeration"]
        assert d["vid_pid"] == "413d:2106" and d["hid_report_descriptor_sha256"] == VENDOR_DESC_SHA
        assert d["descriptor_vs_f20"].startswith("IDENTICAL")

    def test_body_usb_is_silent_even_under_input(self):
        t = self.art()["traffic"]
        assert t["payload_bearing_frames"] == 0
        assert "NO traffic" in t["button_test"]

    def test_operator_disambiguation_is_recorded(self):
        assert "ARMOR-X PRO body" in self.art()["disambiguation"]

    def test_identity_round_trip(self):
        c = self.art()["identity_cycle_confirmed"]
        assert any("045e:0b12" in x for x in c["to_xbox"])
        assert any("413d:2106" in x for x in c["back_to_vendor"])

    def test_safety_distinguishes_agent_and_kernel_writes(self):
        s = self.art()["safety"]
        assert "none" in s["agent_initiated_writes"]
        assert "xpad" in s["automatic_host_traffic"]

    def test_no_overclaim_of_the_input_path(self):
        np = " ".join(self.art()["not_proven"])
        assert "not traced" in np


@pytest.mark.skipif(not F20.exists(), reason="f20 artifact absent")
class TestTrioEvidence:
    def test_trio_string_names_the_xbox_enumeration_step(self):
        txt = (REPO / "results" / "firmware" / "usb-trio-reconstruction.md").read_text()
        assert "m_xbox_enum_step" in txt and "usbh_socket_en" in txt
        assert "0x1e09c4c" in txt

    def test_trio_is_not_claimed_complete(self):
        txt = (REPO / "results" / "firmware" / "usb-trio-reconstruction.md").read_text()
        assert "structurally reconstructed, not field-matched" in txt

    def test_direct_to_d2_map_has_no_fabricated_fields(self):
        m = json.loads((REPO / "results" / "firmware" / "direct-usb-to-d2-map.json").read_text())
        assert m["status"].startswith("NO DIRECT USB ROUTE")
        assert len(m["unresolved"]) >= 3
