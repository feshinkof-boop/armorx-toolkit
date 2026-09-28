"""Guards for the corrected D2-U-007 finding: the harness is not silent.

The project spent hours treating "0 frames on the harness" as a device-level difference. The raw
session record shows the harness receiving 3,292 valid button frames when a key was actually pressed,
and the operator-action log shows the windows read as "silent" had no press requested at all.

These tests pin that down from primary evidence so the wrong reading cannot quietly return.
"""
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))

import importlib.util

spec = importlib.util.spec_from_file_location("hsa", REPO / "automation/scripts/harness-streaming-audit.py")
hsa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hsa)

STREAMING_RUN = REPO / "results/experiments/physical-20260927-170844-d2/session.jsonl"
ACTIONS = REPO / "results/runtime/operator-actions.jsonl"
PRESS_GROUPS = REPO / "results/runtime/press-groups.jsonl"


@pytest.fixture(scope="module")
def audited():
    if not STREAMING_RUN.exists():
        pytest.skip("the 17:08 streaming session record is not in this checkout")
    return hsa.audit(str(STREAMING_RUN))


def test_the_harness_received_real_button_frames(audited):
    assert audited["button_frames"] == 3292
    assert audited["button_frame_lengths"] == {18: 3292}  # in-process audit uses int keys
    assert audited["checksums_all_valid"] is True
    assert audited["conclusion"] == "harness_receives_button_frames"


def test_those_frames_cover_26_key_ids_including_the_boundary_ones(audited):
    ids = set(audited["key_ids_seen"])
    assert audited["key_id_count"] == 26
    for expected in (0, 1, 3, 4, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26,
                     27, 28, 29, 30):
        assert expected in ids, expected
    # id 9 (RT) is the known negative on this unit and must not appear
    assert 9 not in ids
    # held/idle cadence: most frames in the window carry a zero mask
    assert audited["zero_mask_frames"] > audited["nonzero_mask_frames"]


def test_the_streaming_configuration_had_no_d2_pre_clear(audited):
    frames = [c["frame"] for c in audited["control_plane"]]
    assert frames == ["a5040bb4", "a505d2017d", "a505d2007c"], frames
    assert audited["d2_enable_preceded_by_pre_clear"] is False
    assert audited["press_evidence_in_window"] is True


def test_no_press_was_requested_in_the_windows_that_looked_silent():
    """Press requests exist only for the 17:09-17:15 windows - never for the differential runs."""
    if not PRESS_GROUPS.exists():
        pytest.skip("press-group log not present")
    groups = [json.loads(l) for l in PRESS_GROUPS.read_text().splitlines() if l.strip()]
    assert groups, "the 17:08 run did request presses"
    for g in groups:
        assert g["requested_timestamp"].startswith("2026-09-27T17:"), g

    ids = set()
    if ACTIONS.exists():
        for line in ACTIONS.read_text(errors="replace").splitlines():
            m = re.search(r'"action_id": "([^"]+)"', line)
            if m:
                ids.add(m.group(1))
    # the press requests live in press-groups.jsonl, not in operator-actions.jsonl
    press_ids = {g["action_id"] for g in groups}
    assert press_ids and all(i.startswith("press_group_") for i in press_ids), press_ids
    # and the windows that looked silent asked only for power/setup actions
    assert not any(i.startswith("press_group_") for i in ids), sorted(i for i in ids if "press" in i)
    for forbidden in ("armorx_d2_diff_press", "armorx_harness_press"):
        assert forbidden not in ids


def test_the_reclassification_is_recorded_in_the_documents():
    verdict = (REPO / "results/experiments/official-vs-harness-session-20260927-190741/verdict.md").read_text()
    diff = (REPO / "results/experiments/official-vs-harness-session-20260927-190741/official-vs-harness-diff.md").read_text()
    recon = (REPO / "results/reconciliation/d2-u007-harness-streaming-reconciliation.md")
    assert recon.exists()
    body = recon.read_text()
    assert "HARNESS_STREAMS_UNDER_PRESS__DIFFERENTIAL_WINDOWS_WERE_NOT_PRESS-MATCHED" in body
    for doc in (verdict, diff):
        assert "DATED CORRECTION" in doc
        assert "not press-matched" in doc.lower() or "no physical press" in doc.lower()


def test_the_analysis_script_is_reproducible(audited):
    """Re-running the audit must give the same numbers (no drift between runs)."""
    again = hsa.audit(str(STREAMING_RUN))
    assert again == audited
