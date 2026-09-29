"""Exchange envelope tests: determinism, privacy and validation."""

import json
from pathlib import Path

import pytest

from armorx import exchange


def test_content_id_is_independent_of_key_order_and_whitespace(tmp_path: Path):
    env = exchange.create("config", {"keys": {"A": "B"}, "crc": 1})
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps(env.to_dict(), indent=4))
    data = env.to_dict()
    reordered = {"content_id": data["content_id"], "payload": {"crc": 1, "keys": {"A": "B"}},
                 "content_type": data["content_type"], "schema": data["schema"],
                 "toolkit_format": data["toolkit_format"]}
    b.write_text(json.dumps(reordered, separators=(",", ":")))
    assert exchange.load(str(a)).compute_id() == exchange.load(str(b)).compute_id()


def test_content_id_changes_when_the_payload_changes():
    one = exchange.create("config", {"crc": 1})
    two = exchange.create("config", {"crc": 2})
    assert one.compute_id() != two.compute_id()


def test_create_sets_the_content_id():
    env = exchange.create("macro", {"steps": []})
    assert env.content_id == env.compute_id()
    assert env.content_id.startswith("sha256:")


def test_round_trip_through_a_file(tmp_path: Path):
    env = exchange.create("config", {"a": 1}, provenance={"evidence": "proven"})
    path = tmp_path / "cfg.armorx.json"
    exchange.save(env, str(path))
    loaded = exchange.load(str(path))
    assert loaded.compute_id() == env.compute_id()
    assert exchange.verify(loaded)["content_id_ok"] is True


def test_unknown_content_type_is_rejected():
    with pytest.raises(exchange.ExchangeError, match="content_type must be"):
        exchange.create("firmware", {})


def test_serial_keys_are_rejected():
    with pytest.raises(exchange.ExchangeError, match="looks like private data"):
        exchange.create("config", {"serial_number": "123"})


def test_mac_like_values_are_rejected():
    with pytest.raises(exchange.ExchangeError, match="private identifier"):
        exchange.create("config", {"note": "aa:bb:cc:dd:ee:ff"})


def test_home_paths_are_rejected():
    with pytest.raises(exchange.ExchangeError, match="private identifier"):
        exchange.create("config", {"path": "/home/someone/cfg.json"})


def test_private_keys_in_device_metadata_are_rejected():
    with pytest.raises(exchange.ExchangeError, match="device.serial"):
        exchange.create("config", {}, device={"serial": "x"})


def test_nested_private_keys_are_rejected():
    with pytest.raises(exchange.ExchangeError):
        exchange.create("config", {"a": {"b": {"bdaddr": "00:11:22:33:44:55"}}})


def test_sanitise_drops_and_masks():
    cleaned = exchange.sanitise({"user_name": "k", "note": "ip aa:bb:cc:dd:ee:ff",
                                 "path": "/home/k/x", "keep": 1,
                                 "nested": {"serial": "9", "ok": True}})
    assert "user_name" not in cleaned
    assert "serial" not in cleaned["nested"]
    assert cleaned["note"] == "ip <mac>"
    assert cleaned["path"] == "<home>/x"
    assert cleaned["keep"] == 1 and cleaned["nested"]["ok"] is True


def test_missing_required_fields():
    with pytest.raises(exchange.ExchangeError, match="missing required field"):
        exchange.from_dict({"schema": exchange.SCHEMA})


def test_schema_mismatch_is_rejected():
    with pytest.raises(exchange.ExchangeError, match="unsupported schema"):
        exchange.from_dict({"schema": "armorx.exchange/v9", "content_type": "config", "payload": {}})


def test_non_object_envelope_is_rejected():
    with pytest.raises(exchange.ExchangeError, match="must be a JSON object"):
        exchange.from_dict(["not", "an", "object"])


def test_invalid_json_is_a_clear_error(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(exchange.ExchangeError, match="not valid JSON"):
        exchange.load(str(p))


def test_missing_file_is_a_clear_error(tmp_path: Path):
    with pytest.raises(exchange.ExchangeError, match="does not exist"):
        exchange.load(str(tmp_path / "nope.json"))


def test_oversized_payload_is_rejected():
    huge = {"blob": "x" * (exchange.MAX_PAYLOAD_BYTES + 10)}
    with pytest.raises(exchange.ExchangeError, match="above the"):
        exchange.create("config", huge)


def test_verify_detects_a_tampered_content_id():
    env = exchange.create("config", {"a": 1})
    env.content_id = "sha256:0000"
    result = exchange.verify(env)
    assert result["content_id_ok"] is False


def test_verify_reports_evidence_level():
    env = exchange.create("macro", {}, provenance={"evidence": "strong-evidence"})
    assert exchange.verify(env)["evidence"]["payload"] == "strong-evidence"


def test_canonical_json_is_stable():
    assert exchange.canonical_json({"b": 1, "a": [2, {"d": 3, "c": 4}]}) == \
        '{"a":[2,{"c":4,"d":3}],"b":1}'


def test_optional_metadata_is_omitted_when_empty():
    env = exchange.create("config", {"a": 1})
    body = env.body()
    assert "device" not in body and "provenance" not in body and "created" not in body


def test_created_timestamp_can_be_passed_explicitly():
    env = exchange.create("config", {}, created="2026-09-29T00:00:00+00:00")
    assert env.body()["created"] == "2026-09-29T00:00:00+00:00"
