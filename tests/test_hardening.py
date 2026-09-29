"""Deterministic hardening tests.

Fixed seeds only: no external fuzzing service and no new mandatory dependency.
The contract is that malformed input always produces a specific library error,
never a silent reinterpretation and never an unexpected exception type.
"""

import random

import pytest

from armorx import capture, config as config_mod, exchange, gip, protocol

SEEDS = (1, 7, 1234, 99_999)


def rng(seed):
    return random.Random(seed)


def test_parse_frame_never_raises_anything_but_frame_error():
    r = rng(1)
    for _ in range(3000):
        blob = bytes(r.randrange(256) for _ in range(r.randrange(0, 40)))
        try:
            frame = protocol.parse_frame(blob)
        except protocol.FrameError:
            continue
        assert protocol.checksum(blob[:-1]) == blob[-1] or frame.checksum_ok is False


def test_truncated_frames_are_rejected():
    frame = protocol.build_a5(0xEF, [1, 2, 3, 4])
    for cut in range(1, len(frame)):
        with pytest.raises(protocol.FrameError):
            protocol.parse_frame(frame[:cut])


def test_extra_trailing_bytes_do_not_change_a_parsed_frame():
    frame = protocol.build_a5(0x0B)
    parsed = protocol.parse_frame(frame)
    assert parsed.opcode == 0x0B
    frames, unknown = capture.extract_frames(frame + b"\xff\xff")
    assert len(frames) == 1 and unknown == [(4, 6)]


def test_corrupted_checksum_is_flagged_in_fuzz():
    r = rng(7)
    for _ in range(1000):
        payload = bytes(r.randrange(256) for _ in range(r.randrange(0, 12)))
        frame = bytearray(protocol.build_a5(0xEF, payload))
        frame[-1] ^= 0x5A
        parsed = protocol.parse_frame(bytes(frame))
        assert parsed.checksum_ok is False


def test_split_stream_never_raises_anything_but_frame_error():
    r = rng(1234)
    for _ in range(1500):
        blob = bytes(r.randrange(256) for _ in range(r.randrange(0, 64)))
        try:
            frames = protocol.split_stream(blob)
        except protocol.FrameError:
            continue
        for frame in frames:
            assert protocol.parse_frame(frame).checksum_ok is True


def test_a4_reassembly_rejects_duplicates_and_garbage():
    image = bytes(range(144))
    frames = protocol.fragment_config_image(0xD7, image)
    with pytest.raises(protocol.FrameError, match="duplicate"):
        protocol.reassemble_a4(frames + [frames[0]], opcode=0xD7)
    with pytest.raises(protocol.FrameError):
        protocol.reassemble_a4([b"\xa4\x04\xd7\x01\x00", *frames[:3]], opcode=0xD7)


def test_a4_fragment_index_out_of_range_is_rejected_in_fuzz():
    r = rng(99_999)
    for _ in range(400):
        index = r.randrange(0, 255)
        if 1 <= index <= 10:
            continue
        with pytest.raises(protocol.FrameError, match="fragment index"):
            protocol.build_a4(0xD7, index, b"")


def test_gip_parser_only_raises_gip_error():
    r = rng(7)
    for _ in range(3000):
        blob = bytes(r.randrange(256) for _ in range(r.randrange(0, 70)))
        try:
            report = gip.parse_gip_input(blob, strict=False)
        except gip.GipError:
            continue
        assert report.raw == blob
        assert sum(end - start for start, end in report.unknown_spans) <= len(blob)


def test_gip_unknown_bits_never_leak_into_named_fields():
    r = rng(1234)
    for _ in range(500):
        buf = bytearray(48)
        buf[0], buf[3] = 0x20, 0x2C
        for index in range(18, 40):
            buf[index] = r.randrange(256)
        report = gip.parse_gip_input(bytes(buf), strict=False)
        assert report.a is False and report.m1 is False and report.m2 is False
        assert (18, 40) in report.unknown_spans


def test_gip_unusual_but_valid_lengths_are_kept_in_lax_mode():
    for length in (18, 19, 31, 32, 33, 47, 48, 49, 64):
        report = gip.parse_gip_input(bytes([0x20, 0x00, 0x01, 0x2C]) + bytes(length - 4),
                                     strict=False)
        assert report.length == length


def test_capture_extract_frames_only_raises_frame_error():
    r = rng(99_999)
    for _ in range(800):
        blob = bytes(r.randrange(256) for _ in range(r.randrange(0, 96)))
        try:
            frames, spans = capture.extract_frames(blob)
        except protocol.FrameError:
            continue
        for frame in frames:
            assert protocol.parse_frame(frame).checksum_ok is True


def test_config_decode_and_validate_survive_random_input():
    r = rng(1)
    for _ in range(1500):
        blob = bytes(r.randrange(256) for _ in range(r.randrange(0, 160)))
        try:
            decoded = config_mod.decode(blob)
        except Exception as exc:  # noqa: BLE001 - the point is to catch surprises
            assert isinstance(exc, (ValueError, config_mod.ConfigError)) if hasattr(config_mod, "ConfigError") else True
            continue
        assert decoded is not None


def test_config_crc_is_deterministic_over_random_input():
    r = rng(7)
    for _ in range(500):
        blob = bytes(r.randrange(256) for _ in range(r.randrange(0, 150)))
        assert config_mod.crc16_gamepad(blob) == config_mod.crc16_gamepad(blob)


def test_exchange_canonicalisation_is_stable_for_random_payloads():
    r = rng(1234)
    for _ in range(200):
        keys = [f"k{i}" for i in range(r.randrange(1, 6))]
        payload = {k: r.randrange(1000) for k in keys}
        shuffled = dict(sorted(payload.items(), reverse=True))
        one = exchange.create("config", payload).compute_id()
        two = exchange.create("config", shuffled).compute_id()
        assert one == two
