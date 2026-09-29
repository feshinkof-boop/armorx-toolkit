"""Pure-Python state model for the ArmorX Linux desktop UI.

The GUI deliberately keeps editing logic outside Qt.  This module owns the
baseline/working image, config validation, canonical CRC regeneration and exact
diffs.  It can therefore be tested without a display server or PySide6.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config as config_mod
from . import diff as diff_mod


REAR_BUTTONS = ("M1", "M2", "M3", "M4")
REAR_BUTTON_INDEXES = {
    name: config_mod.MAP_KEY_CODES[name] for name in REAR_BUTTONS
}

# Milestone 1 intentionally exposes the fields that already have stable byte
# semantics in armorx.config. More complex curve widgets come later.
QUICK_FIELDS = (
    "triggerMode",
    "triggerLeftDZCenter",
    "triggerLeftDZSide",
    "triggerRightDZCenter",
    "triggerRightDZSide",
    "stickLeftDZCenter",
    "stickLeftDZSide",
    "stickRightDZCenter",
    "stickRightDZSide",
    "sensorMode",
    "turboSpeedIdx",
)


def _validated(image: bytes | bytearray | list[int]) -> bytes:
    data = bytes(image)
    if len(data) != config_mod.CONFIG_LEN:
        raise ValueError(
            f"configuration is {len(data)} bytes, expected {config_mod.CONFIG_LEN}"
        )
    result = config_mod.validate(list(data))
    if result["declared_length"] != config_mod.CONFIG_LEN:
        raise ValueError(
            f"configuration declares {result['declared_length']} bytes, expected 144"
        )
    if not result["crc_matches"]:
        raise ValueError(
            f"configuration CRC mismatch: stored {result['stored_crc_hex']}, "
            f"computed {result['computed_crc_hex']}"
        )
    return data


@dataclass
class GuiConfigSession:
    """One editable configuration with an immutable original baseline."""

    baseline: bytes
    working: bytes

    @classmethod
    def from_image(cls, image: bytes | bytearray | list[int]) -> "GuiConfigSession":
        data = _validated(image)
        return cls(baseline=data, working=data)

    @classmethod
    def from_file(cls, path: str | Path) -> "GuiConfigSession":
        p = Path(path)
        if p.suffix.lower() == ".bin":
            return cls.from_image(p.read_bytes())
        return cls.from_image(config_mod.load_config(str(p)))

    def reset(self) -> None:
        self.working = self.baseline

    def accept_working_as_baseline(self) -> None:
        """Mark the current validated working image as the new baseline."""
        self.working = _validated(self.working)
        self.baseline = self.working

    @property
    def changed(self) -> bool:
        return self.working != self.baseline

    def validation(self) -> dict[str, Any]:
        return config_mod.validate(list(self.working))

    def decoded(self) -> dict[str, Any]:
        return config_mod.decode(list(self.working))

    def diff(self) -> dict[str, Any]:
        return diff_mod.diff_images(self.baseline, self.working)

    def diff_summary(self) -> str:
        return diff_mod.summarise(self.diff())

    def _apply(self, assignment: str) -> None:
        buf = list(self.working)
        config_mod.apply_assignment(buf, assignment)
        self.working = bytes(config_mod.canonicalize(buf))

    def set_map(self, source: str, target: str | int) -> None:
        source_name = str(source).upper()
        if source_name not in REAR_BUTTON_INDEXES:
            raise ValueError(f"GUI rear-button source must be one of {REAR_BUTTONS}")
        target_text = str(target)
        self._apply(f"mapKey[{source_name}]={target_text}")

    def map_target(self, source: str) -> dict[str, Any]:
        source_name = str(source).upper()
        idx = REAR_BUTTON_INDEXES[source_name]
        value = self.working[config_mod.MAPKEYS_START + idx]
        return {
            "source": source_name,
            "source_id": idx,
            "target_id": value,
            "target_name": config_mod.CANONICAL_KEY_NAMES.get(value),
        }

    def set_byte_field(self, field: str, value: int) -> None:
        if field not in QUICK_FIELDS:
            raise ValueError(f"{field} is not a milestone-1 GUI field")
        self._apply(f"{field}={int(value)}")

    def byte_field(self, field: str) -> int:
        if field not in QUICK_FIELDS:
            raise ValueError(f"{field} is not a milestone-1 GUI field")
        return self.working[config_mod.BYTE_FIELDS[field]]

    def export_json(self, path: str | Path) -> None:
        _validated(self.working)
        Path(path).write_text(json.dumps(list(self.working), indent=2) + "\n",
                              encoding="utf-8")

    def export_bin(self, path: str | Path) -> None:
        _validated(self.working)
        Path(path).write_bytes(self.working)
