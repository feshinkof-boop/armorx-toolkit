"""Guards for the 2026-09-28 live C0 physical test.

Two things must not silently regress:

1. **C0 must run as C0.** It was excluded from the declarative path and fell through to a legacy inline
   branch that wrote D2_ON directly - no pre-clear, no operator prompt - so it could not answer the
   question it was named after. The first run in the experiment directory is that branch.
2. **The measured result must stay what it was.** If a later edit or a re-analysis quietly changes the
   numbers, the claim "the pre-clear is not a gate" loses its support.
"""
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
EXP = REPO / "results/experiments/d2-c0-physical-20260928-054549"
BASELINE_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"
D2_OFF = "a505d2007c"
D2_ON = "a505d2017d"


# ------------------------------------------------------------------ the fix that made the test valid

def test_c0_is_routed_through_the_declarative_cases():
    src = (REPO / "automation/scripts/d2-differential.py").read_text()
    assert 'if case in ("C0", "C1", "C2")' in src, (
        "C0 must use its declarative definition (pre-clear + operator prompt), not the legacy inline "
        "branch that omitted both")


def test_recorder_records_a_run_id_so_two_runs_cannot_be_spliced():
    src = (REPO / "automation/scripts/d2-differential.py").read_text()
    assert "run_id" in src and "run_start" in src


def test_the_operator_dialog_offers_an_explicit_cancel():
    src = (REPO / "automation/operator-dialog-kdialog.sh").read_text()
    assert "--cancel" in src and "yesno" in src
    cases = (REPO / "automation/scripts/d2_cases.py").read_text()
    assert "CANCEL / STOP" in cases


# ------------------------------------------------------------------ the measured evidence

def _records():
    f = EXP / "tx-rx.jsonl"
    if not f.exists():
        pytest.skip("live C0 capture not present in this checkout")
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


def test_the_press_produced_a_full_a_twice_sequence_on_bit_0_only():
    recs = _records()
    import sys
    sys.path.insert(0, str(REPO / "automation/scripts"))
    from armorx_lab.frames import parse_button_frame

    valid = []
    for r in recs:
        if r.get("dir") != "RX":
            continue
        b = bytes.fromhex(r["hex"])
        if len(b) == 18 and b[0] == 0xA5 and b[2] == 0x02:
            f = parse_button_frame(b)
            assert f is not None and f.checksum_ok, "every captured button frame must checksum"
            valid.append(f.mask)

    assert len(valid) == 167, f"expected 167 valid frames, got {len(valid)}"
    assert sum(1 for m in valid if m != 0) == 25
    assert {m for m in valid if m != 0} == {1}, "only bit 0 (A) may be set"

    states, prev = [], None
    for m in valid:
        bit = m & 1
        if prev is None or bit != prev:
            states.append(bit)
        prev = bit
    assert states == [1, 0, 1, 0], f"expected PRESS/RELEASE/PRESS/RELEASE, got {states}"


def _runs(recs):
    """Split a capture file into runs.

    Records carry `run_id` from 2026-09-28 onward. For files written before that, `monotonic_s`
    restarts per process, so a decrease is the splicing boundary. Both are handled so the guard works
    against historic captures too.
    """
    out, cur = [], []
    for r in recs:
        if r.get("kind") == "run_start":
            if cur:
                out.append(cur)
            cur = []
            continue
        if cur and r.get("monotonic_s") is not None and cur[-1].get("monotonic_s") is not None \
                and r["monotonic_s"] < cur[-1]["monotonic_s"]:
            out.append(cur)
            cur = []
        cur.append(r)
    if cur:
        out.append(cur)
    return out


def test_the_run_that_streamed_had_the_pre_clear_and_the_post_disable():
    """The whole point: the pre-clear was PRESENT in the streaming run."""
    recs = _records()
    runs = _runs(recs)
    assert len(runs) >= 1
    # the valid run is the last one; the earlier one is the legacy branch (no pre-clear, no prompt)
    run = runs[-1]
    tx = [r["hex"] for r in run if r.get("dir") == "TX"]
    assert tx[0] == "a5040bb4", "sanity query first"
    assert D2_OFF in tx and D2_ON in tx
    assert tx.index(D2_OFF) < tx.index(D2_ON), "the pre-clear must precede the enable"
    assert tx[-1] == D2_OFF, "the final action must be D2 disable"


def test_operator_ack_for_the_c0_press_exists_and_is_the_only_channel():
    ack = REPO / "results/runtime/operator-actions/armorx_d2_causal_c0_a_twice.json"
    if not ack.exists():
        pytest.skip("operator ack not present in this checkout")
    rec = json.loads(ack.read_text())
    assert rec["status"] == "ACK" and rec["response"] == "done"
    assert rec["title"] == "ArmorX D2 C0 Test"
    assert "2026-09-28" in rec["clicked_at"]


def test_post_test_integrity_read_matches_the_canonical_baseline():
    f = EXP / "post-integrity-d6.json"
    if not f.exists():
        pytest.skip("integrity read not present in this checkout")
    d = json.loads(f.read_text())
    assert d["sha256"] == BASELINE_SHA
    assert d["match"] is True
    assert d["image_bytes"] == 144
    # the read must be described as an integrity check, never as a durability proof
    assert "durability" in d["note"].lower() and "not a durability proof" in d["note"].lower()


def test_the_result_document_states_the_decision_tree_outcome():
    doc = (EXP / "RESULT.md").read_text().lower()
    assert "c0_streams_with_preclear" in doc
    assert "c1 and c2 were not run" in doc
    # and it must state the HCI capture limitation rather than imply full coverage
    assert "coverage limitation" in doc
