from __future__ import annotations

import asyncio
import json

from armorx import config as C
from armorx import confirm as confirm_mod
from armorx import gui_workflow as G
from armorx import live as L
from armorx import protocol as P


def image_with_m1(target: str) -> bytes:
    buf = C.fresh()
    C.apply_assignment(buf, f"mapKey[M1]={target}")
    return bytes(C.canonicalize(buf))


def d6(image: bytes):
    return P.fragment_config_image(0xD6, image)


def accepted(_message: str, _title: str):
    return confirm_mod.ConfirmationResult(True, "test", "accepted by test")


def apply_notifications(baseline: bytes, target: bytes):
    return (
        d6(baseline) + d6(baseline)
        + [P.build_a5(0xD7, [0]), None]
        + [P.build_a5(0x0E, [0]), P.build_a5(0x0E, [0]), None]
        + d6(target) + d6(target)
    )


def rollback_notifications(target: bytes, baseline: bytes):
    return (
        d6(target)
        + [P.build_a5(0xD7, [0]), None]
        + [P.build_a5(0x0E, [0]), P.build_a5(0x0E, [0]), None]
        + d6(baseline) + d6(baseline)
    )


def test_profile_store_round_trip_and_safe_metadata(tmp_path):
    store = G.ProfileStore(tmp_path)
    image = image_with_m1("A")
    store.save(
        "My Couch Profile", image,
        metadata={
            "model": "ZJ-XT", "firmware": "2741",
            "address": "AA:BB:CC:DD:EE:FF", "hostname": "private-host",
        },
    )
    assert store.load("My Couch Profile") == image
    assert [x["name"] for x in store.list()] == ["My Couch Profile"]
    raw = next((tmp_path / "profiles").glob("*.json")).read_text()
    assert "AA:BB" not in raw
    assert "private-host" not in raw
    assert store.delete("My Couch Profile") is True
    assert store.list() == []


def test_profile_tamper_is_refused(tmp_path):
    store = G.ProfileStore(tmp_path)
    store.save("safe", image_with_m1("A"))
    path = next((tmp_path / "profiles").glob("*.json"))
    doc = json.loads(path.read_text())
    doc["bytes"][135] ^= 1
    path.write_text(json.dumps(doc))
    try:
        store.load("safe")
    except ValueError as exc:
        assert "CRC" in str(exc) or "SHA" in str(exc)
    else:
        raise AssertionError("tampered profile was accepted")


def test_default_backup_prefix_avoids_collision(tmp_path):
    first = G.default_backup_prefix(root=tmp_path, stamp="20260929-120000")
    first.with_suffix(".bin").write_bytes(b"x")
    second = G.default_backup_prefix(root=tmp_path, stamp="20260929-120000")
    assert second.name == "gui-backup-20260929-120000-2"


def test_gui_apply_reuses_live_backend_and_creates_rollback_record(tmp_path):
    baseline = image_with_m1("B")
    target = image_with_m1("A")
    transport = L.MockLiveTransport(notifications=apply_notifications(baseline, target))
    prefix = tmp_path / "before"
    report = asyncio.run(G.apply_target(
        "synthetic-address", target, backup_prefix=prefix, confirmer=accepted,
        transport_factory=lambda _address: transport, settle=0, ack_window=0.01,
    ))
    assert report["status"] == "APPLIED"
    assert prefix.with_suffix(".bin").read_bytes() == baseline
    assert prefix.with_suffix(".session.json").exists()
    record = json.loads(prefix.with_suffix(".session.json").read_text())
    assert record["apply_verified"] is True
    assert record["target_sha256"] == L.image_summary(target)["sha256"]
    assert report["confirmation"]["method"] == "test"


def test_gui_rollback_uses_exact_saved_backup(tmp_path):
    baseline = image_with_m1("B")
    target = image_with_m1("A")
    apply_transport = L.MockLiveTransport(notifications=apply_notifications(baseline, target))
    prefix = tmp_path / "before"
    asyncio.run(G.apply_target(
        "synthetic-address", target, backup_prefix=prefix, confirmer=accepted,
        transport_factory=lambda _address: apply_transport, settle=0, ack_window=0.01,
    ))
    rollback_transport = L.MockLiveTransport(
        notifications=rollback_notifications(target, baseline)
    )
    report = asyncio.run(G.rollback_backup(
        "synthetic-address", prefix, confirmer=accepted,
        transport_factory=lambda _address: rollback_transport,
        settle=0, ack_window=0.01,
    ))
    assert report["status"] == "RESTORED"
    assert G.backup_image(prefix) == baseline


def test_gui_apply_decline_sends_no_mutating_frames(tmp_path):
    baseline = image_with_m1("B")
    target = image_with_m1("A")
    transport = L.MockLiveTransport(notifications=d6(baseline) + d6(baseline))

    def declined(_message: str, _title: str):
        return confirm_mod.ConfirmationResult(False, "test", "declined by test")

    report = asyncio.run(G.apply_target(
        "synthetic-address", target, backup_prefix=tmp_path / "before",
        confirmer=declined, transport_factory=lambda _address: transport,
        settle=0, ack_window=0.01,
    ))
    assert report["status"] == "REFUSED"
    assert not any(row["mutating"] for row in transport.writes)


def test_backup_image_requires_valid_crc(tmp_path):
    prefix = tmp_path / "before"
    bad = bytearray(image_with_m1("B"))
    bad[30] ^= 1
    prefix.with_suffix(".bin").write_bytes(bad)
    try:
        G.backup_image(prefix)
    except ValueError as exc:
        assert "CRC" in str(exc)
    else:
        raise AssertionError("bad backup image accepted")
