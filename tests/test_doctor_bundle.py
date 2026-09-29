"""Diagnostics bundle sanitisation tests."""

import json
from pathlib import Path

from armorx import device


def make_tree(tmp_path: Path):
    root = tmp_path / "sysfs"
    root.mkdir()
    entry = root / "1-7"
    entry.mkdir()
    (entry / "idVendor").write_text("045e")
    (entry / "idProduct").write_text("0b12")
    (entry / "product").write_text("Controller")
    (entry / "manufacturer").write_text("Microsoft")
    (entry / "serial").write_text("01234567890123")
    (entry / "speed").write_text("12")
    (entry / "bcdDevice").write_text("0518")
    iface = root / "1-7:1.0"
    iface.mkdir()
    (iface / "bInterfaceClass").write_text("ff")
    (iface / "bInterfaceSubClass").write_text("47")
    (iface / "bInterfaceProtocol").write_text("d0")
    return root, tmp_path / "no-hidraw", tmp_path / "no-input"


def bundle(tmp_path, **kwargs):
    root, hidraw, inp = make_tree(tmp_path)
    return device.diagnostics_bundle(sysfs_root=root, hidraw_root=hidraw,
                                     input_root=inp, toolkit_version="0.2.0", **kwargs)


def test_bundle_records_the_toolkit_version(tmp_path):
    assert bundle(tmp_path)["toolkit_version"] == "0.2.0"


def test_serial_numbers_are_not_included(tmp_path):
    data = bundle(tmp_path)
    text = json.dumps(data)
    assert "01234567890123" not in text
    for device in data["devices"]:
        assert not device["identity"].get("serial")


def test_hostname_is_absent_by_default(tmp_path):
    assert "hostname" not in bundle(tmp_path)


def test_hostname_can_be_requested_explicitly(tmp_path):
    data = bundle(tmp_path, include_hostname=True)
    assert data["hostname"] and data["privacy"]["hostname_included"] is True


def test_home_paths_are_masked(tmp_path):
    data = bundle(tmp_path)
    assert "/home/" not in json.dumps(data) or "<home>" in json.dumps(data)


def test_privacy_block_lists_what_is_omitted(tmp_path):
    omitted = bundle(tmp_path)["privacy"]["omitted"]
    for item in ("usernames", "home paths", "usb serial numbers"):
        assert item in omitted


def test_bundle_is_json_serialisable(tmp_path):
    json.dumps(bundle(tmp_path))


def test_bundle_without_hardware_still_reports_checks(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    data = device.diagnostics_bundle(sysfs_root=empty, hidraw_root=tmp_path / "n",
                                     input_root=tmp_path / "n", toolkit_version="0.2.0")
    assert data["devices"] == []
    assert data["doctor"]["checks"]


def test_text_rendering_mentions_privacy(tmp_path):
    text = device.render_bundle_text(bundle(tmp_path))
    assert "omitted for privacy" in text
    assert "armorx toolkit 0.2.0" in text


def test_text_rendering_handles_recognised_devices(tmp_path):
    text = device.render_bundle_text(bundle(tmp_path))
    assert "045e:0b12" in text
