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
    rows = mod.decode_macro_json(obj["macroJson"])
    assert rows[0]["mapListDecoded"] == [0]
    assert rows[1]["mapListDecoded"] == [1, 9]
    assert mod.validate_macro_object(obj) == []


def test_macro_trigger_ids():
    assert mod.RUN_KEYS == {"M1": 23, "M2": 24, "M3": 25, "M4": 26}
