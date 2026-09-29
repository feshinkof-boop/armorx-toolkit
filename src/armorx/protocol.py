"""Offline ARMORX Pro framing and opcode helpers.

Everything here is offline: no transport, no device access. Frames are built
and parsed as plain bytes so contributors can validate captures and fixtures
without hardware.

Evidence levels used throughout the toolkit:

* ``proven``          - observed on hardware or in captured traffic, or stated
                        verbatim in the recovered protocol documentation.
* ``strong_evidence`` - several independent observations agree; hardware
                        confirmation still outstanding.
* ``unknown``         - deliberately unresolved and left unresolved here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Sequence

FAMILY_A5 = 0xA5
FAMILY_A4 = 0xA4

#: 144-byte configuration image split into ten A4 fragments: 9*15 + 9.
CONFIG_IMAGE_LEN = 144
FRAGMENT_DATA_BYTES = 15
FRAGMENT_DATA_BYTES_LAST = 9
FRAGMENT_COUNT = 10

EVIDENCE_PROVEN = "proven"
EVIDENCE_STRONG = "strong_evidence"
EVIDENCE_UNKNOWN = "unknown"


class FrameError(ValueError):
    """Raised when a byte string cannot be interpreted as a frame."""


def checksum(data: Sequence[int]) -> int:
    """Sum-mod-256 checksum used by both A5 and A4 frames.

    The checksum byte is the low byte of the sum of every preceding byte, so
    ``checksum(frame[:-1]) == frame[-1]`` for a valid frame.
    """
    return sum(data) & 0xFF


@dataclass(frozen=True)
class Opcode:
    code: int
    name: str
    summary: str
    evidence: str = EVIDENCE_PROVEN


#: Opcodes with recovered meaning. Anything absent is reported as unknown
#: rather than guessed.
OPCODES: dict[int, Opcode] = {
    0x0B: Opcode(0x0B, "sanity", "payload-free sanity query; observed reply A5 05 0B 30 E5"),
    0x0E: Opcode(0x0E, "config_commit", "configuration persistence, transmitted as A4 fragments; "
                                        "observed as A5 05 0E 00 B8 and A5 05 0E 01 B9"),
    0x0F: Opcode(0x0F, "config_commit_ack", "not independently documented beyond its use in the commit pair"),
    0xD2: Opcode(0xD2, "runtime_input_stream", "A5 05 D2 01 7D enables the raw input stream, "
                                                "A5 05 D2 00 7C disables it"),
    0xD4: Opcode(0xD4, "mapping_read", "key-mapping family"),
    0xD6: Opcode(0xD6, "config_read", "payload-free request; the device replies with ten A4 fragments "
                                       "whose reassembled payload is exactly 144 bytes"),
    0xD7: Opcode(0xD7, "config_write", "sends the complete 144-byte configuration image as ten A4 fragments"),
    0xD8: Opcode(0xD8, "macro_config", "macro record family"),
    0xD9: Opcode(0xD9, "firmware_only", "present in firmware dispatch, not observed on the wire"),
    0xF6: Opcode(0xF6, "gate", "firmware emits 0xF6 with a one-byte payload; gate literal 330,10,492,256 "
                                "corresponds to A5 05 F6 80 20"),
    0xF7: Opcode(0xF7, "stick_step_length", "stick step-length setting, 16-bit little-endian; "
                                            "a read produces no reply on healthy links"),
    0xF8: Opcode(0xF8, "brightness_compensation", "brightness compensation read"),
    0xFC: Opcode(0xFC, "dpi", "DPI family, selector masked with 0x0F"),
    0xFF: Opcode(0xFF, "ack", "acknowledgement/echo, e.g. A5 05 FF FC A5"),
}


def describe_opcode(code: int) -> dict:
    op = OPCODES.get(code)
    if op is None:
        return {"opcode": code, "opcode_hex": f"0x{code:02X}", "name": None,
                "summary": "not recovered", "evidence": EVIDENCE_UNKNOWN}
    return {"opcode": op.code, "opcode_hex": f"0x{op.code:02X}", "name": op.name,
            "summary": op.summary, "evidence": op.evidence}


@dataclass(frozen=True)
class Frame:
    """A parsed A5 or A4 frame."""

    family: int
    length: int
    opcode: int
    payload: bytes
    raw: bytes
    checksum_ok: bool
    fragment_index: int | None = None
    is_fragment: bool = False

    @property
    def family_hex(self) -> str:
        return f"0x{self.family:02X}"

    def to_dict(self) -> dict:
        base = {
            "family": self.family_hex,
            "length": self.length,
            "opcode": self.opcode,
            "opcode_hex": f"0x{self.opcode:02X}",
            "payload_hex": self.payload.hex(" "),
            "raw_hex": self.raw.hex(" "),
            "checksum_ok": self.checksum_ok,
            "opcode_info": describe_opcode(self.opcode),
        }
        if self.is_fragment:
            base["fragment_index"] = self.fragment_index
        return base


def build_a5(opcode: int, payload: Sequence[int] = ()) -> bytes:
    """Build a short A5 frame: ``A5 | length | opcode | data... | checksum``."""
    body = bytearray([FAMILY_A5, 0, opcode])
    body.extend(payload)
    if len(body) > 0xFF:
        raise FrameError("payload too long for the single-byte length field")
    body[1] = len(body) + 1
    body.append(checksum(body))
    return bytes(body)


def build_a4(opcode: int, fragment_index: int, payload: Sequence[int] = ()) -> bytes:
    """Build one A4 fragment: ``A4 | length | opcode | index | data... | checksum``."""
    if not 1 <= fragment_index <= FRAGMENT_COUNT:
        raise FrameError(f"fragment index must be 1..{FRAGMENT_COUNT}, got {fragment_index}")
    max_payload = FRAGMENT_DATA_BYTES_LAST if fragment_index == FRAGMENT_COUNT else FRAGMENT_DATA_BYTES
    if len(payload) > max_payload:
        raise FrameError(f"fragment {fragment_index} carries at most {max_payload} data bytes")
    body = bytearray([FAMILY_A4, 0, opcode, fragment_index])
    body.extend(payload)
    body[1] = len(body) + 1
    body.append(checksum(body))
    return bytes(body)


def parse_frame(data: Sequence[int], *, require_checksum: bool = False) -> Frame:
    """Parse one frame.

    ``require_checksum=True`` rejects a frame whose trailing byte is not the
    sum-mod-256 of the preceding bytes. By default a bad checksum is reported
    through :attr:`Frame.checksum_ok` so that capture tooling can still show
    damaged frames instead of throwing them away.
    """
    buf = bytes(data)
    if len(buf) < 4:
        raise FrameError(f"frame too short: {len(buf)} bytes")
    if buf[0] not in (FAMILY_A5, FAMILY_A4):
        raise FrameError(f"unsupported family byte 0x{buf[0]:02X}")
    length = buf[1]
    if length != len(buf):
        raise FrameError(f"length byte {length} does not match {len(buf)} bytes on the wire")
    expected = checksum(buf[:-1])
    ok = expected == buf[-1]
    if require_checksum and not ok:
        raise FrameError(f"checksum mismatch: expected 0x{expected:02X}, found 0x{buf[-1]:02X}")
    if buf[0] == FAMILY_A5:
        return Frame(FAMILY_A5, length, buf[2], buf[3:-1], buf, ok)
    if length < 5:
        raise FrameError("A4 fragment needs at least an index byte")
    return Frame(FAMILY_A4, length, buf[2], buf[4:-1], buf, ok,
                 fragment_index=buf[3], is_fragment=True)


def fragment_config_image(opcode: int, image: Sequence[int]) -> list[bytes]:
    """Split a 144-byte configuration image into its ten A4 fragments."""
    data = bytes(image)
    if len(data) != CONFIG_IMAGE_LEN:
        raise FrameError(f"configuration image must be {CONFIG_IMAGE_LEN} bytes, got {len(data)}")
    frames: list[bytes] = []
    for index in range(1, FRAGMENT_COUNT + 1):
        start = (index - 1) * FRAGMENT_DATA_BYTES
        size = FRAGMENT_DATA_BYTES_LAST if index == FRAGMENT_COUNT else FRAGMENT_DATA_BYTES
        frames.append(build_a4(opcode, index, data[start:start + size]))
    return frames


def reassemble_a4(frames: Iterable[bytes | Frame], *, opcode: int | None = None,
                  total_len: int = CONFIG_IMAGE_LEN) -> bytes:
    """Reassemble A4 fragments by fragment index.

    Fragments may arrive interleaved because write-without-response traffic can
    be pipelined, so the fragment index is used as a write offset rather than
    trusting arrival order. Missing fragments are reported instead of zero
    filled.
    """
    slots: dict[int, bytes] = {}
    seen_opcodes: set[int] = set()
    for item in frames:
        fr = item if isinstance(item, Frame) else parse_frame(item)
        if not fr.is_fragment:
            raise FrameError(f"expected an A4 fragment, got family {fr.family_hex}")
        if opcode is not None and fr.opcode != opcode:
            continue
        seen_opcodes.add(fr.opcode)
        index = fr.fragment_index or 0
        if index in slots:
            raise FrameError(f"duplicate fragment index {index}")
        slots[index] = bytes(fr.payload)
    if not slots:
        raise FrameError("no fragments matched")
    if len(seen_opcodes) > 1:
        raise FrameError(f"fragments from several opcodes were mixed: "
                         f"{sorted(hex(o) for o in seen_opcodes)}")
    missing = [i for i in range(1, FRAGMENT_COUNT + 1) if i not in slots]
    if missing:
        raise FrameError(f"incomplete fragment set, missing index(es) {missing}")
    out = bytearray()
    for index in range(1, FRAGMENT_COUNT + 1):
        out.extend(slots[index])
    if total_len and len(out) != total_len:
        raise FrameError(f"reassembled payload is {len(out)} bytes, expected {total_len}")
    return bytes(out)


def decode_hex(text: str) -> bytes:
    """Parse a hex string, tolerating spaces, commas, colons and 0x prefixes."""
    cleaned = text.replace(",", " ").replace(":", " ").replace("0x", " ").replace("0X", " ")
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        raise FrameError("no hex bytes supplied")
    if " " not in cleaned and len(cleaned) % 2 == 0:
        tokens = [cleaned[i:i + 2] for i in range(0, len(cleaned), 2)]
    else:
        tokens = cleaned.split()
    try:
        return bytes(int(tok, 16) for tok in tokens)
    except ValueError as exc:
        raise FrameError(f"invalid hex input: {exc}") from exc


def split_stream(data: bytes) -> list[bytes]:
    """Split a concatenated byte stream into individual frames.

    The length byte is authoritative, so a stream of pipelined frames can be
    walked without any heuristics.
    """
    frames: list[bytes] = []
    offset = 0
    while offset < len(data):
        if offset + 2 > len(data):
            raise FrameError(f"trailing {len(data) - offset} byte(s) cannot form a frame")
        if data[offset] not in (FAMILY_A5, FAMILY_A4):
            raise FrameError(f"unsupported family byte 0x{data[offset]:02X} at offset {offset}")
        length = data[offset + 1]
        if length < 4:
            raise FrameError(f"frame at offset {offset} declares an impossible length {length}")
        end = offset + length
        if end > len(data):
            raise FrameError(f"frame at offset {offset} claims {length} bytes but only "
                             f"{len(data) - offset} remain")
        candidate = data[offset:end]
        if candidate[-1] != checksum(candidate[:-1]):
            raise FrameError(f"frame at offset {offset} has a bad checksum")
        frames.append(candidate)
        offset = end
    return frames


@dataclass
class DecodeReport:
    """Human- and machine-readable decode of one frame or a byte stream."""

    frames: list[Frame] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"frame_count": len(self.frames), "frames": [f.to_dict() for f in self.frames]}
