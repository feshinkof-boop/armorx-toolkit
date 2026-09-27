# Emergency restore — STATUS: NOT VALIDATED (do not use on a working device yet)

This tool writes a previously captured known-good ARMOR-X configuration image back to the
controller. **It has not been validated against hardware**, because no ARMOR-X has been reachable
from this host yet.

The script enforces that itself: `emergency-restore.py` refuses to write unless the baseline
manifest contains `"restore_verified": true`, which can only be set after a real D7 write followed
by a D6 read-back produced a byte-identical image. There is no override.

## Prerequisites (exact)

1. A real ARMOR-X Pro session where the harness captured a baseline:
   `automation/scripts/real_device_harness.py --serial <name> baseline`
   → writes `baselines/device/<serial>/baseline_<serial>_144.bin` plus a `.json` manifest with
   `sha256`, `crc_ok`, `declared_len`, `mapkeys`.
2. That manifest must have `crc_ok: true`, `declared_matches: true` and
   `"restore_verified": true` (set by `real_device_harness.py --verify-restore`, which performs the
   write → re-read → compare cycle).
3. The lab adapter isolated and in Bumble mode (`automation/radio/use-bumble.sh`), or the device
   reachable through whatever transport `BumbleTransport` is configured with.

## What it sends

For a 144-byte image with chunk 15 (STRONG EVIDENCE, not proven — see `unresolved.md`):

```
10 × A4 <len> D7 <15 bytes> <sum8>          config write fragments
   A4 0A D8 <n+1> <sum8>                     commit frame (form from the D8 macro writer)
   A5 05 0E 00 B8                            post-write step
   A5 04 D6 7F                               verification read
```

`len` for the fragments is emitted as `payload + 4` (no ordinal byte) because that is the
arithmetically consistent form; the device decides whether it is right. Use `--dry-run` to print
every frame before sending anything.

## Commands

```bash
# inspect only, never writes:
/usr/bin/python3 automation/scripts/emergency-restore/emergency-restore.py \
    --baseline baselines/device/<serial>/ --dry-run

# real restore (only after the manifest has restore_verified: true):
automation/scripts/emergency-restore/emergency-restore.sh --baseline baselines/device/<serial>/
```

Exit codes: `0` restored and verified · `2` refused (validation gate) · `3` no verification reply ·
`4` verification mismatch (device left in an unknown config state — use the other saved baseline or
restore from the Android app).

## Post-restore verification

`0` means: the D6 re-read produced a 144-byte image whose sha256 equals the baseline's sha256.
Anything else is a failure and must be reported as such.

## Honest status

| Item | Status |
|---|---|
| script exists and enforces the gate | WORKING (self-test passes) |
| frames generated matching the protocol research | WORKING (anchors asserted) |
| baseline captured from real hardware | NOT ATTEMPTED — no device session yet |
| restore round-trip validated | NOT ATTEMPTED |
| usable in an emergency | **NO** — until the round-trip has been proven |
