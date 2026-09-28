#!/usr/bin/env python3
"""Tests for RT analog piggyback sampling: deterministic fixtures for every classification path,
plus assertions pinned to the real 2026-09-28 session artifacts."""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))
from armorx_lab.analog_analysis import (            # noqa: E402
    LT_INDEX, RT_INDEX, a_burst_segments, a_triggered, analyse_window, bytes_stats,
    classify_lt_control, classify_rt, compare,
)

SESSION = REPO / "results/experiments/rt-analog-piggyback-20260928-061800"
RUNNER = REPO / "automation/scripts/rt-analog-piggyback.py"


def mk(t, mask, lt=0, rt=0):
    return {"t": t, "mask": mask, "bits": [i for i in range(32) if mask >> i & 1],
            "lt": lt, "rt": rt, "hex": "00"}


def window(per_frame, masks=None):
    return {"per_frame": per_frame, "masks": masks or {}}


A = 1          # A held: bit 0
RT_BIT = 1 << 9
A_RT = A | RT_BIT


# ------------------------------------------------------------------ baseline extraction

def test_baseline_extraction_reports_measured_stats_not_assumptions():
    st = bytes_stats([0, 0, 0, 0, 0])
    assert st["n"] == 5 and st["mode"] == 0 and st["min"] == 0 and st["max"] == 0
    assert st["dominant"] == 0 and st["dominant_fraction"] == 1.0 and st["range"] == 0
    # a non-zero rest is reported as-is, never coerced to zero
    st2 = bytes_stats([90, 92, 90, 91])
    assert st2["mode"] == 90 and st2["min"] == 90 and st2["max"] == 92


def test_baseline_window_on_real_p0_is_zero_and_only_bit_0():
    r = json.loads((SESSION / "result-p0.json").read_text())
    w = analyse_window(r)
    assert r["valid_frames"] == 204
    assert w["bits_seen"] == [0]
    assert w["a_triggered_frames"] == 56
    assert w["a_triggered_lt"]["max"] == 0 and w["a_triggered_rt"]["max"] == 0
    assert w["a_triggered_rt"]["distinct"] == {"0": 56}


# ------------------------------------------------------------------ LT positive control

def test_lt_positive_control_detects_piggybacked_change():
    base = window([mk(0.1, A), mk(0.2, 0)])
    ctl = window([mk(0.1, A | 0x100, lt=255), mk(0.2, A | 0x100, lt=255), mk(0.3, 0, lt=0)])
    v = classify_lt_control(base, ctl)
    assert v["verdict"] == "LT_ANALOG_PIGGYBACK_PROVEN"
    assert v["lt"]["baseline_dominant"] == 0 and v["lt"]["window_dominant"] == 255
    assert v["rt_cross_check"]["verdict"] == "NO_CHANGE"


def test_lt_positive_control_invalidates_the_method_when_byte15_does_not_move():
    base = window([mk(0.1, A), mk(0.2, 0)])
    ctl = window([mk(0.1, A | 0x100, lt=0), mk(0.2, A | 0x100, lt=0)])
    assert classify_lt_control(base, ctl)["verdict"] == "D2_ANALOG_PIGGYBACK_METHOD_NOT_VALIDATED"


def test_lt_positive_control_requires_trigger_frames():
    v = classify_lt_control(window([mk(0.1, 0)]), window([mk(0.1, 0, lt=255)]))
    assert v["verdict"] == "INSUFFICIENT_FRAMES"


# ------------------------------------------------------------------ RT analog detection

def _rt_run(rt_value, bit9=True, bursts=2):
    """Two trigger bursts separated by a gap, each on `rt_value`, plus idle frames at rest."""
    mask = A_RT if bit9 else A
    idle = 0
    pf = [mk(0.0, idle, rt=0)]
    for i in range(bursts):
        base_t = 1.0 + i * 4.0
        pf += [mk(base_t, mask, rt=rt_value), mk(base_t + 0.05, mask, rt=rt_value)]
        pf += [mk(base_t + 0.2, idle, rt=0)]
    return window(pf)


def test_rt_analog_change_is_detected_and_named_analog_only_when_no_bit_appears():
    base = window([mk(0.1, A), mk(0.2, 0)])
    v = classify_rt(base, _rt_run(255, bit9=False))
    assert v["verdict"] == "RT_ANALOG_ONLY_PROVEN_LIVE"
    assert v["criteria"]["2_no_rt_digital_bit"] is True
    assert v["observed_range"] == [255, 255]


def test_verdict_must_not_say_analog_only_when_a_digital_bit_appeared():
    base = window([mk(0.1, A), mk(0.2, 0)])
    v = classify_rt(base, _rt_run(255, bit9=True))
    assert v["rt_digital_bit_observed"] is True
    assert v["criteria"]["2_no_rt_digital_bit"] is False
    assert v["verdict"] == "RT_ANALOG_PROVEN_LIVE__PLUS_DIGITAL_BIT_OBSERVED"
    assert "ANALOG_ONLY" not in v["verdict"]


def test_no_change_is_classified_negative_not_proven():
    base = window([mk(0.1, A), mk(0.2, 0)])
    v = classify_rt(base, _rt_run(0))
    assert v["verdict"] == "RT_ANALOG_NOT_OBSERVED_IN_D2_PIGGYBACK"
    assert v["criteria"]["3_byte16_moves_consistently"] is False


def test_a_single_stray_frame_cannot_carry_a_verdict():
    base = window([mk(0.1, A), mk(0.2, A), mk(0.3, A)])
    # 1 frame at 255 out of 5 -> dominant fraction 0.4 < 0.6 required
    stray = window([mk(0.1, A), mk(0.2, A), mk(0.3, A), mk(0.4, A), mk(0.5, A, rt=255)])
    assert compare("x", analyse_window(base)["a_triggered_rt"],
                   analyse_window(stray)["a_triggered_rt"])["verdict"] == "NO_CHANGE"


def test_repeat_requirement_needs_two_bursts_and_is_bit_independent():
    base = window([mk(0.1, A), mk(0.2, 0)])
    one_burst = window([mk(1.0, A_RT, rt=255), mk(1.05, A_RT, rt=255), mk(1.2, 0, rt=0)])
    v = classify_rt(base, one_burst)
    assert v["criteria"]["5_effect_repeats"] is False
    assert v["verdict"] == "RT_ANALOG_NOT_OBSERVED_IN_D2_PIGGYBACK"
    # bit-independence: the same burst split works with no digital bit at all
    segs = a_burst_segments(_rt_run(255, bit9=False)["per_frame"])
    assert len(segs) == 2 and all(s["rt_values"] == [255] for s in segs)
    assert a_triggered(_rt_run(255, bit9=False)["per_frame"])     # carriers still identified


# ------------------------------------------------------------------ real session artifacts

def test_real_lt_control_proven_and_real_rt_analog_proven():
    d = {n: json.loads((SESSION / f"result-{n}.json").read_text()) for n in ("p0", "p1", "p2", "p2r")}
    lt = classify_lt_control(d["p0"], d["p1"])
    assert lt["verdict"] == "LT_ANALOG_PIGGYBACK_PROVEN"
    assert lt["lt"]["window_dominant"] == 255 and lt["lt"]["window_dominant_fraction"] == 1.0
    rt = classify_rt(d["p0"], d["p2"], repeats=[d["p2r"]])
    assert rt["verdict"] == "RT_ANALOG_PROVEN_LIVE__PLUS_DIGITAL_BIT_OBSERVED"
    assert rt["criteria"] == {"1_a_frames_present": True, "2_no_rt_digital_bit": False,
                              "3_byte16_moves_consistently": True, "4_returns_to_baseline_at_rest": True,
                              "5_effect_repeats": True, "6_byte15_flat": True}
    assert (SESSION / "ANALYSIS.json").exists()


def test_every_trigger_caused_frame_in_the_rt_windows_carries_255_and_lt_stays_flat():
    for name in ("p2", "p2r"):
        r = json.loads((SESSION / f"result-{name}.json").read_text())
        trig = a_triggered(r["per_frame"])
        assert trig and all(f["rt"] == 255 for f in trig)
        assert all(f["lt"] == 0 for f in r["per_frame"])


def test_bit_9_appears_only_in_the_rt_windows_and_is_not_named():
    seen = {}
    for name in ("p0", "p1", "p2", "p2r"):
        r = json.loads((SESSION / f"result-{name}.json").read_text())
        seen[name] = 9 in [b for f in r["per_frame"] for b in f["bits"]]
    assert seen == {"p0": False, "p1": False, "p2": True, "p2r": True}
    # the session record itself must keep it unnamed
    doc = (SESSION / "RESULT.md").read_text()
    assert "NEW_BIT_9_OBSERVED_UNNAMED" in doc
    assert "id 9 = RT" not in doc and "bit 9 = RT" not in doc


def test_session_sent_no_configuration_write_and_d2_is_last():
    for name in ("p0", "p1", "p2", "p2r"):
        tx = json.loads((SESSION / f"result-{name}.json").read_text())["tx"]
        assert tx == ["a5040bb4", "a505d2017d", "a505d2007c"]
        assert tx[-1] == "a505d2007c", "the last write must be D2 OFF"


def test_frame_contract_offsets_are_the_ones_used():
    assert (LT_INDEX, RT_INDEX) == (15, 16)
    contract = (REPO / "results/reconciliation/d2-frame-contract.md").read_text().replace("`", "")
    assert "[15] LT analog" in contract and "[16] RT analog" in contract


def test_harness_helper_path_and_exit_codes():
    src = RUNNER.read_text()
    assert 'DIALOG = str(_HERE.parent / "operator-dialog-kdialog.sh")' in src
    assert (REPO / "automation/operator-dialog-kdialog.sh").exists()
    assert "DIALOG_MISSING" in src and "if rc == 1:" in src and "HARNESS_ERROR" in src
    assert "OPERATOR_CANCELLED" in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
