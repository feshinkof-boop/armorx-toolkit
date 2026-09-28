"""Device discovery tests against a synthetic sysfs tree. No hardware required."""

import json
from pathlib import Path

from armorx import device


def make_usb_entry(root: Path, name: str, vid: str, pid: str, *, product="HID zk",
                   manufacturer="Zikway", speed="12", driver="usbhid", interfaces=(0,),
                   serial=None, bcd="0100"):
    entry = root / name
    entry.mkdir(parents=True)
    (entry / "idVendor").write_text(vid)
    (entry / "idProduct").write_text(pid)
    (entry / "product").write_text(product)
    (entry / "manufacturer").write_text(manufacturer)
    (entry / "speed").write_text(speed)
    (entry / "bcdDevice").write_text(bcd)
    if serial:
        (entry / "serial").write_text(serial)
    for index in interfaces:
        iface = root / f"{name}:1.{index}"
        iface.mkdir()
        (iface / "bInterfaceClass").write_text("03")
        (iface / "bInterfaceSubClass").write_text("00")
        (iface / "bInterfaceProtocol").write_text("00")
        driver_dir = root.parent / "drivers" / driver
        driver_dir.mkdir(parents=True, exist_ok=True)
        (iface / "driver").symlink_to(driver_dir)
    return entry


def make_tree(tmp_path: Path):
    root = tmp_path / "sysfs"
    root.mkdir()
    make_usb_entry(root, "1-7", "413d", "2106")
    make_usb_entry(root, "1-8", "045e", "0b12", product="Controller",
                   manufacturer="Microsoft", speed="12", driver="xpad", serial="3039")
    make_usb_entry(root, "1-2", "1d6b", "0002", product="xHCI Host Controller",
                   manufacturer="Linux Foundation", speed="480", driver="hub")
    hidraw = tmp_path / "hidraw"
    (hidraw / "hidraw2").mkdir(parents=True)
    (hidraw / "hidraw2" / "device").symlink_to(root / "1-7")
    inp = tmp_path / "input"
    (inp / "event18").mkdir(parents=True)
    (inp / "event18" / "device").symlink_to(root / "1-8")
    return root, hidraw, inp


def scan(tmp_path):
    root, hidraw, inp = make_tree(tmp_path)
    return device.scan_devices(sysfs_root=root, hidraw_root=hidraw, input_root=inp)


def test_missing_sysfs_returns_empty_list(tmp_path):
    assert device.scan_devices(sysfs_root=tmp_path / "nope") == []


def test_scan_finds_all_entries(tmp_path):
    assert len(scan(tmp_path)) == 3


def test_known_only_filters(tmp_path):
    root, hidraw, inp = make_tree(tmp_path)
    found = device.scan_devices(sysfs_root=root, hidraw_root=hidraw, input_root=inp,
                                known_only=True)
    assert sorted(c.identity.vid_pid for c in found) == ["045e:0b12", "413d:2106"]


def test_vendor_identity_is_classified_without_radio_claims(tmp_path):
    candidate = next(c for c in scan(tmp_path) if c.identity.vid_pid == "413d:2106")
    names = [s.name for s in candidate.states]
    assert "vendor_hid_personality" in names
    assert candidate.hidraw_nodes == ["/dev/hidraw2"]
    explanation = device.explain_device(candidate)
    assert explanation["evidence"] == "proven"
    assert any("does NOT prove a radio-link state" in c for c in explanation["caveats"])


def test_xbox_identity_reports_xpad_binding(tmp_path):
    candidate = next(c for c in scan(tmp_path) if c.identity.vid_pid == "045e:0b12")
    names = [s.name for s in candidate.states]
    assert "xbox_gip_personality" in names and "xpad_bound" in names
    assert candidate.input_nodes == ["/dev/input/event18"]


def test_unknown_identity_makes_no_claims(tmp_path):
    candidate = next(c for c in scan(tmp_path) if c.identity.vid_pid == "1d6b:0002")
    assert [s.name for s in candidate.states] == ["unrecognized_identity"]
    assert device.explain_device(candidate)["meaning"].startswith("Unknown identity")


def test_find_by_path_resolves_usb_path_and_vid_pid(tmp_path):
    candidates = scan(tmp_path)
    assert device.find_by_path(candidates, "1-7").identity.vid_pid == "413d:2106"
    assert device.find_by_path(candidates, "045e:0b12").identity.product == "Controller"
    assert device.find_by_path(candidates, "9-9") is None


def test_find_by_path_tolerates_vid_only(tmp_path):
    candidates = scan(tmp_path)
    assert device.find_by_path(candidates, "413d") is not None


def test_speed_is_translated_for_humans(tmp_path):
    candidate = next(c for c in scan(tmp_path) if c.identity.usb_path == "1-2")
    assert candidate.identity.speed == "high (480 Mbps)"


def test_doctor_on_a_tree_without_devices(tmp_path):
    empty = tmp_path / "empty-sysfs"
    empty.mkdir()
    result = device.doctor(sysfs_root=empty, hidraw_root=tmp_path / "no-hidraw",
                           input_root=tmp_path / "no-input")
    statuses = {c["check"]: c["status"] for c in result["checks"]}
    assert statuses["known_identities"] == "none"
    assert result["devices_found"] == 0
    assert result["ok"] is True


def test_doctor_on_a_tree_with_devices(tmp_path):
    root, hidraw, inp = make_tree(tmp_path)
    result = device.doctor(sysfs_root=root, hidraw_root=hidraw, input_root=inp)
    assert result["devices_found"] == 2
    assert any("device inspect" in step for step in result["next_steps"])


def test_doctor_is_json_serialisable(tmp_path):
    root, hidraw, inp = make_tree(tmp_path)
    json.dumps(device.doctor(sysfs_root=root, hidraw_root=hidraw, input_root=inp))


def test_gip_report_forms_record_unknown_transition():
    forms = device.GIP_REPORT_FORMS
    assert forms["startup"]["length"] == 32 and forms["steady"]["length"] == 48
    assert forms["transition_cause"]["evidence"] == "unknown"
