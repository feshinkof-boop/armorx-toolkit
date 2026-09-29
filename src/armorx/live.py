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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Any

from . import config as config_mod
from . import diff as diff_mod
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
        # ``None`` marks the end of a bounded window: the marker is consumed and
        # reported as a timeout, so a scripted test can separate the D7, 0E and
        # read-back windows without inventing a fake notification.
        if self.notifications[0] is None:
            self.notifications.pop(0)
            raise LiveTimeout(f"no notification inside the window ({timeout:.1f}s)")
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
        named = name.upper().startswith(ARMORX_NAME_PREFIX.upper())
        manufacturer = _manufacturer_summary(adv)
        service_data = _service_data_summary(adv)
        if named:
            reason = f"local name starts with {ARMORX_NAME_PREFIX!r}"
        elif not name:
            reason = ("no local name in this advertisement, so it cannot be classified as "
                      "an ARMOR-X; judge from the fields below or re-scan with the adapter "
                      "that carries the local name")
        else:
            reason = f"local name {name!r} does not match {ARMORX_NAME_PREFIX!r}"
        rows.append({
            "name": name,
            "address": address,
            "rssi": rssi,
            "service_uuids": service_uuids,
            "manufacturer_data": manufacturer,
            "service_data": service_data,
            "anonymous": not bool(name),
            "is_armorx": named,
            "candidate_reason": reason,
        })
    rows.sort(key=lambda row: (not row["is_armorx"], row["name"], row["address"] or ""))
    return rows


def _manufacturer_summary(adv) -> dict[str, str]:
    """Company id -> payload hex, truncated; empty when the advertisement has none.

    Advertisement payloads are device-level data, not personal data, but they are
    still only for local use: they must not be published in artifacts.
    """
    raw = getattr(adv, "manufacturer_data", None) or {}
    summary: dict[str, str] = {}
    try:
        for company, payload in raw.items():
            data = bytes(payload)
            text = data[:32].hex(" ")
            if len(data) > 32:
                text += f" ... ({len(data)} bytes)"
            summary[f"0x{int(company):04X}"] = text
    except (TypeError, ValueError):
        return {}
    return summary


def _service_data_summary(adv) -> dict[str, str]:
    raw = getattr(adv, "service_data", None) or {}
    summary: dict[str, str] = {}
    try:
        for uuid, payload in raw.items():
            summary[str(uuid)] = bytes(payload)[:32].hex(" ")
    except (TypeError, ValueError):
        return {}
    return summary


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

    try:
        image = protocol_mod.reassemble_a4(
            [fragments[i] for i in sorted(fragments)],
            opcode=0xD6,
        )
    except protocol_mod.FrameError as exc:
        # A malformed fragment set must be a clean refusal, never a traceback:
        # a caller acting on this image may be about to write it back.
        raise LiveError(f"D6 fragments could not be reassembled: {exc}") from exc
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


# ---------------------------------------------------------------------------
# no-op D7 write-safety gate
# ---------------------------------------------------------------------------
#
# This is deliberately ONE narrow command. It never accepts a target image, an
# opcode or a payload: the bytes it writes are the bytes it just read from the
# device, and nothing else can enter this code path.

D7_OPCODE = 0xD7
PERSIST_FRAME_HEX = "a5 05 0e 00 b8"


def save_baseline(prefix: str | Path, image: bytes, *, fragments=None,
                  identity: dict | None = None) -> dict:
    """Write the pre-write baseline as .json, .bin and .sha256.

    The document never contains the BLE address, a serial number, a hostname or
    a path.
    """
    image = bytes(image)
    summary = image_summary(image)
    base = Path(prefix)
    base.parent.mkdir(parents=True, exist_ok=True)
    json_path = base.with_suffix(".json")
    bin_path = base.with_suffix(".bin")
    sha_path = base.with_suffix(".sha256")
    document = backup_document(image, identity=identity, fragments=fragments)
    json_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    bin_path.write_bytes(image)
    sha_path.write_text(summary["sha256"] + "\n", encoding="utf-8")
    # Only base names are recorded: the report is meant to be publishable, so it
    # must never carry a home path or a user name.
    return {
        "json": json_path.name,
        "bin": bin_path.name,
        "sha256_file": sha_path.name,
        "sha256": summary["sha256"],
        "bytes": len(image),
    }


async def collect_notifications(transport: AsyncLiveTransport, *, window: float,
                                max_frames: int = 64) -> list[dict]:
    """Drain FFE2 notifications for a bounded window.

    Every raw notification is recorded even when it does not parse as a frame,
    so nothing observed is silently dropped.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + window
    observed: list[dict] = []
    while loop.time() < deadline:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            raw = await transport.recv(remaining)
        except LiveTimeout:
            break
        except LiveError:
            break
        frames = _frames_from_notification(raw)
        if not frames:
            observed.append({"raw_hex": raw.hex(" "), "parsed": False,
                             "note": "notification did not parse as a frame; kept as evidence"})
        for frame in frames:
            observed.append({
                "raw_hex": raw.hex(" "),
                "parsed": True,
                "opcode": frame.opcode,
                "opcode_hex": f"0x{frame.opcode:02X}",
                "length": frame.length,
                "payload_hex": frame.payload.hex(" "),
                "checksum_ok": frame.checksum_ok,
                "at": round(time.time(), 3),
            })
            if len(observed) >= max_frames:
                return observed
    return observed


async def validate_write_gate(
    transport: AsyncLiveTransport,
    *,
    backup_prefix: str | Path | None = None,
    authorized: bool = False,
    timeout: float = 4.0,
    ack_window: float = 1.5,
    fragment_delay: float = 0.01,
    settle: float = 2.0,
    identity: dict | None = None,
) -> dict:
    """Byte-identical no-op D7 write-back with 0E persistence and D6 read-back.

    Refuses to write unless every preflight condition holds, and never writes
    anything other than the image read from the device moments earlier.
    """
    report: dict[str, Any] = {
        "command": "armorx live validate-write-gate",
        "status": "REFUSED",
        "stage": "preflight",
        "mutating_commands_exposed_by_this_command": False,
        "never_accepts_a_target_image": True,
    }

    # --- preflight read 1 -------------------------------------------------
    first_details: dict = {}
    try:
        image_1 = await read_config(transport, timeout=timeout, report=first_details)
    except LiveError as exc:
        report["refusal_reason"] = f"first D6 read failed: {exc}"
        report["first_read"] = {"ok": False, "error": str(exc)}
        return report
    summary_1 = image_summary(image_1)
    report["first_read"] = {"ok": True, **summary_1,
                            "fragment_count": first_details.get("fragment_count")}

    # --- baseline before any mutation ------------------------------------
    report["baseline_sha256"] = summary_1["sha256"]
    if backup_prefix is None:
        report["refusal_reason"] = "no backup prefix was given; refusing to continue"
        return report
    report["stage"] = "backup"
    try:
        report["backup"] = save_baseline(backup_prefix, image_1,
                                        fragments=first_details.get("fragments"),
                                        identity=identity)
    except OSError as exc:
        report["refusal_reason"] = f"baseline backup failed: {exc}"
        return report

    # --- preflight read 2 -------------------------------------------------
    report["stage"] = "repeat-read"
    second_details: dict = {}
    try:
        image_2 = await read_config(transport, timeout=timeout, report=second_details)
    except LiveError as exc:
        report["refusal_reason"] = f"second D6 read failed: {exc}"
        report["second_read"] = {"ok": False, "error": str(exc)}
        return report
    summary_2 = image_summary(image_2)
    repeated_identical = bytes(image_1) == bytes(image_2)
    report["second_read"] = {"ok": True, **summary_2,
                             "fragment_count": second_details.get("fragment_count")}
    report["repeated_reads_identical"] = repeated_identical
    report["repeated_read_differences"] = _offset_differences(image_1, image_2)
    if not repeated_identical:
        report["refusal_reason"] = ("two consecutive live D6 reads differ; the device is "
                                    "changing configuration bytes, so no write is attempted")
        return report

    # --- operator authorization ------------------------------------------
    report["stage"] = "authorization"
    report["operator_authorized"] = bool(authorized)
    if not authorized:
        report["refusal_reason"] = ("operator authorization not given; re-run with "
                                    "--authorized only after the popup was acknowledged")
        return report

    # --- the write, and only the bytes just read -------------------------
    baseline = bytes(image_1)
    frames = protocol_mod.fragment_config_image(D7_OPCODE, baseline)
    if len(frames) != protocol_mod.FRAGMENT_COUNT:
        report["refusal_reason"] = "internal error: fragment count mismatch"
        return report

    report["stage"] = "d7"
    report["d7"] = {"fragments": [], "sent": 0}
    try:
        transport.allow_mutating = True
        for index, frame in enumerate(frames, start=1):
            await transport.send(frame, mutating=True)
            report["d7"]["fragments"].append({
                "index": index,
                "frame_bytes": len(frame),
                "data_bytes": len(frame) - 5,
                "checksum_ok": protocol_mod.parse_frame(frame).checksum_ok,
                "raw_hex": frame.hex(" "),
                "at": round(time.time(), 3),
            })
            report["d7"]["sent"] = index
            if fragment_delay:
                await asyncio.sleep(fragment_delay)
        report["d7"]["notifications"] = await collect_notifications(transport,
                                                                   window=ack_window)
    except LiveError as exc:
        report["refusal_reason"] = f"D7 write failed: {exc}"
        return report
    finally:
        transport.allow_mutating = False

    acknowledgement = _find_ack(report["d7"]["notifications"], 0xD7)
    report["d7"]["acknowledgement"] = acknowledgement
    report["d7"]["ack_observed"] = acknowledgement["observed"]

    # --- persistence, exactly once ---------------------------------------
    report["stage"] = "persist"
    report["persist"] = {"request_hex": PERSIST_REQUEST.hex(" "),
                         "expected_hex": PERSIST_FRAME_HEX, "sent": 0}
    if PERSIST_REQUEST.hex(" ") != PERSIST_FRAME_HEX:
        report["refusal_reason"] = "internal error: persistence frame mismatch"
        return report
    try:
        transport.allow_mutating = True
        await transport.send(PERSIST_REQUEST, mutating=True)
        report["persist"]["sent"] = 1
        report["persist"]["notifications"] = await collect_notifications(transport,
                                                                        window=ack_window)
    except LiveError as exc:
        report["refusal_reason"] = f"persistence command failed: {exc}"
        return report
    finally:
        transport.allow_mutating = False
    report["persist"]["notification_count"] = len(report["persist"]["notifications"])
    report["persist"]["acknowledgement"] = _find_ack(report["persist"]["notifications"], 0x0E)

    # --- decisive read-back ----------------------------------------------
    report["stage"] = "read-back"
    readback: dict[str, Any] = {"attempts": []}
    try:
        for attempt in (1, 2):
            details: dict = {}
            image = await read_config(transport, timeout=timeout, report=details)
            summary = image_summary(image)
            differences = _offset_differences(baseline, image)
            readback["attempts"].append({
                "attempt": attempt,
                **summary,
                "fragment_count": details.get("fragment_count"),
                "byte_for_byte_match": not differences,
                "differences": differences,
            })
            if attempt == 1 and differences:
                break  # never attempt a repair loop
            if attempt == 1 and settle:
                await asyncio.sleep(settle)
    except LiveError as exc:
        readback["error"] = str(exc)
        report["readback"] = readback
        report["status"] = "FAIL"
        report["failure_reason"] = f"post-write D6 read failed: {exc}"
        return report
    report["readback"] = readback

    attempts = readback["attempts"]
    identical = bool(attempts) and all(a["byte_for_byte_match"] for a in attempts)
    report["byte_for_byte_match"] = identical
    report["final_sha256"] = attempts[-1]["sha256"] if attempts else None
    report["all_offsets_differing"] = (attempts[-1]["differences"] if attempts else [])
    report["status"] = "PASS" if identical and len(attempts) == 2 else "FAIL"
    if report["status"] == "FAIL":
        report["failure_reason"] = ("post-write configuration does not match the baseline "
                                    "byte for byte; no further write was attempted")
    return report


def _offset_differences(before: bytes, after: bytes) -> list[dict]:
    """Exact differing offsets between two images, for the failure path."""
    if len(before) != len(after):
        return [{"length_mismatch": {"before": len(before), "after": len(after)}}]
    return [{"offset": index, "before": before[index], "after": after[index]}
            for index in range(len(before)) if before[index] != after[index]]


def _find_ack(notifications: list[dict], opcode: int) -> dict:
    """Report an acknowledgement if one was seen; never fabricate one."""
    for entry in notifications:
        if entry.get("parsed") and entry.get("opcode") == opcode:
            return {"observed": True, "raw_hex": entry["raw_hex"],
                    "checksum_ok": entry.get("checksum_ok"),
                    "payload_hex": entry.get("payload_hex")}
    return {"observed": False,
            "note": "no acknowledgement notification was seen in the bounded window; "
                    "this is recorded as an absence, not as a rejection"}


# ---------------------------------------------------------------------------
# supervised reversible M1 remap (experimental, single purpose)
# ---------------------------------------------------------------------------
#
# One logical change only: mapKeys[23] (the M1 source) becomes A. The target is
# derived in memory from the live baseline. The command accepts no target image,
# no opcode and no payload; the only image it will ever write during a restore is
# the baseline it saved itself, and its SHA-256 must match the session record.

M1_MAPKEY_INDEX = 23
M1_MAPKEY_OFFSET = config_mod.MAPKEYS_START + M1_MAPKEY_INDEX          # 135
M1_SOURCE_CODE = int(config_mod.MAP_KEY_CODES["M1"])                   # 23
M1_TARGET_NAME = "A"
M1_TARGET_CODE = int(config_mod.MAP_KEY_CODES[M1_TARGET_NAME])         # 0
EXPECTED_MUTATION_OFFSETS = (0, 1, M1_MAPKEY_OFFSET)                   # CRC + mapKeys[23]
SESSION_FORMAT = "armorx-reversible-m1-session-v1"


def build_m1_remap_target(baseline: bytes) -> dict:
    """Derive the M1 -> A target in memory from the live baseline.

    Refuses anything but the single expected logical change.
    """
    baseline = bytes(baseline)
    _validate_image(baseline)
    current = baseline[M1_MAPKEY_OFFSET]
    target = bytearray(baseline)
    target[M1_MAPKEY_OFFSET] = M1_TARGET_CODE
    crc = config_mod.crc16_gamepad(list(target[2:]))
    target[0] = (crc >> 8) & 0xFF
    target[1] = crc & 0xFF
    target = bytes(target)
    summary = image_summary(target)
    if summary["actual_length"] != config_mod.CONFIG_LEN:
        raise LiveError("target length is not 144 bytes")
    if summary["declared_length"] != config_mod.CONFIG_LEN:
        raise LiveError("target declared length is not 144")
    if not summary["crc_matches"]:
        raise LiveError("target CRC does not verify")
    plan = plan_config_change(baseline, target)
    changed = tuple(sorted(d["offset"] for d in plan["differences"]))
    if changed != EXPECTED_MUTATION_OFFSETS:
        raise LiveError(
            f"refusing this mutation: expected the changed offsets {EXPECTED_MUTATION_OFFSETS}, "
            f"got {changed}")
    return {
        "baseline": baseline,
        "target": target,
        "current_m1_code": current,
        "current_m1_name": config_mod.CANONICAL_KEY_NAMES.get(current, f"0x{current:02X}"),
        "target_m1_code": M1_TARGET_CODE,
        "target_m1_name": M1_TARGET_NAME,
        "changed_offsets": list(changed),
        "differences": plan["differences"],
        "target_summary": summary,
        "baseline_summary": image_summary(baseline),
    }


def classify_image(image: bytes, baseline: bytes, target: bytes | None) -> str:
    """Classify a live image against the session's images, never guessing."""
    image = bytes(image)
    if image == bytes(baseline):
        return "BASELINE"
    if target is not None and image == bytes(target):
        return "TARGET"
    return "UNEXPECTED"


def save_session_record(prefix: str | Path, record: dict) -> dict:
    path = Path(prefix).with_suffix(".session.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"session_record": path.name, "session_format": record.get("format")}


def load_session_record(prefix: str | Path) -> dict:
    path = Path(prefix).with_suffix(".session.json")
    if not path.exists():
        raise LiveError(f"no session record at {path.name}; run the apply stage first")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("format") != SESSION_FORMAT:
        raise LiveError("session record has an unexpected format")
    return record


def load_saved_baseline(prefix: str | Path, record: dict) -> bytes:
    """Reopen the baseline this toolkit saved, and prove it is still that image.

    An image supplied by anyone other than this toolkit cannot pass: its SHA-256
    must equal the baseline SHA recorded in the session record.
    """
    base = Path(prefix)
    bin_path = base.with_suffix(".bin")
    if not bin_path.exists():
        raise LiveError(f"no saved baseline at {bin_path.name}")
    image = bin_path.read_bytes()
    _validate_image(image)
    sha = hashlib.sha256(image).hexdigest()
    expected = record.get("baseline_sha256")
    if not expected or sha != expected:
        raise LiveError("saved baseline does not match the session record SHA-256; refusing")
    return image


def _image_meta(image: bytes) -> dict:
    summary = image_summary(image)
    return {"sha256": summary["sha256"], "bytes": summary["actual_length"],
            "crc": summary["stored_crc_hex"]}


async def _write_image_and_persist(transport: AsyncLiveTransport, image: bytes, *,
                                   fragment_delay: float, ack_window: float) -> dict:
    """D7-write one image, record the bounded window, then send 0E exactly once."""
    image = bytes(image)
    _validate_image(image)
    frames = protocol_mod.fragment_config_image(0xD7, image)
    if len(frames) != protocol_mod.FRAGMENT_COUNT:
        raise LiveError("internal error: fragment count mismatch")
    result: dict[str, Any] = {"fragments": [], "sent": 0}
    try:
        transport.allow_mutating = True
        for index, frame in enumerate(frames, start=1):
            await transport.send(frame, mutating=True)
            result["fragments"].append({
                "index": index,
                "frame_bytes": len(frame),
                "data_bytes": len(frame) - 5,
                "checksum_ok": protocol_mod.parse_frame(frame).checksum_ok,
                "at": round(time.time(), 3),
            })
            result["sent"] = index
            if fragment_delay:
                await asyncio.sleep(fragment_delay)
        result["notifications"] = await collect_notifications(transport, window=ack_window)
    finally:
        transport.allow_mutating = False
    result["acknowledgement"] = _find_ack(result["notifications"], 0xD7)
    result["ack_observed"] = result["acknowledgement"]["observed"]

    persist: dict[str, Any] = {"request_hex": PERSIST_REQUEST.hex(" "), "sent": 0}
    if PERSIST_REQUEST.hex(" ") != PERSIST_FRAME_HEX:
        raise LiveError("internal error: persistence frame mismatch")
    try:
        transport.allow_mutating = True
        await transport.send(PERSIST_REQUEST, mutating=True)
        persist["sent"] = 1
        persist["notifications"] = await collect_notifications(transport, window=ack_window)
    finally:
        transport.allow_mutating = False
    persist["notification_count"] = len(persist["notifications"])
    persist["acknowledgement"] = _find_ack(persist["notifications"], 0x0E)
    result["persist"] = persist
    return result


async def _dual_read_and_compare(transport: AsyncLiveTransport, *, expected: bytes,
                                 timeout: float, settle: float) -> dict:
    """Two D6 reads that must both equal ``expected`` exactly."""
    readback: dict[str, Any] = {"attempts": []}
    for attempt in (1, 2):
        details: dict = {}
        image = await read_config(transport, timeout=timeout, report=details)
        differences = _offset_differences(expected, image)
        readback["attempts"].append({
            "attempt": attempt,
            **image_summary(image),
            "fragment_count": details.get("fragment_count"),
            "byte_for_byte_match": not differences,
            "differences": differences,
            "state": classify_image(image, expected, None),
        })
        if differences:
            break
        if attempt == 1 and settle:
            await asyncio.sleep(settle)
    readback["matches"] = bool(readback["attempts"]) and all(
        a["byte_for_byte_match"] for a in readback["attempts"])
    readback["complete"] = len(readback["attempts"]) == 2
    return readback


async def validate_reversible_m1(
    transport: AsyncLiveTransport,
    *,
    backup_prefix: str | Path | None = None,
    authorized: bool = False,
    stage: str = "apply",
    timeout: float = 4.0,
    ack_window: float = 1.5,
    fragment_delay: float = 0.01,
    settle: float = 2.0,
    identity: dict | None = None,
) -> dict:
    """Apply, check or restore the supervised M1 -> A reversible mutation.

    ``stage='check'`` is read-only and classifies the live image.
    ``stage='restore'`` writes back only the baseline this toolkit saved.
    """
    if stage not in {"apply", "check", "restore"}:
        raise LiveError(f"unknown stage: {stage}")
    report: dict[str, Any] = {
        "command": "armorx live validate-reversible-m1",
        "stage": stage,
        "status": "REFUSED",
        "mutation": "mapKeys[23] (M1 source) -> A",
        "never_accepts_a_target_image": True,
        "mutating_commands_exposed_by_this_command": False,
        "general_apply_command_exposed": False,
    }
    if backup_prefix is None:
        report["refusal_reason"] = "no backup prefix was given; refusing to continue"
        return report

    if stage == "check":
        record = load_session_record(backup_prefix)
        target_sha = record.get("target_sha256")
        target = None
        try:
            baseline = load_saved_baseline(backup_prefix, record)
        except LiveError as exc:
            report["refusal_reason"] = str(exc)
            return report
        details: dict = {}
        try:
            image = await read_config(transport, timeout=timeout, report=details)
        except LiveError as exc:
            report["refusal_reason"] = f"D6 read failed: {exc}"
            return report
        summary = image_summary(image)
        state = classify_image(image, baseline, None)
        if state == "UNEXPECTED" and target_sha and summary["sha256"] == target_sha:
            state = "TARGET"
        report["status"] = "OK"
        report["observed_state"] = state
        report["observed"] = {**summary, "fragment_count": details.get("fragment_count")}
        report["baseline_sha256"] = record.get("baseline_sha256")
        report["target_sha256"] = target_sha
        report["restore_authorized"] = state == "TARGET"
        report["this_session_mutation"] = record.get("this_session_mutation")
        if state == "UNEXPECTED":
            report["restore_authorized"] = False
            report["operator_alert_required"] = True
            report["guidance"] = ("the live image is neither this session's baseline nor its "
                                 "target; do not write, alert the operator and preserve evidence")
        return report

    # ---- apply or restore ------------------------------------------------
    preflight_details: dict = {}
    try:
        image_1 = await read_config(transport, timeout=timeout, report=preflight_details)
    except LiveError as exc:
        report["refusal_reason"] = f"first D6 read failed: {exc}"
        return report
    report["first_read"] = {"ok": True, **image_summary(image_1),
                            "fragment_count": preflight_details.get("fragment_count")}

    # One prefix for the whole session: the recovery baseline, its .sha256 and the
    # session record the restore stage will reopen. The operator supplies a prefix
    # such as <dir>/baseline-original.
    backup_path = str(backup_prefix)
    if stage == "apply":
        report["stage_name"] = "preflight"
        try:
            report["baseline_backup"] = save_baseline(
                backup_path, image_1, fragments=preflight_details.get("fragments"),
                identity=identity)
        except OSError as exc:
            report["refusal_reason"] = f"baseline backup failed: {exc}"
            return report
    else:
        report["stage_name"] = "restore-preflight"
        try:
            record = load_session_record(backup_prefix)
            baseline_image = load_saved_baseline(backup_prefix, record)
        except LiveError as exc:
            report["refusal_reason"] = str(exc)
            return report
        saved_summary = image_summary(baseline_image)
        report["saved_baseline"] = saved_summary
        report["saved_baseline_note"] = (
            "the restore image is the baseline this toolkit saved before the mutation; "
            "its SHA-256 must match the session record")
        live_summary = image_summary(image_1)
        if live_summary["sha256"] == saved_summary["sha256"]:
            report["status"] = "NO_RESTORE_NEEDED"
            report["observed_state"] = "BASELINE"
            report["note"] = "the live configuration already equals the saved baseline"
            return report
        target_sha = record.get("target_sha256")
        state = "TARGET" if target_sha and live_summary["sha256"] == target_sha else "UNEXPECTED"
        report["observed_state"] = state
        if state == "UNEXPECTED":
            # Phase rule: an unrecognised third state is never written over.
            report["refusal_reason"] = (
                "the live image is neither this session's baseline nor its target; refusing "
                "to write, alert the operator and preserve every artifact")
            report["operator_alert_required"] = True
            return report
        image_1 = baseline_image          # the restore image is the saved baseline
        report["restore_source_sha256"] = saved_summary["sha256"]
        if not authorized:
            report["refusal_reason"] = ("operator authorization not given; re-run with "
                                       "--authorized only after the popup was acknowledged")
            return report
        report["operator_authorized"] = True
        report["write"] = await _write_image_and_persist(
            transport, baseline_image, fragment_delay=fragment_delay, ack_window=ack_window)
        try:
            readback = await _dual_read_and_compare(transport, expected=baseline_image,
                                                    timeout=timeout, settle=settle)
        except LiveError as exc:
            report["status"] = "FAIL"
            report["failure_reason"] = f"post-restore D6 read failed: {exc}"
            return report
        report["readback"] = readback
        report["byte_for_byte_match"] = readback["matches"]
        report["final_sha256"] = readback["attempts"][-1]["sha256"] if readback["attempts"] else None
        report["status"] = "RESTORED" if readback["matches"] and readback["complete"] else "FAIL"
        report["restored_baseline_sha256"] = saved_summary["sha256"]
        return report

    # apply: a second preflight read must match the first exactly
    report["stage_name"] = "repeat-read"
    second_details: dict = {}
    try:
        image_2 = await read_config(transport, timeout=timeout, report=second_details)
    except LiveError as exc:
        report["refusal_reason"] = f"second D6 read failed: {exc}"
        return report
    report["second_read"] = {"ok": True, **image_summary(image_2),
                             "fragment_count": second_details.get("fragment_count")}
    identical = bytes(image_1) == bytes(image_2)
    report["repeated_reads_identical"] = identical
    if not identical:
        report["refusal_reason"] = ("two consecutive live D6 reads differ; no write is attempted")
        return report

    baseline = bytes(image_1)
    report["baseline_sha256"] = hashlib.sha256(baseline).hexdigest()
    report["baseline_m1"] = {
        "offset": M1_MAPKEY_OFFSET,
        "code": baseline[M1_MAPKEY_OFFSET],
        "name": config_mod.CANONICAL_KEY_NAMES.get(baseline[M1_MAPKEY_OFFSET],
                                                   f"0x{baseline[M1_MAPKEY_OFFSET]:02X}"),
    }
    report["historical_baseline_match"] = (
        report["baseline_sha256"] == "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6")

    # this experiment only makes sense if M1 is not already A
    if baseline[M1_MAPKEY_OFFSET] == M1_TARGET_CODE:
        report["status"] = "ABORTED_ALREADY_A"
        report["refusal_reason"] = ("mapKeys[23] already equals A, so this particular mutation "
                                   "has nothing to apply; no D7 and no 0E were sent")
        return report

    report["stage_name"] = "target"
    try:
        plan = build_m1_remap_target(baseline)
    except LiveError as exc:
        report["refusal_reason"] = str(exc)
        return report
    target = plan["target"]
    report["target"] = {
        "sha256": plan["target_summary"]["sha256"],
        "bytes": plan["target_summary"]["actual_length"],
        "declared_length": plan["target_summary"]["declared_length"],
        "crc_matches": plan["target_summary"]["crc_matches"],
        "m1_code": plan["target_m1_code"],
        "m1_name": plan["target_m1_name"],
        "changed_offsets": plan["changed_offsets"],
    }
    report["target_differences"] = plan["differences"]
    report["expected_changed_offsets"] = list(EXPECTED_MUTATION_OFFSETS)

    report["stage_name"] = "authorization"
    report["operator_authorized"] = bool(authorized)
    if not authorized:
        report["refusal_reason"] = ("operator authorization not given; re-run with --authorized "
                                   "only after the popup was acknowledged")
        return report

    session_record = {
        "format": SESSION_FORMAT,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mutation": f"mapKeys[{M1_MAPKEY_INDEX}] (M1 source) -> {M1_TARGET_NAME}",
        "baseline_sha256": report["baseline_sha256"],
        "baseline_bytes": len(baseline),
        "baseline_m1_code": baseline[M1_MAPKEY_OFFSET],
        "target_sha256": plan["target_summary"]["sha256"],
        "target_m1_code": plan["target_m1_code"],
        "target_changed_offsets": plan["changed_offsets"],
        "device": {k: v for k, v in (identity or {}).items()
                   if k in {"model", "firmware", "battery", "transport"}},
        "this_session_mutation": False,
    }
    report["session_record"] = save_session_record(backup_path, session_record)

    report["stage_name"] = "apply"
    report["write"] = await _write_image_and_persist(
        transport, target, fragment_delay=fragment_delay, ack_window=ack_window)

    report["stage_name"] = "verify-target"
    try:
        readback = await _dual_read_and_compare(transport, expected=target,
                                                timeout=timeout, settle=settle)
    except LiveError as exc:
        report["status"] = "FAIL"
        report["failure_reason"] = f"post-write D6 read failed: {exc}"
        return report
    report["readback"] = readback
    report["byte_for_byte_match"] = readback["matches"]
    report["target_sha256"] = plan["target_summary"]["sha256"]
    report["final_sha256"] = readback["attempts"][-1]["sha256"] if readback["attempts"] else None
    if not readback["matches"]:
        last = readback["attempts"][-1]["sha256"] if readback["attempts"] else None
        state = "UNEXPECTED"
        if last == report["baseline_sha256"]:
            state = "BASELINE"
        elif last == report["target_sha256"]:
            state = "TARGET"
        report["observed_state"] = state
        report["status"] = "FAIL"
        report["failure_reason"] = ("the live configuration does not match the target byte for "
                                   "byte; no further write was attempted")
        report["guidance"] = {
            "BASELINE": "the device already holds the original baseline; no restore is needed",
            "TARGET": "the device holds the target; a restore of the saved baseline is authorized",
            "UNEXPECTED": ("neither this session's baseline nor its target; do not write again, "
                           "alert the operator and preserve every artifact"),
        }[state]
        return report

    session_record["this_session_mutation"] = True
    report["session_record"] = save_session_record(backup_path, session_record)
    report["status"] = "APPLIED"
    report["this_session_mutation"] = True
    report["next_required_step"] = (
        "restore the saved original baseline with --stage restore --authorized, then confirm "
        "with --stage check")
    return report


# ---------------------------------------------------------------------------
# public apply / rollback (productised write path)
# ---------------------------------------------------------------------------
#
# Both commands reuse the proven primitives above: read_config (D6),
# _write_image_and_persist (D7 + one 0E) and _dual_read_and_compare. Nothing in
# this section re-implements the protocol.

CONNECT_ATTEMPTS_DEFAULT = 3
CONNECT_RETRY_DELAY = 1.0

STATUS_APPLIED = "APPLIED"
STATUS_NO_CHANGE = "NO_CHANGE"
STATUS_DRY_RUN = "DRY_RUN"
STATUS_RESTORED = "RESTORED"
STATUS_REFUSED = "REFUSED"
STATUS_FAIL = "FAIL"
STATUS_UNEXPECTED_STATE = "UNEXPECTED_STATE"


def _default_confirmer(automation: bool):
    from . import confirm as confirm_mod

    def confirm(text: str, title: str):
        return confirm_mod.confirm_change(text, title=title, automation=automation)

    return confirm


async def connect_with_retries(transport: AsyncLiveTransport, *,
                               attempts: int = CONNECT_ATTEMPTS_DEFAULT,
                               delay: float = CONNECT_RETRY_DELAY,
                               sleep=asyncio.sleep) -> dict:
    """Connect with a bounded number of attempts.

    Only ever used before the first mutating frame: a connection lost mid-write
    must never be answered by re-sending the transaction.
    """
    errors: list[str] = []
    for attempt in range(1, max(1, attempts) + 1):
        try:
            await transport.connect()
        except LiveError as exc:
            errors.append(str(exc))
            if attempt < attempts:
                await sleep(delay)
            continue
        return {"ok": True, "attempts": attempt, "errors": errors}
    return {"ok": False, "attempts": max(1, attempts), "errors": errors}


def _state_from_readback(readback: dict, *, baseline_sha: str,
                         target_sha: str | None) -> dict | None:
    """Classify the state from a read-back that already happened.

    Re-using the read-back avoids one more BLE round trip purely for diagnosis,
    and it reflects the image the verification actually saw.
    """
    attempts = readback.get("attempts") or []
    if not attempts:
        return None
    last = attempts[-1]
    sha = last.get("sha256")
    if not sha:
        return None
    if sha == baseline_sha:
        state = "BASELINE"
    elif target_sha and sha == target_sha:
        state = "TARGET"
    else:
        state = "UNEXPECTED"
    return {"reachable": True, "state": state, "sha256": sha,
            "length": last.get("actual_length"), "crc_matches": last.get("crc_matches"),
            "source": "the verification read-back itself"}


async def _classify_live(transport: AsyncLiveTransport, *, baseline: bytes,
                         target: bytes | None, timeout: float) -> dict:
    """Read-only classification of the live image, used after a failed write."""
    try:
        image = await read_config(transport, timeout=timeout)
    except LiveError as exc:
        return {"reachable": False, "error": str(exc), "state": "UNREADABLE",
                "sha256": None}
    summary = image_summary(image)
    state = classify_image(image, baseline, target)
    return {"reachable": True, "state": state, "sha256": summary["sha256"],
            "length": summary["actual_length"], "crc_matches": summary["crc_matches"]}


def _confirmation_text(*, identity: dict | None, current_sha: str, target_sha: str,
                       summary: str, diff: dict, backup_name: str,
                       allow_unknown_diff: bool) -> str:
    safe = {k: v for k, v in (identity or {}).items()
            if k in {"model", "firmware", "transport"}}
    lines = [
        "Write this configuration to the controller?",
        "",
        f"device model: {safe.get('model', 'unknown')}",
        f"firmware: {safe.get('firmware', 'unknown')}",
        f"current SHA-256: {current_sha}",
        f"target SHA-256:  {target_sha}",
        f"changed bytes: {diff['total_changed_bytes']}",
        f"known field changes: {len(diff['known_field_changes'])}",
        f"undecoded changed bytes: {diff['unknown_byte_count']}"
        + (" (explicitly allowed)" if allow_unknown_diff else ""),
        f"backup file: {backup_name}",
        "",
        summary,
        "",
        "Click APPLY to write and persist, Cancel to abort with no write.",
    ]
    return "\n".join(lines)


async def apply_config(
    transport: AsyncLiveTransport,
    target: bytes,
    *,
    backup_prefix: str | Path | None = None,
    confirmer=None,
    automation: bool = False,
    dry_run: bool = False,
    allow_unknown_diff: bool = False,
    identity: dict | None = None,
    timeout: float = 4.0,
    ack_window: float = 1.5,
    fragment_delay: float = 0.01,
    settle: float = 2.0,
    confirm_title: str = "ARMOR-X configuration change",
) -> dict:
    """Apply a validated target configuration and prove it landed.

    The target is loaded offline by the caller; this function only ever writes
    the image it was given, as ten full-image D7 fragments.
    """
    report: dict[str, Any] = {
        "command": "armorx live apply",
        "status": STATUS_REFUSED,
        "stage": "target-validation",
        "identity": {k: v for k, v in (identity or {}).items()
                     if k in {"model", "firmware", "battery", "transport"}},
        "dry_run": bool(dry_run),
    }
    target = bytes(target)
    try:
        _validate_image(target)
    except LiveError as exc:
        report["refusal_reason"] = f"target is not a valid 144-byte configuration: {exc}"
        return report
    report["target"] = {"sha256": image_summary(target)["sha256"],
                        "crc": image_summary(target)["stored_crc_hex"],
                        "length": len(target),
                        "declared_length": image_summary(target)["declared_length"]}

    # --- live reads -------------------------------------------------------
    report["stage"] = "live-read-1"
    first_details: dict = {}
    try:
        current = await read_config(transport, timeout=timeout, report=first_details)
    except LiveError as exc:
        report["refusal_reason"] = f"first live D6 read failed: {exc}"
        return report
    report["current"] = {"sha256": image_summary(current)["sha256"],
                         "crc": image_summary(current)["stored_crc_hex"],
                         "length": image_summary(current)["actual_length"],
                         "declared_length": image_summary(current)["declared_length"],
                         "fragment_count": first_details.get("fragment_count")}
    report["stage"] = "live-read-2"
    second_details: dict = {}
    try:
        current_2 = await read_config(transport, timeout=timeout, report=second_details)
    except LiveError as exc:
        report["refusal_reason"] = f"second live D6 read failed: {exc}"
        return report
    if bytes(current) != bytes(current_2):
        report["refusal_reason"] = ("two consecutive live reads differ; the device is "
                                    "changing underneath us, so nothing is written")
        report["live_read_differences"] = _offset_differences(current, current_2)
        return report
    report["live_reads_identical"] = True

    # --- target vs current ------------------------------------------------
    report["stage"] = "compare"
    if bytes(current) == target:
        report["status"] = STATUS_NO_CHANGE
        report["note"] = ("the device already holds this exact configuration; no D7 and "
                          "no 0E were sent")
        return report

    # --- automatic backup, then prove it is on disk -----------------------
    if backup_prefix is None:
        report["refusal_reason"] = "no backup prefix was given; refusing to write"
        return report
    report["stage"] = "backup"
    try:
        backup = save_baseline(backup_prefix, current,
                               fragments=first_details.get("fragments"), identity=identity)
    except OSError as exc:
        report["refusal_reason"] = f"backup could not be written: {exc}"
        return report
    report["backup"] = backup
    report["stage"] = "backup-reopen"
    try:
        reopened = Path(backup_prefix).with_suffix(".bin").read_bytes()
    except OSError as exc:
        report["refusal_reason"] = f"backup could not be reopened: {exc}"
        return report
    reopen_sha = hashlib.sha256(reopened).hexdigest()
    report["backup_reopened_sha256"] = reopen_sha
    if reopen_sha != report["current"]["sha256"]:
        report["refusal_reason"] = ("the reopened backup does not match the live image; "
                                    "refusing to write")
        return report
    report["backup_verified"] = True

    # --- diff and safety classification -----------------------------------
    report["stage"] = "diff"
    changes = diff_mod.diff_images(current, target)
    report["diff"] = changes
    report["diff_summary"] = diff_mod.summarise(changes)
    report["unknown_byte_count"] = changes["unknown_byte_count"]
    report["allow_unknown_diff"] = bool(allow_unknown_diff)
    if changes["has_unknown_changes"] and not allow_unknown_diff:
        report["refusal_reason"] = (
            f"{changes['unknown_byte_count']} changed byte(s) are not decoded by any "
            "recovered field; re-run with --allow-unknown-diff to write them anyway")
        report["unknown_offsets"] = [c["offset"] for c in changes["unknown_byte_changes"]]
        return report

    report["rollback_available"] = True

    # --- confirmation -----------------------------------------------------
    report["stage"] = "confirmation"
    text = _confirmation_text(identity=identity, current_sha=report["current"]["sha256"],
                              target_sha=report["target"]["sha256"],
                              summary=report["diff_summary"], diff=changes,
                              backup_name=backup["bin"], allow_unknown_diff=allow_unknown_diff)
    if dry_run:
        report["status"] = STATUS_DRY_RUN
        report["confirmation_text"] = text
        report["note"] = "dry run: nothing was written, allow_mutating was never enabled"
        report["mutating_frames_sent"] = 0
        return report
    confirmer = confirmer or _default_confirmer(automation)
    try:
        confirmation = confirmer(text, confirm_title)
    except Exception as exc:  # a broken dialog must not write
        report["refusal_reason"] = f"confirmation backend failed: {exc}"
        return report
    outcome = getattr(confirmation, "accepted", None)
    method = getattr(confirmation, "method", "unknown")
    report["confirmation"] = {"method": method, "accepted": outcome,
                              "detail": getattr(confirmation, "detail", "")}
    if outcome is None:
        report["refusal_reason"] = ("no confirmation backend was available; nothing was "
                                    "written")
        return report
    if not outcome:
        report["refusal_reason"] = "the operator declined the change; nothing was written"
        return report

    # --- write ------------------------------------------------------------
    report["stage"] = "d7"
    try:
        report["write"] = await _write_image_and_persist(
            transport, target, fragment_delay=fragment_delay, ack_window=ack_window)
    except LiveError as exc:
        report["status"] = STATUS_FAIL
        report["failure_reason"] = f"the write failed: {exc}"
        report["live_state_after_failure"] = await _classify_live(
            transport, baseline=current, target=target, timeout=timeout)
        report["guidance"] = ("do not write again automatically; classify the state and "
                              "decide with the operator")
        return report

    # --- verification -----------------------------------------------------
    report["stage"] = "verify"
    try:
        readback = await _dual_read_and_compare(transport, expected=target,
                                                timeout=timeout, settle=settle)
    except LiveError as exc:
        report["status"] = STATUS_FAIL
        report["failure_reason"] = f"post-write verification failed to read: {exc}"
        report["live_state_after_failure"] = await _classify_live(
            transport, baseline=current, target=target, timeout=timeout)
        return report
    report["verification"] = readback
    report["byte_for_byte_match"] = readback["matches"]
    report["final_sha256"] = (readback["attempts"][-1]["sha256"] if readback["attempts"]
                              else None)
    if readback["matches"] and readback["complete"]:
        report["status"] = STATUS_APPLIED
        return report
    state = _state_from_readback(readback, baseline_sha=report["current"]["sha256"],
                                target_sha=report["target"]["sha256"])
    if state is None:
        state = await _classify_live(transport, baseline=current, target=target,
                                     timeout=timeout)
    report["live_state_after_failure"] = state
    report["status"] = (STATUS_UNEXPECTED_STATE if state.get("state") == "UNEXPECTED"
                        else STATUS_FAIL)
    report["failure_reason"] = ("the configuration read back does not match the target; "
                                "nothing further was written")
    return report


def _verify_backup_trio(backup_prefix: str | Path) -> dict:
    """Load a saved backup and prove the three files agree with each other."""
    base = Path(backup_prefix)
    json_path = base.with_suffix(".json")
    bin_path = base.with_suffix(".bin")
    sha_path = base.with_suffix(".sha256")
    for path in (json_path, bin_path, sha_path):
        if not path.exists():
            raise LiveError(f"backup file {path.name} is missing")
    image = bin_path.read_bytes()
    _validate_image(image)
    bin_sha = hashlib.sha256(image).hexdigest()
    sha_file = sha_path.read_text(encoding="utf-8").strip().split()[0]
    if sha_file != bin_sha:
        raise LiveError("the .sha256 file does not match the .bin backup")
    document = json.loads(json_path.read_text(encoding="utf-8"))
    json_sha = (document.get("summary") or {}).get("sha256")
    if json_sha and json_sha != bin_sha:
        raise LiveError("the .json backup does not match the .bin backup")
    return {"image": image, "sha256": bin_sha, "document": document,
            "files": {"json": json_path.name, "bin": bin_path.name,
                      "sha256": sha_path.name}}


async def rollback_config(
    transport: AsyncLiveTransport,
    backup_prefix: str | Path,
    *,
    confirmer=None,
    automation: bool = False,
    allow_unrelated_state: bool = False,
    dry_run: bool = False,
    identity: dict | None = None,
    timeout: float = 4.0,
    ack_window: float = 1.5,
    fragment_delay: float = 0.01,
    settle: float = 2.0,
    confirm_title: str = "ARMOR-X rollback",
) -> dict:
    """Write back the exact bytes of a saved backup.

    The backup is authoritative: the image is never rebuilt from a decoded
    document, only the saved ``.bin`` is used, and all three backup files must
    agree before anything is written.
    """
    report: dict[str, Any] = {
        "command": "armorx live rollback",
        "status": STATUS_REFUSED,
        "stage": "backup-verification",
        "identity": {k: v for k, v in (identity or {}).items()
                     if k in {"model", "firmware", "battery", "transport"}},
        "dry_run": bool(dry_run),
    }
    try:
        backup = _verify_backup_trio(backup_prefix)
    except (LiveError, OSError, ValueError, json.JSONDecodeError) as exc:
        report["refusal_reason"] = f"backup is not usable: {exc}"
        return report
    baseline = backup["image"]
    report["backup"] = {"files": backup["files"], "sha256": backup["sha256"],
                        "length": len(baseline),
                        "crc": image_summary(baseline)["stored_crc_hex"]}

    report["stage"] = "live-read"
    try:
        current = await read_config(transport, timeout=timeout)
    except LiveError as exc:
        report["refusal_reason"] = f"live D6 read failed: {exc}"
        return report
    current_sha = image_summary(current)["sha256"]
    report["current"] = {"sha256": current_sha, "crc": image_summary(current)["stored_crc_hex"]}

    if bytes(current) == bytes(baseline):
        report["status"] = STATUS_NO_CHANGE
        report["note"] = "the device already holds the backup configuration"
        return report

    record = None
    record_path = Path(backup_prefix).with_suffix(".session.json")
    if record_path.exists():
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            record = None
    known_target = bool(record and record.get("target_sha256") == current_sha)
    report["state_classification"] = ("known_target" if known_target
                                      else "already_backup" if bytes(current) == bytes(baseline)
                                      else "different")
    report["session_record"] = record_path.name if record else None
    if not known_target and not allow_unrelated_state:
        report["refusal_reason"] = (
            "the live configuration is not the target this backup was written before; "
            "re-run with --allow-unrelated-state to overwrite it anyway")
        return report

    report["stage"] = "confirmation"
    text = "\n".join([
        "Restore this saved configuration to the controller?",
        "",
        f"backup SHA-256: {backup['sha256']}",
        f"current SHA-256: {current_sha}",
        f"backup file: {backup['files']['bin']}",
        "",
        "Click APPLY to write and persist, Cancel to abort with no write.",
    ])
    if dry_run:
        report["status"] = STATUS_DRY_RUN
        report["confirmation_text"] = text
        report["mutating_frames_sent"] = 0
        return report
    confirmer = confirmer or _default_confirmer(automation)
    try:
        confirmation = confirmer(text, confirm_title)
    except Exception as exc:
        report["refusal_reason"] = f"confirmation backend failed: {exc}"
        return report
    outcome = getattr(confirmation, "accepted", None)
    report["confirmation"] = {"method": getattr(confirmation, "method", "unknown"),
                              "accepted": outcome,
                              "detail": getattr(confirmation, "detail", "")}
    if outcome is None:
        report["refusal_reason"] = "no confirmation backend was available; nothing was written"
        return report
    if not outcome:
        report["refusal_reason"] = "the operator declined the rollback; nothing was written"
        return report

    report["stage"] = "d7"
    try:
        report["write"] = await _write_image_and_persist(
            transport, baseline, fragment_delay=fragment_delay, ack_window=ack_window)
    except LiveError as exc:
        report["status"] = STATUS_FAIL
        report["failure_reason"] = f"the rollback write failed: {exc}"
        report["live_state_after_failure"] = await _classify_live(
            transport, baseline=baseline, target=None, timeout=timeout)
        return report

    report["stage"] = "verify"
    try:
        readback = await _dual_read_and_compare(transport, expected=baseline,
                                                timeout=timeout, settle=settle)
    except LiveError as exc:
        report["status"] = STATUS_FAIL
        report["failure_reason"] = f"post-rollback verification failed to read: {exc}"
        report["live_state_after_failure"] = await _classify_live(
            transport, baseline=baseline, target=None, timeout=timeout)
        return report
    report["verification"] = readback
    report["byte_for_byte_match"] = readback["matches"]
    report["final_sha256"] = (readback["attempts"][-1]["sha256"] if readback["attempts"]
                              else None)
    if readback["matches"] and readback["complete"]:
        report["status"] = STATUS_RESTORED
        report["restored_sha256"] = backup["sha256"]
        return report
    state = _state_from_readback(readback, baseline_sha=backup["sha256"], target_sha=None)
    if state is None:
        state = await _classify_live(transport, baseline=baseline, target=None,
                                     timeout=timeout)
    report["live_state_after_failure"] = state
    report["status"] = (STATUS_UNEXPECTED_STATE if state.get("state") == "UNEXPECTED"
                        else STATUS_FAIL)
    report["failure_reason"] = "the configuration read back does not match the backup"
    return report
