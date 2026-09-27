#!/usr/bin/env python3
"""capture-radio-baseline.py -- generate the armorx-lab radio baselines.

Writes two files (paths are configurable):

  * <baselines>/radio/primary-network-baseline.txt
      raw + canonical snapshot of the machine's PRIMARY network
  * <baselines>/radio/combo-adapter.json
      the combinatorial USB Wi-Fi + Bluetooth adapter identity

Identity is bound to the PHYSICAL USB PATH and the MAC/controller addresses --
never to names such as wlan1 / hci1, which are recorded only as derived
observations.

If the combo adapter is not plugged in, live-only fields are written as
MISSING_ARTIFACT, the previously recorded expectation is preserved under
"expected_identity_until_insertion", and the historical dmesg evidence of a
previous attachment is recorded under "attachment_history".

Run via ./capture-radio-baseline.sh (which may add sudo for dmesg).
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys


def run(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = p.stdout
        if p.stderr:
            out += p.stderr
        return p.returncode, out.rstrip("\n")
    except Exception as exc:  # noqa: BLE001
        return 127, f"<failed: {exc}>"


def read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except Exception:  # noqa: BLE001
        return ""


def realpath(path: str) -> str:
    try:
        return os.path.realpath(path)
    except Exception:  # noqa: BLE001
        return ""


def hci_for_usb_path(usb_path: str) -> str:
    for link in sorted(glob.glob("/sys/class/bluetooth/hci*")):
        hci = os.path.basename(link)
        dev = realpath(os.path.join(link, "device"))
        if dev and os.path.basename(os.path.dirname(dev)) == usb_path:
            return hci
    return ""


def hci_bdaddr(hci: str) -> str:
    _, out = run(["hcitool", "dev"])
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == hci:
            return parts[1]
    _, out = run(["hciconfig", hci])
    m = re.search(r"BD Address:\s*([0-9A-Fa-f:]{17})", out)
    return m.group(1) if m else ""


def hciconfig_dump(hci: str) -> str:
    _, out = run(["hciconfig", "-a", hci])
    return out


def hciconfig_field(hci: str, pattern: str) -> str:
    m = re.search(pattern, hciconfig_dump(hci), re.MULTILINE)
    return m.group(1).strip() if m else ""


def iface_driver(iface: str) -> str:
    p = f"/sys/bus/usb/devices/{iface}/driver"
    if os.path.islink(p):
        return os.path.basename(os.path.realpath(p))
    return ""


def netdevs_for_usb_path(usb_path: str) -> list[dict]:
    out = []
    for nd in sorted(glob.glob("/sys/class/net/*")):
        devlink = os.path.join(nd, "device")
        if not os.path.exists(devlink):
            continue
        rp = realpath(devlink)
        if f"/{usb_path}/" not in rp + "/":
            continue
        name = os.path.basename(nd)
        out.append(
            {
                "ifname": name,
                "mac": read(os.path.join(nd, "address")),
                "operstate": read(os.path.join(nd, "operstate")),
                "usb_interface": os.path.basename(rp),
                "usb_interface_realpath": rp,
                "driver": iface_driver(os.path.basename(rp)),
                "netdev_realpath": realpath(nd),
            }
        )
    return out


# Values recorded before the adapter was ever seen live (from the lab brief's
# dmesg evidence: RTL8723B, rtl_bt/rtl8723b_fw.bin, rtl8xxxu-class Wi-Fi).
FALLBACK_EXPECTED = {
    "note": (
        "Expected identity of the lab combo adapter while it is absent. Derived "
        "from the recorded dmesg insertion evidence (Realtek RTL8723B, "
        "rtl_bt/rtl8723b_fw.bin) and the lab brief. Re-run "
        "capture-radio-baseline.sh after insertion to replace live fields."
    ),
    "usb_vid_pid": "0bda:b720",
    "usb_vid": "0bda",
    "usb_pid": "b720",
    "wifi": {
        "driver": "rtl8xxxu",
        "usb_interface": "<bus>-<port>:1.2",
        "mac": "unknown-until-insertion",
        "ifnames": [],
    },
    "bluetooth": {
        "driver": "btusb",
        "usb_interfaces": ["<bus>-<port>:1.0", "<bus>-<port>:1.1"],
        "bdaddr": "unknown-until-insertion",
        "firmware": "rtl_bt/rtl8723b_fw.bin (+ rtl8723b_config.bin)",
    },
}


def capture(usb_path: str, primary_if: str):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    usb_dir = f"/sys/bus/usb/devices/{usb_path}"
    anchor = {
        "usb_bus": None,
        "usb_port_path": usb_path,
        "usb_device_sysfs": usb_dir,
        "usb_device_realpath": "",
        "usb_vid_pid": "",
        "usb_vid": "",
        "usb_pid": "",
        "usb_bcd_device": "",
        "usb_serial": "",
        "usb_product": "",
        "usb_manufacturer": "",
        "usb_busnum": "",
        "usb_devnum": "",
        "usb_interfaces": {},
    }

    wifi_block: dict = {}
    bt_block: dict = {}
    present = os.path.isdir(usb_dir)

    if present:
        anchor["usb_device_realpath"] = realpath(usb_dir)
        vid = read(f"{usb_dir}/idVendor")
        pid = read(f"{usb_dir}/idProduct")
        anchor["usb_vid"] = vid
        anchor["usb_pid"] = pid
        anchor["usb_vid_pid"] = f"{vid}:{pid}" if vid and pid else ""
        anchor["usb_bcd_device"] = read(f"{usb_dir}/bcdDevice")
        anchor["usb_serial"] = read(f"{usb_dir}/serial")
        anchor["usb_product"] = read(f"{usb_dir}/product")
        anchor["usb_manufacturer"] = read(f"{usb_dir}/manufacturer")
        anchor["usb_busnum"] = read(f"{usb_dir}/busnum")
        anchor["usb_devnum"] = read(f"{usb_dir}/devnum")
        try:
            anchor["usb_bus"] = int(anchor["usb_busnum"])
        except Exception:  # noqa: BLE001
            anchor["usb_bus"] = None
        _, udev = run(["udevadm", "info", "-q", "property", "-p", usb_dir])
        for line in udev.splitlines():
            if line.startswith("ID_PATH="):
                anchor["udev_id_path"] = line.split("=", 1)[1]
            if line.startswith("ID_SERIAL="):
                anchor["udev_id_serial"] = line.split("=", 1)[1]

        for ifc_dir in sorted(glob.glob(f"{usb_dir}:*")):
            ifc = os.path.basename(ifc_dir)
            anchor["usb_interfaces"][ifc] = {
                "sysfs": ifc_dir,
                "realpath": realpath(ifc_dir),
                "bInterfaceClass": read(f"{ifc_dir}/bInterfaceClass"),
                "bInterfaceSubClass": read(f"{ifc_dir}/bInterfaceSubClass"),
                "bInterfaceProtocol": read(f"{ifc_dir}/bInterfaceProtocol"),
                "driver": iface_driver(ifc),
            }

        nets = netdevs_for_usb_path(usb_path)
        if nets:
            w = nets[0]
            _, nmstate = run(["nmcli", "-t", "-g", "GENERAL.STATE", "device", "show", w["ifname"]])
            _, nmconn = run(["nmcli", "-t", "-g", "GENERAL.CONNECTION", "device", "show", w["ifname"]])
            _, nmmanaged = run(["nmcli", "-t", "-g", "GENERAL.NM-MANAGED", "device", "show", w["ifname"]])
            wifi_block = {
                "driver": w["driver"],
                "ifnames": [n["ifname"] for n in nets],
                "mac": w["mac"],
                "usb_interface": w["usb_interface"],
                "usb_interface_sysfs": f"/sys/bus/usb/devices/{w['usb_interface']}",
                "usb_interface_realpath": w["usb_interface_realpath"],
                "netdev_sysfs": w["netdev_realpath"],
                "operstate": w["operstate"],
                "all_netdevs_on_this_usb_device": nets,
                "networkmanager": {
                    "managed": nmmanaged.strip(),
                    "state": nmstate.strip(),
                    "connection": nmconn.strip(),
                },
            }

        hci = hci_for_usb_path(usb_path)
        if hci:
            rf = sorted(glob.glob(f"/sys/class/bluetooth/{hci}/rfkill*"))
            rfidx = os.path.basename(rf[0]).replace("rfkill", "") if rf else ""
            ifc = os.path.basename(realpath(f"/sys/class/bluetooth/{hci}/device"))
            bt_block = {
                "hci_name": hci,
                "bdaddr": hci_bdaddr(hci),
                "kernel_driver": iface_driver(ifc),
                "usb_interfaces": [
                    i for i, d in anchor["usb_interfaces"].items()
                    if d["bInterfaceClass"] == "e0" and d["bInterfaceSubClass"] == "01"
                ],
                "usb_interface": ifc,
                "usb_interface_realpath": realpath(f"/sys/class/bluetooth/{hci}/device"),
                "sysfs": realpath(f"/sys/class/bluetooth/{hci}"),
                "hci_version": hciconfig_field(hci, r"HCI Version:\s*([^ \n]+)"),
                "manufacturer": hciconfig_field(hci, r"Manufacturer:\s*([^\n]+)"),
                "hci_revision": hciconfig_field(hci, r"HCI Version:.*Revision:\s*([^\n]+)"),
                "lmp_subversion": hciconfig_field(hci, r"Subversion:\s*([^\n]+)"),
                "rfkill_index": rfidx,
                "hciconfig_state": hciconfig_field(hci, r"^\s*(UP RUNNING|DOWN|UP)\s*$"),
            }

    missing = []
    for path, val in [
        ("live_capture.wifi.mac", (wifi_block or {}).get("mac")),
        ("live_capture.wifi.ifnames", (wifi_block or {}).get("ifnames")),
        ("live_capture.wifi.driver", (wifi_block or {}).get("driver")),
        ("live_capture.bluetooth.bdaddr", (bt_block or {}).get("bdaddr")),
        ("live_capture.bluetooth.hci_name", (bt_block or {}).get("hci_name")),
        ("live_capture.bluetooth.kernel_driver", (bt_block or {}).get("kernel_driver")),
    ]:
        if not val:
            missing.append(path)

    return anchor, wifi_block, bt_block, present, missing, now


def dmesg_evidence(usb_path: str) -> dict:
    rc, out = run(["sudo", "-n", "dmesg"], timeout=30)
    if rc != 0 or not out:
        rc, out = run(["dmesg"], timeout=30)
    keys = ("rtl", "8723", "Bluetooth: hci", "btusb", "rtl8xxxu", "b720", usb_path)
    lines = [ln for ln in out.splitlines() if any(k.lower() in ln.lower() for k in keys)]
    lines = lines[-80:]
    return {
        "source": "dmesg",
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "filter": list(keys),
        "note": (
            "Historical evidence of the combo adapter's attachment. The first "
            "enumeration shows 'RTL: download fw command failed (-19)' followed "
            "by a re-enumeration in which the firmware loaded successfully "
            "('RTL: fw version ...'), so -19 is an initial-attach artefact, not "
            "a hard failure."
        ),
        "lines": lines,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baselines", default="/home/salamanka/armorx-lab/baselines/radio")
    ap.add_argument("--usb-path", default=None,
                    help="physical USB port path; default: read from the existing combo-adapter.json")
    ap.add_argument("--primary-if", default="wlp3s0")
    ap.add_argument("--no-dmesg", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.baselines, exist_ok=True)
    json_path = os.path.join(args.baselines, "combo-adapter.json")
    txt_path = os.path.join(args.baselines, "primary-network-baseline.txt")

    usb_path = args.usb_path
    prev = {}
    if os.path.isfile(json_path):
        try:
            prev = json.load(open(json_path))
        except Exception:  # noqa: BLE001
            prev = {}
    if not usb_path:
        usb_path = (prev.get("physical_anchor", {}) or {}).get("usb_port_path") or "1-8"

    anchor, wifi_block, bt_block, present, missing, now = capture(usb_path, args.primary_if)

    expected = prev.get("expected_identity_until_insertion") or FALLBACK_EXPECTED
    if present and wifi_block and bt_block:
        expected = {
            "note": (
                "SUPERSEDED_BY_LIVE_CAPTURE -- the adapter was physically present "
                "when this file was generated, so these values mirror live_capture "
                "and are kept only as the expected identity for the next insertion. "
                "If the adapter is absent on a later run, these are what discovery "
                "will match against."
            ),
            "usb_port_path": usb_path,
            "usb_vid_pid": anchor["usb_vid_pid"],
            "wifi": {
                "driver": wifi_block.get("driver", ""),
                "ifnames": wifi_block.get("ifnames", []),
                "mac": wifi_block.get("mac", ""),
                "usb_interfaces": [wifi_block.get("usb_interface", "")],
            },
            "bluetooth": {
                "driver": bt_block.get("kernel_driver", ""),
                "usb_interfaces": bt_block.get("usb_interfaces", []),
                "bdaddr": bt_block.get("bdaddr", ""),
                "firmware": "rtl_bt/rtl8723b_fw.bin (+ rtl8723b_config.bin)",
            },
        }

    doc = {
        "schema_version": 1,
        "generated_utc": now,
        "generated_by": "automation/radio/capture-radio-baseline.sh",
        "host": {
            "dmi_chassis_type": read("/sys/class/dmi/id/chassis_type"),
            "dmi_product": read("/sys/class/dmi/id/product_name"),
            "kernel": run(["uname", "-r"])[1],
        },
        "identity_binding": {
            "anchors": ["usb_port_path", "usb_vid_pid", "bluetooth.bdaddr", "wifi.mac"],
            "derived_only_never_anchors": ["wifi.ifnames (e.g. wlan1)", "bluetooth.hci_name (e.g. hci1)"],
            "rule": (
                "Bind identity to the physical USB path plus the MAC/controller "
                "address. Interface names (wlan*, wlx*, hciN) and HCI indices are "
                "NOT stable across re-plugs and are recorded for information only; "
                "all tooling re-derives them from the anchors on every run."
            ),
        },
        "physical_anchor": anchor,
        "live_capture": {
            "status": "PRESENT" if present else "MISSING_ARTIFACT",
            "captured_at_utc": now,
            "wifi": wifi_block or {k: "MISSING_ARTIFACT" for k in
                                   ("driver", "ifnames", "mac", "usb_interface", "operstate")},
            "bluetooth": bt_block or {k: "MISSING_ARTIFACT" for k in
                                      ("hci_name", "bdaddr", "kernel_driver", "usb_interfaces")},
        },
        "expected_identity_until_insertion": expected,
        "missing_artifact_fields": missing,
        "primary_network_reference": {
            "interface": args.primary_if,
            "note": "see primary-network-baseline.txt; must never be disturbed",
        },
    }
    if not args.no_dmesg:
        doc["attachment_history"] = dmesg_evidence(usb_path)

    # The other radio on this machine, for contrast: the built-in controller.
    builtin = {
        "usb_path": "1-6",
        "usb_vid_pid": "",
        "note": "machine built-in Bluetooth (Foxconn/Hon Hai) -- NEVER to be unbound/disabled",
        "hci_name": hci_for_usb_path("1-6"),
    }
    p = "/sys/bus/usb/devices/1-6"
    if os.path.isdir(p):
        builtin["usb_vid_pid"] = f"{read(p + '/idVendor')}:{read(p + '/idProduct')}"
        builtin["bdaddr"] = hci_bdaddr(builtin["hci_name"]) if builtin["hci_name"] else ""
    doc["builtin_bluetooth_reference"] = builtin

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")

    # ---- primary network baseline -------------------------------------------
    cmds = [
        ("ip addr", ["ip", "addr"]),
        ("ip -br addr", ["ip", "-br", "addr"]),
        ("ip route", ["ip", "route"]),
        ("ip route show default", ["ip", "route", "show", "default"]),
        ("default gateway", ["sh", "-c", "ip route | awk '/^default/{print $3}'"]),
        ("iw dev wlp3s0 link", ["iw", "dev", args.primary_if, "link"]),
        ("nmcli general status", ["nmcli", "general", "status"]),
        ("nmcli device status", ["nmcli", "device", "status"]),
        ("rfkill list", ["rfkill", "list"]),
        ("lsusb", ["lsusb"]),
        ("lsusb -t", ["lsusb", "-t"]),
        ("ls -la /sys/class/bluetooth", ["ls", "-la", "/sys/class/bluetooth"]),
    ]
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write("armorx-lab -- PRIMARY NETWORK BASELINE\n")
        fh.write(f"generated_utc: {now}\n")
        fh.write(f"generated_by : automation/radio/capture-radio-baseline.sh\n")
        fh.write(f"host         : {doc['host']['dmi_product']} | kernel {doc['host']['kernel']}\n")
        fh.write("primary_if   : " + args.primary_if + "  (internal Qualcomm ath12k PCIe Wi-Fi; must never be disturbed)\n")
        fh.write("\nNOTE: this file is an observation record. The checkable, canonical form is\n")
        fh.write("      check-primary-network.sh --snapshot (see the last section).\n")
        for title, cmd in cmds:
            rc, out = run(cmd)
            fh.write("\n" + "=" * 78 + "\n")
            fh.write(f"$ {' '.join(cmd)}\n")
            fh.write(f"# {' '.join(cmd) if title != ' '.join(cmd) else title}   [exit {rc}]\n")
            fh.write("-" * 78 + "\n")
            fh.write((out or "(no output)") + "\n")
        snap = run(["/home/salamanka/armorx-lab/automation/radio/check-primary-network.sh", "--snapshot"])
        fh.write("\n" + "=" * 78 + "\n")
        fh.write("$ check-primary-network.sh --snapshot   [exit %d]\n" % snap[0])
        fh.write("-" * 78 + "\n")
        fh.write((snap[1] or "(no output)") + "\n")

    # Canonical, directly comparable snapshot (feed this to --compare-with).
    snap_path = os.path.join(args.baselines, "primary-network-snapshot.txt")
    with open(snap_path, "w", encoding="utf-8") as fh:
        fh.write((snap[1] or "") + "\n")
    print(f"wrote {snap_path}")

    print(f"wrote {json_path}")
    print(f"wrote {txt_path}")
    print(f"live_capture.status = {doc['live_capture']['status']}")
    if missing:
        print("missing live-only fields: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
