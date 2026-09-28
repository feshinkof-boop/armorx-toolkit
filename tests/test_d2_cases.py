"""Offline tests for the C0 / C1 / C2 D2 case definitions.

No hardware is touched. These tests exist so that tomorrow's live run cannot be sabotaged by a
mis-typed case: the sequence, the write whitelist and the (corrected) success semantics are all
asserted here first.

Context: on 2026-09-27 the official 4.0.8 app was captured sending EF, 0B, E2, D4 and a full D6
configuration read before enabling D2, and never pre-clearing D2 the way this harness does. C0/C1/C2
separate those variables. Button frames are EVENT-DRIVEN: zero idle frames is normal.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))

import d2_cases as C  # noqa: E402

FX = json.loads((REPO / "tests/vectors/official-button-test-fixtures.json").read_text())

# Every command byte-string the harness is allowed to put on the wire in these cases. Anything else
# is a design change and must fail this test on purpose.
ALLOWED_WRITES = {
    bytes.fromhex(FX["commands"]["0B_query"]["bytes"]),
    bytes.fromhex(FX["commands"]["EF_query"]["bytes"]),
    bytes.fromhex(FX["commands"]["E2_query"]["bytes"]),
    bytes.fromhex(FX["commands"]["D4_query"]["bytes"]),
    bytes.fromhex(FX["commands"]["D6_query"]["bytes"]),
    bytes.fromhex(FX["commands"]["D2_enable"]["bytes"]),
    bytes.fromhex(FX["commands"]["D2_disable"]["bytes"]),
}


def steps(case):
    return C.sequence(case)


def writes(case):
    return [bytes.fromhex(s["frame"]) for s in steps(case) if s["op"] == "write"]


def test_all_three_cases_exist_and_are_documented():
    assert set(C.CASES) == {"C0", "C1", "C2"}
    for case, meta in C.CASES.items():
        assert meta["description"] and meta["isolates"]
        assert isinstance(meta["pre_clear"], bool) and isinstance(meta["read_burst"], bool)


def test_only_the_single_intended_variable_changes_between_cases():
    t = C.truth_table()
    assert t["C0"] == {"pre_clear": True, "read_burst": False}
    assert t["C1"] == {"pre_clear": False, "read_burst": False}
    assert t["C2"] == {"pre_clear": False, "read_burst": True}
    # C1 differs from C0 only by the pre-clear; C2 differs from C1 only by the burst
    assert writes("C0") == [C.D2_OFF, C.D2_ON]
    assert writes("C1") == [C.D2_ON]
    assert writes("C2") == [C.EF_QUERY, C.GET_VERSION, C.E2_QUERY, C.D4_QUERY, C.D6_QUERY, C.D2_ON]


def test_c2_pre_burst_matches_the_official_capture_byte_for_byte():
    fixt = {k: bytes.fromhex(v["bytes"]) for k, v in FX["commands"].items()}
    assert writes("C2")[0:5] == [fixt["EF_query"], fixt["0B_query"], fixt["E2_query"],
                                 fixt["D4_query"], fixt["D6_query"]]
    assert writes("C2")[-1] == fixt["D2_enable"]


def test_every_case_ends_by_observing_and_is_bracketed_by_preflight():
    for case in C.CASES:
        seq = steps(case)
        assert seq[-1]["op"] == "observe", case
        assert seq[0]["op"] == "sanity", case
        assert sum(1 for s in seq if s["op"] == "observe") == 1, case


def test_only_whitelisted_frames_can_be_written():
    for case in C.CASES:
        for w in writes(case):
            assert w in ALLOWED_WRITES, (case, w.hex())
            assert len(w) >= 4 and w[0] == 0xA5
            assert (sum(w[:-1]) & 0xFF) == w[-1], f"checksum drift in {w.hex()}"


def test_config_read_waits_for_nine_full_fragments():
    """The D6 read is ten reply frames; the harness waits for the nine full ones (the tenth is short).

    CORRECTED 2026-09-27: the read is 10 frames / 144 bytes, not 8.
    """
    wf = [s for s in steps("C2") if s["op"] == "wait_fragments"]
    assert len(wf) == 1
    assert wf[0]["prefix"] == "a414d6" and wf[0]["expect_min"] == 9
    assert 0 < wf[0]["seconds"] <= 10
    frags = FX["d6_fragments"]
    assert len(frags) == 10
    assert sum(1 for f in frags if f["bytes"].startswith("a414d6")) == 9
    assert sum(1 for f in frags if f["bytes"].startswith("a40ed6")) == 1


def test_success_criteria_use_the_corrected_event_driven_semantics():
    sc = C.SUCCESS_CRITERIA
    assert "event-driven" in sc["zero_idle_frames"].lower()
    assert "NORMAL" in sc["zero_idle_frames"]
    assert "not a failure" in sc["zero_idle_frames"].lower().replace("is not", "not")
    assert sc["physical_action_required"] is True
    assert "PRESS, RELEASE, PRESS, RELEASE" in sc["strong"]
    assert "18-byte" in sc["minimum"]


def test_cases_never_write_configuration_or_other_forbidden_families():
    """D7/D8/FC/AB/macro/OTA/firmware families must never appear in these cases."""
    forbidden_opcodes = {0xD7, 0xD8, 0xFC, 0xAB, 0xE1, 0x0E}
    for case in C.CASES:
        for w in writes(case):
            assert w[2] not in forbidden_opcodes, (case, w.hex())
    # and the D2 toggle is the only state-changing write allowed here
    for case in C.CASES:
        stateful = [w for w in writes(case) if w[2] == 0xD2]
        assert stateful, case


def test_sequence_is_pure_and_repeatable():
    a, b = C.sequence("C2"), C.sequence("C2")
    assert a == b
    a[0]["op"] = "mutated"
    assert C.sequence("C2")[0]["op"] == "sanity", "callers must not be able to corrupt the definition"


def test_unknown_case_is_rejected():
    with pytest.raises(ValueError):
        C.sequence("C9")


# ---------------------------------------------------------------- operator contract (Part 12)

def test_every_causal_case_asks_for_exactly_one_operator_action():
    for case in C.CASES:
        prompts = [st for st in steps(case) if st["op"] == "operator_prompt"]
        assert len(prompts) == 1, case
        pr = prompts[0]
        assert pr["button"] == "DONE" and pr["cancel_button"] == "CANCEL"
        assert pr["action_id"].startswith("armorx_d2_causal_")
        assert len(pr["action_id"]) > 10


def test_operator_prompt_wording_matches_the_agreed_contract_exactly():
    """ONE popup, ONE sound, ONE action, click = ACK. The text must not drift."""
    for case in C.CASES:
        msg = [st for st in steps(case) if st["op"] == "operator_prompt"][0]["message"]
        assert msg == C.A_TWICE_MESSAGE
        assert "TWICE" in msg
        assert "Do not press any other controller button" in msg
        assert msg.strip().endswith("click DONE.")


def test_prompt_comes_after_d2_enable_and_before_the_observation_window():
    """The presses must happen while D2 is streaming, so ordering is part of the test."""
    for case in C.CASES:
        seq = steps(case)
        i_enable = max(i for i, st in enumerate(seq)
                       if st["op"] == "write" and st.get("frame") == C.D2_ON.hex())
        i_prompt = [i for i, st in enumerate(seq) if st["op"] == "operator_prompt"][0]
        i_observe = [i for i, st in enumerate(seq) if st["op"] == "observe"][0]
        assert i_enable < i_prompt < i_observe, case


def test_no_case_uses_chat_acknowledgement_or_a_repeating_alert():
    """The historical repeating-alert / chat-response design must not come back.

    Checked structurally rather than by keyword: the only interaction must be the single
    click-to-acknowledge popup, and nothing in the sequence may wait on, or ask for, a chat reply.
    """
    allowed_ops = {"sanity", "write", "sleep", "wait_fragments", "cccd_renew", "operator_prompt", "observe"}
    for case in C.CASES:
        for st in steps(case):
            assert st["op"] in allowed_ops, (case, st["op"])
    # the acknowledged channel is the popup click, and it is stated as such
    assert "click = ACK" in C.SUCCESS_CRITERIA["operator_prompt"]
    assert "never chat" in C.SUCCESS_CRITERIA["operator_prompt"]
    # there is exactly one notification-producing mechanism (the popup), never a sound loop
    src_prompt = C.A_TWICE_MESSAGE.lower()
    for bad in ("every minute", "repeat", "loop", "remind"):
        assert bad not in src_prompt, bad


def test_cancel_returns_the_device_to_a_safe_state():
    """The harness must attempt D2 disable on the cancel path (static check of the sources)."""
    script = (REPO / "automation/scripts/d2-differential.py").read_text()
    runner = (REPO / "automation/scripts/d2_runner.py").read_text()
    assert "OperatorCancelled" in script and "OperatorCancelled" in runner
    assert "D2 disable (operator cancel path)" in script
    assert "OPERATOR_CANCELLED" in script
    # the prompt must be awaited asynchronously, not blocking the notify loop
    assert "create_subprocess_exec" in runner and "proc.wait()" in runner
    # and the executor must not depend on a BLE stack, so it stays offline-testable
    assert "from bleak" not in runner and "import bleak" not in runner
