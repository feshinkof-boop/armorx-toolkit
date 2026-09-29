"""Offline capture inspection.

Reads files, never devices. Three input shapes are supported:

* text or hex dumps of ARMORX frames ("A5 04 0B B4", "a5040bb4", ...);
* raw binary streams containing A5/A4 frames;
* usbmon pcap files, parsed by a small built-in reader so that the base install
  needs no packet-processing dependency.

Everything the parser does not recognise is reported as unknown bytes with their
offsets, never silently reinterpreted.
"""

from __future__ import annotations

import pathlib
import shutil
import struct
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from . import gip as gip_mod
from . import protocol as protocol_mod

# LINKTYPE values used by usbmon captures.
DLT_USB_LINUX = 189
DLT_USB_LINUX_MMAPPED = 220
USB_LINUX_HEADER = 48
USB_LINUX_MMAPPED_HEADER = 64
PCAP_MAGIC_LE = 0xA1B2C3D4
PCAP_MAGIC_BE = 0xD4C3B2A1
PCAPNG_MAGIC = 0x0A0D0D0A


class CaptureError(ValueError):
    """Raised when a capture cannot be read at all."""


@dataclass(frozen=True)
class UsbPacket:
    """One usbmon record, reduced to what offline inspection needs."""

    index: int
    timestamp: float
    urb_type: str
    transfer_type: str
    endpoint: int
    device: int
    bus: int
    status: int
    declared_length: int
    data: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": round(self.timestamp, 6),
            "urb_type": self.urb_type,
            "transfer_type": self.transfer_type,
            "endpoint": f"0x{self.endpoint:02X}",
            "device": self.device,
            "bus": self.bus,
            "status": self.status,
            "declared_length": self.declared_length,
            "captured_length": len(self.data),
            "data_hex": self.data.hex(),
        }


@dataclass
class CaptureReport:
    path: str
    kind: str
    size_bytes: int
    frames: list[dict[str, Any]] = field(default_factory=list)
    gip_reports: list[dict[str, Any]] = field(default_factory=list)
    usb_packets: list[UsbPacket] = field(default_factory=list)
    unknown_spans: list[tuple[int, int]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": self.path,
            "kind": self.kind,
            "size_bytes": self.size_bytes,
            "frame_count": len(self.frames),
            "frames": self.frames,
            "gip_report_count": len(self.gip_reports),
            "gip_reports": self.gip_reports,
            "unknown_spans": [list(s) for s in self.unknown_spans],
            "notes": self.notes,
        }
        if self.usb_packets:
            payload["usb_packets"] = [p.to_dict() for p in self.usb_packets]
        return payload


# ---------------------------------------------------------------------------
# usbmon pcap
# ---------------------------------------------------------------------------

_URB_TYPES = {0x53: "submit", 0x43: "complete", 0x53 | 0x80: "submit"}
_XFER_TYPES = {
    0: "isochronous",
    1: "interrupt",
    2: "control",
    3: "bulk",
}


def _classify_urb(value: int) -> str:
    """usbmon encodes 'S'/'C' plus the URB type in one byte."""
    if value in (0x53, 0x53 | 0x80):
        return "submit"
    if value in (0x43, 0x43 | 0x80):
        return "complete"
    char = chr(value & 0x7F).upper()
    return {"S": "submit", "C": "complete"}.get(char, f"0x{value:02x}")


def parse_pcap(data: bytes, *, limit: int | None = None) -> list[UsbPacket]:
    """Parse a classic usbmon pcap into packet records.

    Only classic pcap is supported; a pcapng file raises a specific error rather
    than being misparsed.
    """
    if len(data) < 24:
        raise CaptureError("truncated pcap: fewer than 24 header bytes")
    raw_magic = data[0:4]
    magic = struct.unpack_from("<I", data, 0)[0]
    if magic == PCAPNG_MAGIC:
        raise CaptureError(
            "pcapng is not supported by the built-in reader; save the capture as classic pcap "
            "(tshark -F pcap) instead"
        )
    # A classic pcap stores 0xa1b2c3d4 in its own byte order: the byte sequence
    # decides the endianness, not the value read one way.
    if raw_magic == b"\xd4\xc3\xb2\xa1":
        endian = "<"
    elif raw_magic == b"\xa1\xb2\xc3\xd4":
        endian = ">"
    else:
        raise CaptureError(f"not a pcap file (magic {raw_magic.hex()})")

    linktype = struct.unpack_from(endian + "I", data, 20)[0]
    if linktype not in (DLT_USB_LINUX, DLT_USB_LINUX_MMAPPED):
        raise CaptureError(
            f"link type {linktype} is not a usbmon capture "
            f"(expected {DLT_USB_LINUX} or {DLT_USB_LINUX_MMAPPED})"
        )
    header_size = USB_LINUX_MMAPPED_HEADER if linktype == DLT_USB_LINUX_MMAPPED else USB_LINUX_HEADER

    packets: list[UsbPacket] = []
    offset = 24
    index = 0
    while offset + 16 <= len(data):
        ts_sec, ts_usec, incl, orig = struct.unpack_from(endian + "IIII", data, offset)
        offset += 16
        if incl > len(data) - offset:
            raise CaptureError(
                f"truncated pcap: record {index} claims {incl} bytes but only "
                f"{len(data) - offset} remain"
            )
        record = data[offset:offset + incl]
        offset += incl
        index += 1
        if len(record) < header_size:
            raise CaptureError(f"truncated usbmon header in record {index}")
        urb_type = record[8]
        transfer_type = record[9]
        endpoint = record[10]
        device = record[11]
        bus = struct.unpack_from(endian + "H", record, 12)[0]
        status = struct.unpack_from(endian + "i", record, 28)[0]
        declared = struct.unpack_from(endian + "I", record, 32)[0]
        captured = struct.unpack_from(endian + "I", record, 36)[0]
        payload = record[header_size:]
        if captured and captured <= len(payload):
            payload = payload[:captured]
        packets.append(UsbPacket(
            index=index,
            timestamp=ts_sec + ts_usec / 1_000_000,
            urb_type=_classify_urb(urb_type),
            transfer_type=_XFER_TYPES.get(transfer_type, f"0x{transfer_type:02x}"),
            endpoint=endpoint,
            device=device,
            bus=bus,
            status=status,
            declared_length=declared,
            data=payload,
        ))
        if limit is not None and len(packets) >= limit:
            break
    if not packets:
        raise CaptureError("pcap contains no packet records")
    return packets


# ---------------------------------------------------------------------------
# hex / binary
# ---------------------------------------------------------------------------

def _looks_like_hex_dump(text: str) -> bool:
    tokens = text.replace(",", " ").replace(":", " ").split()
    if not tokens:
        return False
    hexish = sum(1 for t in tokens if len(t) <= 4 and all(c in "0123456789abcdefABCDEF" for c in t))
    return hexish / len(tokens) > 0.9


def extract_frames(data: bytes, *, family: Iterable[int] = (protocol_mod.FAMILY_A5, protocol_mod.FAMILY_A4),
                   resync: bool = True) -> tuple[list[bytes], list[tuple[int, int]]]:
    """Split a byte stream into frames, reporting the spans that were skipped.

    A malformed frame is never re-flagged as a smaller valid one: on a length or
    checksum error the scanner resynchronises at the *next* family byte and the
    skipped bytes are returned as an unknown span.
    """
    families = set(family)
    frames: list[bytes] = []
    unknown: list[tuple[int, int]] = []
    i = 0
    scan_start = 0
    while i < len(data):
        if data[i] not in families:
            i += 1
            continue
        if i + 2 > len(data):
            break
        length = data[i + 1]
        end = i + length
        if length >= 3 and end <= len(data) and data[end - 1] == protocol_mod.checksum(data[i:end - 1]):
            frames.append(data[i:end])
            if scan_start < i:
                unknown.append((scan_start, i))
            i = end
            scan_start = i
            continue
        if not resync:
            raise protocol_mod.FrameError(f"malformed frame at offset {i}")
        i += 1
    if scan_start < len(data):
        unknown.append((scan_start, len(data)))
    if not frames and unknown:
        raise protocol_mod.FrameError("no valid frame found in this input")
    return frames, unknown


def inspect_bytes(data: bytes, *, name: str = "<memory>", usb_limit: int | None = None) -> CaptureReport:
    """Inspect an in-memory capture."""
    report = CaptureReport(path=name, kind="unknown", size_bytes=len(data))
    if data[:4] == b"\xd4\xc3\xb2\xa1" or data[:4] == b"\xa1\xb2\xc3\xd4" or data[:4] == b"\x0a\x0d\x0d\x0a":
        report.kind = "usbmon-pcap"
        packets = parse_pcap(data, limit=usb_limit)
        report.usb_packets = packets
        report.notes.append(
            "usbmon records were parsed with the built-in reader; payload bytes are the URB "
            "data as captured, nothing is decoded further without evidence"
        )
        for packet in packets:
            for frame in _frames_in_payload(packet.data):
                info = protocol_mod.parse_frame(frame).to_dict()
                info["packet_index"] = packet.index
                info["timestamp"] = round(packet.timestamp, 6)
                report.frames.append(info)
            if gip_mod.is_probable_input_report(packet.data):
                entry = gip_mod.parse_gip_input(packet.data, strict=False).to_dict()
                entry["packet_index"] = packet.index
                report.gip_reports.append(entry)
        return report

    report.kind = "raw"
    frames, unknown = extract_frames(data)
    report.unknown_spans = unknown
    for frame in frames:
        report.frames.append(protocol_mod.parse_frame(frame).to_dict())
    for frame in frames:
        if len(frame) in (32, 48) and gip_mod.is_probable_input_report(frame):
            report.gip_reports.append(gip_mod.parse_gip_input(frame, strict=False).to_dict())
    return report


def _frames_in_payload(payload: bytes) -> list[bytes]:
    try:
        frames, _ = extract_frames(payload)
    except protocol_mod.FrameError:
        return []
    return frames


def inspect_file(path: str, *, usb_limit: int | None = None) -> CaptureReport:
    """Inspect a file on disk: hex text, raw binary or usbmon pcap."""
    p = pathlib.Path(path)
    if not p.exists():
        raise CaptureError(f"{path} does not exist")
    if p.is_dir():
        raise CaptureError(f"{path} is a directory, not a capture file")
    data = p.read_bytes()
    if not data:
        raise CaptureError(f"{path} is empty")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    if text is not None and _looks_like_hex_dump(text):
        try:
            decoded = protocol_mod.decode_hex(text)
        except protocol_mod.FrameError as exc:
            raise CaptureError(f"{path} looks like a hex dump but could not be decoded: {exc}") from exc
        report = inspect_bytes(decoded, name=str(p), usb_limit=usb_limit)
        report.kind = "hex-text"
        report.size_bytes = len(data)
        return report
    report = inspect_bytes(data, name=str(p), usb_limit=usb_limit)
    return report


def summarise(report: CaptureReport) -> str:
    """One-line human summary."""
    bits = [f"{report.path}: {report.kind}, {report.size_bytes} bytes"]
    if report.usb_packets:
        bits.append(f"{len(report.usb_packets)} usbmon records")
    bits.append(f"{len(report.frames)} frames")
    if report.gip_reports:
        bits.append(f"{len(report.gip_reports)} gip reports")
    if report.unknown_spans:
        bits.append(f"{len(report.unknown_spans)} unknown spans")
    return ", ".join(bits)


def external_reader_hint() -> str | None:
    """Return a hint about an optional external reader, if one is installed."""
    for tool in ("tshark", "tcpdump"):
        found = shutil.which(tool)
        if found:
            return f"{tool} is available at {found} for formats the built-in reader does not cover"
    return None


def iter_payloads(packets: Sequence[UsbPacket]) -> Iterable[bytes]:
    for packet in packets:
        if packet.data:
            yield packet.data
