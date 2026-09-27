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
    ("A5 04 D4 7D", 0xD4, "getInputModel"),
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


def test_d8_terminator_legacy_0x0a_is_flagged():
    """A commit frame carrying the superseded 0x0A length byte must still parse (so old logs
    remain readable) but must be labelled as a legacy reading."""
    body = bytes([0xA4, 0x0A, 0xD8, 0x0B])
    frame = proto.parse_frame(body + bytes([proto.frame_checksum(body)]))
    assert frame is not None
    assert any("LEGACY" in n for n in frame.notes), frame.notes


def test_d8_terminator_parses():
    # A4 05 D8 <nfrags+1> <sum8>  (length byte 0x05 = empty segment + 5; the old 0x0A
    # reading treated the tagged Smi `mov x16, #0xa` as a wire byte - see smi-audit.md D1)
    body = bytes([0xA4, 0x05, 0xD8, 0x0B])
    terminator = body + bytes([proto.frame_checksum(body)])
    frame = proto.parse_frame(terminator)
    assert frame is not None
    assert frame.kind == "fragment"
    assert frame.opcode == 0xD8
    assert frame.checksum_ok
    assert frame.payload[0] == 0x0B


def test_reply_table_marks_only_evidence_backed():
    backed = {op for op, spec in proto.REPLY_TABLE.items() if spec.status == "EVIDENCE-BACKED"}
    assert backed == {0x0B, 0xEF, 0xD4, 0xD6, 0xD7, 0x0E}
    for op in (0xE4, 0xE2, 0x04):
        assert proto.reply_status(op).status == "UNKNOWN"


# ---------------------------------------------------------------------------
# 0xD4 -- "input model" / "onboard config"
#
# The request frame is byte-exact in all four builds; the reply STRUCTURE is
# evidence-backed (whole-frame indices 3 and 4, A5 length byte = total, checksum
# = sum & 0xFF). The VALUE DOMAIN of the two payload bytes is UNKNOWN, so the
# tests pin the layout and the arithmetic -- never a claimed device value.
# Evidence: results/reconciliation/d4-reconstruction.md|json
# ---------------------------------------------------------------------------

D4_REQUEST = bytes.fromhex("A504D47D")


def test_d4_request_is_byte_exact_in_all_four_builds():
    assert proto.D4_REQUEST == D4_REQUEST
    frame = proto.parse_frame(D4_REQUEST)
    assert frame is not None
    assert frame.kind == "short"
    assert frame.opcode == 0xD4
    assert frame.length == 4 == len(D4_REQUEST)
    assert frame.checksum_ok
    # checksum derivation: (0xA5 + 0x04 + 0xD4) & 0xFF == 0x7D
    assert proto.frame_checksum(D4_REQUEST[:3]) == 0x7D


def test_d4_reply_layout_and_checksum_are_evidence_backed():
    reply = proto.build_d4_reply(0x06, 0x03)
    assert reply.hex() == "a506d4060388"
    assert reply[0] == proto.FRAME_SHORT          # index 0 header
    assert reply[1] == len(reply) == 6            # index 1 length byte == total
    assert reply[2] == 0xD4                       # index 2 opcode
    assert reply[proto.D4_GAMEPAD_MODE_INDEX] == 0x06   # index 3 gamepad mode
    assert reply[proto.D4_ONBOARD_MODE_INDEX] == 0x03   # index 4 onboard mode
    assert proto.frame_checksum(reply[:-1]) == reply[-1]  # index 5 checksum


@pytest.mark.parametrize(
    "gamepad,onboard,hexstr",
    [
        (0x00, 0x00, "a506d400007f"),
        (0x06, 0x03, "a506d4060388"),
        (0x06, 0x00, "a506d4060085"),
        (0x01, 0x01, "a506d4010181"),
    ],
)
def test_d4_reply_test_vectors(gamepad, onboard, hexstr):
    assert proto.build_d4_reply(gamepad, onboard).hex() == hexstr
    decoded = proto.parse_d4_reply(bytes.fromhex(hexstr))
    assert decoded.valid and decoded.checksum_ok
    assert decoded.gamepad_mode == gamepad
    assert decoded.onboard_mode == onboard


def test_d4_reply_structured_parser_extracts_indices_3_and_4():
    decoded = proto.parse_d4_reply(proto.build_d4_reply(0x07, 0x02))
    assert decoded.as_dict()["gamepad_mode_index"] == 3
    assert decoded.as_dict()["onboard_mode_index"] == 4
    assert decoded.gamepad_mode == 0x07
    assert decoded.onboard_mode == 0x02
    assert decoded.errors == []


def test_d4_reply_bad_checksum_is_rejected():
    bad = bytes.fromhex("a506d4000000")           # correct bytes, checksum 0x7F -> 0x00
    decoded = proto.parse_d4_reply(bad)
    assert decoded.valid is False
    assert decoded.checksum_ok is False
    assert any("checksum" in e for e in decoded.errors)


def test_d4_reply_truncated_is_rejected():
    truncated = bytes.fromhex("a506d4")           # indices 3 and 4 missing
    decoded = proto.parse_d4_reply(truncated)
    assert decoded.valid is False
    assert decoded.gamepad_mode is None and decoded.onboard_mode is None
    assert any("truncated" in e for e in decoded.errors)
    # a 5-byte frame still has no room for both payload bytes + checksum
    assert proto.parse_d4_reply(bytes.fromhex("a506d40000")).valid is False


def test_d4_reply_rejects_bad_opcode_and_out_of_range_values():
    wrong_op = bytes([0xA5, 0x06, 0xD6, 0x00, 0x00])
    decoded = proto.parse_d4_reply(wrong_op + bytes([proto.frame_checksum(wrong_op)]))
    assert decoded.valid is False
    assert any("opcode" in e for e in decoded.errors)
    with pytest.raises(ValueError):
        proto.build_d4_reply(0x100, 0x00)


def test_unknown_commands_never_have_reply_bytes():
    # The peripheral only ever transmits for EVIDENCE-BACKED replies; every
    # other opcode resolves to UNKNOWN and is logged with reply_bytes_sent=0.
    for op in (0x04, 0x05, 0x06, 0x70, 0x73, 0xAB, 0xD2, 0xDA, 0xE2, 0xE4, 0xF5, 0xFC, 0xFF):
        spec = proto.reply_status(op)
        assert spec.status == "UNKNOWN"
        assert spec.description  # must state why nothing is sent
