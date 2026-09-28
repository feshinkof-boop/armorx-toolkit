"""Offline tests for the causal case executor (automation/scripts/d2_runner.py).

No adapter, no device, no popup, no operator: the executor is driven with a fake client and a fake
prompt command, so every branch - including the CANCEL path and the "no frames" outcome - is
exercised here rather than being discovered live tomorrow.
"""
import asyncio
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))

import d2_cases as C  # noqa: E402
import d2_runner as R  # noqa: E402

FIX = json.loads((REPO / "tests/vectors/official-button-test-fixtures.json").read_text())


class FakeRecorder:
    """Mimics the subset of Recorder that run_steps touches."""

    def __init__(self):
        self.frames = []
        self.events = []
        self.writes = []

    def mark(self, event, detail=""):
        self.events.append((event, detail))
        return 0.0

    def log(self, direction, uuid, payload, **extra):
        if direction == "TX":
            self.writes.append((bytes(payload), extra.get("label", ""), extra.get("write_mode", "")))
        return 0.0

    def on_notify(self, _char, data):
        raw = bytes(data)
        self.frames.append({"hex": raw.hex(), "kind": "valid_status" if len(raw) == 18 else "other",
                            "mask": None, "keys": None})


class FakeClient:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    async def write_gatt_char(self, uuid, frame, response=False):
        if self.fail_on and frame == self.fail_on:
            raise RuntimeError("write failed")
        self.calls.append((uuid, bytes(frame), response))

    async def stop_notify(self, uuid):
        self.calls.append(("stop_notify", uuid))

    async def start_notify(self, uuid, cb):
        self.calls.append(("start_notify", uuid))


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setenv("D2_OBSERVE_S", "0.05")
    monkeypatch.setattr(R, "PROMPT_COMMAND", ["true"])   # 'true' exits 0 = operator clicked DONE


def test_c1_writes_only_d2_enable(monkeypatch):
    rec, cli = FakeRecorder(), FakeClient()
    run(R.run_steps(cli, rec, [s for s in C.sequence("C1") if s["op"] != "sanity"]))
    assert [c[1].hex() for c in cli.calls] == [C.D2_ON.hex()]
    assert all(c[2] is False for c in cli.calls), "D2 must be written without response"
    assert any(e[0] == "operator_prompt_raised" for e in rec.events)
    assert any(e[0] == "observe_end" for e in rec.events)


def test_c2_writes_the_official_burst_then_d2_and_never_pre_clears(monkeypatch):
    rec, cli = FakeRecorder(), FakeClient()
    calls = 0

    async def fake_wait(self, uuid, frame, response=False):
        nonlocal calls
        calls += 1
        self.calls.append((uuid, bytes(frame), response))
        if frame == C.D6_QUERY:            # simulate the device answering with nine full frames
            for i in range(9):
                rec.frames.append({"hex": f"a414d6{i+1:02d}" + "00" * 15, "kind": "other", "mask": None, "keys": None})

    monkeypatch.setattr(FakeClient, "write_gatt_char", fake_wait)
    run(R.run_steps(cli, rec, [s for s in C.sequence("C2") if s["op"] != "sanity"]))
    written = [c[1].hex() for c in cli.calls]
    assert written == [C.EF_QUERY.hex(), C.GET_VERSION.hex(), C.E2_QUERY.hex(), C.D4_QUERY.hex(),
                       C.D6_QUERY.hex(), C.D2_ON.hex()]
    assert C.D2_OFF.hex() not in written, "C2 must not pre-clear D2"
    assert not any(e[0] == "fragments_received" and "0 " in e[1] for e in rec.events)


def test_operator_cancel_raises_and_stops_the_case(monkeypatch):
    monkeypatch.setattr(R, "PROMPT_COMMAND", ["false"])   # 'false' exits non-zero = CANCEL/STOP
    rec, cli = FakeRecorder(), FakeClient()
    with pytest.raises(R.OperatorCancelled):
        run(R.run_steps(cli, rec, [s for s in C.sequence("C1") if s["op"] != "sanity"]))
    # the enable went out (it precedes the prompt) but the case body stopped there
    assert [c[1].hex() for c in cli.calls] == [C.D2_ON.hex()]
    assert any(e[0] == "operator_cancelled" for e in rec.events)
    assert not any(e[0] == "observe_end" for e in rec.events), "must not continue after a cancel"


def test_observe_step_never_reports_failure_for_an_empty_window():
    rec, cli = FakeRecorder(), FakeClient()
    run(R.run_steps(cli, rec, [{"op": "observe"}]))
    detail = [e[1] for e in rec.events if e[0] == "observe_end"][0]
    assert "NORMAL" in detail and "not failure" in detail


def test_wait_fragments_times_out_without_hanging_and_records_the_shortfall():
    rec, cli = FakeRecorder(), FakeClient()
    run(R.run_steps(cli, rec, [{"op": "wait_fragments", "prefix": "a414d6", "expect_min": 9, "seconds": 0.05}]))
    got = [e[1] for e in rec.events if e[0] == "fragments_received"][0]
    assert got.startswith("0 "), got


def test_unknown_step_is_rejected():
    rec, cli = FakeRecorder(), FakeClient()
    with pytest.raises(RuntimeError):
        run(R.run_steps(cli, rec, [{"op": "do_something_new"}]))


# ---------------------------------------------------------------- verdict vocabulary

def frame(mask, key):
    return {"kind": "valid_status", "mask": f"0x{mask:08X}", "keys": key}


def test_verdict_calls_an_empty_window_normal_not_failed():
    v = R.verdict_from_frames([])
    assert v["verdict"] == "NO_IDLE_FRAMES_OBSERVED"
    assert "NOT a failure" in v["meaning"]


def test_verdict_recognises_a_twice():
    frames = [frame(1, [0]), frame(0, []), frame(1, [0]), frame(0, [])]
    v = R.verdict_from_frames(frames)
    assert v["verdict"] == "A_TWICE_PROVEN" and v["keys"] == [0] and v["transitions"] == 4


def test_verdict_recognises_frames_from_other_keys():
    v = R.verdict_from_frames([frame(1 << 3, [3])])
    assert v["verdict"] == "BUTTON_FRAMES_RECEIVED_OTHER_KEYS" and v["keys"] == [3]


def test_verdict_uses_the_official_capture_shape():
    """Sanity: the real official A-twice masks produce the strong verdict."""
    masks = [0x00000001, 0x00000000, 0x00000001, 0x00000000]
    frames = [frame(m, [0] if m else []) for m in masks]
    assert R.verdict_from_frames(frames)["verdict"] == "A_TWICE_PROVEN"


def test_the_executor_module_has_no_ble_dependency():
    """d2_runner must stay importable without bleak - that is why it exists."""
    src = (REPO / "automation/scripts/d2_runner.py").read_text()
    assert "import bleak" not in src and "from bleak" not in src
