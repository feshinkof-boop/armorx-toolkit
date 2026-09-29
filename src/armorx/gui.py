"""PySide6 desktop configurator for ArmorX Toolkit v0.5 development.

The desktop reuses the released v0.4 live backend. It never implements the wire
protocol itself: live reads, guarded apply and rollback delegate to
armorx.live through armorx.gui_workflow.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import __version__
from . import config as config_mod
from . import confirm as confirm_mod
from . import gui_workflow as workflow
from .gui_model import (
    GUI_EDITABLE_FIELDS,
    GuiConfigSession,
    QUICK_FIELDS,
    REAR_BUTTONS,
)

try:
    from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFileDialog, QFormLayout, QGridLayout,
        QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
        QListWidget, QMainWindow, QMessageBox, QProgressBar, QPushButton,
        QSpinBox, QStatusBar, QTabWidget, QTableWidget, QTableWidgetItem,
        QTextEdit, QVBoxLayout, QWidget,
    )
    from .gui_visual import StickVisualEditor, TriggerVisualEditor
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


async def _scan_live(seconds: float = 8.0) -> list[dict[str, Any]]:
    from . import live as live_mod
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


    @dataclass
    class _ConfirmationTicket:
        message: str
        title: str
        event: threading.Event
        result: confirm_mod.ConfirmationResult | None = None


    class QtConfirmationBridge(QObject):
        requested = Signal(object)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.requested.connect(self._show)

        def __call__(self, message: str, title: str):
            ticket = _ConfirmationTicket(message, title, threading.Event())
            self.requested.emit(ticket)
            if not ticket.event.wait(900):
                return confirm_mod.ConfirmationResult(
                    None, "qt-dialog", "confirmation timed out"
                )
            return ticket.result or confirm_mod.ConfirmationResult(
                None, "qt-dialog", "dialog returned no result"
            )

        @Slot(object)
        def _show(self, ticket: _ConfirmationTicket) -> None:
            try:
                box = QMessageBox()
                box.setWindowTitle(ticket.title)
                box.setIcon(QMessageBox.Icon.Warning)
                box.setText("Review this controller configuration change.")
                box.setInformativeText(ticket.message)
                apply_button = box.addButton("APPLY", QMessageBox.ButtonRole.AcceptRole)
                box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                box.exec()
                accepted = box.clickedButton() is apply_button
                ticket.result = confirm_mod.ConfirmationResult(
                    accepted, "qt-dialog",
                    "Qt dialog accepted" if accepted else "Qt dialog declined",
                )
            finally:
                ticket.event.set()


    class ArmorXWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(f"ArmorX Toolkit {__version__} — Linux")
            self.resize(1120, 760)
            self.pool = QThreadPool.globalInstance()
            # Strong references to in-flight background tasks. QThreadPool
            # drops its own reference to a runnable as soon as run() returns;
            # a collected task takes its signal object with it, and Qt then
            # silently discards a still-queued result/finished delivery. The
            # visible symptom is a window stuck on "busy": the progress
            # indicator never hides and every action button stays disabled.
            self._tasks: set[Any] = set()
            self.session: GuiConfigSession | None = None
            self.identity: dict[str, Any] = {}
            self._updating = False
            self._busy = False
            self.confirm_bridge = QtConfirmationBridge(self)
            self.profile_store = workflow.ProfileStore()
            self.last_backup_prefix: Path | None = None
            self.pending_backup_prefix: Path | None = None
            self._build_ui()
            self._set_loaded(False)
            self.refresh_profiles()

        def _build_ui(self) -> None:
            root = QWidget()
            outer = QVBoxLayout(root)
            device_box = QGroupBox("Device")
            device = QGridLayout(device_box)
            self.address = QLineEdit()
            self.address.setPlaceholderText("BLE address")
            self.address.textChanged.connect(lambda: self._refresh_action_state())
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
            canonical = [(code, name) for code, name in
                         sorted(config_mod.CANONICAL_KEY_NAMES.items())]
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

            stick_page = QWidget()
            stick_layout = QHBoxLayout(stick_page)
            self.stick_editors = {
                "left": StickVisualEditor("left"),
                "right": StickVisualEditor("right"),
            }
            for editor in self.stick_editors.values():
                editor.fieldChanged.connect(self._visual_field_changed)
                stick_layout.addWidget(editor, 1)
            self.tabs.addTab(stick_page, "Stick visuals")

            trigger_page = QWidget()
            trigger_layout = QHBoxLayout(trigger_page)
            self.trigger_editors = {
                "left": TriggerVisualEditor("left"),
                "right": TriggerVisualEditor("right"),
            }
            for editor in self.trigger_editors.values():
                editor.fieldChanged.connect(self._visual_field_changed)
                trigger_layout.addWidget(editor, 1)
            self.tabs.addTab(trigger_page, "Trigger visuals")

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
            self.tabs.addTab(tuning_page, "Advanced bytes")

            self.diff_table = QTableWidget(0, 5)
            self.diff_table.setHorizontalHeaderLabels(
                ["Offset", "Class", "Field", "Before", "After"]
            )
            self.diff_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.Stretch
            )
            self.tabs.addTab(self.diff_table, "Changes")

            profiles = QWidget()
            profile_layout = QVBoxLayout(profiles)
            self.profile_list = QListWidget()
            row = QHBoxLayout()
            self.profile_save = QPushButton("Save current as profile…")
            self.profile_load = QPushButton("Load")
            self.profile_delete = QPushButton("Delete")
            row.addWidget(self.profile_save)
            row.addWidget(self.profile_load)
            row.addWidget(self.profile_delete)
            profile_layout.addWidget(self.profile_list)
            profile_layout.addLayout(row)
            self.tabs.addTab(profiles, "Profiles")

            actions = QHBoxLayout()
            self.reset_button = QPushButton("Reset changes")
            self.export_button = QPushButton("Export target…")
            self.rollback_button = QPushButton("Rollback last backup")
            self.apply_button = QPushButton("Apply & Verify")
            actions.addWidget(self.reset_button)
            actions.addStretch(1)
            actions.addWidget(self.export_button)
            actions.addWidget(self.rollback_button)
            actions.addWidget(self.apply_button)
            outer.addLayout(actions)

            self.progress = QProgressBar()
            self.progress.setRange(0, 0)
            self.progress.hide()
            outer.addWidget(self.progress)
            self.setCentralWidget(root)
            self.setStatusBar(QStatusBar())

            self.scan_button.clicked.connect(self.scan)
            self.read_button.clicked.connect(self.read_live)
            self.open_button.clicked.connect(self.open_config)
            self.scan_table.cellDoubleClicked.connect(self.select_scan_row)
            self.reset_button.clicked.connect(self.reset_changes)
            self.export_button.clicked.connect(self.export_target)
            self.apply_button.clicked.connect(self.apply_and_verify)
            self.rollback_button.clicked.connect(self.rollback_last_backup)
            self.profile_save.clicked.connect(self.save_profile)
            self.profile_load.clicked.connect(self.load_profile)
            self.profile_delete.clicked.connect(self.delete_profile)
            self.profile_list.itemDoubleClicked.connect(lambda _item: self.load_profile())

        def _set_busy(self, busy: bool, text: str = "") -> None:
            self._busy = busy
            self.scan_button.setEnabled(not busy)
            self.read_button.setEnabled(not busy)
            self.open_button.setEnabled(not busy)
            self.progress.setVisible(busy)
            if text:
                self.statusBar().showMessage(text)
            self._refresh_action_state()

        def _set_loaded(self, loaded: bool) -> None:
            # Keep the tab widget available even before a config is loaded so a
            # saved local profile can be opened from a fresh application start.
            self.tabs.setEnabled(True)
            self.reset_button.setEnabled(loaded)
            self.export_button.setEnabled(loaded)
            self.profile_save.setEnabled(loaded)
            self._refresh_action_state()

        def _refresh_action_state(self) -> None:
            has_session = self.session is not None
            has_address = bool(self.address.text().strip())
            self.apply_button.setEnabled(has_session and has_address and not self._busy)
            self.rollback_button.setEnabled(
                self.last_backup_prefix is not None and has_address and not self._busy
            )

        def _task(self, factory, on_result, message: str) -> None:
            self._set_busy(True, message)
            task = AsyncTask(factory)
            task.signals.result.connect(on_result)
            task.signals.error.connect(self._task_error)
            task.signals.finished.connect(lambda: self._finish_task(task))
            self._tasks.add(task)
            self.pool.start(task)

        def _finish_task(self, task: "AsyncTask") -> None:
            """Release a finished task and stop the progress indicator."""
            self._tasks.discard(task)
            self._set_busy(False)

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
            self._task(lambda: workflow.read_live_config(address), self._read_result,
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
                for side, editor in self.stick_editors.items():
                    editor.set_values(self.session.stick_visual(side))
                for side, editor in self.trigger_editors.items():
                    editor.set_values(self.session.trigger_visual(side))
            finally:
                self._updating = False
            self._refresh_summary()
            self._refresh_diff()
            self._refresh_action_state()

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
                f"Changed from loaded baseline: {self.session.changed}",
                "",
                self.session.diff_summary(),
            ]
            if self.last_backup_prefix is not None:
                lines.extend(["", f"Last rollback backup: {self.last_backup_prefix.name}"])
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
                    str(change["offset"]), change.get("classification") or "",
                    change.get("field") or change.get("region") or "",
                    str(change["before"]), str(change["after"]),
                ]
                for col, value in enumerate(values):
                    self.diff_table.setItem(row, col, QTableWidgetItem(value))

        def _map_changed(self, source: str) -> None:
            if self._updating or self.session is None:
                return
            self.session.set_map(source, int(self.map_boxes[source].currentData()))
            self._refresh_summary()
            self._refresh_diff()

        def _field_changed(self, field: str, value: int) -> None:
            if self._updating or self.session is None:
                return
            self.session.set_byte_field(field, value)
            self._refresh_controls()

        def _visual_field_changed(self, field: str, value: int) -> None:
            if self._updating or self.session is None:
                return
            if field not in GUI_EDITABLE_FIELDS:
                QMessageBox.critical(self, "ArmorX", f"Unsupported visual field: {field}")
                return
            self.session.set_byte_field(field, value)
            self._refresh_controls()

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

        @Slot()
        def apply_and_verify(self) -> None:
            if self.session is None:
                return
            address = self.address.text().strip()
            if not address:
                QMessageBox.warning(self, "ArmorX", "Choose or enter a BLE address first.")
                return
            prefix = workflow.default_backup_prefix()
            self.pending_backup_prefix = prefix
            target = bytes(self.session.working)
            self._task(
                lambda: workflow.apply_target(
                    address, target, backup_prefix=prefix,
                    confirmer=self.confirm_bridge,
                ),
                self._apply_result,
                "Applying configuration and verifying two read-backs…",
            )

        @Slot(object)
        def _apply_result(self, report: dict[str, Any]) -> None:
            status = report.get("status")
            # Once a real pre-write backup exists, keep it reachable even when
            # the later D7/verification stage fails. The rollback backend will
            # still refuse an unrelated/ambiguous live state by default.
            backup_available = False
            if self.pending_backup_prefix is not None:
                backup_available = self.pending_backup_prefix.with_suffix(".bin").exists()
                if backup_available:
                    self.last_backup_prefix = self.pending_backup_prefix

            if status in {"APPLIED", "NO_CHANGE"}:
                if self.session is not None:
                    self.session.accept_working_as_baseline()
                    self._refresh_controls()
                QMessageBox.information(
                    self, "ArmorX",
                    f"Apply result: {status}\n\nFinal SHA-256: "
                    f"{report.get('final_sha256') or report.get('target', {}).get('sha256', 'n/a')}"
                )
            else:
                reason = report.get("failure_reason") or report.get("refusal_reason") or (
                    "The write did not complete successfully."
                )
                recovery = (
                    "\n\nA verified pre-write backup is available through "
                    "'Rollback last backup' if the backend classifies the live state as safe."
                    if backup_available else ""
                )
                QMessageBox.warning(
                    self, "ArmorX — Apply not completed",
                    f"Status: {status}\n\n{reason}\n\nNo automatic retry was performed."
                    f"{recovery}"
                )
            self.pending_backup_prefix = None
            self._refresh_summary()
            self._refresh_action_state()

        @Slot()
        def rollback_last_backup(self) -> None:
            if self.last_backup_prefix is None:
                return
            address = self.address.text().strip()
            if not address:
                QMessageBox.warning(self, "ArmorX", "Choose or enter a BLE address first.")
                return
            prefix = self.last_backup_prefix
            self._task(
                lambda: workflow.rollback_backup(
                    address, prefix, confirmer=self.confirm_bridge
                ),
                self._rollback_result,
                "Restoring the last pre-write backup and verifying…",
            )

        @Slot(object)
        def _rollback_result(self, report: dict[str, Any]) -> None:
            status = report.get("status")
            if status in {"RESTORED", "NO_CHANGE"}:
                try:
                    image = workflow.backup_image(self.last_backup_prefix)
                    self._load_session(GuiConfigSession.from_image(image))
                except Exception as exc:
                    QMessageBox.warning(
                        self, "ArmorX",
                        f"Rollback succeeded but the UI could not reopen the backup: {exc}"
                    )
                else:
                    QMessageBox.information(
                        self, "ArmorX",
                        f"Rollback result: {status}\nOriginal backup is active."
                    )
            else:
                reason = report.get("failure_reason") or report.get("refusal_reason") or (
                    "Rollback did not complete successfully."
                )
                QMessageBox.warning(
                    self, "ArmorX — Rollback not completed",
                    f"Status: {status}\n\n{reason}\n\nNo automatic retry was performed."
                )
            self._refresh_summary()
            self._refresh_action_state()

        def refresh_profiles(self) -> None:
            self.profile_list.clear()
            try:
                rows = self.profile_store.list()
            except Exception as exc:
                self.statusBar().showMessage(f"Could not read profiles: {exc}")
                return
            for row in rows:
                self.profile_list.addItem(row["name"])

        @Slot()
        def save_profile(self) -> None:
            if self.session is None:
                return
            name, ok = QInputDialog.getText(self, "Save profile", "Profile name")
            if not ok or not name.strip():
                return
            try:
                self.profile_store.save(
                    name, self.session.working,
                    metadata={
                        "model": self.identity.get("model"),
                        "firmware": self.identity.get("firmware"),
                    },
                )
            except Exception as exc:
                QMessageBox.critical(self, "ArmorX", str(exc))
                return
            self.refresh_profiles()
            self.statusBar().showMessage(f"Saved profile {name.strip()}")

        @Slot()
        def load_profile(self) -> None:
            item = self.profile_list.currentItem()
            if item is None:
                return
            try:
                image = self.profile_store.load(item.text())
            except Exception as exc:
                QMessageBox.critical(self, "ArmorX", str(exc))
                return
            self.identity = {}
            self._load_session(GuiConfigSession.from_image(image))
            self.statusBar().showMessage(f"Loaded profile {item.text()}")

        @Slot()
        def delete_profile(self) -> None:
            item = self.profile_list.currentItem()
            if item is None:
                return
            answer = QMessageBox.question(
                self, "Delete profile", f"Delete local profile '{item.text()}'?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                self.profile_store.delete(item.text())
            except Exception as exc:
                QMessageBox.critical(self, "ArmorX", str(exc))
                return
            self.refresh_profiles()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="armorx-gui",
        description="ArmorX Toolkit Linux desktop configurator (v0.5 development)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
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


if __name__ == "__main__":
    raise SystemExit(main())
