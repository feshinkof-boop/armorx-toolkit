"""Unit tests for the ARMOR-X protocol primitives.

These pin the byte-exact request frames and reply frames to the canonical
research, so a regression in the checksum/CRC/framing cannot silently change the
wire format.

Run:  ../bumble/venv/bin/python -m pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import armorx_protocol as proto  # noqa: E402


BYTE_EXACT_REQUESTS = [
    ("A5 04 0B B4", 0x0B, "getZKMVer"),
    ("A5 0C EF 00 00 00 00 00 00 00 00 A0", 0xEF, "getDeviceUUID"),
    ("A5 04 D6 7F", 0xD6, "getDeviceConfig"),
    ("A5 04 E4 8D", 0xE4, "getMTU"),
    ("A5 04 E2 8B", 0xE2, "readFirmware"),
    ("A5 04 04 AD", 0x04, "getBattery"),
]


@pytest.mark.parametrize("hexstr,opcode,name", BYTE_EXACT_REQUESTS)
def test_byte_exact_request_frames_parse(hexstr, opcode, name):
    raw = bytes.fromhex(hexstr.replace(" ", ""))
    frame = proto.parse_frame(raw)
    assert frame is not None
    assert frame.kind == "short"
    assert frame.opcode == opcode
    assert frame.opcode_name == name
    assert frame.checksum_ok
    assert frame.length == len(raw)


def test_short_frame_checksum_rule():
    # checksum = (sum of all preceding bytes) & 0xFF
    body = bytes([0xA5, 0x04, 0x0B])
    assert proto.frame_checksum(body) == 0xB4
    assert proto.build_frame(0x0B, b"") == bytes.fromhex("A5040BB4")


def test_bad_checksum_is_rejected():
    frame = proto.parse_frame(bytes.fromhex("A5040BB5"))
    assert frame is not None and frame.checksum_ok is False


def test_wrong_length_byte_is_rejected():
    # length byte says 5 but the frame is 4 bytes
    frame = proto.parse_frame(bytes.fromhex("A5050BB4"))
    assert frame is not None and frame.checksum_ok is False


def test_default_config_144_is_byte_exact_and_crc_valid():
    # default_001 has CRC placeholder 0x0000; the loader recomputes 0x848A
    image = proto.load_default_config_144()
    assert len(image) == 144
    assert image[2:4] == bytes([0x00, 0x90])
    assert image[0:2] == bytes([0x84, 0x8A])   # research default-configs/README.md
    assert proto.config_crc_valid(image)


def test_crc16_modbus_matches_research_value():
    # CRC-16/MODBUS over bytes 2..143 of the 144-byte default == 0x848A
    image = proto.load_default_config_144()
    assert proto.crc16_modbus(image[2:]) == 0x848A


def test_d6_reply_uses_ten_fragments_with_index_byte():
    image = proto.load_default_config_144()
    frames = proto.build_fragment_sequence(0xD6, image)
    assert len(frames) == 10
    assert [len(f) for f in frames] == [20] * 9 + [14]
    parsed = [proto.parse_frame(f) for f in frames]
    assert [p.frag_index for p in parsed] == list(range(1, 11))
    assert all(p.checksum_ok for p in parsed)
    assert b"".join(p.data for p in parsed) == image


def test_version_reply_bytes():
    # live-captured reply for the tested unit: A5 05 0B 30 E5
    assert proto.build_frame(0x0B, bytes([0x30])).hex() == "a5050b30e5"


def test_ef_reply_places_uuid_at_bytes_3_to_10():
    uuid = bytes.fromhex("0001020304050607")
    reply = proto.build_frame(0xEF, uuid)
    assert reply[2] == 0xEF
    assert reply[3:11] == uuid
    assert proto.parse_frame(reply).checksum_ok


def test_d7_ack_bytes():
    assert proto.build_frame(0xD7, bytes([0x00])).hex() == "a505d70081"


def test_d8_terminator_parses():
    # A4 0A D8 <nfrags+1> <sum8>
    body = bytes([0xA4, 0x0A, 0xD8, 0x0B])
    terminator = body + bytes([proto.frame_checksum(body)])
    frame = proto.parse_frame(terminator)
    assert frame is not None
    assert frame.kind == "fragment"
    assert frame.opcode == 0xD8
    assert frame.checksum_ok
    assert frame.payload[0] == 0x0B


def test_reply_table_marks_only_evidence_backed():
    backed = {op for op, spec in proto.REPLY_TABLE.items() if spec.status == "EVIDENCE-BACKED"}
    assert backed == {0x0B, 0xEF, 0xD6, 0xD7, 0x0E}
    for op in (0xE4, 0xE2, 0x04):
        assert proto.reply_status(op).status == "UNKNOWN"


def test_unknown_commands_never_have_reply_bytes():
    # The peripheral only ever transmits for EVIDENCE-BACKED replies; every
    # other opcode resolves to UNKNOWN and is logged with reply_bytes_sent=0.
    for op in (0x04, 0x05, 0x06, 0x70, 0x73, 0xAB, 0xD2, 0xDA, 0xE2, 0xE4, 0xF5, 0xFC, 0xFF):
        spec = proto.reply_status(op)
        assert spec.status == "UNKNOWN"
        assert spec.description  # must state why nothing is sent
