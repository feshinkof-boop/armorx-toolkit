"""Tests for the range-gated table-branch extractor and the full dispatch model (2026-09-28 semantics pass).

Two layers:

* pure-logic tests that build a synthetic q32s image in memory and exercise
  ``q32s_tables.find_range_tables`` - these always run;
* assertions over the *tracked* artifacts written by the extractor, so the recorded dispatch model
  cannot silently drift away from the tool.

Image-dependent tests skip when the vendor toolchain or the unpacked image is absent (a fresh clone
has neither, by design).
"""
from __future__ import annotations

import json
import pathlib
import struct
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "q32s"))

import q32s_tables  # noqa: E402

QF = REPO / "results" / "q32s"
FW = REPO / "results" / "firmware"
BASE = 0x01E00000


def _rec(addr, text, size=2):
    return {"addr": addr, "text": text, "size": size}


def test_range_gate_bounds_uses_the_gate_on_the_rebased_index():
    """The bounds check that sets the case count sits on the *rebased* index register."""
    recs = [
        _rec(BASE, "ifs (r1 > 0x2e) goto 0x1e01800"),      # outer range split, not the bounds check
        _rec(BASE + 2, "r2 = r1 + -0xb"),
        _rec(BASE + 4, "if (r2 > 0x2) goto 0x1e01800"),    # bounds check -> 3 cases
        _rec(BASE + 6, "r3 = r2 << 0x1"),
        _rec(BASE + 8, "tbh [r3]"),
    ]
    # three halfword entries at BASE+0xa, in halfword units relative to the table start
    image = bytearray(0x40)
    for i, e in enumerate((0, 2, 4)):
        struct.pack_into("<H", image, 0xA + 2 * i, e)
    # make every target a "real" instruction so alignment scores 1.0
    for t in (BASE + 0xA, BASE + 0xE, BASE + 0x12):
        recs.append(_rec(t, "nop"))
    tabs = q32s_tables.find_range_tables(bytes(image), BASE, recs)
    assert len(tabs) == 1
    t = tabs[0]
    assert t["cases"] == 3
    assert t["base_model"] == "table_start"
    assert t["entry_scale"] == 2
    assert t["confidence"] == 1.0
    assert t["targets"] == [f"{BASE + 0xA:#x}", f"{BASE + 0xE:#x}", f"{BASE + 0x12:#x}"]


def test_index_scaling_step_is_walked_through():
    """`tbh [r3]` where r3 = r2 << 1 must still find the gate on r2."""
    recs = [
        _rec(BASE, "r2 = r1 + -0xd4"),
        _rec(BASE + 2, "if (r2 > 0x5) goto 0x1e01800"),
        _rec(BASE + 4, "r3 = r2 << 0x1"),
        _rec(BASE + 6, "tbh [r3]"),
        _rec(BASE + 8, "nop"),
    ]
    image = bytearray(0x40)
    struct.pack_into("<H", image, 0x8, 0)
    tabs = q32s_tables.find_range_tables(bytes(image), BASE, recs)
    assert len(tabs) == 1
    assert tabs[0]["cases"] == 6          # 0x5 -> 6 cases
    assert tabs[0]["index_src"] == "r1"   # the raw opcode register behind the rebase is named


def test_bounds_check_is_required_before_a_table_is_reported():
    """A bare tbh with no reachable bounds check must not be reported (false-positive control)."""
    recs = [_rec(BASE, "tbh [r3]"), _rec(BASE + 2, "nop")]
    assert q32s_tables.find_range_tables(bytes(0x40), BASE, recs) == []


def test_unscaled_index_still_covers_the_first_entry_after_the_table():
    """Entry 0 must land exactly on the instruction after the table (the self-consistency rule)."""
    recs = [
        _rec(BASE, "r0 = r1 + -0xb"),
        _rec(BASE + 2, "if (r0 > 0x1) goto 0x1e01800"),
        _rec(BASE + 4, "tbh [r0]"),
        _rec(BASE + 0x8, "nop"),   # table is 2 cases * 2 bytes -> ends at +8
        _rec(BASE + 0xA, "nop"),
    ]
    image = bytearray(0x40)
    # entries are halfword offsets from table_start (BASE+6): 2 -> BASE+0xA, 4 -> BASE+0xE
    struct.pack_into("<H", image, 0x6, 2)
    struct.pack_into("<H", image, 0x8, 4)
    recs.append(_rec(BASE + 0xE, "nop"))
    tabs = q32s_tables.find_range_tables(bytes(image), BASE, recs)
    assert len(tabs) == 1
    assert tabs[0]["targets"] == [f"{BASE + 0xA:#x}", f"{BASE + 0xE:#x}"]
    assert tabs[0]["confidence"] == 1.0


@pytest.mark.skipif(not (QF / "v41-table-branches.json").exists(),
                    reason="table-branch artifact not present")
class TestRecordedDispatchModel:
    def _tabs(self):
        return json.loads((QF / "v41-table-branches.json").read_text())

    def test_four_tables_all_fully_aligned(self):
        tabs = self._tabs()
        assert len(tabs) == 4
        assert all(t["confidence"] == 1.0 for t in tabs), "every extracted table must be fully aligned"

    def test_table_opcodes_and_cases(self):
        tabs = {t["branch"]: t for t in self._tabs()}
        assert tabs["0x1e089c4"]["cases"] == 17          # opcodes 0x0B..0x1B
        assert tabs["0x1e08a04"]["cases"] == 5           # opcodes 0xE1..0xE5
        assert tabs["0x1e09060"]["cases"] == 6           # opcodes 0xD4..0xD9
        assert tabs["0x1e08e78"]["cases"] == 6           # sub-dispatch inside opcode 0x05

    def test_targets_never_point_into_the_table_itself(self):
        """A table's own bytes must not be a branch target: every target is at or after table_end."""
        for t in self._tabs():
            end = int(t["table_end"], 16)
            for tg in t["targets"]:
                assert int(tg, 16) >= end, f"{t['branch']} target {tg} points into the table"
            assert t["base_model"] == "table_start"

    def test_d6_d7_d8_d9_are_routed(self):
        tabs = {t["branch"]: t for t in self._tabs()}
        tgt = {0xD4 + i: t for i, t in enumerate(tabs["0x1e09060"]["targets"])}
        assert tgt[0xD6] == "0x1e0921c"
        assert tgt[0xD7] == "0x1e09232"
        assert tgt[0xD8] == "0x1e0928c"
        assert tgt[0xD9] == "0x1e09346"


@pytest.mark.skipif(not (FW / "armorx-command-dispatch-full.json").exists(),
                    reason="dispatch model not generated")
class TestFullDispatchModel:
    def _model(self):
        return json.loads((FW / "armorx-command-dispatch-full.json").read_text())

    def test_opcode_register_and_offset(self):
        p = self._model()["parser"]
        assert p["opcode_register"] == "r1"
        assert "r9+2" in p["opcode_offset_in_frame"]

    def test_every_route_handler_is_a_one_page_address(self):
        for r in self._model()["routes"]:
            a = int(r["handler"], 16)
            assert BASE <= a < BASE + 0x40000

    def test_fc_and_f6_are_recorded_as_unrouted(self):
        """FC/F6 must not be silently mapped: the model says they fall to the default handler."""
        m = self._model()
        ops = {r["opcode"] for r in m["routes"]}
        assert "0xfc" not in ops and "0xf6" not in ops
        assert "0xEF is accepted" in m["dispatch_structure"]["0xE6..0xFF"]

    def test_contradictions_are_recorded_not_buried(self):
        assert len(self._model()["open_contradictions"]) >= 2


@pytest.mark.skipif(not (REPO / "results/reconciliation/firmware-unknown-ledger.json").exists(),
                    reason="ledger not present")
class TestLedgerTransitions:
    def _led(self):
        d = json.loads((REPO / "results/reconciliation/firmware-unknown-ledger.json").read_text())
        return {e["id"]: e for e in d["entries"]}

    def test_frame_base_unknown_is_closed(self):
        assert self._led()["FW-U-024"]["status"] == "RESOLVED"

    def test_new_unknowns_were_added_rather_than_hidden(self):
        led = self._led()
        assert "FW-U-028" in led and "FW-U-029" in led

    def test_f7_not_promoted_to_write_only(self):
        txt = json.dumps(self._led()["FW-U-016"]).lower()
        assert "not promoted to f7_write_only" in txt


def test_modbus_crc_matches_the_live_validated_algorithm():
    """CRC-16/MODBUS (poly 0xA001, init 0xFFFF) is what the live device's 144-byte config uses."""
    def crc16_modbus(data: bytes) -> int:
        crc = 0xFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
        return crc
    # standard check value for CRC-16/MODBUS
    assert crc16_modbus(b"123456789") == 0x4B37
    # and the nibble table the firmware routine indexes must be the one for that polynomial
    lsb = []
    for i in range(16):
        c = i
        for _ in range(4):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
        lsb.append(c & 0xFFFF)
    assert lsb == [0x0000, 0xCC01, 0xD801, 0x1400, 0xF001, 0x3C00, 0x2800, 0xE401,
                   0xA001, 0x6C00, 0x7800, 0xB401, 0x5000, 0x9C01, 0x8801, 0x4400]
