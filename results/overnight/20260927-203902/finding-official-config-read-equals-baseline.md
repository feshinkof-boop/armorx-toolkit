# Finding: the official app's D6 read is byte-identical to our durable baseline

Date: 2026-09-27 (overnight, no hardware used). Evidence: the committed raw snoop
`.../official-session-live/raw/android-official-session.cfa` (sha256 bbaf10bd...).

## What was measured

The official BIGBIG WON 4.0.8 app, connected to the real ARMOR-X Pro, sent the D6 configuration read
request `A5 04 D6 7F` (frame 6265, +59.29 s after connect) and the device answered with **ten frames**:

| # | frame | shape | payload |
|---|---|---|---|
| 1-9 | 6267-6277 | `A4 14 D6 01`..`A4 14 D6 09` (20 bytes each) | 15 bytes each = 135 |
| 10 | 6279 | `A4 0E D6 0A 01 0D 19 1A 1B 1C 1D 1E 1F 64` (14 bytes) | 9 bytes |

Every frame self-validates: `raw[1] == len(raw)` and `sum(raw[:-1]) & 0xFF == raw[-1]`.

Reassembling the payloads in ordinal order gives **144 bytes** with sha256
`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` - which is **exactly** the lab's
durable configuration baseline (`baselines/device/ZJ-XT_2741_2D-37-35-6D-66-11/20260927-170400-baseline-as-found.bin`,
`CONFIG_BASELINE_MATCH = YES`, `DURABLE_OK`).

## Why this matters

1. **Independent validation of the fragment model.** Ordinals start at 1 and are contiguous; the last
   frame of the series is SHORTER (14 bytes, 9 payload bytes instead of 15). Any reassembler that
   assumes a fixed frame length, or that stops at the first short frame, is wrong.
2. **Independent validation of the 144-byte configuration format** and of our baseline's authenticity:
   the official app and the lab see the same bytes.
3. **Correction of a propagated error.** An earlier extraction capped the fragment list at eight, so
   several documents said "eight 20-byte fragments". The true count is 10 frames / 144 payload bytes.
   Corrected in the fixtures, the canonical timeline and the official-session artifacts on 2026-09-27.
   Files that mention "8 fragments" about a DIFFERENT subject (D8 macro segmentation, APK manifests)
   were deliberately left untouched.
4. **It sharpens the C2 hypothesis.** The official app really does read the full configuration before
   enabling D2, and the bytes it gets back are what our baseline already contains - so if that read is
   what arms the Button Test stream, C2's replay (which uses a real read, not invented bytes) is a
   faithful reproduction of the official sequence.

## Grade

PROVEN LIVE (single capture, byte-level, self-validating checksums, and cross-checked against an
independent artifact - the durable baseline).
