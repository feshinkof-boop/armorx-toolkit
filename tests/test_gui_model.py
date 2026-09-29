from __future__ import annotations

import json

import pytest

from armorx import config as C
from armorx.gui_model import (
    GUI_EDITABLE_FIELDS,
    GuiConfigSession,
    QUICK_FIELDS,
    REAR_BUTTONS,
    STICK_VISUAL_FIELDS,
    TRIGGER_VISUAL_FIELDS,
)


def baseline() -> bytes:
    return bytes(C.fresh())


def test_from_image_requires_valid_crc():
    bad = bytearray(baseline())
    bad[20] ^= 1
    with pytest.raises(ValueError, match="CRC mismatch"):
        GuiConfigSession.from_image(bad)


def test_rear_buttons_are_m1_through_m4():
    assert REAR_BUTTONS == ("M1", "M2", "M3", "M4")


def test_map_edit_regenerates_crc_and_preserves_length():
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M1", "A")
    result = session.validation()
    assert result["actual_length"] == 144
    assert result["declared_length"] == 144
    assert result["crc_matches"] is True
    assert session.map_target("M1")["target_name"] == "A"


def test_map_edit_changes_only_crc_and_target_slot_for_fresh_image():
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M1", "A")
    offsets = {change["offset"] for change in session.diff()["changes"]}
    assert offsets == {0, 1, C.MAPKEYS_START + C.MAP_KEY_CODES["M1"]}


@pytest.mark.parametrize("field", QUICK_FIELDS)
def test_quick_field_round_trip(field):
    session = GuiConfigSession.from_image(baseline())
    session.set_byte_field(field, 7)
    assert session.byte_field(field) == 7
    assert session.validation()["crc_matches"] is True


def test_reset_restores_original_exactly():
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M2", "B")
    assert session.changed
    session.reset()
    assert session.working == session.baseline
    assert session.diff()["identical"] is True


def test_export_json_reopens(tmp_path):
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M3", "X")
    path = tmp_path / "target.json"
    session.export_json(path)
    reopened = GuiConfigSession.from_file(path)
    assert reopened.baseline == session.working
    assert json.loads(path.read_text()) == list(session.working)


def test_export_bin_reopens(tmp_path):
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M4", "Y")
    path = tmp_path / "target.bin"
    session.export_bin(path)
    reopened = GuiConfigSession.from_file(path)
    assert reopened.baseline == session.working


def test_unknown_gui_field_is_refused():
    session = GuiConfigSession.from_image(baseline())
    with pytest.raises(ValueError, match="GUI-editable byte field"):
        session.set_byte_field("reserved_after_turbo", 1)


def test_accept_working_as_baseline_clears_diff():
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M1", "A")
    assert session.changed
    session.accept_working_as_baseline()
    assert session.changed is False
    assert session.diff()["identical"] is True


def test_curve_visual_field_edit_changes_only_crc_and_recovered_byte():
    session = GuiConfigSession.from_image(baseline())
    field = STICK_VISUAL_FIELDS["left"]["pt1_x"]
    offset = C.BYTE_FIELDS[field]
    session.set_byte_field(field, 77)
    offsets = {change["offset"] for change in session.diff()["changes"]}
    assert offsets == {0, 1, offset}
    assert session.validation()["crc_matches"] is True


def test_stick_visual_snapshot_matches_raw_fields():
    session = GuiConfigSession.from_image(baseline())
    for role, field in STICK_VISUAL_FIELDS["right"].items():
        session.set_byte_field(field, 10 + len(role))
    values = session.stick_visual("right")
    assert set(values) == set(STICK_VISUAL_FIELDS["right"])
    for role, field in STICK_VISUAL_FIELDS["right"].items():
        assert values[role] == session.working[C.BYTE_FIELDS[field]]


def test_trigger_visual_edit_preserves_unknown_bytes():
    session = GuiConfigSession.from_image(baseline())
    before = session.working
    field = TRIGGER_VISUAL_FIELDS["left"]["dz_center"]
    offset = C.BYTE_FIELDS[field]
    session.set_byte_field(field, 93)
    changed = {i for i, (a, b) in enumerate(zip(before, session.working)) if a != b}
    assert changed == {0, 1, offset}


def test_all_visual_fields_are_gui_editable_known_bytes():
    expected = {
        field for side in STICK_VISUAL_FIELDS.values() for field in side.values()
    } | {
        field for side in TRIGGER_VISUAL_FIELDS.values() for field in side.values()
    }
    assert expected <= set(GUI_EDITABLE_FIELDS)
    assert all(field in C.BYTE_FIELDS for field in expected)
