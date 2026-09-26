import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("armorx_macro", ROOT / "tools" / "armorx_macro.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def test_macro_build_and_decode():
    obj = mod.build_macro_object(
        name="Test",
        trigger="M1",
        mode="tap",
        repeat_time=200,
        steps=[
            {"keys": "A", "duration": 80, "interval": 50},
            {"keys": "B+RT", "duration": 120, "interval": 70},
        ],
    )
    assert obj["runKey"] == 23
    assert obj["isRepeat"] == 1
    raw_rows = __import__("json").loads(obj["macroJson"])
    assert all(isinstance(row, str) for row in raw_rows)
    rows = mod.decode_macro_json(obj["macroJson"])
    assert rows[0]["mapListDecoded"] == [0]
    assert rows[1]["mapListDecoded"] == [1, 9]
    assert rows[0]["showAdd"] is True
    assert rows[1]["showAdd"] is True
    assert mod.validate_macro_object(obj) == []


def test_macro_trigger_ids():
    assert mod.RUN_KEYS == {"M1": 23, "M2": 24, "M3": 25, "M4": 26}


def test_add_macro_payload_uses_integer_inuse():
    obj = mod.build_macro_object(
        name="Test",
        trigger="M1",
        mode="tap",
        active=True,
        steps=[{"keys": "A", "duration": 80, "interval": 50}],
    )
    payload = mod.build_add_macro_payload(
        phone_uuid="phone",
        dev_uuid="device",
        macro_obj=obj,
    )
    assert payload["inUse"] == 1
    assert isinstance(payload["inUse"], int)


def test_guide_key_is_available_as_live_proven_mapping():
    assert mod.KEY_IDS["GUIDE"] == 12
    assert mod.KEY_IDS["MODE"] == 12
    assert mod.CANONICAL_NAMES[12] == "GUIDE"
