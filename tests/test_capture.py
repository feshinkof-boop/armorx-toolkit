"""Capture inspection tests. All fixtures are synthetic; no hardware is touched."""

import struct
from pathlib import Path

import pytest

from armorx import capture, gip, protocol


def usbmon_record(payload: bytes, *, incl_extra: int = 0, header=64, linktype=220,
                  urb_type=0x43, xfer=1, endpoint=0x83, device=5, bus=1, status=0, endian="<"):
    header_bytes = bytearray(header)
    header_bytes[8] = urb_type
    header_bytes[9] = xfer
    header_bytes[10] = endpoint
    header_bytes[11] = device
    struct.pack_into(endian + "H", header_bytes, 12, bus)
    struct.pack_into(endian + "i", header_bytes, 28, status)
    struct.pack_into(endian + "I", header_bytes, 32, len(payload))
    struct.pack_into(endian + "I", header_bytes, 36, len(payload))
    return bytes(header_bytes) + payload + b"\x00" * incl_extra


def pcap_bytes(records, *, linktype=220, endian="<", magic=0xA1B2C3D4):
    out = struct.pack(endian + "IHHiIII", magic, 2, 4, 0, 0, 65535, linktype)
    for index, record in enumerate(records):
        out += struct.pack(endian + "IIII", 1_700_000_000 + index, index * 1000,
                           len(record), len(record))
        out += record
    return out


def gip_frame(length=48, sequence=7, buttons_low=0x11):
    buf = bytearray(length)
    buf[0], buf[2], buf[3] = 0x20, sequence, 0x2C
    buf[4] = buttons_low
    return bytes(buf)


def test_pcap_round_trip_of_usbmon_records():
    payload = gip_frame()
    data = pcap_bytes([usbmon_record(payload), usbmon_record(b"abc")])
    packets = capture.parse_pcap(data)
    assert len(packets) == 2
    assert packets[0].data == payload
    assert packets[0].endpoint == 0x83
    assert packets[0].urb_type == "complete"
    assert packets[0].transfer_type == "interrupt"
    assert packets[1].data == b"abc"


def test_pcap_big_endian_magic_is_supported():
    # A big-endian file stores the same magic value in its own byte order, so the
    # byte sequence is a1 b2 c3 d4 rather than d4 c3 b2 a1.
    data = pcap_bytes([usbmon_record(b"xy", endian=">")], endian=">", magic=0xA1B2C3D4)
    assert data[:4] == b"\xa1\xb2\xc3\xd4"
    assert capture.parse_pcap(data)[0].data == b"xy"


def test_little_endian_magic_bytes_are_recognised():
    data = pcap_bytes([usbmon_record(b"xy")])
    assert data[:4] == b"\xd4\xc3\xb2\xa1"
    assert capture.parse_pcap(data)[0].data == b"xy"


def test_non_usbmon_linktype_is_rejected():
    data = pcap_bytes([usbmon_record(b"x")], linktype=1)
    with pytest.raises(capture.CaptureError, match="not a usbmon capture"):
        capture.parse_pcap(data)


def test_pcapng_is_rejected_with_a_specific_message():
    data = struct.pack("<I", 0x0A0D0D0A) + bytes(64)
    with pytest.raises(capture.CaptureError, match="pcapng is not supported"):
        capture.parse_pcap(data)


def test_bad_magic_is_rejected():
    with pytest.raises(capture.CaptureError, match="not a pcap file"):
        capture.parse_pcap(b"\x00" * 32)


def test_truncated_pcap_header_is_rejected():
    with pytest.raises(capture.CaptureError, match="fewer than 24"):
        capture.parse_pcap(b"\x00" * 10)


def test_truncated_record_is_rejected():
    data = pcap_bytes([usbmon_record(b"abcd")])[:-2]
    with pytest.raises(capture.CaptureError, match="truncated pcap"):
        capture.parse_pcap(data)


def test_short_usbmon_header_is_rejected():
    record = struct.pack("<IIII", 1, 0, 8, 8) + bytes(8)
    with pytest.raises(capture.CaptureError, match="truncated usbmon header"):
        capture.parse_pcap(pcap_bytes([record]))


def test_empty_pcap_is_rejected():
    with pytest.raises(capture.CaptureError, match="no packet records"):
        capture.parse_pcap(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 220))


def test_limit_stops_early():
    data = pcap_bytes([usbmon_record(b"a"), usbmon_record(b"b"), usbmon_record(b"c")])
    assert len(capture.parse_pcap(data, limit=2)) == 2


def test_inspect_pcap_finds_frames_and_gip_reports():
    frames = protocol.build_a5(0x0B) + protocol.build_a5(0xD2, [0x01])
    data = pcap_bytes([usbmon_record(frames), usbmon_record(gip_frame())])
    report = capture.inspect_bytes(data)
    assert report.kind == "usbmon-pcap"
    assert [f["opcode"] for f in report.frames] == [0x0B, 0xD2]
    assert len(report.gip_reports) == 1
    assert report.gip_reports[0]["form"] == "steady"


def test_pcap_records_without_frames_are_preserved():
    data = pcap_bytes([usbmon_record(b"\x01\x02\x03")])
    report = capture.inspect_bytes(data)
    assert report.frames == []
    assert report.usb_packets[0].data == b"\x01\x02\x03"


def test_hex_text_file_is_accepted(tmp_path: Path):
    p = tmp_path / "dump.txt"
    p.write_text("A5 04 0B B4\nA5 05 D2 01 7D\n")
    report = capture.inspect_file(str(p))
    assert report.kind == "hex-text"
    assert [f["opcode"] for f in report.frames] == [0x0B, 0xD2]


def test_colon_separated_hex_is_accepted(tmp_path: Path):
    p = tmp_path / "dump.txt"
    p.write_text("A5:04:0B:B4")
    assert capture.inspect_file(str(p)).frames[0]["opcode"] == 0x0B


def test_raw_binary_file_is_accepted(tmp_path: Path):
    p = tmp_path / "raw.bin"
    p.write_bytes(protocol.build_a5(0x0B) + protocol.build_a5(0x0B))
    report = capture.inspect_file(str(p))
    assert report.kind == "raw" and len(report.frames) == 2


def test_missing_file_is_a_clear_error(tmp_path: Path):
    with pytest.raises(capture.CaptureError, match="does not exist"):
        capture.inspect_file(str(tmp_path / "nope.bin"))


def test_directory_is_rejected(tmp_path: Path):
    with pytest.raises(capture.CaptureError, match="is a directory"):
        capture.inspect_file(str(tmp_path))


def test_empty_file_is_rejected(tmp_path: Path):
    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    with pytest.raises(capture.CaptureError, match="is empty"):
        capture.inspect_file(str(p))


def test_garbage_bytes_are_reported_not_claimed():
    with pytest.raises(protocol.FrameError, match="no valid frame"):
        capture.inspect_bytes(b"\xde\xad\xbe\xef" * 8)


def test_unknown_spans_are_reported():
    stream = b"\x00\x11" + protocol.build_a5(0x0B) + b"\x99"
    frames, unknown = capture.extract_frames(stream)
    assert len(frames) == 1
    assert unknown == [(0, 2), (6, 7)]


def test_resync_skips_a_corrupt_frame_without_reinterpreting_it():
    good = protocol.build_a5(0x0B)
    corrupt = bytearray(protocol.build_a5(0xEF, [1, 2, 3]))
    corrupt[-1] ^= 0xFF
    frames, unknown = capture.extract_frames(bytes(corrupt) + good)
    assert [protocol.parse_frame(f).opcode for f in frames] == [0x0B]
    assert unknown and unknown[0][0] == 0


def test_no_resync_raises_on_malformed_input():
    with pytest.raises(protocol.FrameError, match="malformed frame"):
        capture.extract_frames(b"\xa5\x04\x0b\x00", resync=False)


def test_summarise_is_readable():
    report = capture.inspect_bytes(protocol.build_a5(0x0B))
    text = capture.summarise(report)
    assert "bytes" in text and "frames" in text


def test_iter_payloads_skips_empty_records():
    data = pcap_bytes([usbmon_record(b""), usbmon_record(b"x")])
    assert list(capture.iter_payloads(capture.parse_pcap(data))) == [b"x"]
