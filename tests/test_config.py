import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("armorx_config", ROOT / "tools" / "armorx_config.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def test_fresh_config_is_144_bytes_and_crc_valid():
    cfg = mod.fresh()
    assert len(cfg) == 144
    result = mod.validate(cfg)
    assert result["declared_length"] == 144
    assert result["crc_matches"] is True


def test_named_mapkey_patch():
    cfg = mod.fresh()
    mod.apply_assignment(cfg, "mapKey[M1]=A")
    cfg = mod.canonicalize(cfg)
    assert cfg[112 + 23] == 0
    assert mod.validate(cfg)["crc_matches"] is True


def test_proven_key_ids():
    assert mod.MAP_KEY_CODES["A"] == 0
    assert mod.MAP_KEY_CODES["RT"] == 9
    assert mod.MAP_KEY_CODES["M4"] == 26


def test_share_res2_region_is_74_to_111():
    cfg = mod.fresh()
    cfg[74:112] = list(range(38))
    decoded = mod.decode(cfg)
    region = decoded["share_regions"]["res2"]
    assert region["offsets"] == [74, 111]
    assert region["bytes"] == list(range(38))
