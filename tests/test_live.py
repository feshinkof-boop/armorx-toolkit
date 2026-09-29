"""v0.4 live BLE foundation tests.  No BLE hardware is touched."""

import argparse
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


def test_read_config_reports_the_fragment_accounting():
    """The read path must report its ten fragments, not just the reassembled image.

    Regression from the 2026-09-29 live validation: the artefact proved the image
    but said nothing about how many fragments arrived or how large they were.
    """
    image = _image()
    fragments = P.fragment_config_image(0xD6, image)
    report: dict = {}
    transport = L.MockLiveTransport(notifications=fragments)
    result = asyncio.run(L.read_config(transport, report=report))
    assert result == image
    assert report["fragment_count"] == 10
    indexes = [f["index"] for f in report["fragments"]]
    assert indexes == list(range(1, 11))
    assert all(f["checksum_ok"] for f in report["fragments"])
    data_bytes = [f["data_bytes"] for f in report["fragments"]]
    assert data_bytes == [15] * 9 + [9]
    assert sum(data_bytes) == 144


def test_read_config_still_works_without_a_report_dict():
    image = _image()
    transport = L.MockLiveTransport(notifications=P.fragment_config_image(0xD6, image))
    assert asyncio.run(L.read_config(transport)) == image


def test_backup_document_records_fragments_only_when_given():
    image = _image()
    plain = L.backup_document(image)
    assert "fragments" not in plain
    with_fragments = L.backup_document(
        image, fragments=[{"index": 1, "frame_bytes": 20, "data_bytes": 15,
                           "checksum_ok": True}])
    assert with_fragments["fragments"][0]["index"] == 1


def test_cli_read_config_payload_carries_the_fragment_accounting(tmp_path, monkeypatch):
    from armorx import cli
    image = _image()
    details = {"fragment_count": 10,
               "fragments": [{"index": i, "frame_bytes": 20, "data_bytes": 15,
                              "checksum_ok": True} for i in range(1, 11)]}

    async def fake_read(address, connect_timeout, reply_timeout):
        return {"model": "ZJ-XT", "firmware": "2741", "battery": 87}, image, details

    monkeypatch.setattr(cli, "_live_read", fake_read)
    out = tmp_path / "read.json"
    args = argparse.Namespace(address="AA:BB:CC:DD:EE:FF", connect_timeout=1.0,
                              reply_timeout=1.0, compact=False, output=str(out))
    assert cli.cmd_live_read_config(args) == 0
    payload = json.loads(out.read_text())
    assert payload["fragment_count"] == 10
    assert [f["index"] for f in payload["fragments"]] == list(range(1, 11))
    assert "AA:BB:CC:DD:EE:FF" not in out.read_text()
