#!/usr/bin/env python3
"""RT analog piggyback sampling: sample the analog fields inside D2 frames whose transmission is
caused by a DIGITAL event (A), because analog-only changes never trigger a frame themselves.

  P0  baseline      : nothing else touched, A held/released twice
  P1  LT control    : LT fully held, A burst twice inside that hold  (validates the method)
  P2  RT test       : RT fully held, A burst twice inside that hold  (the actual question)

Contract (verified before the run against results/reconciliation/d2-frame-contract.md):
  [3..6] digital key mask, big-endian u32, bit index == key id
  [7..14] four signed int16 BE axes
  [15] LT analog
  [16] RT analog
  [17] trailer / checksum byte

Rules enforced here:
  * ONE popup, ONE sound per mode, and the notification loop stays live while it is open.
  * only rc == 1 is an operator cancel; 2/3/127 are HARNESS_ERROR, never OPERATOR_CANCELLED.
  * a valid frame is exactly 18 bytes, A5 12 02, checksum valid - nothing else is counted.
  * rest is never assumed to be numerically zero; every statistic is measured from the frames.

Usage: rt-analog-piggyback.py --mode P0|P1|P2 --outdir DIR [--observe 6]
Exit: 0 analysed, 1 OPERATOR_CANCELLED, 5 not found, 6 sanity failed, 7 harness/dialog error
"""
from __future__ import annotations

import argparse, asyncio, json, pathlib, statistics, subprocess, sys, time
from collections import Counter
from datetime import datetime, timezone

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from armorx_lab.frames import parse_button_frame          # noqa: E402

try:
    from bleak import BleakClient, BleakScanner
except Exception as exc:                                   # pragma: no cover
    print(f"FATAL: bleak unavailable: {exc}")
    sys.exit(3)

FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"
ID_CHARS = {"2a24": "00002a24-0000-1000-8000-00805f9b34fb",
            "2a26": "00002a26-0000-1000-8000-00805f9b34fb"}
D2_ON = bytes.fromhex("A505D2017D")
D2_OFF = bytes.fromhex("A505D2007C")
Q_0B = bytes.fromhex("A5040BB4")
MFR_PREFIX = bytes.fromhex("5a4a2d5854")
KNOWN_ADDRESS = "2D:37:35:6D:66:11"
DIALOG = str(_HERE.parent / "operator-dialog-kdialog.sh")
LT_ANALOG_INDEX, RT_ANALOG_INDEX = 15, 16

MODES = {
    "P0": {"action": "armorx_rt_analog_p0", "title": "ArmorX RT Analog Test \u2014 Baseline",
           "msg": ("Do not touch LT or RT.\n\nHold A for about 1 second, then release it.\n\n"
                   "Repeat once.\n\nAfter the second release click DONE.")},
    "P1": {"action": "armorx_rt_analog_p1", "title": "ArmorX RT Analog Test \u2014 LT Control",
           "msg": ("Pull LT fully and KEEP IT HELD.\n\nWhile holding LT:\n"
                   "hold A for about 1 second and release it.\nRepeat A once.\n\n"
                   "Then release LT.\n\nClick DONE.")},
    "P2": {"action": "armorx_rt_analog_p2", "title": "ArmorX RT Analog Test \u2014 RT",
           "msg": ("Pull RT fully and KEEP IT HELD.\n\nWhile holding RT:\n"
                   "hold A for about 1 second and release it.\nRepeat A once.\n\n"
                   "Then release RT.\n\nClick DONE.")},
    "P2R": {"action": "armorx_rt_analog_p2r", "title": "ArmorX RT Analog Test \u2014 RT (repeat)",
            "msg": ("REPEAT of the RT measurement.\n\nPull RT fully and KEEP IT HELD.\n\n"
                    "While holding RT:\nhold A for about 1 second and release it.\nRepeat A once.\n\n"
                    "Then release RT.\n\nClick DONE.")},
}


def iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def find_device(timeout: float = 20.0):
    devs = await BleakScanner.discover(timeout=timeout, return_adv=True)
    by_addr = by_mfr = None
    for address, (dev, adv) in devs.items():
        name = dev.name or adv.local_name or ""
        if name.startswith("ARMOR-X Pro"):
            return dev, adv
        if address.upper() == KNOWN_ADDRESS:
            by_addr = (dev, adv)
        if any(bytes(v).startswith(MFR_PREFIX) for v in (adv.manufacturer_data or {}).values()):
            by_mfr = (dev, adv)
    return by_addr or by_mfr or (None, None)


def bytes_stats(values: list[int]) -> dict:
    """Reported statistics for one analog byte. Nothing is assumed about the numeric rest value."""
    if not values:
        return {"n": 0, "mode": None, "median": None, "min": None, "max": None,
                "distinct": {}, "dominant": None, "dominant_fraction": None, "range": None}
    c = Counter(values)
    dom, dom_n = c.most_common(1)[0]
    return {"n": len(values), "mode": dom, "median": statistics.median(values),
            "min": min(values), "max": max(values),
            "distinct": {str(k): v for k, v in sorted(c.items())},
            "dominant": dom, "dominant_fraction": round(dom_n / len(values), 3),
            "range": max(values) - min(values)}


def compare(label: str, base: dict, win: dict, min_delta: int = 8, min_fraction: float = 0.6) -> dict:
    """Did this byte materially and consistently leave its baseline value?

    Material = the dominant value in the window is at least `min_delta` away from the baseline's
    dominant value; consistent = at least `min_fraction` of the window's frames sit on that
    dominant value. Both conditions must hold, so a single stray frame can never carry a verdict.
    """
    if not base.get("n") or not win.get("n"):
        return {"label": label, "verdict": "INSUFFICIENT_FRAMES",
                "baseline": base, "window": win, "delta": None}
    delta = win["dominant"] - base["dominant"]
    moved = abs(delta) >= min_delta and (win["dominant_fraction"] or 0) >= min_fraction
    return {"label": label, "verdict": "CHANGED" if moved else "NO_CHANGE",
            "baseline_dominant": base["dominant"], "window_dominant": win["dominant"],
            "delta": delta, "window_dominant_fraction": win["dominant_fraction"],
            "min_delta_required": min_delta, "baseline": base, "window": win}


async def run_mode(mode: str, outdir: pathlib.Path, observe: float) -> int:
    cfg = MODES[mode]
    if not pathlib.Path(DIALOG).exists():
        print(f"DIALOG_MISSING: {DIALOG}")
        return 7
    dev, _adv = await find_device()
    if not dev:
        print("CONNECT_FAILED: device not found")
        return 5

    frames: list[dict] = []
    t0 = time.monotonic()

    def on_notify(_c, data: bytearray) -> None:
        raw = bytes(data)
        f = parse_button_frame(raw) if (len(raw) == 18 and raw[0] == 0xA5 and raw[2] == 0x02) else None
        ok = bool(f and f.checksum_ok)
        rec = {"t": round(time.monotonic() - t0, 3), "ts": iso(), "hex": raw.hex(), "valid": ok,
               "len": len(raw), "checksum_ok": ok, "mask": (f.mask if f else None),
               "bits": ([i for i in range(32) if f.mask >> i & 1] if f else []),
               "lt": (raw[LT_ANALOG_INDEX] if ok else None),
               "rt": (raw[RT_ANALOG_INDEX] if ok else None),
               "axes": (raw[7:15].hex() if ok else None)}
        frames.append(rec)

    client = BleakClient(dev, timeout=25.0)
    await client.connect()
    identity, tx, cancelled = {}, [], False
    try:
        for k, uuid in ID_CHARS.items():
            try:
                identity[k] = bytes(await client.read_gatt_char(uuid)).hex()
            except Exception:
                identity[k] = None
        await client.start_notify(FFE2, on_notify)
        await asyncio.sleep(0.5)
        got_0b = False
        await client.write_gatt_char(FFE1, Q_0B, response=False)
        tx.append(Q_0B.hex())
        dl = time.monotonic() + 4.0
        while time.monotonic() < dl:
            if any(f["hex"].startswith("a5050b") for f in frames):
                got_0b = True
                break
            await asyncio.sleep(0.1)
        if not got_0b:
            print("SANITY_FAILED: no 0B reply")
            return 6
        await client.write_gatt_char(FFE1, D2_ON, response=False)
        tx.append(D2_ON.hex())
        await asyncio.sleep(0.4)

        proc = await asyncio.create_subprocess_exec(
            "bash", DIALOG, "--id", cfg["action"], "--title", cfg["title"],
            "--message", cfg["msg"], "--button", "DONE", "--cancel", "CANCEL / STOP",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        rc = await proc.wait()
        if rc == 1:
            cancelled = True
        elif rc != 0:
            print(f"HARNESS_ERROR: dialog rc={rc} (not an operator cancel)")
            return 7
        await asyncio.sleep(observe)
    finally:
        try:
            await client.write_gatt_char(FFE1, D2_OFF, response=False)
            tx.append(D2_OFF.hex())
            await asyncio.sleep(0.6)
        except Exception:
            pass
        try:
            await client.disconnect()
        except Exception:
            pass

    valid = [f for f in frames if f["valid"]]
    lt_stats = bytes_stats([f["lt"] for f in valid])
    rt_stats = bytes_stats([f["rt"] for f in valid])
    masks = Counter(f["mask"] for f in valid)
    bits = sorted({b for f in valid for b in f["bits"]})
    result = {"mode": mode, "action_id": cfg["action"], "started": iso(), "identity": identity,
              "tx": tx, "cancelled": cancelled, "host": "linux-bleak-harness",
              "frames_total": len(frames), "valid_frames": len(valid),
              "LT_BASELINE_or_window": lt_stats, "RT_BASELINE_or_window": rt_stats,
              "masks": {str(k): v for k, v in masks.items()}, "bits_seen": bits,
              "per_frame": [{"t": f["t"], "mask": f["mask"], "bits": f["bits"], "lt": f["lt"],
                             "rt": f["rt"], "axes": f["axes"], "hex": f["hex"]} for f in valid]}
    (outdir / f"window-{mode.lower()}.jsonl").write_text(
        "\n".join(json.dumps(f) for f in frames) + ("\n" if frames else ""))
    (outdir / f"result-{mode.lower()}.json").write_text(json.dumps(result, indent=1) + "\n")

    print(f"{mode}: valid={len(valid)}/{len(frames)} bits={bits} masks={dict(masks)}")
    print(f"  LT[15]: {json.dumps({k: v for k, v in lt_stats.items() if k != 'distinct'})}")
    print(f"  RT[16]: {json.dumps({k: v for k, v in rt_stats.items() if k != 'distinct'})}")
    if cancelled:
        print("OPERATOR_CANCELLED")
        return 1
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=sorted(MODES))
    ap.add_argument("--outdir", required=True, type=pathlib.Path)
    ap.add_argument("--observe", type=float, default=6.0)
    a = ap.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    return await run_mode(a.mode, a.outdir, a.observe)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
