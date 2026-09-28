#!/usr/bin/env python3
"""One-variable RT identification: W0 (A only) -> W1 (RT held + A) -> W2 (A only).

Answers one question: is digital mask bit 9 RT's digital state?

ONE connection, ONE D2 session, three operator windows. btmon is managed here because it has stalled
silently before: before every window the capture is (re)started if needed, and after every window the file
size is re-measured, so a window can never be credited with HCI coverage it did not have.

Usage: rt-bit9-confirm.py --outdir DIR [--observe 6]
Exit: 0 analysed, 1 OPERATOR_CANCELLED, 5 not found, 6 sanity failed, 7 harness/dialog error
"""
from __future__ import annotations

import argparse, asyncio, json, pathlib, subprocess, sys, time
from datetime import datetime, timezone

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from armorx_lab.frames import parse_button_frame          # noqa: E402
from armorx_lab.analog_analysis import (                   # noqa: E402
    classify_bit9_confirmation, window_bit_stats, RT_BIT_ID,
)

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

NO_TOUCH = ("Do NOT touch LT or RT.\n\nHold A for about 1 second and release it.\n\n"
            "Repeat once.\n\nAfter the second release click DONE.")
RT_HELD = ("Pull RT fully and KEEP IT HELD.\n\nWhile holding RT:\nhold A for about 1 second and release it.\n"
           "Repeat A once.\n\nThen release RT.\n\nClick DONE.")
WINDOWS = [
    ("W0", "armorx_rt_bit9_w0", "ArmorX RT Bit 9 \u2014 Control", NO_TOUCH),
    ("W1", "armorx_rt_bit9_w1", "ArmorX RT Bit 9 \u2014 RT Test", RT_HELD),
    ("W2", "armorx_rt_bit9_w2", "ArmorX RT Bit 9 \u2014 Final Control", NO_TOUCH),
]


def iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Capture:
    """Owns btmon so a stalled capture is detected and replaced rather than assumed."""

    def __init__(self, outdir: pathlib.Path, external_file: pathlib.Path | None = None) -> None:
        self.outdir = outdir
        self.current = external_file
        self.log: list[dict] = []

    def attach(self) -> None:
        """The capture must already be running (started outside, before the connection)."""
        self.log.append({"event": "attach", "file": (self.current.name if self.current else None),
                         "bytes": self._size(), "running": self._running()})

    def _size(self) -> int:
        return self.current.stat().st_size if self.current and self.current.exists() else 0

    def _running(self) -> bool:
        return subprocess.run(["pgrep", "-x", "btmon"], capture_output=True).returncode == 0

    def start(self, tag: str) -> None:
        """(Re)start btmon into a per-window file, then verify it actually grows."""
        if self._running():
            subprocess.run(["sudo", "-n", "pkill", "-x", "btmon"], capture_output=True)
            time.sleep(1.0)
        self.current = self.outdir / f"btmon-{tag}.btsnoop"
        subprocess.Popen(["sudo", "-n", "btmon", "-i", "hci1", "-w", str(self.current)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        time.sleep(2.5)
        grew = False
        base = self._size()
        for _ in range(6):
            time.sleep(1.5)
            if self._size() > base:
                grew = True
                break
        self.log.append({"event": "start", "tag": tag, "file": self.current.name,
                         "alive": self._running(), "grew_on_start": grew, "bytes": self._size()})

    def before_window(self, tag: str) -> dict:
        """Measure the capture before a window. It is NEVER restarted here.

        Restarting btmon mid-connection was tried and it killed the BLE link: btmon takes the HCI user
        channel, so cycling it under a live connection silently produced two empty windows. The capture
        is started once, outside this script, before the connection; here we only measure it and report
        coverage honestly if it stopped growing.
        """
        return {"tag": tag, "file": (self.current.name if self.current else None),
                "bytes_before": self._size(), "btmon_running": self._running()}

    def after_window(self, st: dict) -> dict:
        st["bytes_after"] = self._size()
        st["grew"] = st["bytes_after"] > st["bytes_before"]
        st["hci_coverage"] = bool(st["grew"])
        self.log.append({"event": "window", **st})
        return st

    def stop(self) -> None:
        subprocess.run(["sudo", "-n", "pkill", "-x", "btmon"], capture_output=True)
        time.sleep(1.5)


async def probe_link(client, sink: list[dict], timeout: float = 4.0) -> bool:
    """Active liveness probe using ONLY the permitted 0B sanity query.

    A dead link and a silent device look identical in the frame log, so between windows the control
    channel is re-queried: a fresh 0B reply proves the link carried traffic through that window.
    """
    try:
        if not client.is_connected:
            return False
        before = len(sink)
        await client.write_gatt_char(FFE1, Q_0B, response=False)
        dl = time.monotonic() + timeout
        while time.monotonic() < dl:
            if any(f["hex"].startswith("a5050b") for f in sink[before:]):
                return True
            await asyncio.sleep(0.1)
        return False
    except Exception:
        return False


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


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True, type=pathlib.Path)
    ap.add_argument("--observe", type=float, default=6.0)
    ap.add_argument("--capture-file", type=pathlib.Path, default=None,
                    help="btmon output started OUTSIDE this script; never restarted mid-connection")
    a = ap.parse_args()
    a.outdir.mkdir(parents=True, exist_ok=True)
    if not pathlib.Path(DIALOG).exists():
        print(f"DIALOG_MISSING: {DIALOG}")
        return 7

    cap = Capture(a.outdir, external_file=a.capture_file)
    cap.attach()

    dev, _adv = await find_device()
    if not dev:
        cap.stop()
        print("CONNECT_FAILED: device not found")
        return 5

    tracks: dict[str, list[dict]] = {w[0]: [] for w in WINDOWS}
    current = {"window": None}          # every notification is tagged with the window it arrived in
    results: dict[str, dict] = {}
    tx: list[str] = []
    identity: dict = {}
    cancelled = False
    t0 = time.monotonic()

    def make_notify():
        def on_notify(_c, data: bytearray) -> None:
            raw = bytes(data)
            bucket = tracks[current["window"] or "W0"]
            f = parse_button_frame(raw) if (len(raw) == 18 and raw[0] == 0xA5 and raw[2] == 0x02) else None
            ok = bool(f and f.checksum_ok)
            bucket.append({"window": current["window"], "t": round(time.monotonic() - t0, 3),
                           "ts": iso(), "hex": raw.hex(),
                           "valid": ok, "len": len(raw), "checksum_ok": ok,
                           "mask": (f.mask if f else None),
                           "bits": ([i for i in range(32) if f.mask >> i & 1] if f else []),
                           "lt": (raw[15] if ok else None), "rt": (raw[16] if ok else None),
                           "axes": (raw[7:15].hex() if ok else None)})
        return on_notify

    client = BleakClient(dev, timeout=25.0)
    await client.connect()
    try:
        for k, uuid in ID_CHARS.items():
            try:
                identity[k] = bytes(await client.read_gatt_char(uuid)).hex()
            except Exception:
                identity[k] = None
        await client.start_notify(FFE2, make_notify())
        await asyncio.sleep(0.5)
        got_0b = False
        await client.write_gatt_char(FFE1, Q_0B, response=False)
        tx.append(Q_0B.hex())
        dl = time.monotonic() + 4.0
        while time.monotonic() < dl:
            if any(f["hex"].startswith("a5050b") for f in tracks["W0"]):
                got_0b = True
                break
            await asyncio.sleep(0.1)
        if not got_0b:
            print("SANITY_FAILED: no 0B reply")
            return 6
        await client.write_gatt_char(FFE1, D2_ON, response=False)
        tx.append(D2_ON.hex())
        await asyncio.sleep(0.4)

        for tag, action, title, msg in WINDOWS:
            current["window"] = tag
            cst = cap.before_window(tag)
            proc = await asyncio.create_subprocess_exec(
                "bash", DIALOG, "--id", action, "--title", title, "--message", msg,
                "--button", "DONE", "--cancel", "CANCEL / STOP",
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            rc = await proc.wait()
            if rc == 1:
                cancelled = True
                cap.after_window(cst)
                break
            if rc != 0:
                cap.after_window(cst)
                print(f"HARNESS_ERROR: dialog rc={rc} (not an operator cancel)")
                return 7
            await asyncio.sleep(a.observe)
            cst = cap.after_window(cst)
            current["window"] = None
            link = await probe_link(client, tracks["W0"])
            cst["link_alive_after_window"] = link
            pf = [f for f in tracks[tag] if f["valid"]]
            res = {"window": tag, "title": title, "capture": cst, "valid_frames": len(pf),
                   "frames_total": len(tracks[tag]),
                   "per_frame": [{"t": f["t"], "mask": f["mask"], "bits": f["bits"], "lt": f["lt"],
                                  "rt": f["rt"], "axes": f["axes"], "hex": f["hex"]} for f in pf]}
            results[tag] = res
            (a.outdir / f"window-{tag.lower()}.jsonl").write_text(
                "\n".join(json.dumps(f) for f in tracks[tag]) + ("\n" if tracks[tag] else ""))
            (a.outdir / f"result-{tag.lower()}.json").write_text(json.dumps(res, indent=1) + "\n")
            s = window_bit_stats(res, RT_BIT_ID)
            print(f"{tag}: valid={len(pf)} bit9_frames={s['bit_frames']} bits={s['bits_seen']} "
                  f"rt_range={s['rt_range']} hci={'yes' if cst.get('hci_coverage') else 'NO'}")
            if cancelled:
                break
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
        cap.stop()

    out = {"started": iso(), "identity": identity, "tx": tx, "cancelled": cancelled,
           "capture_log": cap.log, "windows": {k: {kk: vv for kk, vv in v.items() if kk != "per_frame"}
                                               for k, v in results.items()}}
    if all(w in results for w in ("W0", "W1", "W2")):
        out["classification"] = classify_bit9_confirmation(results["W0"], results["W1"], results["W2"])
    (a.outdir / "RESULT.json").write_text(json.dumps(out, indent=1) + "\n")
    if "classification" in out:
        print("VERDICT:", out["classification"]["verdict"])
        for k, v in out["classification"]["criteria"].items():
            print(f"  {k}: {v}")
    if cancelled:
        print("OPERATOR_CANCELLED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
