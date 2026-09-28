"""Deterministic checks on the captured official Android session.

These read committed artifacts only: no phone, no adapter, no network.
"""
import hashlib
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
AX = REPO / "results/experiments/official-vs-harness-session-20260927-190741/official-session/transport-attempt-20260927-193109/official-session-live"
BASE_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"


def _j(name):
    return json.loads((AX / name).read_text())


def test_installed_app_matches_the_repository_4_0_8_pull():
    ident = _j("app-identity.json")
    assert ident["runtime_classification"] == "OFFICIAL_4_0_8_MATCH"
    assert ident["package"]["versionName"] == "4.0.8"
    assert ident["package"]["versionCode"] == 409
    assert ident["package"]["debuggable"] is False
    assert ident["package"]["instrumentation_libraries_present"] == []
    assert ident["package"]["splits"]["base.apk"] == ident["repo_reference"]["base_apk_sha256"]
    # and the repo copy really hashes to that value
    repo_apk = REPO / "apk/extracted/4.0.8/splits/base.apk"
    if repo_apk.exists():
        assert hashlib.sha256(repo_apk.read_bytes()).hexdigest() == ident["repo_reference"]["base_apk_sha256"]


def test_official_d2_is_identical_to_the_harness_d2():
    g = _j("official-gatt-sequence.json")
    en = g["d2_enable"]
    assert en["value"] == "a505d2017d"
    assert en["op"] == "Write Command (0x52)"
    assert en["handle"] == "0x0075"
    assert g["d2_disable"]["value"] == "a505d2007c"
    assert len(en["echo_frames"]) == 2


def test_official_streams_buttons_and_is_event_driven():
    b = _j("official-button-test.json")
    assert b["idle_window"]["valid_button_frames"] == 0, "stream must be event-driven, not continuous"
    a = b["a_twice"]
    assert a["performed"] is True
    events = [t["event"].split()[0] for t in a["transitions"]]
    assert events == ["PRESS", "RELEASE", "PRESS", "RELEASE"]
    assert [t["mask"] for t in a["transitions"]] == ["00000001", "00000000", "00000001", "00000000"]
    assert a["other_bits_ever_set"] == "NONE", "only the A bit may be set"
    assert a["frame_length"] == 18 and a["checksum_valid"] is True
    assert a["frames_total"] == 155 and a["frames_with_A_bit"] == 29


def test_official_link_is_unbonded_and_unencrypted():
    h = _j("official-hci-summary.json")
    assert h["security"]["bonded"] is False
    assert h["security"]["encrypted"] is False
    assert h["security"]["smp_frames"] == 0
    assert h["security"]["encryption_change_events"] == 0
    assert h["security"]["armorx_in_bond_list"] is False
    assert h["att_mtu"]["negotiated"] == 64, "the default 23 exchange must not be mistaken for the final MTU"


def test_earliest_difference_is_the_interval_and_causality_is_not_claimed():
    d = json.loads((REPO / "results/experiments/official-vs-harness-session-20260927-190741/official-vs-harness-diff.json").read_text())
    assert d["overall_status"] == "COMPLETE"
    assert d["earliest_proven_material_difference"]["id"] == "OFFICIAL_CONNECTION_INTERVAL_DIFFERENT"
    assert d["earliest_proven_material_difference"]["causality"] == "NOT established"
    assert d["connection"]["official"]["interval_ms"] == 11.25
    assert d["connection"]["harness"]["interval_ms"] == 7.50
    # the config-read burst is recorded as an observation, never as a proven precondition
    assert d["first_protocol_level_difference"]["id"] == "EXTRA_OFFICIAL_WRITE_OBSERVED"
    assert d["first_protocol_level_difference"]["causality"].startswith("NOT established")
    fd = json.loads((REPO / "results/experiments/official-vs-harness-session-20260927-190741/first-divergence.json").read_text())
    assert "MISSING_PRECONDITION" in fd["explicitly_not_labelled"]
    assert fd["no_unknown_official_traffic_replayed"] is True


def test_identical_stages_are_reported_as_identical():
    d = json.loads((REPO / "results/experiments/official-vs-harness-session-20260927-190741/official-vs-harness-diff.json").read_text())
    assert d["security"]["same"] is True, "both links are unbonded/unencrypted"
    assert d["att_gatt"]["same"] is True, "same MTU and same handles"
    assert d["d2"]["same"] is True, "identical D2 command and write type"


def test_final_d6_matches_and_durability_wording_intact():
    d6 = _j("final-d6.json")
    assert d6["sha256"] == BASE_SHA and d6["verdict"] == "CONFIG_BASELINE_MATCH"
    assert "NOT a new durability proof" in d6["durability_note"]
    v = (REPO / "results/experiments/official-vs-harness-session-20260927-190741/verdict.md").read_text()
    assert "COMPLETE" in v and "DURABLE_OK" in v and "STAGED_OK" in v


def test_the_apparmor_lesson_is_recorded():
    """A capture must be copied to /tmp before tshark; the earlier wrong claim is corrected."""
    p = REPO / "results/experiments/d2-live-differential-20260927-184643/tshark-att.txt"
    text = p.read_text()
    assert "AppArmor" in text and "CORRECTED" in text
