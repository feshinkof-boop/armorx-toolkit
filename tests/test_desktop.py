from __future__ import annotations

from armorx import desktop


def test_default_applications_dir_uses_xdg(tmp_path):
    path = desktop.default_applications_dir(
        env={"XDG_DATA_HOME": str(tmp_path / "xdg")},
        home=tmp_path / "home",
    )
    assert path == tmp_path / "xdg" / "applications"


def test_default_applications_dir_falls_back_to_home(tmp_path):
    path = desktop.default_applications_dir(env={}, home=tmp_path)
    assert path == tmp_path / ".local" / "share" / "applications"


def test_desktop_entry_uses_absolute_python_and_gui_module(tmp_path):
    python = tmp_path / "venv with space" / "bin" / "python"
    text = desktop.desktop_entry(python_executable=python)
    assert "[Desktop Entry]" in text
    assert "Name=ArmorX Toolkit" in text
    assert f'"{python.resolve()}" -m armorx.gui' in text
    assert "Icon=input-gaming" in text
    assert "Terminal=false" in text


def test_install_and_uninstall(tmp_path):
    apps = tmp_path / "applications"
    path = desktop.install(applications_dir=apps, python_executable="/usr/bin/python3")
    assert path == apps / desktop.DESKTOP_ID
    assert path.exists()
    assert path.stat().st_mode & 0o777 == 0o644
    assert "/usr/bin/python3" in path.read_text()
    assert desktop.uninstall(applications_dir=apps) is True
    assert desktop.uninstall(applications_dir=apps) is False


def test_cli_install_and_status(tmp_path, capsys):
    apps = tmp_path / "applications"
    assert desktop.main(["--applications-dir", str(apps), "install"]) == 0
    assert desktop.main(["--applications-dir", str(apps), "status"]) == 0
    assert desktop.DESKTOP_ID in capsys.readouterr().out
