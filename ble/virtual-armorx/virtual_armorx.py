#!/usr/bin/env python3
"""Virtual ARMOR-X Pro BLE peripheral (MYGT 4.0.8).

A software-only Bumble peripheral that reproduces the ARMOR-X Pro GATT surface
and the *evidence-backed* subset of the A5/A4 command protocol recovered from the
canonical 4.0.8 research. Commands whose device reply the research marks UNKNOWN
are logged as UNKNOWN and produce NO bytes.

Transport (no physical radio is touched):
    The peripheral is a complete virtual device built from two Bumble
    ``Controller`` instances on one in-process ``LocalLink``:

      * C_PERIPH  -- the peripheral's own radio, wired to the peripheral Host
                     through a local UNIX-socket HCI pipe;
      * C_PEER    -- a peer radio on the same link, whose HCI faces a TCP
                     server so a *second* Bumble process can attach as central.

    No hci0 / hci-socket / vhci / usb transport is used: the host's physical
    Bluetooth adapter is never opened, unbound or rfkill-ed.

Evidence: every reply frame is cited in armorx_protocol.py and in the status
report at results/final/virtual-armorx-status.md.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import armorx_protocol as proto  # noqa: E402

from bumble.controller import Controller  # noqa: E402
from bumble.core import AdvertisingData  # noqa: E402
from bumble.device import Device  # noqa: E402
from bumble.gatt import Characteristic, Service  # noqa: E402
from bumble.link import LocalLink  # noqa: E402
from bumble.transport import open_transport  # noqa: E402

# ---------------------------------------------------------------------------
# UUIDs -- ble-architecture.md "UUIDs (all present in 4.0.8)"
# ---------------------------------------------------------------------------

VENDOR_SERVICE = "00000000-0000-1000-8000-00805f9b34fb"
FFE1_WRITE = "0000ffe1-0000-1000-8000-00805f9b34fb"
FFE2_NOTIFY = "0000ffe2-0000-1000-8000-00805f9b34fb"
DEVICE_INFO_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"
MODEL_NUMBER_2A24 = "00002a24-0000-1000-8000-00805f9b34fb"
FIRMWARE_REV_2A26 = "00002a26-0000-1000-8000-00805f9b34fb"
BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_2A19 = "00002a19-0000-1000-8000-00805f9b34fb"

# Advertising-name prefix the apps scan for -- ble-architecture.md line 106
NAME_PREFIX = "ARMOR-X Pro_"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class SessionLogs:
    """Per-session raw capture (.bin + .hex) and structured JSONL."""

    def __init__(self, log_dir: Path, session_id: str, app_version: str, meta: dict):
        log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.app_version = app_version
        self.bin_path = log_dir / f"{session_id}.bin"
        self.hex_path = log_dir / f"{session_id}.hex"
        self.jsonl_path = log_dir / f"{session_id}.jsonl"
        self.meta = meta
        self._bin = open(self.bin_path, "wb")
        self._hex = open(self.hex_path, "w", encoding="utf-8")
        self._jsonl = open(self.jsonl_path, "w", encoding="utf-8")
        self._hex.write(f"# raw capture {self.session_id}  app_version={app_version}\n")
        self._hex.write(
            "# record = <dir><u16 len><payload>; dir '<' host->peripheral, '>' peripheral->host\n"
        )
        self.jsonl(
            "session_start",
            session_id=session_id,
            app_version=app_version,
            **meta,
        )

    def _raw(self, direction: str, payload: bytes) -> None:
        rec = direction.encode("ascii") + len(payload).to_bytes(2, "big") + payload
        self._bin.write(rec)
        self._bin.flush()
        # human-readable hex dump of the same record
        stamp = _now_iso()
        for off in range(0, len(payload), 16):
            chunk = payload[off : off + 16]
            hexpart = " ".join(f"{b:02X}" for b in chunk)
            self._hex.write(f"{stamp} {direction} {off:04X}  {hexpart}\n")
        self._hex.flush()

    def jsonl(self, event: str, **fields) -> None:
        entry = {"ts": _now_iso(), "session": self.session_id, "event": event}
        entry["app_version"] = self.app_version
        entry.update(fields)
        self._jsonl.write(json.dumps(entry, default=str) + "\n")
        self._jsonl.flush()

    def inbound(self, payload: bytes) -> None:
        self._raw("<", payload)

    def outbound(self, payload: bytes) -> None:
        self._raw(">", payload)

    def close(self) -> None:
        self.jsonl("session_end")
        for handle in (self._bin, self._hex, self._jsonl):
            try:
                handle.close()
            except Exception:
                pass


class ArmorXPeripheral:
    """Evidence-backed ARMOR-X Pro command handling."""

    def __init__(self, args, logs: SessionLogs):
        self.args = args
        self.logs = logs
        self.device_uuid = bytes.fromhex(args.device_uuid)
        if len(self.device_uuid) != 8:
            raise ValueError("--device-uuid must be exactly 8 bytes (16 hex chars)")
        self.zkm_version = args.zkm_version & 0xFF
        self.config = (
            Path(args.config_file).read_bytes()
            if args.config_file
            else proto.load_default_config_144()
        )
        if len(self.config) != 144:
            raise ValueError(f"config image must be 144 bytes, got {len(self.config)}")
        # pending A4 reassembly buffers, keyed by opcode
        self._frags: dict[int, dict[int, bytes]] = {}
        self.ffe2: Characteristic | None = None
        self.unknown_logged: dict[int, int] = {}

    # -- GATT ---------------------------------------------------------------

    def build_services(self) -> list[Service]:
        ffe1 = Characteristic(
            FFE1_WRITE,
            Characteristic.Properties.WRITE
            | Characteristic.Properties.WRITE_WITHOUT_RESPONSE,
            Characteristic.Permissions.WRITEABLE,
            bytes(0),
        )
        self.ffe2 = Characteristic(
            FFE2_NOTIFY,
            Characteristic.Properties.READ | Characteristic.Properties.NOTIFY,
            Characteristic.Permissions.READABLE,
            bytes(0),
        )
        ffe1.on("write", self._on_ffe1_write)
        self.ffe2.on("read", self._on_char_read)
        vendor = Service(VENDOR_SERVICE, [ffe1, self.ffe2])

        model = Characteristic(
            MODEL_NUMBER_2A24,
            Characteristic.Properties.READ,
            Characteristic.Permissions.READABLE,
            self.args.model_number.encode("utf-8"),
        )
        firmware = Characteristic(
            FIRMWARE_REV_2A26,
            Characteristic.Properties.READ,
            Characteristic.Permissions.READABLE,
            self.args.firmware_revision.encode("utf-8"),
        )
        battery = Characteristic(
            BATTERY_LEVEL_2A19,
            Characteristic.Properties.READ | Characteristic.Properties.NOTIFY,
            Characteristic.Permissions.READABLE,
            bytes([self.args.battery_level & 0xFF]),
        )
        for ch in (model, firmware, battery):
            ch.on("read", self._on_char_read)

        device_info = Service(DEVICE_INFO_SERVICE, [model, firmware])
        battery_service = Service(BATTERY_SERVICE, [battery])
        return [vendor, device_info, battery_service]

    def _on_char_read(self, connection, value: bytes) -> None:
        self.logs.jsonl(
            "gatt_read",
            peer=str(getattr(connection, "peer_address", "")),
            value=value.hex(),
        )

    # -- inbound frame handling --------------------------------------------

    def _on_ffe1_write(self, connection, value: bytes) -> None:
        """Every FFE1 write carries exactly one A5/A4 frame."""
        value = bytes(value)
        self.logs.inbound(value)
        frame = proto.parse_frame(value)
        if frame is None:
            self.logs.jsonl(
                "frame_in",
                raw=value.hex(),
                parsed_opcode=None,
                checksum_ok=False,
                note="too short to parse",
            )
            return
        self.logs.jsonl(
            "frame_in",
            raw=value.hex(),
            kind=frame.kind,
            length=frame.length,
            parsed_opcode=f"0x{frame.opcode:02X}",
            opcode_name=frame.opcode_name,
            fragment_index=frame.frag_index,
            checksum_ok=frame.checksum_ok,
            computed_checksum=f"0x{frame.computed_checksum:02X}",
            stored_checksum=f"0x{frame.stored_checksum:02X}",
            notes=frame.notes,
        )
        if not frame.checksum_ok:
            self.logs.jsonl(
                "frame_error",
                raw=value.hex(),
                reason="checksum mismatch or length mismatch",
            )
            return
        asyncio.get_running_loop().create_task(self._dispatch(connection, frame))

    async def _dispatch(self, connection, frame) -> None:
        if frame.kind == "short":
            await self._dispatch_short(connection, frame)
        elif frame.kind == "fragment":
            await self._dispatch_fragment(connection, frame)
        else:
            await self._unknown(connection, frame, "unparsed header")

    async def _dispatch_short(self, connection, frame) -> None:
        op = frame.opcode
        if op == 0x0B:
            reply = proto.build_frame(0x0B, bytes([self.zkm_version]))
            await self._send(connection, reply, "version", "0B version reply A5 05 0B VV CC")
        elif op == 0xEF:
            reply = proto.build_frame(0xEF, self.device_uuid)
            await self._send(
                connection,
                reply,
                "device_uuid",
                "EF uuid reply A5 0C EF <8 uuid> <sum>",
            )
        elif op == 0xD6:
            frames = proto.build_fragment_sequence(0xD6, self.config)
            for frag in frames:
                frag_index = proto.parse_frame(frag).frag_index
                await self._send(
                    connection,
                    frag,
                    "config_read",
                    f"A4/D6 config fragment {frag_index}/{len(frames)}",
                )
        elif op == 0x0E:
            await self._send(connection, frame.raw, "echo", "0E echoed verbatim")
        else:
            await self._unknown(connection, frame, "no evidence-backed short reply")

    async def _dispatch_fragment(self, connection, frame) -> None:
        op = frame.opcode
        # D8 terminator: A4 0A D8 <nfrags+1> <sum8>  (d8-macro.md §3.3)
        if op == 0xD8 and frame.length == 0x0A and len(frame.raw) == 5:
            pending = self._frags.get(0xD8, {})
            self.logs.jsonl(
                "macro_terminator",
                expected_total_frames=frame.payload[0] if frame.payload else None,
                received_frames=len(pending),
                note="D8 macro write accepted; device reply UNKNOWN - no bytes sent",
            )
            self._frags.pop(0xD8, None)
            return

        if op in (0xD6, 0xD7, 0xD8):
            if frame.frag_index is None:
                await self._unknown(connection, frame, "fragment without index byte")
                return
            buf = self._frags.setdefault(op, {})
            buf[frame.frag_index] = frame.data
            # D7 = full 144-byte config write: 10 fragments (docs/android-protocol.md)
            if op == 0xD7 and len(buf) >= 10:
                image = b"".join(buf[i] for i in sorted(buf))
                if len(image) == 144:
                    valid = proto.config_crc_valid(image)
                    self.config = image if not self.args.ignore_config_crc else image
                    self.logs.jsonl(
                        "config_write",
                        bytes=len(image),
                        crc_valid=valid,
                        stored_crc=image[:2].hex(),
                        computed_crc=bytes(proto.config_crc_bytes(image)).hex(),
                    )
                    ack = proto.build_frame(0xD7, bytes([0x00]))
                    await self._send(
                        connection, ack, "config_write_ack", "A5 05 D7 00 81"
                    )
                self._frags.pop(op, None)
            return

        if op == 0xD6:
            return
        await self._unknown(connection, frame, "no evidence-backed fragment reply")

    async def _unknown(self, connection, frame, reason: str) -> None:
        spec = proto.reply_status(frame.opcode)
        self.unknown_logged[frame.opcode] = self.unknown_logged.get(frame.opcode, 0) + 1
        self.logs.jsonl(
            "command_unknown",
            raw=frame.raw.hex(),
            parsed_opcode=f"0x{frame.opcode:02X}",
            opcode_name=frame.opcode_name,
            reason=reason,
            research_status=spec.status,
            research_note=spec.description,
            research_evidence=spec.evidence,
            reply_bytes_sent=0,
        )

    async def _send(self, connection, payload: bytes, tag: str, note: str) -> None:
        self.logs.outbound(payload)
        parsed = proto.parse_frame(payload)
        self.logs.jsonl(
            "reply_out",
            tag=tag,
            raw=payload.hex(),
            parsed_opcode=f"0x{parsed.opcode:02X}" if parsed else None,
            checksum_ok=parsed.checksum_ok if parsed else None,
            note=note,
        )
        await self.device.gatt_server.notify_subscribers(self.ffe2, payload)

    # -- device events ------------------------------------------------------

    def wire_events(self) -> None:
        self.device.on(Device.EVENT_CONNECTION, self._on_connection)

    def _on_connection(self, connection) -> None:
        self.logs.jsonl(
            "connect",
            peer=str(connection.peer_address),
            handle=connection.handle,
            role=connection.role_name,
        )
        connection.on(
            connection.EVENT_CONNECTION_ATT_MTU_UPDATE,
            lambda: self.logs.jsonl(
                "mtu",
                peer=str(connection.peer_address),
                att_mtu=connection.att_mtu,
            ),
        )
        connection.on(connection.EVENT_DISCONNECTION, self._on_disconnection)
        for attr_name in ("ffe2", "ffe1"):
            attr = getattr(self, attr_name, None)
            if attr is not None:
                attr.on(
                    "subscription",
                    lambda conn, enabled, _n=attr_name: self.logs.jsonl(
                        "subscription", characteristic=_n, enabled=bool(enabled)
                    ),
                )

    def _on_disconnection(self, *args) -> None:
        connection = args[0] if args else None
        self.logs.jsonl(
            "disconnect",
            peer=str(getattr(connection, "peer_address", "")),
            handle=getattr(connection, "handle", None),
            reason=str(args[-1]) if len(args) > 1 else None,
        )

    # -- lifecycle ----------------------------------------------------------

    async def run(self) -> None:
        c_periph = c_peer = None
        if self.args.mode == "direct":
            # Attach the peripheral Host straight onto an externally-provided
            # controller HCI link (e.g. the emulator's netsim RootCanal chip).
            # No local Controllers / LocalLink: the transport *is* the HCI link
            # to a real controller, exactly like Device.with_hci over TCP.
            peer_transport = await open_transport(self.args.transport)
            self.device = Device.with_hci(
                f"{NAME_PREFIX}{self.args.name_suffix}",
                self.args.address,
                peer_transport.source,
                peer_transport.sink,
            )
        else:
            link = LocalLink()
            sock = self.args.local_transport
            try:
                os.unlink(sock)
            except FileNotFoundError:
                pass

            local_server = await open_transport(f"unix-server:{sock}")
            local_client = await open_transport(f"unix-client:{sock}")
            c_periph = Controller(
                "C_PERIPH",
                host_source=local_server.source,
                host_sink=local_server.sink,
                link=link,
                public_address=self.args.address,
            )
            peer_transport = await open_transport(self.args.transport)
            c_peer = Controller(
                "C_PEER",
                host_source=peer_transport.source,
                host_sink=peer_transport.sink,
                link=link,
                public_address=self.args.peer_address,
            )

            self.device = Device.with_hci(
                f"{NAME_PREFIX}{self.args.name_suffix}",
                self.args.address,
                local_client.source,
                local_client.sink,
            )
        for service in self.build_services():
            self.device.add_service(service)
        self.wire_events()

        await self.device.power_on()

        ad = AdvertisingData(
            [
                (AdvertisingData.FLAGS, bytes([0x06])),
                (AdvertisingData.COMPLETE_LOCAL_NAME, f"{NAME_PREFIX}{self.args.name_suffix}".encode()),
            ]
        )
        # The 128-bit vendor service UUID does not fit in the 31-byte legacy
        # advertising payload alongside the name, so it goes in the scan
        # response (a real controller rejects an over-long AD with
        # HCI_Error(INVALID_COMMAND_PARAMETERS)).
        sd = AdvertisingData(
            [
                (
                    AdvertisingData.INCOMPLETE_LIST_OF_128_BIT_SERVICE_CLASS_UUIDS,
                    bytes(reversed(bytes.fromhex(VENDOR_SERVICE.replace("-", "")))),
                ),
            ]
        )
        await self.device.start_advertising(
            advertising_data=bytes(ad), scan_response_data=bytes(sd), auto_restart=True
        )
        self.logs.jsonl(
            "advertising_started",
            name=f"{NAME_PREFIX}{self.args.name_suffix}",
            address=self.args.address,
            transport=self.args.transport,
            c_periph=str(c_periph),
            c_peer=str(c_peer),
        )
        print(
            f"[virtual-armorx] advertising as '{NAME_PREFIX}{self.args.name_suffix}' "
            f"({self.args.address}) | peer HCI on {self.args.transport} | "
            f"session {self.logs.session_id}",
            flush=True,
        )

        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:  # pragma: no cover
                pass
        await stop.wait()
        print("[virtual-armorx] stopping", flush=True)
        await self.device.stop_advertising()
        self.logs.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        default="tcp-server:127.0.0.1:9510",
        help="Bumble HCI transport exposed to the central client (default tcp-server)",
    )
    parser.add_argument(
        "--local-transport",
        default="/tmp/armorx_periph_hci.sock",
        help="UNIX socket path for the peripheral's own local HCI pipe",
    )
    parser.add_argument(
        "--mode",
        choices=["bridge", "direct"],
        default="bridge",
        help="bridge = two local Controllers on a LocalLink (TCP selftest model); "
        "direct = attach the peripheral Host straight onto the transport's HCI "
        "(use this for android-netsim / a real controller)",
    )
    parser.add_argument(
        "--address", default="F0:0A:A5:00:00:01", help="peripheral BD address"
    )
    parser.add_argument(
        "--peer-address", default="F0:0A:A5:00:00:02", help="peer-controller BD address"
    )
    parser.add_argument("--name-suffix", default="0001", help="suffix after 'ARMOR-X Pro_'")
    parser.add_argument(
        "--device-uuid",
        default="0001020304050607",
        help="8-byte device UUID (16 hex chars) returned in the EF reply. "
        "DEVICE IDENTITY, not a research constant; the research only fixes that "
        "reply bytes 3..10 are the UUID (ble-architecture.md:85).",
    )
    parser.add_argument(
        "--zkm-version",
        type=lambda v: int(v, 0),
        default=0x30,
        help="ZKM/MCU version byte for the 0B reply (default 0x30 = live-captured V48)",
    )
    parser.add_argument("--model-number", default="ZJ-XT", help="2A24 value (live: ZJ-XT)")
    parser.add_argument(
        "--firmware-revision", default="41", help="2A26 value (live capture: firmwareVersion=41)"
    )
    parser.add_argument("--battery-level", type=int, default=100)
    parser.add_argument("--config-file", default=None, help="override 144-byte config image")
    parser.add_argument("--ignore-config-crc", action="store_true")
    parser.add_argument("--app-version", default="4.0.8", help="app version under test")
    parser.add_argument(
        "--log-dir",
        default=str(Path(__file__).resolve().parent / "logs"),
    )
    parser.add_argument("--session-id", default=None)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    session_id = args.session_id or datetime.now().strftime("session-%Y%m%d-%H%M%S")
    logs = SessionLogs(
        Path(args.log_dir),
        session_id,
        args.app_version,
        {
            "role": "peripheral",
            "transport": args.transport,
            "name": f"{NAME_PREFIX}{args.name_suffix}",
            "address": args.address,
            "model_number": args.model_number,
            "firmware_revision": args.firmware_revision,
            "zkm_version": hex(args.zkm_version),
            "device_uuid": args.device_uuid,
            "config_bytes": 144,
        },
    )
    periph = ArmorXPeripheral(args, logs)
    try:
        asyncio.run(periph.run())
    except KeyboardInterrupt:
        pass
    finally:
        try:
            logs.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
