#!/usr/bin/env python3
"""Real ARMOR-X Pro BLE client for the physical research pass.

Design rules (from the lab harness discipline):
  * read-only by default; every write path is an explicit, separately-named command,
  * every frame is logged raw (TX/RX + parsed) to the session directory,
  * a bounded wait that expires is reported as DEVICE_SLEEP_OR_LINK_LOSS, never as
    "the device rejected the frame",
  * nothing is fabricated: an absent reply is logged as absent.

Phases implemented here:
  scan       - list every advertisement, save them, flag ARMOR-X ones
  identity   - connect + GATT inventory + 2A24/2A26/2A19 raw reads (no writes)
  readonly   - 0B -> EF -> D4 -> E2 -> D6 with raw capture on every reply
  d2         - button-test enable / capture / disable (reversible, no config change)
  noop-d7    - gated identical-image D7 round trip (requires --baseline + hashes)

Usage:
  <venv>/bin/python armorx_real.py --transport hci-socket:1 scan --seconds 20
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent.parent
sys.path.insert(0, str(LAB / "ble" / "virtual-armorx"))
sys.path.insert(0, str(LAB / "automation" / "scripts"))

import armorx_protocol as proto  # noqa: E402
from bumble.core import AdvertisingData, UUID  # noqa: E402
from bumble.device import Device, Peer  # noqa: E402
from bumble.transport import open_transport  # noqa: E402

try:  # constants live with the virtual peripheral so both sides share one definition
    from virtual_armorx import (  # noqa: E402
        BATTERY_LEVEL_2A19, FFE1_WRITE, FFE2_NOTIFY, FIRMWARE_REV_2A26,
        MODEL_NUMBER_2A24, NAME_PREFIX, VENDOR_SERVICE,
    )
except Exception:  # pragma: no cover
    NAME_PREFIX = "ARMOR-X Pro_"
    VENDOR_SERVICE = "00000000-0000-1000-8000-00805f9b34fb"
    FFE1_WRITE = "0000ffe1-0000-1000-8000-00805f9b34fb"
    FFE2_NOTIFY = "0000ffe2-0000-1000-8000-00805f9b34fb"
    MODEL_NUMBER_2A24 = "00002a24-0000-1000-8000-00805f9b34fb"
    FIRMWARE_REV_2A26 = "00002a26-0000-1000-8000-00805f9b34fb"
    BATTERY_LEVEL_2A19 = "00002a19-0000-1000-8000-00805f9b34fb"

# Frames used by the read-only protocol initialisation (all proven live/static).
F_0B = bytes.fromhex("A5040BB4")
F_EF = bytes.fromhex("A50CEF0000000000000000A0")
F_D4 = proto.D4_REQUEST                       # A5 04 D4 7D
F_D6 = bytes.fromhex("A504D67F")
F_E2 = bytes.fromhex("A504E28B")
F_D2_ON = bytes.fromhex("A505D2017D")         # rainbow_test.dart test-mode enable
F_D2_OFF = bytes.fromhex("A505D2007C")
# read-only DPI queries, byte-exact from the 4.0.8 asm:
#   getDpi       @0x8b4e3c builds [0xA5,0x05,0xFC,0x80,cks]  -> A5 05 FC 80 26
#   getMotionDpi @0xacea28 builds [0xAB,0x05,0x05,0x25,cks]  -> AB 05 05 25 DA
F_DPI_QUERY = proto.build_frame(0xFC, bytes([0x80]))
#   getMotionDpi also builds a second 5-byte variant with sub-command 0x26 (asm @0xace94c:
#   mov x16,#0x4c) -> AB 05 05 26 DB. Same shape, so it is a query, not the AB 07 write form.
F_MOTION_DPI_QUERY = bytes([0xAB, 0x05, 0x05, 0x25,
                            (0xAB + 0x05 + 0x05 + 0x25) & 0xFF])
F_MOTION_DPI_QUERY2 = bytes([0xAB, 0x05, 0x05, 0x26,
                             (0xAB + 0x05 + 0x05 + 0x26) & 0xFF])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _u(obj) -> str:
    text = str(obj)
    if text.startswith("UUID-16:"):
        short = text.split(":", 1)[1].strip().split(" ", 1)[0].lower()
        return f"0000{short}-0000-1000-8000-00805f9b34fb"
    return text.lower()


def _adv_name(adv) -> str:
    for ad_type in (AdvertisingData.COMPLETE_LOCAL_NAME,
                    AdvertisingData.SHORTENED_LOCAL_NAME):
        value = adv.data.get(ad_type, raw=True)
        if value:
            return bytes(value).decode("utf-8", "replace")
    return ""


class Session:
    """One physical session: directory, meta, JSONL event log, raw TX/RX log."""

    def __init__(self, root: Path, session_id: str, meta: dict):
        self.dir = root
        self.dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.jsonl = open(self.dir / "session.jsonl", "a", encoding="utf-8")
        self.raw = open(self.dir / "raw-tx-rx.log", "a", encoding="utf-8")
        (self.dir / "session-meta.json").write_text(json.dumps(meta, indent=1))
        self.state("SESSION_START", meta=meta)

    def state(self, state: str, **fields):
        self._write("state", state=state, **fields)

    def event(self, event: str, **fields):
        self._write(event, **fields)

    def _write(self, event: str, **fields):
        self.jsonl.write(json.dumps({"ts": _now(), "event": event, **fields}) + "\n")
        self.jsonl.flush()

    def tx(self, raw: bytes, label: str = ""):
        self.raw.write(f"{_now()} TX {raw.hex()} {label}\n")
        self.raw.flush()
        self.event("tx", raw=raw.hex(), label=label)

    def rx(self, raw: bytes, label: str = ""):
        parsed = proto.parse_frame(raw)
        info = {
            "raw": raw.hex(), "label": label,
            "kind": parsed.kind if parsed else None,
            "opcode": f"0x{parsed.opcode:02X}" if parsed else None,
            "frag_index": parsed.frag_index if parsed else None,
            "checksum_ok": parsed.checksum_ok if parsed else None,
            "declared_length": parsed.length if parsed else None,
        }
        self.raw.write(f"{_now()} RX {raw.hex()} {label} {json.dumps(info)}\n")
        self.raw.flush()
        self.event("rx", **info)

    def close(self):
        self.state("SESSION_END")
        self.jsonl.close()
        self.raw.close()


def _repo_state() -> dict:
    import subprocess

    def g(repo: str, *args: str) -> str:
        try:
            return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                                  text=True, timeout=20).stdout.strip()
        except Exception:
            return ""

    return {
        "lab_branch": g(str(LAB), "branch", "--show-current"),
        "lab_head": g(str(LAB), "rev-parse", "HEAD"),
        "toolkit_branch": g("/home/salamanka/armorx-re/repo", "branch", "--show-current"),
        "toolkit_head": g("/home/salamanka/armorx-re/repo", "rev-parse", "HEAD"),
    }


async def _scan(device: Device, session: Session, seconds: float) -> dict:
    found: dict[str, object] = {}

    def on_advertisement(adv):
        name = _adv_name(adv)
        key = str(adv.address)
        addr_type = getattr(getattr(adv, "address", None), "address_type", None)
        services = []
        try:
            for ad_type in (AdvertisingData.COMPLETE_LIST_OF_128_BIT_SERVICE_CLASS_UUIDS,
                            AdvertisingData.INCOMPLETE_LIST_OF_128_BIT_SERVICE_CLASS_UUIDS,
                            AdvertisingData.COMPLETE_LIST_OF_16_BIT_SERVICE_CLASS_UUIDS,
                            AdvertisingData.INCOMPLETE_LIST_OF_16_BIT_SERVICE_CLASS_UUIDS):
                for value in adv.data.get(ad_type, []) or []:
                    services.append(str(value))
        except Exception:  # noqa: BLE001
            pass
        mfg = None
        try:
            mfg_value = adv.data.get(AdvertisingData.MANUFACTURER_SPECIFIC_DATA, raw=True)
            if mfg_value:
                mfg = bytes(mfg_value).hex()
        except Exception:  # noqa: BLE001
            pass
        entry = {
            "address": key,
            "address_type": str(addr_type) if addr_type is not None else None,
            "name": name,
            "rssi": getattr(adv, "rssi", None),
            "data_bytes": getattr(adv, "data_bytes", b"").hex(),
            "is_scan_response": getattr(adv, "is_scan_response", None),
            "is_connectable": getattr(adv, "is_connectable", None),
            "service_uuids": services,
            "manufacturer_data": mfg,
            "is_armorx": name.startswith(NAME_PREFIX.rstrip("_")) or "ARMOR-X" in name.upper(),
        }
        slot = found.setdefault(key, {"first": None, "last": None, "count": 0,
                                      "advertisement": None, "scan_response": None})
        slot["last"] = entry
        slot["count"] += 1
        if slot["first"] is None:
            slot["first"] = entry
        bucket = "scan_response" if entry["is_scan_response"] else "advertisement"
        if entry["name"] or not slot[bucket]:
            slot[bucket] = entry

    device.on(Device.EVENT_ADVERTISEMENT, on_advertisement)
    session.state("WAITING_FOR_DEVICE", seconds=seconds)
    await device.start_scanning()
    await asyncio.sleep(seconds)
    await device.stop_scanning()
    session.event("scan_result", devices={k: v["last"] for k, v in found.items()},
                  counts={k: v["count"] for k, v in found.items()})
    return found


async def run(args) -> int:
    repo = _repo_state()
    if args.session_dir:
        session_dir = Path(args.session_dir)
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        session_dir = LAB / "results" / "experiments" / f"physical-{stamp}"
    meta = {
        **repo,
        "start": _now(),
        "phase": args.phase,
        "transport": args.transport,
        "kernel": os.uname().release,
        "hostname": os.uname().nodename,
        "target": {"name_prefix": NAME_PREFIX, "address": args.address},
    }
    session = Session(session_dir, args.phase, meta)
    print(f"[session] {session.dir}")

    async with await open_transport(args.transport) as (hci_source, hci_sink):
        device = Device.with_hci("armorx-real-central", args.local_address, hci_source, hci_sink)
        await device.power_on()
        session.event("transport_open", transport=args.transport)

        if args.phase == "scan":
            found = await _scan(device, session, args.scan_seconds)
            armorx = {k: v for k, v in found.items() if v["last"]["is_armorx"]}
            print(f"[scan] {len(found)} devices, {len(armorx)} ARMOR-X-like")
            for k, v in found.items():
                tag = "ARMOR-X" if v["last"]["is_armorx"] else "       "
                advb = (v["advertisement"] or {}).get("data_bytes", "")
                rspb = (v["scan_response"] or {}).get("data_bytes", "")
                svc = (v["last"] or {}).get("service_uuids") or []
                print(f"  {tag} {k} type={v['last']['address_type']} "
                      f"{v['last']['name']!r} rssi={v['last']['rssi']} n={v['count']}")
                print(f"          adv={advb} rsp={rspb} services={svc} "
                      f"mfg={(v['last'] or {}).get('manufacturer_data')}")
            (session_dir / "advertisements.json").write_text(json.dumps(
                {k: v["last"] for k, v in found.items()}, indent=1))
            session.close()
            return 0 if armorx else 2

        # --- everything below needs a connection -------------------------------
        found = await _scan(device, session, args.scan_seconds)
        target = None
        if args.address:
            target = args.address.upper()
        else:
            for k, v in found.items():
                if v["last"]["is_armorx"]:
                    target = k
                    break
        if not target:
            session.state("WAITING_FOR_DEVICE", reason="no ARMOR-X advertisement seen")
            print("[scan] no ARMOR-X advertisement seen -- nothing to connect to")
            session.close()
            return 2

        session.state("CONNECTING", address=target)
        # Bounded, retried connect: Bumble's connect() has no timeout of its own and a
        # hung connect must never look like "the device rejected us".
        connection = None
        for attempt in range(1, args.connect_attempts + 1):
            try:
                connection = await asyncio.wait_for(
                    device.connect(target), timeout=args.connect_timeout)
                session.event("connected_attempt", attempt=attempt, ok=True)
                break
            except Exception as exc:  # noqa: BLE001
                session.event("connect_attempt_failed", attempt=attempt, error=repr(exc))
                print(f"[conn] attempt {attempt}/{args.connect_attempts} failed: {exc!r}")
                connection = None
                await asyncio.sleep(2)
        if connection is None:
            session.state("DEVICE_SLEEP_OR_LINK_LOSS",
                          reason=f"connect failed {args.connect_attempts}x within "
                                 f"{args.connect_timeout}s each")
            print("[conn] no connection -- DEVICE_SLEEP_OR_LINK_LOSS (advertisement seen, link not established)")
            session.close()
            return 3
        peer = Peer(connection)
        session.state("DEVICE_AWAKE", address=target)
        await peer.request_mtu(args.mtu)
        session.event("connected", peer=str(connection.peer_address), att_mtu=connection.att_mtu)

        services = await peer.discover_services()
        session.event("services", uuids=[_u(s.uuid) for s in services])
        all_chars: dict[str, object] = {}
        for service in services:
            try:
                await peer.discover_characteristics(service=service)
            except Exception as exc:  # noqa: BLE001
                session.event("discover_characteristics_failed", uuid=_u(service.uuid),
                              error=str(exc))
                continue
            for ch in service.characteristics:
                all_chars[_u(ch.uuid)] = ch
        session.event("characteristics", uuids=sorted(all_chars))
        print(f"[gatt] services={len(services)} characteristics={len(all_chars)}")

        async def read_raw(uuid_str: str, label: str):
            ch = all_chars.get(uuid_str)
            if ch is None:
                session.event("gatt_read_missing", characteristic=uuid_str, label=label)
                return None
            try:
                value = bytes(await peer.gatt_client.read_value(ch))
            except Exception as exc:  # noqa: BLE001
                session.event("gatt_read_failed", characteristic=uuid_str, error=str(exc))
                return None
            session.event("gatt_read", characteristic=uuid_str, label=label,
                          raw=value.hex(), ascii=value.decode("latin-1"),
                          length=len(value))
            print(f"[gatt] {label:10s} {uuid_str[-4:]} len={len(value)} raw={value.hex()} "
                  f"ascii={value.decode('latin-1')!r}")
            return value

        await read_raw(MODEL_NUMBER_2A24, "2A24_model")
        await read_raw(FIRMWARE_REV_2A26, "2A26_firmware")
        await read_raw(BATTERY_LEVEL_2A19, "2A19_battery")

        queue: asyncio.Queue = asyncio.Queue()

        def on_notify(value):
            queue.put_nowait(bytes(value))

        ffe2 = all_chars.get(FFE2_NOTIFY)
        ffe1 = all_chars.get(FFE1_WRITE)
        if ffe1 is None or ffe2 is None:
            session.event("channels_missing", ffe1=bool(ffe1), ffe2=bool(ffe2))
            print("[gatt] FFE1/FFE2 missing -- cannot exchange frames")
            session.close()
            return 1
        await ffe2.subscribe(on_notify)
        session.state("CAPTURING_IDENTITY")

        async def send(raw: bytes, label: str, expect: int = 1, timeout: float | None = None):
            """Send one frame and collect up to `expect` notifications."""
            session.tx(raw, label)
            print(f"[tx] {label:22s} {raw.hex()}")
            await ffe1.write_value(raw, with_response=False)
            replies = []
            t = timeout if timeout is not None else args.reply_timeout
            for _ in range(expect):
                try:
                    chunk = await asyncio.wait_for(queue.get(), t)
                except asyncio.TimeoutError:
                    session.state("DEVICE_SLEEP_OR_LINK_LOSS", waiting_for=label)
                    print(f"[rx] {label:22s} NO REPLY within {t}s (link state unproven)")
                    return replies
                replies.append(chunk)
                session.rx(chunk, label)
                print(f"[rx] {label:22s} {chunk.hex()}")
            return replies

        if args.phase == "identity":
            await send(F_0B, "0B version", expect=1)
            session.state("CAPTURING_IDENTITY_DONE")
            session.close()
            return 0

        if args.phase == "readonly":
            await send(F_0B, "0B version", expect=1)
            await send(F_EF, "EF device uuid", expect=1)
            await send(F_D4, "D4 input model", expect=1)
            if not args.no_e2:
                await send(F_E2, "E2 firmware read", expect=1, timeout=args.e2_timeout)
            frags = await send(F_D6, "D6 config read", expect=args.d6_fragments,
                               timeout=args.d6_timeout)
            parsed = [proto.parse_frame(f) for f in frags]
            image = b"".join(p.data for p in parsed if p)
            if image:
                (session_dir / "baseline-as-found.bin").write_bytes(image)
                (session_dir / "baseline-as-found.hex").write_text(image.hex(" ") + "\n")
                digest = hashlib.sha256(image).hexdigest()
                (session_dir / "baseline-as-found.sha256").write_text(digest + "\n")
                summary = {
                    "length": len(image),
                    "sha256": digest,
                    "crc_valid": proto.config_crc_valid(image),
                    "declared_length": image[2:4].hex() if len(image) >= 4 else None,
                    "stored_crc": image[0:2].hex() if len(image) >= 2 else None,
                    "fragments": [{"index": p.frag_index, "len": len(p.raw),
                                   "checksum_ok": p.checksum_ok} for p in parsed if p],
                }
                (session_dir / "baseline-as-found.json").write_text(json.dumps(summary, indent=1))
                print(f"[baseline] {len(image)} bytes sha256={digest} "
                      f"crc_valid={summary['crc_valid']} declared={summary['declared_length']}")
            session.state("CAPTURING_BASELINE_DONE", fragments=len(frags))
            session.close()
            return 0

        if args.phase == "noop-d7":
            # ---------------------------------------------------------------
            # GATED: write back the byte-identical baseline image, then read D6
            # and require byte-for-byte equality. This is the gate for every
            # later configuration mutation.
            # ---------------------------------------------------------------
            if not args.baseline:
                print("[gate] --baseline <baseline-as-found.bin> is required")
                session.close()
                return 2
            baseline = Path(args.baseline).read_bytes()
            digest = hashlib.sha256(baseline).hexdigest()
            problems = []
            if len(baseline) != 144:
                problems.append(f"length {len(baseline)} != 144")
            if not proto.config_crc_valid(baseline):
                problems.append("CRC-16/MODBUS does not verify over bytes 2..end")
            if args.expect_sha256 and digest != args.expect_sha256.lower():
                problems.append(f"sha256 {digest} != expected {args.expect_sha256.lower()}")
            if len(baseline) == 144 and int.from_bytes(baseline[2:4], "big") != 144:
                problems.append(f"declared length {baseline[2:4].hex()} != 0090")
            session.event("noop_gate_checks", sha256=digest, length=len(baseline),
                          crc_valid=proto.config_crc_valid(baseline), problems=problems)
            if problems:
                session.state("RESTORE_VALIDATION_FAILED", phase="gate", problems=problems)
                print(f"[gate] REFUSING to write: {problems}")
                session.close()
                return 3
            session.state("VALIDATING_RESTORE", baseline_sha256=digest)

            await send(F_0B, "0B version", expect=1)
            for frag in proto.build_fragment_sequence(0xD7, baseline):
                await send(frag, "D7 noop fragment", expect=0)
            # collect whatever the device sends back within the reply window
            got = []
            deadline = time.time() + args.reply_timeout
            while time.time() < deadline:
                try:
                    got.append(await asyncio.wait_for(queue.get(), max(0.1, deadline - time.time())))
                except asyncio.TimeoutError:
                    break
            for chunk in got:
                session.rx(chunk, "D7 response")
                print(f"[d7] response {chunk.hex()}")
            session.event("noop_write_responses", responses=[c.hex() for c in got])
            if not got:
                print("[d7] NO RESPONSE to the D7 write (link state unproven)")
                session.state("DEVICE_SLEEP_OR_LINK_LOSS", waiting_for="D7 ack")

            # follow-up: read the config back
            while not queue.empty():
                queue.get_nowait()
            frags = await send(F_D6, "D6 readback", expect=args.d6_fragments,
                               timeout=args.d6_timeout)
            parsed = [proto.parse_frame(f) for f in frags]
            readback = b"".join(p.data for p in parsed if p)
            (session_dir / "noop-write-readback.bin").write_bytes(readback)
            rb_digest = hashlib.sha256(readback).hexdigest()
            equal = readback == baseline
            report = {
                "baseline_sha256": digest,
                "readback_sha256": rb_digest,
                "byte_for_byte_equal": equal,
                "lengths": {"baseline": len(baseline), "readback": len(readback)},
                "crc_valid_readback": proto.config_crc_valid(readback),
                "differences": [
                    {"offset": i, "baseline": f"0x{baseline[i]:02X}", "readback": f"0x{readback[i]:02X}"}
                    for i in range(min(len(baseline), len(readback))) if baseline[i] != readback[i]
                ],
            }
            (session_dir / "noop-roundtrip.json").write_text(json.dumps(report, indent=1))
            session.event("noop_roundtrip", **report)
            session.state("RESTORED_AND_VERIFIED" if equal else "RESTORE_VALIDATION_FAILED",
                          **{k: v for k, v in report.items() if k != "differences"})
            print(f"[gate] no-op D7 round trip: equal={equal} readback_sha256={rb_digest}")
            if not equal:
                print(f"[gate] DIFFERENCES: {report['differences'][:10]}")
            session.close()
            return 0 if equal else 4

        if args.phase == "query-dpi":
            # READ-ONLY: the two query frames only; nothing is written.
            await send(F_0B, "0B version", expect=1)
            # NOTE: after any no-reply, 0B is re-sent to prove the link is still alive, so
            # "no reply" can never be silently read as "the device rejected the frame".
            print(f"[dpi] normal DPI query frame = {F_DPI_QUERY.hex()}")
            await send(F_DPI_QUERY, "FC 80 DPI query", expect=1, timeout=args.e2_timeout)
            print(f"[dpi] motion DPI query frame = {F_MOTION_DPI_QUERY.hex()}")
            await send(F_MOTION_DPI_QUERY, "AB 05 05 25 motion query", expect=1,
                       timeout=args.e2_timeout)
            print(f"[dpi] motion DPI query 2 frame = {F_MOTION_DPI_QUERY2.hex()}")
            await send(F_MOTION_DPI_QUERY2, "AB 05 05 26 motion query 2", expect=1,
                       timeout=args.e2_timeout)
            await send(F_0B, "0B link-alive check", expect=1)
            session.close()
            return 0

        if args.phase == "d2":
            await send(F_0B, "0B version", expect=1)
            await send(F_D2_ON, "D2 test ON", expect=1, timeout=args.reply_timeout)
            session.state("RUNNING_READ_ONLY_TEST", test="button_capture")
            print("[d2] test mode ON -- press buttons now")
            deadline = time.time() + args.seconds
            while time.time() < deadline:
                try:
                    chunk = await asyncio.wait_for(queue.get(), 1.0)
                except asyncio.TimeoutError:
                    continue
                session.rx(chunk, "D2 capture")
                print(f"[d2] {chunk.hex()}")
            await send(F_D2_OFF, "D2 test OFF", expect=1, timeout=args.reply_timeout)
            session.close()
            return 0

        print(f"[phase] {args.phase} not implemented in this tool yet")
        session.close()
        return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="real ARMOR-X BLE client")
    ap.add_argument("--transport", default="hci-socket:1",
                    help="Bumble transport, e.g. hci-socket:1 or usb:1-8")
    ap.add_argument("--local-address", default="F0:0A:A5:00:00:09")
    ap.add_argument("--address", default=None, help="target BLE address (skip name match)")
    ap.add_argument("--seconds", type=float, default=15.0, help="capture window (phase-specific)")
    ap.add_argument("--scan-seconds", type=float, default=12.0,
                    help="advertisement scan window (kept separate from --seconds so a long "
                         "capture window cannot turn into a long scan)")
    ap.add_argument("--mtu", type=int, default=247)
    ap.add_argument("--connect-timeout", type=float, default=20.0,
                    help="per-attempt connect timeout (Bumble itself has none)")
    ap.add_argument("--connect-attempts", type=int, default=3)
    ap.add_argument("--reply-timeout", type=float, default=3.0)
    ap.add_argument("--e2-timeout", type=float, default=5.0)
    ap.add_argument("--d6-timeout", type=float, default=3.0)
    ap.add_argument("--d6-fragments", type=int, default=10)
    ap.add_argument("--no-e2", action="store_true")
    ap.add_argument("--session-dir", default=None)
    ap.add_argument("--baseline", default=None,
                    help="baseline-as-found.bin for the gated no-op D7 round trip")
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("phase", choices=["scan", "identity", "readonly", "d2", "noop-d7",
                                      "keytest", "query-dpi"])
    # automation/radio/use-bumble.sh appends the transport spec positionally, so accept
    # it that way as well as via --transport.
    ap.add_argument("transport_pos", nargs="?", default=None,
                    help="transport spec passed positionally by use-bumble.sh")
    args = ap.parse_args()
    if args.transport_pos:
        args.transport = args.transport_pos
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
