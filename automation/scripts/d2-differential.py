#!/usr/bin/env python3
"""d2-differential.py -- live D2 / Button Test differential experiment.

Compares four cleanly separated cases against the real unit and records, per case,
- the ATT operation actually used (Write Request vs Write Command, from the mode we request),
- CCCD/notification activity,
- every notification classified against the reconstructed button-test RX contract.

The RX contract (statically reconstructed, build 4.0.8):
    18 bytes, header 0xA5, length byte 0x12, opcode 0x02, key mask = big-endian u32 at [3..6]
A 5-byte D2 echo (A5 05 D2 ..) never counts as a button-test frame.

Runtime mode only: D2 enable/disable and notification operations. No configuration,
DPI, lighting, macro, RCSP/OTA or firmware command is ever sent.

Usage:
  d2-differential.py scan         --outdir DIR
  d2-differential.py preflight    --outdir DIR
  d2-differential.py variant      --outdir DIR --case C0|A|B|C
"""
from __future__ import annotations

import argparse, asyncio, json, os, pathlib, sys, time
from datetime import datetime, timezone

try:
    from bleak import BleakClient, BleakScanner
except Exception as exc:                                          # pragma: no cover
    print(f"FATAL: bleak unavailable: {exc}")
    sys.exit(3)

NAME_PREFIX = "ARMOR-X Pro"
FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"   # control write
FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"   # notify
ID_CHARS = {
    "2a24": "00002a24-0000-1000-8000-00805f9b34fb",   # model number string
    "2a26": "00002a26-0000-1000-8000-00805f9b34fb",   # firmware revision string
    "2a19": "00002a19-0000-1000-8000-00805f9b34fb",   # battery level
}

D2_ON = bytes.fromhex("A505D2017D")
D2_OFF = bytes.fromhex("A505D2007C")
Q_0B = bytes.fromhex("A5040BB4")
R_0B = bytes.fromhex("A5050B30E5")

OBSERVE_S = 20.0

def observe_window() -> float:
    """Observation window in seconds.

    Overridable via the D2_OBSERVE_S environment variable (Phase 10 of the session-differential
    brief uses 10 s where the differential matrix used 20 s). An env var is used rather than a CLI
    flag because the value must survive into the asyncio worker regardless of subparser routing.
    """
    env = os.environ.get("D2_OBSERVE_S")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return _OBSERVE_OVERRIDE if _OBSERVE_OVERRIDE else OBSERVE_S


_OBSERVE_OVERRIDE: float | None = None
BRIEF_S = 7.0


def iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify(frame: bytes) -> str:
    """Classify a notification against the reconstructed RX contract."""
    if len(frame) == 5 and frame[:3] == b"\xa5\x05\xd2":
        return "d2_echo"
    if len(frame) < 4:
        return "malformed_short"
    if len(frame) != 18:
        return f"wrong_length_{len(frame)}"
    if frame[0] != 0xA5:
        return "bad_header"
    if frame[2] != 0x02:
        return f"opcode_0x{frame[2]:02X}_not_0x02"
    body = frame[:17]
    if sum(body) & 0xFF != frame[17]:
        return "checksum_mismatch"
    return "valid_status"


def mask_of(frame: bytes) -> int:
    return int.from_bytes(frame[3:7], "big")


def key_ids(mask: int) -> list[int]:
    return [i for i in range(32) if mask & (1 << i)]


class Recorder:
    def __init__(self, outdir: pathlib.Path, case: str):
        self.dir = outdir / case
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jsonl = outdir / "tx-rx.jsonl"
        self.csv = outdir / "timeline.csv"
        self.t0 = time.monotonic()
        self.frames: list[dict] = []
        if not self.csv.exists():
            self.csv.write_text("case,monotonic_s,event,detail\n")

    def mark(self, event: str, detail: str = "") -> float:
        t = round(time.monotonic() - self.t0, 3)
        with self.csv.open("a") as fh:
            fh.write(f"{self.dir.name},{t},{event},\"{detail}\"\n")
        return t

    def log(self, direction: str, uuid: str, payload: bytes, **extra) -> None:
        rec = {"case": self.dir.name, "ts_utc": iso(),
               "monotonic_s": self.mark(f"{direction}:{extra.get('label','')}", payload.hex()),
               "dir": direction, "uuid": uuid, "hex": payload.hex(), **extra}
        with self.jsonl.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def on_notify(self, _char, data: bytearray) -> None:
        raw = bytes(data)
        kind = classify(raw)
        self.frames.append({"t": round(time.monotonic() - self.t0, 3), "hex": raw.hex(),
                            "kind": kind,
                            "mask": f"0x{mask_of(raw):08X}" if kind == "valid_status" else None,
                            "keys": key_ids(mask_of(raw)) if kind == "valid_status" else None})
        self.log("RX", FFE2, raw, label="notify", kind=kind)

    def summary(self) -> dict:
        kinds: dict[str, int] = {}
        for f in self.frames:
            kinds[f["kind"]] = kinds.get(f["kind"], 0) + 1
        return {"total_notifications": len(self.frames), "by_kind": kinds,
                "valid_status_frames": kinds.get("valid_status", 0),
                "frames": self.frames}


# Known-good identity of the unit (from the repo's live captures). The address is static for this
# device; the scan still prefers a name match so a different unit could never be mistaken for it.
KNOWN_ADDRESSES = {a.upper() for a in ("2D:37:35:6D:66:11",)}


async def find_device(timeout: float = 20.0):
    """Find the unit by advertised name, else by its known address.

    The unit does not always put its local name in the advertisement (a scan response may carry
    it), so matching the name alone produces false NOT_FOUND results - observed live: BlueZ listed
    the device at RSSI -84 while a name-only matcher reported nothing.
    """
    devs = await BleakScanner.discover(timeout=timeout, return_adv=True)
    by_addr = None
    for address, (dev, adv) in devs.items():
        name = dev.name or adv.local_name or ""
        if name.startswith(NAME_PREFIX):
            return dev, adv
        if address.upper() in KNOWN_ADDRESSES:
            by_addr = (dev, adv)
    return by_addr if by_addr else (None, None)


async def cmd_scan(args) -> int:
    dev, adv = await find_device()
    out = args.outdir / "device-discovery.txt"
    args.outdir.mkdir(parents=True, exist_ok=True)
    if not dev:
        out.write_text(f"{iso()} scan: device with prefix {NAME_PREFIX!r} NOT FOUND\n")
        print("SCAN_RESULT: NOT_FOUND")
        return 4
    lines = [f"{iso()} scan result",
             f"address={dev.address}", f"name={dev.name}", f"rssi={adv.rssi}",
             f"local_name={adv.local_name}",
             f"manufacturer_data={ {k: v.hex() for k, v in adv.manufacturer_data.items()} }",
             f"service_uuids={adv.service_uuids}",
             f"tx_power={adv.tx_power}"]
    out.write_text("\n".join(lines) + "\n")
    print("SCAN_RESULT: FOUND", dev.address, dev.name)
    print("\n".join(lines))
    return 0


async def connect_and_prepare(rec: Recorder, verbose=True):
    dev, adv = await find_device()
    if not dev:
        raise RuntimeError("device not found")
    rec.mark("discovered", dev.address)
    client = BleakClient(dev, timeout=25.0)
    await client.connect()
    rec.mark("connected", str(client.is_connected))
    services = client.services
    disc = []
    for s in services:
        entry = {"service": s.uuid, "description": s.description, "characteristics": []}
        for c in s.characteristics:
            entry["characteristics"].append({"uuid": c.uuid, "properties": list(c.properties),
                                             "handle": getattr(c, "handle", None)})
        disc.append(entry)
    (rec.dir / "services.json").write_text(json.dumps(disc, indent=1) + "\n")
    identity = {}
    for key, uuid in ID_CHARS.items():
        try:
            val = await client.read_gatt_char(uuid)
            identity[key] = val.hex()
        except Exception as exc:
            identity[key] = f"ERROR:{type(exc).__name__}"
    (rec.dir / "identity.json").write_text(json.dumps(identity, indent=1) + "\n")
    if verbose:
        print("identity:", identity)
    await client.start_notify(FFE2, rec.on_notify)
    rec.mark("notify_started", FFE2)
    return client, identity, disc


async def sanity(client, rec: Recorder) -> bool:
    """Proven read-only 0B control-channel check."""
    await client.write_gatt_char(FFE1, Q_0B, response=False)
    rec.log("TX", FFE1, Q_0B, label="0B sanity", write_mode="without_response")
    await asyncio.sleep(2.0)
    ok = any(bytes.fromhex(f["hex"]) == R_0B for f in rec.frames)
    rec.mark("sanity", "ok" if ok else "FAILED")
    return ok


async def d2_off(client, rec: Recorder) -> None:
    try:
        await client.write_gatt_char(FFE1, D2_OFF, response=False)
        rec.log("TX", FFE1, D2_OFF, label="D2 disable (pre)", write_mode="without_response")
        await asyncio.sleep(1.5)
    except Exception as exc:
        rec.mark("d2_off_error", str(exc))


async def run_case(args) -> int:
    case = args.case
    rec = Recorder(args.outdir, case)
    try:
        client, identity, disc = await connect_and_prepare(rec)
    except Exception as exc:
        print(f"CONNECT_FAILED: {exc}")
        return 5

    try:
        if not await sanity(client, rec):
            print("PREFLIGHT_CONTROL_CHANNEL_FAILED")
            return 6
        await d2_off(client, rec)

        if case == "C0":                                  # current harness behaviour
            await client.write_gatt_char(FFE1, D2_ON, response=False)
            rec.log("TX", FFE1, D2_ON, label="D2 enable", write_mode="without_response")
            rec.mark("observe_start", f"{observe_window()}s")
            await asyncio.sleep(observe_window())
        elif case == "A":                                 # write WITH response
            await client.write_gatt_char(FFE1, D2_ON, response=True)
            rec.log("TX", FFE1, D2_ON, label="D2 enable", write_mode="with_response")
            rec.mark("observe_start", f"{observe_window()}s")
            await asyncio.sleep(observe_window())
        elif case == "B":                                 # explicit CCCD renewal after enable
            await client.write_gatt_char(FFE1, D2_ON, response=False)
            rec.log("TX", FFE1, D2_ON, label="D2 enable", write_mode="without_response")
            rec.mark("cccd_renew_start")
            try:
                await client.stop_notify(FFE2)
                rec.mark("cccd_unsubscribe_done")
                await asyncio.sleep(1.0)
                await client.start_notify(FFE2, rec.on_notify)
                rec.mark("cccd_resubscribe_done")
            except Exception as exc:
                rec.mark("cccd_renew_error", str(exc))
            await asyncio.sleep(observe_window())
        elif case == "C":                                 # same-connection re-enable
            await client.write_gatt_char(FFE1, D2_ON, response=False)
            rec.log("TX", FFE1, D2_ON, label="D2 enable (1st)", write_mode="without_response")
            await asyncio.sleep(BRIEF_S)
            await client.write_gatt_char(FFE1, D2_OFF, response=False)
            rec.log("TX", FFE1, D2_OFF, label="D2 disable (between)", write_mode="without_response")
            await asyncio.sleep(1.0)
            await client.write_gatt_char(FFE1, D2_ON, response=False)
            rec.log("TX", FFE1, D2_ON, label="D2 enable (re-enable)", write_mode="without_response")
            rec.mark("observe_start", f"{observe_window()}s (after re-enable)")
            await asyncio.sleep(observe_window())
        else:
            print(f"unknown case {case}")
            return 2

        # always attempt D2 disable before disconnect
        try:
            await client.write_gatt_char(FFE1, D2_OFF, response=False)
            rec.log("TX", FFE1, D2_OFF, label="D2 disable (post)", write_mode="without_response")
            await asyncio.sleep(1.0)
        except Exception as exc:
            rec.mark("d2_off_post_error", str(exc))
    finally:
        try:
            await client.stop_notify(FFE2)
        except Exception:
            pass
        try:
            await client.disconnect()
            rec.mark("disconnected")
        except Exception:
            pass

    summary = rec.summary()
    summary["case"] = case
    summary["identity"] = identity
    (rec.dir / "result.json").write_text(json.dumps(summary, indent=1) + "\n")
    valid = summary["valid_status_frames"]
    print(f"CASE {case}: valid_status={valid} total_notifications={summary['total_notifications']} kinds={summary['by_kind']}")
    return 0


async def cmd_preflight(args) -> int:
    rec = Recorder(args.outdir, "preflight")
    client, identity, disc = await connect_and_prepare(rec)
    ok = await sanity(client, rec)
    (rec.dir / "preflight.json").write_text(json.dumps(
        {"identity": identity, "control_channel_ok": ok, "services": disc}, indent=1) + "\n")
    try:
        await client.disconnect()
    except Exception:
        pass
    print("PREFLIGHT:", "OK" if ok else "CONTROL_CHANNEL_FAILED")
    return 0 if ok else 6


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "preflight", "variant"):
        p = sub.add_parser(name)
        p.add_argument("--outdir", required=True, type=pathlib.Path)
        if name == "variant":
            p.add_argument("--case", required=True, choices=["C0", "A", "B", "C"])
    args = ap.parse_args()
    global _OBSERVE_OVERRIDE
    if getattr(args, "observe", None):
        _OBSERVE_OVERRIDE = args.observe
    if args.cmd == "scan":
        return asyncio.run(cmd_scan(args))
    if args.cmd == "preflight":
        return asyncio.run(cmd_preflight(args))
    return asyncio.run(run_case(args))


if __name__ == "__main__":
    sys.exit(main())
