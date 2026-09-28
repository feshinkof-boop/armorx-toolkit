"""Tests for the live F20 capture artifacts (2026-09-28)."""
from __future__ import annotations

import hashlib
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
ART = REPO / "results" / "f20" / "f20-dual-identity.json"
DESC = REPO / "results" / "linux-driver" / "hid-report-descriptor.bin"


@pytest.mark.skipif(not ART.exists(), reason="artifact absent")
class TestF20Live:
    def art(self):
        return json.loads(ART.read_text())

    def test_vendor_mode_identity(self):
        assert self.art()["vendor_mode"]["vid_pid"] == "413d:2106"

    def test_vendor_mode_has_no_input_node(self):
        assert "NO /dev/input/event" in self.art()["vendor_mode"]["nodes"]

    def test_receiver_alone_is_silent(self):
        t = self.art()["vendor_mode"]["receiver_alone_traffic"]
        assert "NONE carrying data" in t and "12 interrupt IN URBs" in t

    def test_xbox_mode_identity_and_driver(self):
        x = self.art()["xbox_mode"]
        assert x["vid_pid"] == "045e:0b12" and "xpad" in x["interface0"]

    def test_hid_interface_is_replaced_in_xbox_mode(self):
        assert "CONTRADICTED" in self.art()["hypothesis_status"]["previous assumption that F20 keeps exposing the vendor HID interface"]

    def test_transition_records_the_same_port(self):
        tl = self.art()["transition_timeline"]
        assert any("USB disconnect, device number 5" in r[1] for r in tl)
        assert any("idVendor=045e" in r[1] for r in tl)

    def test_descriptor_hash_is_frozen(self):
        assert hashlib.sha256(DESC.read_bytes()).hexdigest() == self.art()["vendor_mode"]["hid_report_descriptor_sha256"]

    def test_reported_gaps_are_in_the_artifact(self):
        nd = " ".join(self.art()["not_done"])
        assert "per-control input mapping" in nd and "female USB port" in nd


@pytest.mark.skipif(not DESC.exists(), reason="descriptor absent")
class TestDescriptorBytes:
    def test_descriptor_is_the_frozen_29_bytes(self):
        d = DESC.read_bytes()
        assert len(d) == 29
        assert d[:3] == bytes.fromhex("067aff")          # usage page 0xFF7A
        assert d[-2:] == b"\xc0\xc0"                     # two end-collections
        assert bytes.fromhex("9540") in d                 # report count 64
