#!/usr/bin/env python3
"""Run the C0/C1/C2 causal cases end to end against a virtual ARMOR-X Pro. No hardware.

Why: tomorrow's physical run must be interpretable the moment it finishes. This script proves, in
advance, that the harness and its verdict logic can tell the hypotheses apart - and it exercises the
real executor (`d2_runner.run_steps`), not a copy of it.

Two device hypotheses, both plausible until the real unit is asked:

  H_PRECLEAR_MATTERS : a D2-OFF pre-clear before the D2 enable suppresses streaming, even while a key
                       is pressed  ->  C0 silent, C1 and C2 stream
  H_PRECLEAR_HARMLESS: the pre-clear is irrelevant                    ->  C0, C1 and C2 all stream

If the real run matches neither, that is itself a result and the difference is worth its own case.

Usage:
    offline-causal-run.py [--out DIR]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import d2_cases as C  # noqa: E402
import d2_runner as R  # noqa: E402
from armorx_lab.mock_gatt import MockGattClient, OfflineRecorder  # noqa: E402
from armorx_lab.virtual_device import VirtualArmorX  # noqa: E402


async def operator_task(client: MockGattClient, device: VirtualArmorX) -> None:
    """Stand in for the human: wait until the device is in D2 test mode, then press A twice."""
    for _ in range(2000):
        if device.d2_enabled:
            break
        await asyncio.sleep(0.005)
    await asyncio.sleep(0.01)          # let the popup/observe window open first
    client.press_a_twice()


async def run_case(case: str, *, preclear_is_fatal: bool, outdir: pathlib.Path) -> dict:
    device = VirtualArmorX(preclear_is_fatal=preclear_is_fatal)
    client = MockGattClient(device)
    rec = OfflineRecorder(path=str(outdir / f"{case}-{'preclear_matters' if preclear_is_fatal else 'preclear_harmless'}.jsonl"))
    steps = [s for s in C.sequence(case) if s["op"] != "sanity"]
    # the live harness subscribes to FFE2 notifications during connect/preflight, before the case
    # body; mirror that here or the executor would be observing a link with no notification path.
    await client.start_notify(client.FFE2, rec.on_notify)
    op = asyncio.create_task(operator_task(client, device))
    try:
        await R.run_steps(client, rec, steps)
    finally:
        op.cancel()
    rec.close()
    verdict = R.verdict_from_frames(rec.frames)
    return {
        "case": case,
        "hypothesis": "H_PRECLEAR_MATTERS" if preclear_is_fatal else "H_PRECLEAR_HARMLESS",
        "writes": [f.hex() for f in device.tx],
        "device": {k: v for k, v in device.describe().items() if k != "emitted"},
        "recorder": rec.summary(),
        "verdict": verdict,
    }


async def main_async(outdir: pathlib.Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for fatal in (True, False):
        for case in ("C0", "C1", "C2"):
            results.append(await run_case(case, preclear_is_fatal=fatal, outdir=outdir))
    (outdir / "offline-causal-matrix.json").write_text(json.dumps(
        {"note": "C0/C1/C2 executed against the virtual ARMOR-X Pro; ground truth = official fixtures",
         "results": results}, indent=1) + "\n")

    print(f"{'case':5s} {'hypothesis':22s} {'writes':>6s} {'rx':>5s} {'valid':>6s} {'verdict':26s} keys")
    for r in results:
        v = r["verdict"]
        keys = ",".join(str(k) for k in (v.get("keys") or []))
        print(f"{r['case']:5s} {r['hypothesis']:22s} {len(r['writes']):6d} {r['recorder']['rx_total']:5d} "
              f"{r['recorder']['valid_status']:6d} {v['verdict']:26s} {keys}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent.parent / "results/reconciliation/offline-causal-run"))
    a = ap.parse_args()
    return asyncio.run(main_async(pathlib.Path(a.out)))


if __name__ == "__main__":
    sys.exit(main())
