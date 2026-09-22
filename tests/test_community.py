import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("armorx_community", ROOT / "tools" / "armorx_community.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def test_list_payload_shape():
    payload = mod.build_list_payload("phone", "device", page_num=1, config_type=1)
    assert payload == {
        "phoneUuid": "phone",
        "devUuid": "device",
        "pageNum": 1,
        "configType": 1,
    }


def test_import_payload_minimal():
    assert mod.build_import_payload("ABC12345") == {"shareCode": "ABC12345"}


def test_import_payload_with_ids():
    payload = mod.build_import_payload("ABC12345", phone_uuid="phone", dev_uuid="device")
    assert payload["phoneUuid"] == "phone"
    assert payload["devUuid"] == "device"
