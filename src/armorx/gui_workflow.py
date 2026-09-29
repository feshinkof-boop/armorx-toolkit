"""Qt-independent workflow helpers for the Linux desktop configurator.

This module is the desktop adapter around the already-released v0.4 live
backend. It does not implement D6/D7/0E itself: apply and rollback delegate to
armorx.live.apply_config / rollback_config so the GUI inherits the same backup,
diff, confirmation and verification contract as the CLI.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from . import config as config_mod
from . import live as live_mod


PROFILE_FORMAT = "armorx-gui-profile-v1"


def default_data_root(*, env: Mapping[str, str] | None = None,
                      home: str | Path | None = None) -> Path:
    env = os.environ if env is None else env
    xdg = env.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "armorx-toolkit"
    base = Path(home) if home is not None else Path.home()
    return base / ".local" / "share" / "armorx-toolkit"


def default_backup_prefix(*, root: str | Path | None = None,
                          stamp: str | None = None) -> Path:
    base = Path(root) if root is not None else default_data_root()
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    backup_dir = base / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    candidate = backup_dir / f"gui-backup-{stamp}"
    if not any(candidate.with_suffix(s).exists()
               for s in (".json", ".bin", ".sha256", ".session.json")):
        return candidate
    suffix = 2
    while True:
        other = backup_dir / f"gui-backup-{stamp}-{suffix}"
        if not any(other.with_suffix(s).exists()
                   for s in (".json", ".bin", ".sha256", ".session.json")):
            return other
        suffix += 1


def _validate_image(image: bytes | bytearray | list[int]) -> bytes:
    data = bytes(image)
    if len(data) != config_mod.CONFIG_LEN:
        raise ValueError(f"configuration is {len(data)} bytes, expected 144")
    result = config_mod.validate(list(data))
    if result["declared_length"] != config_mod.CONFIG_LEN:
        raise ValueError(
            f"configuration declares {result['declared_length']} bytes, expected 144"
        )
    if not result["crc_matches"]:
        raise ValueError("configuration CRC does not validate")
    return data


def _profile_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()).strip("._")
    cleaned = cleaned[:40] or "profile"
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned}-{digest}.json"


class ProfileStore:
    """Local profile store containing validated full 144-byte images."""

    def __init__(self, root: str | Path | None = None):
        data_root = Path(root) if root is not None else default_data_root()
        self.root = data_root / "profiles"

    def _ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, name: str, image: bytes | bytearray | list[int], *,
             metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        name = str(name).strip()
        if not name:
            raise ValueError("profile name must not be empty")
        if len(name) > 80:
            raise ValueError("profile name is too long")
        data = _validate_image(image)
        summary = live_mod.image_summary(data)
        safe_meta = {
            key: value for key, value in (metadata or {}).items()
            if key in {"model", "firmware", "note"}
        }
        document = {
            "format": PROFILE_FORMAT,
            "name": name,
            "bytes": list(data),
            "summary": {
                "sha256": summary["sha256"],
                "crc": summary["stored_crc_hex"],
                "length": summary["actual_length"],
            },
            "metadata": safe_meta,
        }
        self._ensure()
        path = self.root / _profile_filename(name)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        temp.replace(path)
        return {"name": name, "file": path.name, **document["summary"]}

    def _documents(self) -> list[tuple[Path, dict[str, Any]]]:
        if not self.root.exists():
            return []
        rows: list[tuple[Path, dict[str, Any]]] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if doc.get("format") == PROFILE_FORMAT and isinstance(doc.get("name"), str):
                rows.append((path, doc))
        return rows

    def list(self) -> list[dict[str, Any]]:
        result = []
        for path, doc in self._documents():
            result.append({
                "name": doc["name"],
                "file": path.name,
                "sha256": (doc.get("summary") or {}).get("sha256"),
                "metadata": dict(doc.get("metadata") or {}),
            })
        return sorted(result, key=lambda row: row["name"].casefold())

    def load(self, name: str) -> bytes:
        for _path, doc in self._documents():
            if doc["name"] == name:
                data = _validate_image(doc.get("bytes") or [])
                expected = (doc.get("summary") or {}).get("sha256")
                actual = hashlib.sha256(data).hexdigest()
                if expected and expected != actual:
                    raise ValueError("profile SHA-256 does not match its bytes")
                return data
        raise FileNotFoundError(f"profile not found: {name}")

    def delete(self, name: str) -> bool:
        for path, doc in self._documents():
            if doc["name"] == name:
                path.unlink()
                return True
        return False


async def read_live_config(address: str, *,
                           transport_factory: Callable[[str], Any] | None = None,
                           connect_attempts: int = 3) -> dict[str, Any]:
    factory = transport_factory or (lambda value: live_mod.BleakLiveTransport(address=value))
    transport = factory(address)
    connection = await live_mod.connect_with_retries(transport, attempts=connect_attempts)
    if not connection["ok"]:
        raise live_mod.LiveError(
            "could not connect to the device: " + "; ".join(connection["errors"])
        )
    try:
        identity = await live_mod.read_identity(transport)
        details: dict[str, Any] = {}
        image = await live_mod.read_config(transport, report=details)
        return {
            "identity": identity,
            "image": image,
            "details": details,
            "connect_attempts": connection["attempts"],
        }
    finally:
        await transport.close()


async def apply_target(address: str, target: bytes, *, backup_prefix: str | Path,
                       confirmer, transport_factory: Callable[[str], Any] | None = None,
                       connect_attempts: int = 3, allow_unknown_diff: bool = False,
                       timeout: float = 4.0, ack_window: float = 1.5,
                       settle: float = 2.0) -> dict[str, Any]:
    target = _validate_image(target)
    factory = transport_factory or (lambda value: live_mod.BleakLiveTransport(address=value))
    transport = factory(address)
    connection = await live_mod.connect_with_retries(transport, attempts=connect_attempts)
    if not connection["ok"]:
        return {
            "command": "armorx gui apply",
            "status": live_mod.STATUS_REFUSED,
            "refusal_reason": "could not connect to the device",
            "connect_attempts": connection["attempts"],
            "never_wrote": True,
        }
    try:
        identity = await live_mod.read_identity(transport)
        report = await live_mod.apply_config(
            transport,
            target,
            backup_prefix=backup_prefix,
            confirmer=confirmer,
            automation=False,
            dry_run=False,
            allow_unknown_diff=allow_unknown_diff,
            identity=identity,
            timeout=timeout,
            ack_window=ack_window,
            settle=settle,
            confirm_title="ArmorX — Apply & Verify",
        )
    finally:
        await transport.close()
    report["command"] = "armorx gui apply"
    report["connect_attempts"] = connection["attempts"]
    return report


async def rollback_backup(address: str, backup_prefix: str | Path, *, confirmer,
                          transport_factory: Callable[[str], Any] | None = None,
                          connect_attempts: int = 3, timeout: float = 4.0,
                          ack_window: float = 1.5, settle: float = 2.0,
                          allow_unrelated_state: bool = False) -> dict[str, Any]:
    factory = transport_factory or (lambda value: live_mod.BleakLiveTransport(address=value))
    transport = factory(address)
    connection = await live_mod.connect_with_retries(transport, attempts=connect_attempts)
    if not connection["ok"]:
        return {
            "command": "armorx gui rollback",
            "status": live_mod.STATUS_REFUSED,
            "refusal_reason": "could not connect to the device",
            "connect_attempts": connection["attempts"],
            "never_wrote": True,
        }
    try:
        identity = await live_mod.read_identity(transport)
        report = await live_mod.rollback_config(
            transport,
            backup_prefix,
            confirmer=confirmer,
            automation=False,
            allow_unrelated_state=allow_unrelated_state,
            dry_run=False,
            identity=identity,
            timeout=timeout,
            ack_window=ack_window,
            settle=settle,
            confirm_title="ArmorX — Rollback",
        )
    finally:
        await transport.close()
    report["command"] = "armorx gui rollback"
    report["connect_attempts"] = connection["attempts"]
    return report


def backup_image(backup_prefix: str | Path) -> bytes:
    data = Path(backup_prefix).with_suffix(".bin").read_bytes()
    return _validate_image(data)
