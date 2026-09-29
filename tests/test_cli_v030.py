"""CLI regression tests for the v0.3.0 offline command groups."""

import json
from pathlib import Path

import pytest

from armorx.cli import main


def run(capsys, *argv):
    code = main(list(argv))
    return code, capsys.readouterr().out


def test_device_list_runs_without_hardware(capsys):
    code, out = run(capsys, "device", "list", "--known-only")
    assert code == 0
    payload = json.loads(out)
    assert "devices" in payload and "supported_count" in payload


def test_device_doctor_runs_without_hardware(capsys):
    code, out = run(capsys, "device", "doctor")
    assert code == 0
    payload = json.loads(out)
    assert "checks" in payload and "next_steps" in payload


def test_device_inspect_for_absent_device_is_success(capsys):
    code, out = run(capsys, "device", "inspect", "99-99")
    assert code == 0
    payload = json.loads(out)
    assert payload["found"] is False


def test_protocol_decode_documented_frame(capsys):
    code, out = run(capsys, "protocol", "decode", "A5 04 0B B4")
    assert code == 0
    payload = json.loads(out)
    assert payload["frames"][0]["opcode_info"]["name"] == "sanity"
    assert payload["frames"][0]["checksum_ok"] is True


def test_protocol_decode_stream(capsys):
    code, out = run(capsys, "protocol", "decode", "A5 04 0B B4 A5 05 D2 01 7D", "--stream")
    assert code == 0
    assert json.loads(out)["frame_count"] == 2


def test_protocol_build_matches_documentation(capsys):
    code, out = run(capsys, "protocol", "build", "--opcode", "0B")
    assert code == 0
    assert out.strip() == "A5 04 0B B4"


def test_protocol_build_writes_a_file(tmp_path: Path, capsys):
    target = tmp_path / "frame.bin"
    code, _ = run(capsys, "protocol", "build", "--opcode", "D2", "--payload", "01",
                  "-o", str(target))
    assert code == 0
    assert target.read_bytes() == bytes([0xA5, 0x05, 0xD2, 0x01, 0x7D])


def test_protocol_build_rejects_a_bad_fragment_index(capsys):
    code, _ = run(capsys, "protocol", "build", "--opcode", "D7", "--fragment", "11")
    assert code == 2


def test_protocol_opcodes_lists_evidence(capsys):
    code, out = run(capsys, "protocol", "opcodes")
    assert code == 0
    payload = json.loads(out)
    assert any(row["name"] == "config_read" for row in payload["opcodes"])


def test_protocol_describe_image(capsys):
    image = " ".join(f"{b:02X}" for b in range(144))
    code, out = run(capsys, "protocol", "describe-image", "--image", image)
    assert code == 0
    payload = json.loads(out)
    assert payload["fragment_count"] == 10
    assert payload["fragments"][0].startswith("A4 14 D7 01")


def test_gip_decode_synthetic_frame(capsys):
    frame = bytearray(48)
    frame[0], frame[2], frame[3] = 0x20, 0xCA, 0x2C
    frame[4] = 0x11
    frame[6], frame[7] = 0xFC, 0x03
    code, out = run(capsys, "gip", "decode", " ".join(f"{b:02X}" for b in frame))
    assert code == 0
    payload = json.loads(out)
    assert payload["buttons"]["A"] is True
    assert payload["triggers"]["LT"] == 1020
    assert payload["unknown_spans"]


def test_gip_decode_rejects_a_non_input_type(capsys):
    frame = " ".join(f"{b:02X}" for b in bytes(48))
    code, _ = run(capsys, "gip", "decode", frame)
    assert code == 2


def test_gip_forms_documents_the_unknown_transition(capsys):
    code, out = run(capsys, "gip", "forms")
    assert code == 0
    payload = json.loads(out)
    assert payload["forms"]["transition_cause"]["evidence"] == "unknown"


def test_top_level_help_lists_the_new_groups(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for group in ("device", "protocol", "gip"):
        assert group in out
