from __future__ import annotations

import json

import pytest

from armorx import macro as M
from armorx.gui_macro_model import MacroDraft, MacroStep


def test_default_draft_builds_valid_v41_object():
    draft = MacroDraft()
    obj = draft.to_object()
    assert M.validate_macro_object(obj) == []
    assert obj["runKey"] == 23
    assert len(M.decode_macro_json(obj["macroJson"])) == 1


def test_chord_timeline_round_trip():
    draft = MacroDraft(
        name="Combo",
        trigger="M2",
        mode="tap_cycle",
        repeat_time=333,
        active=True,
        steps=[
            MacroStep("A", 80, 50),
            MacroStep("B+RT", 120, 70),
        ],
    )
    obj = draft.to_object()
    restored = MacroDraft.from_object(obj)
    assert restored.name == "Combo"
    assert restored.trigger == "M2"
    assert restored.mode == "tap_cycle"
    assert restored.repeat_time == 333
    assert restored.active is True
    assert [step.keys for step in restored.steps] == ["A", "B+RT"]
    assert [step.duration for step in restored.steps] == [80, 120]


def test_reorder_and_remove_steps():
    draft = MacroDraft(steps=[
        MacroStep("A"), MacroStep("B"), MacroStep("X")
    ])
    assert draft.move_step(2, -1) == 1
    assert [step.keys for step in draft.steps] == ["A", "X", "B"]
    draft.remove_step(1)
    assert [step.keys for step in draft.steps] == ["A", "B"]


def test_macro_keeps_at_least_one_step():
    draft = MacroDraft()
    with pytest.raises(ValueError, match="at least one"):
        draft.remove_step(0)


def test_macro_caps_at_sixteen_steps():
    draft = MacroDraft(steps=[MacroStep("A") for _ in range(M.V41_MAX_STEPS)])
    with pytest.raises(ValueError, match="at most"):
        draft.add_step(MacroStep("B"))


def test_invalid_key_is_reported_without_guessing():
    draft = MacroDraft(steps=[MacroStep("SHARE", 100, 50)])
    errors = draft.validate()
    assert errors
    assert "unknown key" in errors[0]


def test_export_and_load(tmp_path):
    draft = MacroDraft(
        name="Stored",
        trigger="M4",
        mode="long_press",
        steps=[MacroStep("LB+RB", 90, 10)],
    )
    path = tmp_path / "macro.json"
    draft.export(path)
    raw = json.loads(path.read_text())
    assert M.validate_macro_object(raw) == []
    loaded = MacroDraft.load(path)
    assert loaded.name == "Stored"
    assert loaded.trigger == "M4"
    assert loaded.steps[0].keys == "LB+RB"
