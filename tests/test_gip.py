"""Offline GIP input parsing tests with synthetic frames.

The frames below are built from the documented field layout, not copied from a
capture, so they are explicitly synthetic and contain only proven structure.
"""

import pytest

from armorx import gip


def synthetic_report(*, length=48, sequence=0xCA, buttons_low=0x01, buttons_high=0x00,
                     lt=0, rt=0, left=(0xDD, 0xFD), right=(0xAF, 0xFD),
                     counters=(0x16F4, 0x16F4)):
    buf = bytearray(length)
    buf[0] = 0x20
    buf[1] = 0x00
    buf[2] = sequence
    buf[3] = 0x2C
    buf[4] = buttons_low
    buf[5] = buttons_high
    buf[6] = lt & 0xFF
    buf[7] = (lt >> 8) & 0xFF
    buf[8] = rt & 0xFF
    buf[9] = (rt >> 8) & 0xFF
    buf[10] = left[0] & 0xFF
    buf[11] = (left[0] >> 8) & 0xFF
    buf[12] = left[1] & 0xFF
    buf[13] = (left[1] >> 8) & 0xFF
    buf[14] = right[0] & 0xFF
    buf[15] = (right[0] >> 8) & 0xFF
    buf[16] = right[1] & 0xFF
    buf[17] = (right[1] >> 8) & 0xFF
    if length >= 48 and counters:
        buf[40:44] = counters[0].to_bytes(4, "little")
        buf[44:48] = counters[1].to_bytes(4, "little")
    return bytes(buf)


def test_steady_state_form_parses():
    report = gip.parse_gip_input(synthetic_report())
    assert report.length == 48 and report.form == "steady"
    assert report.sequence == 0xCA
    assert report.counters == (0x16F4, 0x16F4)


def test_short_form_parses_and_has_no_counters():
    report = gip.parse_gip_input(synthetic_report(length=32))
    assert report.length == 32 and report.form == "short"
    assert report.counters is None


def test_button_bits():
    report = gip.parse_gip_input(synthetic_report(buttons_low=0x11, buttons_high=0x40))
    assert report.a is True
    assert report.m1 is False
    assert report.m2 is True


def test_m1_bit():
    report = gip.parse_gip_input(synthetic_report(buttons_low=0x21))
    assert report.m1 is True and report.a is False


def test_triggers_are_little_endian_16_bit():
    report = gip.parse_gip_input(synthetic_report(lt=1020, rt=0x0102))
    assert report.lt == 1020
    assert report.rt == 0x0102


def test_stick_pairs():
    report = gip.parse_gip_input(synthetic_report(left=(0x1234, 0x5678)))
    assert report.left_stick == (0x1234, 0x5678)


def test_unknown_bytes_are_reported_not_dropped():
    report = gip.parse_gip_input(synthetic_report())
    spans = report.unknown_spans
    assert (18, 40) in spans
    assert (0, 0) not in spans
    covered = sum(end - start for start, end in spans)
    assert covered + 26 == report.length  # 18 field bytes + 8 counter bytes are claimed


def test_unknown_payload_is_preserved_raw():
    report = gip.parse_gip_input(synthetic_report())
    assert bytes(report.raw) == synthetic_report()


def test_wrong_type_byte_is_rejected():
    bad = bytearray(synthetic_report())
    bad[0] = 0x21
    with pytest.raises(gip.GipError, match="type-0x20"):
        gip.parse_gip_input(bytes(bad))


def test_unexpected_length_is_rejected_in_strict_mode():
    with pytest.raises(gip.GipError, match="unexpected report length"):
        gip.parse_gip_input(synthetic_report(length=40))


def test_unexpected_length_is_kept_in_lax_mode():
    report = gip.parse_gip_input(synthetic_report(length=40), strict=False)
    assert report.form == "unexpected" and report.length == 40


def test_lenient_prefix_check():
    odd = bytearray(synthetic_report())
    odd[3] = 0x2D
    with pytest.raises(gip.GipError, match="byte 3"):
        gip.parse_gip_input(bytes(odd))
    assert gip.parse_gip_input(bytes(odd), strict=False).length == 48


def test_short_input_is_rejected():
    with pytest.raises(gip.GipError, match="too short"):
        gip.parse_gip_input(bytes(10))


def test_probable_input_report_predicate():
    assert gip.is_probable_input_report(synthetic_report()) is True
    assert gip.is_probable_input_report(b"\x00" * 48) is False


def test_to_dict_marks_unresolved_semantics():
    payload = gip.parse_gip_input(synthetic_report()).to_dict()
    assert payload["counters_evidence"].startswith("monotonic")
    assert "no digital" in payload["triggers"]["note"]
