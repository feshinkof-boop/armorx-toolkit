"""Regression fixtures built from the REAL official 4.0.8 BLE session (2026-09-27).

Source of every byte here: an Android HCI snoop of the official BIGBIG WON 4.0.8 app
(com.moojiang.bigbigwon.mygt, versionCode 409) talking to the real ARMOR-X Pro.
Capture sha256 bbaf10bd337a840ee0316291cd53f442859b55d8ce10c2414973d9c59248ba2f.
Nothing in this file is hand-typed: the fixtures were extracted from the capture by script and are
checked in as tests/vectors/official-button-test-fixtures.json.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "automation/scripts"))

from armorx_lab import frames as F  # noqa: E402

FX = json.loads((REPO / "tests/vectors/official-button-test-fixtures.json").read_text())
B = FX["button"]


def h(s):
    return bytes.fromhex(s)


# ---------------------------------------------------------------- framing / parser gate

def test_valid_input_length_is_18_bytes():
    frames = [B["a_initial_press"]["bytes"], B["a_release"]["bytes"], B["second_press"]["bytes"]] + \
             [f["bytes"] for f in B["a_held_frames"]]
    for raw in frames:
        assert len(h(raw)) == 18
        pf = F.parse_button_frame(h(raw))
        assert pf is not None and pf.checksum_ok


def test_frame_2_is_0x02_in_4_0_8():
    """The 4.0.8 parser gate is frame[2] == 0x02 (static: @0xacfaac; confirmed live)."""
    for raw in [B["a_initial_press"]["bytes"], B["a_release"]["bytes"]]:
        assert h(raw)[2] == 0x02
    # and a frame whose subcode differs must be rejected outright
    bad = bytearray(h(B["a_initial_press"]["bytes"])); bad[2] = 0x03
    bad[17] = sum(bad[:17]) & 0xFF
    assert F.parse_button_frame(bytes(bad)) is None


def test_checksum_is_verified_and_a_bad_one_is_not_input():
    raw = h(B["a_initial_press"]["bytes"])
    assert F.checksum(raw[:17]) == raw[17]
    bad = bytearray(raw); bad[17] ^= 0xFF
    assert F.parse_button_frame(bytes(bad)) is None, "a frame failing checksum is not evidence"


# ---------------------------------------------------------------- the D2 echo trap

def test_d2_echo_is_not_input():
    """The 5-byte D2 echo carries the same bytes as the command and must never count as input."""
    for echo in FX["d2_echoes"]:
        assert echo["bytes"] == FX["commands"]["D2_enable"]["bytes"] == "a505d2017d"
        assert F.parse_button_frame(h(echo["bytes"])) is None
    # every non-button command/reply in the fixture set must be rejected as input too
    for name, rec in FX["commands"].items():
        assert F.parse_button_frame(h(rec["bytes"])) is None, name
    for frag in FX["d6_fragments"]:
        assert F.parse_button_frame(h(frag["bytes"])) is None


# ---------------------------------------------------------------- the A key

def test_a_is_bit_zero_and_release_is_mask_zero():
    press = F.parse_button_frame(h(B["a_initial_press"]["bytes"]))
    release = F.parse_button_frame(h(B["a_release"]["bytes"]))
    assert press.mask == 0x00000001 and press.keys == [0]
    assert release.mask == 0x00000000 and release.keys == []
    assert F.KEY_NAMES_PROVEN_LIVE[0] == "A"


def test_repeated_held_reports_do_not_count_as_separate_presses():
    """A held button repeats ~every 12 ms; those repeats are ONE press."""
    stream = [h(B["a_initial_press"]["bytes"])] + [h(f["bytes"]) for f in B["a_held_frames"]] \
             + [h(B["a_release"]["bytes"])]
    assert len(stream) >= 5, "fixture must contain repeated press reports"
    ev = F.press_transitions(stream)
    assert [e["event"] for e in ev] == ["PRESS", "RELEASE"], ev
    assert all(e["key_id"] == 0 for e in ev)


def test_two_physical_presses_yield_four_transitions():
    """The real official A-twice sequence: PRESS, RELEASE, PRESS, RELEASE."""
    stream = [h(B["a_initial_press"]["bytes"]), h(B["a_release"]["bytes"]),
              h(B["second_press"]["bytes"]), h(B["second_release"]["bytes"])]
    ev = F.press_transitions(stream)
    assert [e["event"] for e in ev] == ["PRESS", "RELEASE", "PRESS", "RELEASE"]


# ---------------------------------------------------------------- event-driven semantics

def test_idle_silence_is_valid_not_failure():
    """Zero frames while nothing is pressed is NORMAL: the stream is event-driven."""
    idle = FX["windows"]["idle_window"]
    assert idle["button_frames"] == 0
    assert idle["meaning"].startswith("VALID_EVENT_DRIVEN_SILENCE")
    assert idle["end_s"] > idle["start_s"] > 0


def test_physical_action_is_required_for_an_event_driven_test():
    """A run that never pressed anything cannot demonstrate the stream: it can only show silence."""
    assert FX["windows"]["press_window"]["button_frames"] > 0
    assert B["counts"]["total_button_frames"] == 155
    assert B["counts"]["mask_00000001"] == 29 and B["counts"]["mask_00000000"] == 126
    # the official capture also proves the frame count is bounded by presses, not time
    assert FX["d2_disable"]["delta_s"] > 100


def test_known_commands_rebuild_to_the_captured_bytes():
    """Rebuilding the captured command bytes must reproduce them exactly (no drift)."""
    assert F.build_short(0x0B).hex() == FX["commands"]["0B_query"]["bytes"]
    assert F.build_short(0xEF, bytes(8)).hex() == FX["commands"]["EF_query"]["bytes"]
    assert F.build_short(0xE2).hex() == FX["commands"]["E2_query"]["bytes"]
    assert F.build_short(0xD4).hex() == FX["commands"]["D4_query"]["bytes"]
    assert F.build_short(0xD6).hex() == FX["commands"]["D6_query"]["bytes"]
    assert F.build_short(0xD2, b"\x01").hex() == FX["commands"]["D2_enable"]["bytes"]
    assert F.build_short(0xD2, b"\x00").hex() == FX["commands"]["D2_disable"]["bytes"]


def test_official_write_type_was_write_command():
    """PROVEN LIVE: D2 enable travels as ATT Write Command (0x52) on handle 0x0075."""
    en = FX["commands"]["D2_enable"]
    assert en["op"] == "0x52" and en["handle"] == "0x0075"


def test_d6_reply_is_ten_frames_reassembling_to_the_durable_config():
    """CORRECTED 2026-09-27: the D6 read is TEN frames (nine 20-byte + one 14-byte), not eight.

    An earlier extraction truncated the list at 8 and several documents inherited the error. The
    ten frames carry 135 + 9 = 144 payload bytes, which reassemble to exactly the lab's durable
    baseline (sha256 bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6).
    """
    import hashlib
    frags = FX["d6_fragments"]
    assert len(frags) == 10
    assert [int(f["bytes"][6:8], 16) for f in frags] == list(range(1, 11)), "1-based contiguous ordinals"
    assert all(f["bytes"].startswith(("a414d6", "a40ed6")) for f in frags)
    assert [f["length"] for f in frags] == [20] * 9 + [14], "nine full frames then a short tail frame"
    payload = b"".join(bytes.fromhex(f["bytes"])[4:-1] for f in frags)
    assert len(payload) == 144
    assert hashlib.sha256(payload).hexdigest() == FX["d6_read"]["reassembled_sha256"]
    assert FX["d6_read"]["matches_durable_baseline"] is True
    # every frame self-validates
    for f in frags:
        raw = bytes.fromhex(f["bytes"])
        assert raw[1] == len(raw) and (sum(raw[:-1]) & 0xFF) == raw[-1]


def test_official_config_read_equals_the_durable_baseline():
    """The strongest cross-check available offline.

    The official app's D6 read (10 frames, reassembled in ordinal order) must reproduce the lab's
    durable baseline byte for byte. If this ever fails, either the fixture extraction or the
    baseline has moved, and the whole configuration story needs re-examination.
    """
    import hashlib
    frags = FX["d6_fragments"]
    payload = b"".join(bytes.fromhex(f["bytes"])[4:-1] for f in frags)
    assert len(payload) == 144
    baseline = REPO / "baselines/device/ZJ-XT_2741_2D-37-35-6D-66-11/20260927-170400-baseline-as-found.bin"
    if not baseline.exists():
        pytest.skip("baseline binary not present in this checkout")
    raw = baseline.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FX["d6_read"]["reassembled_sha256"]
    assert raw == payload, "official D6 read must equal the durable baseline byte for byte"


def test_last_d6_frame_is_shorter_and_still_validates():
    """A reassembler that assumes a constant frame length would silently truncate to 135 bytes."""
    frags = FX["d6_fragments"]
    tail = frags[-1]
    raw = bytes.fromhex(tail["bytes"])
    assert len(raw) == 14 and raw[1] == 14 and raw[3] == 10
    assert (sum(raw[:-1]) & 0xFF) == raw[-1]
    assert len(raw[4:-1]) == 9
    full = frags[:-1]
    assert all(len(bytes.fromhex(f["bytes"])) == 20 for f in full)
    assert len(full) * 15 + 9 == 144
