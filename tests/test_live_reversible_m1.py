"""Hardware-free tests for the supervised reversible M1 -> A mutation.

Nothing here touches BLE hardware. Every scenario is scripted on the mock
transport, which marks the end of a bounded notification window with None.
"""

import asyncio
import inspect
import json
from pathlib import Path

import pytest

from armorx import cli
from armorx import config as C
from armorx import live as L
from armorx import protocol as P

D7_ACK = bytes.fromhex("a505d70081")
PERSIST_ACK = bytes.fromhex("a5050e00b8")
OFFSET_M1 = 135
OFFSETS_EXPECTED = [0, 1, 135]
HISTORICAL_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"


def _set_crc(values):
    crc = C.crc16_gamepad(list(values[2:144]))
    values[0] = (crc >> 8) & 0xFF
    values[1] = crc & 0xFF


def _live(m1: int = 1, tweak: int = 0) -> bytes:
    """A valid 144-byte image whose mapKeys[23] holds ``m1``."""
    values = list(C.fresh())
    values[OFFSET_M1] = m1
    if tweak:
        values[40] = (values[40] + tweak) % 256
    _set_crc(values)
    return bytes(values)


def _reads(*images):
    script = []
    for image in images:
        script.extend(P.fragment_config_image(0xD6, image))
    return script


def _script(before, after=(), *, d7_ack=D7_ACK, persist_ack=PERSIST_ACK):
    script = _reads(*before)
    if d7_ack is not None:
        script.append(d7_ack)
    script.append(None)
    if persist_ack is not None:
        script.append(persist_ack)
    script.append(None)
    script.extend(_reads(*after))
    return script


def _run(script, *, stage="apply", authorized=True, prefix, **kwargs):
    transport = L.MockLiveTransport(notifications=list(script))
    result = asyncio.run(L.validate_reversible_m1(
        transport, backup_prefix=prefix, authorized=authorized, stage=stage,
        settle=0.0, fragment_delay=0.0, ack_window=0.05, **kwargs))
    return transport, result


def _writes(transport):
    return [w["frame"] for w in transport.writes if w["mutating"]]


def _d7(transport):
    return [f for f in _writes(transport) if P.parse_frame(f).opcode == 0xD7]


def _prefix(tmp_path: Path, name: str) -> Path:
    return tmp_path / name


# --- requirement 1: no mutation without explicit authorization ---------------
def test_no_mutation_without_explicit_authorization(tmp_path):
    image = _live()
    prefix = _prefix(tmp_path, "baseline")
    transport, result = _run(_script([image, image]), authorized=False, prefix=prefix)
    assert result["status"] == "REFUSED"
    assert "authorization" in result["refusal_reason"]
    assert _writes(transport) == []
    assert not prefix.with_suffix(".session.json").exists()
    # the recovery baseline must still have been saved before that point
    assert prefix.with_suffix(".bin").read_bytes() == image


# --- requirements 2-5: preflight refusals -----------------------------------
def test_two_pre_write_reads_must_be_identical(tmp_path):
    transport, result = _run(_script([_live(), _live(tweak=1)]),
                             prefix=_prefix(tmp_path, "b"))
    assert result["status"] == "REFUSED"
    assert result["repeated_reads_identical"] is False
    assert _writes(transport) == []


def test_baseline_must_be_144_bytes(tmp_path):
    image = _live()
    frames = P.fragment_config_image(0xD6, image)
    short = frames[:-1] + [P.build_a4(0xD6, 10, image[-5:])]
    transport, result = _run(short + [None], prefix=_prefix(tmp_path, "b"))
    assert result["status"] == "REFUSED"
    assert "144" in result["refusal_reason"]
    assert _writes(transport) == []


def test_baseline_declared_length_must_be_144(tmp_path):
    values = list(_live())
    values[3] = 0x91
    _set_crc(values)
    bad = bytes(values)
    transport, result = _run(_script([bad]), prefix=_prefix(tmp_path, "b"))
    assert result["status"] == "REFUSED"
    assert "declares" in result["refusal_reason"]
    assert _writes(transport) == []


def test_baseline_crc_must_verify(tmp_path):
    values = list(_live())
    values[0] ^= 0xFF
    transport, result = _run(_script([bytes(values)]), prefix=_prefix(tmp_path, "b"))
    assert result["status"] == "REFUSED"
    assert "CRC" in result["refusal_reason"]
    assert _writes(transport) == []


# --- requirement 6: the backup must succeed before a target exists ----------
def test_backup_must_succeed_before_target_generation(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    prefix = blocker / "nested" / "baseline"
    transport, result = _run(_script([_live(), _live()]), prefix=prefix)
    assert result["status"] == "REFUSED"
    assert "backup failed" in result["refusal_reason"]
    assert "target" not in result
    assert _writes(transport) == []


# --- requirement 7: the current M1 value is read, never assumed -------------
def test_current_m1_is_read_from_the_live_baseline(tmp_path):
    for m1 in (1, 4, 26):
        transport, result = _run(_script([_live(m1=m1), _live(m1=m1)]),
                                 prefix=_prefix(tmp_path, f"b{m1}"))
        assert result["baseline_m1"]["code"] == m1
        assert result["baseline_m1"]["offset"] == OFFSET_M1
    # and the builder itself derives the current value from the image it is given
    assert L.build_m1_remap_target(_live(m1=4))["current_m1_code"] == 4
    assert L.build_m1_remap_target(_live(m1=1))["current_m1_code"] == 1


# --- requirement 8: already-A aborts this experiment ------------------------
def test_already_a_aborts_without_writing(tmp_path):
    image = _live(m1=0)
    transport, result = _run(_script([image, image]), prefix=_prefix(tmp_path, "b"))
    assert result["status"] == "ABORTED_ALREADY_A"
    assert _writes(transport) == []
    assert "no D7 and no 0E were sent" in result["refusal_reason"]


# --- requirements 9-12: the target is a copy with one logical change --------
def test_target_is_a_copy_of_the_baseline_apart_from_crc_and_m1(tmp_path):
    baseline = _live(m1=1)
    plan = L.build_m1_remap_target(baseline)
    target = plan["target"]
    assert len(target) == 144
    assert target[OFFSET_M1] == 0
    for offset in range(144):
        if offset in (0, 1, OFFSET_M1):
            continue
        assert target[offset] == baseline[offset], offset


def test_only_mapkeys_23_changes_logically(tmp_path):
    baseline = _live(m1=1)
    plan = L.build_m1_remap_target(baseline)
    assert plan["current_m1_code"] == 1
    assert plan["target_m1_code"] == 0
    assert plan["target_m1_name"] == "A"
    assert plan["changed_offsets"] == OFFSETS_EXPECTED
    logical = [d for d in plan["differences"] if d["offset"] not in (0, 1)]
    assert logical == [{"offset": OFFSET_M1, "before": 1, "after": 0}]


def test_target_crc_is_regenerated(tmp_path):
    baseline = _live(m1=1)
    target = L.build_m1_remap_target(baseline)["target"]
    stored = (target[0] << 8) | target[1]
    assert stored == C.crc16_gamepad(list(target[2:]))
    assert target[0:2] != baseline[0:2]


def test_a_fourth_changed_byte_aborts(monkeypatch):
    monkeypatch.setattr(L, "EXPECTED_MUTATION_OFFSETS", (0, 1, 135, 40))
    with pytest.raises(L.LiveError) as excinfo:
        L.build_m1_remap_target(_live(m1=1))
    assert "refusing this mutation" in str(excinfo.value)


# --- requirements 13-15: the write is ten fragments, one 0E, exact verify ---
def test_target_is_written_as_ten_fragments_and_reconstructs_exactly(tmp_path):
    baseline = _live(m1=1)
    target = L.build_m1_remap_target(baseline)["target"]
    transport, result = _run(_script([baseline, baseline], [target, target]),
                             prefix=_prefix(tmp_path, "b"))
    frames = _d7(transport)
    assert len(frames) == 10
    assert P.reassemble_a4(frames, opcode=0xD7) == target
    assert [P.parse_frame(f).fragment_index for f in frames] == list(range(1, 11))
    assert result["status"] == "APPLIED"


def test_exactly_one_persistence_frame_after_the_target(tmp_path):
    baseline = _live(m1=1)
    target = L.build_m1_remap_target(baseline)["target"]
    transport, result = _run(_script([baseline, baseline], [target, target]),
                             prefix=_prefix(tmp_path, "b"))
    persist = [f for f in _writes(transport) if f == L.PERSIST_REQUEST]
    assert len(persist) == 1
    assert persist[0] == bytes.fromhex("a5050e00b8")
    assert result["write"]["persist"]["sent"] == 1
    # the order is: all ten D7 fragments, then exactly one 0E
    opcodes = [P.parse_frame(f).opcode for f in _writes(transport)]
    assert opcodes == [0xD7] * 10 + [0x0E]


def test_target_verification_must_match_the_target(tmp_path):
    baseline = _live(m1=1)
    target = L.build_m1_remap_target(baseline)["target"]
    transport, result = _run(_script([baseline, baseline], [target, target]),
                             prefix=_prefix(tmp_path, "b"))
    assert result["byte_for_byte_match"] is True
    assert result["target_sha256"] == result["readback"]["attempts"][0]["sha256"]
    assert result["readback"]["attempts"][0]["differences"] == []
    assert result["this_session_mutation"] is True


# --- requirement 16-18: restore uses the saved baseline ---------------------
def _apply(tmp_path, name="session"):
    baseline = _live(m1=1)
    target = L.build_m1_remap_target(baseline)["target"]
    prefix = _prefix(tmp_path, name)
    transport, result = _run(_script([baseline, baseline], [target, target]), prefix=prefix)
    assert result["status"] == "APPLIED"
    return baseline, target, prefix


def test_restore_writes_back_the_saved_baseline(tmp_path):
    baseline, target, prefix = _apply(tmp_path)
    transport, result = _run(_script([target], [baseline, baseline]),
                             stage="restore", prefix=prefix)
    assert result["status"] == "RESTORED"
    assert P.reassemble_a4(_d7(transport), opcode=0xD7) == baseline
    assert result["restored_baseline_sha256"] == result["saved_baseline"]["sha256"]
    assert result["readback"]["attempts"][-1]["sha256"] ==         L.image_summary(baseline)["sha256"]


def test_restore_sends_exactly_one_persistence_frame(tmp_path):
    baseline, target, prefix = _apply(tmp_path)
    transport, result = _run(_script([target], [baseline, baseline]),
                             stage="restore", prefix=prefix)
    opcodes = [P.parse_frame(f).opcode for f in _writes(transport)]
    assert opcodes == [0xD7] * 10 + [0x0E]
    assert result["write"]["persist"]["sent"] == 1


def test_restore_refuses_a_tampered_saved_baseline(tmp_path):
    baseline, target, prefix = _apply(tmp_path)
    bin_path = prefix.with_suffix(".bin")
    data = bytearray(bin_path.read_bytes())
    data[40] ^= 0x01
    _set_crc(data)
    bin_path.write_bytes(bytes(data))
    transport, result = _run(_script([target], [baseline, baseline]),
                             stage="restore", prefix=prefix)
    assert result["status"] == "REFUSED"
    assert "session record SHA-256" in result["refusal_reason"]
    assert _writes(transport) == []


def test_restore_reports_when_nothing_needs_restoring(tmp_path):
    baseline, target, prefix = _apply(tmp_path)
    transport, result = _run(_script([baseline]), stage="restore", prefix=prefix)
    assert result["status"] == "NO_RESTORE_NEEDED"
    assert _writes(transport) == []


# --- requirement 19: an unexpected third state is a hard stop ---------------
def test_unexpected_third_state_is_a_hard_stop(tmp_path):
    baseline, target, prefix = _apply(tmp_path)
    third = _live(m1=9, tweak=3)
    transport, result = _run(_script([third], [baseline, baseline]),
                             stage="restore", prefix=prefix)
    assert result["status"] == "REFUSED"
    assert result["observed_state"] == "UNEXPECTED"
    assert result["operator_alert_required"] is True
    assert _writes(transport) == []


def test_check_stage_classifies_states_read_only(tmp_path):
    baseline, target, prefix = _apply(tmp_path)
    for image, expected in ((baseline, "BASELINE"), (target, "TARGET"),
                            (_live(m1=7, tweak=2), "UNEXPECTED")):
        transport, result = _run(_script([image]), stage="check", prefix=prefix)
        assert result["observed_state"] == expected
        assert result["status"] == "OK"
        assert _writes(transport) == []
        if expected == "TARGET":
            assert result["restore_authorized"] is True
        else:
            assert result["restore_authorized"] is False


def test_a_mismatched_target_write_fails_and_never_rewrites(tmp_path):
    baseline = _live(m1=1)
    transport, result = _run(_script([baseline, baseline], [_live(m1=4, tweak=5)]),
                             prefix=_prefix(tmp_path, "b"))
    assert result["status"] == "FAIL"
    assert result["observed_state"] == "UNEXPECTED"
    assert len(_d7(transport)) == 10          # no automatic second write
    assert "no further write was attempted" in result["failure_reason"]


# --- requirement 20: no general apply command, no target input --------------
def test_no_general_apply_command_and_no_target_input():
    parser = cli.build_parser()
    for banned in ("apply", "write-config", "write", "console", "raw", "opcode"):
        with pytest.raises(SystemExit):
            parser.parse_args(["live", banned, "--address", "AA:BB:CC:DD:EE:FF"])
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args([
            "live", "validate-reversible-m1", "--address", "AA:BB:CC:DD:EE:FF",
            "--backup-prefix", "/tmp/x", "--target", "/tmp/y"])
    accepted = cli.build_parser().parse_args([
        "live", "validate-reversible-m1", "--address", "AA:BB:CC:DD:EE:FF",
        "--backup-prefix", "/tmp/x"])
    assert accepted.authorized is False
    assert accepted.stage == "apply"
    params = set(inspect.signature(L.validate_reversible_m1).parameters)
    for banned in ("image", "target", "payload", "opcode", "config"):
        assert banned not in params


# --- requirement 21: artifacts stay private ---------------------------------
def test_artifacts_contain_no_private_values(tmp_path):
    baseline = _live(m1=1)
    target = L.build_m1_remap_target(baseline)["target"]
    prefix = _prefix(tmp_path, "b")
    transport = L.MockLiveTransport(notifications=_script([baseline, baseline],
                                                          [target, target]))
    result = asyncio.run(L.validate_reversible_m1(
        transport, backup_prefix=prefix, authorized=True, stage="apply",
        settle=0.0, fragment_delay=0.0, ack_window=0.05,
        identity={"model": "ZJ-XT", "firmware": "2741", "battery": 87,
                  "transport": "ble", "address": "AA:BB:CC:DD:EE:FF",
                  "serial": "SECRET-SERIAL", "hostname": "secret-host"}))
    blob = json.dumps(result)
    for path in tmp_path.iterdir():
        blob += path.read_text() if path.suffix in {".json", ".sha256"} else ""
    for leaked in ("AA:BB:CC:DD:EE:FF", "aa:bb:cc", "SECRET-SERIAL", "secret-host",
                   "/home/", str(tmp_path)):
        assert leaked not in blob
    assert "address" not in result.get("session_record", {})
