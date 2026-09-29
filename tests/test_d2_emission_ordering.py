"""Guards for the 2026-09-29 D2 emission-ordering and arming-provenance findings.

These tests pin the corrections so the superseded readings cannot quietly return.
"""
import json, pathlib
import pytest

R = pathlib.Path(__file__).resolve().parents[1] / "results" / "firmware"
order = json.loads((R / "d2-emission-ordering.json").read_text())
prov = json.loads((R / "rt-lt-arming-state-provenance.json").read_text())


def test_synthesis_buffer_is_the_memcmp_operand():
    assert "sp+1080" in order["buffer_identity"]
    assert "0x1e0dad2" in order["buffer_identity"]


def test_dominance_cannot_order_the_loop_blocks():
    assert order["dominance_verdicts"]["synthesis(0x1e0cfc0) vs memcmp(0x1e0dad2)"] == "CYCLIC_BOTH_ORDERS_POSSIBLE"
    assert "not reproducible" in order["dominance_verdicts"]["interpretation"].lower()


def test_edge_path_is_not_necessary():
    key = "is_the_edge_toggle_path_necessary_for_an_emitted_D2_change"
    assert order["answers"][key].lower().startswith("no")


def test_state_can_change_without_emission():
    key = "can_an_analogue_trigger_movement_change_internal_state_without_causing_a_D2_report"
    assert order["answers"][key].upper().startswith("YES")


def test_corrections_are_preserved():
    for doc in (order, prov):
        joined = " ".join(doc["corrections"])
        assert "INTERSECTION" in joined
        assert "0x1e094de" in joined


def test_lt_and_rt_share_the_helper():
    assert prov["lt_reaches_equivalent_logic"].startswith("YES")
    sites = {s["addr"]: s for s in prov["call_sites"]}
    assert sites["0x1e0cec2"]["channel_index"] == "r0 = 0x0"
    assert sites["0x1e0cee8"]["channel_index"].startswith("r0 = 0x1")


def test_gate_bytes_are_recorded():
    assert "0x1d6" in prov["gate_observation"]
    assert "0x1db" in prov["gate_observation"]


def test_r4_base_is_the_candidate_buffer():
    assert prov["r4_provenance"]["reaching_definition"].startswith("0x1e0cd58")
    assert "sp+1080" in prov["r4_provenance"]["why_it_matters"]


def test_mode_byte_domain_is_bounded_and_flagged():
    assert "0/1" in prov["mode_byte_domain"]
    assert "unknown" in prov["mode_byte_domain"]


def test_pseudocode_records_both_gates():
    assert "0x1d6" in order["pseudocode"] and "0x1db" in order["pseudocode"]
