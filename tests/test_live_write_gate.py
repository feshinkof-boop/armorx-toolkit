"""Hardware-free tests for the supervised no-op D7 write-safety gate.

Nothing here touches BLE hardware. Every scenario is scripted on the mock
transport, which can mark the end of a bounded notification window with None.
"""

import argparse
import asyncio
import inspect
import json

import pytest

from armorx import cli
from armorx import config as C
from armorx import live as L
from armorx import protocol as P

D7_ACK = bytes.fromhex("a505d70081")
PERSIST_ACK = bytes.fromhex("a5050e00b8")


def _image() -> bytes:
    return bytes(C.fresh())


def _other_image() -> bytes:
    """A second, genuinely valid 144-byte image with a matching CRC."""
    values = list(C.fresh())
    values[40] = (values[40] + 1) % 256
    crc = C.crc16_gamepad(values[2:144])
    values[0] = (crc >> 8) & 0xFF
    values[1] = crc & 0xFF
    return bytes(values)


def _broken_crc_image() -> bytes:
    values = list(C.fresh())
    values[0] ^= 0xFF
    return bytes(values)


def _reads(*images):
    """Notification script for a sequence of D6 reads (no window markers)."""
    script: list = []
    for image in images:
        script.extend(P.fragment_config_image(0xD6, image))
    return script


def _script(before, after=(), *, d7_ack=D7_ACK, persist_ack=PERSIST_ACK):
    """Full script: the preflight reads, the D7 window, the 0E window, the read-back.

    ``None`` marks the end of a bounded window without consuming a notification.
    """
    script = _reads(*before)
    if d7_ack is not None:
        script.append(d7_ack)
    script.append(None)
    if persist_ack is not None:
        script.append(persist_ack)
    script.append(None)
    script.extend(_reads(*after))
    return script


def _run(script, *, authorized=True, prefix=None, tmp_path=None, **kwargs):
    transport = L.MockLiveTransport(notifications=script)
    result = asyncio.run(L.validate_write_gate(
        transport,
        backup_prefix=prefix if prefix is not None else tmp_path / "baseline-before-write",
        authorized=authorized,
        settle=0.0,
        fragment_delay=0.0,
        ack_window=0.05,
        **kwargs,
    ))
    return transport, result


def _mutating_frames(transport):
    return [w["frame"] for w in transport.writes if w["mutating"]]


def test_gate_refuses_without_operator_authorization(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], authorized=False) if False else _script([image, image]), authorized=False, tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert "authorization" in result["refusal_reason"]
    assert _mutating_frames(transport) == []
    # but the preflight backup must already exist before any authorization
    assert (tmp_path / "baseline-before-write.bin").read_bytes() == image


def test_gate_refuses_when_repeated_reads_differ(tmp_path):
    transport, result = _run(_script([_image(), _other_image()]), tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert result["repeated_reads_identical"] is False
    assert result["repeated_read_differences"]
    assert _mutating_frames(transport) == []


def test_gate_refuses_on_bad_crc(tmp_path):
    transport, result = _run(_script([_broken_crc_image()]), tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert "CRC" in result["refusal_reason"]
    assert _mutating_frames(transport) == []


def test_gate_refuses_on_invalid_length(tmp_path):
    image = _image()
    transport, result = _run(_script([image])[:-2], tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert _mutating_frames(transport) == []


def test_gate_refuses_when_the_backup_cannot_be_written(tmp_path):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x")
    transport, result = _run(_script([_image(), _image()]),
                             prefix=blocker / "nested" / "baseline", tmp_path=tmp_path)
    assert result["status"] == "REFUSED"
    assert "backup failed" in result["refusal_reason"]
    assert _mutating_frames(transport) == []


def test_noop_write_is_exactly_ten_d7_a4_fragments(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [image, image]), tmp_path=tmp_path)
    d7 = [f for f in _mutating_frames(transport)
          if P.parse_frame(f).opcode == 0xD7]
    assert len(d7) == 10
    parsed = [P.parse_frame(f) for f in d7]
    assert all(p.is_fragment and p.family == P.FAMILY_A4 for p in parsed)
    assert [p.fragment_index for p in parsed] == list(range(1, 11))
    assert all(p.checksum_ok for p in parsed)
    assert result["d7"]["sent"] == 10


def test_d7_fragments_reconstruct_the_exact_baseline(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [image, image], d7_ack=None), tmp_path=tmp_path)
    d7 = [f for f in _mutating_frames(transport) if P.parse_frame(f).opcode == 0xD7]
    assert P.reassemble_a4(d7, opcode=0xD7) == image
    assert result["baseline_sha256"] == result["final_sha256"]


def test_exactly_one_persistence_frame_is_sent(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [image, image]), tmp_path=tmp_path)
    persist = [f for f in _mutating_frames(transport) if f == L.PERSIST_REQUEST]
    assert len(persist) == 1
    assert persist[0] == bytes.fromhex("a5050e00b8")
    assert result["persist"]["sent"] == 1
    assert result["persist"]["notification_count"] >= 1


def test_identical_readback_passes(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [image, image]), tmp_path=tmp_path)
    assert result["status"] == "PASS"
    assert result["byte_for_byte_match"] is True
    assert result["all_offsets_differing"] == []
    assert len(result["readback"]["attempts"]) == 2


def test_differing_readback_fails_with_exact_offsets(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [_other_image()], d7_ack=None), tmp_path=tmp_path)
    assert result["status"] == "FAIL"
    assert result["byte_for_byte_match"] is False
    offsets = [d["offset"] for d in result["all_offsets_differing"]]
    assert offsets
    # the gate must not attempt a second write in response
    assert len([f for f in _mutating_frames(transport) if P.parse_frame(f).opcode == 0xD7]) == 10
    assert result["readback"]["attempts"][0]["differences"]


def test_the_gate_cannot_accept_a_target_image():
    params = set(inspect.signature(L.validate_write_gate).parameters)
    assert params == {"transport", "backup_prefix", "authorized", "timeout",
                      "ack_window", "fragment_delay", "settle", "identity"}
    for banned in ("image", "target", "payload", "opcode", "config"):
        assert banned not in params
    parser = cli.build_parser()
    with pytest.raises(SystemExit):  # a target argument must be rejected outright
        parser.parse_args(["live", "validate-write-gate", "--address", "AA:BB:CC:DD:EE:FF",
                           "--backup-prefix", "/tmp/x", "--target", "/tmp/y"])
    accepted = parser.parse_args(["live", "validate-write-gate", "--address",
                                 "AA:BB:CC:DD:EE:FF", "--backup-prefix", "/tmp/x"])
    assert accepted.authorized is False  # never authorized by default


def test_ack_is_recorded_and_absence_is_not_a_rejection(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [image, image]), tmp_path=tmp_path)
    assert result["d7"]["ack_observed"] is True
    assert result["d7"]["acknowledgement"]["checksum_ok"] is True
    assert result["status"] == "PASS"

    _, result2 = _run(_script([image, image], [image, image], d7_ack=None), tmp_path=tmp_path)
    assert result2["d7"]["ack_observed"] is False
    assert "absence" in result2["d7"]["acknowledgement"]["note"]
    assert result2["status"] == "PASS"


def test_no_general_write_command_is_exposed():
    """The gate must not have grown a general apply/write-config command."""
    parser = cli.build_parser()
    for banned in ("apply", "write-config", "write", "console", "opcode",
                   "raw", "send"):
        with pytest.raises(SystemExit):
            parser.parse_args(["live", banned, "--address", "AA:BB:CC:DD:EE:FF"])
    live_commands = sorted(
        action.choices.keys()
        for action in parser._subparsers._group_actions[0]._choices_actions and []
    ) if False else None
    # the live subcommand set is fixed and known
    import armorx.cli as cli_mod
    live_parser = parser._subparsers._group_actions[0].choices["live"]
    assert sorted(live_parser._subparsers._group_actions[0].choices) == [
        "backup", "info", "plan", "read-config", "scan", "validate-reversible-m1",
        "validate-write-gate"]


def test_no_local_path_or_user_name_reaches_the_report(tmp_path):
    image = _image()
    transport, result = _run(_script([image, image], [image, image], d7_ack=None),
                             tmp_path=tmp_path)
    text = json.dumps(result)
    assert str(tmp_path) not in text
    assert "/home/" not in text
    assert result["backup"]["json"] == "baseline-before-write.json"


def test_no_ble_address_reaches_the_artifacts(tmp_path):
    image = _image()
    transport = L.MockLiveTransport(notifications=_script([image, image], [image, image], d7_ack=None))
    result = asyncio.run(L.validate_write_gate(
        transport, backup_prefix=tmp_path / "baseline-before-write",
        authorized=True, settle=0.0, fragment_delay=0.0, ack_window=0.05,
        identity={"model": "ZJ-XT", "firmware": "2741", "battery": 87,
                  "transport": "ble", "address": "AA:BB:CC:DD:EE:FF"}))
    text = json.dumps(result)
    backup_text = (tmp_path / "baseline-before-write.json").read_text()
    for banned in ("AA:BB:CC:DD:EE:FF", "aa:bb:cc"):
        assert banned not in text
        assert banned not in backup_text
