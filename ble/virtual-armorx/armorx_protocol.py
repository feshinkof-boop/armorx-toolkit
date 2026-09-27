"""ARMOR-X Pro wire-protocol primitives (MYGT 4.0.8) for the virtual peripheral.

Everything in this module is derived ONLY from the canonical 4.0.8 research.
Each constant carries the research file it came from. Nothing here is invented;
where the research marks a value UNKNOWN the code returns UNKNOWN and never
fabricates bytes.

Canonical research root (canonical copy, may be mirrored under
/home/salamanka/armorx-lab/baselines/imported-research/):
    /home/salamanka/armorx-re/mygt408/research/mygt-4.0.8/
Additional cross-version / live-capture evidence:
    /home/salamanka/armorx-re/repo/docs/android-protocol.md
    /home/salamanka/armorx-re/repo/docs/usb-protocol.md
    /home/salamanka/armorx-re/repo/research/apk-2.23.0609/ef-dataflow.md
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Research source locations
# ---------------------------------------------------------------------------

RESEARCH_CANONICAL = Path("/home/salamanka/armorx-re/mygt408/research/mygt-4.0.8")
RESEARCH_MIRROR = Path("/home/salamanka/armorx-lab/baselines/imported-research")
DEFAULT_CONFIG_144_NAME = "default_001_device___len_144.json"


def _candidate_roots() -> list[Path]:
    """Roots to search for a research file, mirror first (lab baseline when filled)."""
    return [RESEARCH_MIRROR, RESEARCH_CANONICAL]


def research_file(relative: str) -> Path:
    """Locate a research artefact, preferring the lab mirror then the canonical tree."""
    for root in _candidate_roots():
        candidate = root / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"research file '{relative}' not found under "
        f"{' or '.join(str(r) for r in _candidate_roots())}"
    )


def _research_dir() -> Path:
    """Prefer the lab mirror when it has the research index, else the canonical tree."""
    for root in _candidate_roots():
        if (root / "ble-architecture.md").is_file():
            return root
    # Fall back to the canonical path so the error message names it.
    return RESEARCH_CANONICAL


# ---------------------------------------------------------------------------
# Frame constants  (ble-architecture.md "Transport stack";
#                   docs/android-protocol.md "Short frames")
# ---------------------------------------------------------------------------

FRAME_SHORT = 0xA5  # A5 | length | opcode | data... | checksum
FRAME_FRAG = 0xA4   # A4 | length | opcode | fragment_index | data... | checksum

CHECKSUM_RULE = "checksum = (sum of all preceding frame bytes) & 0xFF"

# opcode -> semantics; the request frames are byte-exact in command-index.md
OPCODES: dict[int, dict[str, str]] = {
    0x04: {"name": "getBattery", "evidence": "command-index.md 0x04"},
    0x05: {"name": "UNKNOWN", "evidence": "command-index.md 0x05"},
    0x06: {"name": "UNKNOWN", "evidence": "command-index.md 0x06"},
    0x0B: {"name": "getZKMVer", "evidence": "command-index.md 0x0B; ef-dataflow.md"},
    0x0E: {"name": "writeDevice", "evidence": "command-index.md 0x0E; android-protocol.md"},
    0x1A: {"name": "reset", "evidence": "command-index.md 0x1A"},
    0x1B: {"name": "startCalibration/stopCalibration", "evidence": "command-index.md 0x1B"},
    0x25: {"name": "getMotionDpi", "evidence": "command-index.md 0x25"},
    0x26: {"name": "getMotionList", "evidence": "command-index.md 0x26"},
    0x70: {"name": "lighting config (R3)", "evidence": "command-index.md 0x70"},
    0x73: {"name": "light enable state", "evidence": "command-index.md 0x73"},
    0xA6: {"name": "UNKNOWN", "evidence": "command-index.md 0xA6"},
    0xA9: {"name": "(doujiang keyboard) empty packet", "evidence": "command-index.md 0xA9"},
    0xAB: {"name": "UNKNOWN", "evidence": "command-index.md 0xAB"},
    0xD2: {"name": "testModeSwitch", "evidence": "command-index.md 0xD2"},
    0xD3: {"name": "getMaxSize", "evidence": "command-index.md 0xD3"},
    0xD4: {"name": "getInputModel", "evidence": "command-index.md 0xD4"},
    0xD6: {"name": "getDeviceConfig", "evidence": "command-index.md 0xD6"},
    0xD7: {"name": "writeDeviceConfig", "evidence": "command-index.md 0xD7"},
    0xD8: {"name": "macro device protocol", "evidence": "d8-macro.md"},
    0xDA: {"name": "UNKNOWN", "evidence": "command-index.md 0xDA"},
    0xDD: {"name": "charging light effect", "evidence": "command-index.md 0xDD"},
    0xE1: {"name": "connect mode", "evidence": "command-index.md 0xE1"},
    0xE2: {"name": "readFirmware", "evidence": "command-index.md 0xE2; unresolved.md §8"},
    0xE4: {"name": "getMTU", "evidence": "command-index.md 0xE4"},
    0xEF: {"name": "getDeviceUUID", "evidence": "command-index.md 0xEF; ef-dataflow.md"},
    0xF5: {"name": "keyboard/doujiang light - logo colour", "evidence": "command-index.md 0xF5"},
    0xF6: {"name": "keyboard/doujiang light - charging mode", "evidence": "command-index.md 0xF6"},
    0xF7: {"name": "step length / SOCD", "evidence": "command-index.md 0xF7"},
    0xF8: {"name": "brightness compensation", "evidence": "command-index.md 0xF8"},
    0xFC: {"name": "DPI / transcribe control", "evidence": "command-index.md 0xFC"},
    0xFD: {"name": "macro/transcribe response", "evidence": "command-index.md 0xFD"},
    0xFF: {"name": "lighting payload marker", "evidence": "command-index.md 0xFF"},
}


def opcode_name(opcode: int) -> str:
    return OPCODES.get(opcode, {}).get("name", "UNKNOWN")


# ---------------------------------------------------------------------------
# Checksum + CRC
# ---------------------------------------------------------------------------

def frame_checksum(data: bytes) -> int:
    """Short/fragment frame checksum: (sum of all preceding bytes) & 0xFF.

    config-144-reconstruction.md §6 (getCheckSum); d8-macro.md §3.4.
    """
    return sum(data) & 0xFF


def crc16_modbus(data: bytes, init: int = 0xFFFF, poly: int = 0xA001) -> int:
    """CRC-16/MODBUS (poly 0xA001, init 0xFFFF) -- config image CRC.

    config-144-reconstruction.md §7 / default-configs/README.md: the CRC is
    computed over config bytes 2..end and stored big-endian at bytes 0..1.
    d8-macro.md §3.1 gives the identical reflected algorithm.
    """
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
    return crc & 0xFFFF


def config_crc_bytes(config: bytes) -> tuple[int, int]:
    """Return the (hi, lo) big-endian CRC-16/MODBUS over config bytes 2..end."""
    crc = crc16_modbus(config[2:])
    return (crc >> 8) & 0xFF, crc & 0xFF


# ---------------------------------------------------------------------------
# Frame model
# ---------------------------------------------------------------------------

@dataclass
class Frame:
    """One parsed A5/A4 wire frame."""

    raw: bytes
    kind: str                 # "short" | "fragment" | "unknown"
    length: int               # raw length byte
    opcode: int
    payload: bytes            # bytes after opcode, before checksum
    checksum_ok: bool
    stored_checksum: int
    computed_checksum: int
    frag_index: int | None = None   # A4 only
    data: bytes = b""               # A4 payload after the index byte
    notes: list[str] = field(default_factory=list)

    @property
    def opcode_name(self) -> str:
        return opcode_name(self.opcode)

    def hex(self, sep: str = " ") -> str:
        return sep.join(f"{b:02X}" for b in self.raw)


def parse_frame(buf: bytes) -> Frame | None:
    """Parse one complete A5/A4 frame from *buf*.

    Layout (ble-architecture.md, docs/android-protocol.md):
        A5 | length | opcode | data...            | checksum
        A4 | length | opcode | fragment_index | data... | checksum
    The length byte equals the total frame length for A5 short frames and for
    A4 data fragments; the D8 terminator (d8-macro.md §3.3) is special-cased
    because it carries the constant 0x0A instead of a computed length.
    """
    if len(buf) < 3:
        return None
    header = buf[0]
    if header not in (FRAME_SHORT, FRAME_FRAG):
        notes = [f"unknown frame header 0x{header:02X} (expected A5/A4)"]
        return Frame(
            raw=buf,
            kind="unknown",
            length=buf[1],
            opcode=buf[2] if len(buf) > 2 else -1,
            payload=buf[3:-1] if len(buf) > 4 else b"",
            checksum_ok=False,
            stored_checksum=buf[-1] if buf else -1,
            computed_checksum=frame_checksum(buf[:-1]) if buf else -1,
            notes=notes,
        )

    length = buf[1]
    opcode = buf[2]
    payload = buf[3:-1]
    trailing = buf[-1]

    # D8 terminator: A4 0A D8 <nfrags+1> <sum8>  (constant length byte 0x0A)
    is_d8_terminator = (
        header == FRAME_FRAG and length == 0x0A and opcode == 0xD8 and len(buf) == 5
    )

    if is_d8_terminator:
        declared_total = len(buf)
    else:
        declared_total = length

    checksum_ok = frame_checksum(buf[:-1]) == trailing
    if declared_total != len(buf):
        checksum_ok = False

    notes = []
    frag_index = None
    data = b""
    kind = "short" if header == FRAME_SHORT else "fragment"
    if header == FRAME_FRAG:
        if is_d8_terminator:
            notes.append("D8 terminator frame (constant length byte 0x0A, d8-macro.md)")
        elif payload:
            frag_index = payload[0]
            data = payload[1:]
        else:
            notes.append("A4 fragment with empty payload")

    return Frame(
        raw=buf,
        kind=kind,
        length=length,
        opcode=opcode,
        payload=payload,
        checksum_ok=checksum_ok,
        stored_checksum=trailing,
        computed_checksum=frame_checksum(buf[:-1]),
        frag_index=frag_index,
        data=data,
        notes=notes,
    )


def build_frame(opcode: int, payload: bytes = b"", header: int = FRAME_SHORT) -> bytes:
    """Build a frame: header | total_length | opcode | payload | sum8."""
    body = bytes([header, 0, opcode]) + bytes(payload)
    total = len(body) + 1
    body = bytes([header, total, opcode]) + bytes(payload)
    return body + bytes([frame_checksum(body)])


def build_fragment_sequence(
    opcode: int, image: bytes, chunk: int = 15
) -> list[bytes]:
    """Split *image* into A4 fragments with a 1-based fragment index byte.

    docs/android-protocol.md "A4 fragmentation" / docs/usb-protocol.md:
    `A4 | length | opcode | fragment_index | up to 15 data bytes | checksum`;
    a 144-byte image becomes ten fragments (1..9 carry 15 bytes, 10 carries 9).
    """
    frames: list[bytes] = []
    for index, start in enumerate(range(0, len(image), chunk), start=1):
        piece = image[start : start + chunk]
        payload = bytes([index]) + piece
        frames.append(build_frame(opcode, payload, header=FRAME_FRAG))
    return frames


# ---------------------------------------------------------------------------
# 144-byte config image (ARMOR-X Pro)
# ---------------------------------------------------------------------------

def load_default_config_144() -> bytes:
    """Load the byte-exact 144-byte ARMOR-X Pro default image.

    Source: default-configs/default_001_device___len_144.json ("bytes" key),
    itself extracted from Define::defaultConfig() define.dart:512
    (config-144-reconstruction.md §7, default-configs/README.md).
    The stored CRC field in that literal is a 0x0000 placeholder; the correct
    big-endian CRC-16/MODBUS over bytes 2..143 is recomputed and spliced in so
    the image the peripheral returns has a valid CRC.
    """
    path = research_file(
        str(Path("default-configs") / DEFAULT_CONFIG_144_NAME)
    )
    with open(path, "r", encoding="utf-8") as handle:
        blob = json.load(handle)
    image = bytes(blob["bytes"])
    if len(image) != 144:
        raise ValueError(f"{path}: expected 144 bytes, got {len(image)}")
    if image[2:4] != bytes([0x00, 0x90]):
        raise ValueError(f"{path}: bytes 2..3 are not 0x0090 (declared length 144)")
    return with_valid_crc(image)


def with_valid_crc(image: bytes) -> bytes:
    """Return *image* with bytes 0..1 replaced by a valid big-endian CRC."""
    hi, lo = config_crc_bytes(image)
    out = bytearray(image)
    out[0] = hi
    out[1] = lo
    return bytes(out)


def config_crc_valid(image: bytes) -> bool:
    if len(image) < 3:
        return False
    return image[0] == config_crc_bytes(image)[0] and image[1] == config_crc_bytes(image)[1]


# ---------------------------------------------------------------------------
# Evidence table: which replies the research actually supports
# ---------------------------------------------------------------------------

@dataclass
class ReplySpec:
    opcode: int
    status: str        # "EVIDENCE-BACKED" | "UNKNOWN"
    description: str
    evidence: str


REPLY_TABLE: dict[int, ReplySpec] = {
    0x0B: ReplySpec(
        0x0B,
        "EVIDENCE-BACKED",
        "A5 05 0B <VV> <sum>  (VV = ZKM/MCU version byte; live capture A5 05 0B 30 E5)",
        "ef-dataflow.md:20; docs/android-frame-builder-reconciliation.md:49; "
        "docs/usb-protocol.md:162",
    ),
    0xEF: ReplySpec(
        0xEF,
        "EVIDENCE-BACKED",
        "A5 0C EF <8 device-uuid bytes> <sum>  (reply bytes 3..10 -> devUuid hex)",
        "ef-dataflow.md:39 ([PROVEN_LIVE]); ble-architecture.md:85",
    ),
    0xD6: ReplySpec(
        0xD6,
        "EVIDENCE-BACKED",
        "ten A4/D6 fragments reassembling to the 144-byte config image",
        "docs/android-protocol.md:126-143; usb-protocol.md:165",
    ),
    0xD7: ReplySpec(
        0xD7,
        "EVIDENCE-BACKED",
        "A5 05 D7 00 81  (short acknowledgement of a config write)",
        "docs/android-protocol.md:153-159; usb-protocol.md:166",
    ),
    0x0E: ReplySpec(
        0x0E,
        "EVIDENCE-BACKED",
        "device echoes the 5-byte frame verbatim (A5 05 0E 00 B8)",
        "docs/android-protocol.md:230",
    ),
    0x04: ReplySpec(
        0x04, "UNKNOWN",
        "getBattery -- no byte-exact device reply in the research "
        "(app reads battery via GATT 2A19)",
        "command-index.md 0x04; ble-architecture.md",
    ),
    0xE2: ReplySpec(
        0xE2, "UNKNOWN",
        "readFirmware -- decoder shape known (min 16 bytes, opcode E2, 9-byte "
        "marker at bytes 6..14) but marker CONTENT is UNKNOWN; no bytes sent",
        "research-status-2026-09-25.md:116-121; unresolved.md §8",
    ),
    0xE4: ReplySpec(
        0xE4, "UNKNOWN",
        "getMTU -- request is byte-exact, device reply never captured; no bytes sent",
        "command-index.md 0xE4; live-test-plan.md:10",
    ),
}


def reply_status(opcode: int) -> ReplySpec:
    return REPLY_TABLE.get(
        opcode,
        ReplySpec(opcode, "UNKNOWN", "no evidence-backed reply in the research", "n/a"),
    )
