"""v0.4 live BLE foundation tests.  No BLE hardware is touched."""

import asyncio
import json

import pytest

from armorx import config as C
from armorx import live as L
from armorx import protocol as P


def _image() -> bytes:
    return bytes(C.fresh())


def test_d6_read_reassembles_indexed_fragments():
    image = _image()
    fragments = P.fragment_config_image(0xD6, image)
    scripted = fragments[4:8] + fragments[:4] + fragments[8:]
    transport = L.MockLiveTransport(notifications=scripted)
    result = asyncio.run(L.read_config(transport))
    assert result == image
    assert transport.writes == [{"frame": P.build_a5(0xD6), "mutating": False}]


def test_d6_read_reports_missing_fragments():
    image = _image()
    transport = L.MockLiveTransport(
        notifications=P.fragment_config_image(0xD6, image)[:-1]
    )
    with pytest.raises(L.LiveTimeout, match="missing fragment"):
        asyncio.run(L.read_config(transport, timeout=0.01))


def test_identity_reads_are_non_mutating():
    transport = L.MockLiveTransport(characteristics={
        L.MODEL_UUID: b"ZJ-XT",
        L.FIRMWARE_UUID: b"2741",
        L.BATTERY_UUID: bytes([91]),
    })
    result = asyncio.run(L.read_identity(transport))
    assert result["model"] == "ZJ-XT"
    assert result["firmware"] == "2741"
    assert result["battery"] == 91
    assert transport.writes == []


def test_mutating_d7_is_refused_by_default():
    transport = L.MockLiveTransport()
    with pytest.raises(L.LiveWriteRefused):
        asyncio.run(L.write_config_volatile(transport, _image(), fragment_delay=0))
    assert transport.writes == []


def test_mutating_helpers_only_work_after_explicit_gate():
    transport = L.MockLiveTransport(allow_mutating=True)
    asyncio.run(L.write_config_volatile(transport, _image(), fragment_delay=0))
    asyncio.run(L.persist_config(transport))
    assert len(transport.writes) == 11
    assert all(item["mutating"] for item in transport.writes)
    assert [P.parse_frame(item["frame"]).opcode for item in transport.writes[:10]] == [0xD7] * 10
    assert P.parse_frame(transport.writes[-1]["frame"]).opcode == 0x0E


def test_backup_document_omits_private_connection_identifiers():
    doc = L.backup_document(_image(), identity={
        "model": "ZJ-XT",
        "firmware": "2741",
        "battery": 91,
        "transport": "ble",
        "address": "AA:BB:CC:DD:EE:FF",
        "serial": "private",
        "hostname": "private-host",
    })
    rendered = json.dumps(doc)
    assert "AA:BB:CC" not in rendered
    assert "private-host" not in rendered
    assert '"serial"' not in rendered
    assert doc["privacy"]["ble_address_stored"] is False


def test_plan_reports_exact_byte_differences():
    baseline = _image()
    target_list = list(baseline)
    C.apply_assignment(target_list, "mapKey[M1]=A")
    target = bytes(C.canonicalize(target_list))
    plan = L.plan_config_change(baseline, target)
    assert plan["changed_bytes"] >= 1
    assert any(d["offset"] == C.MAPKEYS_START + 23 for d in plan["differences"])
    assert plan["mutating_commands_exposed"] is False


def test_load_image_accepts_backup_json(tmp_path):
    doc = L.backup_document(_image())
    path = tmp_path / "backup.json"
    path.write_text(json.dumps(doc))
    assert L.load_image(path) == _image()
