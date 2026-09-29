"""Hardware-free tests for the public `armorx live rollback` command."""

import asyncio
import hashlib
import json

import pytest

from armorx import config as C
from armorx import confirm as CONFIRM
from armorx import live as L
from armorx import protocol as P

D7_ACK = bytes.fromhex("a505d70081")
PERSIST = bytes.fromhex("a5050e00b8")
MAPKEY_M1 = C.MAPKEYS_START + 23


def _canonical(values):
    values = list(values)
    crc = C.crc16_gamepad(values[2:144])
    values[0] = (crc >> 8) & 0xFF
    values[1] = crc & 0xFF
    return bytes(values)


def _baseline() -> bytes:
    return _canonical(C.fresh())


def _target_image() -> bytes:
    values = list(C.fresh())
    values[MAPKEY_M1] = 0
    return _canonical(values)


def _reads(*images):
    script = []
    for image in images:
        script.extend(P.fragment_config_image(0xD6, image))
    return script


def _script(before, after=(), *, d7_ack=D7_ACK, persist=(PERSIST,)):
    script = _reads(*before)
    if d7_ack is not None:
        script.append(d7_ack)
    script.append(None)
    script.extend(persist)
    script.append(None)
    script.extend(_reads(*after))
    return script


def _accept(text, title):
    return CONFIRM.ConfirmationResult(True, "test-double", "accepted by the test")


def _decline(text, title):
    return CONFIRM.ConfirmationResult(False, "test-double", "declined")


def _make_backup(tmp_path, image=None, *, session_target=None, sha_file=None,
                 json_sha=None, name="baseline-original"):
    image = image if image is not None else _baseline()
    prefix = tmp_path / name
    prefix.with_suffix(".bin").write_bytes(image)
    document = L.backup_document(image)
    if json_sha:
        document["summary"]["sha256"] = json_sha
    prefix.with_suffix(".json").write_text(json.dumps(document, indent=2))
    digest = sha_file or hashlib.sha256(image).hexdigest()
    prefix.with_suffix(".sha256").write_text(digest + "\n")
    if session_target is not None:
        prefix.with_suffix(".session.json").write_text(json.dumps({
            "format": "armorx-reversible-m1-session-v1",
            "baseline_sha256": hashlib.sha256(image).hexdigest(),
            "target_sha256": session_target,
        }))
    return prefix


def _run(script, prefix, *, confirmer=_accept, **kwargs):
    transport = L.MockLiveTransport(notifications=list(script))
    result = asyncio.run(L.rollback_config(
        transport, prefix, confirmer=confirmer, settle=0.0, fragment_delay=0.0,
        ack_window=0.05, **kwargs))
    return transport, result


def _writes(transport):
    return [w["frame"] for w in transport.writes if w["mutating"]]


def _d7(transport):
    return [f for f in _writes(transport) if P.parse_frame(f).opcode == 0xD7]


# --- the happy paths --------------------------------------------------------
def test_rollback_writes_the_exact_saved_bytes(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target=L.image_summary(_target_image())["sha256"])
    target = _target_image()
    transport, result = _run(_script([target], [baseline, baseline]), prefix)
    assert result["status"] == "RESTORED"
    assert P.reassemble_a4(_d7(transport), opcode=0xD7) == baseline
    assert result["state_classification"] == "known_target"
    assert result["restored_sha256"] == hashlib.sha256(baseline).hexdigest()
    assert result["byte_for_byte_match"] is True


def test_rollback_sends_exactly_one_persistence_frame(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target=L.image_summary(_target_image())["sha256"])
    transport, result = _run(_script([_target_image()], [baseline, baseline]), prefix)
    assert [f for f in _writes(transport) if f == PERSIST] == [PERSIST]
    assert [P.parse_frame(f).opcode for f in _writes(transport)] == [0xD7] * 10 + [0x0E]
    assert result["write"]["persist"]["sent"] == 1


def test_rollback_reports_no_change_when_already_restored(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target="8" * 64)
    transport, result = _run(_script([baseline]), prefix)
    assert result["status"] == "NO_CHANGE"
    assert _writes(transport) == []


def test_rollback_dry_run_writes_nothing(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target=L.image_summary(_target_image())["sha256"])
    transport, result = _run(_script([_target_image()]), prefix, dry_run=True)
    assert result["status"] == "DRY_RUN"
    assert result["mutating_frames_sent"] == 0
    assert _writes(transport) == []


# --- backup integrity -------------------------------------------------------
def test_rollback_refuses_a_tampered_bin(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline)
    data = bytearray(prefix.with_suffix(".bin").read_bytes())
    data[70] ^= 0x01
    prefix.with_suffix(".bin").write_bytes(_canonical(data))
    transport, result = _run(_script([_target_image()], [baseline, baseline]), prefix)
    assert result["status"] == "REFUSED"
    assert ".sha256 file does not match" in result["refusal_reason"]
    assert _writes(transport) == []


def test_rollback_refuses_a_bad_sha_file(tmp_path):
    prefix = _make_backup(tmp_path, _baseline(), sha_file="0" * 64)
    transport, result = _run(_script([_target_image()], [_baseline(), _baseline()]), prefix)
    assert result["status"] == "REFUSED"
    assert ".sha256 file does not match" in result["refusal_reason"]
    assert _writes(transport) == []


def test_rollback_refuses_a_json_that_disagrees(tmp_path):
    prefix = _make_backup(tmp_path, _baseline(), json_sha="1" * 64)
    transport, result = _run(_script([_target_image()]), prefix)
    assert result["status"] == "REFUSED"
    assert ".json backup does not match" in result["refusal_reason"]
    assert _writes(transport) == []


@pytest.mark.parametrize("missing", ["json", "bin", "sha256"])
def test_rollback_refuses_a_missing_backup_file(tmp_path, missing):
    prefix = _make_backup(tmp_path, _baseline())
    prefix.with_suffix(f".{missing}").unlink()
    transport, result = _run(_script([_target_image()]), prefix)
    assert result["status"] == "REFUSED"
    assert "missing" in result["refusal_reason"]
    assert _writes(transport) == []


def test_rollback_refuses_a_backup_that_is_not_144_bytes(tmp_path):
    prefix = _make_backup(tmp_path, _baseline())
    prefix.with_suffix(".bin").write_bytes(b"\x00" * 100)
    transport, result = _run(_script([_target_image()]), prefix)
    assert result["status"] == "REFUSED"
    assert _writes(transport) == []


# --- state classification ---------------------------------------------------
def test_rollback_refuses_unrelated_state_by_default(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target="7" * 64)
    values = list(C.fresh())
    values[90] = 4
    unrelated = _canonical(values)
    transport, result = _run(_script([unrelated], [baseline, baseline]), prefix)
    assert result["status"] == "REFUSED"
    assert result["state_classification"] == "different"
    assert "--allow-unrelated-state" in result["refusal_reason"]
    assert _writes(transport) == []


def test_rollback_allows_unrelated_state_with_the_override(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline)
    values = list(C.fresh())
    values[90] = 4
    unrelated = _canonical(values)
    transport, result = _run(_script([unrelated], [baseline, baseline]), prefix,
                             allow_unrelated_state=True)
    assert result["status"] == "RESTORED"
    assert result["state_classification"] == "different"
    assert P.reassemble_a4(_d7(transport), opcode=0xD7) == baseline


def test_rollback_without_a_session_record_needs_the_override(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline)          # no session record
    transport, result = _run(_script([_target_image()], [baseline, baseline]), prefix)
    assert result["status"] == "REFUSED"
    assert result["session_record"] is None


# --- confirmation and failure -----------------------------------------------
def test_declined_rollback_writes_nothing(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target=L.image_summary(_target_image())["sha256"])
    transport, result = _run(_script([_target_image()], []), prefix, confirmer=_decline)
    assert result["status"] == "REFUSED"
    assert "declined" in result["refusal_reason"]
    assert _writes(transport) == []


def test_rollback_verification_mismatch_is_reported(tmp_path):
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target=L.image_summary(_target_image())["sha256"])
    values = list(C.fresh())
    values[91] = 6
    third = _canonical(values)
    transport, result = _run(_script([_target_image()], [third]), prefix)
    assert result["status"] in {"FAIL", "UNEXPECTED_STATE"}
    assert result["byte_for_byte_match"] is False
    assert result["live_state_after_failure"]["state"] == "UNEXPECTED"


def test_rollback_uses_the_saved_bytes_not_the_json(tmp_path):
    """A decoded document must never be turned back into an image."""
    baseline = _baseline()
    prefix = _make_backup(tmp_path, baseline, session_target=L.image_summary(_target_image())["sha256"])
    document = json.loads(prefix.with_suffix(".json").read_text())
    document["bytes"] = [0] * 144                 # a hostile/edited document
    prefix.with_suffix(".json").write_text(json.dumps(document))
    transport, result = _run(_script([_target_image()], [baseline, baseline]), prefix)
    assert result["status"] == "RESTORED"
    assert P.reassemble_a4(_d7(transport), opcode=0xD7) == baseline
    assert result["restored_sha256"] == hashlib.sha256(baseline).hexdigest()
