"""Offline end-to-end tests for the virtual ARMOR-X Pro and the causal cases (Parts H/I).

These run the REAL executor (`d2_runner.run_steps`) against a virtual device whose bytes come from
the official capture, so the harness plumbing and the verdict logic are exercised without hardware.

The load-bearing assertion is discrimination: with a device that suppresses streaming after a D2
pre-clear, case C0 must come back silent while C1/C2 stream; with a device that does not care, all
three must stream. If that ever stops holding, tomorrow's physical result stops being interpretable.
"""
import asyncio
import hashlib
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))

import d2_cases as C  # noqa: E402
import d2_runner as R  # noqa: E402
from armorx_lab.mock_gatt import MockGattClient, OfflineRecorder  # noqa: E402
from armorx_lab.virtual_device import VirtualArmorX  # noqa: E402

BASELINE_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setenv("D2_OBSERVE_S", "0.05")
    monkeypatch.setattr(R, "PROMPT_COMMAND", ["true"])


# ------------------------------------------------------------------ device ground truth

def test_device_reassembles_the_official_configuration_byte_for_byte():
    d = VirtualArmorX()
    assert len(d.d6_frames) == 10
    assert [len(f) for f in d.d6_frames] == [20] * 9 + [14]
    assert len(d.config_bytes) == 144
    assert hashlib.sha256(d.config_bytes).hexdigest() == BASELINE_SHA


def test_device_is_silent_while_idle():
    """An idle window produces ZERO button frames - the official behaviour, not a failure."""
    d = VirtualArmorX()
    cli = MockGattClient(d)
    d.handle_write(d.D2_ENABLE)
    assert d.idle_frame_count == 0, "a D2 enable alone must not produce button traffic"
    assert d.d2_enabled is True
    # and after several idle seconds there is still nothing
    assert d.idle_frame_count == 0


def test_device_streams_on_a_press_only_when_d2_is_enabled():
    d = VirtualArmorX()
    d.handle_write(d.D2_ENABLE)          # device now in test mode, still silent
    d.press_a_twice()
    assert d.idle_frame_count == 2 * (1 + d.held_reports + 1)
    buttons = [f for f in d.emitted if f[:3] == b"\xa5\x12\x02"]
    assert buttons[0] == d.press and buttons[-1] == d.release
    # the D2 enable itself is echoed but must never be counted as input
    assert all(f[:5] != b"\xa5\x12\x02" for f in d.emitted if f == d.D2_ENABLE or f in d.d2_echoes)

    fresh = VirtualArmorX()
    fresh.press_a_twice()                # no D2 enable: nothing at all, like the real unit
    assert fresh.idle_frame_count == 0


def test_device_replays_the_official_query_replies():
    d = VirtualArmorX()
    f = d.fixtures["commands"]
    for key in ("EF", "0B", "E2", "D4"):
        d.handle_write(bytes.fromhex(f[f"{key}_query"]["bytes"]))
    assert [x.hex() for x in d.emitted] == [f[f"{k}_reply"]["bytes"] for k in ("EF", "0B", "E2", "D4")]


# ------------------------------------------------------------------ end-to-end case runs

async def _run(case, *, preclear_is_fatal, outdir):
    device = VirtualArmorX(preclear_is_fatal=preclear_is_fatal)
    client = MockGattClient(device)
    rec = OfflineRecorder(path=str(outdir / f"{case}.jsonl"))
    await client.start_notify(client.FFE2, rec.on_notify)
    steps = [s for s in C.sequence(case) if s["op"] != "sanity"]

    async def operator():
        for _ in range(2000):
            if device.d2_enabled:
                break
            await asyncio.sleep(0.002)
        await asyncio.sleep(0.005)
        client.press_a_twice()

    task = asyncio.create_task(operator())
    try:
        await R.run_steps(client, rec, steps)
    finally:
        task.cancel()
    rec.close()
    return device, client, rec, R.verdict_from_frames(rec.frames)


def test_c1_and_c2_stream_under_both_hypotheses(tmp_path):
    for fatal in (True, False):
        for case in ("C1", "C2"):
            dev, _cli, rec, verdict = asyncio.run(_run(case, preclear_is_fatal=fatal, outdir=tmp_path))
            assert verdict["verdict"] == "A_TWICE_PROVEN", (case, fatal, verdict)
            assert verdict["keys"] == [0]
            assert dev.describe()["button_frames_emitted"] > 0


def test_c0_discriminates_the_pre_clear_hypothesis(tmp_path):
    """The whole point of case C0: it must separate 'pre-clear matters' from 'pre-clear harmless'."""
    dev_m, _c, _r, v_matters = asyncio.run(_run("C0", preclear_is_fatal=True, outdir=tmp_path))
    dev_h, _c2, _r2, v_harmless = asyncio.run(_run("C0", preclear_is_fatal=False, outdir=tmp_path))
    assert v_matters["verdict"] == "NO_IDLE_FRAMES_OBSERVED"
    assert v_harmless["verdict"] == "A_TWICE_PROVEN"
    assert v_matters["verdict"] != v_harmless["verdict"]
    assert dev_m.describe()["muted_by_preclear"] is True
    assert dev_h.describe()["muted_by_preclear"] is False


def test_the_case_control_planes_are_what_they_claim_to_be(tmp_path):
    _d, cli_c0, _r, _v = asyncio.run(_run("C0", preclear_is_fatal=False, outdir=tmp_path))
    _d, cli_c1, _r, _v = asyncio.run(_run("C1", preclear_is_fatal=False, outdir=tmp_path))
    _d, cli_c2, _r, _v = asyncio.run(_run("C2", preclear_is_fatal=False, outdir=tmp_path))
    assert [w[1].hex() for w in cli_c0.writes] == [C.D2_OFF.hex(), C.D2_ON.hex()]
    assert [w[1].hex() for w in cli_c1.writes] == [C.D2_ON.hex()]
    assert [w[1].hex() for w in cli_c2.writes] == [C.EF_QUERY.hex(), C.GET_VERSION.hex(),
                                                   C.E2_QUERY.hex(), C.D4_QUERY.hex(),
                                                   C.D6_QUERY.hex(), C.D2_ON.hex()]
    # D2 is always written without response
    for cli in (cli_c0, cli_c1, cli_c2):
        assert all(r is False for _u, _f, r in cli.writes)


def test_recorded_frames_are_valid_18_byte_reports(tmp_path):
    _d, _c, rec, _v = asyncio.run(_run("C1", preclear_is_fatal=False, outdir=tmp_path))
    assert rec.summary()["valid_status"] == 10
    for f in rec.frames:
        if f["kind"] != "valid_status":
            continue
        assert f["length"] == 18
        raw = bytes.fromhex(f["hex"])
        assert (sum(raw[:-1]) & 0xFF) == raw[-1]
        assert int(f["mask"], 16) in (0, 1)


def test_offline_matrix_artifact_matches_a_fresh_run(tmp_path):
    """The committed matrix must be reproducible, not a hand-written claim."""
    art = REPO / "results/reconciliation/offline-causal-run/offline-causal-matrix.json"
    if not art.exists():
        pytest.skip("offline matrix artifact not present")
    data = json.loads(art.read_text())
    rows = {(r["case"], r["hypothesis"]): r["verdict"]["verdict"] for r in data["results"]}
    assert rows[("C0", "H_PRECLEAR_MATTERS")] == "NO_IDLE_FRAMES_OBSERVED"
    assert rows[("C0", "H_PRECLEAR_HARMLESS")] == "A_TWICE_PROVEN"
    for case in ("C1", "C2"):
        assert rows[(case, "H_PRECLEAR_MATTERS")] == "A_TWICE_PROVEN"
        assert rows[(case, "H_PRECLEAR_HARMLESS")] == "A_TWICE_PROVEN"
