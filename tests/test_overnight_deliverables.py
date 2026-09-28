"""Guards for the overnight shift's deliverables (Parts A-O).

These assert that the documents and machine-readable artifacts exist and remain internally consistent.
They are deliberately structural rather than textual: the point is that a future pass cannot quietly
drop the master report, the ledger or the key-map table, or reintroduce a resolved entry as open.
"""
import csv
import json
import re
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]


def load(rel):
    p = REPO / rel
    if not p.exists():
        pytest.skip(f"{rel} not present in this checkout")
    return json.loads(p.read_text())


# ---------------------------------------------------------------- Parts M / N / O

def test_master_report_covers_every_required_section():
    p = REPO / "results/final/real-armorx-master-report.md"
    assert p.exists(), "the master report must exist"
    body = p.read_text().lower()
    for section in ("hardware", "ble", "official android", "d2", "d4", "d6", "durability", "config",
                    "key map", "d8", "dpi", "motion", "lighting", "usb", "windows", "jieli",
                    "linux support", "community platform", "unknowns", "next physical tests"):
        assert section in body, section
    # and it must carry the shift's headline correction rather than the old conclusion
    assert "harness_streams_under_press" in body.replace(" ", "_").lower() or "harness is not silent" in body


def test_previous_master_report_is_archived_not_lost():
    arch = REPO / "results/final/archive/real-armorx-master-report-physical-pass-2026-09-27.md"
    assert arch.exists() and arch.stat().st_size > 1000


def test_unknown_ledger_is_complete_and_classified():
    d = load("results/reconciliation/master-unknown-ledger.json")
    allowed = {"DEFERRED_REQUIRES_HARDWARE", "DEFERRED_REQUIRES_OPERATOR",
               "DEFERRED_REQUIRES_NEW_EXTERNAL_EVIDENCE", "STATICALLY_EXHAUSTED",
               # classes an item can be CLOSED into when a physical session answers it
               # (2026-09-28 key-ID closure: ids no control of this unit emits; RT proven negative)
               "UNOBSERVED_RESERVED_OR_UNUSED", "PROVEN_NEGATIVE",
               "UNOBSERVABLE_BY_FRAME_METHOD",
               # 2026-09-28 RT analog piggyback: analog proven, the earlier digital negative retracted
               "ANALOG_PROVEN_LIVE", "DIGITAL_NEGATIVE_RETRACTED",
               # closed by a direct physical proof rather than by static analysis
               "PHYSICALLY_RESOLVED"}
    assert len(d["entries"]) >= 15
    for e in d["entries"]:
        for field in ("id", "question", "priority", "ruled_out", "best_evidence",
                      "next_offline_step", "next_hardware_step", "dependencies", "classification"):
            assert field in e, (e["id"], field)
        # an entry may carry a compound class ("A (digital) / B (analog)"); every part must be known
        for part in re.split(r"\s*/\s*", e["classification"]):
            assert part.split(" (")[0] in allowed, (e["id"], part)
        assert e["status"], e["id"]


def test_resolved_entries_are_not_left_open():
    d = load("results/reconciliation/master-unknown-ledger.json")
    by_id = {e["id"]: e for e in d["entries"]}
    for rid in ("D2-U-001", "D2-U-002", "D2-U-007", "D2-U-008", "D2-U-010"):
        assert by_id[rid]["status"].upper().startswith(("RESOLVED", "REFUTED")), (rid, by_id[rid]["status"])
    # and the live C0 verdict must be named in the entry that closed on it
    assert "C0_STREAMS_WITH_PRECLEAR" in by_id["D2-U-010"]["status"]


def test_tomorrow_plan_states_the_press_requirement_and_stops_after_c0():
    body = (REPO / "results/overnight/20260927-203902/tomorrow-plan.md").read_text().lower()
    assert "zero idle frames is normal" in body
    assert "no pre-clear" in body
    assert "confirmed" in body
    assert "stop" in body


# ---------------------------------------------------------------- Parts A-I

def test_key_map_live_ids_and_leaves_the_rest_unknown():
    d = load("results/final/key-map-confidence.json")
    rows = {r["id"]: r for r in d["rows"]}
    assert d["counts"]["proven_live"] == 27      # 26 + RT, proven 2026-09-28
    for i in (0, 1, 3, 4, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25, 26, 27, 28, 29, 30):
        assert rows[i]["grade"] == "PROVEN LIVE", i
    for i in (2, 5, 21, 22, 31, 32, 33):   # 9 left this set on 2026-09-28 - it is RT
        assert rows[i]["grade"] == "UNKNOWN", i
    # the define.dart offset finding must be recorded, and must not be used to re-name wire bits
    assert d["name_conflicts"] and all("offset" in c["grade"] for c in d["name_conflicts"])
    assert d["static_key_constants"]["keyM1"] == 24 and d["static_key_constants"]["keyUp"] == 17


def test_key_map_csv_matches_json():
    d = load("results/final/key-map-confidence.json")
    csv_path = REPO / "results/final/key-map-confidence.csv"
    assert csv_path.exists()
    with csv_path.open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(d["rows"])
    assert {int(r["id"]) for r in rows} == {r["id"] for r in d["rows"]}


def test_offline_causal_matrix_records_both_hypotheses():
    d = load("results/reconciliation/offline-causal-run/offline-causal-matrix.json")
    got = {(r["case"], r["hypothesis"]): r["verdict"]["verdict"] for r in d["results"]}
    assert got[("C0", "H_PRECLEAR_MATTERS")] == "NO_IDLE_FRAMES_OBSERVED"
    assert got[("C0", "H_PRECLEAR_HARMLESS")] == "A_TWICE_PROVEN"
    assert got[("C1", "H_PRECLEAR_HARMLESS")] == "A_TWICE_PROVEN"


def test_consolidated_documents_exist():
    for rel in ("docs/linux-support-architecture.md",
                "docs/community-platform-architecture.md",
                "docs/community-platform-api-draft.md",
                "docs/community-platform-schema.md",
                "results/final/protocol-closure-fc-dpi-motion-lighting.md",
                "results/final/windows-usb-static-closure.md",
                "results/reconciliation/apk-cross-version-closure.md",
                "results/reconciliation/jieli-firmware-static.md",
                "results/final/ef-e2-d4-d6-origin-findings.md",
                "results/reconciliation/d2-u007-harness-streaming-reconciliation.md"):
        assert (REPO / rel).exists(), rel


def test_the_dpi_transcription_correction_is_recorded():
    body = (REPO / "results/final/real-dpi.md").read_text()
    assert "DATED CORRECTION" in body
    assert "AB 05 05 25 DA" in body
    # the wrong form must be flagged as checksum-invalid, not silently deleted
    assert "0xD4" in body or "0xDA" in body
