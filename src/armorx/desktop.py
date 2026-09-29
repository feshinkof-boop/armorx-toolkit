"""Freedesktop launcher integration for the ArmorX Linux GUI."""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


DESKTOP_ID = "io.github.feshinkof_boop.armorx-toolkit.desktop"
APP_NAME = "ArmorX Toolkit"


def default_applications_dir(*, env: dict[str, str] | None = None,
                             home: str | Path | None = None) -> Path:
    env = os.environ if env is None else env
    xdg = env.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "applications"
    base = Path(home) if home is not None else Path.home()
    return base / ".local" / "share" / "applications"


def _quote_exec_arg(value: str) -> str:
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("$", "\\$")
    )
    return f'"{escaped}"'


def desktop_entry(*, python_executable: str | Path | None = None) -> str:
    executable = Path(python_executable or sys.executable).resolve()
    exec_line = f"{_quote_exec_arg(str(executable))} -m armorx.gui"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Version=1.0\n"
        f"Name={APP_NAME}\n"
        "Comment=Configure BIGBIG WON ARMOR-X Pro controllers\n"
        f"Exec={exec_line}\n"
        "Icon=input-gaming\n"
        "Terminal=false\n"
        "Categories=Game;Utility;\n"
        "Keywords=ArmorX;ARMOR-X;BIGBIG WON;Xbox;Controller;Gamepad;\n"
        "StartupNotify=true\n"
    )


def desktop_path(*, applications_dir: str | Path | None = None) -> Path:
    root = Path(applications_dir) if applications_dir is not None else default_applications_dir()
    return root / DESKTOP_ID


def install(*, applications_dir: str | Path | None = None,
            python_executable: str | Path | None = None) -> Path:
    path = desktop_path(applications_dir=applications_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(desktop_entry(python_executable=python_executable), encoding="utf-8")
    temp.chmod(0o644)
    temp.replace(path)
    return path


def uninstall(*, applications_dir: str | Path | None = None) -> bool:
    path = desktop_path(applications_dir=applications_dir)
    if not path.exists():
        return False
    path.unlink()
    return True


def _refresh_database(path: Path) -> None:
    tool = shutil.which("update-desktop-database")
    if tool:
        import subprocess
        subprocess.run([tool, str(path.parent)], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="armorx-desktop",
        description="Install or remove the ArmorX Toolkit Linux desktop launcher.",
    )
    parser.add_argument(
        "--applications-dir",
        help="override the freedesktop applications directory (mainly for testing)",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("install", help="install/update the per-user desktop launcher")
    sub.add_parser("uninstall", help="remove the per-user desktop launcher")
    sub.add_parser("status", help="show the launcher path and whether it exists")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    directory = args.applications_dir
    path = desktop_path(applications_dir=directory)
    if args.command == "install":
        path = install(applications_dir=directory)
        _refresh_database(path)
        print(f"Installed {path}")
        return 0
    if args.command == "uninstall":
        removed = uninstall(applications_dir=directory)
        _refresh_database(path)
        print(f"{'Removed' if removed else 'Not installed'} {path}")
        return 0
    print(f"{path} ({'installed' if path.exists() else 'not installed'})")
    return 0 if path.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
