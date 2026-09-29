"""Operator confirmation for mutating live commands.

Three backends, tried in order: KDE ``kdialog`` when it is installed and a
desktop session is present, a terminal prompt when stdin is interactive, and
otherwise a refusal. A non-interactive run therefore cannot mutate anything
unless the caller explicitly asks for automation.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Mapping

METHOD_KDialog = "kdialog"
METHOD_TERMINAL = "terminal"
METHOD_AUTOMATION = "automation"
METHOD_NONE = "none"

ACCEPTED = "accepted"
DECLINED = "declined"
UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ConfirmationResult:
    accepted: bool | None
    method: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"accepted": self.accepted, "method": self.method, "detail": self.detail}


def _desktop_session_available(env: Mapping[str, str]) -> bool:
    return bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))


def kdialog_available(env: Mapping[str, str] | None = None,
                      which: Callable[[str], str | None] = shutil.which) -> bool:
    env = os.environ if env is None else env
    return bool(which("kdialog")) and _desktop_session_available(env)


def _stdin_isatty() -> bool:
    import sys

    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except Exception:  # pragma: no cover - defensive only
        return False


def confirm_change(
    message: str,
    *,
    title: str = "ARMOR-X configuration change",
    env: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    runner: Callable[..., Any] = subprocess.run,
    input_fn: Callable[[str], str] | None = None,
    stdin_isatty: bool | None = None,
    allow_terminal: bool = True,
    automation: bool = False,
    timeout: int = 900,
) -> ConfirmationResult:
    """Ask the operator to confirm one mutating action.

    Returns ``accepted=True`` on confirmation, ``accepted=False`` when the
    operator declined, and ``accepted=None`` when no backend could ask.
    """
    env = os.environ if env is None else env
    if automation:
        return ConfirmationResult(True, METHOD_AUTOMATION,
                                  "explicit automation flags were supplied")
    if kdialog_available(env, which):
        try:
            completed = runner(
                ["kdialog", "--title", title, "--yesno", message, "--yes-label", "APPLY",
                 "--no-label", "Cancel"],
                capture_output=True, text=True, timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            detail = f"kdialog could not run: {exc}"
        else:
            if completed.returncode == 0:
                return ConfirmationResult(True, METHOD_KDialog, "kdialog accepted")
            if completed.returncode == 1:
                return ConfirmationResult(False, METHOD_KDialog, "kdialog declined")
            detail = f"kdialog exited {completed.returncode}"
    else:
        detail = "kdialog is not available for this session"
    if allow_terminal:
        isatty = stdin_isatty if stdin_isatty is not None else _stdin_isatty()
        if isatty:
            prompt = f"{message}\n\nType APPLY to proceed, anything else to abort: "
            reader = input_fn or input
            answer = reader(prompt)
            if str(answer).strip().upper() == "APPLY":
                return ConfirmationResult(True, METHOD_TERMINAL, "terminal confirmation")
            return ConfirmationResult(False, METHOD_TERMINAL, "terminal declined")
        detail += "; stdin is not interactive"
    return ConfirmationResult(None, METHOD_NONE, detail)
