"""PySide6 desktop shell for ArmorX Toolkit.

Milestone 1 is deliberately conservative: it scans BLE, reads the live
configuration, opens existing configs, edits already-decoded fields, previews
the exact diff, and exports a validated target.  Live Apply/Rollback remain in
the proven CLI for this first GUI milestone; the desktop write transaction will
be wired only after the GUI confirmation/backup workflow is covered by tests.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Callable

from . import __version__
from . import config as config_mod
from . import live as live_mod
from .gui_model import GuiConfigSession, QUICK_FIELDS, REAR_BUTTONS

try:  # optional dependency: importing armorx itself must not require Qt
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot, Qt
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QFileDialog,
        QFormLayout,
        QGridLayout,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTabWidget,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
    QT_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised by console smoke manually
    QT_AVAILABLE = False


async def _read_live(address: str) -> dict[str, Any]:
    transport = live_mod.BleakLiveTransport(address=address)
    await transport.connect()
    try:
        identity = await live_mod.read_identity(transport)
        details: dict[str, Any] = {}
        image = await live_mod.read_config(transport, report=details)
        return {"identity": identity, "image": image, "details": details}
    finally:
        await transport.close()


async def _scan_live(seconds: float = 8.0) -> list[dict[str, Any]]:
    return await live_mod.scan_ble(seconds=seconds)


if QT_AVAILABLE:
    class TaskSignals(QObject):
        result = Signal(object)
        error = Signal(str)
        finished = Signal()


    class AsyncTask(QRunnable):
        def __init__(self, factory: Callable[[], Any]):
            super().__init__()
            self.factory = factory
            self.signals = TaskSignals()

        @Slot()
        def run(self) -> None:
            try:
                result = asyncio.run(self.factory())
            except Exception as exc:
                self.signals.error.emit(str(exc))
            else:
                self.signals.result.emit(result)
            finally:
                self.signals.finished.emit()


    class ArmorXWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(f"ArmorX Toolkit {__version__} — Linux")
            self.resize(1050, 720)
            self.pool = QThreadPool.globalInstance()
            self.session: GuiConfigSession | None = None
            self.identity: dict[str, Any] = {}
            self._updating = False
            self._build_ui()
            self._set_loaded(False)

        def _build_ui(self) -> None:
            root = QWidget()
            outer = QVBoxLayout(root)

            device_box = QGroupBox("Device")
            device = QGridLayout(device_box)
            self.address = QLineEdit()
            self.address.setPlaceholderText("BLE address")
            self.scan_button = QPushButton("Scan")
            self.read_button = QPushButton("Read live config")
            self.open_button = QPushButton("Open config…")
            self.device_state = QLabel("No configuration loaded")
            device.addWidget(QLabel("Address"), 0, 0)
            device.addWidget(self.address, 0, 1)
            device.addWidget(self.scan_button, 0, 2)
            device.addWidget(self.read_button, 0, 3)
            device.addWidget(self.open_button, 0, 4)
            device.addWidget(self.device_state, 1, 0, 1, 5)
            outer.addWidget(device_box)

            self.scan_table = QTableWidget(0, 4)
            self.scan_table.setHorizontalHeaderLabels(
                ["Name", "Address", "RSSI", "Candidate reason"]
            )
            self.scan_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            self.scan_table.setMaximumHeight(150)
            outer.addWidget(self.scan_table)

            self.tabs = QTabWidget()
            outer.addWidget(self.tabs, 1)

            self.summary = QTextEdit()
            self.summary.setReadOnly(True)
            self.tabs.addTab(self.summary, "Summary")

            rear_page = QWidget()
            rear_layout = QFormLayout(rear_page)
            self.map_boxes: dict[str, QComboBox] = {}
            canonical = [
                (code, name) for code, name in sorted(config_mod.CANONICAL_KEY_NAMES.items())
            ]
            for source in REAR_BUTTONS:
                combo = QComboBox()
                for code, name in canonical:
                    combo.addItem(f"{name} ({code})", code)
                combo.currentIndexChanged.connect(
                    lambda _index, s=source: self._map_changed(s)
                )
                rear_layout.addRow(f"{source} maps to", combo)
                self.map_boxes[source] = combo
            self.tabs.addTab(rear_page, "Rear buttons")

            tuning_page = QWidget()
            tuning_layout = QFormLayout(tuning_page)
            self.field_boxes: dict[str, QSpinBox] = {}
            for field in QUICK_FIELDS:
                spin = QSpinBox()
                spin.setRange(0, 255)
                spin.valueChanged.connect(
                    lambda value, f=field: self._field_changed(f, value)
                )
                tuning_layout.addRow(field, spin)
                self.field_boxes[field] = spin
            self.tabs.addTab(tuning_page, "Sticks / triggers / turbo")

            self.diff_table = QTableWidget(0, 5)
            self.diff_table.setHorizontalHeaderLabels(
                ["Offset", "Class", "Field", "Before", "After"]
            )
            self.diff_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            self.tabs.addTab(self.diff_table, "Changes")

            actions = QHBoxLayout()
            self.reset_button = QPushButton("Reset changes")
            self.export_button = QPushButton("Export target…")
            self.apply_button = QPushButton("Apply & Verify")
            self.apply_button.setEnabled(False)
            self.apply_button.setToolTip(
                "Milestone 1 keeps live writes in the proven CLI; GUI Apply lands next."
            )
            actions.addWidget(self.reset_button)
            actions.addStretch(1)
            actions.addWidget(self.export_button)
            actions.addWidget(self.apply_button)
            outer.addLayout(actions)

            self.setCentralWidget(root)
            self.setStatusBar(QStatusBar())

            self.scan_button.clicked.connect(self.scan)
            self.read_button.clicked.connect(self.read_live)
            self.open_button.clicked.connect(self.open_config)
            self.scan_table.cellDoubleClicked.connect(self.select_scan_row)
            self.reset_button.clicked.connect(self.reset_changes)
            self.export_button.clicked.connect(self.export_target)

        def _set_busy(self, busy: bool, text: str = "") -> None:
            self.scan_button.setEnabled(not busy)
            self.read_button.setEnabled(not busy)
            self.open_button.setEnabled(not busy)
            if text:
                self.statusBar().showMessage(text)

        def _set_loaded(self, loaded: bool) -> None:
            self.tabs.setEnabled(loaded)
            self.reset_button.setEnabled(loaded)
            self.export_button.setEnabled(loaded)

        def _task(self, factory, on_result, message: str) -> None:
            self._set_busy(True, message)
            task = AsyncTask(factory)
            task.signals.result.connect(on_result)
            task.signals.error.connect(self._task_error)
            task.signals.finished.connect(lambda: self._set_busy(False))
            self.pool.start(task)

        def _task_error(self, message: str) -> None:
            self.statusBar().showMessage("Operation failed")
            QMessageBox.critical(self, "ArmorX", message)

        @Slot()
        def scan(self) -> None:
            self._task(lambda: _scan_live(8.0), self._scan_result,
                       "Scanning for BLE devices…")

        @Slot(object)
        def _scan_result(self, devices: list[dict[str, Any]]) -> None:
            self.scan_table.setRowCount(len(devices))
            for row, item in enumerate(devices):
                reason = item.get("candidate_reason") or (
                    "ARMOR-X name" if item.get("is_armorx") else ""
                )
                values = [
                    item.get("name") or "(anonymous)",
                    item.get("address") or "",
                    "" if item.get("rssi") is None else str(item.get("rssi")),
                    reason,
                ]
                for col, value in enumerate(values):
                    self.scan_table.setItem(row, col, QTableWidgetItem(value))
            self.statusBar().showMessage(
                f"Scan complete: {len(devices)} advertisement(s)"
            )

        @Slot(int, int)
        def select_scan_row(self, row: int, _column: int) -> None:
            item = self.scan_table.item(row, 1)
            if item:
                self.address.setText(item.text())

        @Slot()
        def read_live(self) -> None:
            address = self.address.text().strip()
            if not address:
                QMessageBox.warning(self, "ArmorX", "Choose or enter a BLE address first.")
                return
            self._task(lambda: _read_live(address), self._read_result,
                       "Reading live ARMOR-X configuration…")

        @Slot(object)
        def _read_result(self, payload: dict[str, Any]) -> None:
            self.identity = dict(payload.get("identity") or {})
            self._load_session(GuiConfigSession.from_image(payload["image"]))
            fragments = (payload.get("details") or {}).get("fragment_count")
            self.statusBar().showMessage(
                f"Live configuration loaded ({fragments or '?'} D6 fragments)"
            )

        @Slot()
        def open_config(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open ArmorX configuration", "",
                "ArmorX configs (*.json *.bin);;All files (*)"
            )
            if not path:
                return
            try:
                session = GuiConfigSession.from_file(path)
            except Exception as exc:
                QMessageBox.critical(self, "ArmorX", str(exc))
                return
            self.identity = {}
            self._load_session(session)
            self.statusBar().showMessage(f"Opened {Path(path).name}")

        def _load_session(self, session: GuiConfigSession) -> None:
            self.session = session
            self._set_loaded(True)
            self._refresh_controls()

        def _refresh_controls(self) -> None:
            if self.session is None:
                return
            self._updating = True
            try:
                for source, combo in self.map_boxes.items():
                    target = self.session.map_target(source)["target_id"]
                    index = combo.findData(target)
                    combo.setCurrentIndex(index if index >= 0 else 0)
                for field, spin in self.field_boxes.items():
                    spin.setValue(self.session.byte_field(field))
            finally:
                self._updating = False
            self._refresh_summary()
            self._refresh_diff()

        def _refresh_summary(self) -> None:
            if self.session is None:
                return
            v = self.session.validation()
            ident = self.identity
            lines = [
                f"Model: {ident.get('model') or 'offline / unknown'}",
                f"Firmware: {ident.get('firmware') or 'offline / unknown'}",
                f"Battery: {ident.get('battery') if ident.get('battery') is not None else 'n/a'}",
                "",
                f"Length: {v['actual_length']} (declared {v['declared_length']})",
                f"CRC: {v['stored_crc_hex']} (valid: {v['crc_matches']})",
                f"Changed from baseline: {self.session.changed}",
                "",
                self.session.diff_summary(),
            ]
            self.summary.setPlainText("\n".join(lines))
            self.device_state.setText(
                "Configuration loaded" + (" — modified" if self.session.changed else "")
            )

        def _refresh_diff(self) -> None:
            if self.session is None:
                return
            changes = self.session.diff()["changes"]
            self.diff_table.setRowCount(len(changes))
            for row, change in enumerate(changes):
                values = [
                    str(change["offset"]),
                    change.get("classification") or "",
                    change.get("field") or change.get("region") or "",
                    str(change["before"]),
                    str(change["after"]),
                ]
                for col, value in enumerate(values):
                    self.diff_table.setItem(row, col, QTableWidgetItem(value))

        def _map_changed(self, source: str) -> None:
            if self._updating or self.session is None:
                return
            combo = self.map_boxes[source]
            self.session.set_map(source, int(combo.currentData()))
            self._refresh_summary()
            self._refresh_diff()

        def _field_changed(self, field: str, value: int) -> None:
            if self._updating or self.session is None:
                return
            self.session.set_byte_field(field, value)
            self._refresh_summary()
            self._refresh_diff()

        @Slot()
        def reset_changes(self) -> None:
            if self.session is None:
                return
            self.session.reset()
            self._refresh_controls()
            self.statusBar().showMessage("Changes reset to the loaded baseline")

        @Slot()
        def export_target(self) -> None:
            if self.session is None:
                return
            path, selected = QFileDialog.getSaveFileName(
                self, "Export validated target", "armorx-target.json",
                "JSON (*.json);;Binary (*.bin)"
            )
            if not path:
                return
            try:
                if selected.startswith("Binary") or path.lower().endswith(".bin"):
                    self.session.export_bin(path)
                else:
                    if not path.lower().endswith(".json"):
                        path += ".json"
                    self.session.export_json(path)
            except Exception as exc:
                QMessageBox.critical(self, "ArmorX", str(exc))
                return
            self.statusBar().showMessage(f"Exported {Path(path).name}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="armorx-gui",
        description="ArmorX Toolkit Linux desktop configurator (v0.5 development)",
    )
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    if not QT_AVAILABLE:
        print(
            'armorx-gui requires the optional GUI dependencies. '
            'Install with: python -m pip install -e ".[gui]"',
            file=sys.stderr,
        )
        return 2
    app = QApplication(sys.argv[:1])
    app.setApplicationName("ArmorX Toolkit")
    window = ArmorXWindow()
    window.show()
    return int(app.exec())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
