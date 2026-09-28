#!/usr/bin/env python3
"""Tests for the DPI / trigger-command (F7 / F6 / FC) static reconstruction.

Covers: the frame-literal reconstruction tool (deterministic, on a synthetic assembly fixture),
the checksum rule, the committed corpus, the cross-version matrix, the ledger entries and the
F7-is-not-trigger-travel refutation. Nothing here touches hardware.
"""

import importlib.util
import json
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
CORPUS = REPO / "results/reconciliation/dpi-trigger-command-corpus.json"
LEDGER = REPO / "results/reconciliation/master-unknown-ledger.json"
TOOL = REPO / "automation/scripts/frame-literal-scan.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("frame_literal_scan", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def corpus():
    return json.loads(CORPUS.read_text())


# ---------------------------------------------------------------- tool behaviour

def test_tool_exists_and_is_importable(tool):
    assert callable(tool.reconstruct)
    assert callable(tool.scan_tree)


def test_reconstructs_a_frame_from_a_synthetic_literal(tool, tmp_path):
    """A minimal AllocateArray literal must decode to exact bytes (Smi halved) + sum8 trailer."""
    src = tmp_path / "synthetic.dart"
    src.write_text("""  void _ build(/* No info */) async {
    // ** addr: 0x1000, size: 0x10
    // 0x1000: AllocateArray
    //     0x1000: bl              #0xd2aab4  ; AllocateArrayStub
    // 0x1004: r16 = 330
    //     0x1004: mov             x16, #0x14a
    // 0x1008: StoreField: r0->field_f = r16
    //     0x1008: stur            w16, [x0, #0xf]
    // 0x100c: r16 = 8
    //     0x100c: mov             x16, #8
    // 0x1010: StoreField: r0->field_13 = r16
    //     0x1010: stur            w16, [x0, #0x13]
    // 0x1014: r16 = 494
    //     0x1014: mov             x16, #0x1ee
    // 0x1018: ArrayStore: r0[0] = r16  ; List_4
    //     0x1018: stur            w16, [x0, #0x17]
    // 0x101c: StoreField: r0->field_1b = rZR
    //     0x101c: stur            wzr, [x0, #0x1b]
    // 0x1020: bl              #0x819078  ; [package:moojiang/define.dart] ::getCheckSum
  }
""")
    recs = tool.scan_tree(tmp_path)
    assert len(recs) == 1
    r = recs[0]
    assert r["bytes"] == "A5 04 F7 A0"   # Smi 330->0xA5, 8->0x04, 494->0xF7, trailer 0xA5+0x04+0xF7
    assert r["length_byte"] == 4
    assert r["opcode"] == "F7"


def test_checksum_is_sum8_of_preceding_bytes(tool, corpus):
    checked = 0
    for e in corpus["entries"]:
        if not e.get("frame") or "checksum" not in e:
            continue
        checked += 1
        b = [int(x, 16) for x in e["frame"].split()]
        assert (sum(b[:-1]) & 0xFF) == b[-1], f"bad trailer in {e['frame']}"
        assert e["checksum_valid"] is True
    assert checked >= 8, "the checksum rule must be exercised on the complete frames"


def test_corpus_never_reports_a_frame_for_runtime_dynamic_writers(corpus):
    """writeDpiConfig / writeStepLengthConfig have runtime length+value: layout only, no frame."""
    dyn = [e for e in corpus["entries"] if e.get("reconstruction", "").startswith("LIMITED")]
    assert dyn, "the two dynamic writers must be marked LIMITED"
    for e in dyn:
        assert e["frame"] is None
        assert e["static_layout"]
        assert e["version"] != "4.0.8 (live)"


# ---------------------------------------------------------------- proven frames

def test_f7_read_frame_is_pinned(corpus):
    f7 = [e for e in corpus["entries"] if (e.get("frame") or "").startswith("A5 04 F7")]
    assert f7, "the F7 read frame A5 04 F7 A0 must be in the corpus"
    assert any(e["frame"] == "A5 04 F7 A0" for e in f7)
    assert any(e["role"] == "READ request" for e in f7)
    assert any(e["version"] == "4.0.8" for e in f7)


def test_f6_variants_are_pinned(corpus):
    frames = {e.get("frame") for e in corpus["entries"]}
    assert "A5 05 F6 80 20" in frames
    assert "A5 04 F6 9F" in frames
    assert "A5 05 F6 07" in frames or any(
        e.get("static_layout", "").startswith("A5 05 FC|F6") for e in corpus["entries"])


def test_fc_has_three_separated_roles(corpus):
    feats = {e["feature"] for e in corpus["entries"] if "FC" in (e.get("frame") or "") or "FC" in e.get("static_layout", "")}
    assert any("DPI" in f for f in feats)
    assert any("transcription" in f for f in feats), "the A5 0B FC transcribe role must be separated"
    trans = [e for e in corpus["entries"] if "transcription" in e["feature"]]
    assert len(trans) == 4                      # start/stop x 2 versions
    prefixes = {e["static_layout"].split(" <")[0] for e in trans}
    assert prefixes == {"A5 0B FC 00", "A5 0B FC 01"}
    assert all(e["frame"] is None for e in trans), "11-byte frame: only the prefix is static"


def test_live_dpi_pair_recorded_with_grade(corpus):
    live = {e["frame"]: e for e in corpus["entries"] if e["evidence_grade"] == "PROVEN LIVE"}
    assert live["A5 05 FC 80 26"]["direction"].startswith("TX")
    assert live["A5 05 FF FC A5"]["direction"].startswith("RX")


# ---------------------------------------------------------------- cross-version

def test_cross_version_matrix(corpus):
    byver = {}
    for e in corpus["entries"]:
        byver.setdefault(e["version"], []).append(e)
    assert "2.22.0901" not in byver, "2.22.0901 must contribute no F7/F6/FC frame"
    assert corpus["counts"]["first_version_with"] == {"F7": "2.24.0919", "F6": "2.24.0919", "FC": "2.23.0609"}
    v2306 = byver["2.23.0609"]
    assert all("F6" not in (e.get("frame") or "") and "F7" not in (e.get("frame") or "") for e in v2306)
    assert any("F7" in (e.get("frame") or "") for e in byver["2.24.0919"])
    assert any("F6" in (e.get("frame") or "") for e in byver["2.24.0919"])
    assert any("F7" in (e.get("frame") or "") for e in byver["4.0.8"])


# ---------------------------------------------------------------- refutation + ledger

def test_f7_is_not_claimed_to_be_trigger_travel():
    txt = (REPO / "results/final/real-trigger-travel.md").read_text()
    assert "CONTRADICTED" in txt
    assert "步长精度" in txt and "摇杆" in txt      # the strings that refute the hypothesis
    assert "A5 04 F7 A0" in txt
    assert "no connection exists in the binary" in txt.lower() or "no connection" in txt.lower()


def test_corpus_states_the_refutation():
    md = (REPO / "results/reconciliation/dpi-trigger-command-corpus.md").read_text()
    assert "No entry claims F7 is trigger travel" in md
    assert "摇杆" in md


def test_ledger_has_the_new_items():
    d = json.loads(LEDGER.read_text())
    ids = {e.get("id"): e for e in d["entries"]}
    assert ids["TRG-U-002"]["status"] == "CLOSED_NEGATIVE"
    assert ids["TRG-U-002"]["classification"] == "STATICALLY_EXHAUSTED"
    assert ids["DPI-U-003"]["status"] == "OPEN"
    assert ids["PRS-U-001"]["classification"] == "DEFERRED_REQUIRES_HARDWARE"
    assert ids["DPI-U-004"]["status"] == "CLOSED_SEPARATE_FEATURE"
    assert ids["DPI-U-002"]["status"] == "PARTIALLY_RESOLVED"


def test_no_hardware_claim_in_this_pass():
    """This pass was static-only: no experiment directory was created for it."""
    exps = list((REPO / "results/experiments").glob("*trigger*")) + \
           list((REPO / "results/experiments").glob("*dpi-trigger*"))
    assert exps == [], "the DPI/trigger phase must not have produced a hardware experiment"


def test_frame_inventory_is_complete_and_consistent():
    inv = json.loads((REPO / "results/reconciliation/frame-literal-inventory.json").read_text())
    assert set(inv["by_version"]) == {"2.22.0901", "2.23.0609", "2.24.0919", "4.0.8"}
    total = 0
    for ver, ks in inv["by_version"].items():
        for k in ks:
            total += 1
            b = k["frame"].split()
            assert b[0] in ("A5", "AB"), f"{k['frame']} is not a frame"
            if k["complete"]:
                assert int(b[1], 16) == len(b), f"length byte {b[1]} != {len(b)} bytes in {k['frame']}"
                assert (sum(int(x, 16) for x in b[:-1]) & 0xFF) == int(b[-1], 16), f"bad trailer {k['frame']}"
    assert total >= 90


def test_inventory_covers_the_part19_backlog_families():
    inv = json.loads((REPO / "results/reconciliation/frame-literal-inventory.json").read_text())
    groups = {k["group"] for ks in inv["by_version"].values() for k in ks}
    for fam in ("motion & gyro", "lighting", "config read"):
        assert fam in groups, f"the {fam} family must appear in the inventory"
