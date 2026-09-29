"""Shareable local exchange envelope for configurations and macros.

This is the local half of the planned community platform: a stable envelope with
a schema version, provenance and a deterministic content hash. There is no server
here and nothing leaves the machine.

Determinism rules:

* the content id is the SHA-256 of the canonical JSON of the envelope with the
  content id removed, so whitespace and key order in the source file are
  irrelevant;
* canonical JSON uses sorted keys and compact separators;
* private identifiers (serials, MACs, hostnames, home paths, usernames) are
  rejected by default and can only be included deliberately.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "armorx.exchange/v1"
CONTENT_TYPES = ("config", "macro")
EVIDENCE_LEVELS = ("proven", "strong-evidence", "inferred", "unknown")
MAX_PAYLOAD_BYTES = 64 * 1024

_PRIVATE_KEY_PATTERNS = (
    re.compile(r"serial", re.I),
    re.compile(r"\bmac\b|mac_?address", re.I),
    re.compile(r"hostname|host_?name", re.I),
    re.compile(r"home_?dir|homepath", re.I),
    re.compile(r"user_?name|\buser\b", re.I),
    re.compile(r"token|secret|password|api_?key", re.I),
    re.compile(r"bdaddr|bluetooth_?address|device_?address", re.I),
)
_PRIVATE_VALUE_PATTERNS = (
    (re.compile(r"\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", re.I), "<mac>"),
    (re.compile(r"/(?:home|Users)/[^/\s\"']+"), "<home>"),
)
_REDACTED = "<redacted>"


class ExchangeError(ValueError):
    """Raised when an envelope is malformed, unsafe or inconsistent."""


@dataclass
class ExchangeEnvelope:
    content_type: str
    payload: dict[str, Any]
    schema: str = SCHEMA
    toolkit_format: str = "0.2.0"
    device: dict[str, Any] = field(default_factory=dict)
    firmware: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    created: str | None = None
    notes: str | None = None
    content_id: str | None = None

    # -- construction -------------------------------------------------------

    def __post_init__(self) -> None:
        if self.content_type not in CONTENT_TYPES:
            raise ExchangeError(
                f"content_type must be one of {CONTENT_TYPES}, got {self.content_type!r}"
            )
        self._reject_private(self.payload, where="payload")
        self._reject_private(self.device, where="device")
        self._reject_private(self.provenance, where="provenance")
        encoded = canonical_json(self.payload).encode()
        if len(encoded) > MAX_PAYLOAD_BYTES:
            raise ExchangeError(
                f"payload is {len(encoded)} bytes, above the {MAX_PAYLOAD_BYTES} byte limit"
            )

    @staticmethod
    def _reject_private(mapping: dict[str, Any], *, where: str) -> None:
        if not isinstance(mapping, dict):
            raise ExchangeError(f"{where} must be a mapping")
        for key, value in mapping.items():
            for pattern in _PRIVATE_KEY_PATTERNS:
                if pattern.search(key):
                    raise ExchangeError(
                        f"{where}.{key} looks like private data; drop it or pass it explicitly"
                    )
            if isinstance(value, str):
                for pattern, _ in _PRIVATE_VALUE_PATTERNS:
                    if pattern.search(value):
                        raise ExchangeError(
                            f"{where}.{key} contains a private identifier; sanitise it first"
                        )
            elif isinstance(value, dict):
                ExchangeEnvelope._reject_private(value, where=f"{where}.{key}")

    # -- hashing / serialisation -------------------------------------------

    def body(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schema": self.schema,
            "content_type": self.content_type,
            "toolkit_format": self.toolkit_format,
            "payload": self.payload,
        }
        for name in ("device", "firmware", "provenance"):
            value = getattr(self, name)
            if value:
                data[name] = value
        for name in ("created", "notes"):
            value = getattr(self, name)
            if value:
                data[name] = value
        return data

    def compute_id(self) -> str:
        digest = hashlib.sha256(canonical_json(self.body()).encode()).hexdigest()
        return f"sha256:{digest}"

    def to_dict(self) -> dict[str, Any]:
        data = self.body()
        data["content_id"] = self.content_id or self.compute_id()
        return data

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


def canonical_json(value: Any) -> str:
    """Canonical form: sorted keys, compact separators, no trailing whitespace."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


# -- module level helpers ---------------------------------------------------

def create(content_type: str, payload: dict[str, Any], *, device: dict | None = None,
           firmware: dict | None = None, provenance: dict | None = None,
           created: str | None = None, notes: str | None = None,
           toolkit_format: str = "0.2.0") -> ExchangeEnvelope:
    env = ExchangeEnvelope(content_type=content_type, payload=payload, device=device or {},
                           firmware=firmware or {}, provenance=provenance or {},
                           created=created, notes=notes, toolkit_format=toolkit_format)
    env.content_id = env.compute_id()
    return env


def from_dict(data: dict[str, Any]) -> ExchangeEnvelope:
    if not isinstance(data, dict):
        raise ExchangeError("an envelope must be a JSON object")
    missing = [k for k in ("schema", "content_type", "payload") if k not in data]
    if missing:
        raise ExchangeError(f"envelope is missing required field(s): {', '.join(missing)}")
    if data["schema"] != SCHEMA:
        raise ExchangeError(
            f"unsupported schema {data['schema']!r}; this toolkit writes {SCHEMA!r}"
        )
    env = ExchangeEnvelope(
        content_type=data["content_type"],
        payload=data["payload"],
        schema=data["schema"],
        toolkit_format=data.get("toolkit_format", "0.2.0"),
        device=data.get("device", {}),
        firmware=data.get("firmware", {}),
        provenance=data.get("provenance", {}),
        created=data.get("created"),
        notes=data.get("notes"),
        content_id=data.get("content_id"),
    )
    return env


def load(path: str) -> ExchangeEnvelope:
    p = pathlib.Path(path)
    if not p.exists():
        raise ExchangeError(f"{path} does not exist")
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise ExchangeError(f"{path} is not valid JSON: {exc.msg} at line {exc.lineno}") from exc
    return from_dict(data)


def save(env: ExchangeEnvelope, path: str) -> str:
    p = pathlib.Path(path)
    p.write_text(env.to_json())
    return str(p)


def verify(env: ExchangeEnvelope) -> dict[str, Any]:
    expected = env.compute_id()
    claimed = env.content_id
    payload_bytes = len(canonical_json(env.payload).encode())
    return {
        "content_id": expected,
        "content_id_claimed": claimed,
        "content_id_ok": claimed is None or claimed == expected,
        "payload_bytes": payload_bytes,
        "schema": env.schema,
        "content_type": env.content_type,
        "toolkit_format": env.toolkit_format,
        "evidence": {
            "payload": env.provenance.get("evidence", "unknown"),
            "note": "evidence describes how the payload was obtained, not whether it is valid",
        },
    }


def sanitise(mapping: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with private keys removed and private values masked."""
    out: dict[str, Any] = {}
    for key, value in mapping.items():
        if any(p.search(key) for p in _PRIVATE_KEY_PATTERNS):
            continue
        if isinstance(value, dict):
            out[key] = sanitise(value)
        elif isinstance(value, str):
            masked = value
            for pattern, replacement in _PRIVATE_VALUE_PATTERNS:
                masked = pattern.sub(replacement, masked)
            out[key] = masked
        elif isinstance(value, list):
            out[key] = [sanitise(v) if isinstance(v, dict) else v for v in value]
        else:
            out[key] = value
    return out
