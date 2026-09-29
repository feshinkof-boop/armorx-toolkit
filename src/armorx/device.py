"""Read-only ARMORX device discovery and diagnostics.

Nothing in this module writes to a device. Discovery reads sysfs; diagnostics
report what was found and what it means, with an explicit evidence level for
every claim. "No supported device found" is a successful result, not an error.
"""

from __future__ import annotations

import os
import platform
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .protocol import EVIDENCE_PROVEN, EVIDENCE_STRONG, EVIDENCE_UNKNOWN

DEFAULT_SYSFS_ROOT = "/sys/bus/usb/devices"
DEFAULT_HIDRAW_CLASS = "/sys/class/hidraw"
DEFAULT_INPUT_CLASS = "/sys/class/input"

#: Identities observed on real hardware. ``meaning`` states only what is
#: actually supported; see ``caveats`` for the limits of each claim.
KNOWN_IDENTITIES: dict[str, dict] = {
    "413d:2106": {
        "family": "armorx_vendor_hid",
        "manufacturer": "Zikway",
        "product": "HID zk",
        "bcd_device": "0x0100",
        "usage_page": "0xFF7A",
        "endpoints": "0x03 OUT interrupt 64 bytes; 0x83 IN interrupt 64 bytes; interval 8 ms",
        "evidence": EVIDENCE_PROVEN,
        "meaning": (
            "The vendor HID personality. Observed on the ARMORX Pro itself and on the "
            "F20 receiver when the unit is USB-powered without an active controller "
            "session. In that state the interface was silent: interrupted captures "
            "showed probe traffic only, and a physical button press produced no "
            "payload-bearing frames."
        ),
        "caveats": [
            "VID:PID 413D:2106 alone does NOT prove a radio-link state, power state or "
            "which physical unit is attached; the ARMORX Pro and the F20 are "
            "byte-for-byte indistinguishable from this identity, including the report "
            "descriptor, so the hardware must be identified by the user.",
            "No serial number is exposed, so two units cannot be told apart from the wire.",
        ],
    },
    "045e:0b12": {
        "family": "xbox_gip",
        "manufacturer": "Microsoft",
        "product": "Controller",
        "bcd_device": "0x0518",
        "evidence": EVIDENCE_PROVEN,
        "meaning": (
            "The Xbox operating personality. Observed after the ARMORX power button is "
            "pressed while USB is connected; the device re-enumerates on the same port, "
            "the Linux xpad driver binds interface 0 and a live GIP input stream starts "
            "at roughly 4 ms cadence."
        ),
        "caveats": [
            "This identity is what an Xbox controller presents; seeing it does not by "
            "itself prove that an ARMORX Pro is in the path.",
        ],
    },
}

#: Reports seen from the GIP personality.
GIP_REPORT_FORMS = {
    "startup": {"length": 32, "evidence": EVIDENCE_PROVEN},
    "steady": {"length": 48, "evidence": EVIDENCE_PROVEN},
    "transition_cause": {"value": None, "evidence": EVIDENCE_UNKNOWN,
                         "note": "why the stream moves from 32 to 48 bytes is unknown"},
}


@dataclass
class Interface:
    number: int
    class_code: int | None
    subclass: int | None
    protocol: int | None
    driver: str | None = None

    def to_dict(self) -> dict:
        return {"number": self.number, "class": self.class_code, "subclass": self.subclass,
                "protocol": self.protocol, "driver": self.driver}


@dataclass
class DeviceIdentity:
    vid: int
    pid: int
    manufacturer: str | None = None
    product: str | None = None
    serial: str | None = None
    bcd_device: str | None = None
    usb_path: str | None = None
    speed: str | None = None

    @property
    def vid_pid(self) -> str:
        return f"{self.vid:04x}:{self.pid:04x}"

    @property
    def known(self) -> dict | None:
        return KNOWN_IDENTITIES.get(self.vid_pid)

    @property
    def family(self) -> str:
        info = self.known
        return info["family"] if info else "unknown"

    def to_dict(self) -> dict:
        return {"vid_pid": self.vid_pid, "vid": f"0x{self.vid:04X}", "pid": f"0x{self.pid:04X}",
                "manufacturer": self.manufacturer, "product": self.product,
                "serial": self.serial, "bcd_device": self.bcd_device,
                "usb_path": self.usb_path, "speed": self.speed, "family": self.family,
                "recognized": bool(self.known)}


@dataclass
class DeviceState:
    name: str
    evidence: str
    description: str

    def to_dict(self) -> dict:
        return {"name": self.name, "evidence": self.evidence, "description": self.description}


@dataclass
class DeviceCandidate:
    identity: DeviceIdentity
    sysfs_path: str
    interfaces: list[Interface] = field(default_factory=list)
    hidraw_nodes: list[str] = field(default_factory=list)
    input_nodes: list[str] = field(default_factory=list)
    states: list[DeviceState] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "identity": self.identity.to_dict(),
            "sysfs_path": self.sysfs_path,
            "interfaces": [i.to_dict() for i in self.interfaces],
            "hidraw_nodes": self.hidraw_nodes,
            "input_nodes": self.input_nodes,
            "states": [s.to_dict() for s in self.states],
        }


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


_HEX_STRING = re.compile(r"^(?:[0-9a-fA-F]{2})+$")


def _decode_serial(raw: str | None) -> str | None:
    """Decode the sysfs serial form.

    The kernel prints a string descriptor as a hex dump when it is not plain
    ASCII, so ``/sys/bus/usb/devices/.../serial`` can read as
    ``3039373130373639393537313433`` for the serial ``09710769957143``. Both
    forms are useful: the decoded one is what the device actually reports, the
    raw one is what sysfs says. Only a fully printable decode is substituted.
    """
    if raw is None:
        return None
    if len(raw) % 2 == 0 and _HEX_STRING.match(raw):
        try:
            decoded = bytes.fromhex(raw).decode("ascii")
        except (ValueError, UnicodeDecodeError):
            return raw
        if decoded.isprintable():
            return decoded
    return raw


def _read_int(path: Path, base: int = 16) -> int | None:
    text = _read(path)
    if text is None:
        return None
    try:
        return int(text, base)
    except ValueError:
        return None


def _speed_text(raw: str | None) -> str | None:
    return {"1.5": "low (1.5 Mbps)", "12": "full (12 Mbps)",
            "480": "high (480 Mbps)", "5000": "super (5 Gbps)"}.get(raw or "", raw)


def _interfaces_for(device_path: Path) -> list[Interface]:
    interfaces: list[Interface] = []
    parent = device_path.name
    for child in sorted(device_path.parent.glob(f"{parent}:*")):
        # "<device>:<configuration>.<interface>", e.g. "1-7:1.2" is interface 2
        # of configuration 1. Taking the part before the dot reports every
        # interface of a device as number 1, which real hardware exposed.
        number_text = child.name.rsplit(".", 1)[-1]
        try:
            number = int(number_text)
        except ValueError:
            continue
        driver_link = child / "driver"
        driver = driver_link.resolve().name if driver_link.exists() else None
        interfaces.append(Interface(
            number=number,
            class_code=_read_int(child / "bInterfaceClass"),
            subclass=_read_int(child / "bInterfaceSubClass"),
            protocol=_read_int(child / "bInterfaceProtocol"),
            driver=driver,
        ))
    return interfaces


def _hidraw_for(device_path: Path, hidraw_root: Path) -> list[str]:
    nodes: list[str] = []
    if not hidraw_root.is_dir():
        return nodes
    for entry in sorted(hidraw_root.iterdir()):
        try:
            resolved = (entry / "device").resolve()
        except OSError:
            continue
        if str(device_path.resolve()) in str(resolved):
            nodes.append(f"/dev/{entry.name}")
    return nodes


def _input_for(device_path: Path, input_root: Path) -> list[str]:
    nodes: list[str] = []
    if not input_root.is_dir():
        return nodes
    for entry in sorted(input_root.iterdir()):
        if not entry.name.startswith("event") and not entry.name.startswith("js"):
            continue
        try:
            resolved = (entry / "device").resolve()
        except OSError:
            continue
        if str(device_path.resolve()) in str(resolved):
            nodes.append(f"/dev/input/{entry.name}")
    return nodes


def scan_devices(*, sysfs_root: str | os.PathLike[str] = DEFAULT_SYSFS_ROOT,
                 hidraw_root: str | os.PathLike[str] = DEFAULT_HIDRAW_CLASS,
                 input_root: str | os.PathLike[str] = DEFAULT_INPUT_CLASS,
                 known_only: bool = False) -> list[DeviceCandidate]:
    """Inspect the USB bus without touching any device.

    Returns candidates for every USB device, or only the recognized ones when
    ``known_only`` is set. Missing sysfs (containers, Windows, macOS) yields an
    empty list rather than an exception.
    """
    root = Path(sysfs_root)
    if not root.is_dir():
        return []
    candidates: list[DeviceCandidate] = []
    for entry in sorted(root.iterdir()):
        vid = _read_int(entry / "idVendor")
        pid = _read_int(entry / "idProduct")
        if vid is None or pid is None:
            continue
        identity = DeviceIdentity(
            vid=vid, pid=pid,
            manufacturer=_read(entry / "manufacturer"),
            product=_read(entry / "product"),
            serial=_decode_serial(_read(entry / "serial")),
            bcd_device=_read(entry / "bcdDevice"),
            usb_path=entry.name,
            speed=_speed_text(_read(entry / "speed")),
        )
        if known_only and not identity.known:
            continue
        candidate = DeviceCandidate(
            identity=identity,
            sysfs_path=str(entry),
            interfaces=_interfaces_for(entry),
            hidraw_nodes=_hidraw_for(entry, Path(hidraw_root)),
            input_nodes=_input_for(entry, Path(input_root)),
        )
        candidate.states = classify_device(candidate)
        candidates.append(candidate)
    return candidates


def classify_device(candidate: DeviceCandidate) -> list[DeviceState]:
    """Derive states from proven signals only."""
    states: list[DeviceState] = []
    key = candidate.identity.vid_pid
    if key == "413d:2106":
        states.append(DeviceState(
            "vendor_hid_personality",
            EVIDENCE_PROVEN,
            "The 413D:2106 vendor HID personality is present. This is the state in which "
            "the interface was observed to carry no input traffic, so do not expect "
            "gamepad reports from it.",
        ))
        if candidate.hidraw_nodes:
            states.append(DeviceState(
                "hidraw_available", EVIDENCE_PROVEN,
                "A hidraw node exists; reading it requires write access to that node's "
                "permissions and the device must be opened read-only.",
            ))
        else:
            states.append(DeviceState(
                "hidraw_absent", EVIDENCE_STRONG,
                "No hidraw node was resolved for this device; the HID interface may not be "
                "bound to the generic HID driver yet.",
            ))
    elif key == "045e:0b12":
        state = DeviceState(
            "xbox_gip_personality", EVIDENCE_PROVEN,
            "The Xbox GIP personality is present; a live input stream is expected and "
            "xpad should have bound interface 0.",
        )
        states.append(state)
        if any(i.driver == "xpad" for i in candidate.interfaces):
            states.append(DeviceState("xpad_bound", EVIDENCE_PROVEN,
                                      "xpad bound an interface, so standard Linux gamepad "
                                      "input is available through evdev."))
        else:
            states.append(DeviceState("xpad_not_bound", EVIDENCE_STRONG,
                                      "xpad is not bound to any interface of this device; "
                                      "input nodes may be missing."))
        if candidate.input_nodes:
            states.append(DeviceState("input_nodes_present", EVIDENCE_PROVEN,
                                      "Input nodes exist: " + ", ".join(candidate.input_nodes)))
    else:
        states.append(DeviceState("unrecognized_identity", EVIDENCE_UNKNOWN,
                                  "This identity has not been observed in the project's "
                                  "hardware runs."))
    return states


def explain_device(candidate: DeviceCandidate) -> dict:
    """Explain one candidate, keeping claims inside their evidence level."""
    info = candidate.identity.known
    explanation = {
        "identity": candidate.identity.to_dict(),
        "sysfs_path": candidate.sysfs_path,
        "interfaces": [i.to_dict() for i in candidate.interfaces],
        "hidraw_nodes": candidate.hidraw_nodes,
        "input_nodes": candidate.input_nodes,
        "states": [s.to_dict() for s in candidate.states],
        "recognized": bool(info),
        "meaning": info["meaning"] if info else "Unknown identity; no claims are made.",
        "caveats": list(info["caveats"]) if info else [],
        "evidence": info["evidence"] if info else EVIDENCE_UNKNOWN,
    }
    return explanation


@dataclass
class DoctorCheck:
    name: str
    status: str
    detail: str
    evidence: str = EVIDENCE_PROVEN
    hint: str | None = None

    def to_dict(self) -> dict:
        out = {"check": self.name, "status": self.status, "detail": self.detail,
               "evidence": self.evidence}
        if self.hint:
            out["hint"] = self.hint
        return out


def doctor(*, sysfs_root: str | os.PathLike[str] = DEFAULT_SYSFS_ROOT,
           hidraw_root: str | os.PathLike[str] = DEFAULT_HIDRAW_CLASS,
           input_root: str | os.PathLike[str] = DEFAULT_INPUT_CLASS) -> dict:
    """Diagnose whether this machine can talk to ARMORX hardware.

    A machine with no hardware present is a passing diagnosis: every check is
    reported with a status and the caller decides what to do.
    """
    checks: list[DoctorCheck] = []
    root = Path(sysfs_root)
    checks.append(DoctorCheck(
        "usb_sysfs",
        "ok" if root.is_dir() else "missing",
        f"{sysfs_root} {'is readable' if root.is_dir() else 'is not present'}",
        EVIDENCE_PROVEN,
        None if root.is_dir() else "USB discovery needs Linux sysfs; other platforms are "
                                    "not supported for discovery yet.",
    ))
    hidraw_root_path = Path(hidraw_root)
    nodes = sorted(p.name for p in hidraw_root_path.iterdir()) if hidraw_root_path.is_dir() else []
    checks.append(DoctorCheck(
        "hidraw_class",
        "ok" if nodes else "empty",
        f"{len(nodes)} hidraw node(s): {', '.join(nodes) if nodes else 'none'}",
        EVIDENCE_PROVEN,
        None if nodes else "No HID devices are bound to the generic HID driver.",
    ))
    if nodes:
        unreadable = [n for n in nodes if not os.access(Path("/dev") / n, os.R_OK)]
        checks.append(DoctorCheck(
            "hidraw_permissions",
            "ok" if not unreadable else "restricted",
            "all hidraw nodes readable" if not unreadable
            else f"not readable by this user: {', '.join(unreadable)}",
            EVIDENCE_PROVEN,
            None if not unreadable else "Reading hidraw nodes needs group access or a udev "
                                        "rule; no write access is required for diagnostics.",
        ))
    candidates = scan_devices(sysfs_root=sysfs_root, hidraw_root=hidraw_root,
                              input_root=input_root)
    known = [c for c in candidates if c.identity.known]
    checks.append(DoctorCheck(
        "known_identities",
        "ok" if known else "none",
        ("recognized: " + ", ".join(c.identity.vid_pid for c in known)) if known
        else "no ARMORX or Xbox identities found on the USB bus",
        EVIDENCE_PROVEN,
        None if known else "No supported device found is a normal result when nothing is "
                           "plugged in.",
    ))
    xpad_loaded = "xpad" in _module_names()
    xbox_present = any(c.identity.vid_pid == "045e:0b12" for c in known)
    if xpad_loaded:
        xpad_status = "present"
        xpad_detail = "xpad is loaded"
        xpad_hint = None
    elif xbox_present:
        xpad_status = "missing"
        xpad_detail = (
            "xpad is not loaded while an Xbox personality is present; standard Linux "
            "gamepad input nodes may not be available"
        )
        xpad_hint = "Load the xpad driver, then run 'armorx device doctor' again."
    else:
        xpad_status = "not_needed"
        xpad_detail = "xpad is not loaded, but no Xbox personality is present"
        xpad_hint = None
    checks.append(DoctorCheck(
        "xpad_module",
        xpad_status,
        xpad_detail,
        EVIDENCE_STRONG,
        xpad_hint,
    ))
    xbox_stream = GIP_REPORT_FORMS
    checks.append(DoctorCheck(
        "gip_expectations",
        "info",
        "input reports have been observed in 32-byte startup and 48-byte steady-state forms; "
        "the transition cause is unknown",
        EVIDENCE_STRONG,
    ))
    blocking = [c for c in checks if c.status in ("missing", "error")]
    summary = {
        "ok": not blocking,
        "blocking_checks": [c.name for c in checks if c.status in ("missing", "error")],
        "findings": [c.name for c in checks if c.status in ("restricted", "empty", "none")],
        "checks": [c.to_dict() for c in checks],
        "candidates": [c.to_dict() for c in candidates],
        "devices_found": len(known),
        "report_forms": xbox_stream,
        "next_steps": (
            ["Plug an ARMORX Pro or F20 into USB to continue.",
             "Run 'armorx device list' after connecting to see the identity."]
            if not known else
            ["Run 'armorx device inspect <usb-path>' for the full explanation."]
        ),
    }
    return summary


def _module_names() -> set[str]:
    path = Path("/proc/modules")
    if not path.is_file():
        return set()
    names = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line:
            names.add(line.split()[0])
    return names


def find_by_path(candidates: Iterable[DeviceCandidate], selected: str) -> DeviceCandidate | None:
    """Resolve a candidate by sysfs path, usb path or VID:PID."""
    wanted = selected.strip().lower()
    for candidate in candidates:
        ident = candidate.identity
        if wanted in (candidate.sysfs_path.lower(), (ident.usb_path or "").lower(),
                      ident.vid_pid, f"{ident.vid:04x}", f"{ident.pid:04x}"):
            return candidate
    return None


# ---------------------------------------------------------------------------
# diagnostics bundle (safe to paste into an issue report)
# ---------------------------------------------------------------------------

_BUNDLE_KEY_PATTERNS = (
    re.compile(r"serial", re.I),
    re.compile(r"mac_?address|\bMAC\b"),
    re.compile(r"bdaddr|bluetooth_?address"),
    re.compile(r"token|secret|password|api_?key", re.I),
)
_HOME_RE = re.compile(r"/(?:home|Users|root)/[^/\s\"']+")


def _clean_value(value):
    if isinstance(value, str):
        return _HOME_RE.sub("<home>", value)
    if isinstance(value, dict):
        return {k: _clean_value(v) for k, v in value.items()
                if not any(p.search(k) for p in _BUNDLE_KEY_PATTERNS)}
    if isinstance(value, list):
        return [_clean_value(v) for v in value]
    return value


def diagnostics_bundle(*, include_hostname: bool = False, sysfs_root=None,
                       hidraw_root=None, input_root=None, toolkit_version: str = "",
                       usb_limit: int = 32) -> dict:
    """Build a sanitised diagnostics bundle intended for public issue reports.

    Deliberately omitted: usernames, home directory paths, hostname (unless asked
    for), USB serial numbers, Bluetooth or MAC addresses, and any environment
    value that looks like a credential.
    """
    kwargs = {}
    if sysfs_root is not None:
        kwargs["sysfs_root"] = sysfs_root
    if hidraw_root is not None:
        kwargs["hidraw_root"] = hidraw_root
    if input_root is not None:
        kwargs["input_root"] = input_root
    result = doctor(**kwargs)
    bundle = {
        "toolkit_version": toolkit_version or "unknown",
        "python": platform.python_version(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "doctor": result,
        "devices": [],
        "usb_inventory_truncated": False,
        "privacy": {
            "omitted": ["usernames", "home paths", "usb serial numbers", "bluetooth/MAC addresses",
                        "credentials"],
            "hostname_included": bool(include_hostname),
        },
    }
    if include_hostname:
        bundle["hostname"] = platform.node()
    for candidate in scan_devices(**kwargs):
        entry = candidate.to_dict()
        entry["identity"].pop("serial", None)
        entry["identity"]["serial"] = "<omitted>" if candidate.identity.serial else None
        bundle["devices"].append(entry)
    bundle = _clean_value(bundle)
    if len(bundle["devices"]) >= usb_limit:
        bundle["usb_inventory_truncated"] = True
    return bundle


def render_bundle_text(bundle: dict) -> str:
    """Human-readable rendering of a diagnostics bundle."""
    lines = [f"armorx toolkit {bundle.get('toolkit_version')}",
             f"python {bundle.get('python')} on {bundle.get('system')} {bundle.get('release')}",
             ""]
    for check in bundle["doctor"]["checks"]:
        lines.append(f"[{check['status']}] {check['check']}: {check['detail']}")
    lines.append("")
    lines.append(f"recognized devices: {len(bundle['devices'])}")
    for device in bundle["devices"]:
        identity = device["identity"]
        states = device["states"]
        if states and isinstance(states[0], dict):
            states = [s.get("name", "?") for s in states]
        lines.append(f"  {identity['vid_pid']} {identity['usb_path']} "
                     f"{identity.get('product') or '?'} -> {', '.join(states)}")
    lines.append("")
    lines.append("omitted for privacy: " + ", ".join(bundle["privacy"]["omitted"]))
    return "\n".join(lines)
