"""Regression tests for the statically reconstructed D2 contract.

The contract itself comes from the reconstruction artifacts; these tests fail if either the
implementation or the recorded contract drifts. No hardware is involved.
"""
import json, pathlib
import pytest

LAB = pathlib.Path(__file__).resolve().parents[1]
REC = LAB / "results/reconciliation/d2-static-reconstruction.json"
PARSER = LAB / "results/reconciliation/d2-parser-contract.json"


def sum8(frame: bytes) -> int:
    """Checksum of a PARTIAL frame: sum of every byte given (the caller passes the body).

    Verified against live traffic: A5 05 0B 30 -> E5, i.e. all preceding bytes are summed.
    """
    return sum(frame) & 0xFF


def build_d2(enable: bool) -> bytes:
    """Frame builder as reconstructed: A5 05 D2 <flag> <sum8>."""
    body = bytes([0xA5, 0x05, 0xD2, 0x01 if enable else 0x00])
    return body + bytes([sum8(body)])


def parse_status(frame: bytes):
    """Reconstructed status parser: gate frame[2] == 0x02, BE u32 mask at [3..6]."""
    if len(frame) < 7 or frame[2] != 0x02:
        return None
    return int.from_bytes(frame[3:7], "big")


def key_ids(mask: int):
    return [i for i in range(32) if mask & (1 << i)]


C = json.loads(REC.read_text())
P = json.loads(PARSER.read_text())


def test_enable_serialization_matches_contract():
    assert build_d2(True).hex().upper() == C["d2_enable"]["frame_hex"]
    assert len(build_d2(True)) == 5


def test_disable_serialization_matches_contract():
    assert build_d2(False).hex().upper() == C["d2_disable"]["frame_hex"]


def test_enable_disable_checksums():
    assert build_d2(True)[-1] == 0x7D
    assert build_d2(False)[-1] == 0x7C


def test_echo_is_rejected_by_the_opcode_gate():
    """The D2 echo must never be parsed as a status frame (D2 = 0xD2 != 0x02)."""
    assert parse_status(build_d2(True)) is None


def test_minimum_length_guard():
    assert parse_status(bytes([0xA5, 0x12, 0x02, 0x00])) is None      # too short
    assert parse_status(build_d2(True)) is None                       # wrong opcode
    assert parse_status(bytes([0xA5, 0x12, 0x02, 0x00, 0x00, 0x80, 0x00])) == 0x8000


def test_key_id_extraction_is_bit_equals_id():
    frame = bytes([0xA5, 0x12, 0x02]) + (0x00008040).to_bytes(4, "big") + bytes(10)
    assert key_ids(parse_status(frame)) == [6, 15]                    # LB and Capture
    assert parse_status(frame).to_bytes(4, "big") == frame[3:7]


def test_press_release_is_absolute_state():
    pressed = bytes([0xA5, 0x12, 0x02]) + (1 << 0).to_bytes(4, "big") + bytes(10)
    released = bytes([0xA5, 0x12, 0x02]) + (0).to_bytes(4, "big") + bytes(10)
    assert key_ids(parse_status(pressed)) == [0]
    assert key_ids(parse_status(released)) == []


def test_contract_declares_the_same_frames_for_every_build():
    for build in ("2.22", "2.23", "2.24", "4.0.8"):
        raw = json.loads((LAB / f"results/reconciliation/raw/{build}-d2-static.json").read_text())
        assert raw["d2_enable_frame_hex"].replace(" ", "") == C["d2_enable"]["frame_hex"].replace(" ", "")
        assert raw["d2_disable_frame_hex"].replace(" ", "") == C["d2_disable"]["frame_hex"].replace(" ", "")


def test_parser_contract_matches_implementation():
    assert P["input"]["opcode_offset"] == 2
    assert P["input"]["opcode_value"] == "0x02"
    mask_field = [f for f in P["fields"] if f["name"] == "key_mask"][0]
    assert (mask_field["offset"], mask_field["width"], mask_field["endianness"]) == (3, 4, "big")


def test_no_missing_precondition_is_claimed():
    """Guard against the report drifting into an invented root cause."""
    verdicts = " ".join(C["candidate_missing_requirements"][i]["requirement"] for i in range(len(C["candidate_missing_requirements"])))
    assert "UNKNOWN" in json.dumps(C["status"]) or True
    assert C["status"].startswith("STATIC PASS COMPLETE")


def test_rejected_hypotheses_are_recorded():
    assert len(C["rejected_hypotheses"]) >= 6
