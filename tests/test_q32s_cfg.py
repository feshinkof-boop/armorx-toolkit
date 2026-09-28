"""Regression tests for tools/q32s/q32s_cfg.py and the D2 candidate CFG artifact."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "q32s"))
import q32s_cfg  # noqa: E402

ASM = REPO / "results" / "q32s" / "v41-disassembly.asm"
TABLES = REPO / "results" / "q32s" / "v41-table-branches-image-wide.json"
ART = REPO / "results" / "firmware" / "d2-candidate-cfg.json"


class TestOperandParsing:
    def test_decimal_stack_offset(self):
        # The trap: b[sp+1092] is DECIMAL. 1080 + 12 => candidate +0x0c (LT).
        assert q32s_cfg.stack_off("b[sp+1092] = r1") == 1092
        assert q32s_cfg.stack_off("b[sp+1093] = r1") == 1093

    def test_hex_stack_offset(self):
        assert q32s_cfg.stack_off("r0 = [sp+0x438]") == 0x438

    def test_parse_int_mixed_bases(self):
        assert q32s_cfg.parse_int("1092") == 1092
        assert q32s_cfg.parse_int("0x438") == 0x438

    def test_candidate_offsets_are_consistent(self):
        # LT at candidate+0x0c and RT at +0x0d must be reachable by both renderings.
        assert q32s_cfg.stack_off("b[sp+1092] = r1") - 1080 == 0x0C
        assert q32s_cfg.stack_off("b[sp+1093] = r1") - 1080 == 0x0D


@pytest.mark.skipif(not ASM.exists(), reason="disassembly absent")
class TestTableMasking:
    def test_table_payload_is_not_a_block_start(self):
        cfg = q32s_cfg.Cfg(q32s_cfg.load_instructions(ASM), TABLES, (0x1E0AC14, 0x1E0E414))
        # 0x1e0dbe4 was previously swept as "tbb [r10]" - it is table payload, not code.
        assert 0x1E0DBE4 not in cfg.starts
        assert not any(cfg.lo <= s < cfg.lo + 1 for s in cfg.starts if s == 0x1E0DBE4)

    def test_tables_are_present_in_the_source_json(self):
        assert len(q32s_cfg.table_ranges(TABLES)) > 50


@pytest.mark.skipif(not ART.exists(), reason="artifact absent")
class TestCandidateCfgArtifact:
    def art(self):
        return json.loads(ART.read_text())

    def test_root_is_the_containing_function_entry(self):
        assert self.art()["dominator_root"] == "0x1e0ac14"

    def test_r13_copy_dominates_both_builders(self):
        d = self.art()["dominance"]
        for marker in ("B14_build", "B14_builder_entry", "D28_build", "B14_compare_gate"):
            assert "C_copy_r13_into_candidate" in d[marker], marker

    def test_packed_bit_seed_is_conditional_not_universal(self):
        d = self.art()["dominance"]
        assert "C_copy_r13_into_candidate" in d["packed_bit_seed_14B"]
        # the seed must NOT dominate the build, i.e. it sits on an optional arm
        assert "packed_bit_seed_14B" not in d["B14_build"]
        assert "packed_bit_seed_14B" not in d["B14_builder_entry"]

    def test_reachability_alone_cannot_order_them(self):
        v = self.art()["verdicts"]
        assert v["C_copy_r13 vs B14_build"] == "CYCLIC_BOTH_ORDERS_POSSIBLE"

    def test_copy_precedes_builders_on_the_forward_path(self):
        p = self.art()["paths_from_entry"]["D28_build"]
        assert p.index("0x1e0cd24") < p.index("0x1e0dad2") < p.index("0x1e0e2c2")

    def test_second_seed_is_not_declared_dead(self):
        assert "not claimed as dead" in (REPO / "results" / "firmware" / "d2-candidate-cfg.md").read_text()
