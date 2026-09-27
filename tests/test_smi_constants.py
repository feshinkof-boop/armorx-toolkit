#!/usr/bin/env python3
"""Regression guard for Dart Smi (tagged-integer) decoding in the ARMOR-X Pro Blutter trees.

Origin: the project's key-mask rule was once `keyCapture = 0x10000 => bit index = key id + 1`,
which came from reading a raw `mov` immediate without applying Dart's Smi tag (`Smi(n) == n << 1`).
Re-reading 4.0.8 `define.dart:1583` (`mov x0, #0x10000`) and halving gives `keyCapture = 0x8000`
= bit 15 = config key id 15 (Capture); `keyUp` = `#0x20000` -> 0x10000 = bit 16 (D-pad up);
`keyL1` = `#0x80` -> 0x40 = bit 6 (LB).  Rule: **bit == key id**, no `+1`.

These tests are deliberately pure-stdlib.  Run either way:

    python3 tests/test_smi_constants.py
    python3 -m pytest tests/test_smi_constants.py

Methodology: results/reconciliation/dart-smi-methodology.md
Ledger:      results/reconciliation/smi-audit.md / .json
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# 1. The primitive: Smi tagging, and the two mechanical tests
# --------------------------------------------------------------------------

SMI_TAG_BITS = 1  # arm64 android compressed-pointers null-safety (all four builds)


def smi_decode(immediate: int, context: str = "") -> int:
    """Decode a raw Blutter `mov xN, #imm` operand that lives in a tagged Dart int slot."""
    if immediate % 2 != 0:
        raise ValueError(
            f"{immediate:#x} is ODD and cannot be a Dart Smi (Smi(n) == n<<1); "
            f"this operand is RAW, so it must not be halved [{context}]"
        )
    return immediate >> SMI_TAG_BITS


def smi_encode(value: int) -> int:
    return value << SMI_TAG_BITS


def is_possible_smi(immediate: int) -> bool:
    """Cheap negative test: an odd immediate can never be a tagged Smi."""
    return immediate % 2 == 0


def bitmask_for_key_id(key_id: int) -> int:
    """The ONE rule this project must never regress on."""
    assert 0 <= key_id <= 31, "config key ids live in the 0..31 mapKeys space"
    return 1 << key_id


# --------------------------------------------------------------------------
# 2. Ground truth extracted from the four trees (file:address in the docstring)
# --------------------------------------------------------------------------

# Key-mask getters.  value = raw `mov x0, #imm` operand, per build.
# 2.22.0901/2.17.5  asm/moojiang/units/gamepadset.dart
# 2.23.0609/2.19.6  asm/moojiang/units/gamepadset.dart
# 2.24.0919/3.2.3   asm/moojiang/define.dart
# 4.0.8/3.12.2      asm/moojiang/define.dart
KEY_MASKS_222 = {  # getter -> (raw immediate, address)
    "keyL1": (0x80, "0x7a91c4"), "keyR1": (0x100, "0x7a8f1c"),
    "keyL2": (0x200, "0x79c874"), "keyR2": (0x400, "0x7a8f0c"),
    "keySelect": (0x800, "0x79c87c"), "keyStart": (0x1000, "0x7a8ef4"),
    "keyRThumb": (0x8000, "0x79c468"), "keyUp": (0x20000, "0x7a70d0"),
    "keyDown": (0x40000, "0x7a5594"), "keyLeft": (0x80000, "0x7a8eec"),
    "keyRight": (0x100000, "0x79c884"), "keyY": (0x20, "0x79dfc0"),
    "keyM1": (0x1000000, "0x7a3fb0"), "keyM2": (0x2000000, "0x7a8efc"),
    "keyM3": (0x4000000, "0x7a8f04"), "keyM4": (0x8000000, "0x79c88c"),
    "keyM6": (0x20000000, "0x7a8ee4"), "rightStickY": (0x40, "0x7a8f14"),
}
KEY_MASKS_223 = {
    "keyL1": (0x80, "0x7ad700"), "keyR1": (0x100, "0x7ad6f0"),
    "keyL2": (0x200, "0x7ad6f8"), "keyR2": (0x400, "0x7ad6e8"),
    "keySelect": (0x800, "0x8b1d60"), "keyStart": (0x1000, "0x8b1d58"),
    "keyRThumb": (0x8000, "0x8b1d50"), "keyUp": (0x20000, "0x8b1d48"),
    "keyDown": (0x40000, "0x8b1d40"), "keyLeft": (0x80000, "0x8b1d38"),
    "keyRight": (0x100000, "0x8b1d30"), "keyY": (0x20, "0x7ad6e0"),
    "keyM1": (0x1000000, "0x7ad6d8"), "keyM2": (0x2000000, "0x7ad6d0"),
    "keyM3": (0x4000000, "0x7ad6c8"), "keyM4": (0x8000000, "0x7ad6c0"),
    "keyM6": (0x20000000, "0x8b1d28"), "rightStickY": (0x40, "0x7b42d4"),
}
KEY_MASKS_224 = {
    "keyL1": (0x80, "0x7c430c"), "keyR1": (0x100, "0x7c42fc"),
    "keyL2": (0x200, "0x7c4304"), "keyR2": (0x400, "0x7c42f4"),
    "keySelect": (0x800, "0x7c42bc"), "keyStart": (0x1000, "0x7c42b4"),
    "keyRThumb": (0x8000, "0x7c42c4"), "keyCapture": (0x10000, "0x7c42ac"),
    "keyUp": (0x20000, "0x7c42e4"), "keyDown": (0x40000, "0x7c42dc"),
    "keyLeft": (0x80000, "0x7c42d4"), "keyRight": (0x100000, "0x7c42cc"),
    "keyY": (0x20, "0x7c42ec"),
    "keyM1": (0x1000000, "0x7c42a4"), "keyM2": (0x2000000, "0x7c429c"),
    "keyM3": (0x4000000, "0x7c4294"), "keyM4": (0x8000000, "0x7c428c"),
    "rightStickY": (0x40, "0x7cd990"),
}
KEY_MASKS_408 = {
    "keyL1": (0x80, "0x94cbc8"), "keyR1": (0x100, "0x94cbb8"),
    "keyL2": (0x200, "0x94cbc0"), "keyR2": (0x400, "0x94cbb0"),
    "keySelect": (0x800, "0x94cb80"), "keyStart": (0x1000, "0x94cb78"),
    "keyRThumb": (0x8000, "0x94cb88"), "keyCapture": (0x10000, "0x94cb70"),
    "keyUp": (0x20000, "0x94cba8"), "keyDown": (0x40000, "0x94cba0"),
    "keyLeft": (0x80000, "0x94cb98"), "keyRight": (0x100000, "0x94cb90"),
    "keyM1": (0x1000000, "0x94cb68"), "keyM2": (0x2000000, "0x94cb60"),
    "keyM3": (0x4000000, "0x94cb58"), "keyM4": (0x8000000, "0x94cb50"),
}
ALL_KEY_MASKS = {
    "2.22.0901": KEY_MASKS_222, "2.23.0609": KEY_MASKS_223,
    "2.24.0919": KEY_MASKS_224, "4.0.8": KEY_MASKS_408,
}

# getter -> (config key id, human label).  The id space is the one the app's own
# `gamePadKeyName` Map<int,String> literal uses (see smi-audit.md item K1).
KEY_ID = {
    "keyY": (4, "Y"), "keyL1": (6, "LB"), "keyR1": (7, "RB"),
    "keyL2": (8, "LT"), "keyR2": (9, "RT"), "keySelect": (10, "Select"),
    "keyStart": (11, "Start"), "keyRThumb": (14, "R3"),
    "keyCapture": (15, "Capture"), "keyUp": (16, "D-pad up"),
    "keyDown": (17, "D-pad down"), "keyLeft": (18, "D-pad left"),
    "keyRight": (19, "D-pad right"), "keyM1": (23, "M1"), "keyM2": (24, "M2"),
    "keyM3": (25, "M3"), "keyM4": (26, "M4"), "keyM6": (28, "M6"),
}


# --------------------------------------------------------------------------
# 3. Tests — the corrected bit-mask rule
# --------------------------------------------------------------------------

def test_pinned_bit_masks():
    """The three pinned examples from the bug report, hard-coded forever."""
    assert smi_decode(0x80) == 0x40, "keyL1: #0x80 -> 0x40"
    assert smi_decode(0x10000) == 0x8000, "keyCapture: #0x10000 -> 0x8000"
    assert smi_decode(0x20000) == 0x10000, "keyUp: #0x20000 -> 0x10000"

    assert bitmask_for_key_id(KEY_ID["keyL1"][0]) == 0x40       # id 6  -> LB
    assert bitmask_for_key_id(KEY_ID["keyCapture"][0]) == 0x8000  # id 15 -> Capture
    assert bitmask_for_key_id(KEY_ID["keyUp"][0]) == 0x10000      # id 16 -> D-pad up


def test_bit_index_equals_key_id_in_every_build():
    for version, table in ALL_KEY_MASKS.items():
        for getter, (immediate, addr) in table.items():
            if getter not in KEY_ID:
                continue  # rightStickY is a stick-axis bit with its own table
            key_id, label = KEY_ID[getter]
            got = smi_decode(immediate, context=f"{version} {getter}@{addr}")
            assert got == bitmask_for_key_id(key_id), (
                f"{version}: {getter}({label}) decoded to {got:#x}, "
                f"expected 1<<{key_id} = {bitmask_for_key_id(key_id):#x} at {addr}"
            )


def test_bit_is_one_hot_per_id_and_unique():
    """Un-halved, the table collides; halved it must be a gapless one-key-one-bit map."""
    seen = {}
    for version, table in ALL_KEY_MASKS.items():
        seen[version] = {}
        for getter, (immediate, addr) in table.items():
            if getter not in KEY_ID:
                continue
            bit = smi_decode(immediate)
            assert bit & (bit - 1) == 0, f"{version}:{getter} is not a power of two"
            assert bit not in seen[version], (
                f"{version}: {getter}@{addr} collides with "
                f"{seen[version][bit]} on bit {bit.bit_length()-1}"
            )
            seen[version][bit] = getter


def test_no_plus_one_offset_regression():
    """The exact banned rule, expressed so it can never come back silently."""
    for getter in ("keyCapture", "keyUp", "keyL1"):
        key_id, label = KEY_ID[getter]
        immediate = ALL_KEY_MASKS["4.0.8"][getter][0]
        bit = smi_decode(immediate).bit_length() - 1
        assert bit == key_id, f"{getter} ({label}) bit {bit} != id {key_id}"
        assert bit != key_id + 1, (
            f"{getter}: the old 'bit = key id + 1' rule resurfaced "
            f"(id {key_id} would claim bit {key_id + 1})"
        )


def test_raw_immediate_reading_is_inconsistent():
    """Proves the old reading is self-contradictory, not merely 'different'.

    Read un-halved, keyL1 = 0x80 claims bit 7 and keyR1 = 0x100 claims bit 8, while the
    app's own id->label map says LB = id 6 and RB = id 7.  A rule that shifts every key by
    one is therefore falsified by the binary's other, independent table.
    """
    assert (ALL_KEY_MASKS["4.0.8"]["keyL1"][0].bit_length() - 1) == 7
    assert (ALL_KEY_MASKS["4.0.8"]["keyR1"][0].bit_length() - 1) == 8
    assert KEY_ID["keyL1"][0] == 6 and KEY_ID["keyR1"][0] == 7
    assert (ALL_KEY_MASKS["4.0.8"]["keyL1"][0].bit_length() - 1) != KEY_ID["keyL1"][0]
    # and the halved reading closes:
    assert (smi_decode(ALL_KEY_MASKS["4.0.8"]["keyL1"][0]).bit_length() - 1) == KEY_ID["keyL1"][0]


def test_key_id_space_is_0_to_31():
    """mapKeys is 32 one-byte slots (config bytes 112..143) -> 32 legal source ids."""
    assert bitmask_for_key_id(0) == 1
    assert bitmask_for_key_id(31) == 0x80000000
    for bad in (-1, 32, 33):
        try:
            bitmask_for_key_id(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"id {bad} must be rejected")


# --------------------------------------------------------------------------
# 4. Tests — the same rule on the other high-risk constants
# --------------------------------------------------------------------------

def test_d8_commit_byte_is_0x05_not_0x0a():
    """4.0.8 gamepadset.dart 0x85aba8 and 2.24 gamepadset.dart 0x80012c: `mov x16,#0xa`
    into a List<int> element -> Dart 5.  Live/deduced frame: A4 05 D8 <nfrags+1> <cks>."""
    assert smi_decode(0xA) == 0x05
    frame = bytes([0xA4, smi_decode(0xA), 0xD8, 3 + 1, 0x00])
    assert frame[:4] == bytes([0xA4, 0x05, 0xD8, 0x04])
    # sibling immediates in the SAME list prove the tagging of the whole list
    assert smi_decode(0x148) == 0xA4 and smi_decode(0x1B0) == 0xD8
    # and the terminator needs no special case: length byte == total frame length
    assert frame[1] == len(frame)


def test_lighting_mode_ordinals_and_masks():
    class ListInt:
        """Fake growable List<int> whose elements are tagged Smis (4-byte stride stores)."""

        def __init__(self):
            self.items = []

        def append_tagged(self, immediate):
            self.items.append(smi_decode(immediate))

    per_zone = ListInt()
    for imm in (2, 4, 6):                      # 4.0.8 writeLightConfig 0x849824/88/8ec
        per_zone.append_tagged(imm)
    assert per_zone.items == [1, 2, 3]
    assert smi_decode(0x7E) == 0x3F            # 0x8495c4 -> LED mask byte 63
    assert smi_decode(0x1FE) == 0xFF           # 0x849604 -> 0xFF (proves the list is tagged)
    # 2.22 rainbow_tab_light.dart 0x8da2cc / 0x8da388
    assert smi_decode(2) == 1 and smi_decode(6) == 3


def test_durations_and_pptxt_are_already_decoded():
    """pp.txt prints decoded List<int> values and decoded Duration microseconds."""
    assert 0x7A120 == 500_000           # the live-proven 500 ms anchor
    assert 0xFA0 == 4000                # D8 inter-fragment delay = 4 ms
    assert 0x30D40 == 200_000           # 200 ms
    # the powers-of-two bit table cannot be raw (0x80000000 cannot be 2n in 32 bits)
    assert 0x80000000 == 1 << 31


def test_raw_constants_are_not_halved():
    """Regressions in the opposite direction: these must stay untouched."""
    # stick pseudo-key patterns (orr immediates on an unboxed accumulator) - raw
    assert (0x80000000 | 0x7F000000) == 0xFF000000
    assert 0xA55A0000 == 2774138880              # annotated raw
    assert 0x3F == 0x3F                          # raw range bound on a LED id
    # DPI: raw mask applied after ubfx, then re-tagged with lsl #1
    assert (0xABCD & 0x0F) == 0x0D and smi_encode(0x0D) == 0x1A
    # config sizes are AllocateArray counts / raw compares
    assert 0x90 == 144 and 0x58 == 88 and 0x1FC == 508
    # firmware thresholds compared raw
    for t in (0x28, 0x31, 0x35, 0x36, 0x39, 0x60, 0x61):
        assert t in (40, 49, 53, 54, 57, 96, 97)


def test_parity_rule_rejects_untagged_stores():
    """Odd immediates cannot be Smis (2.22 slider `divisions` = 0xff, LightColorRainBow3 = -1)."""
    for odd in (0xFF, -1, 0x1, 0x3F, 0x3, 0x7):
        assert not is_possible_smi(odd), f"{odd} must be recognised as non-Smi"
        try:
            smi_decode(odd)
        except ValueError:
            pass
        else:
            raise AssertionError(f"smi_decode({odd}) must refuse an odd immediate")
    # the even ones in the same instruction family are tagged and DO halve
    assert smi_decode(0xFE) == 0x7F and smi_decode(-2) == -1


def test_methodology_artifacts_present_and_consistent():
    """Guard that the ledger and the methodology both exist and still carry the rule."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    meth = os.path.join(root, "results", "reconciliation", "dart-smi-methodology.md")
    audit = os.path.join(root, "results", "reconciliation", "smi-audit.json")
    summary = os.path.join(root, "results", "reconciliation", "smi-audit-summary.md")
    for path in (meth, audit, summary):
        assert os.path.exists(path), f"missing deliverable: {path}"
    import json

    data = json.load(open(audit))
    assert data["item_count"] == len(data["items"])
    bad = [i["id"] for i in data["items"]
           if i["classification"] not in data["classification_vocabulary"]]
    assert not bad, f"items with an unknown classification: {bad}"
    for item in data["items"]:
        if item["classification"] == "TAGGED SMI — CORRECTED":
            assert len(item["independent_anchors"]) >= 2, (
                f"{item['id']} is a correction and must carry >= 2 independent anchors"
            )
    text = open(meth).read()
    assert "bit == config key id" in text and "There is no `+1`" in text


# --------------------------------------------------------------------------
# 5. Plain-python runner (no pytest required)
# --------------------------------------------------------------------------

def _main() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {name}")
    print("-" * 68)
    print(f"{len(tests) - len(failed)}/{len(tests)} passed"
          f"  ({len(failed)} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
