"""Offline framing tests. No hardware is involved anywhere in this file."""

import pytest

from armorx import protocol as P


def test_checksum_is_sum_mod_256():
    assert P.checksum([0xA5, 0x04, 0x0B]) == 0xB4


def test_build_a5_matches_a_documented_frame():
    # A5 04 0B B4 is the sanity query recorded in the protocol documentation.
    assert P.build_a5(0x0B).hex(" ").upper() == "A5 04 0B B4"


def test_build_a5_with_payload_matches_a_documented_frame():
    assert P.build_a5(0xD2, [0x01]).hex(" ").upper() == "A5 05 D2 01 7D"


def test_a5_roundtrip():
    frame = P.build_a5(0xEF, bytes(range(8)))
    parsed = P.parse_frame(frame, require_checksum=True)
    assert parsed.family == P.FAMILY_A5
    assert parsed.opcode == 0xEF
    assert parsed.payload == bytes(range(8))
    assert parsed.checksum_ok is True
    assert parsed.is_fragment is False


def test_length_mismatch_is_rejected():
    with pytest.raises(P.FrameError, match="length byte"):
        P.parse_frame(bytes([0xA5, 0x09, 0x0B, 0xB4]))


def test_bad_checksum_reported_not_raised_by_default():
    bad = bytes([0xA5, 0x04, 0x0B, 0x00])
    parsed = P.parse_frame(bad)
    assert parsed.checksum_ok is False
    with pytest.raises(P.FrameError, match="checksum mismatch"):
        P.parse_frame(bad, require_checksum=True)


def test_unknown_family_is_rejected():
    with pytest.raises(P.FrameError, match="unsupported family"):
        P.parse_frame(bytes([0x42, 0x04, 0x0B, 0x00]))


def test_a4_fragment_parse_carries_the_index():
    frame = P.build_a4(0xD6, 3, bytes(range(15)))
    parsed = P.parse_frame(frame)
    assert parsed.is_fragment is True
    assert parsed.fragment_index == 3
    assert len(parsed.payload) == 15


def test_fragment_index_bounds():
    with pytest.raises(P.FrameError, match="fragment index"):
        P.build_a4(0xD6, 0)
    with pytest.raises(P.FrameError, match="fragment index"):
        P.build_a4(0xD6, 11)


def test_fragment_payload_limits():
    with pytest.raises(P.FrameError, match="at most 15"):
        P.build_a4(0xD6, 1, bytes(16))
    with pytest.raises(P.FrameError, match="at most 9"):
        P.build_a4(0xD6, 10, bytes(10))


def test_config_image_fragments_and_reassembly_roundtrip():
    image = bytes((i * 7) % 256 for i in range(144))
    frames = P.fragment_config_image(0xD7, image)
    assert len(frames) == 10
    assert [len(f) - 5 for f in frames[:9]] == [15] * 9
    assert len(frames[9]) - 5 == 9
    assert P.reassemble_a4(frames, opcode=0xD7) == image


def test_reassembly_uses_the_index_not_arrival_order():
    image = bytes(range(144))
    frames = P.fragment_config_image(0xD7, image)
    shuffled = frames[3:7] + frames[:3] + frames[7:]
    assert P.reassemble_a4(shuffled, opcode=0xD7) == image


def test_reassembly_reports_missing_fragments():
    image = bytes(range(144))
    frames = P.fragment_config_image(0xD7, image)
    with pytest.raises(P.FrameError, match="missing index"):
        P.reassemble_a4(frames[:5], opcode=0xD7)


def test_reassembly_rejects_mixed_opcodes():
    mixed = [P.build_a4(0xD6, 1, bytes(15)), P.build_a4(0xD7, 2, bytes(15))]
    with pytest.raises(P.FrameError, match="several opcodes"):
        P.reassemble_a4(mixed)


def test_wrong_image_length_is_rejected():
    with pytest.raises(P.FrameError, match="144 bytes"):
        P.fragment_config_image(0xD7, bytes(143))


def test_split_stream_walks_pipelined_frames():
    stream = P.build_a5(0x0B) + P.build_a5(0xD2, [0x01]) + P.build_a5(0xD2, [0x00])
    frames = P.split_stream(stream)
    assert len(frames) == 3
    assert [P.parse_frame(f).opcode for f in frames] == [0x0B, 0xD2, 0xD2]


def test_split_stream_rejects_a_truncated_tail():
    with pytest.raises(P.FrameError, match="remain"):
        P.split_stream(P.build_a5(0x0B)[:-1])


def test_decode_hex_accepts_common_shapes():
    assert P.decode_hex("A5 04 0B B4") == P.decode_hex("a5040bb4")
    assert P.decode_hex("A5,04,0B,B4") == P.decode_hex("0xA5 0x04 0x0B 0xB4")
    assert P.decode_hex("A5:04:0B:B4") == bytes([0xA5, 0x04, 0x0B, 0xB4])


def test_decode_hex_rejects_junk():
    with pytest.raises(P.FrameError, match="invalid hex"):
        P.decode_hex("nope")


def test_opcode_table_reports_unknown_rather_than_guessing():
    known = P.describe_opcode(0xD6)
    assert known["name"] == "config_read" and known["evidence"] == P.EVIDENCE_PROVEN
    unknown = P.describe_opcode(0x77)
    assert unknown["name"] is None and unknown["evidence"] == P.EVIDENCE_UNKNOWN


def test_frame_to_dict_is_json_friendly():
    frame = P.parse_frame(P.build_a5(0x0B))
    payload = frame.to_dict()
    assert payload["family"] == "0xA5"
    assert payload["checksum_ok"] is True
    assert payload["opcode_info"]["name"] == "sanity"
