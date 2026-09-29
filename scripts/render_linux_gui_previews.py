#!/usr/bin/env python3
"""Render deterministic, address-free Linux GUI preview assets."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from armorx import config as config_mod
from armorx.gui import ArmorXWindow
from armorx.gui_macro_model import MacroDraft, MacroStep
from armorx.gui_model import GuiConfigSession, STICK_VISUAL_FIELDS, TRIGGER_VISUAL_FIELDS


OUT = Path("docs/assets/linux/v0.5.0")


def _tab_index(window: ArmorXWindow, label: str) -> int:
    for index in range(window.tabs.count()):
        if window.tabs.tabText(index) == label:
            return index
    raise RuntimeError(f"tab not found: {label}")


def _save_tab(app: QApplication, window: ArmorXWindow, label: str, filename: str) -> None:
    index = _tab_index(window, label)
    window.tabs.setCurrentIndex(index)
    app.processEvents()
    page = window.tabs.widget(index)
    pixmap = page.grab()
    if pixmap.isNull():
        raise RuntimeError(f"failed to render {label}")
    pixmap = pixmap.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation)
    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / (Path(filename).stem + ".png")
    webp = OUT / filename
    if not pixmap.save(str(png), "PNG"):
        raise RuntimeError(f"failed to save {png}")
    with Image.open(png) as image:
        image.save(webp, "WEBP", quality=88, method=6)
    png.unlink()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    window = ArmorXWindow()
    window.resize(1180, 820)

    session = GuiConfigSession.from_image(bytes(config_mod.fresh()))
    examples = {
        STICK_VISUAL_FIELDS["left"]["dz_center"]: 28,
        STICK_VISUAL_FIELDS["left"]["dz_side"]: 210,
        STICK_VISUAL_FIELDS["left"]["curve_mode"]: 1,
        STICK_VISUAL_FIELDS["left"]["curve_ydivx"]: 128,
        STICK_VISUAL_FIELDS["left"]["pt1_x"]: 65,
        STICK_VISUAL_FIELDS["left"]["pt1_y"]: 48,
        STICK_VISUAL_FIELDS["left"]["pt2_x"]: 190,
        STICK_VISUAL_FIELDS["left"]["pt2_y"]: 220,
        STICK_VISUAL_FIELDS["right"]["dz_center"]: 18,
        STICK_VISUAL_FIELDS["right"]["dz_side"]: 225,
        STICK_VISUAL_FIELDS["right"]["curve_mode"]: 0,
        STICK_VISUAL_FIELDS["right"]["curve_ydivx"]: 110,
        STICK_VISUAL_FIELDS["right"]["pt1_x"]: 72,
        STICK_VISUAL_FIELDS["right"]["pt1_y"]: 58,
        STICK_VISUAL_FIELDS["right"]["pt2_x"]: 182,
        STICK_VISUAL_FIELDS["right"]["pt2_y"]: 215,
        TRIGGER_VISUAL_FIELDS["left"]["dz_center"]: 12,
        TRIGGER_VISUAL_FIELDS["left"]["dz_side"]: 238,
        TRIGGER_VISUAL_FIELDS["right"]["dz_center"]: 20,
        TRIGGER_VISUAL_FIELDS["right"]["dz_side"]: 232,
    }
    for field, value in examples.items():
        session.set_byte_field(field, value)
    window._load_session(session)

    window.macro_editor.load_draft(MacroDraft(
        name="Example Combo",
        trigger="M1",
        mode="tap_cycle",
        repeat_time=200,
        steps=[
            MacroStep("A", 80, 50),
            MacroStep("X", 100, 60),
            MacroStep("B+RT", 120, 70),
            MacroStep("Y", 90, 100),
        ],
    ))

    window.show()
    app.processEvents()

    _save_tab(app, window, "Stick visuals", "05-stick-visuals.webp")
    _save_tab(app, window, "Trigger visuals", "06-trigger-visuals.webp")
    _save_tab(app, window, "Macros", "07-macro-timeline.webp")

    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
