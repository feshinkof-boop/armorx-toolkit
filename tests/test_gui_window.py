"""Qt widget-level regression tests for the Linux desktop configurator.

These exercise the real window object, so they need the optional GUI extra.
They are skipped - never failed - when PySide6 (or the system libraries Qt
needs, e.g. libEGL) cannot be loaded, which keeps the core test matrix
runnable on a bare interpreter.
"""
from __future__ import annotations

import os
import time

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from armorx import gui as gui_mod  # noqa: E402


def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _drain(app: QApplication, seconds: float = 3.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)


def _window() -> "gui_mod.ArmorXWindow":
    return gui_mod.ArmorXWindow()


async def _advertisement():
    return [{
        "address": "00:11:22:33:44:55",
        "name": "ARMOR-X Pro_11",
        "rssi": -40,
        "is_armorx": True,
        "candidate_reason": "local name starts with 'ARMOR-X Pro'",
        "manufacturer_data": {},
        "service_data": {},
        "service_uuids": [],
        "anonymous": False,
    }]


async def _boom():
    raise RuntimeError("worker exploded")


def test_worker_result_reaches_the_window_and_clears_the_busy_state():
    """A completed background task must deliver its result and stop the
    progress indicator: the task object must outlive its own queued signals.
    """
    app = _application()
    window = _window()
    try:
        received = []
        original = window._scan_result

        def capture(payload):
            received.append(payload)
            original(payload)

        window._task(_advertisement, capture, "Scanning…")
        assert window._busy is True
        assert window.scan_button.isEnabled() is False
        _drain(app)
        assert received, "the worker result never reached the GUI thread"
        assert window._busy is False, "the busy state never cleared"
        assert window.progress.isVisible() is False
        assert window.scan_button.isEnabled() is True
        assert window.read_button.isEnabled() is True
        assert window.scan_table.rowCount() == 1
    finally:
        window.close()


def test_worker_failure_reaches_the_window_and_clears_the_busy_state():
    app = _application()
    window = _window()
    try:
        errors = []
        window._task_error = errors.append
        window._task(_boom, lambda _payload: None, "Scanning…")
        _drain(app)
        assert errors and "worker exploded" in errors[0]
        assert window._busy is False
        assert window.scan_button.isEnabled() is True
    finally:
        window.close()


def test_clicks_are_ignored_while_a_task_is_running():
    app = _application()
    window = _window()
    try:
        started = []
        window.scan = lambda: started.append("scan")
        window._task(_advertisement, lambda _payload: None, "Scanning…")
        window.scan_button.click()
        assert started == []
        _drain(app)
        window.scan = lambda: started.append("scan")
        window.scan_button.click()
        assert started == ["scan"]
    finally:
        window.close()
