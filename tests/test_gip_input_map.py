"""Tests for the live Xbox GIP input map (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
GIP = REPO / "results" / "linux-driver" / "xbox-gip-input-map.json"
HOST = REPO / "results" / "firmware" / "gip-host-normalization-map.json"
TRIO = REPO / "results" / "firmware" / "usb-trio-reconstruction.md"


class TestGipMap:
    def g(self):
        return json.loads(GIP.read_text())

    def f(self, name):
        return next(x for x in self.g()["fields"] if x["control"] == name)

    def test_report_is_48_bytes_type_20(self):
        assert self.g()["frame"]["length"] == 48 and self.g()["frame"]["type"] == "0x20"

    def test_digital_controls_have_two_cycles(self):
        for n in ("A", "M1", "M2"):
            assert self.f(n)["cycles"] == 2

    def test_a_and_m1_share_byte4_different_bits(self):
        assert self.f("A")["offset"] == 4 and self.f("A")["bit"] == "0x10"
        assert self.f("M1")["bit"] == "0x20"

    def test_m2_is_byte5(self):
        assert self.f("M2")["offset"] == 5 and self.f("M2")["bit"] == "0x40"

    def test_triggers_are_16bit_and_rt_has_no_digital_bit(self):
        assert self.f("LT")["offset"] == "6-7" and self.f("RT")["offset"] == "8-9"
        txt = (REPO / "results" / "linux-driver" / "xbox-gip-input-map.md").read_text()
        assert "RT has no digital bit of its own" in txt

    def test_counters_rejected_before_field_assignment(self):
        assert self.f("sequence")["class"] == "SEQUENCE"
        assert self.f("timestamp/counter A")["class"] == "TIMESTAMP"

    def test_axis_roles_are_not_overclaimed(self):
        assert any("axis role" in x for x in self.g()["not_proven"])


class TestHostSideHonesty:
    def test_host_side_columns_remain_unknown(self):
        h = json.loads(HOST.read_text())
        assert h["status"].startswith("PARTIAL")
        assert all(r.get("host_side") == "UNKNOWN" for r in h["rows"])

    def test_trio_reports_the_endianness_tension(self):
        t = TRIO.read_text()
        assert "big-endian" in t and "little-endian" in t


class TestTrioStructure:
    def test_dispatch_table_is_recorded(self):
        t = TRIO.read_text()
        assert "0x1e09ae8" in t and "0x1e09c4c" in t and "0x1e09b9d" in t

    def test_transfer_length_is_recorded(self):
        t = TRIO.read_text()
        assert "0xc00" in t and "3072" in t
