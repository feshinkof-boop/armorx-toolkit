"""Hardware-free tests for the reusable configuration diff layer."""

import random

import pytest

from armorx import config as C
from armorx import diff as D


def _canonical(values):
    values = list(values)
    crc = C.crc16_gamepad(values[2:144])
    values[0] = (crc >> 8) & 0xFF
    values[1] = crc & 0xFF
    return bytes(values)


def _image() -> bytes:
    return _canonical(C.fresh())


def test_identical_images_produce_no_changes():
    image = _image()
    result = D.diff_images(image, image)
    assert result["identical"] is True
    assert result["changed_bytes"] == 0
    assert result["unknown_byte_count"] == 0
    assert "no changes" in D.summarise(result)


def test_crc_and_length_offsets_are_classified():
    for offset, classification in ((0, D.CLASS_CRC), (1, D.CLASS_CRC),
                                   (2, D.CLASS_DECLARED_LENGTH),
                                   (3, D.CLASS_DECLARED_LENGTH)):
        entry = D.classify_offset(offset)
        assert entry["classification"] == classification
        assert entry["field"]
        assert entry["evidence"]


def test_known_byte_field_is_classified_with_its_name():
    offset = C.BYTE_FIELDS["triggerMode"]
    entry = D.classify_offset(offset)
    assert entry["classification"] == D.CLASS_KNOWN_FIELD
    assert entry["field"] == "triggerMode"


def test_u32_and_group_spans_are_classified():
    span = C.U32_FIELDS["sensorSwitch"]
    for extra in range(4):
        entry = D.classify_offset(span + extra)
        assert entry["classification"] == D.CLASS_KNOWN_FIELD
        assert entry["field"] == "sensorSwitch"
    # group members carry the finer byte-field name when one exists, and the
    # group name otherwise; either way the classification is a known field
    byte_by_offset = {offset: name for name, offset in C.BYTE_FIELDS.items()}
    for offset in C.GROUP_FIELDS["stickLeftCurve"]:
        entry = D.classify_offset(offset)
        assert entry["classification"] == D.CLASS_KNOWN_FIELD
        assert entry["field"] == byte_by_offset.get(offset, "stickLeftCurve")
    # mapKeys is the one group with no per-byte table, so it keeps its own class
    for offset in C.GROUP_FIELDS["mapKeys"]:
        assert D.classify_offset(offset)["classification"] == D.CLASS_MAP_KEY


def test_mapkeys_carry_source_and_target_names():
    before = _image()
    values = list(before)
    values[C.MAPKEYS_START + 23] = int(C.MAP_KEY_CODES["A"])
    after = _canonical(values)
    result = D.diff_images(before, after)
    entry = [c for c in result["changes"] if c["offset"] == C.MAPKEYS_START + 23][0]
    assert entry["classification"] == D.CLASS_MAP_KEY
    assert entry["field"] == "mapKeys[23]"
    key = entry["map_key"]
    assert key["source_id"] == 23
    assert key["source_name"] == "M1"
    assert key["new_target_id"] == 0 and key["new_target_name"] == "A"
    assert result["map_key_changes"] == [key]
    assert "M1" in D.summarise(result)


def test_reserved_bytes_are_unknown_and_named_as_a_region():
    before = _image()
    values = list(before)
    values[90] = (values[90] + 7) % 256
    after = _canonical(values)
    result = D.diff_images(before, after)
    unknown = result["unknown_byte_changes"]
    assert [u["offset"] for u in unknown] == [90]
    assert unknown[0]["classification"] == D.CLASS_UNKNOWN
    assert unknown[0]["field"] is None
    assert unknown[0]["region"] == "reserved_after_turbo"
    assert result["has_unknown_changes"] is True
    assert result["unknown_byte_count"] == 1


def test_every_offset_is_classified_and_never_invented():
    for offset in range(C.CONFIG_LEN):
        entry = D.classify_offset(offset)
        assert entry["classification"] in D.KNOWN_CLASSES + (D.CLASS_UNKNOWN,)
        if entry["classification"] == D.CLASS_UNKNOWN:
            assert entry["field"] is None
        assert entry["evidence"]


def test_wrong_sized_images_are_refused():
    with pytest.raises(ValueError):
        D.diff_images(b"\x00" * 143, _image())
    with pytest.raises(ValueError):
        D.diff_images(_image(), b"\x00" * 200)
    with pytest.raises(ValueError):
        D.classify_offset(144)


def test_randomised_diffs_do_not_lose_a_changed_byte():
    rng = random.Random(20260929)
    for _ in range(60):
        before = bytearray(_image())
        after = bytearray(before)
        expected = set()
        for _ in range(rng.randint(1, 6)):
            offset = rng.randrange(4, 144)
            if after[offset] == before[offset]:
                after[offset] = (after[offset] + rng.randint(1, 255)) % 256
            expected.add(offset)
        before_b = _canonical(before)
        after_b = _canonical(after)
        result = D.diff_images(before_b, after_b)
        offsets = {c["offset"] for c in result["changes"]}
        assert expected <= offsets
        assert result["total_changed_bytes"] == len(result["changes"])
        assert (len(result["known_field_changes"])
                + len(result["unknown_byte_changes"])) == result["total_changed_bytes"]


def test_known_and_unknown_counts_add_up_on_a_mixed_change():
    before = _image()
    values = list(before)
    values[90] = 3                     # reserved/undecoded
    values[C.BYTE_FIELDS["stickTurn"]] = 9
    after = _canonical(values)
    result = D.diff_images(before, after)
    assert result["unknown_byte_count"] == 1
    assert len(result["known_field_changes"]) == 3   # two CRC bytes + the field
    assert result["total_changed_bytes"] == 4
