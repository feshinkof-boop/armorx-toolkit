"""Hardware-free tests for the public `armorx live apply` pipeline."""

import argparse
import asyncio
import hashlib
import json

import pytest

from armorx import cli
from armorx import config as C
from armorx import confirm as CONFIRM
from armorx import live as L
from armorx import protocol as P

D7_ACK = bytes.fromhex("a505d70081")
PERSIST_ACK = bytes.fromhex("a5050e00b8")
PERSIST = bytes.fromhex("a5050e00b8")
UNKNOWN_OFFSET = 90          # reserved_after_turbo: no recovered field covers it
MAPKEY_M1 = C.MAPKEYS_START + 23


def _canonical(values):
    values = list(values)
    crc = C.crc16_gamepad(values[2:144])
    values[0] = (crc >> 8) & 0xFF
    values[1] = crc & 0xFF
    return bytes(values)


def _image() -> bytes:
    return _canonical(C.fresh())


def _remapped(value: int = 0) -> bytes:
    values = list(C.fresh())
    values[MAPKEY_M1] = value
    return _canonical(values)


def _with_raw(offset: int, value: int) -> bytes:
    values = list(C.fresh())
    values[offset] = value
    return _canonical(values)


def _reads(*images):
    script = []
    for image in images:
        script.extend(P.fragment_config_image(0xD6, image))
    return script


def _script(before, after=(), *, d7_ack=D7_ACK, persist=(PERSIST_ACK,), windows=True):
    script = _reads(*before)
    if windows:
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
    return CONFIRM.ConfirmationResult(False, "test-double", "declined by the test")


def _unavailable(text, title):
    return CONFIRM.ConfirmationResult(None, "none", "no backend")


def _run(script, target, *, tmp_path, confirmer=_accept, prefix=None, **kwargs):
    transport = L.MockLiveTransport(notifications=list(script))
    result = asyncio.run(L.apply_config(
        transport, target,
        backup_prefix=prefix or (tmp_path / "baseline-original"),
        confirmer=confirmer, settle=0.0, fragment_delay=0.0, ack_window=0.05,
        **kwargs))
    return transport, result


def _writes(transport):
    return [w["frame"] for w in transport.writes if w["mutating"]]


def _d7(transport):
    return [f for f in _writes(transport) if P.parse_frame(f).opcode == 0xD7]


# --- the happy path ---------------------------------------------------------
def test_valid_apply_writes_ten_fragments_and_verifies(tmp_path):
    current = _image()
    target = _remapped(0)
    transport, result = _run(_script([current, current], [target, target]), target,
                             tmp_path=tmp_path)
    assert result["status"] == "APPLIED"
    assert len(_d7(transport)) == 10
    assert P.reassemble_a4(_d7(transport), opcode=0xD7) == target
    assert result["byte_for_byte_match"] is True
    assert result["current"]["sha256"] != result["target"]["sha256"]
    assert result["rollback_available"] is True
    assert result["diff"]["total_changed_bytes"] == 3


def test_no_change_target_writes_nothing(tmp_path):
    current = _image()
    transport, result = _run(_script([current, current]), current, tmp_path=tmp_path)
    assert result["status"] == "NO_CHANGE"
    assert _writes(transport) == []
    assert "no D7 and no 0E" in result["note"]


def test_dry_run_backs_up_but_never_writes(tmp_path):
    current = _image()
    target = _remapped(0)
    prefix = tmp_path / "baseline-original"
    transport, result = _run(_script([current, current], []), target,
                             tmp_path=tmp_path, prefix=prefix, dry_run=True)
    assert result["status"] == "DRY_RUN"
    assert _writes(transport) == []
    assert result["mutating_frames_sent"] == 0
    assert result["backup"]["sha256"] == L.image_summary(current)["sha256"]
    assert prefix.with_suffix(".bin").read_bytes() == current
    assert "changed bytes" in result["confirmation_text"]


# --- target validation ------------------------------------------------------
def test_bad_target_length_is_refused(tmp_path):
    transport, result = _run(_script([_image(), _image()]), b"\x00" * 143, tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert "144-byte" in result["refusal_reason"] or "144" in result["refusal_reason"]
    assert _writes(transport) == []


def test_bad_target_crc_is_refused(tmp_path):
    broken = bytearray(_remapped(0))
    broken[0] ^= 0xFF
    transport, result = _run(_script([_image(), _image()]), bytes(broken), tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert "CRC" in result["refusal_reason"]
    assert _writes(transport) == []


def test_live_read_mismatch_is_refused(tmp_path):
    transport, result = _run(_script([_image(), _with_raw(90, 5)], []), _remapped(0),
                             tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert result["live_read_differences"]
    assert _writes(transport) == []


def test_backup_failure_refuses_before_any_write(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    prefix = blocker / "nested" / "baseline"
    transport, result = _run(_script([_image(), _image()]), _remapped(0),
                             tmp_path=tmp_path, prefix=prefix)
    assert result["status"] == "REFUSED"
    assert "backup could not be written" in result["refusal_reason"]
    assert _writes(transport) == []


def test_backup_reopen_mismatch_refuses(tmp_path, monkeypatch):
    real = L.save_baseline

    def sabotaged(prefix, image, **kwargs):
        info = real(prefix, image, **kwargs)
        path = __import__("pathlib").Path(prefix).with_suffix(".bin")
        data = bytearray(path.read_bytes())
        data[70] ^= 0x01
        path.write_bytes(bytes(data))
        return info

    monkeypatch.setattr(L, "save_baseline", sabotaged)
    transport, result = _run(_script([_image(), _image()]), _remapped(0), tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert "reopened backup" in result["refusal_reason"]
    assert _writes(transport) == []


# --- unknown-byte safety ----------------------------------------------------
def test_unknown_byte_change_is_refused_by_default(tmp_path):
    target = _with_raw(UNKNOWN_OFFSET, 9)
    transport, result = _run(_script([_image(), _image()]), target, tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert result["unknown_offsets"] == [UNKNOWN_OFFSET]
    assert "not decoded" in result["refusal_reason"]
    assert _writes(transport) == []


def test_allow_unknown_diff_proceeds_and_records_the_flag(tmp_path):
    current = _image()
    target = _with_raw(UNKNOWN_OFFSET, 9)
    transport, result = _run(_script([current, current], [target, target]), target,
                             tmp_path=tmp_path, allow_unknown_diff=True)
    assert result["status"] == "APPLIED"
    assert result["allow_unknown_diff"] is True
    assert result["unknown_byte_count"] == 1
    assert len(_d7(transport)) == 10


def test_known_field_change_needs_no_override(tmp_path):
    current = _image()
    values = list(current)
    values[C.BYTE_FIELDS["stickTurn"]] = 7
    target = _canonical(values)
    transport, result = _run(_script([current, current], [target, target]), target,
                             tmp_path=tmp_path)
    assert result["status"] == "APPLIED"
    assert result["unknown_byte_count"] == 0


# --- confirmation -----------------------------------------------------------
def test_declined_confirmation_writes_nothing(tmp_path):
    transport, result = _run(_script([_image(), _image()], []), _remapped(0),
                             tmp_path=tmp_path, confirmer=_decline)
    assert result["status"] == "REFUSED"
    assert "declined" in result["refusal_reason"]
    assert _writes(transport) == []


def test_missing_confirmation_backend_writes_nothing(tmp_path):
    transport, result = _run(_script([_image(), _image()], []), _remapped(0),
                             tmp_path=tmp_path, confirmer=_unavailable)
    assert result["status"] == "REFUSED"
    assert "no confirmation backend" in result["refusal_reason"]
    assert _writes(transport) == []


def test_automation_confirmer_accepts_and_is_recorded(tmp_path):
    current = _image()
    target = _remapped(0)
    transport = L.MockLiveTransport(notifications=_script([current, current], [target, target]))
    result = asyncio.run(L.apply_config(
        transport, target, backup_prefix=tmp_path / "b", automation=True,
        settle=0.0, fragment_delay=0.0, ack_window=0.05))
    assert result["status"] == "APPLIED"
    assert result["confirmation"]["method"] == CONFIRM.METHOD_AUTOMATION


def test_confirm_module_requires_both_automation_switches():
    # the flag policy lives in the CLI; the module only honours an explicit request
    assert CONFIRM.confirm_change("x", env={}, which=lambda n: None,
                                  stdin_isatty=False).accepted is None
    assert CONFIRM.confirm_change("x", env={}, which=lambda n: None,
                                  stdin_isatty=False, automation=True).accepted is True


def test_cli_refuses_yes_without_acknowledge_backup(capsys, tmp_path):
    target = tmp_path / "t.bin"
    target.write_bytes(_remapped(0))
    args = argparse.Namespace(target=str(target), yes=True, acknowledge_backup=False)
    assert cli.cmd_live_apply(args) == 2
    assert "--acknowledge-backup" in capsys.readouterr().err


# --- acknowledgement and notification windows -------------------------------
def test_d7_ack_is_recorded(tmp_path):
    current = _image()
    target = _remapped(0)
    _, result = _run(_script([current, current], [target, target]), target, tmp_path=tmp_path)
    assert result["write"]["ack_observed"] is True
    assert result["write"]["acknowledgement"]["checksum_ok"] is True


def test_absent_d7_ack_is_recorded_as_absence_not_rejection(tmp_path):
    current = _image()
    target = _remapped(0)
    _, result = _run(_script([current, current], [target, target], d7_ack=None), target,
                     tmp_path=tmp_path)
    assert result["status"] == "APPLIED"
    assert result["write"]["ack_observed"] is False
    assert "absence" in result["write"]["acknowledgement"]["note"]


@pytest.mark.parametrize("responses", [[], [PERSIST_ACK], [PERSIST_ACK, PERSIST_ACK]])
def test_persistence_response_counts_are_recorded(tmp_path, responses):
    current = _image()
    target = _remapped(0)
    script = _script([current, current], [target, target], persist=tuple(responses))
    _, result = _run(script, target, tmp_path=tmp_path)
    assert result["status"] == "APPLIED"
    assert result["write"]["persist"]["notification_count"] == len(responses)
    assert result["write"]["persist"]["sent"] == 1
    if responses:
        assert result["write"]["persist"]["acknowledgement"]["observed"] is True
    else:
        assert result["write"]["persist"]["acknowledgement"]["observed"] is False


def test_exactly_one_persistence_frame_is_sent(tmp_path):
    current = _image()
    target = _remapped(0)
    transport, result = _run(_script([current, current], [target, target]), target,
                             tmp_path=tmp_path)
    assert [f for f in _writes(transport) if f == PERSIST] == [PERSIST]
    opcodes = [P.parse_frame(f).opcode for f in _writes(transport)]
    assert opcodes == [0xD7] * 10 + [0x0E]


# --- verification failures --------------------------------------------------
def test_verification_mismatch_fails_with_diagnostics(tmp_path):
    current = _image()
    target = _remapped(0)
    third = _with_raw(70, 3)
    _, result = _run(_script([current, current], [third]), target, tmp_path=tmp_path)
    assert result["status"] == "UNEXPECTED_STATE"
    assert result["byte_for_byte_match"] is False
    assert result["live_state_after_failure"]["state"] == "UNEXPECTED"
    assert "the verification read-back itself" == result["live_state_after_failure"]["source"]
    assert "nothing further was written" in result["failure_reason"]


def test_second_verification_mismatch_fails(tmp_path):
    current = _image()
    target = _remapped(0)
    _, result = _run(_script([current, current], [target, _image()]), target, tmp_path=tmp_path)
    assert result["byte_for_byte_match"] is False
    assert result["verification"]["matches"] is False
    assert len(result["verification"]["attempts"]) == 2      # both reads did happen
    assert result["verification"]["attempts"][1]["differences"]   # the second one differed
    assert result["status"] in {"FAIL", "UNEXPECTED_STATE"}


def test_classification_distinguishes_baseline_and_target(tmp_path):
    current = _image()
    target = _remapped(0)
    # read-back equals the baseline: the write did not take effect
    _, result = _run(_script([current, current], [current]), target, tmp_path=tmp_path)
    assert result["live_state_after_failure"]["state"] == "BASELINE"
    assert result["status"] == "FAIL"


# --- connection retries -----------------------------------------------------
class _FlakyConnect(L.MockLiveTransport):
    def __init__(self, fail_times, **kwargs):
        super().__init__(**kwargs)
        self.fail_times = fail_times
        self.connects = 0

    async def connect(self):
        self.connects += 1
        if self.connects <= self.fail_times:
            raise L.LiveError("transient connect failure")
        await super().connect()


def test_transient_connect_failure_is_retried_before_mutation():
    transport = _FlakyConnect(2)
    result = asyncio.run(L.connect_with_retries(transport, attempts=3, delay=0.0))
    assert result["ok"] is True
    assert result["attempts"] == 3
    assert len(result["errors"]) == 2
    assert transport.writes == []


def test_connect_retries_are_bounded_and_reported():
    transport = _FlakyConnect(5)
    result = asyncio.run(L.connect_with_retries(transport, attempts=3, delay=0.0))
    assert result["ok"] is False
    assert result["attempts"] == 3
    assert transport.connects == 3          # never unbounded


class _FailMidWrite(L.MockLiveTransport):
    """Fails on the Nth mutating frame, like a drop mid-transaction."""

    def __init__(self, fail_on, **kwargs):
        super().__init__(**kwargs)
        self.fail_on = fail_on
        self.mutating_sent = 0

    async def send(self, frame, *, mutating=False):
        if mutating:
            self.mutating_sent += 1
            if self.mutating_sent == self.fail_on:
                raise L.LiveError("link lost mid-write")
        await super().send(frame, mutating=mutating)


def test_no_retry_after_the_first_d7_fragment(tmp_path):
    current = _image()
    target = _remapped(0)
    script = _script([current, current], [], windows=False)
    transport = _FailMidWrite(fail_on=5, notifications=script)
    result = asyncio.run(L.apply_config(
        transport, target, backup_prefix=tmp_path / "b", confirmer=_accept,
        settle=0.0, fragment_delay=0.0, ack_window=0.05))
    assert result["status"] == "FAIL"
    assert len(_d7(transport)) == 4            # only the four that succeeded
    assert transport.mutating_sent == 5        # the transaction was never restarted
    assert result["live_state_after_failure"]["state"] in {"UNREADABLE", "BASELINE", "TARGET", "UNEXPECTED"}


# --- privacy and CLI surface ------------------------------------------------
def _third_image() -> bytes:
    values = list(C.fresh())
    values[91] = 6
    return _canonical(values)


def test_report_contains_no_private_values(tmp_path):
    current = _image()
    target = _remapped(0)
    transport = L.MockLiveTransport(notifications=_script([current, current], [target, target]))
    result = asyncio.run(L.apply_config(
        transport, target, backup_prefix=tmp_path / "b", confirmer=_accept,
        settle=0.0, fragment_delay=0.0, ack_window=0.05,
        identity={"model": "ZJ-XT", "firmware": "2741", "battery": 87,
                  "transport": "ble", "address": "AA:BB:CC:DD:EE:FF",
                  "serial": "SECRET-SERIAL", "hostname": "secret-host"}))
    blob = json.dumps(result)
    for path in tmp_path.iterdir():
        if path.suffix in {".json", ".sha256"}:
            blob += path.read_text()
    for leaked in ("AA:BB:CC:DD:EE:FF", "SECRET-SERIAL", "secret-host", "/home/",
                   str(tmp_path)):
        assert leaked not in blob
    assert result["backup"]["bin"] == "b.bin"


def test_default_backup_prefix_is_timestamped_and_beside_the_target(tmp_path):
    target = tmp_path / "config.json"
    prefix = cli.default_backup_prefix(str(target))
    assert prefix.startswith(str(tmp_path / "config-backup-"))
    stamp = prefix.rsplit("-backup-", 1)[1]
    assert len(stamp) == 15 and stamp[8] == "-"      # YYYYmmdd-HHMMSS
    # and it works through the command without any BLE access being attempted
    args = argparse.Namespace(target=str(target), yes=True, acknowledge_backup=False,
                              backup_prefix=None)
    assert cli.cmd_live_apply(args) == 2


# --- report classification wording (Phase 17) -------------------------------
def test_target_verification_reads_are_labelled_target(tmp_path):
    target = _remapped(0)
    _t, result = _run(_script([_image(), _image()], [target, target]), target, tmp_path=tmp_path)
    assert result["status"] == "APPLIED"
    attempts = result["verification"]["attempts"]
    assert [a["state"] for a in attempts] == ["TARGET", "TARGET"]
    assert all(a["matches_expected"] for a in attempts)
    assert all(a["expected_sha256"] == hashlib.sha256(target).hexdigest() for a in attempts)


def test_an_unrelated_verification_read_is_labelled_unexpected(tmp_path):
    target = _remapped(0)
    third = _remapped(3)
    _t, result = _run(_script([_image(), _image()], [third]), target, tmp_path=tmp_path)
    assert result["verification"]["attempts"][0]["state"] == "UNEXPECTED"
    assert result["live_state_after_failure"]["state"] == "UNEXPECTED"


def test_a_readback_that_is_still_the_baseline_is_labelled_baseline(tmp_path):
    target = _remapped(0)
    _t, result = _run(_script([_image(), _image()], [_image()]), target, tmp_path=tmp_path)
    assert result["verification"]["attempts"][0]["state"] == "BASELINE"
    assert result["live_state_after_failure"]["state"] == "BASELINE"


def test_dual_read_labels_follow_the_session_images_not_the_expectation():
    """The helper still demands ``expected``; the label describes what it is."""
    expected_image = _image()
    transport = L.MockLiveTransport(notifications=list(_reads(expected_image, expected_image)))
    readback = asyncio.run(L._dual_read_and_compare(
        transport, expected=expected_image, timeout=1.0, settle=0.0,
        baseline=_remapped(0), target=expected_image))
    assert readback["attempts"][0]["state"] == "TARGET"      # it *is* the target
    assert readback["attempts"][0]["matches_expected"] is True
    transport = L.MockLiveTransport(notifications=list(_reads(expected_image, expected_image)))
    readback = asyncio.run(L._dual_read_and_compare(
        transport, expected=expected_image, timeout=1.0, settle=0.0))
    assert readback["attempts"][0]["state"] == "BASELINE"    # fallback: the expectation


def _help(argv):
    import contextlib
    import io
    from armorx import cli as cli_mod
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), pytest.raises(SystemExit):
        cli_mod.main(argv)
    return " ".join(buffer.getvalue().split())


def test_public_live_help_does_not_claim_writes_are_unavailable():
    """The group help must describe the commands that actually exist."""
    text = _help(["--help"])
    assert "guarded apply/rollback" in text
    assert "not exposed yet" not in text


def test_public_live_group_lists_both_write_commands():
    text = _help(["live", "--help"])
    assert "{scan,info,read-config,backup,apply,rollback" in text
    assert "write a configuration file to the device" in text
    assert "restore the exact bytes of a saved backup" in text


def test_cli_has_no_opcode_or_payload_options():
    parser = cli.build_parser()
    for command in ("apply", "rollback"):
        live_parser = parser._subparsers._group_actions[0].choices["live"]
        sub = live_parser._subparsers._group_actions[0].choices[command]
        options = {option for action in sub._actions for option in action.option_strings}
        assert not options & {"--opcode", "--payload", "--raw", "--fragments", "--hex"}
    for banned in ("console", "raw", "opcode", "send"):
        with pytest.raises(SystemExit):
            parser.parse_args(["live", banned, "--address", "AA:BB:CC:DD:EE:FF"])


# --- Phase 16: apply and rollback must work as a pair ------------------------
def test_apply_records_its_target_before_the_write(tmp_path):
    """The record is written first, so an interrupted write is still rollbackable."""
    target = _remapped(0)
    prefix = tmp_path / "public-apply-baseline"
    script = _script([_image(), _image()])
    transport = _FailMidWrite(fail_on=1, notifications=script)
    result = asyncio.run(L.apply_config(
        transport, target, backup_prefix=prefix, confirmer=_accept,
        settle=0.0, fragment_delay=0.0, ack_window=0.05))
    assert result["status"] == "FAIL"
    record = json.loads((tmp_path / "public-apply-baseline.session.json").read_text())
    assert record["format"] == L.APPLY_SESSION_FORMAT
    assert record["target_sha256"] == hashlib.sha256(target).hexdigest()
    assert record["baseline_sha256"] == hashlib.sha256(_image()).hexdigest()
    assert record["changed_offsets"] == [0, 1, 135]
    assert record["apply_verified"] is False


def test_apply_marks_the_record_verified_after_success(tmp_path):
    target = _remapped(0)
    prefix = tmp_path / "public-apply-baseline"
    _t, result = _run(_script([_image(), _image()], [target, target]), target,
                      tmp_path=tmp_path, prefix=prefix)
    assert result["status"] == "APPLIED"
    record = json.loads((tmp_path / "public-apply-baseline.session.json").read_text())
    assert record["apply_verified"] is True
    assert record["verified_sha256"] == hashlib.sha256(target).hexdigest()


def test_the_session_record_carries_no_private_values(tmp_path):
    target = _remapped(0)
    prefix = tmp_path / "public-apply-baseline"
    _t, result = _run(_script([_image(), _image()], [target, target]), target,
                      tmp_path=tmp_path, prefix=prefix,
                      identity={"model": "ZJ-XT", "firmware": "2741",
                                "address": "2D:37:35:6D:66:11", "serial": "SECRET"})
    text = (tmp_path / "public-apply-baseline.session.json").read_text()
    assert "2D:37:35" not in text and "SECRET" not in text
    assert "/home/" not in text and str(tmp_path) not in text
    assert "public-apply-baseline" in text          # base name only


def test_rollback_of_an_applied_target_needs_no_override(tmp_path):
    """The regression this session found: apply then rollback, no extra flag."""
    target = _remapped(0)
    prefix = tmp_path / "public-apply-baseline"
    _t, applied = _run(_script([_image(), _image()], [target, target]), target,
                       tmp_path=tmp_path, prefix=prefix)
    assert applied["status"] == "APPLIED"
    script = _script([target], [_image(), _image()])
    transport = L.MockLiveTransport(notifications=list(script))
    rolled = asyncio.run(L.rollback_config(
        transport, prefix, confirmer=_accept, settle=0.0, fragment_delay=0.0,
        ack_window=0.05))
    assert rolled["status"] == "RESTORED"
    assert rolled["state_classification"] == "known_target"
    assert rolled["session_record"] == "public-apply-baseline.session.json"


def test_rollback_still_refuses_an_unrelated_image_despite_the_record(tmp_path):
    target = _remapped(0)
    prefix = tmp_path / "public-apply-baseline"
    _t, applied = _run(_script([_image(), _image()], [target, target]), target,
                       tmp_path=tmp_path, prefix=prefix)
    assert applied["status"] == "APPLIED"
    unrelated = _remapped(4)
    script = _script([unrelated])
    transport = L.MockLiveTransport(notifications=list(script))
    rolled = asyncio.run(L.rollback_config(
        transport, prefix, confirmer=_accept, settle=0.0, fragment_delay=0.0,
        ack_window=0.05))
    assert rolled["status"] == "REFUSED"
    assert rolled["state_classification"] == "different"
    assert [w for w in transport.writes if w["mutating"]] == []
