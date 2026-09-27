# Open questions (armorx-lab, after the autonomous pass)

Carried forward from the static pass (`baselines/imported-research/unresolved.md`), restated with
the lab's new state.

## Protocol / firmware

1. **D8 fragment length byte** — canonical docs say `len = payload + 5`, the 4.0.8 reconstruction
   reports the same for fragments with no ordinal byte; only one can be right. Test **L07** decides.
   Both forms are implemented (`frames.build_frag(index=...)`).
2. **D8 chunk size for ARMOR-X Pro** — candidates 15 / 43 / 67 (`subpackageLength()-5`).
3. **D8 `0x0A` commit byte meaning**, readback byte offsets, `repeatTime` unit (test L08).
4. **Key ids 5, 12, 20, 21, 30, 31, 32, 33** — no label in any of the six id→label tables.
   Test L03 (single `mapKeys` byte) resolves which are real sources; id 15 = Capture is the first target.
5. **DPI selector → real DPI mapping** — the payload is a 4-bit selector; the preset table is app/
   server side and was not recovered.
6. **DPI reply parser** — request frames are byte-exact; the reply interpretation is unknown.
7. **Lighting semantics** — RGB order, brightness/speed ranges, effect enums, and which element of
   the `LightColorRainBow3` triple is (id, colour, speed) remain UNKNOWN.
8. **144-byte config gaps** — header byte 4, byte 76, and offsets 6–8/26–27/34–35/50–51/58–59/
   66–67/73–75/94–111 unnamed; `motorMin` is declared but never parsed.
9. **`default_005` (240-byte) CRC anomaly** — first two bytes match no standard CRC-16 over four
   candidate scopes; negative result preserved.
10. **E2 semantics** — `A5 04 E2 8B` exists in 4.0.8; whether its reply equals the GATT 2A26 value
    is unverified (test L02).
11. **ZJ-XT provenance** — the mark string is absent from all three APKs; the virtual peripheral
    currently serves it as identity data (2A24) because that is what the toolkit observed live from
    the *device*. Which firmware paths report it is still open.

## Dynamic / tooling

12. **4.0.8 and 2.24 cannot be executed on this host** (arm64-only; no arm64 AVD possible on x86_64,
    translation SIGILLs). Needs a physical arm64 device or arm64 host — this gates the entire
    Phase 9 dynamic matrix.
13. **No ARMOR-X Pro has been attached**, so no baseline, no restore validation, no live tests,
    no btsnoop correlation yet.
14. **Flutter framework version for 4.0.8** — the bundle contains only the Dart runtime banner;
    the framework version is not recorded (UNKNOWN).
15. **2.23/2.24 per-field detail** — D8 payload layout for 2.23, turbo parameter-index→byte mapping
    for 2.23/2.24, and the numeric key-id table for the older builds are only partially resolved
    (4.0.8 was used as the control).

## Next highest-value experiment

**L01 then L03**: attach the ARMOR-X Pro, capture the "as found" 144-byte baseline with a verified
CRC, then flip exactly `mapKeys[15]` to `2` (empty) and confirm the Capture button stops acting —
one byte, fully reversible, and it converts the last provisional key id into PROVEN LIVE.
