# 2.22.0901 — open questions and UNKNOWNs

Everything here is something the static evidence *could not* settle. Each entry states exactly what
would settle it. No filler UNKNOWNs — these are the real gaps.

## Protocol

1. **A4 frame field order.** The interior of an A4 fragment could not be mapped onto wire byte
   positions. The reply handlers (`_ArmorXProConfigWidgetState` @0x89b438,
   `_ConfigsConfigWidgetState` @0x8a6a04) index the received list through an unresolved dynamic
   selector (`GDT[cid_x0 - 0xfcb]`), so the observed indices (0 = header, 4 = opcode,
   6 = fragment index) cannot be translated into byte offsets. Observed constants:
   header 0xA4 / 0xA5, reply opcode 0xD6 (428) / 0xD4 (424) / 0xD7 (430), fragment index 1..10.
   *Settles it:* a Blutter build with resolved selector ids, or a live capture of a 144-byte
   config read/write.
2. **A4 checksum.** No call to `::getCheckSum` exists inside the A4 builders (`0x7a005c`,
   `0x79e158`). Whether the A4 family has a checksum at all, and where, is UNKNOWN.
3. **Exact byte-exact frame for 0x70 (lighting).** `writeLightConfig` @0x7a74c4 builds a 6-element
   `A5 …` frame with the opcode 0x70 at element 2 and 0x00 elsewhere, then patches length/checksum
   later; the full byte sequence for any concrete lighting command was not reconstructed.
   *Settles it:* trace the patch helper that fills element 1 before send.
4. **Guards.** No device-id or firmware-version guard was found on any builder. If a guard exists it
   is at the UI level (which screen is reachable), not in the frame builders.
5. **`devRainbowS` (id 2).** Display name, screen and scan prefix unresolved.

## Config

6. **Residue bytes 2,3,4,10,22,23,30,31,37,38,39,46,47,54,55 and 61-107** of the 144-byte config are
   written through computed indices, so their byte values were not read statically. Byte-for-byte
   equivalence with the 4.0.8 144-byte map is therefore asserted only for the positions listed in
   `config-map.md` §4.
7. **The 4.0.8 reference document is internally inconsistent** about turboSpeedIdx/turboKey
   (section-2 says byte 80 / 81-84; section-3 says 76 / 77-80). 2.22 agrees with section 2.
   The 4.0.8 *binary* was not re-checked here; flagging rather than silently correcting.

## CRC

8. **No shipped 2.22 image carries a valid pre-computed CRC** — both extracted defaults store
   `0x0000`. The CRC rule is proven from three code sites, not from the images. An independent
   image-based confirmation is impossible with the 2.22 data alone.
9. **Site 1 (`::changeGamepadDef` @0x79c894)**: the byte range and the destination of its CRC result
   were not reconstructed. It is the same loop shape and constants as sites 2/3 but its use is
   UNKNOWN (possibly a verify-on-read path).

## Opcode census caveat

10. The census counts *Smi immediates*, and any even immediate ≤ 0x200 can look like an opcode.
    Every surviving hit was hand-read before being called present (documented per-opcode in
    `command-index.md` §4). Opcodes with **no** frame context were classified ABSENT — this is a
    positive statement about the 2.22 image, but a future opcode built at runtime (e.g. from a
    table) rather than from an immediate would be invisible to this method. No such table was
    found: `grep -oE 'List\([0-9]+\) \[(165|328|342)[^]]*\]' pp.txt` → 0 hits.

## Method / reproduction

11. `reconstruct_frames222.py` only finds A5 frames built with `AllocateArray` + array literals.
    A4/AB builders (append-style) are out of its reach by construction — that is why
    `command-index.md` labels 0xD7/0xD8 `STRONG EVIDENCE` rather than `PROVEN STATIC`.
