"""Experimental live BLE backend for the v0.4.0 Linux work.

The current public CLI intentionally exposes only scan, identity, D6 config
read/backup, and offline planning.  Mutating D7/0E helpers exist behind an
explicit transport gate so they can be tested with mocks before any public
write command is added.

Protocol evidence comes from the project's captured Android/Windows BLE runs:
FFE1 is WriteWithoutResponse, FFE2 is Notify, D6 returns ten A4 fragments,
D7 carries the full 144-byte image, and A5 05 0E 00 B8 persists a D7-written
configuration across power loss on the tested ARMOR-X Pro.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Any

from . import config as config_mod
from . import protocol as protocol_mod

ARMORX_NAME_PREFIX = "ARMOR-X Pro"
VENDOR_SERVICE_UUID = "00000000-0000-1000-8000-00805f9b34fb"
FFE1_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
FFE2_UUID = "0000ffe2-0000-1000-8000-00805f9b34fb"
MODEL_UUID = "00002a24-0000-1000-8000-00805f9b34fb"
FIRMWARE_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
BATTERY_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

D6_REQUEST = protocol_mod.build_a5(0xD6)
PERSIST_REQUEST = protocol_mod.build_a5(0x0E, [0x00])


class LiveError(RuntimeError):
    """Base class for live-backend errors."""


class LiveDependencyError(LiveError):
    """Raised when the optional BLE dependency is unavailable."""


class LiveTimeout(LiveError):
    """Raised when a bounded live operation does not complete."""


class LiveWriteRefused(LiveError):
    """Raised when a mutating BLE operation has not been explicitly enabled."""


class AsyncLiveTransport(Protocol):
    """Small async seam used by both the Bleak backend and offline tests."""

    allow_mutating: bool

    async def connect(self) -> None: ...

    async def close(self) -> None: ...

    async def read_characteristic(self, uuid: str) -> bytes: ...

    async def send(self, frame: bytes, *, mutating: bool = False) -> None: ...

    async def recv(self, timeout: float) -> bytes: ...


@dataclass
class MockLiveTransport:
    """Scripted transport for deterministic hardware-free tests."""

    notifications: list[bytes] = field(default_factory=list)
    characteristics: dict[str, bytes] = field(default_factory=dict)
    allow_mutating: bool = False
    writes: list[dict[str, Any]] = field(default_factory=list)
    connected: bool = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    async def read_characteristic(self, uuid: str) -> bytes:
        if uuid not in self.characteristics:
            raise LiveError(f"characteristic {uuid} is not scripted")
        return bytes(self.characteristics[uuid])

    async def send(self, frame: bytes, *, mutating: bool = False) -> None:
        if mutating and not self.allow_mutating:
            raise LiveWriteRefused("mutating BLE writes are disabled")
        self.writes.append({"frame": bytes(frame), "mutating": bool(mutating)})

    async def recv(self, timeout: float) -> bytes:
        if not self.notifications:
            raise LiveTimeout(f"no scripted notification within {timeout:.1f}s")
        return bytes(self.notifications.pop(0))


def _load_bleak():
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError as exc:
        raise LiveDependencyError(
            "BLE support is optional; install armorx-toolkit[live] (requires bleak)"
        ) from exc
    return BleakClient, BleakScanner


@dataclass
class BleakLiveTransport:
    """BlueZ/Bleak transport for the proven FFE1/FFE2 path."""

    address: str
    connect_timeout: float = 20.0
    allow_mutating: bool = False
    _client: Any = None
    _queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def connect(self) -> None:
        BleakClient, _ = _load_bleak()
        self._client = BleakClient(self.address, timeout=self.connect_timeout)
        try:
            await self._client.connect()
            await self._client.start_notify(FFE2_UUID, self._on_notify)
        except Exception as exc:
            await self.close()
            raise LiveError(f"BLE connect/subscribe failed: {exc}") from exc

    def _on_notify(self, _sender, data) -> None:
        self._queue.put_nowait(bytes(data))

    async def close(self) -> None:
        client = self._client
        self._client = None
        if client is None:
            return
        try:
            if getattr(client, "is_connected", False):
                try:
                    await client.stop_notify(FFE2_UUID)
                except Exception:
                    pass
                await client.disconnect()
        except Exception:
            pass

    def _require_client(self):
        if self._client is None or not getattr(self._client, "is_connected", False):
            raise LiveError("BLE transport is not connected")
        return self._client

    async def read_characteristic(self, uuid: str) -> bytes:
        client = self._require_client()
        try:
            return bytes(await client.read_gatt_char(uuid))
        except Exception as exc:
            raise LiveError(f"BLE read {uuid} failed: {exc}") from exc

    async def send(self, frame: bytes, *, mutating: bool = False) -> None:
        if mutating and not self.allow_mutating:
            raise LiveWriteRefused(
                "mutating BLE writes are disabled; no public v0.4 command enables them yet"
            )
        client = self._require_client()
        try:
            await client.write_gatt_char(FFE1_UUID, bytes(frame), response=False)
        except Exception as exc:
            raise LiveError(f"BLE FFE1 write failed: {exc}") from exc

    async def recv(self, timeout: float) -> bytes:
        try:
            return bytes(await asyncio.wait_for(self._queue.get(), timeout))
        except asyncio.TimeoutError as exc:
            raise LiveTimeout(f"no FFE2 notification within {timeout:.1f}s") from exc


async def scan_ble(*, seconds: float = 8.0) -> list[dict]:
    """Scan locally for BLE advertisements, marking ARMOR-X-like names."""
    _, BleakScanner = _load_bleak()
    try:
        discovered = await BleakScanner.discover(timeout=seconds, return_adv=True)
    except Exception as exc:
        raise LiveError(f"BLE scan failed: {exc}") from exc

    rows: list[dict] = []
    if isinstance(discovered, dict):
        values = discovered.values()
    else:
        values = ((device, None) for device in discovered)

    for item in values:
        if isinstance(item, tuple) and len(item) == 2:
            device, adv = item
        else:
            device, adv = item, None
        name = (
            getattr(adv, "local_name", None)
            or getattr(device, "name", None)
            or ""
        )
        address = getattr(device, "address", None)
        rssi = getattr(adv, "rssi", None)
        service_uuids = list(getattr(adv, "service_uuids", None) or [])
        rows.append({
            "name": name,
            "address": address,
            "rssi": rssi,
            "service_uuids": service_uuids,
            "is_armorx": name.upper().startswith(ARMORX_NAME_PREFIX.upper()),
        })
    rows.sort(key=lambda row: (not row["is_armorx"], row["name"], row["address"] or ""))
    return rows


def _decode_text(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").strip("\x00")


async def read_identity(transport: AsyncLiveTransport) -> dict:
    """Read standard identity characteristics without changing config state."""
    fields: dict[str, Any] = {}
    for key, uuid in (
        ("model", MODEL_UUID),
        ("firmware", FIRMWARE_UUID),
        ("battery", BATTERY_UUID),
    ):
        try:
            raw = await transport.read_characteristic(uuid)
        except LiveError:
            fields[key] = None
            continue
        if key == "battery":
            fields[key] = raw[0] if raw else None
        else:
            fields[key] = _decode_text(raw)
    return {
        **fields,
        "transport": "ble",
        "service_uuid": VENDOR_SERVICE_UUID,
        "write_characteristic": FFE1_UUID,
        "notify_characteristic": FFE2_UUID,
    }


def _frames_from_notification(raw: bytes) -> list[protocol_mod.Frame]:
    if not raw:
        return []
    try:
        if len(raw) >= 2 and raw[1] == len(raw):
            return [protocol_mod.parse_frame(raw, require_checksum=True)]
        chunks = protocol_mod.split_stream(raw)
        return [protocol_mod.parse_frame(chunk, require_checksum=True) for chunk in chunks]
    except protocol_mod.FrameError:
        return []


async def read_config(transport: AsyncLiveTransport, *, timeout: float = 4.0,
                      report: dict[str, Any] | None = None) -> bytes:
    """Issue proven D6 and collect the ten indexed A4 configuration fragments.

    When *report* is a dict it is filled with the fragment accounting for the
    read, so a caller can record how many fragments arrived and how large each
    one was instead of taking the reassembled image on trust.
    """
    await transport.send(D6_REQUEST, mutating=False)
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    fragments: dict[int, protocol_mod.Frame] = {}

    while len(fragments) < protocol_mod.FRAGMENT_COUNT:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            raw = await transport.recv(remaining)
        except LiveTimeout:
            break
        for frame in _frames_from_notification(raw):
            if not frame.is_fragment or frame.opcode != 0xD6:
                continue
            index = frame.fragment_index or 0
            existing = fragments.get(index)
            if existing is not None and existing.raw != frame.raw:
                raise LiveError(f"conflicting D6 fragment {index}")
            fragments[index] = frame

    if len(fragments) != protocol_mod.FRAGMENT_COUNT:
        missing = [i for i in range(1, protocol_mod.FRAGMENT_COUNT + 1)
                   if i not in fragments]
        raise LiveTimeout(f"D6 incomplete: missing fragment(s) {missing}")

    image = protocol_mod.reassemble_a4(
        [fragments[i] for i in sorted(fragments)],
        opcode=0xD6,
    )
    _validate_image(image)
    if report is not None:
        report["fragment_count"] = len(fragments)
        report["fragments"] = [
            {
                "index": index,
                "frame_bytes": len(frame.raw),
                "data_bytes": len(frame.payload),
                "checksum_ok": frame.checksum_ok,
            }
            for index, frame in sorted(fragments.items())
        ]
    return image


def _validate_image(image: bytes) -> dict:
    if len(image) != config_mod.CONFIG_LEN:
        raise LiveError(f"configuration image is {len(image)} bytes, expected 144")
    result = config_mod.validate(list(image))
    if result["declared_length"] != config_mod.CONFIG_LEN:
        raise LiveError(
            f"configuration declares {result['declared_length']} bytes, expected 144"
        )
    if not result["crc_matches"]:
        raise LiveError("configuration CRC does not validate")
    return result


def image_summary(image: bytes) -> dict:
    validation = _validate_image(bytes(image))
    return {
        **validation,
        "sha256": hashlib.sha256(bytes(image)).hexdigest(),
    }


def backup_document(image: bytes, *, identity: dict | None = None,
                    fragments: list[dict[str, Any]] | None = None) -> dict:
    """Create a privacy-conscious baseline that config.load_config can reopen."""
    safe_identity = {
        key: value for key, value in (identity or {}).items()
        if key in {"model", "firmware", "battery", "transport"}
    }
    document = {
        "format": "armorx-live-backup-v1",
        "bytes": list(bytes(image)),
        "summary": image_summary(bytes(image)),
        "device": safe_identity,
        "privacy": {
            "ble_address_stored": False,
            "serial_stored": False,
            "hostname_stored": False,
        },
    }
    if fragments is not None:
        document["fragments"] = fragments
    return document


def load_image(path: str | Path) -> bytes:
    p = Path(path)
    if p.suffix.lower() == ".bin":
        data = p.read_bytes()
        _validate_image(data)
        return data
    values = config_mod.load_config(str(p))
    data = bytes(values)
    _validate_image(data)
    return data


def plan_config_change(baseline: bytes, target: bytes) -> dict:
    baseline = bytes(baseline)
    target = bytes(target)
    before = image_summary(baseline)
    after = image_summary(target)
    differences = [
        {"offset": i, "before": baseline[i], "after": target[i]}
        for i in range(config_mod.CONFIG_LEN)
        if baseline[i] != target[i]
    ]
    return {
        "baseline": before,
        "target": after,
        "changed_bytes": len(differences),
        "differences": differences,
        "mutating_commands_exposed": False,
        "next_gate": (
            "future apply must first read and save the live baseline, then D7 the "
            "validated target, issue 0E persistence, and D6 read back byte-for-byte"
        ),
    }


async def write_config_volatile(
    transport: AsyncLiveTransport,
    image: bytes,
    *,
    fragment_delay: float = 0.01,
) -> None:
    """Internal test seam for D7; not wired to the public CLI."""
    image = bytes(image)
    _validate_image(image)
    for frame in protocol_mod.fragment_config_image(0xD7, image):
        await transport.send(frame, mutating=True)
        if fragment_delay:
            await asyncio.sleep(fragment_delay)


async def persist_config(transport: AsyncLiveTransport) -> None:
    """Internal test seam for the proven 0E persistence command."""
    await transport.send(PERSIST_REQUEST, mutating=True)
