"""Theme-aware visual editors for recovered ArmorX stick/trigger bytes.

These widgets are deliberately evidence-bounded.  They visualize the recovered
byte fields in normalized 0..255 *byte space*; they do not claim that 128 means
50% physical travel or that the plotted stick curve is the firmware's exact
transfer function.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .gui_model import STICK_VISUAL_FIELDS, TRIGGER_VISUAL_FIELDS


def _clamp_byte(value: int) -> int:
    return max(0, min(255, int(value)))


class _ByteControl(QWidget):
    valueChanged = Signal(int)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(label)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 255)
        self.spin = QSpinBox()
        self.spin.setRange(0, 255)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.spin.valueChanged.connect(self.valueChanged)
        row.addWidget(self.label)
        row.addWidget(self.slider, 1)
        row.addWidget(self.spin)

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, value: int) -> None:
        value = _clamp_byte(value)
        old = self.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.blockSignals(True)
        try:
            self.slider.setValue(value)
            self.spin.setValue(value)
        finally:
            self.spin.blockSignals(False)
            self.slider.blockSignals(False)
            self.blockSignals(old)


class DeadzoneCanvas(QWidget):
    """Raw-byte ring preview for the two recovered deadzone fields."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.center_value = 0
        self.side_value = 0
        self.setMinimumSize(210, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_values(self, center: int, side: int) -> None:
        self.center_value = _clamp_byte(center)
        self.side_value = _clamp_byte(side)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        fg = palette.text().color()
        muted = palette.mid().color()

        painter.setPen(fg)
        painter.drawText(QRectF(0, 2, self.width(), 24),
                         Qt.AlignmentFlag.AlignHCenter, self.title)

        size = min(self.width() - 36, self.height() - 64)
        size = max(40, size)
        left = (self.width() - size) / 2
        top = 34
        outer = QRectF(left, top, size, size)
        painter.setPen(QPen(muted, 1))
        painter.drawEllipse(outer)
        center = outer.center()
        radius = size / 2

        for value, style in (
            (self.center_value, Qt.PenStyle.SolidLine),
            (self.side_value, Qt.PenStyle.DashLine),
        ):
            r = radius * (value / 255.0)
            painter.setPen(QPen(fg, 1.5, style))
            painter.drawEllipse(center, r, r)

        painter.setPen(fg)
        painter.drawText(
            QRectF(0, top + size + 3, self.width(), 22),
            Qt.AlignmentFlag.AlignHCenter,
            f"center byte {self.center_value}   •   side byte {self.side_value}",
        )


class CurveCanvas(QWidget):
    """Preview recovered control-point bytes without claiming exact firmware math."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.values = {
            "curve_mode": 0, "curve_ydivx": 0,
            "pt1_x": 0, "pt1_y": 0, "pt2_x": 0, "pt2_y": 0,
        }
        self.setMinimumSize(300, 230)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_values(self, values: dict[str, int]) -> None:
        for key in self.values:
            if key in values:
                self.values[key] = _clamp_byte(values[key])
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        fg = palette.text().color()
        muted = palette.mid().color()
        base = palette.base().color()

        painter.setPen(fg)
        painter.drawText(QRectF(0, 2, self.width(), 24),
                         Qt.AlignmentFlag.AlignHCenter, self.title)

        graph = QRectF(38, 34, max(80, self.width() - 58), max(90, self.height() - 82))
        painter.fillRect(graph, base)
        painter.setPen(QPen(muted, 1))
        painter.drawRect(graph)
        painter.drawLine(graph.bottomLeft(), graph.topRight())

        def point(x: int, y: int) -> QPointF:
            return QPointF(
                graph.left() + graph.width() * (_clamp_byte(x) / 255.0),
                graph.bottom() - graph.height() * (_clamp_byte(y) / 255.0),
            )

        p0 = graph.bottomLeft()
        p1 = point(self.values["pt1_x"], self.values["pt1_y"])
        p2 = point(self.values["pt2_x"], self.values["pt2_y"])
        p3 = graph.topRight()
        painter.setPen(QPen(fg, 2))
        painter.drawPolyline([p0, p1, p2, p3])

        guide_x = graph.left() + graph.width() * (self.values["curve_ydivx"] / 255.0)
        painter.setPen(QPen(muted, 1, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(guide_x, graph.top()), QPointF(guide_x, graph.bottom()))

        painter.setPen(QPen(fg, 5))
        painter.drawPoint(p1)
        painter.drawPoint(p2)

        painter.setPen(fg)
        painter.drawText(
            QRectF(0, graph.bottom() + 5, self.width(), 38),
            Qt.AlignmentFlag.AlignHCenter,
            f"mode byte {self.values['curve_mode']}   •   yDivx byte {self.values['curve_ydivx']}\n"
            f"P1 ({self.values['pt1_x']}, {self.values['pt1_y']})   •   "
            f"P2 ({self.values['pt2_x']}, {self.values['pt2_y']})",
        )


class StickVisualEditor(QGroupBox):
    fieldChanged = Signal(str, int)

    LABELS = (
        ("dz_center", "Center deadzone"),
        ("dz_side", "Side deadzone"),
        ("curve_mode", "Curve mode byte"),
        ("curve_ydivx", "YDivx byte"),
        ("pt1_x", "Point 1 X byte"),
        ("pt1_y", "Point 1 Y byte"),
        ("pt2_x", "Point 2 X byte"),
        ("pt2_y", "Point 2 Y byte"),
    )

    def __init__(self, side: str, parent=None):
        side = side.lower()
        if side not in STICK_VISUAL_FIELDS:
            raise ValueError("stick side must be left or right")
        super().__init__(f"{side.title()} stick", parent)
        self.side = side
        self.fields = STICK_VISUAL_FIELDS[side]
        layout = QVBoxLayout(self)
        previews = QHBoxLayout()
        self.deadzone = DeadzoneCanvas("Deadzone byte-space preview")
        self.curve = CurveCanvas("Recovered curve control-point preview")
        previews.addWidget(self.deadzone, 1)
        previews.addWidget(self.curve, 2)
        layout.addLayout(previews)

        note = QLabel(
            "Visualization uses raw 0–255 config bytes. It is not a calibrated "
            "physical percentage or an exact firmware transfer-function simulator."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        form = QFormLayout()
        self.controls: dict[str, _ByteControl] = {}
        for role, label in self.LABELS:
            control = _ByteControl(label)
            field = self.fields[role]
            control.valueChanged.connect(
                lambda value, f=field: self.fieldChanged.emit(f, value)
            )
            self.controls[role] = control
            form.addRow(control)
        layout.addLayout(form)

    def set_values(self, values: dict[str, int]) -> None:
        for role, control in self.controls.items():
            control.setValue(values.get(role, 0))
        self.deadzone.set_values(values.get("dz_center", 0), values.get("dz_side", 0))
        self.curve.set_values(values)


class TriggerVisualEditor(QGroupBox):
    fieldChanged = Signal(str, int)

    def __init__(self, side: str, parent=None):
        side = side.lower()
        if side not in TRIGGER_VISUAL_FIELDS:
            raise ValueError("trigger side must be left or right")
        super().__init__(f"{side.title()} trigger", parent)
        self.side = side
        self.fields = TRIGGER_VISUAL_FIELDS[side]
        layout = QVBoxLayout(self)
        self.deadzone = DeadzoneCanvas("Trigger deadzone byte-space preview")
        layout.addWidget(self.deadzone)
        note = QLabel(
            "Rings represent the two recovered raw deadzone bytes only; firmware "
            "travel scaling is not assumed."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.center = _ByteControl("Center deadzone")
        self.side_control = _ByteControl("Side deadzone")
        self.center.valueChanged.connect(
            lambda value: self.fieldChanged.emit(self.fields["dz_center"], value)
        )
        self.side_control.valueChanged.connect(
            lambda value: self.fieldChanged.emit(self.fields["dz_side"], value)
        )
        layout.addWidget(self.center)
        layout.addWidget(self.side_control)

    def set_values(self, values: dict[str, int]) -> None:
        self.center.setValue(values.get("dz_center", 0))
        self.side_control.setValue(values.get("dz_side", 0))
        self.deadzone.set_values(values.get("dz_center", 0), values.get("dz_side", 0))
