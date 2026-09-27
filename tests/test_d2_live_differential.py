"""Deterministic tests for the D2 live-differential experiment.

Two kinds of check:
  1. the RX classifier used to judge the experiment (synthetic frames);
  2. the recorded experiment result (all four cases silent), read from the committed artifacts.
No hardware is touched.
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]

import importlib.util
import sys
import types

# The experiment script requires bleak at import time; stub it so the pure helpers
# (RX classifier, mask extraction, checksum) stay testable without the BLE stack.
if "bleak" not in sys.modules:
    try:
        import bleak  # noqa: F401
    except ImportError:
        stub = types.ModuleType("bleak")
        stub.BleakScanner = object
        stub.BleakClient = object
        sys.modules["bleak"] = stub
        sys.modules["bleak.backends"] = types.ModuleType("bleak.backends")
        sys.modules["bleak.backends.characteristic"] = types.ModuleType("bleak.backends.characteristic")

spec = importlib.util.spec_from_file_location("d2diff", REPO / "automation/scripts/d2-differential.py")
d2diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d2diff)


def test_classifier_accepts_a_contract_valid_frame():
    """18-byte, opcode 0x02, correct checksum -> a valid button-test frame."""
    body = [0xA5, 0x12, 0x02, 0x00, 0x00, 0x00, 0x01] + [0x00] * 10
    chk = sum(body) & 0xFF
    frame = bytes(body + [chk])
    assert len(frame) == 18
    assert d2diff.classify(frame) == "valid_status"


def test_classifier_rejects_the_five_byte_d2_echo():
    """The D2 transaction echo must never count as streaming."""
    for echo in (bytes.fromhex("a505d2017d"), bytes.fromhex("a505d2007c")):
        assert d2diff.classify(echo) == "d2_echo"


def test_classifier_rejects_the_0b_control_reply():
    """The 0B sanity reply is legitimate for 0B but is not a button frame."""
    assert d2diff.classify(bytes.fromhex("a5050b30e5")) == "wrong_length_5"


def test_classifier_rejects_wrong_opcode_and_bad_checksum():
    body = [0xA5, 0x12, 0x0B, 0x00, 0x00, 0x00, 0x01] + [0x00] * 10
    assert d2diff.classify(bytes(body + [sum(body) & 0xFF])).startswith("opcode_0x")
    body = [0xA5, 0x12, 0x02, 0x00, 0x00, 0x00, 0x01] + [0x00] * 10
    assert d2diff.classify(bytes(body + [(sum(body) + 1) & 0xFF])) == "checksum_mismatch"


def test_recorded_experiment_is_the_expected_case_6():
    """The live run found no streaming variant: CASE 6, D2-U-007 still unknown."""
    exp = json.loads((REPO / "results/experiments/d2-live-differential-20260927-184643/experiment.json").read_text())
    assert exp["classification"] == "CASE 6 - none succeed"
    assert exp["config_baseline_match"] is True
    assert exp["final_d6_sha256"] == "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"
    assert "D2-U-007 REMAINS UNKNOWN" in exp["verdict"]
    for case, d in exp["cases"].items():
        assert d["valid_status_frames"] == 0, case
    # the ATT-verified write type for variant A, i.e. hypothesis A really was exercised
    a = [w for w in exp["att_windows"] if w["window"].startswith("A ")][0]
    assert "Write Request (0x12)" in a["d2_enable_att_op"]


def test_durability_vocabulary_not_regressed():
    """Immediate readback must never be described as durable persistence."""
    for name in ("results/final/real-config-durability.md",
                 "results/final/real-armorx-restore-validation.md",
                 "results/final/real-armorx-master-report.md"):
        text = (REPO / name).read_text()
        assert "STAGED_OK" in text and "DURABLE_OK" in text, name
    verdict = (REPO / "results/experiments/d2-live-differential-20260927-184643/verdict.md").read_text()
    assert "DURABLE_OK" in verdict
    assert "STAGED_OK" in verdict or "integrity" in verdict
