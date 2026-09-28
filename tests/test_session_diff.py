"""Deterministic tests for the session differential (official vs harness).

Covers the shared classification helper, the staged-differential artifact, and the honesty rules the
brief insists on (no divergence claimed without an official capture; no durability regression).
No hardware and no capture file is required beyond the committed artifacts.
"""
import importlib.util
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
SES = REPO / "results/experiments/official-vs-harness-session-20260927-190741"


def _load():
    spec = importlib.util.spec_from_file_location("sessdiff", REPO / "automation/scripts/session-diff.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sd = _load()


def test_classify_recognises_the_known_frames():
    assert sd.classify({"value": "a505d2017d", "opcode": "Write Command"}) == "D2_ENABLE"
    assert sd.classify({"value": "a505d2007c", "opcode": "Write Command"}) == "D2_DISABLE"
    assert sd.classify({"value": "a5040bb4", "opcode": "Write Command"}) == "CTRL_QUERY_0B"
    assert sd.classify({"value": "a5050b30e5", "opcode": "Handle Value Notification"}) == "CTRL_REPLY_0B"
    assert sd.classify({"value": "a505d2017d", "opcode": "Handle Value Notification"}) == "D2_ECHO"


def test_classify_recognises_a_contract_valid_button_frame():
    frame = "a51202" + "00" * 15  # 36 hex chars = 18 bytes, opcode 0x02
    assert sd.classify({"value": frame, "opcode": "Handle Value Notification"}) == "BUTTON_FRAME"


def test_classify_does_not_treat_an_echo_as_a_button_frame():
    for echo in ("a505d2017d", "a505d2007c"):
        assert sd.classify({"value": echo, "opcode": "Handle Value Notification"}) != "BUTTON_FRAME"


def test_partial_pass_record_is_preserved_and_honest():
    """The PARTIAL-era record must survive intact in the snapshot (it documents a real blocked pass).

    The living documents legitimately advanced to COMPLETE once the official session was captured;
    these assertions therefore run against the preserved snapshot, plus the placeholder artifacts.
    """
    snap = SES / "official-session/completion-20260927-192908/partial-snapshot"
    diff = json.loads((snap / "official-vs-harness-diff.json").read_text())
    assert diff["overall_status"] == "PARTIAL"
    assert diff["official_session"]["captured"] is False
    assert diff["official_session"]["reason"] == "ANDROID_HCI_CAPTURE_UNAVAILABLE"
    for stage in ("connection", "security", "att_gatt", "application_sequence", "rx", "exit"):
        assert diff[stage]["official"]["status"] == "NOT_CAPTURED", stage
    # the placeholder artifacts still record the absence, and are not overwritten by the later capture
    summ = json.loads((SES / "official-session/official-hci-summary.json").read_text())
    assert summ["captured"] is False
    assert (SES / "official-session/raw/CAPTURE_UNAVAILABLE.txt").exists()
    # and the living documents now say the opposite - both must coexist
    live = json.loads((SES / "official-vs-harness-diff.json").read_text())
    assert live["overall_status"] == "COMPLETE"


def test_no_divergence_was_claimed_before_the_capture():
    """In the blocked pass the earliest difference was UNKNOWN - that record is preserved."""
    fd = json.loads((SES / "official-session/completion-20260927-192908/partial-snapshot/first-divergence.json").read_text())
    assert fd["earliest_proven_material_difference"] == "UNKNOWN"
    assert fd["computable"] is False
    assert "MISSING_PRECONDITION" in fd["explicitly_not_labelled"]
    assert fd["no_unknown_official_traffic_replayed"] is True


def test_harness_side_numbers_are_the_measured_ones():
    h = json.loads((SES / "harness-session/harness-hci-summary.json").read_text())
    assert h["role"] == "Central"
    assert h["peer_address_type"] == "Public"
    assert h["connection_interval_ms"] == 7.50
    assert h["peripheral_latency"] == 0
    assert h["supervision_timeout_ms"] == 2000
    assert h["att_mtu_negotiated"] == 64
    assert h["bonded"] is False and h["encrypted"] is False
    assert h["d2_enable_att_code"] == "0x52"


def test_harness_control_sequence_order_and_timestamps():
    g = json.loads((SES / "harness-session/harness-gatt-sequence.json").read_text())
    q, r = g["zero_b_query"], g["zero_b_reply"]
    pre, en, post = g["d2_disable_preclear"], g["d2_enable"], g["d2_disable_post"]
    assert q["value"] == "a5040bb4" and r["value"] == "a5050b30e5"
    assert en["value"] == "a505d2017d" and en["op"] == "Write Command"
    # the harness pre-clears D2 *before* the enable, then observes, then disables
    assert q["t"] < pre["t"] < en["t"] < post["t"]
    assert round(post["t"] - en["t"], 1) == 10.0, "the 10 s idle window"
    assert round(g["idle_window_s"], 1) == 10.0  # measured 10.01 s
    # the echo is the same bytes on RX: only the ATT opcode separates command from echo
    assert g["d2_enable_echo"]["dir"] == "RX" and "Notification" in g["d2_enable_echo"]["op"]


def test_final_d6_is_the_durable_baseline_and_not_a_new_durability_claim():
    d6 = json.loads((SES / "final-d6.json").read_text())
    assert d6["sha256"] == "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"
    assert d6["verdict"] == "CONFIG_BASELINE_MATCH"
    assert "NOT a new durability proof" in d6["durability_note"]
    # the blocked-pass verdict keeps its PARTIAL wording; the completed verdict says COMPLETE
    partial_verdict = (SES / "official-session/completion-20260927-192908/partial-snapshot/verdict.md").read_text()
    assert "PARTIAL" in partial_verdict
    verdict = (SES / "verdict.md").read_text()
    assert "COMPLETE" in verdict and "DURABLE_OK" in verdict and "STAGED_OK" in verdict
