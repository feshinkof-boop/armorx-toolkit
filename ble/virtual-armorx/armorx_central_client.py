#!/usr/bin/env python3
"""Bumble central client used to exercise the virtual ARMOR-X Pro peripheral.

It connects to the peripheral over a *virtual* HCI transport (tcp-client by
default), then drives the evidence-backed first-contact sequence and verifies
each reply against the canonical research:

    A5 04 0B B4  -> A5 05 0B <VV> <sum>
    A5 0C EF 00x8 A0  -> A5 0C EF <8 uuid bytes> <sum>
    A5 04 D6 7F  -> ten A4/D6 fragments reassembling to a 144-byte config with
                    a valid CRC-16/MODBUS
    ten A4/D7 fragments + 144 bytes -> A5 05 D7 00 81
    A5 04 E4 8D / A5 04 E2 8B -> no bytes (UNKNOWN-by-design)

Exit code 0 iff every expectation holds.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import armorx_protocol as proto  # noqa: E402

from bumble.core import AdvertisingData, UUID  # noqa: E402
from bumble.device import Device, Peer  # noqa: E402
from bumble.transport import open_transport  # noqa: E402

from virtual_armorx import (  # noqa: E402
    BATTERY_LEVEL_2A19,
    FFE1_WRITE,
    FFE2_NOTIFY,
    FIRMWARE_REV_2A26,
    MODEL_NUMBER_2A24,
    NAME_PREFIX,
    VENDOR_SERVICE,
)


class Results:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.items.append({"check": name, "ok": bool(ok), "detail": detail})
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {name}: {detail}", flush=True)

    @property
    def ok(self) -> bool:
        return all(item["ok"] for item in self.items)


async def _wait_for_notification(queue: asyncio.Queue, timeout: float):
    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


def _u(obj) -> str:
    """Canonicalise a UUID to its full lowercase 128-bit string.

    Bumble renders 16-bit GATT UUIDs as 'UUID-16:2A24'; expand those onto the
    Bluetooth base UUID so comparisons/keys are stable.
    """
    text = str(obj)
    if text.startswith("UUID-16:"):
        short = text.split(":", 1)[1].strip().split(" ", 1)[0].lower()
        return f"0000{short}-0000-1000-8000-00805f9b34fb"
    return text.lower()


def _adv_name(adv) -> str:
    for ad_type in (
        AdvertisingData.COMPLETE_LOCAL_NAME,
        AdvertisingData.SHORTENED_LOCAL_NAME,
    ):
        value = adv.data.get(ad_type, raw=True)
        if value:
            try:
                return bytes(value).decode("utf-8", "replace")
            except Exception:
                return ""
    return ""


async def run(args) -> int:
    results = Results()
    log_path = None
    if args.log_dir:
        Path(args.log_dir).mkdir(parents=True, exist_ok=True)
        log_path = Path(args.log_dir) / f"{args.session_id or 'client'}.jsonl"
    log_handle = open(log_path, "w", encoding="utf-8") if log_path else None

    def log(event: str, **fields):
        if log_handle:
            log_handle.write(
                json.dumps(
                    {
                        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                        "event": event,
                        "role": "central",
                        "app_version": args.app_version,
                        **fields,
                    }
                )
                + "\n"
            )
            log_handle.flush()

    async with await open_transport(args.transport) as (hci_source, hci_sink):
        device = Device.with_hci("armorx-central", args.address, hci_source, hci_sink)
        device.advertising_data = b""
        await device.power_on()
        log("power_on", transport=args.transport)

        # --- scan for the peripheral's advertising-name prefix -------------
        found: dict[str, object] = {}
        want = args.name_prefix

        def on_advertisement(adv):
            name = _adv_name(adv)
            if name.startswith(want) and name not in found:
                found[name] = adv
                print(f"[scan] found '{name}' at {adv.address}", flush=True)

        device.on(Device.EVENT_ADVERTISEMENT, on_advertisement)
        await device.start_scanning()

        deadline = asyncio.get_running_loop().time() + args.scan_timeout
        while not found and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.1)
        await device.stop_scanning()

        if not found:
            results.add(
                "scan_found_prefix",
                False,
                f"no advertisement whose name starts with '{want}' in {args.scan_timeout}s",
            )
            log("scan_failed", prefix=want)
            if log_handle:
                log_handle.close()
            return 1
        name, adv = next(iter(found.items()))
        results.add("scan_found_prefix", True, f"name='{name}' address={adv.address}")
        log("scan_found", name=name, address=str(adv.address))

        # --- connect + discover -------------------------------------------
        connection = await device.connect(adv.address)
        peer = Peer(connection)
        await peer.request_mtu(args.mtu)
        log("connected", peer=str(connection.peer_address), att_mtu=connection.att_mtu)
        results.add("connected", True, f"att_mtu={connection.att_mtu}")

        services = await peer.discover_services()
        service_uuids = {_u(s.uuid) for s in services}
        log("services_discovered", uuids=sorted(service_uuids))
        results.add(
            "vendor_service_present",
            UUID(VENDOR_SERVICE) in {s.uuid for s in services},
            f"services={sorted(service_uuids)}",
        )

        vendor = [s for s in services if _u(s.uuid) == VENDOR_SERVICE]
        chars = {}
        if vendor:
            await peer.discover_characteristics(service=vendor[0])
            for ch in vendor[0].characteristics:
                chars[_u(ch.uuid)] = ch
        results.add(
            "ffe1_ffe2_present",
            FFE1_WRITE in chars and FFE2_NOTIFY in chars,
            f"characteristics={sorted(chars)}",
        )

        # --- standard GATT identity reads ---------------------------------
        all_chars: dict[str, object] = {}
        for service in services:
            try:
                await peer.discover_characteristics(service=service)
            except Exception:
                continue
            for ch in service.characteristics:
                all_chars[_u(ch.uuid)] = ch

        async def read_char(uuid_str: str, label: str):
            ch = all_chars.get(uuid_str)
            if ch is None:
                results.add(label, False, f"{uuid_str} not found")
                return None
            value = await peer.gatt_client.read_value(ch)
            log("gatt_read", characteristic=uuid_str, value=bytes(value).hex())
            results.add(label, bool(value), f"{uuid_str} = {bytes(value)!r}")
            return bytes(value)

        await read_char(MODEL_NUMBER_2A24, "read_2A24_model")
        await read_char(FIRMWARE_REV_2A26, "read_2A26_firmware")
        await read_char(BATTERY_LEVEL_2A19, "read_2A19_battery")

        # --- subscribe to FFE2 and exchange frames ------------------------
        ffe2 = all_chars.get(FFE2_NOTIFY)
        ffe1 = all_chars.get(FFE1_WRITE)
        if ffe1 is None or ffe2 is None:
            results.add("ffe1_ffe2_channels", False, "write/notify channels missing")
            if log_handle:
                log_handle.close()
            return 1

        queue: asyncio.Queue = asyncio.Queue()

        def on_notification(value):
            queue.put_nowait(bytes(value))

        await ffe2.subscribe(on_notification)
        results.add("subscribe_ffe2", True, "notifications enabled")
        log("subscribe", characteristic="0000ffe2")

        async def send(raw: bytes, with_response=False, label=""):
            log("frame_out", raw=raw.hex(), label=label)
            await ffe1.write_value(raw, with_response=with_response)

        # 1) version request  A5 04 0B B4
        await send(bytes.fromhex("A5040BB4"), label="0B request")
        reply = await _wait_for_notification(queue, args.reply_timeout)
        ok = reply == bytes.fromhex(f"A5050B{args.expect_zkm:02X}"
                                    + f"{(0xA5 + 0x05 + 0x0B + args.expect_zkm) & 0xFF:02X}")
        results.add("reply_0B_version", ok, f"got {reply.hex() if reply else None}")
        log("reply", raw=reply.hex() if reply else None, label="0B")

        # 2) device uuid request  A5 0C EF 00*8 A0
        await send(bytes.fromhex("A50CEF0000000000000000A0"), label="EF request")
        reply = await _wait_for_notification(queue, args.reply_timeout)
        uuid_bytes = bytes.fromhex(args.expect_device_uuid)
        expected = proto.build_frame(0xEF, uuid_bytes)
        results.add(
            "reply_EF_device_uuid",
            reply == expected,
            f"got {reply.hex() if reply else None}, expected {expected.hex()}",
        )
        log("reply", raw=reply.hex() if reply else None, label="EF")

        # 3) config read  A5 04 D6 7F -> ten A4/D6 fragments
        await send(bytes.fromhex("A504D67F"), label="D6 request")
        frags = []
        while True:
            chunk = await _wait_for_notification(queue, args.reply_timeout)
            if chunk is None:
                break
            frags.append(chunk)
            if len(frags) >= 10:
                break
        parsed = [proto.parse_frame(f) for f in frags]
        reassembled = b"".join(p.data for p in parsed if p)
        results.add(
            "reply_D6_config_read",
            len(frags) == 10
            and len(reassembled) == 144
            and proto.config_crc_valid(reassembled)
            and [p.frag_index for p in parsed] == list(range(1, 11)),
            f"fragments={len(frags)} bytes={len(reassembled)} crc_valid="
            f"{proto.config_crc_valid(reassembled)}",
        )
        log(
            "reply",
            label="D6",
            fragments=len(frags),
            bytes=len(reassembled),
            crc_valid=proto.config_crc_valid(reassembled),
        )

        # 4) config write  ten A4/D7 fragments -> A5 05 D7 00 81
        image = reassembled if len(reassembled) == 144 else proto.load_default_config_144()
        for frag in proto.build_fragment_sequence(0xD7, image):
            await send(frag, label="D7 fragment")
        reply = await _wait_for_notification(queue, args.reply_timeout)
        results.add(
            "reply_D7_config_write_ack",
            reply == bytes.fromhex("A505D70081"),
            f"got {reply.hex() if reply else None}",
        )
        log("reply", raw=reply.hex() if reply else None, label="D7")

        # 5) UNKNOWN-by-design: MTU query and firmware read must produce no bytes
        for label, frame in (
            ("E4_MTU", "A504E48D"),
            ("E2_readFirmware", "A504E28B"),
        ):
            while not queue.empty():
                queue.get_nowait()
            await send(bytes.fromhex(frame), label=f"{label} request")
            reply = await _wait_for_notification(queue, args.unknown_timeout)
            results.add(
                f"unknown_{label}_no_bytes",
                reply is None,
                f"got {reply.hex() if reply else None} (expected none)",
            )
            log("unknown_command", raw=frame, reply=reply.hex() if reply else None)

        await ffe2.unsubscribe(on_notification)
        await connection.disconnect()

    if log_handle:
        log_handle.close()
    print("", flush=True)
    print(f"=== client summary: {sum(i['ok'] for i in results.items)}/"
          f"{len(results.items)} checks passed ===", flush=True)
    return 0 if results.ok else 1


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--transport", default="tcp-client:127.0.0.1:9510")
    p.add_argument("--address", default="F0:0A:CF:00:00:01", help="central BD address")
    p.add_argument("--name-prefix", default=NAME_PREFIX)
    p.add_argument("--mtu", type=int, default=247)
    p.add_argument("--scan-timeout", type=float, default=10.0)
    p.add_argument("--reply-timeout", type=float, default=3.0)
    p.add_argument("--unknown-timeout", type=float, default=1.0)
    p.add_argument("--expect-zkm", type=lambda v: int(v, 0), default=0x30)
    p.add_argument("--expect-device-uuid", default="0001020304050607")
    p.add_argument("--app-version", default="4.0.8")
    p.add_argument("--log-dir", default=None)
    p.add_argument("--session-id", default=None)
    return p.parse_args(argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(run(parse_args())))
