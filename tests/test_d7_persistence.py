"""Tests for the D7 persistence chain artifact (2026-09-28 config-persistence pass)."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "q32s"))
CG = REPO / "results" / "firmware" / "d7-persistence-callgraph.json"

import q32s_tables  # noqa: E402  (kept for parity with the other q32s tests)


def model():
    return json.loads(CG.read_text())


@pytest.mark.skipif(not CG.exists(), reason="call graph not built")
class TestPersistenceChain:
    def test_chain_covers_handler_writer_finalizer_and_slot_select(self):
        addrs = [c["address"] for c in model()["chain"]]
        for a in ("0x1e09232", "0x1e05c66", "0x1e069c2", "0x1e059a2", "0x1e0580c"):
            assert a in addrs

    def test_every_chain_entry_cites_instructions(self):
        for c in model()["chain"]:
            assert c.get("evidence"), f"{c['address']} has no cited instructions"

    def test_finalizer_targets_the_out_of_image_library(self):
        fin = next(c for c in model()["chain"] if c["address"] == "0x1e069c2")
        assert "0x3003ec" in fin["evidence"][-1]

    def test_storage_model_constants(self):
        sm = model()["storage_model"]
        assert sm["config_record_length"] == "0x0090 = 144"
        assert "0x400" in sm["slots"] or "1024" in sm["slots"] + sm["slot_base"]
        assert "0x3120" in sm["slot_base"]
        assert sm["active_slot_state"] == "[0x4850+0x14]"
        assert sm["descriptor_state"] == "[0x4850+0x1b0]"

    def test_slot_to_key_binding_uses_the_m_button_mask(self):
        """Slots map through a mask of bits 23..26 = M1..M4 in the live key map."""
        slot = next(c for c in model()["chain"] if c["address"] == "0x1e06998")
        assert "0x7800000" in " ".join(slot["evidence"])
        assert "23..26" in slot["consequence"]

    def test_staged_ok_is_proven_and_durable_is_not_overclaimed(self):
        sv = model()["staged_vs_durable"]
        assert "PROVEN STATIC" in sv["staged_ok"]
        assert "NOT RESOLVABLE" in sv["classification"]
        assert "we do not hold" in sv["durable_ok"]

    def test_bytes_112_115_correction_is_recorded(self):
        assert any("135..138" in c for c in model()["corrections"])


@pytest.mark.skipif(not (REPO / "results/reconciliation/firmware-unknown-ledger.json").exists(),
                    reason="ledger absent")
class TestLedger:
    def _led(self):
        d = json.loads((REPO / "results/reconciliation/firmware-unknown-ledger.json").read_text())
        return {e["id"]: e for e in d["entries"]}

    def test_new_unknowns_are_present_and_honest(self):
        led = self._led()
        assert led["FW-U-032"]["status"] == "DEFERRED_REQUIRES_LIBRARY_BINARY"
        assert led["FW-U-033"]["status"] == "OPEN"

    def test_no_invented_vendor_api_name(self):
        txt = json.dumps(self._led()["FW-U-032"]).lower()
        for name in ("vm_write", "syscfg_write", "flash_write"):
            assert name not in txt
