from __future__ import annotations

import json

import pytest

from armorx import config as C
from armorx.gui_model import GuiConfigSession, QUICK_FIELDS, REAR_BUTTONS


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
    with pytest.raises(ValueError, match="milestone-1 GUI field"):
        session.set_byte_field("reserved_after_turbo", 1)


def test_accept_working_as_baseline_clears_diff():
    session = GuiConfigSession.from_image(baseline())
    session.set_map("M1", "A")
    assert session.changed
    session.accept_working_as_baseline()
    assert session.changed is False
    assert session.diff()["identical"] is True
