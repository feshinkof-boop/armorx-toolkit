#!/usr/bin/env python3
"""Read the unit's configuration (D6) and verify it against the canonical baseline. READ ONLY.

Post-experiment integrity check: after a live session, prove the configuration is still the baseline.

This script sends exactly one frame - the D6 configuration READ request - and only consumes
notifications. It never writes configuration, never disables/enables D2, and never sends a D7/D8
or any other write. It is an integrity readback only: a match here is NOT a new durability proof
(durability requires write -> readback -> settle -> power cycle -> D6 match; that was established
earlier and is unchanged).

Usage:
  read-config-integrity.py --outdir DIR [--expect-sha SHA]
Exit codes: 0 = CONFIG_BASELINE_MATCH, 4 = MISMATCH, 5 = connect failed, 6 = read incomplete
"""
from __future__ import annotations

import argparse, asyncio, hashlib, importlib.util, json, pathlib, sys, time

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
try:
    from bleak import BleakClient
    # d2-differential.py has a hyphen in its name, so it cannot be imported by statement; load it
    # explicitly and reuse its device matcher and characteristic UUIDs rather than duplicating them.
    _spec = importlib.util.spec_from_file_location("d2diff", _HERE / "d2-differential.py")
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    find_device, FFE1, FFE2 = _mod.find_device, _mod.FFE1, _mod.FFE2
except Exception as exc:                                          # pragma: no cover
    print(f"FATAL: {exc}")
    sys.exit(3)

# canonical durable baseline (immutable, never hand-typed into a test: this file is the one reader)
BASELINE_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"
D6_QUERY = bytes.fromhex("a504d67f")
FRAGMENT_PREFIXES = (bytes.fromhex("a414d6"), bytes.fromhex("a40ed6"))
EXPECT_BYTES = 144
READ_WINDOW_S = 12.0


def reassemble(frames: list[bytes]) -> bytes:
    """Concatenate the payloads of the A4 D6 reply frames.

    Layout: A4 | total_len | 0xD6 | ordinal | payload... | checksum. The payload is everything
    between the ordinal and the trailing checksum. Nine 20-byte frames carry 15 bytes each and the
    final 14-byte frame carries 9, giving the 144-byte image.
    """
    out = bytearray()
    for fr in sorted(frames, key=lambda f: f[3]):
        out += fr[4:-1]
    return bytes(out)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True, type=pathlib.Path)
    ap.add_argument("--expect-sha", default=BASELINE_SHA)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    dev, _adv = await find_device()
    if not dev:
        print("READ_FAILED: device not found")
        return 5
    fragments: list[bytes] = []

    def on_notify(_sender, data: bytearray) -> None:
        b = bytes(data)
        if any(b.startswith(p) for p in FRAGMENT_PREFIXES):
            fragments.append(b)

    client = BleakClient(dev, timeout=25.0)
    await client.connect()
    try:
        await client.start_notify(FFE2, on_notify)
        await asyncio.sleep(0.5)
        await client.write_gatt_char(FFE1, D6_QUERY, response=False)
        deadline = time.monotonic() + READ_WINDOW_S
        while time.monotonic() < deadline and len(fragments) < 10:
            await asyncio.sleep(0.2)
        await asyncio.sleep(0.5)
    finally:
        try:
            await client.disconnect()
        except Exception:
            pass

    image = reassemble(fragments)
    sha = hashlib.sha256(image).hexdigest()
    result = {
        "read": "D6 configuration read request a504d67f (no writes sent)",
        "frames": len(fragments),
        "frame_lengths": [len(f) for f in fragments],
        "image_bytes": len(image),
        "sha256": sha,
        "expected_sha256": args.expect_sha,
        "match": sha == args.expect_sha and len(image) == EXPECT_BYTES,
        "note": ("integrity readback only - NOT a durability proof; "
                 "durability = write -> readback -> settle -> power cycle -> D6 match"),
    }
    (args.outdir / "post-integrity-d6.json").write_text(json.dumps(result, indent=1) + "\n")
    (args.outdir / "post-integrity-d6.bin").write_bytes(image)
    print(json.dumps({k: result[k] for k in ("frames", "frame_lengths", "image_bytes",
                                             "sha256", "match")}, indent=1))
    if len(image) != EXPECT_BYTES or not fragments:
        print("READ_INCOMPLETE")
        return 6
    print("CONFIG_BASELINE_MATCH" if result["match"] else "CONFIG_BASELINE_MISMATCH")
    return 0 if result["match"] else 4


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
