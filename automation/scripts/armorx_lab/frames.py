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
    """A4 05 D8 <nfrags+1> <sum8> - commit frame, all four builds (PROVEN STATIC).

    The length byte is 0x05 (empty segment + 5), not 0x0A: the old reading took the
    tagged Smi `mov x16, #0xa` as a wire byte, but the same List<int> stores 0xA4 as
    #0x148 and 0xD8 as #0x1b0 (both exactly 2x). See smi-audit.md item D1.
    """
    body = bytes([FRAG_HEADER, 0x05, 0xD8, nfrags + 1])
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


def fragment_config(opcode: int, payload: bytes, chunk: int
                    ) -> Tuple[List[bytes], Optional[bytes]]:
    """Split `payload` into A4 fragments of `chunk` bytes and return (frames, commit_frame).

    The chunk size for a given device is subpackageLength()-5 (15 / 43 / 67 for subpkg 20 / 48 / 72).
    **Settled live on the real ARMOR-X Pro (2026-09-27):** every fragment carries the 1-based
    ordinal byte at frame offset 3, so a full fragment is `A4 | (chunk+5) | opcode | idx | chunk |
    sum8` (20 bytes for chunk 15) - the real device's own D6 fragments look like
    `A4 14 D6 01 ...` and it accepted `A4 14 D7 01 ...`, acked `A5 05 D7 00 81` and read back
    byte-identical. The earlier ordinal-less 19-byte form was wrong.

    The commit frame is only meaningful for the 0xD8 macro opcode (the 5-byte
    `A4 05 D8 <nfrags+1> <sum8>`); a D7 config write needs no commit frame - the real device acks
    the last fragment directly.
    """
    frames = [build_frag(opcode, payload[i:i + chunk], index=i // chunk + 1)
              for i in range(0, len(payload), chunk)]
    commit = build_d8_terminator(len(frames)) if opcode == 0xD8 else None
    return frames, commit


# ---------------------------------------------------------------------------------------------
# Button Test input frames (RX) - parser only; nothing here designs bytes
# ---------------------------------------------------------------------------------------------

BUTTON_HEADER = 0xA5
BUTTON_OPCODE = 0x12
BUTTON_SUBCODE = 0x02
BUTTON_FRAME_LEN = 18

# Bit index == key id. Confirmed live against the official 4.0.8 session (2026-09-27):
# A produced mask 00000001 and release produced 00000000.
KEY_NAMES_PROVEN_LIVE: Dict[int, str] = {0: "A"}


@dataclass
class ButtonFrame:
    """One decoded 18-byte Button Test report.

    Layout (PROVEN LIVE, official 4.0.8 session 2026-09-27, and consistent with the 4.0.8
    static parser gate `frame[2] == 0x02`):
        [0]    0xA5
        [1]    0x12
        [2]    0x02          subcode / frame kind
        [3..6] button mask, u32 BIG-endian; bit index == key id
        [7..14] axes
        [15]   LT
        [16]   RT
        [17]   checksum = sum(bytes[0..16]) & 0xFF
    """
    raw: bytes
    mask: int
    axes: bytes
    lt: int
    rt: int
    checksum_ok: bool
    keys: List[int] = field(default_factory=list)


def parse_button_frame(raw: bytes) -> Optional[ButtonFrame]:
    """Parse a Button Test input frame, or return None if it is not one.

    Returning None for anything that is not a well-formed 18-byte button frame is deliberate: the
    D2 command echo (`A5 05 D2 01 7D`) and every other 5-byte reply must never be mistaken for
    input. A frame with a bad length, header, subcode or checksum is NOT input evidence.
    """
    if len(raw) != BUTTON_FRAME_LEN:
        return None
    if raw[0] != BUTTON_HEADER or raw[1] != BUTTON_OPCODE or raw[2] != BUTTON_SUBCODE:
        return None
    if checksum(raw[:BUTTON_FRAME_LEN - 1]) != raw[BUTTON_FRAME_LEN - 1]:
        return None
    mask = int.from_bytes(raw[3:7], "big")
    return ButtonFrame(raw=raw, mask=mask, axes=raw[7:15], lt=raw[15], rt=raw[16],
                       checksum_ok=True, keys=key_ids(mask))


def key_ids(mask: int) -> List[int]:
    """Bit index == key id (NOT id+1). A = 0, B = 1, X = 3, ... (project key map)."""
    return [i for i in range(32) if mask & (1 << i)]


def press_transitions(frames: List[bytes]) -> List[Dict[str, object]]:
    """Collapse a stream of button frames into PRESS/RELEASE transitions per key id.

    A held button is reported ~every 12 ms; those repeats are the SAME press and must not be
    counted as new presses. Only a 0->1 change of a key's bit is a PRESS and only a 1->0 change
    is a RELEASE. Non-frames are ignored.
    """
    parsed = [pf for pf in (parse_button_frame(f) for f in frames) if pf is not None]
    events: List[Dict[str, object]] = []
    state: Dict[int, bool] = {}
    for pf in parsed:
        for kid in range(32):
            down = bool(pf.mask & (1 << kid))
            if down and not state.get(kid, False):
                events.append({"key_id": kid, "event": "PRESS", "mask": f"{pf.mask:08x}", "raw": pf.raw.hex()})
            elif not down and state.get(kid, False):
                events.append({"key_id": kid, "event": "RELEASE", "mask": f"{pf.mask:08x}", "raw": pf.raw.hex()})
            state[kid] = down
    return events


def _selfcheck() -> None:
    bad = []
    for name, (frame, _ev) in KNOWN_FRAMES.items():
        anchor = LIVE_ANCHORS.get(name)
        if anchor is not None and frame.hex(" ").upper() != anchor:
            bad.append((name, frame.hex(" ").upper(), anchor))
    if bad:
        raise AssertionError("live anchor mismatch: %r" % (bad,))


_selfcheck()
