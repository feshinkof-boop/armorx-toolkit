#!/usr/bin/env python3
"""gatt-dump-bleak.py -- independent GATT dump through BlueZ/bluetoothd (Bleak).

Cross-validation rule (project policy): the same fact obtained through two
genuinely independent implementations. This path goes through bluetoothd over
D-Bus (bleak), NOT through Bumble's HCI-socket session - so it is independent of
the capture path A, not a second wrapper around the same parser.

It also records characteristic PROPERTIES, which the Bumble session log did not,
and reads 2A24/2A26/2A19 for the identity cross-check.

Run:  .venv-bumble/bin/python automation/scripts/gatt-dump-bleak.py --out <json>
Note: needs the adapter powered and bluetoothd running, and must NOT run while a
Bumble session owns the adapter (they cannot share it).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
from datetime import datetime, timezone

from bleak import BleakClient, BleakScanner

NAME_PREFIX = "ARMOR-X Pro_"


async def dump(out_path: pathlib.Path) -> int:
    print("scanning (BlueZ/bluetoothd path) ...")
    found = await BleakScanner.discover(timeout=12.0, return_adv=True)
    target = None
    for dev, adv in found.values():
        if (adv.local_name or "").startswith(NAME_PREFIX) or (dev.name or "").startswith(NAME_PREFIX):
            target = (dev, adv)
            break
    if target is None:
        print(json.dumps({"verdict": "DEVICE_NOT_ADVERTISING",
                          "seen": [d.address for d, _ in found.values()]}, indent=1))
        return 2
    dev, adv = target
    print(f"found {adv.local_name or dev.name!r} {dev.address} rssi={adv.rssi}")

    services = []
    identity = {}
    async with BleakClient(dev.address, timeout=25.0) as client:
        for svc in client.services:
            entry = {"uuid": svc.uuid, "description": svc.description,
                     "handle": getattr(svc, "handle", None), "characteristics": []}
            for ch in svc.characteristics:
                c = {"uuid": ch.uuid, "description": ch.description,
                     "handle": getattr(ch, "handle", None),
                     "properties": list(ch.properties),
                     "descriptors": [{"uuid": d.uuid, "handle": getattr(d, "handle", None)}
                                     for d in ch.descriptors]}
                c["uuid_16"] = ch.uuid[4:8].lower()
                entry["characteristics"].append(c)
            services.append(entry)

        for short, label in (("2a24", "model"), ("2a26", "firmware"), ("2a19", "battery")):
            match = next((c for s in services for c in s["characteristics"]
                          if c["uuid_16"] == short), None)
            if not match:
                continue
            try:
                raw = await client.read_gatt_char(match["uuid"])
                identity[short] = {"raw": raw.hex(), "label": label,
                                   "ascii": raw.decode("ascii", "replace").strip("\x00")
                                   if short != "2a19" else None,
                                   "value": raw[0] if short == "2a19" and raw else None}
            except Exception as exc:                      # noqa: BLE001
                identity[short] = {"error": str(exc), "label": label}

    doc = {
        "path": "BlueZ / bluetoothd via Bleak (independent of the Bumble HCI session)",
        "ts": datetime.now(timezone.utc).isoformat(),
        "device": {"address": dev.address, "advertised_name": adv.local_name or dev.name,
                   "rssi": adv.rssi},
        "services": services,
        "identity_reads": identity,
        "evidence": "PROVEN LIVE",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"services": len(services),
                      "characteristics": sum(len(s["characteristics"]) for s in services),
                      "identity": identity}, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/final/real-gatt-services-bleak.json")
    args = ap.parse_args()
    return asyncio.run(dump(pathlib.Path(args.out)))


if __name__ == "__main__":
    raise SystemExit(main())
