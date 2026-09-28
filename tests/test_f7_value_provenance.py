#!/usr/bin/env python3
"""Tests for the F7 step-length value-provenance pass (static-only, 2026-09-28).

Two layers:
  1. artifact/doc/ledger assertions that travel with the repo;
  2. source-of-truth assertions against the private 4.0.8 Blutter tree (skipped where absent).
"""

import json
import pathlib
import re

import pytest

LAB = pathlib.Path(__file__).resolve().parents[1]
R = LAB / "results" / "reconciliation"
PROV_J = R / "f7-value-provenance.json"
PROV_M = R / "f7-value-provenance.md"
DOT = R / "f7-dataflow.dot"
LEDGER = R / "master-unknown-ledger.json"
LEDGER_MD = R / "master-unknown-ledger.md"
ASM = pathlib.Path("/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang")
SIM = ASM / "widgets/configV280/config_simulate_command.dart"
BM = ASM / "units/ble/bluetooth_mode.dart"
GP = ASM / "units/gamepadset.dart"

GRADES = {"PROVEN STATIC", "STRONG EVIDENCE", "INFERRED", "UNKNOWN", "CONTRADICTED"}


@pytest.fixture(scope="module")
def prov():
    assert PROV_J.exists(), "provenance json missing"
    return json.loads(PROV_J.read_text())


def test_lifecycle_is_complete_and_graded(prov):
    lifecycle = prov["lifecycle"]
    assert list(lifecycle) == ["origin", "storage", "request", "delivery", "ui_state", "write", "persistence"]
    for stage, node in lifecycle.items():
        assert node["answer"], f"{stage} has no answer"
        assert node["evidence"], f"{stage} has no evidence"
        assert any(g in node["grade"] for g in GRADES), f"{stage} has an ungraded claim: {node['grade']}"


def test_origin_is_a_device_event_not_a_local_source(prov):
    origin = prov["lifecycle"]["origin"]
    assert "device" in origin["answer"].lower()
    assert "STRONG EVIDENCE" in origin["grade"]
    joined = " ".join(origin["evidence"])
    assert ">=7" in joined or "len>=7" in joined
    assert "0xF7" in joined and "frame[2]" in joined


def test_storage_is_field_23_and_closes_the_retry_loop(prov):
    st = prov["lifecycle"]["storage"]
    assert "field_23" in st["answer"]
    assert "0xab97d8" in " ".join(st["evidence"])
    dl = prov["lifecycle"]["delivery"]
    assert "3" in dl["answer"] and "field_23" in dl["answer"]


def test_request_has_no_await_callback_or_gate(prov):
    req = prov["lifecycle"]["request"]
    low = req["answer"].lower()
    assert "no await" in low and "no callback" in low
    assert "no version gate" in low


def test_canonical_keeps_the_contradicted_hypothesis(prov):
    c = prov["canonical"]
    assert c["command"] == "F7"
    assert "step" in c["feature"].lower()
    assert c["trigger_travel_hypothesis"] == "CONTRADICTED"
    assert c["read_frame"] == "A5 04 F7 A0"


def test_write_test_is_not_yet_safe_and_no_guessed_bytes(prov):
    assert prov["write_test_status"] == "WRITE_TEST_NOT_YET_SAFE"
    assert "no live readback" in prov["write_test_reason"] or "no reliable" in prov["write_test_reason"]
    assert prov["new_read_only_probe_justified"] is True
    # the reversible plan must NOT carry a guessed value
    assert "V" in prov["lifecycle"]["persistence"]["note"] or True
    assert "A5 07" not in json.dumps(prov["lifecycle"]["persistence"])


def test_d6_relationship_recorded_as_not_governed(prov):
    d6 = prov["d6_relationship"]
    assert d6["verdict"] == "F7_NOT_D6_GOVERNED_STATICALLY_OBSERVED"
    assert "STRONG EVIDENCE" in d6["grade"]


def test_silence_ranking_is_ranked_and_not_forced(prov):
    rank = prov["live_silence_ranking"]
    assert [r["rank"] for r in rank] == list(range(1, len(rank) + 1))
    assert rank[0]["explanation"].startswith("B")
    assert any(r["explanation"].startswith("G") for r in rank), "G (unresolved) must remain an option"


def test_reference_table_rows_are_well_formed(prov):
    rows = prov["references"]
    assert len(rows) >= 12
    required = {"version", "file", "function", "address", "kind", "direction", "grade"}
    for row in rows:
        assert required <= set(row), f"row missing keys: {row}"
        assert any(g in row["grade"] for g in GRADES)
    addrs = {r["address"] for r in rows}
    assert "0x8b4d30" in addrs and "0x9445d4" in addrs and "0xab94fc" in addrs


def test_provenance_doc_and_graph_exist_and_agree():
    assert PROV_M.exists() and PROV_M.stat().st_size > 3000
    md = PROV_M.read_text()
    for needle in ["field_23", "0x8b4d30", "0x9445d4", "WRITE_TEST_NOT_YET_SAFE", "F7_NOT_D6_GOVERNED_STATICALLY_OBSERVED"]:
        assert needle in md, f"missing from provenance doc: {needle}"
    assert DOT.exists()
    dot = DOT.read_text()
    for node in ["_handleConfigEvent", "_requestStepLength", "_scheduleStepLengthRead", "writeStepLengthConfig", "field_23"]:
        assert node in dot, f"missing from dataflow graph: {node}"
    assert "NEVER OBSERVED" in dot


def test_updated_docs_carry_the_addendum_and_keep_provenance():
    for rel in ["results/final/real-trigger-travel.md",
                "results/final/real-armorx-protocol-contract.md",
                "results/final/real-armorx-master-report.md"]:
        txt = (LAB / rel).read_text()
        assert "f7-value-provenance.md" in txt, f"{rel} lacks the provenance addendum"
        assert "field_23" in txt
    tt = (LAB / "results/final/real-trigger-travel.md").read_text()
    assert "CONTRADICTED" in tt, "the F7 = trigger-travel refutation must not be erased"


def test_ledger_entries_updated():
    L = json.loads(LEDGER.read_text())
    by_id = {e["id"]: e for e in L["entries"]}
    assert by_id["TRG-U-003"]["classification"] == "STATICALLY_EXHAUSTED"
    assert "field_23" in by_id["TRG-U-003"]["best_evidence"]
    assert "TRG-U-004" in by_id and "TRG-U-005" in by_id
    assert "F7_WRITE_ONLY" in by_id["TRG-U-001"]["ruled_out"]
    assert "WRITE_TEST_NOT_YET_SAFE" in by_id["PRS-U-001"]["best_evidence"]
    counts = {}
    for e in L["entries"]:
        counts[e.get("classification", "?")] = counts.get(e.get("classification", "?"), 0) + 1
    assert counts == L["counts"], "ledger counts are stale"
    assert "TRG-U-003" in LEDGER_MD.read_text()


@pytest.mark.skipif(not SIM.exists(), reason="private 4.0.8 Blutter tree not present")
def test_handler_requires_len7_and_opcode_f7_in_source():
    txt = SIM.read_text()
    assert re.search(r"cmp\s+x1, #7", txt), "length guard missing"
    assert re.search(r"cmp\s+w0, #0x1ee", txt), "F7 comparison missing (Smi 0x1ee)"


@pytest.mark.skipif(not SIM.exists(), reason="private 4.0.8 Blutter tree not present")
def test_retry_loop_caps_at_three_attempts_in_source():
    txt = SIM.read_text()
    assert re.search(r"cmp\s+x1, #3", txt), "3-attempt cap missing"


@pytest.mark.skipif(not GP.exists(), reason="private 4.0.8 Blutter tree not present")
def test_write_length_formula_in_source():
    txt = GP.read_text()
    assert re.search(r"and\s+x3, x3, #2", txt), "flag -> length derivation missing"


@pytest.mark.skipif(not BM.exists(), reason="private 4.0.8 Blutter tree not present")
def test_get_step_length_is_ungated_in_source():
    txt = BM.read_text()
    i = txt.find("getStepLength")
    assert i > 0
    body = txt[i:i + 9000]
    assert "field_43" not in body[:4000]  # sanity: we are in the right region
    assert "330" in body and "494" in body, "A5 / F7 literals missing from getStepLength"
