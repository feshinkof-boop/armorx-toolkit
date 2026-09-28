#!/usr/bin/env python3
"""F7 getStepLength READ-ONLY live probe (2026-09-28).

Sole objective: does the app's own F7 read request (`A5 04 F7 A0`, getStepLength) produce any live
notification response at all?

READ-ONLY. The only frames this script can send are the three the application itself sends and that
hardware has already accepted:

    A5 04 0B B4     the 0B sanity query           (health control, every phase)
    A5 05 FC 80 26  the DPI read request          (positive control, live-proven)
    A5 04 F7 A0     the F7 getStepLength request  (the subject of the experiment)

No write frames exist anywhere in this file: there is no F7 07/08 form, no FC/F6 selector write, no
D6/D7/D8, no D2, no lighting, no macro traffic. A guard asserts every emitted frame is in the
allow-list before it is written to the characteristic.

Phases follow the brief: A (0B health) -> B (FC positive control) -> C (F7 attempt 1, 3 s) ->
D (0B health) -> E (F7 attempt 2, 5 s) -> F (final 0B + FC control) -> disconnect.

Notification capture is NOT filtered by opcode: every FFE2 frame in each window is recorded with its
raw bytes, declared length, recomputed checksum, opcode and arrival delta.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import sys
import time
from datetime import datetime, timezone

from bleak import BleakClient, BleakScanner

FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"
KNOWN_ADDRESS = "2D:37:35:6D:66:11"
EXPECTED_ADAPTER = "E8:4E:06:8A:F2:00"

Q_0B = bytes.fromhex("A5040BB4")
Q_FC = bytes.fromhex("A505FC8026")
Q_F7 = bytes.fromhex("A504F7A0")
ALLOWED = {Q_0B: "0B sanity query", Q_FC: "FC DPI read (positive control)", Q_F7: "F7 getStepLength read"}

REPLY_0B = bytes.fromhex("A5050B30E5")
REPLY_FC = bytes.fromhex("A505FFFCA5")


def iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")


def cks(frame: bytes) -> int:
    return sum(frame[:-1]) & 0xFF


def parse(frame: bytes) -> dict:
    return {
        "raw": " ".join(f"{b:02X}" for b in frame),
        "length_byte": frame[1] if len(frame) > 1 else None,
        "declared_len_ok": (len(frame) > 1 and frame[1] == len(frame)),
        "opcode": f"0x{frame[2]:02X}" if len(frame) > 2 else None,
        "payload": " ".join(f"{b:02X}" for b in frame[3:-1]) if len(frame) > 4 else "",
        "trailer": f"0x{frame[-1]:02X}" if frame else None,
        "checksum_ok": (len(frame) > 1 and cks(frame) == frame[-1]),
    }


class Runner:
    def __init__(self, outdir: pathlib.Path, capture_file: pathlib.Path | None):
        self.out = outdir
        self.capture_file = capture_file
        self.notifications: list[dict] = []      # every FFE2 frame, phase-tagged
        self.tx: list[dict] = []
        self.phase = "boot"
        self.t0 = time.monotonic()
        self.waiters: list[tuple[bytes, asyncio.Future]] = []

    # ---- plumbing ---------------------------------------------------------
    def log(self, event: str, **kw):
        rec = {"ts": iso(), "t_rel": round(time.monotonic() - self.t0, 3), "event": event, **kw}
        with (self.out / "session.jsonl").open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        return rec

    def notify(self, _char, data: bytearray):
        frame = bytes(data)
        rec = {"ts": iso(), "t_rel": round(time.monotonic() - self.t0, 3), "phase": self.phase,
               "from_tx_s": (round(time.monotonic() - self.last_tx_at, 3)
                             if getattr(self, "last_tx_at", None) else None), **parse(frame)}
        self.notifications.append(rec)
        for want, fut in list(self.waiters):
            if frame == want and not fut.done():
                fut.set_result(rec)

    async def send(self, frame: bytes, label: str) -> dict:
        if frame not in ALLOWED:
            raise RuntimeError(f"REFUSING to send a frame outside the read-only allow-list: {frame.hex()}")
        if cks(frame) != frame[-1]:
            raise RuntimeError(f"frame fails its own checksum: {frame.hex()}")
        rec = {"ts": iso(), "t_rel": round(time.monotonic() - self.t0, 3), "phase": self.phase,
               "tx": " ".join(f"{b:02X}" for b in frame), "label": label}
        self.tx.append(rec)
        self.log("TX", **rec)
        self.last_tx_at = time.monotonic()
        await self.client.write_gatt_char(FFE1, frame, response=False)
        return rec

    async def await_reply(self, want: bytes, timeout: float) -> dict | None:
        fut = asyncio.get_running_loop().create_future()
        self.waiters.append((want, fut))
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.waiters = [(w, f) for w, f in self.waiters if f is not fut]

    def window(self, start_idx: int) -> list[dict]:
        return self.notifications[start_idx:]

    # ---- phases -----------------------------------------------------------
    async def health(self, label: str, timeout: float = 4.0) -> dict:
        before = len(self.notifications)
        await self.send(Q_0B, "0B sanity query")
        reply = await self.await_reply(REPLY_0B, timeout)
        self.log("HEALTH", label=label, healthy=reply is not None,
                 reply=(reply or {}).get("raw"), frames_in_window=len(self.window(before)))
        return {"label": label, "healthy": reply is not None, "reply": reply,
                "other_frames": [n for n in self.window(before) if n["raw"] != (reply or {}).get("raw")]}


async def find_device(timeout: float = 25.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = await BleakScanner.discover(timeout=6.0, return_adv=True)
        for addr, (d, adv) in found.items():
            if addr.upper() == KNOWN_ADDRESS:
                return d, adv.rssi
    return None, None


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--capture-file", default=None)
    ap.add_argument("--fc-window", type=float, default=2.0)
    ap.add_argument("--f7-window-1", type=float, default=3.0)
    ap.add_argument("--f7-window-2", type=float, default=5.0)
    args = ap.parse_args()

    outdir = pathlib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cap = pathlib.Path(args.capture_file) if args.capture_file else None
    r = Runner(outdir, cap)
    res: dict = {"verdict": None, "phases": {}}
    r.log("START", argv=sys.argv, adapter_expected=EXPECTED_ADAPTER, outdir=str(outdir),
          capture=str(cap) if cap else None)

    device, rssi = await find_device()
    if device is None:
        r.log("ABORT", reason="device not advertising")
        (outdir / "analysis.json").write_text(json.dumps({"verdict": "DEVICE_NOT_ADVERTISING"}, indent=1))
        return 3
    r.log("DEVICE", address=device.address, name=device.name, rssi=rssi)

    async with BleakClient(device) as client:
        r.client = client
        r.log("CONNECTED", mtu_hint=None)
        await client.start_notify(FFE2, r.notify)
        r.log("SUBSCRIBED", char=FFE2)

        # ---- PHASE A
        r.phase = "A"
        a = await r.health("pre")
        res["phases"]["A_0B_pre"] = {"healthy": a["healthy"], "reply": (a["reply"] or {}).get("raw")}
        if not a["healthy"]:
            res["verdict"] = "CONTROL_CHANNEL_NOT_HEALTHY"
            r.log("STOP", verdict=res["verdict"], note="F7 was NOT sent")
            await client.disconnect()
            (outdir / "analysis.json").write_text(json.dumps(res, indent=1))
            return 4

        # ---- PHASE B (FC positive control)
        r.phase = "B"
        before = len(r.notifications)
        await r.send(Q_FC, "FC DPI read (positive control)")
        fc = await r.await_reply(REPLY_FC, timeout=args.fc_window)
        await asyncio.sleep(max(0.0, args.fc_window - 2.0))
        res["phases"]["B_FC_control"] = {
            "tx": "A5 05 FC 80 26", "expected": "A5 05 FF FC A5",
            "reported": fc, "all_frames": r.window(before),
            "status": "FC_READ_CONTROL_PASS" if fc else "FC_CONTROL_UNEXPECTED_NO_REPLY"}
        if not fc:
            r.log("FC_NO_REPLY", note="re-running 0B before deciding")
            recheck = await r.health("post_fc_failure")
            res["phases"]["B_0B_recheck"] = {"healthy": recheck["healthy"]}
            if recheck["healthy"]:
                r.log("RECONNECT", note="0B healthy but FC silent - reconnecting once before F7")
                try:
                    await client.disconnect()
                    await asyncio.sleep(1.0)
                    await client.connect()
                    await client.start_notify(FFE2, r.notify)
                    again = await r.health("after_reconnect")
                    res["phases"]["B_0B_after_reconnect"] = {"healthy": again["healthy"]}
                except Exception as exc:                       # noqa: BLE001 - recorded, never hidden
                    res["phases"]["B_0B_after_reconnect"] = {"healthy": None, "error": repr(exc)}

        # ---- PHASE C (F7 attempt 1)
        r.phase = "C"
        before = len(r.notifications)
        await r.send(Q_F7, "F7 getStepLength read (attempt 1)")
        await asyncio.sleep(args.f7_window_1)
        c_frames = r.window(before)
        res["phases"]["C_f7_attempt1"] = {"tx": "A5 04 F7 A0", "window_s": args.f7_window_1,
                                         "frames": c_frames, "frame_count": len(c_frames)}

        # ---- PHASE D (health after attempt 1)
        r.phase = "D"
        d = await r.health("after_f7_1")
        res["phases"]["D_0B_after_f7_1"] = {"healthy": d["healthy"],
                                            "reply": (d["reply"] or {}).get("raw"),
                                            "other_frames": d["other_frames"]}
        if not d["healthy"]:
            res["verdict"] = "LINK_UNHEALTHY_AFTER_F7_1"
            r.log("STOP", verdict=res["verdict"], note="attempt 2 NOT sent")
            await client.disconnect()
            (outdir / "analysis.json").write_text(json.dumps(res, indent=1))
            return 5

        # ---- PHASE E (F7 attempt 2)
        r.phase = "E"
        await asyncio.sleep(1.0)
        before = len(r.notifications)
        await r.send(Q_F7, "F7 getStepLength read (attempt 2)")
        await asyncio.sleep(args.f7_window_2)
        e_frames = r.window(before)
        res["phases"]["E_f7_attempt2"] = {"tx": "A5 04 F7 A0", "window_s": args.f7_window_2,
                                          "frames": e_frames, "frame_count": len(e_frames)}

        # ---- PHASE F (final controls)
        r.phase = "F"
        f = await r.health("final")
        res["phases"]["F_0B_final"] = {"healthy": f["healthy"], "reply": (f["reply"] or {}).get("raw")}
        before = len(r.notifications)
        await r.send(Q_FC, "FC DPI read (post-F7 control)")
        fc2 = await r.await_reply(REPLY_FC, timeout=3.0)
        await asyncio.sleep(1.0)
        res["phases"]["F_FC_final"] = {"reported": fc2, "all_frames": r.window(before),
                                       "status": "FC_READ_CONTROL_PASS" if fc2 else "FC_CONTROL_UNEXPECTED_NO_REPLY"}
        await client.disconnect()
        r.log("DISCONNECTED")

    # ---- verdict (per the brief's three cases; silence is never "write-only")
    c1 = res["phases"]["C_f7_attempt1"]["frames"]
    e1 = res["phases"]["E_f7_attempt2"]["frames"]
    def candidates(frames):
        return [f for f in frames if f["opcode"] not in (None, "0x0B")]
    cand1, cand2 = candidates(c1), candidates(e1)
    fc_ok = res["phases"]["B_FC_control"]["status"] == "FC_READ_CONTROL_PASS"
    f7a = res["phases"]["D_0B_after_f7_1"]["healthy"] and res["phases"]["F_0B_final"]["healthy"]
    if cand1 and cand2 and [x["raw"] for x in cand1] == [x["raw"] for x in cand2]:
        res["verdict"] = "F7_REPLY_PROVEN_LIVE"
    elif (cand1 and not cand2) or (cand2 and not cand1):
        res["verdict"] = "F7_REPLY_OBSERVED_NOT_REPRODUCED"
    elif not cand1 and not cand2 and f7a and fc_ok:
        res["verdict"] = "F7_NO_REPLY_LINK_HEALTHY"
    else:
        res["verdict"] = "INCONCLUSIVE_SEE_PHASES"
    res["notes"] = ("A silent F7 read does NOT prove F7_WRITE_ONLY: the app's getStepLength request may "
                    "expect no explicit reply (no protocol reply on this model, asynchronous state, an "
                    "unidentified generic ack, a firmware/model gate, a timing/state requirement, or "
                    "acceptance without payload).")
    res["capture"] = {"file": str(cap) if cap else None,
                      "size_after": cap.stat().st_size if (cap and cap.exists()) else None}
    res["counts"] = {"notifications_total": len(r.notifications), "tx_total": len(r.tx),
                     "distinct_rx": sorted({n["raw"] for n in r.notifications})}
    (outdir / "analysis.json").write_text(json.dumps(res, indent=1))
    (outdir / "notifications.json").write_text(json.dumps(r.notifications, indent=1))
    (outdir / "tx.json").write_text(json.dumps(r.tx, indent=1))
    summary = {}
    for k, v in res["phases"].items():
        if not isinstance(v, dict):
            summary[k] = v
        elif "healthy" in v:
            summary[k] = {"healthy": v["healthy"], "reply": v.get("reply")}
        else:
            summary[k] = {"status": v.get("status"), "frames": v.get("frame_count")}
    print(json.dumps({"verdict": res["verdict"], "counts": res["counts"], "phases": summary}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
