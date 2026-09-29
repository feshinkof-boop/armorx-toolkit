"""Offline parser for the Xbox GIP input stream observed on ARMORX Pro.

Only structure that was observed live is exposed. Unknown bytes are retained
and reported as spans rather than dropped, and unresolved bits are left
unnamed.

Observed report forms (evidence: proven live):

* a 32-byte form seen for roughly the first 46 seconds after enumeration;
* a 48-byte steady-state form.

Both carry type byte ``0x20`` and the prefix ``20 00 <sequence> 2c``. **The
reason for the 32 to 48 transition is unknown** and nothing here depends on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

GIP_TYPE_INPUT = 0x20
REPORT_LEN_STARTUP = 32
REPORT_LEN_STEADY = 48
REPORT_LENS = (REPORT_LEN_STARTUP, REPORT_LEN_STEADY)

# Field offsets. Every one of these was established by differential analysis of
# live captures against idle windows, not by assumption.
OFF_SEQUENCE = 2
OFF_BUTTONS_LOW = 4
OFF_BUTTONS_HIGH = 5
OFF_LT = 6
OFF_RT = 8
OFF_STICK_LEFT = 10
OFF_STICK_RIGHT = 14
OFF_COUNTERS = 40

BIT_A = 0x10
BIT_M1 = 0x20
BIT_M2 = 0x40

KNOWN_PREFIX_BYTES = {0: 0x20, 1: 0x00, 3: 0x2C}


class GipError(ValueError):
    """Raised when a frame is not a parseable GIP input report."""


@dataclass
class GipInputReport:
    """A decoded type-0x20 input report."""

    raw: bytes
    length: int
    form: str
    sequence: int
    buttons_low: int
    buttons_high: int
    a: bool
    m1: bool
    m2: bool
    lt: int
    rt: int
    left_stick: tuple[int, int]
    right_stick: tuple[int, int]
    counters: tuple[int, int] | None = None
    unknown_spans: list[tuple[int, int]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "length": self.length,
            "form": self.form,
            "type_hex": f"0x{self.raw[0]:02X}",
            "sequence": self.sequence,
            "buttons": {
                "buttons_low": self.buttons_low,
                "buttons_high": self.buttons_high,
                "A": self.a,
                "M1": self.m1,
                "M2": self.m2,
            },
            "triggers": {"LT": self.lt, "RT": self.rt,
                         "note": "16-bit little-endian; the Xbox report carries no digital "
                                 "RT bit, so any digital trigger state is produced by the device"},
            "sticks": {
                "left": list(self.left_stick),
                "right": list(self.right_stick),
                "left_s16": [_as_s16(v) for v in self.left_stick],
                "right_s16": [_as_s16(v) for v in self.right_stick],
                "note": "raw 16-bit little-endian words exactly as they appear on the wire; "
                        "the signed reading is shown for convenience only. Neither the "
                        "signedness nor the scaling to the host axis range has been "
                        "established: a live stick sweep correlated to evdev has not been "
                        "recorded, so treat a stick value as raw, not as an axis position.",
            },
            "counters": list(self.counters) if self.counters else None,
            "counters_evidence": "monotonic 32-bit values; whether they are timestamps is unknown",
            "unknown_spans": [[start, end] for start, end in self.unknown_spans],
            "raw_hex": self.raw.hex(" "),
        }


def _u16le(data: bytes, off: int) -> int:
    return data[off] | (data[off + 1] << 8)


def _u32le(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 4], "little")


def parse_gip_input(data: bytes | bytearray, *, strict: bool = True) -> GipInputReport:
    """Parse one type-0x20 GIP input report.

    ``strict`` (default) enforces the observed type byte, the observed prefix
    bytes and one of the two observed lengths. Passing ``strict=False`` keeps
    the parse but records the deviation in the returned object's ``form`` as
    ``"unexpected"`` so that capture tooling can still show the frame.
    """
    buf = bytes(data)
    if len(buf) < 18:
        raise GipError(f"input report too short: {len(buf)} bytes")
    if buf[0] != GIP_TYPE_INPUT:
        raise GipError(f"not a type-0x20 input report (found 0x{buf[0]:02X})")
    for off, expected in KNOWN_PREFIX_BYTES.items():
        if off < len(buf) and buf[off] != expected and strict:
            raise GipError(f"byte {off} is 0x{buf[off]:02X}, expected 0x{expected:02X}")
    if len(buf) in REPORT_LENS:
        form = "short" if len(buf) == REPORT_LEN_STARTUP else "steady"
    else:
        if strict:
            raise GipError(f"unexpected report length {len(buf)}; observed forms are "
                           f"{REPORT_LEN_STARTUP} and {REPORT_LEN_STEADY}")
        form = "unexpected"

    counters = None
    if len(buf) >= OFF_COUNTERS + 8:
        counters = (_u32le(buf, OFF_COUNTERS), _u32le(buf, OFF_COUNTERS + 4))

    # Everything not claimed by a proven field is reported, never discarded.
    claimed = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}
    if counters is not None:
        claimed.update(range(OFF_COUNTERS, OFF_COUNTERS + 8))
    spans: list[tuple[int, int]] = []
    start = None
    for i in range(len(buf)):
        if i not in claimed:
            if start is None:
                start = i
        elif start is not None:
            spans.append((start, i))
            start = None
    if start is not None:
        spans.append((start, len(buf)))

    return GipInputReport(
        raw=buf,
        length=len(buf),
        form=form,
        sequence=buf[OFF_SEQUENCE],
        buttons_low=buf[OFF_BUTTONS_LOW],
        buttons_high=buf[OFF_BUTTONS_HIGH],
        a=bool(buf[OFF_BUTTONS_LOW] & BIT_A),
        m1=bool(buf[OFF_BUTTONS_LOW] & BIT_M1),
        m2=bool(buf[OFF_BUTTONS_HIGH] & BIT_M2),
        lt=_u16le(buf, OFF_LT),
        rt=_u16le(buf, OFF_RT),
        left_stick=(_u16le(buf, OFF_STICK_LEFT), _u16le(buf, OFF_STICK_LEFT + 2)),
        right_stick=(_u16le(buf, OFF_STICK_RIGHT), _u16le(buf, OFF_STICK_RIGHT + 2)),
        counters=counters,
        unknown_spans=spans,
    )


def _as_s16(value: int) -> int:
    """Two's-complement reading of a raw 16-bit word. Convenience only, never authoritative."""
    return value - 0x10000 if value >= 0x8000 else value


def is_probable_input_report(data: bytes | bytearray) -> bool:
    """Cheap predicate for capture filtering; never raises."""
    buf = bytes(data)
    return len(buf) in REPORT_LENS and bool(buf) and buf[0] == GIP_TYPE_INPUT
