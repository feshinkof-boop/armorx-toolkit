#!/usr/bin/env python3
"""Tests for the one-variable RT bit-9 confirmation (2026-09-28).

Pins: the W0/W1/W2 result and its verdict, the canonical RT mapping (digital 9 / mask 0x200 / analog
byte 16), the LT counterpart (digital 8 / analog byte 15), the negative branches of the classifier, and
the two harness bugs that voided attempt 1 (a shared notification bucket, and restarting btmon under a
live connection).
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))
from armorx_lab.analog_analysis import (              # noqa: E402
    classify_bit9_confirmation, window_bit_stats, RT_BIT_ID,
)

C = REPO / "results/experiments/rt-bit9-confirmation-20260928-063300"
RUNNER = REPO / "automation/scripts/rt-bit9-confirm.py"
RT_MASK = 1 << RT_BIT_ID


def mk(t, mask, lt=0, rt=0):
    return {"t": t, "mask": mask, "bits": [i for i in range(32) if mask >> i & 1], "lt": lt, "rt": rt,
            "hex": "00"}


def win(pf):
    return {"per_frame": pf}


A = 1


# ---------------------------------------------------------------- the real result

def test_real_windows_show_absent_present_absent():
    st = {w: window_bit_stats(json.loads((C / f"result-{w}.json").read_text()), RT_BIT_ID)
          for w in ("w0", "w1", "w2")}
    # W0: control, bit 9 absent, analog at rest
    assert st["w0"]["valid_frames"] == 228 and st["w0"]["bit_frames"] == 0
    assert st["w0"]["bits_seen"] == [0] and st["w0"]["rt_range"] == [0, 0]
    # W1: RT held, bit 9 present through the holds, analog high
    assert st["w1"]["valid_frames"] == 263 and st["w1"]["bit_frames"] == 184
    assert st["w1"]["bits_seen"] == [0, 9] and st["w1"]["rt_range"] == [0, 255]
    assert st["w1"]["bit_9_holds"] == 2
    # W2: control again, bit 9 gone, analog back at rest
    assert st["w2"]["valid_frames"] == 283 and st["w2"]["bit_frames"] == 0
    assert st["w2"]["bits_seen"] == [0] and st["w2"]["rt_range"] == [0, 0]


def test_real_verdict_is_the_proof_and_every_criterion_passes():
    res = json.loads((C / "RESULT.json").read_text())
    assert res["classification"]["verdict"] == "RT_DIGITAL_ID_9_PROVEN_LIVE"
    assert all(v is True for v in res["classification"]["criteria"].values()), \
        res["classification"]["criteria"]
    assert res["classification"]["rt_mask"] == RT_MASK == 0x00000200
    # no control other than A/RT moved anything in any window
    for w in ("w0", "w1", "w2"):
        st = window_bit_stats(json.loads((C / f"result-{w}.json").read_text()), RT_BIT_ID)
        assert st["unexpected_bits"] == []


def test_bit_9_clears_on_release_and_no_idle_frame_carries_it():
    r = json.loads((C / "result-w1.json").read_text())
    idle = [f for f in r["per_frame"] if f["mask"] == 0]
    assert idle, "idle frames must exist for the clearing claim to be observable"
    assert not any(f["mask"] & RT_MASK for f in idle)
    assert all(f["rt"] == 0 for f in idle)


def test_session_hygiene_d2_off_last_and_no_config_write():
    res = json.loads((C / "RESULT.json").read_text())
    assert res["tx"][0] == "a5040bb4" and res["tx"][1] == "a505d2017d"
    assert res["tx"][-1] == "a505d2007c", "the last runtime write must be D2 OFF"
    assert res["cancelled"] is False
    assert set(res["tx"]) == {"a5040bb4", "a505d2017d", "a505d2007c"}      # nothing else was sent


def test_every_window_has_verified_hci_coverage_this_time():
    res = json.loads((C / "RESULT.json").read_text())
    for w in ("W0", "W1", "W2"):
        cap = res["windows"][w]["capture"]
        assert cap["hci_coverage"] is True and cap["grew"] is True and cap["btmon_running"] is True
        assert cap["link_alive_after_window"] is True, "a dead link must never pass as 'no frames'"


# ---------------------------------------------------------------- negative branches

def _run(bit9_in_w0=False, bit9_in_w1=True, bit9_in_w2=False, rt_moves=True):
    def frames(bit9, rt):
        m = A | (RT_MASK if bit9 else 0)
        return [mk(0.0, 0, rt=0), mk(1.0, m, rt=rt), mk(1.1, m, rt=rt), mk(1.3, 0, rt=0),
                mk(4.0, m, rt=rt), mk(4.1, m, rt=rt), mk(4.3, 0, rt=0)]
    return (win(frames(bit9_in_w0, 0)), win(frames(bit9_in_w1, 255 if rt_moves else 0)),
            win(frames(bit9_in_w2, 0)))


def test_bit9_in_a_control_window_means_it_is_not_rt_specific():
    w0, w1, w2 = _run(bit9_in_w0=True)
    assert classify_bit9_confirmation(w0, w1, w2)["verdict"] == "BIT9_NOT_RT_SPECIFIC"


def test_bit9_missing_in_w1_means_the_association_was_not_reproduced():
    w0, w1, w2 = _run(bit9_in_w1=False)
    assert classify_bit9_confirmation(w0, w1, w2)["verdict"] == "BIT9_RT_ASSOCIATION_NOT_REPRODUCED"


def test_analog_must_move_with_the_bit_for_the_proof():
    w0, w1, w2 = _run(rt_moves=False)
    v = classify_bit9_confirmation(w0, w1, w2)
    assert v["criteria"]["5_rt_analog_moves_at_the_same_time"] is False
    assert v["verdict"] != "RT_DIGITAL_ID_9_PROVEN_LIVE"


def test_clean_synthetic_run_passes():
    w0, w1, w2 = _run()
    assert classify_bit9_confirmation(w0, w1, w2)["verdict"] == "RT_DIGITAL_ID_9_PROVEN_LIVE"


# ---------------------------------------------------------------- canonical mapping

def test_canonical_files_now_carry_rt_as_proven_live_id_9():
    km = json.loads((REPO / "results/final/key-map-confidence.json").read_text())
    row9 = next(r for r in km["rows"] if r["id"] == 9)
    assert row9["name"] == "RT" and row9["grade"] == "PROVEN LIVE"
    assert row9["static_constant"] == "0x00000200"
    assert km["counts"]["proven_live"] == 27
    assert "9" not in km["final_classification_of_unresolved"]
    canon = json.loads((REPO / "results/final/real-key-id-map.json").read_text())
    assert canon["proven_live_count"] == 27
    assert canon["proven_live"]["9"]["button"] == "RT"
    rt = canon["rt_mapping"]
    assert (rt["digital_id"], rt["digital_mask"], rt["analog_byte"]) == (9, "0x00000200", 16)
    assert rt["analog_observed_range"] == [0, 255]
    # the superseded negative survives as dated history
    assert "METHOD-LIMITED" in rt["superseded_history"]


def test_lt_and_rt_channel_pairing():
    """LT = digital 8 / analog byte 15; RT = digital 9 / analog byte 16. Only assert RT's name after proof."""
    from armorx_lab.analog_analysis import LT_INDEX, RT_INDEX
    assert (LT_INDEX, RT_INDEX) == (15, 16)
    canon = json.loads((REPO / "results/final/real-key-id-map.json").read_text())
    assert canon["proven_live"]["8"]["button"] == "LT"        # digital bit 8
    assert canon["proven_live"]["9"]["button"] == "RT"        # digital bit 9
    assert canon["rt_mapping"]["analog_byte"] == 16
    contract = (REPO / "results/reconciliation/d2-frame-contract.md").read_text().replace("`", "")
    assert "Mask bit 9 = RT, PROVEN LIVE" in contract


# ---------------------------------------------------------------- the attempt-1 bugs stay fixed

def test_runner_does_not_restart_btmon_under_a_live_connection():
    src = RUNNER.read_text()
    loop = src[src.index("for tag, action, title, msg in WINDOWS"):src.index("finally:")]
    assert "cap.start(" not in loop, "restarting btmon mid-connection kills the link (attempt 1)"
    assert "cap.before_window(" in loop, "coverage must still be measured per window"


def test_runner_tags_frames_with_the_window_they_arrived_in():
    src = RUNNER.read_text()
    assert 'current["window"] = tag' in src
    assert 'bucket = tracks[current["window"] or "W0"]' in src
    # the specific old bug: subscribing once with a fixed bucket
    assert 'start_notify(FFE2, make_notify(tracks["W0"]))' not in src


def test_attempt_1_is_preserved_as_evidence():
    a1 = C / "attempt-1-link-lost"
    assert (a1 / "NOTE.md").exists()
    note = (a1 / "NOTE.md").read_text()
    assert "HCI" in note
    assert "user channel" in note
    assert "no hci coverage" in note.lower()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
