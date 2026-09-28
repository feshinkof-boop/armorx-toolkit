# Verdict — D2-U-002

**PROVEN STATIC: the `0x24` at `0x91d168` (`cmp w0, #0x24`) in the 2.24 `_RainbowTestState::analysisData`
(entry `0x91d130`) is the Dart Smi (tagged) encoding of the integer 18 — `0x24 = 18 << 1 = 0x12 << 1` — and it
is compared against `data[1]`, the frame's byte at index 1 (the frame length/type field, whose value is
`0x12` = 18 for a full 18-byte report frame).** The operand `w0` is the return of a one-argument element
accessor on a `List<int>` and is therefore a tagged Smi: the same class's D2 frame builder stores each byte as
`2 x value` (`0x0091e3c4: mov x17, #0x14a` for 0xA5, `mov x17, #0x1a4` for 0xD2, `mov x17, #2` for 0x01, and the
GrowableList length 5 as `mov x0, #0xa`), so a tagged `0x24` untags to `0x12` = 18, while the integer 36 would
have been emitted as `0x48` and is arithmetically excluded. This is independently confirmed by the 2.22.0901 and
2.23 builds, which compile the identical gate with an explicit untag (`0x8e2450`/`0x8b06e8: sbfx x1, x0, #1,
#0x1f`) followed by `cmp x1, #0x12` (= 18), and by the sibling constant in the same function (`0x172` in 2.24
vs `0xb9` = 185 in 2.23 — ratio exactly 2, the same tagged/untagged factor). It is **not** 36, **not** a 36-byte
frame length, **not** a container `.length` (the accessor takes one argument; the no-argument property getter in
the same class is a different call), **not** an array index (the index is the separate immediate `mov x16, #2`
= Smi 1), **not** a byte offset, and **not** an enum value. Residual: the dispatch target of
`GDT[cid_x0 - 0x30c]` is unnamed in the dump, so the accessor is identified only as "a one-int-argument accessor
on `List<int>`" (`operator[]`/`elementAt`); nothing in the verdict depends on that name.
