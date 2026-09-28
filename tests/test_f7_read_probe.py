#!/usr/bin/env python3
"""Tests for the live F7 read probe (2026-09-28, read-only).

Pins: the verdict and its controls, the runner's read-only guarantee, the D6 integrity result, the
ledger/doc state, and - importantly - that silence was NOT promoted to F7_WRITE_ONLY.
"""

import json
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
EXP = REPO / "results/experiments/f7-read-live-20260928-074652"
RUNNER = REPO / "automation/scripts/f7-read-probe.py"
BASELINE_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"


def _an():
    return json.loads((EXP / "analysis.json").read_text())


def _nots():
    return json.loads((EXP / "notifications.json").read_text())


def test_artifacts_present():
    for name in ("RESULT.md", "analysis.json", "notifications.json", "tx.json", "session.jsonl",
                 "btmon.btsnoop", "btmon.txt"):
        assert (EXP / name).exists(), f"missing {name}"
    assert (EXP / "post-integrity-d6" / "post-integrity-d6.json").exists()


def test_verdict_is_the_briefs_case_3():
    assert _an()["verdict"] == "F7_NO_REPLY_LINK_HEALTHY"


def test_both_f7_attempts_received_zero_frames():
    an = _an()
    assert an["phases"]["C_f7_attempt1"]["tx"] == "A5 04 F7 A0"
    assert an["phases"]["C_f7_attempt1"]["frames"] == []
    assert an["phases"]["C_f7_attempt1"]["window_s"] == 3.0
    assert an["phases"]["E_f7_attempt2"]["frames"] == []
    assert an["phases"]["E_f7_attempt2"]["window_s"] == 5.0


def test_controls_were_healthy_before_between_and_after():
    p = _an()["phases"]
    assert p["A_0B_pre"]["healthy"] is True
    assert p["D_0B_after_f7_1"]["healthy"] is True
    assert p["D_0B_after_f7_1"]["other_frames"] == []      # no delayed F7 frame either
    assert p["F_0B_final"]["healthy"] is True
    assert p["B_FC_control"]["status"] == "FC_READ_CONTROL_PASS"
    assert p["F_FC_final"]["status"] == "FC_READ_CONTROL_PASS"


def test_exactly_the_expected_notifications_and_none_from_f7():
    n = _nots()
    assert len(n) == 5
    assert [x["raw"] for x in n] == ["A5 05 0B 30 E5", "A5 05 FF FC A5", "A5 05 0B 30 E5",
                                     "A5 05 0B 30 E5", "A5 05 FF FC A5"]
    assert all(x["checksum_ok"] and x["declared_len_ok"] for x in n)
    assert all(x["phase"] in ("A", "B", "D", "F") for x in n), "no notification may belong to C or E"
    assert all(x["from_tx_s"] < 0.1 for x in n)            # every control answered in <100 ms
    counts = _an()["counts"]
    assert counts["notifications_total"] == 5 and counts["tx_total"] == 7
    assert counts["distinct_rx"] == ["A5 05 0B 30 E5", "A5 05 FF FC A5"]


def test_hci_capture_shows_the_exact_interleaved_sequence():
    """The decisive HCI evidence: each F7 write is followed by the *next control's* write, with no
    notification between - i.e. the two F7 attempts produced nothing at all on the wire."""
    txt = (EXP / "btmon.txt").read_text()
    assert "Connection Complete" in txt and "Disconnect Complete" in txt
    frames = [f for f in re.findall(r"Data\[\d\]: ([0-9a-f]{8,10})", txt)
              if f in ("a5040bb4", "a505fc8026", "a504f7a0", "a5050b30e5", "a505fffca5")]
    assert frames == ["a5040bb4", "a5050b30e5", "a505fc8026", "a505fffca5",
                      "a504f7a0", "a5040bb4", "a5050b30e5",
                      "a504f7a0", "a5040bb4", "a5050b30e5",
                      "a505fc8026", "a505fffca5"], frames
    body = frames[4:10]
    assert body == ["a504f7a0", "a5040bb4", "a5050b30e5", "a504f7a0", "a5040bb4", "a5050b30e5"], body
    # neither F7 write is followed by a notification before the next control write
    for i, f in enumerate(body):
        if f == "a504f7a0":
            assert body[i + 1] == "a5040bb4", "an F7 write must be followed by the next control"


def test_runner_is_read_only_by_construction():
    """The only frames the runner can build or send are the three read-only requests."""
    src = RUNNER.read_text()
    allowed = re.findall(r'Q_\w+ = bytes\.fromhex\("([0-9A-Fa-f]+)"\)', src)
    assert allowed == ["A5040BB4", "A505FC8026", "A504F7A0"], allowed
    assert "REFUSING to send a frame outside the read-only allow-list" in src
    assert "await self.client.write_gatt_char(FFE1, frame, response=False)" in src
    # exactly one write call site, and it is fed only by send()'s allow-list-checked frame
    assert src.count("write_gatt_char") == 1
    # no write-family opcode appears as a frame literal anywhere in the runner
    literals = set(re.findall(r'bytes\.fromhex\("([0-9A-Fa-f]+)"\)', src))
    assert not any(lit[4:6] in ("07", "08") for lit in literals)


def test_silence_was_not_promoted_to_write_only():
    assert "F7_WRITE_ONLY" in _an()["notes"]
    res = (EXP / "RESULT.md").read_text()
    assert "F7_NO_REPLY_LINK_HEALTHY" in res
    assert "NOT `F7_WRITE_ONLY`" in res or "is NOT `F7_WRITE_ONLY`" in res
    pc = (REPO / "results/final/real-armorx-protocol-contract.md").read_text()
    assert "F7_WRITE_ONLY" in pc and "NOT claimed" in pc


def test_d6_integrity_matched_and_is_not_called_durability():
    integ = json.loads((EXP / "post-integrity-d6" / "post-integrity-d6.json").read_text())
    assert integ["sha256"] == BASELINE_SHA and integ["match"] is True
    res = (EXP / "RESULT.md").read_text()
    assert "CONFIG_BASELINE_MATCH" in res
    assert "not** a new durability proof" in res or "NOT a new durability proof" in res


def test_trigger_travel_refutation_is_preserved_with_dated_provenance():
    t = (REPO / "results/final/real-trigger-travel.md").read_text()
    assert "CONTRADICTED" in t and "步长精度" in t
    assert "F7_NO_REPLY_LINK_HEALTHY" in t


def test_ledger_reflects_the_live_result():
    d = json.loads((REPO / "results/reconciliation/master-unknown-ledger.json").read_text())
    ids = {e.get("id"): e for e in d["entries"]}
    assert ids["TRG-U-001"]["status"] == "PARTIALLY_RESOLVED"
    assert "F7_WRITE_ONLY is explicitly NOT concluded" in ids["TRG-U-001"]["ruled_out"]
    assert ids["TRG-U-003"]["status"] == "OPEN"
    assert ids["TRG-U-003"]["classification"] == "DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE"
