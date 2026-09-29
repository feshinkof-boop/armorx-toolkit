ArmorX Toolkit Linux desktop package
===================================

This bundle installs the Linux desktop configurator into a private per-user
Python virtual environment and adds a freedesktop/KDE launcher.

Requirements
------------
- Linux with Python 3.10+
- working Bluetooth/BlueZ stack
- Internet access during installation for the PySide6 and Bleak dependencies

Install
-------
  ./install.sh

The installer creates:
  ~/.local/share/armorx-toolkit/venv
  ~/.local/share/applications/io.github.feshinkof_boop.armorx-toolkit.desktop

When XDG_DATA_HOME is set, that location is used instead of ~/.local/share.

Uninstall the application
-------------------------
  ./uninstall.sh

Uninstall deliberately preserves profiles and backups under the ArmorX data
directory.

The launcher uses the standard freedesktop "input-gaming" icon so it follows
the installed desktop theme and does not depend on a private logo asset.
