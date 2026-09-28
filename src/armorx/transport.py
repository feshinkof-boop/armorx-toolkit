"""Transport abstractions with an offline mock.

The public toolkit never performs experimental writes on its own. Transports
here exist so that parsers and tooling can be developed and tested without
hardware, and so that a future read-only backend has a defined seam.

A transport is deliberately small:

* :class:`Transport` - the interface;
* :class:`MockTransport` - a scripted, fully offline implementation;
* :func:`open_hidraw` - an optional read-only hidraw transport.

Writes are refused by default everywhere. Nothing in this module opens a
device unless it is explicitly asked to.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence, Protocol


class TransportError(RuntimeError):
    """Raised for transport-level failures."""


class WriteRefused(TransportError):
    """Raised when a write is attempted on a read-only transport."""


class Transport(Protocol):
    """Minimum surface a transport must provide."""

    @property
    def name(self) -> str: ...

    def read(self, size: int = 64, timeout: float | None = None) -> bytes: ...

    def close(self) -> None: ...


@dataclass
class MockTransport:
    """A scripted transport for tests and offline development.

    Chunks are returned in order; when they run out, :class:`TransportError` is
    raised so tests fail loudly instead of hanging.
    """

    chunks: list[bytes] = field(default_factory=list)
    name: str = "mock"
    writes: list[bytes] = field(default_factory=list)
    read_only: bool = True
    closed: bool = False

    def feed(self, data: bytes) -> None:
        self.chunks.append(bytes(data))

    def read(self, size: int = 64, timeout: float | None = None) -> bytes:
        if self.closed:
            raise TransportError("transport is closed")
        if not self.chunks:
            raise TransportError("no scripted data left")
        chunk = self.chunks.pop(0)
        return chunk[:size] if size else chunk

    def write(self, data: bytes) -> int:
        if self.read_only:
            raise WriteRefused("this transport is read-only by design")
        self.writes.append(bytes(data))
        return len(data)

    def close(self) -> None:
        self.closed = True


@dataclass
class HidrawTransport:
    """Read-only hidraw transport.

    Opening a hidraw node is a read-only action, but it still requires the
    owning user to change node permissions. Writing is refused unless the
    caller explicitly opts in with ``allow_writes=True``, and no toolkit
    command enables that path today.
    """

    path: str
    allow_writes: bool = False
    _fh: object | None = None
    name: str = "hidraw"

    def open(self) -> "HidrawTransport":
        if not os.path.exists(self.path):
            raise TransportError(f"{self.path} does not exist")
        if not os.access(self.path, os.R_OK):
            raise TransportError(f"{self.path} is not readable by this user")
        self._fh = open(self.path, "rb", buffering=0)
        return self

    def read(self, size: int = 64, timeout: float | None = None) -> bytes:
        if self._fh is None:
            raise TransportError("transport is not open")
        return os.read(self._fh.fileno(), size)

    def write(self, data: bytes) -> int:
        if not self.allow_writes:
            raise WriteRefused("hidraw writes are disabled; the toolkit does not write to devices")
        raise WriteRefused("write support is intentionally not implemented")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def open_hidraw(path: str, *, allow_writes: bool = False) -> HidrawTransport:
    """Open a hidraw node read-only."""
    return HidrawTransport(path=path, allow_writes=allow_writes).open()


def replay(chunks: Iterable[bytes]) -> MockTransport:
    """Convenience: a mock transport preloaded with chunks."""
    transport = MockTransport()
    for chunk in chunks:
        transport.feed(chunk)
    return transport


def drive(transport: Transport, parser) -> list:
    """Feed every chunk of a transport through a parser until it is exhausted."""
    results = []
    while True:
        try:
            chunk = transport.read()
        except TransportError:
            break
        results.append(parser(chunk))
    return results
