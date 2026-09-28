"""Tests for the persistence-closure attempt artifact (2026-09-28)."""
from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
A = REPO / "results" / "firmware" / "persistence-closure-attempt.json"
L = REPO / "results" / "firmware" / "library-callsites-0x1f0000-0x31ffff.json"


def art():
    return json.loads(A.read_text())


@pytest.mark.skipif(not A.exists(), reason="artifact absent")
class TestClosureAttempt:
    def test_3003ec_has_exactly_one_callsite(self):
        q = art()["q_3003ec_callsites"]
        assert q["count"] == 1
        assert q["sites"][0]["addr"] == "0x1e069d4"
        assert q["sites"][0]["target"] == "0x3003ec"

    def test_abi_is_stated_but_not_overclaimed(self):
        abi = art()["inferred_abi_0x3003ec"]
        assert abi["r2"] == "0x90 = 144 = the config record length"
        assert "no vendor symbol name" in abi["not_claimed"]

    def test_dirty_flag_writer_and_reader_are_cited(self):
        df = art()["dirty_flag_xrefs"]
        assert df["writer"][0]["addr"] == "0x1e05cae" and df["writer"][0]["value"] == "3"
        assert df["reader"][0]["addr"] == "0x1e0684c"
        assert "PROVEN" in df["reader"][0]["base"]

    def test_value_3_is_not_overinterpreted(self):
        assert art()["dirty_flag_xrefs"]["meaning_of_3"].startswith("NOT a proven")

    def test_usbh_finding_is_flagged_as_a_caveat(self):
        u = art()["usbh_finding"]
        assert "usbh_gamepad_ready" in u["evidence"]
        assert "must not assume otherwise" in u["consequence"]

    def test_unknowns_are_honest(self):
        assert art()["fw_u_033"].startswith("OPEN")
        assert "UNRESOLVED" in art()["fw_u_032"]


@pytest.mark.skipif(not L.exists(), reason="library inventory absent")
class TestLibraryInventory:
    def test_inventory_is_large_and_consistent(self):
        lib = json.loads(L.read_text())
        assert len(lib) > 1000
        for c in lib:
            assert c["instr"] in ("call", "goto")
            assert 0x1F0000 <= int(c["target"], 16) <= 0x31FFFF

    def test_3003ec_appears_once_in_the_inventory(self):
        lib = json.loads(L.read_text())
        assert [c for c in lib if c["target"] == "0x3003ec"] == [lib[[c["target"] for c in lib].index("0x3003ec")]]
