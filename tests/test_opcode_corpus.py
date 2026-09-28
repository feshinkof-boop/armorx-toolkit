"""Guards for the overnight opcode corpus.

The corpus file lives under results/overnight/<timestamp>/ (one directory per shift), so this test
locates the newest one and skips cleanly if none exists. It asserts the invariants that make the
corpus trustworthy rather than the exact contents, so a future shift can extend the corpus without
breaking this test.

Context: the first corpus pass used a greedy btmon text parser that mis-attributed unrelated Data
buffers (the device name, connection parameters) to ATT records and produced phantom opcodes with
false checksum failures. These assertions exist so that cannot recur silently.
"""
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
OVERNIGHT = REPO / "results/overnight"


def newest_corpus():
    if not OVERNIGHT.is_dir():
        pytest.skip("no overnight shift directory in this checkout")
    for d in sorted(OVERNIGHT.iterdir(), reverse=True):
        p = d / "opcode-corpus.json"
        if p.exists():
            return json.loads(p.read_text())
    pytest.skip("no opcode corpus in any overnight directory")


def test_every_protocol_frame_has_a_valid_checksum():
    c = newest_corpus()
    bad = sum(e["checksum_bad"] for e in c["entries"])
    assert bad == 0, f"{bad} protocol frames failed their checksum - classifier is mis-parsing"
    frames = sum(e["count"] for e in c["entries"] if e["category"] == "protocol_frame")
    assert frames > 100, "corpus should contain the official session's frames"


def test_gatt_data_is_not_counted_as_protocol_frames():
    """Device names and connection parameters must never appear as protocol opcodes."""
    c = newest_corpus()
    for e in c["entries"]:
        if e["category"] != "protocol_frame":
            continue
        for ex in e["examples"]:
            raw = bytes.fromhex(ex)
            assert raw[0] in (0xA5, 0xA4, 0xAB), (e["protocol_opcode"], ex)
            # 0x41524d4f... is ASCII 'ARMOR' - the phantom the greedy parser produced
            assert not ex.lower().startswith("41524d4f"), "device-name buffer leaked into protocol frames"


def test_corpus_separates_the_three_kinds_of_ble_traffic():
    c = newest_corpus()
    cats = {e["category"] for e in c["entries"]}
    assert "protocol_frame" in cats
    assert cats - {"protocol_frame"}, "descriptor/attribute traffic must be recorded, not dropped"


def test_official_button_frames_appear_in_the_corpus():
    c = newest_corpus()
    btn = [e for e in c["entries"] if e["category"] == "protocol_frame" and e["protocol_opcode"] == "0x02"
           and e["att_name"].startswith("Handle Value Notification")]
    assert btn, "the 155 official button frames should be in the corpus"
    e = btn[0]
    assert e["count"] == 155 and list(e["lengths"]) == ["18"]
