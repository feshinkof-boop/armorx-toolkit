"""Qt-independent draft model for the v0.5 macro timeline editor."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import macro as macro_mod


@dataclass
class MacroStep:
    keys: str = "A"
    duration: int = 200
    interval: int = 100

    def normalized(self) -> "MacroStep":
        ids, names = macro_mod.parse_chord(self.keys)
        if self.duration < 0 or self.interval < 0:
            raise ValueError("macro timing must be non-negative")
        return MacroStep(
            keys="+".join(names),
            duration=int(self.duration),
            interval=int(self.interval),
        )


@dataclass
class MacroDraft:
    name: str = "ArmorX Macro"
    trigger: str = "M1"
    mode: str = "tap"
    repeat_time: int = 200
    active: bool = False
    steps: list[MacroStep] = field(default_factory=lambda: [MacroStep()])
    macro_id: int = -1

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name.strip():
            errors.append("macro name must not be empty")
        if self.trigger not in macro_mod.RUN_KEYS:
            errors.append("macro trigger must be M1, M2, M3 or M4")
        if self.mode not in {"long_press", "tap", "long_press_cycle", "tap_cycle"}:
            errors.append("unknown macro execution mode")
        if self.repeat_time < 0:
            errors.append("repeat time must be non-negative")
        if not (1 <= len(self.steps) <= macro_mod.V41_MAX_STEPS):
            errors.append(
                f"macro must contain 1..{macro_mod.V41_MAX_STEPS} steps"
            )
        for index, step in enumerate(self.steps, 1):
            try:
                step.normalized()
            except Exception as exc:
                errors.append(f"step {index}: {exc}")
        if errors:
            return errors
        try:
            obj = self.to_object()
        except Exception as exc:
            return [str(exc)]
        return macro_mod.validate_macro_object(obj)

    def to_object(self) -> dict[str, Any]:
        normalized = [step.normalized() for step in self.steps]
        return macro_mod.build_macro_object(
            name=self.name.strip(),
            trigger=self.trigger,
            mode=self.mode,
            repeat_time=int(self.repeat_time),
            active=bool(self.active),
            steps=[
                {
                    "keys": step.keys,
                    "duration": step.duration,
                    "interval": step.interval,
                }
                for step in normalized
            ],
            macro_id=int(self.macro_id),
        )

    def add_step(self, step: MacroStep | None = None, *, index: int | None = None) -> None:
        if len(self.steps) >= macro_mod.V41_MAX_STEPS:
            raise ValueError(
                f"firmware V41 supports at most {macro_mod.V41_MAX_STEPS} steps"
            )
        value = step or MacroStep()
        if index is None:
            self.steps.append(value)
        else:
            self.steps.insert(max(0, min(int(index), len(self.steps))), value)

    def remove_step(self, index: int) -> None:
        if len(self.steps) <= 1:
            raise ValueError("a macro must keep at least one step")
        if not 0 <= index < len(self.steps):
            raise IndexError(index)
        self.steps.pop(index)

    def move_step(self, index: int, delta: int) -> int:
        if not 0 <= index < len(self.steps):
            raise IndexError(index)
        target = index + int(delta)
        if not 0 <= target < len(self.steps):
            return index
        self.steps[index], self.steps[target] = self.steps[target], self.steps[index]
        return target

    @classmethod
    def from_object(cls, obj: dict[str, Any]) -> "MacroDraft":
        errors = macro_mod.validate_macro_object(obj)
        if errors:
            raise ValueError("; ".join(errors))
        rows = macro_mod.decode_macro_json(obj["macroJson"])
        trigger = next(
            (name for name, key_id in macro_mod.RUN_KEYS.items()
             if key_id == obj["runKey"]),
            obj.get("runKeyName"),
        )
        mode = macro_mod.MODE_NAMES[obj["isRepeat"]]
        steps = [
            MacroStep(
                keys="+".join(row["keyNameListDecoded"]),
                duration=int(row["duration"]),
                interval=int(row["interval"]),
            )
            for row in rows
        ]
        return cls(
            name=str(obj["macroName"]),
            trigger=str(trigger),
            mode=mode,
            repeat_time=int(obj["repeatTime"]),
            active=bool(obj["inUse"]),
            steps=steps,
            macro_id=int(obj.get("id", -1)),
        )

    @classmethod
    def load(cls, path: str | Path) -> "MacroDraft":
        return cls.from_object(json.loads(Path(path).read_text(encoding="utf-8")))

    def export(self, path: str | Path) -> None:
        obj = self.to_object()
        errors = macro_mod.validate_macro_object(obj)
        if errors:
            raise ValueError("; ".join(errors))
        Path(path).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
