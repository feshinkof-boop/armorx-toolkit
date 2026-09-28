"""Tests for the BigBigWon `.bup` container parser (tools/firmware/armorx_bup.py).

Covers: header parsing, chunk-record walking, round-trip unpack, and the malformed-input
cases the format invites (bad magic, truncated record, corrupt zlib block, empty file,
absurd lengths). The fuzz loop asserts the parser never raises unexpectedly and never
writes outside the caller-supplied output directory.

Fixtures are synthesised in-process, so the tests do not depend on the multi-megabyte
originals; one optional test pins the real V41 image hash when the evidence tree is present.
"""
from __future__ import annotations

import hashlib
import pathlib
import struct
import sys
import zlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "firmware"))
import armorx_bup  # noqa: E402

WS = REPO / "research" / "firmware" / "2026-09-28"
V41_BUP = WS / "chinese-v41" / "01战甲X Pro固件-V41.bup"
V41_IMAGE_SHA = "3c73727214801bea5097ad289c6672db3cca6dc9aaf5ea52cf5a81ff0598de26"
V41_APP_SHA = "302a700be0a5b351"


def build_bup(slot_a: bytes = b"", slot_b: bytes = b"",
              name_a: str = "null.bin", name_b: str = "XT_TEST_update_s_v99_20260101.ufw",
              block: int = 0x8000) -> bytes:
    """Synthesise a .bup with the documented layout (records of zlib blocks)."""
    hdr = bytearray(0x8B)
    hdr[0:22] = b"BigBigWon Upgrade Pack\x00\x00"
    struct.pack_into("<I", hdr, 0x16, 1)
    hdr[0x1A] = 1
    hdr[0x1B:0x1F] = bytes((0x00, 0x01, 0x1D, 0x00))
    hdr[0x21:0x28] = b"V99\x00\x00\x00"
    hdr[0x2B:0x2B + len(name_a)] = name_a.encode()[:32]
    hdr[0x5B:0x5B + len(name_b)] = name_b.encode()[:32]

    def enc(img: bytes) -> bytes:
        out = bytearray()
        for o in range(0, len(img), block):
            piece = img[o:o + block]
            comp = zlib.compress(piece)
            out += struct.pack("<II", len(comp), len(piece))
            out += comp
        return bytes(out)

    body_a = enc(slot_a) if slot_a else b""
    body_b = enc(slot_b) if slot_b else b""
    if body_a:
        struct.pack_into("<I", hdr, 0x8B - 4, len(body_a))
    data = bytes(hdr)
    if body_a:
        data = data[:0x8B] + body_a
    if body_b:
        data += struct.pack("<I", len(body_b)) + body_b
    return data


def write(tmp_path: pathlib.Path, blob: bytes, name: str = "t.bup") -> pathlib.Path:
    p = tmp_path / name
    p.write_bytes(blob)
    return p


# ------------------------------------------------------------------ happy path
def test_round_trip_single_slot(tmp_path):
    img = bytes(range(256)) * 300  # 76,800 B => 3 blocks
    p = write(tmp_path, build_bup(slot_a=img))
    hdr, images, table = armorx_bup.analyze(p)
    assert hdr["magic"] == "BigBigWon Upgrade Pack"
    assert images[0][1] == img
    assert len(table) == 3
    assert all(c["uncompressed"] <= 0x8000 for c in table)


def test_round_trip_two_slots(tmp_path):
    a, b = b"A" * 40_000, b"B" * 10
    p = write(tmp_path, build_bup(slot_a=a, slot_b=b))
    hdr, images, _ = armorx_bup.analyze(p)
    assert [n for n, _ in images][0] == "null.bin"
    assert images[0][1] == a
    assert len(images) == 2 and images[1][1] == b


def test_incompressible_block_is_stored(tmp_path):
    import os
    img = os.urandom(0x8000)
    p = write(tmp_path, build_bup(slot_a=img))
    _, images, table = armorx_bup.analyze(p)
    assert images[0][1] == img
    # stored zlib blocks are slightly larger than the payload
    assert table[0]["compressed"] > table[0]["uncompressed"]


def test_header_fields_parsed(tmp_path):
    p = write(tmp_path, build_bup(slot_a=b"x" * 10))
    hdr, _, _ = armorx_bup.analyze(p)
    assert hdr["version_string"] == "V99"
    assert hdr["first_record_offset"] == 0x8B
    assert hdr["file_size"] == len((tmp_path / "t.bup").read_bytes())


# ------------------------------------------------------------------- malformed
def test_bad_magic_raises(tmp_path):
    blob = build_bup(slot_a=b"x" * 10)
    blob = b"NotBigBigWon!" + blob[14:]
    with pytest.raises(ValueError):
        armorx_bup.analyze(write(tmp_path, blob))


def test_empty_file_raises(tmp_path):
    with pytest.raises(ValueError):
        armorx_bup.analyze(write(tmp_path, b""))


def test_truncated_file_does_not_crash(tmp_path):
    blob = build_bup(slot_a=bytes(range(256)) * 300, slot_b=b"B" * 40_000)
    p = write(tmp_path, blob[:0x8B + (len(blob) - 0x8B) // 2])
    hdr, images, _ = armorx_bup.analyze(p)  # must return partial data, not raise
    assert hdr["file_size"] < len(blob)
    assert images


def test_corrupt_zlib_block_is_detected(tmp_path):
    """A damaged block must never be emitted as if it were valid data."""
    good = build_bup(slot_a=bytes(range(256)) * 300)      # 3 blocks
    intact = armorx_bup.analyze(write(tmp_path, good, "good.bup"))[2]
    blob = bytearray(good)
    blob[0x8B + 8 + 4] ^= 0xFF                            # damage block 1 payload
    hdr, images, table = armorx_bup.analyze(write(tmp_path, bytes(blob), "bad.bup"))
    assert len(table) < len(intact)          # the corrupt block was not accepted
    assert all(len(c["sha256"]) == 64 for c in table)


def test_absurd_record_lengths_rejected(tmp_path):
    blob = bytearray(build_bup(slot_a=b"x" * 10))
    struct.pack_into("<II", blob, 0x8B, 0xFFFFFFFF, 0xFFFFFFFF)
    with pytest.raises(ValueError):
        armorx_bup.analyze(write(tmp_path, bytes(blob)))


def test_fuzz_never_raises_and_never_writes_outside(tmp_path):
    import random
    rng = random.Random(20260928)
    base = build_bup(slot_a=bytes(range(256)) * 300, slot_b=b"B" * 40_000)
    out = tmp_path / "ifuzz"
    out.mkdir()
    before = {p.name for p in tmp_path.iterdir()}
    for _ in range(400):
        blob = bytearray(base)
        for _ in range(rng.randint(1, 24)):
            blob[rng.randrange(len(blob))] = rng.randrange(256)
        p = tmp_path / "fz.bup"
        p.write_bytes(bytes(blob))
        try:
            hdr, images, table = armorx_bup.analyze(p)
        except ValueError:
            continue
        for idx, (name, img) in enumerate(images):
            (out / f"{idx}.bin").write_bytes(img)
        assert hdr["file_size"] == len(blob)
    assert {p.name for p in tmp_path.iterdir()} == before | {"fz.bup"}


# ------------------------------------------------------- real artifact (pinned)
@pytest.mark.skipif(not V41_BUP.exists(), reason="evidence tree not present")
def test_real_v41_package_pinned_hashes(tmp_path):
    hdr, images, table = armorx_bup.analyze(V41_BUP)
    assert hdr["magic"] == "BigBigWon Upgrade Pack"
    assert hdr["version_string"].startswith("V41")
    assert hdr["board_code_id"] == 0x1d  # 29 = ArmorX Pro body
    assert hdr["board_code_raw"] == "00011d00"
    img = images[0][1]
    assert hashlib.sha256(img).hexdigest() == V41_IMAGE_SHA
    assert len(img) == 1_124_288
    assert len(table) == 35
    assert len(images) == 2  # V41 ships two chip-key variants
    assert hashlib.sha256(images[0][1]).digest() != hashlib.sha256(images[1][1]).digest()
