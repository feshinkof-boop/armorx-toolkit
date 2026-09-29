"""Hardware-free tests for the confirmation abstraction."""

import pytest

from armorx import confirm as C


class _Completed:
    def __init__(self, returncode):
        self.returncode = returncode


def _runner(code):
    def run(*args, **kwargs):
        return _Completed(code)
    return run


def test_kdialog_is_preferred_when_a_desktop_session_exists():
    result = C.confirm_change("message", title="t", env={"DISPLAY": ":0"},
                              which=lambda name: "/usr/bin/kdialog",
                              runner=_runner(0), stdin_isatty=False)
    assert result.accepted is True
    assert result.method == C.METHOD_KDialog


def test_kdialog_decline_is_a_decline_not_an_error():
    result = C.confirm_change("message", env={"WAYLAND_DISPLAY": "wayland-0"},
                              which=lambda name: "/usr/bin/kdialog",
                              runner=_runner(1), stdin_isatty=False)
    assert result.accepted is False
    assert result.method == C.METHOD_KDialog


def test_terminal_is_used_when_kdialog_is_absent():
    result = C.confirm_change("message", env={}, which=lambda name: None,
                              input_fn=lambda prompt: "APPLY", stdin_isatty=True)
    assert result.accepted is True
    assert result.method == C.METHOD_TERMINAL


def test_terminal_decline():
    result = C.confirm_change("message", env={}, which=lambda name: None,
                              input_fn=lambda prompt: "no", stdin_isatty=True)
    assert result.accepted is False
    assert result.method == C.METHOD_TERMINAL


def test_non_interactive_without_automation_is_unavailable_not_accepted():
    result = C.confirm_change("message", env={}, which=lambda name: None,
                              stdin_isatty=False)
    assert result.accepted is None
    assert result.method == C.METHOD_NONE
    assert "not interactive" in result.detail


def test_automation_bypasses_the_backends_but_is_marked():
    result = C.confirm_change("message", env={}, which=lambda name: None,
                              stdin_isatty=False, automation=True)
    assert result.accepted is True
    assert result.method == C.METHOD_AUTOMATION
    assert "automation" in result.detail


def test_kdialog_needs_both_the_binary_and_a_session():
    assert C.kdialog_available({}, which=lambda name: "/usr/bin/kdialog") is False
    assert C.kdialog_available({"DISPLAY": ":0"}, which=lambda name: None) is False
    assert C.kdialog_available({"DISPLAY": ":0"}, which=lambda name: "/usr/bin/kdialog") is True


def test_a_broken_kdialog_falls_through_to_the_terminal():
    def boom(*args, **kwargs):
        raise OSError("cannot start kdialog")

    result = C.confirm_change("message", env={"DISPLAY": ":0"},
                              which=lambda name: "/usr/bin/kdialog", runner=boom,
                              input_fn=lambda prompt: "APPLY", stdin_isatty=True)
    assert result.accepted is True
    assert result.method == C.METHOD_TERMINAL
