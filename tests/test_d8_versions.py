#!/usr/bin/env python3
"""Regression tests: the OLD-format (2.22/2.23) and MODERN-format (2.24/4.0.8) D8 macro
builders/taxonomy must not be confusable.

Evidence base: results/reconciliation/d8-taxonomy.md + d8-taxonomy.json (all claims cited to
Blutter asm addresses). Nothing here talks to a device or modifies an APK.

Key invariants enforced:
  * OLD step record is exactly 7 bytes; MODERN step frame is exactly 10 bytes. A builder for one
    family must reject a record of the other family's size.
  * payload length N = 10 + 7n (old) / 10 + 10n (modern).
  * header byte 4: OLD = GamepadAtt.type (att.type), MODERN = constant 0x00.
  * fragmentation framing is IDENTICAL in both families and carries an ordinal byte:
      A4 | (segLen+5) | D8 | (i+1) | seg | csum     total = segLen+5
  * commit frame is identical and its length byte is 0x05, never 0x0A:
      A4 | 05 | D8 | (nfrags+1) | csum
  * chunk source: OLD = hard-coded 15; MODERN = subpackageLength()-5 in {15,43,67}.
"""
from __future__ import annotations

import unittest

COMMIT_LEN_BYTE = 0x05          # PROVEN: 0x79eb7c / 0x798744 / 0x80012c / 0x85aba8  (mov x,#0xa == Smi 5)
OPCODE_D8 = 0xD8
FRAG_HEADER = 0xA4
OLD_RECORD_LEN = 7              # PROVEN: 0x7a6234 mul x16,#7
MODERN_RECORD_LEN = 10          # PROVEN: 0x85cf5c mul x16,#0xa
OLD_CHUNK = 15                  # PROVEN literal
SUBPKG_LENGTHS = (20, 48, 72)   # PROVEN: 0x819238/0x819264/0x819274 and 0x7b9124/0x7b90ec/0x7b9134
MODERN_CHUNKS = tuple(s - 5 for s in SUBPKG_LENGTHS)   # 15, 43, 67

STICK = {0x22: 0x80000000, 0x23: 0x7f000000, 0x24: 0x007f0000, 0x25: 0x00800000,
         0x26: 0x00008000, 0x27: 0x00007f00, 0x28: 0x0000007f, 0x29: 0x00000080,
         0x2a: 0xa55a0000, 0x2b: 0x5a5a0000, 0x2c: 0xa5a50000, 0x2d: 0x5aa50000,
         0x2e: 0x0000a55a, 0x2f: 0x00005a5a, 0x30: 0x0000a5a5, 0x31: 0x00005aa5}


class FormatError(ValueError):
    """Raised when a step record of the wrong family is fed to a builder."""


def crc16_modbus(data: bytes, init: int = 0xFFFF) -> int:
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def sum8(bs) -> int:
    return sum(bs) & 0xFF


# ---------------------------------------------------------------------------------------------
# shared fragmentation framing (identical in every version)
# ---------------------------------------------------------------------------------------------
def build_frag(seg: bytes, ordinal: int) -> bytes:
    if not 1 <= ordinal <= 0xFF:
        raise FormatError("ordinal out of range")
    body = bytes([FRAG_HEADER, len(seg) + 5, OPCODE_D8, ordinal]) + bytes(seg)
    return body + bytes([sum8(body)])


def build_commit(nfrags: int) -> bytes:
    if nfrags < 0:
        raise FormatError("negative nfrags")
    body = bytes([FRAG_HEADER, COMMIT_LEN_BYTE, OPCODE_D8, nfrags + 1])
    return body + bytes([sum8(body)])


def fragment(payload: bytes, chunk: int):
    return [build_frag(payload[i * chunk:(i + 1) * chunk], i + 1)
            for i in range(max(1, (len(payload) + chunk - 1) // chunk))]


# ---------------------------------------------------------------------------------------------
# OLD family (2.22.0901 / 2.23.0609)
# ---------------------------------------------------------------------------------------------
def old_record(duration_ms: int, keys, type_byte: int = 0x80) -> bytes:
    rec = bytes([type_byte]) + ((duration_ms // 8) & 0xFFFF).to_bytes(2, "big")
    km = 0
    for k in keys:
        if k <= 0x21:
            km |= 1 << k
        elif 0x22 <= k <= 0x31:
            km |= STICK[k]
    return rec + (km & 0xFFFFFFFF).to_bytes(4, "big")


def old_payload(records, runkey: int = 46, repeat: int = 200, isrepeat: int = 0,
                att_type: int = 0) -> bytes:
    """records: list of 7-byte records. Rejects anything else (incl. a 10-byte modern frame)."""
    for r in records:
        if len(r) != OLD_RECORD_LEN:
            raise FormatError(
                "OLD format requires %d-byte GamepadDefMap records, got %d (a 10-byte "
                "TranscribeFrame belongs to 2.24/4.0.8)" % (OLD_RECORD_LEN, len(r)))
    n = 10 + OLD_RECORD_LEN * len(records)
    h = bytearray(10)
    h[2], h[3] = (n >> 8) & 0xFF, n & 0xFF
    h[4] = att_type                       # 2.22: GamepadAtt.type
    h[5] = runkey
    h[6] = runkey if runkey != 0 else 5
    h[7] = isrepeat
    h[8], h[9] = (repeat >> 8) & 0xFF, repeat & 0xFF
    body = bytes(h) + b"".join(records)
    crc = crc16_modbus(body[2:])
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF]) + body[2:]


# ---------------------------------------------------------------------------------------------
# MODERN family (2.24.0919 / 4.0.8)
# ---------------------------------------------------------------------------------------------
def modern_frame(duration_ms: int, keys) -> bytes:
    t8 = (duration_ms // 8) & 0xFFF
    km = stk = 0
    for k in keys:
        if k <= 0x20:
            km |= 1 << k
        elif 0x22 <= k <= 0x31:
            stk |= STICK[k]
    return bytes([(t8 & 0x0F) << 4, (t8 >> 4) & 0xFF,
                  (km >> 24) & 0xFF, (km >> 16) & 0xFF, (km >> 8) & 0xFF, km & 0xFF,
                  (stk >> 24) & 0xFF, (stk >> 16) & 0xFF, (stk >> 8) & 0xFF, stk & 0xFF])


def modern_payload(frames, runkey: int = 23, repeat: int = 0, isrepeat: int = 0) -> bytes:
    """frames: list of 10-byte TranscribeFrame frames. Rejects anything else (incl. 7-byte records)."""
    for f in frames:
        if len(f) != MODERN_RECORD_LEN:
            raise FormatError(
                "MODERN format requires %d-byte TranscribeFrame frames, got %d (a 7-byte "
                "GamepadDefMap record belongs to 2.22/2.23)" % (MODERN_RECORD_LEN, len(f)))
    n = 10 + MODERN_RECORD_LEN * len(frames)
    h = bytearray(10)
    h[2], h[3] = (n >> 8) & 0xFF, n & 0xFF
    h[4] = 0x00                           # PROVEN constant 0x85d238
    h[5] = runkey
    h[6] = runkey if runkey != 0 else 5
    h[7] = isrepeat
    h[8], h[9] = (repeat >> 8) & 0xFF, repeat & 0xFF
    body = bytes(h) + b"".join(frames)
    crc = crc16_modbus(body[2:])
    return bytes([(crc >> 8) & 0xFF, crc & 0xFF]) + body[2:]


# =============================================================================================
class TestFamilyIsolation(unittest.TestCase):
    """The two families cannot be silently interchanged."""

    def test_old_rejects_modern_10_byte_frame(self):
        ten = modern_frame(500, [1])
        self.assertEqual(len(ten), 10)
        with self.assertRaises(FormatError):
            old_payload([ten])
        with self.assertRaises(FormatError):
            old_payload([old_record(100, [0]), ten])   # mixed list must also fail

    def test_modern_rejects_old_7_byte_record(self):
        seven = old_record(100, [0])
        self.assertEqual(len(seven), 7)
        with self.assertRaises(FormatError):
            modern_payload([seven])
        with self.assertRaises(FormatError):
            modern_payload([modern_frame(500, [1]), seven])

    def test_record_sizes_are_the_documented_ones(self):
        self.assertEqual(len(old_record(100, [0])), OLD_RECORD_LEN)
        self.assertEqual(len(modern_frame(500, [1])), MODERN_RECORD_LEN)

    def test_payload_length_formulas(self):
        for i in (0, 1, 2, 3, 8):
            recs = [old_record(100, [k]) for k in range(i)]
            self.assertEqual(len(old_payload(recs)), 10 + 7 * i)
            frs = [modern_frame(100, [k]) for k in range(i)]
            self.assertEqual(len(modern_payload(frs)), 10 + 10 * i)

    def test_header_byte4_differs_between_families(self):
        # OLD: att.type; MODERN: constant 0
        self.assertEqual(old_payload([old_record(100, [0])], att_type=0x00)[4], 0x00)
        self.assertEqual(old_payload([old_record(100, [0])], att_type=0x3C)[4], 0x3C)
        self.assertEqual(modern_payload([modern_frame(100, [0])])[4], 0x00)

    def test_runkey_zero_substitution_is_shared_and_must_be_supplied_explicitly(self):
        # both families: byte6 = runKey with 0 -> 5 (0x79ca70 / 0x85d314)
        self.assertEqual(old_payload([old_record(100, [0])], runkey=0)[6], 5)
        self.assertEqual(modern_payload([modern_frame(100, [0])], runkey=0)[6], 5)


class TestFramingIdenticalAcrossVersions(unittest.TestCase):
    """The A4 fragmentation framing (incl. the ordinal byte) is shared by every version."""

    def test_ordinal_at_frame_offset_3_and_len_equals_total(self):
        for ver, payload, chunk in (
                ("2.22.0901", old_payload([old_record(100, [0])]), OLD_CHUNK),
                ("2.23.0609", old_payload([old_record(200, [0]), old_record(400, [1])]), OLD_CHUNK),
                ("2.24.0919", modern_payload([modern_frame(500, [1]), modern_frame(100, [])]), 15),
                ("4.0.8", modern_payload([modern_frame(500, [1])]), 15)):
            with self.subTest(ver=ver):
                frames = fragment(payload, chunk)
                for i, f in enumerate(frames):
                    self.assertEqual(f[0], FRAG_HEADER)
                    self.assertEqual(f[2], OPCODE_D8)
                    self.assertEqual(f[3], i + 1, "ordinal byte must be i+1 at frame offset 3")
                    self.assertEqual(f[1], len(f), "len byte must equal total frame length")
                    self.assertEqual(f[1], (len(f) - 5) + 5)
                    self.assertEqual(f[-1], sum8(f[:-1]))

    def test_old_data_fragment_carries_ordinal_too(self):
        # regression guard for the CONTRADICTED "no ordinal byte in old format" claim
        f0 = fragment(old_payload([old_record(100, [0])]), OLD_CHUNK)[0]
        self.assertEqual(f0[3], 1)
        self.assertEqual(len(f0), 20)   # 4 header + 15 payload + 1 csum

    def test_modern_data_fragment_carries_ordinal(self):
        # the imported 4.0.8 doc claimed no ordinal byte -> 19-byte frames were wrong
        frames = fragment(modern_payload([modern_frame(500, [1])]), 15)
        self.assertEqual(len(frames[0]), 20)
        self.assertEqual(frames[0][3], 1)
        self.assertNotEqual(len(frames[0]), 19)

    def test_commit_frame_exists_for_every_version(self):
        for ver, payload, chunk in (
                ("2.22.0901", old_payload([old_record(100, [0])]), OLD_CHUNK),
                ("2.23.0609", old_payload([old_record(200, [0]), old_record(400, [1])]), OLD_CHUNK),
                ("2.24.0919", modern_payload([modern_frame(500, [1])]), 15),
                ("4.0.8", modern_payload([modern_frame(500, [1])]), 15)):
            with self.subTest(ver=ver):
                c = build_commit(len(fragment(payload, chunk)))
                self.assertEqual(c[0], FRAG_HEADER)
                self.assertEqual(c[2], OPCODE_D8)

    def test_all_three_chunk_classes_work_for_modern(self):
        p = modern_payload([modern_frame(500, [1])])
        for chunk in MODERN_CHUNKS:
            frames = fragment(p, chunk)
            self.assertEqual(len(frames), 1 if chunk >= len(p) else 2)
            for i, f in enumerate(frames):
                self.assertEqual(f[3], i + 1)
                self.assertEqual(f[1], len(f))


class TestCommitFrame(unittest.TestCase):
    """Every version's commit frame must have the documented length byte 0x05 (never 0x0A)."""

    def test_documented_length_byte_0x05_every_version(self):
        for ver in ("2.22.0901", "2.23.0609", "2.24.0919", "4.0.8"):
            with self.subTest(ver=ver):
                c = build_commit(2)
                self.assertEqual(c[1], COMMIT_LEN_BYTE)
                self.assertEqual(c, bytes.fromhex("A4 05 D8 03 84"))

    def test_0x0a_is_never_the_commit_length_byte(self):
        for n in range(0, 12):
            self.assertNotEqual(build_commit(n)[1], 0x0A)
            # and the whole commit frame must not contain a standalone 0x0A *as its length byte*
            self.assertNotEqual(build_commit(n)[:2], bytes([FRAG_HEADER, 0x0A]))

    def test_commit_count_is_nfrags_plus_one_and_checksum_closes(self):
        for n in range(0, 12):
            c = build_commit(n)
            self.assertEqual(c[3], n + 1)
            self.assertEqual(len(c), 5)
            self.assertEqual(c[-1], sum8(c[:-1]))

    def test_commit_len_byte_is_seglen_plus_five_at_seglen_zero(self):
        # commit == the ordinary fragment formula evaluated on an empty segment
        empty = build_frag(b"", 1)
        self.assertEqual(empty[1], COMMIT_LEN_BYTE)
        self.assertEqual(empty[1], len(empty))


class TestChunkTaxonomy(unittest.TestCase):
    """OLD chunk is a literal 15; MODERN chunk is subpackageLength()-5 in {15,43,67}."""

    def test_subpackage_length_set_and_derived_chunks(self):
        self.assertEqual(SUBPKG_LENGTHS, (20, 48, 72))
        self.assertEqual(MODERN_CHUNKS, (15, 43, 67))

    def test_old_chunk_is_not_derived_from_subpackage_length(self):
        # 2.22/2.23 have no subpackageLength symbol at all -> chunk must be a literal, and the
        # builder must not accept a 43/67 chunk as "the old default".
        self.assertEqual(OLD_CHUNK, 15)
        # a device with subpkg 48/72 would yield 43/67: those must be rejected by an OLD builder
        class OldBuilder:
            chunk = OLD_CHUNK
            def build(self, payload):
                if self.chunk != OLD_CHUNK:
                    raise FormatError("2.22/2.23 hard-code chunk 15 (fmov d1,#15.0 @0x79e300)")
                return fragment(payload, self.chunk)
        b = OldBuilder()
        self.assertTrue(b.build(old_payload([old_record(100, [0])])))
        b.chunk = 43
        with self.assertRaises(FormatError):
            b.build(old_payload([old_record(100, [0])]))

    def test_modern_builder_rejects_chunk_not_in_table(self):
        for bad in (0, 5, 16, 42, 44, 100):
            self.assertNotIn(bad, MODERN_CHUNKS)


class TestKnownVectors(unittest.TestCase):
    """Pinned vectors (DERIVED, see d8-version-test-vectors.json)."""

    def test_2_22_vector(self):
        p = old_payload([old_record(100, [0])])
        self.assertEqual(p.hex(" ").upper(),
                         "11 FB 00 11 00 2E 2E 00 00 C8 80 00 0C 00 00 00 01")
        self.assertEqual([f.hex(" ").upper() for f in fragment(p, 15)],
                         ["A4 14 D8 01 11 FB 00 11 00 2E 2E 00 00 C8 80 00 0C 00 00 5E",
                          "A4 07 D8 02 00 01 86"])
        self.assertEqual(build_commit(2).hex(" ").upper(), "A4 05 D8 03 84")

    def test_4_08_max_time_vector(self):
        p = modern_payload([modern_frame(32760, [24])])
        self.assertEqual(p.hex(" ").upper(),
                         "02 FF 00 14 00 17 17 00 00 00 F0 FF 01 00 00 00 00 00 00 00")
        self.assertEqual(fragment(p, 15)[0].hex(" ").upper(),
                         "A4 14 D8 01 02 FF 00 14 00 17 17 00 00 00 F0 FF 01 00 00 C4")

    def test_imported_4_08_vector_is_rejected(self):
        # the imported vector used 0x0A and omitted the ordinal -> must not be produced here
        c = build_commit(2)
        self.assertNotEqual(c.hex(" ").upper(), "A4 0A D8 03 89")
        frames = fragment(modern_payload([modern_frame(500, [1]), modern_frame(100, [])]), 15)
        self.assertEqual(len(frames[0]), 20)                               # ordinal byte present
        self.assertNotEqual(frames[0].hex(" ").upper()[:8], "A4 14 D8 97")  # not the ordinal-less form
        self.assertEqual(frames[0][3], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
