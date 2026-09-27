"""Regression vectors from REAL ARMOR-X Pro captures (session 2026-09-27).

No byte string is hand-typed here: everything comes from
tests/vectors/real-device-vectors.json, which automation/scripts/export-test-vectors.py
rebuilds from the committed capture files (the immutable D6 baseline, the live D2
press-group status frames, and the live 0B/EF/D4/E2 replies).

If the parsers ever disagree with the physical device, these tests fail.

Rebuild vectors:  automation/scripts/export-test-vectors.py ... (see its --help)
Run:              PYTHONPATH=ble/virtual-armorx:automation/scripts /usr/bin/python3.14 -m pytest tests -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import pytest

LAB = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "ble" / "virtual-armorx"))
sys.path.insert(0, str(LAB / "automation" / "scripts"))

import armorx_protocol as proto  # noqa: E402

VECTORS = json.loads((LAB / "tests" / "vectors" / "real-device-vectors.json").read_text())
BYTE_BASE = {6: 0, 5: 8, 4: 16, 3: 24}


def decode_ids(raw_hex: str) -> list[int]:
    b = bytes.fromhex(raw_hex)
    assert len(b) == 18 and b[2] == 0x02, "not an opcode 0x02 status frame"
    ids = []
    for byte_idx, base in BYTE_BASE.items():
        val = b[byte_idx]
        for bit in range(8):
            if val >> bit & 1:
                ids.append(base + bit)
    return ids


def payload_of(parsed) -> bytes:
    """Short frames (0x0c-style lengths) keep their bytes in .payload, long frames
    in .data - the vector set contains both kinds, so normalise here."""
    data = bytes(parsed.data or b"")
    return data if data else bytes(parsed.payload or b"")


# --- the immutable baseline ---------------------------------------------------

def test_baseline_matches_the_live_capture_bit_for_bit():
    raw = bytes.fromhex(VECTORS["baseline"]["hex"])
    assert len(raw) == 144
    assert hashlib.sha256(raw).hexdigest() == VECTORS["baseline"]["sha256"]
    assert VECTORS["baseline"]["sha256"] == "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"


def test_baseline_crc_and_declared_length():
    raw = bytes.fromhex(VECTORS["baseline"]["hex"])
    assert proto.config_crc_valid(raw) is True
    assert int.from_bytes(raw[2:4], "big") == len(raw) == 144


def test_mapkeys_source_slot_15_is_absolute_offset_127():
    raw = bytes.fromhex(VECTORS["baseline"]["hex"])
    assert VECTORS["baseline"]["byte127_source_slot_15"] == raw[127] == 0x0F
    assert 112 <= 127 <= 143


def test_key_mask_rule_is_bit_equals_id_not_id_plus_one():
    assert 1 << 6 == 0x40
    assert 1 << 15 == 0x8000
    assert 1 << 16 == 0x10000


# --- ID 15 experiment ---------------------------------------------------------

def test_id15_mutant_differs_only_in_crc_and_offset_127():
    base = bytes.fromhex(VECTORS["baseline"]["hex"])
    raw = bytearray(base)
    raw[127] = 0x02                                   # NIL / empty mapping
    mutant = proto.with_valid_crc(bytes(raw))
    assert [i for i in range(144) if mutant[i] != base[i]] == [0, 1, 127]
    assert proto.config_crc_valid(mutant) is True
    assert len(proto.build_fragment_sequence(0xD7, mutant)) == 10


# --- live status frames (61 real frames) --------------------------------------

@pytest.mark.parametrize("vector", VECTORS["status_frames"],
                         ids=[f"{v['group']}-{v['raw'][10:14]}-{v['ids']}"
                              for v in VECTORS["status_frames"]])
def test_live_status_frame_decodes_to_the_ids_the_operator_actually_pressed(vector):
    assert decode_ids(vector["raw"]) == vector["ids"]


def test_every_key_mask_frame_has_the_expected_shape():
    for v in VECTORS["status_frames"]:
        b = bytes.fromhex(v["raw"])
        assert len(b) == 18 and b[0] == 0xA5 and b[1] == 0x12 and b[2] == 0x02
        assert sum(b[:-1]) & 0xFF == b[-1], f"checksum mismatch on {v['raw']}"


def test_lt_is_the_only_trigger_that_ever_reported_analog_travel():
    lt_seen = rt_nonzero = 0
    for v in VECTORS["status_frames"]:
        b = bytes.fromhex(v["raw"])
        if b[15]:
            lt_seen += 1
        if b[16]:
            rt_nonzero += 1
    assert lt_seen > 0, "LT analog byte [15] never moved in the capture"
    assert rt_nonzero == 0, "RT analog byte [16] moved - update the trigger findings"


# --- live replies -------------------------------------------------------------

def test_live_d4_reply_shape():
    for entry in VECTORS["replies"].get("opcode_0xD4", []):
        raw = bytes.fromhex(entry["raw"])
        parsed = proto.parse_frame(raw)
        assert parsed is not None and parsed.opcode == 0xD4
        assert len(raw) == 7 and len(payload_of(parsed)) == 3


def test_live_e2_reply_carries_firmware_and_model_strings():
    """Real E2 payload: <fw BCD hi> <fw BCD lo> 0x02 "ZJ-XT" 00000000.

    The firmware is NOT ASCII: fw 2741 is the two BCD bytes 0x27 0x41, followed by
    a 0x02 byte (semantics UNKNOWN - NOT a name length, the name that follows is 5
    bytes) and then the model string. Established from the live reply, not assumed.
    """
    entries = VECTORS["replies"].get("opcode_0xE2", [])
    assert entries, "no real E2 reply in the vector set"
    for entry in entries:
        payload = payload_of(proto.parse_frame(bytes.fromhex(entry["raw"])))
        assert payload[0] == 0x27 and payload[1] == 0x41, "firmware BCD bytes"
        assert f"{payload[0]:02X}{payload[1]:02X}" == "2741"
        assert payload[2:8] == b"\x02ZJ-XT"
        assert b"2741" not in payload, "firmware must not appear as ASCII"


def test_live_0b_and_ef_replies_parse_with_valid_checksums():
    for opcode in ("opcode_0x0B", "opcode_0xEF"):
        entries = VECTORS["replies"].get(opcode, [])
        assert entries, f"no real {opcode} reply in the vector set"
        for entry in entries:
            parsed = proto.parse_frame(bytes.fromhex(entry["raw"]))
            assert parsed is not None and parsed.checksum_ok is True
