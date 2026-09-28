#!/usr/bin/env python3
"""Regression tests for the 2026-09-28 key-ID closure session.

These lock three things:
  1. the physical result (RT and the L stick produced nothing, and that is recorded as such);
  2. the harness bug that misreported a *missing dialog script* as an operator cancel;
  3. the final classification of the unresolved numeric ids, in every canonical file.
"""
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
SESSION = REPO / "results/experiments/key-id-closure-20260928-060134"
RUNNER = REPO / "automation/scripts/key-id-closure.py"


def _j(p):
    return json.loads(p.read_text())


# ---------------------------------------------------------------- the physical result

def test_session_artifacts_exist():
    for f in ("RESULT.md", "control-inventory.json", "control-inventory.md",
              "result-rt.json", "result-l_stick.json",
              "window-rt.jsonl", "window-l_stick.jsonl", "btmon.btsnoop"):
        assert (SESSION / f).exists(), f"missing session artifact: {f}"


def test_rt_produced_no_frames_at_all():
    """RT was pulled twice in a popup open 16.8 s and ACKed; nothing crossed the link."""
    r = _j(SESSION / "result-rt.json")
    assert r["classification"] == "RT_NO_REPORT_OBSERVED"
    assert r["analysis"]["verdict"] == "NO_REPORT_OBSERVED"
    assert r["analysis"]["valid_frames"] == 0
    assert r["analysis"]["bits"] == []
    assert r["analysis"]["transitions"] == []
    assert r["cancelled"] is False, "the operator ACKed; this must never be recorded as a cancel"


def test_rt_window_contains_no_valid_button_frame():
    recs = [json.loads(l) for l in (SESSION / "window-rt.jsonl").read_text().splitlines() if l.strip()]
    assert recs, "the window must still hold the frames that DID arrive"
    assert not any(r["valid"] for r in recs)
    # and it must hold exactly the three control-plane frames, nothing more
    assert sorted(r["hex"] for r in recs) == ["a5050b30e5", "a505d2007c", "a505d2017d"]


def test_l_stick_probe_also_produced_no_frames():
    r = _j(SESSION / "result-l_stick.json")
    assert r["classification"] == "STICK_NO_REPORT_OBSERVED"
    assert r["analysis"]["valid_frames"] == 0


def test_session_sent_no_configuration_write():
    """Only the sanity query and the D2 runtime toggles may appear in this session's TX."""
    for name in ("rt", "l_stick"):
        tx = _j(SESSION / f"result-{name}.json")["tx"]
        assert tx, f"{name}: expected the control-plane writes to be recorded"
        for frame in tx:
            assert re.fullmatch(r"a5040bb4|a505d2017d|a505d2007c", frame), f"unexpected write: {frame}"
    joined = " ".join(f for n in ("rt", "l_stick") for f in _j(SESSION / f"result-{n}.json")["tx"])
    for forbidden in ("d7", "d8", "fc", "fd"):
        assert f"a505{forbidden}" not in joined


def test_rt_analog_offset_was_verified_against_the_contract():
    """The brief required verifying the analyzer's offset before trusting it."""
    contract = (REPO / "results/reconciliation/d2-frame-contract.md").read_text().replace("`", "")
    assert "[16] RT analog" in contract
    r = _j(SESSION / "result-rt.json")
    assert r["rt_analog_offset_verified"]["index"] == 16
    # and the session must NOT claim an analog result it could not sample
    note = r["classification_note"].lower()
    assert "neither" in note and "confirmed" in note and "excluded" in note


# ---------------------------------------------------------------- the harness bug

def test_runner_resolves_the_dialog_helper_to_an_existing_path():
    """It once resolved automation/scripts/operator-dialog-kdialog.sh, which does not exist; bash then
    exited 127 with no popup at all."""
    src = RUNNER.read_text()
    assert 'DIALOG = str(_HERE.parent / "operator-dialog-kdialog.sh")' in src
    m = re.search(r'DIALOG = str\(_HERE\.parent / "([^"]+)"\)', src)
    resolved = REPO / "automation" / m.group(1)
    assert resolved.exists(), f"the resolved dialog helper does not exist: {resolved}"


def test_runner_refuses_to_run_without_the_dialog_helper():
    src = RUNNER.read_text()
    assert "DIALOG_MISSING" in src


def test_only_exit_code_1_is_an_operator_cancel():
    """A missing script / bad args / no GUI session must never be recorded as OPERATOR_CANCELLED."""
    src = RUNNER.read_text()
    assert "if rc == 1:" in src
    assert "DIALOG_FAILED: rc=" in src
    # the old blanket form must be gone
    assert not re.search(r"if rc != 0:\s*\n\s*cancelled = True", src)


def test_dialog_helper_exit_code_contract_is_documented():
    dlg = (REPO / "automation/operator-dialog-kdialog.sh").read_text()
    assert "--cancel" in dlg
    assert "2 = dialog failed" in dlg or "2 = " in dlg


# ---------------------------------------------------------------- the classifications

def test_canonical_map_records_the_final_classifications():
    canon = _j(REPO / "results/final/real-key-id-map.json")
    assert canon["proven_live_count"] == 26
    assert len(canon["proven_live"]) == 26
    cls = canon["unresolved_classification"]
    assert cls["9"] == "PROVEN_NEGATIVE"
    for i in ("2", "5", "21", "22", "31", "32", "33"):
        assert cls[i] == "UNOBSERVED_RESERVED_OR_UNUSED"
    assert set(cls) == {"2", "5", "9", "21", "22", "31", "32", "33"}
    # the map must not claim an analog result for RT
    assert "neither confirmed nor excluded" in canon["unresolved_detail"]["9"]


def test_consolidated_table_ingests_the_session_and_stays_at_26_proven():
    km = _j(REPO / "results/final/key-map-confidence.json")
    assert km["counts"]["proven_live"] == 26
    controls = {c["control"] for c in km["closure_session_evidence"]}
    assert {"RT", "L stick"} <= controls
    assert all(c["valid_frames"] == 0 for c in km["closure_session_evidence"])
    assert km["final_classification_of_unresolved"]["9"] == "PROVEN_NEGATIVE"
    row9 = next(r for r in km["rows"] if r["id"] == 9)
    assert row9["final_classification"] == "PROVEN_NEGATIVE"
    assert "PROVEN NEGATIVE as a digital bit" in row9["notes"]


def test_no_unresolved_id_is_forced_to_acquire_a_control_name():
    km = _j(REPO / "results/final/key-map-confidence.json")
    for row in km["rows"]:
        if row["id"] in (2, 5, 9, 21, 22, 31, 32, 33):
            assert row["grade"] == "UNKNOWN", f"id {row['id']} must not be promoted to PROVEN LIVE"
            assert not row.get("name")


def test_ledger_both_key_unknowns_closed_with_dated_evidence():
    led = _j(REPO / "results/reconciliation/master-unknown-ledger.json")
    by_id = {e["id"]: e for e in led["entries"]}
    assert by_id["KEY-U-001"]["classification"] == "UNOBSERVED_RESERVED_OR_UNUSED"
    assert by_id["KEY-U-001"]["resolved_at"] == "2026-09-28"
    assert by_id["KEY-U-002"]["status"] == "RESOLVED"
    assert "PROVEN_NEGATIVE" in by_id["KEY-U-002"]["classification"]
    # the overstatement must be corrected, not silently kept
    assert "never SAMPLED" in by_id["KEY-U-002"]["best_evidence"]


def test_control_inventory_says_rt_was_the_only_untested_control():
    inv = _j(SESSION / "control-inventory.json")
    assert inv["proven_live_count"] == 26
    # RT is the only control that was REQUESTED and never proven; the sticks were never requested at all
    assert "RT" in inv["physical_controls_not_yet_proven"]
    assert "L stick (analog, full deflection)" in inv["physical_controls_not_yet_proven"]
    assert "L stick (analog, full deflection)" in inv["never_requested_physical_controls"]
    # the derivation must state that it was not made from list order
    assert "no ordering inference" in inv["method"].lower()
    # and it must keep the possibility of unused ids explicit
    assert "unused" in inv["unresolved_id_note"].lower()
    assert "no name is assumed" in inv["unresolved_id_note"].lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
