"""PySide6 macro timeline editor built on armorx.macro."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import macro as macro_mod
from .gui_macro_model import MacroDraft, MacroStep


class MacroTimelineEditor(QWidget):
    """Offline V41 macro editor. It never sends BLE/network traffic."""

    draftChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.draft = MacroDraft()
        self._refreshing = False
        self._build_ui()
        self.load_draft(self.draft)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)

        notice = QLabel(
            "Offline editor — this tab builds and validates the recovered V41 macro "
            "JSON format. It does not write macros to the controller or call the network."
        )
        notice.setWordWrap(True)
        outer.addWidget(notice)

        meta = QFormLayout()
        self.name_edit = QLineEdit()
        self.trigger_combo = QComboBox()
        self.trigger_combo.addItems(list(macro_mod.RUN_KEYS))
        self.mode_combo = QComboBox()
        for mode in ("long_press", "tap", "long_press_cycle", "tap_cycle"):
            self.mode_combo.addItem(mode.replace("_", " ").title(), mode)
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(0, 999999)
        self.repeat_spin.setSuffix(" ms")
        self.active_check = QCheckBox("Mark macro in use")
        meta.addRow("Name", self.name_edit)
        meta.addRow("Trigger", self.trigger_combo)
        meta.addRow("Execution", self.mode_combo)
        meta.addRow("Repeat time", self.repeat_spin)
        meta.addRow("", self.active_check)
        outer.addLayout(meta)

        splitter = QSplitter(Qt.Orientation.Vertical)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Step", "Keys / chord", "Hold (ms)", "Interval (ms)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        splitter.addWidget(self.table)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add step")
        self.remove_button = QPushButton("Remove")
        self.up_button = QPushButton("Move up")
        self.down_button = QPushButton("Move down")
        self.import_button = QPushButton("Open macro…")
        self.export_button = QPushButton("Export macro…")
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)
        buttons.addStretch(1)
        buttons.addWidget(self.import_button)
        buttons.addWidget(self.export_button)
        outer.addLayout(buttons)

        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)
        outer.addWidget(self.validation_label)

        self.name_edit.textChanged.connect(self._metadata_changed)
        self.trigger_combo.currentTextChanged.connect(self._metadata_changed)
        self.mode_combo.currentIndexChanged.connect(self._metadata_changed)
        self.repeat_spin.valueChanged.connect(self._metadata_changed)
        self.active_check.toggled.connect(self._metadata_changed)
        self.add_button.clicked.connect(self.add_step)
        self.remove_button.clicked.connect(self.remove_step)
        self.up_button.clicked.connect(lambda: self.move_step(-1))
        self.down_button.clicked.connect(lambda: self.move_step(1))
        self.import_button.clicked.connect(self.open_macro)
        self.export_button.clicked.connect(self.export_macro)
        self.table.itemSelectionChanged.connect(self._refresh_button_state)

    def _make_row(self, row: int, step: MacroStep) -> None:
        index_item = QTableWidgetItem(str(row + 1))
        index_item.setFlags(index_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 0, index_item)

        keys = QLineEdit(step.keys)
        keys.setPlaceholderText("A or B+RT")
        keys.editingFinished.connect(self._rows_changed)
        self.table.setCellWidget(row, 1, keys)

        duration = QSpinBox()
        duration.setRange(0, 999999)
        duration.setValue(step.duration)
        duration.valueChanged.connect(self._rows_changed)
        self.table.setCellWidget(row, 2, duration)

        interval = QSpinBox()
        interval.setRange(0, 999999)
        interval.setValue(step.interval)
        interval.valueChanged.connect(self._rows_changed)
        self.table.setCellWidget(row, 3, interval)

    def load_draft(self, draft: MacroDraft) -> None:
        self.draft = draft
        self._refreshing = True
        try:
            self.name_edit.setText(draft.name)
            self.trigger_combo.setCurrentText(draft.trigger)
            idx = self.mode_combo.findData(draft.mode)
            self.mode_combo.setCurrentIndex(max(0, idx))
            self.repeat_spin.setValue(draft.repeat_time)
            self.active_check.setChecked(draft.active)
            self.table.setRowCount(0)
            for step in draft.steps:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self._make_row(row, step)
        finally:
            self._refreshing = False
        self._refresh_validation()
        self._refresh_button_state()

    def _metadata_changed(self, *_args) -> None:
        if self._refreshing:
            return
        self.draft.name = self.name_edit.text()
        self.draft.trigger = self.trigger_combo.currentText()
        self.draft.mode = str(self.mode_combo.currentData())
        self.draft.repeat_time = self.repeat_spin.value()
        self.draft.active = self.active_check.isChecked()
        self._refresh_validation()
        self.draftChanged.emit()

    def _rows_changed(self, *_args) -> None:
        if self._refreshing:
            return
        steps: list[MacroStep] = []
        for row in range(self.table.rowCount()):
            keys = self.table.cellWidget(row, 1)
            duration = self.table.cellWidget(row, 2)
            interval = self.table.cellWidget(row, 3)
            steps.append(MacroStep(
                keys=keys.text(),
                duration=duration.value(),
                interval=interval.value(),
            ))
        self.draft.steps = steps
        self._refresh_validation()
        self.draftChanged.emit()

    def _refresh_validation(self) -> None:
        errors = self.draft.validate()
        self.export_button.setEnabled(not errors)
        self.add_button.setEnabled(len(self.draft.steps) < macro_mod.V41_MAX_STEPS)
        if errors:
            self.validation_label.setText("Not valid: " + " • ".join(errors))
            self.preview.setPlainText("")
            return
        obj = self.draft.to_object()
        self.validation_label.setText(
            f"Valid V41 macro: {len(self.draft.steps)} step(s), "
            f"trigger {self.draft.trigger}, mode {self.draft.mode}"
        )
        rows = macro_mod.decode_macro_json(obj["macroJson"])
        preview = {
            "macroName": obj["macroName"],
            "runKeyName": obj["runKeyName"],
            "isRepeat": obj["isRepeat"],
            "repeatTime": obj["repeatTime"],
            "inUse": obj["inUse"],
            "steps": [
                {
                    "keys": "+".join(row["keyNameListDecoded"]),
                    "hold_ms": row["duration"],
                    "interval_ms": row["interval"],
                    "ids": row["mapListDecoded"],
                }
                for row in rows
            ],
        }
        self.preview.setPlainText(json.dumps(preview, indent=2))

    def _selected_row(self) -> int:
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _refresh_button_state(self) -> None:
        row = self._selected_row()
        has = row >= 0
        self.remove_button.setEnabled(has and len(self.draft.steps) > 1)
        self.up_button.setEnabled(has and row > 0)
        self.down_button.setEnabled(has and row < len(self.draft.steps) - 1)

    def add_step(self) -> None:
        try:
            self._rows_changed()
            self.draft.add_step(MacroStep())
        except Exception as exc:
            QMessageBox.warning(self, "ArmorX macro", str(exc))
            return
        self.load_draft(self.draft)
        row = len(self.draft.steps) - 1
        self.table.selectRow(row)

    def remove_step(self) -> None:
        row = self._selected_row()
        if row < 0:
            return
        try:
            self._rows_changed()
            self.draft.remove_step(row)
        except Exception as exc:
            QMessageBox.warning(self, "ArmorX macro", str(exc))
            return
        self.load_draft(self.draft)
        self.table.selectRow(min(row, len(self.draft.steps) - 1))

    def move_step(self, delta: int) -> None:
        row = self._selected_row()
        if row < 0:
            return
        self._rows_changed()
        target = self.draft.move_step(row, delta)
        self.load_draft(self.draft)
        self.table.selectRow(target)

    def open_macro(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ArmorX macro", "", "JSON macro (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            draft = MacroDraft.load(path)
        except Exception as exc:
            QMessageBox.critical(self, "ArmorX macro", str(exc))
            return
        self.load_draft(draft)

    def export_macro(self) -> None:
        self._rows_changed()
        errors = self.draft.validate()
        if errors:
            QMessageBox.warning(self, "ArmorX macro", "\n".join(errors))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export ArmorX macro", "armorx-macro.json", "JSON macro (*.json)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        try:
            self.draft.export(path)
        except Exception as exc:
            QMessageBox.critical(self, "ArmorX macro", str(exc))
            return
        QMessageBox.information(self, "ArmorX macro", f"Exported {Path(path).name}")
