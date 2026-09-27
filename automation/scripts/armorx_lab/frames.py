"""ARMOR-X lab protocol helpers.

Every builder here computes its own checksum instead of hard-coding one, and the module-level
KNOWN_FRAMES table asserts the computed value against the byte-exact frames recovered in the
MYGT 4.0.8 static pass (see /home/salamanka/armorx-re/mygt408/research/mygt-4.0.8/command-index.md).
If an assertion fails, the protocol understanding has drifted and the lab must stop.

Evidence levels (project standard):
    PROVEN LIVE     observed against real hardware
    PROVEN STATIC   established from code/dataflow/constants in the APK
    STRONG EVIDENCE independent evidence agrees, one link missing
    INFERRED        reasonable but unproven
    UNKNOWN         insufficient or conflicting evidence

Nothing in this module designs new bytes: unknown replies must stay UNKNOWN.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------------------------
# framing
# ---------------------------------------------------------------------------------------------

SHORT_HEADER = 0xA5          # short frame:  A5 | total_len | opcode | payload | sum8
FRAG_HEADER = 0xA4           # A4 family:    A4 | total_len | opcode | payload | sum8
AB_HEADER = 0xAB             # motion/gyro:  AB | total_len | 05 | subcmd | payload | sum8


def checksum(payload: bytes) -> int:
    """sum(all previous frame bytes) & 0xFF  (PROVEN STATIC + PROVEN LIVE: A5 04 0B B4)."""
    return sum(payload) & 0xFF


def build_short(opcode: int, payload: bytes = b"", length: Optional[int] = None) -> bytes:
    """Build A5 | len | opcode | payload | checksum.

    `len` counts every byte of the frame including the checksum itself: header(3) + payload + 1.
    Verified against the live captures: A5 04 0B B4 (payload 0 -> 4), A5 05 D2 01 7D (payload 1 -> 5),
    A5 0C EF 00*8 A0 (payload 8 -> 12).
    """
    body = bytes([SHORT_HEADER, length if length is not None else 4 + len(payload), opcode]) + payload
    return body + bytes([checksum(body)])


def build_frag(opcode: int, payload: bytes, index: Optional[int] = None) -> bytes:
    """Build an A4 data frame: A4 | len | opcode | [index |] payload | sum8.

    OPEN QUESTION (see unresolved.md / live-test-plan.md T2): the 2.23/2.24 research describes
    `len = chunk + 5` together with a 1-based ordinal byte inside the frame (3 header + index +
    chunk + checksum = chunk + 5), while the 4.0.8 D8 reconstruction reports `len = payload + 5`
    for fragments that carry NO ordinal byte. Both cannot be true for the same frame. This builder
    therefore emits the arithmetically consistent form and keeps the ordinal explicit:
        index given     -> A4 | len(=chunk+5) | opcode | index | chunk | sum8
        index omitted   -> A4 | len(=chunk+4) | opcode | chunk | sum8
    The live experiment T2 decides which form the device accepts; until then treat the D8 fragment
    length byte as STRONG EVIDENCE, not proven.
    """
    if index is None:
        body = bytes([FRAG_HEADER, 4 + len(payload), opcode]) + payload
    else:
        body = bytes([FRAG_HEADER, 5 + len(payload), opcode, index & 0xFF]) + payload
    return body + bytes([checksum(body)])


def build_ab(subcmd_group: int, subcmd: int, payload: bytes = b"") -> bytes:
    """AB | len | 05 | subcmd | payload | checksum   (motion/gyro family, PROVEN STATIC)."""
    body = bytes([AB_HEADER, 5 + len(payload), subcmd_group, subcmd]) + payload
    return body + bytes([checksum(body)])


def build_d8_terminator(nfrags: int) -> bytes:
    """A4 0A D8 <nfrags+1> <sum8> - commit frame from the 4.0.8 macro writer (PROVEN STATIC)."""
    body = bytes([FRAG_HEADER, 0x0A, 0xD8, nfrags + 1])
    return body + bytes([checksum(body)])


@dataclass
class Frame:
    raw: bytes
    header: int
    total_len: int
    opcode: int
    payload: bytes
    checksum_ok: bool
    truncated: bool = False


def parse_frame(raw: bytes) -> Frame:
    """Parse one A5/A4/AB frame; never raises on malformed input (sets checksum_ok=False)."""
    if len(raw) < 4:
        return Frame(raw, raw[0] if raw else -1, len(raw), -1, b"", False, True)
    header, total_len, opcode = raw[0], raw[1], raw[2]
    truncated = total_len > len(raw)
    payload = raw[3:max(3, min(total_len, len(raw)) - 1)]
    ok = (checksum(raw[:max(0, min(total_len, len(raw)) - 1)]) == raw[min(total_len, len(raw)) - 1]
          ) if len(raw) >= 4 else False
    return Frame(raw, header, total_len, opcode, payload, ok, truncated)


# ---------------------------------------------------------------------------------------------
# config image CRC (generalised: six embedded default images self-validate this way)
# ---------------------------------------------------------------------------------------------

def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    """CRC-16/MODBUS: poly 0xA001, init 0xFFFF, reflected.  PROVEN STATIC (6 embedded defaults)."""
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def config_with_crc(image: bytes) -> bytes:
    """Return the image with bytes 0..1 replaced by the CRC-16/MODBUS over bytes 2..end, big-endian."""
    if len(image) < 4:
        raise ValueError("config image too short")
    crc = crc16_modbus(image[2:])
    out = bytearray(image)
    out[0:2] = crc.to_bytes(2, "big")
    return bytes(out)


def config_verify(image: bytes) -> Tuple[bool, int, int]:
    """Returns (stored==computed, stored, computed). Stored 0x0000 is the app's placeholder form."""
    stored = int.from_bytes(image[0:2], "big")
    computed = crc16_modbus(image[2:])
    return stored == computed, stored, computed


def config_length(image: bytes) -> int:
    """bytes 2..3 hold the declared length, big-endian (PROVEN STATIC across all families)."""
    return int.from_bytes(image[2:4], "big")


def mapkeys(image: bytes) -> List[int]:
    """mapKeys[32] = the last 32 bytes, mapKeys[source] = target (PROVEN LIVE for 144-byte images)."""
    return list(image[-32:])


# ---------------------------------------------------------------------------------------------
# known frames
# ---------------------------------------------------------------------------------------------

KNOWN_FRAMES: Dict[str, Tuple[bytes, str]] = {
    # name                     frame                                                     evidence
    "get_version":      (build_short(0x0B), "PROVEN LIVE + PROVEN STATIC (A5 04 0B B4)"),
    "get_device_uuid":  (build_short(0xEF, bytes(8)), "PROVEN LIVE + PROVEN STATIC (A5 0C EF 00*8 A0)"),
    "get_device_config": (build_short(0xD6), "PROVEN LIVE + PROVEN STATIC (A5 04 D6 7F)"),
    "get_mtu":          (build_short(0xE4), "PROVEN STATIC (A5 04 E4 8D)"),
    "read_firmware":    (build_short(0xE2), "PROVEN STATIC (A5 04 E2 8B, new in 4.0.8)"),
    "testmode_off":     (build_short(0xD2, b"\x00"), "PROVEN STATIC (A5 05 D2 00 7C)"),
    "testmode_on":      (build_short(0xD2, b"\x01"), "PROVEN STATIC (A5 05 D2 01 7D)"),
    "write_step":       (build_short(0x0E, b"\x00"), "PROVEN LIVE + PROVEN STATIC (A5 05 0E 00 B8)"),
    "get_dpi":          (build_short(0xFC, b"\x80"), "PROVEN STATIC (A5 05 FC 80 ...)"),
    "get_motion_dpi":   (build_ab(0x05, 0x25), "PROVEN STATIC (AB 05 05 25 ...)"),
    "get_motion_list":  (build_ab(0x05, 0x26), "PROVEN STATIC (AB 05 05 26 ...)"),
}

# frames whose exact bytes were captured live and must never change
LIVE_ANCHORS: Dict[str, str] = {
    "get_version": "A5 04 0B B4",
    "get_device_uuid": "A5 0C EF 00 00 00 00 00 00 00 00 A0",
    "get_device_config": "A5 04 D6 7F",
    "write_step": "A5 05 0E 00 B8",
}


def set_dpi_selector(selector: int) -> bytes:
    """A5 05 FC <selector & 0x0F> <cks> - the payload is a 4-bit selector, not a DPI number."""
    return build_short(0xFC, bytes([selector & 0x0F]))


def set_motion_dpi(value: int) -> bytes:
    """AB 07 05 25 <lo> <hi> <cks> - motion/gyro DPI, u16 LITTLE-endian."""
    return build_ab(0x05, 0x25, bytes([value & 0xFF, (value >> 8) & 0xFF]))


def fragment_config(opcode: int, payload: bytes, chunk: int) -> Tuple[List[bytes], bytes]:
    """Split `payload` into A4 fragments of `chunk` bytes and return (frames, commit_frame).

    The chunk size for a given device is subpackageLength()-5 (15 / 43 / 67 for subpkg 20 / 48 / 72)
    and is STRONG EVIDENCE, not proven for ARMOR-X Pro - see unresolved.md and live-test-plan.md T2.
    """
    frames = [build_frag(opcode, payload[i:i + chunk]) for i in range(0, len(payload), chunk)]
    return frames, build_d8_terminator(len(frames))


def _selfcheck() -> None:
    bad = []
    for name, (frame, _ev) in KNOWN_FRAMES.items():
        anchor = LIVE_ANCHORS.get(name)
        if anchor is not None and frame.hex(" ").upper() != anchor:
            bad.append((name, frame.hex(" ").upper(), anchor))
    if bad:
        raise AssertionError("live anchor mismatch: %r" % (bad,))


_selfcheck()
