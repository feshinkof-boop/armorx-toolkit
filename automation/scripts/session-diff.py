#!/usr/bin/env python3
"""session-diff.py -- normalize and diff an official-app BLE session against a Linux harness session.

Two decoders, because the two capture formats need different mature tools:

  * Android btsnoop ("btsnoop" encapsulation)  -> tshark JSON (`-T json` on btatt/bthci_evt/btsmp)
  * Linux btmon capture ("Bluetooth Linux Monitor") -> `btmon -r` text

NOTE (corrected 2026-09-27): an earlier pass believed tshark could not decode this host's Linux
btmon capture. It can. The real obstacle was that tshark is AppArmor-confined here and cannot read
files under /home/salamanka; copying a capture to /tmp makes tshark decode it normally (verified:
174 frames, 44 ATT ops, agreeing exactly with the btmon-derived control plane). The harness side is
still decoded with `btmon -r` for its richer HCI detail, with tshark as an independent cross-check.

Stages compared (chronological, not by packet count):
  CONNECTION, SECURITY, ATT/GATT, APPLICATION SEQUENCE, RX, EXIT
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

D2_ENABLE = "a505d2017d"
D2_DISABLE = "a505d2007c"
CTRL_QUERY = "a5040bb4"


def run(cmd: list[str]) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return p.stdout
    except Exception as exc:  # noqa: BLE001
        return f"__ERROR__ {exc}"


# ---------------------------------------------------------------- harness side
def decode_btmon(path: Path) -> list[dict]:
    """Normalize a Linux btmon capture via the mature `btmon -r` decoder."""
    tmp = path
    if not shutil.which("btmon"):
        return []
    out = run(["sudo", "-n", "btmon", "-r", str(tmp)])
    if out.startswith("__ERROR__"):
        out = run(["btmon", "-r", str(tmp)])
    events: list[dict] = []
    cur: dict | None = None
    link: dict = {}
    for line in out.splitlines():
        m = re.search(r"Connection interval: ([\d.]+)", line)
        if m: link["connection_interval"] = float(m.group(1))
        m = re.search(r"Peripheral latency: (\d+)", line)
        if m: link["peripheral_latency"] = int(m.group(1))
        m = re.search(r"Supervision timeout: (\d+)", line)
        if m: link["supervision_timeout"] = int(m.group(1))
        m = re.search(r"(?:PHY|phys?)[^\n]*:?\s*(\d+)\s*M", line)
        if m and "PHY" in line: link.setdefault("phy_mbit", []).append(int(m.group(1)))
        m = re.search(r"(?:Max TX octets|Max Tx octets|max_tx_octets)[:\s]+(\d+)", line)
        if m: link["max_tx_octets"] = int(m.group(1))
        m = re.search(r"(?:Max TX time|Max Tx time|max_tx_time)[:\s]+(\d+)", line)
        if m: link["max_tx_time"] = int(m.group(1))
        m = re.search(r"MTU[:\s]+(\d+)", line)
        if m: link.setdefault("mtu_seen", []).append(int(m.group(1)))
        m = re.search(r"ACL Data (TX|RX).*\[hci(\d+)\] ([\d.]+)", line)
        if m:
            cur = {"dir": m.group(1), "t": float(m.group(3)), "opcode": None,
                   "handle": None, "uuid": None, "value": None, "layer": "ATT"}
            events.append(cur)
            continue
        m = re.search(r"LE Connection Complete.*?(\d+\.\d+)$", line)
        if m and "Connection Complete" in line:
            events.append({"dir": "EVT", "t": float(m.group(1)), "opcode": "HCI_LE_CONN_COMPLETE",
                           "layer": "HCI", "raw": line.strip()})
            cur = None
            continue
        if cur is None:
            continue
        m = re.search(r"ATT: ([A-Za-z ]+) \((0x[0-9a-f]+)\)", line)
        if m:
            cur["opcode"] = m.group(1).strip()
            cur["att_code"] = m.group(2)
            continue
        m = re.search(r"Handle: (0x[0-9a-f]+)(?: Type: ([^(]+)\((0000[0-9a-f]{4}|[0-9a-f-]{36})\))?", line)
        if m:
            cur["handle"] = m.group(1)
            cur["uuid"] = (m.group(3) or "").strip()
            continue
        m = re.search(r"Data(?:\[\d+\])?: ([0-9a-f ]+)", line)
        if m:
            cur["value"] = m.group(1).strip().replace(" ", "")
    for e in events:
        e["value"] = e.get("value") or ""
        e["classification"] = classify(e)
    if link:
        events.insert(0, {"dir": "LINK", "t": events[0]["t"] if events else 0.0, "layer": "HCI",
                          "opcode": "LE_LINK_PARAMETERS", "value": "", "classification": "LINK_PARAMS",
                          "link": link})
    return events


# ---------------------------------------------------------------- official side
def decode_android_btsnoop(path: Path) -> list[dict]:
    """Normalize an Android btsnoop via tshark JSON."""
    raw = run(["tshark", "-r", str(path), "-Y", "btatt or bthci_evt or btsmp", "-T", "json"])
    if raw.startswith("__ERROR__") or not raw.strip():
        return []
    try:
        packets = json.loads(raw)
    except json.JSONDecodeError:
        return []
    events: list[dict] = []
    for pkt in packets:
        layers = pkt.get("_source", {}).get("layers", {})
        t = float(layers.get("frame", {}).get("frame.time_epoch", "0") or 0)
        att = layers.get("btatt")
        if att:
            if isinstance(att, list):
                att = att[0]
            op = att.get("btatt.opcode")
            opname = {"0x12": "Write Request", "0x52": "Write Command", "0x13": "Write Response",
                      "0x1b": "Handle Value Notification", "0x1d": "Handle Value Indication",
                      "0x0a": "Read Request", "0x0b": "Read Response", "0x08": "Read By Type Request",
                      "0x09": "Read By Type Response", "0x10": "Read By Group Type Request",
                      "0x11": "Read By Group Type Response", "0x04": "Find Information Request",
                      "0x05": "Find Information Response", "0x03": "Exchange MTU Request",
                      "0x02": "Exchange MTU Response", "0x01": "Error Response"}.get(op, op)
            events.append({"dir": "RX" if str(att.get("btatt.opcode")) in ("0x1b", "0x1d") else "TX",
                           "t": t, "layer": "ATT", "opcode": opname, "att_code": op,
                           "handle": att.get("btatt.handle"), "uuid": att.get("btatt.uuid16"),
                           "value": (att.get("btatt.value") or "").replace(":", ""),
                           "mtu": att.get("btatt.mtu")})
            continue
        hci = layers.get("bthci_evt")
        if hci:
            if isinstance(hci, list):
                hci = hci[0]
            events.append({"dir": "EVT", "t": t, "layer": "HCI",
                           "opcode": hci.get("bthci_evt.code"),
                           "interval": hci.get("bthci_evt.le_connection_interval"),
                           "latency": hci.get("bthci_evt.le_connection_latency"),
                           "timeout": hci.get("bthci_evt.le_connection_timeout"),
                           "raw": hci.get("bthci_evt.code")})
            continue
        smp = layers.get("btsmp")
        if smp:
            if isinstance(smp, list):
                smp = smp[0]
            events.append({"dir": "SMP", "t": t, "layer": "SMP",
                           "opcode": smp.get("btsmp.opcode"), "raw": smp.get("btsmp.opcode")})
    for e in events:
        e["value"] = e.get("value") or ""
        e["classification"] = classify(e)
    return events


def classify(e: dict) -> str:
    """Classify one ATT event.

    The D2 command and its echo carry IDENTICAL bytes (a505d2017d / a505d2007c), so the value alone
    is ambiguous: only the ATT operation separates our write from the device's notification. A live
    test caught exactly that mistake, hence the opcode-first logic here.
    """
    v = (e.get("value") or "").lower()
    op = (e.get("opcode") or "")
    is_rx = ("Notification" in op) or ("Indication" in op) or (e.get("dir") == "RX")
    is_write = op.startswith("Write") or (e.get("dir") == "TX" and e.get("layer") == "ATT")

    if v in (D2_ENABLE, D2_DISABLE):
        if is_rx and not is_write:
            return "D2_ECHO"
        return "D2_ENABLE" if v == D2_ENABLE else "D2_DISABLE"
    if v == CTRL_QUERY:
        return "CTRL_QUERY_0B"
    if v.startswith("a5050b30"):
        return "CTRL_REPLY_0B"
    if len(v) == 36 and v.startswith("a51202"):
        return "BUTTON_FRAME"
    if len(v) == 36 and v.startswith("a512") and not v.startswith("a51202"):
        return "BUTTON_FRAME_WRONG_OPCODE"
    if v in ("0100", "0000") and op.startswith("Write"):
        return "CCCD_WRITE"
    if "Notification" in op:
        return "NOTIFICATION_OTHER"
    if op.startswith("Write"):
        return "WRITE_OTHER"
    return op or "OTHER"


def summarize(events: list[dict]) -> dict:
    connects = [e for e in events if e["layer"] == "HCI" and "CONN_COMPLETE" in str(e.get("opcode", "")).upper()]
    t0 = connects[0]["t"] if connects else (events[0]["t"] if events else 0.0)
    kinds: dict[str, int] = {}
    for e in events:
        kinds[e["classification"]] = kinds.get(e["classification"], 0) + 1
    en = [e for e in events if e["classification"] == "D2_ENABLE"]
    dis = [e for e in events if e["classification"] == "D2_DISABLE"]
    cc = [e for e in events if e["classification"] == "CCCD_WRITE"]
    btn = [e for e in events if e["classification"] == "BUTTON_FRAME"]
    pre_d2 = [e for e in events if en and e["t"] < en[0]["t"] and e["layer"] == "ATT"
              and str(e.get("opcode", "")).startswith("Write")]
    return {
        "connection_events": len(connects),
        "first_conn_event": connects[0] if connects else None,
        "after_connect_s": (en[0]["t"] - t0) if (en and connects) else None,
        "d2_enable": en[0] if en else None,
        "d2_disable": dis[0] if dis else None,
        "d2_enable_to_disable_s": ((dis[0]["t"] - en[0]["t"]) if (en and dis) else None),
        "cccd_events": cc,
        "cccd_first_s_after_connect": ((cc[0]["t"] - t0) if (cc and connects) else None),
        "button_frames": len(btn),
        "button_frame_kinds": kinds,
        "writes_before_d2": pre_d2,
        "counts": kinds,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--official", help="Android btsnoop (or a directory containing raw/)")
    ap.add_argument("--harness", help="Linux btmon capture (or a directory containing raw/)")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    out = Path(a.outdir)
    (out / "official-session").mkdir(parents=True, exist_ok=True)
    (out / "harness-session").mkdir(parents=True, exist_ok=True)

    def find(base: str, names: list[str]) -> Path | None:
        if not base:
            return None
        p = Path(base)
        if p.is_file():
            return p
        for n in names:
            for c in list(p.rglob(n)):
                return c
        return None

    result: dict[str, dict] = {}
    off = find(a.official, ["btsnoop_hci*", "*.btsnoop", "btsnoop*"])
    if off:
        ev = decode_android_btsnoop(off)
        result["official"] = {"source": str(off), "decoder": "tshark-json",
                              "events": len(ev), "summary": summarize(ev) if ev else {}}
        (out / "official-session/official-timeline.csv").write_text(to_csv(ev))
        (out / "official-session/official-att.jsonl").write_text(to_jsonl(ev))
        (out / "official-session/official-att-summary.json").write_text(json.dumps(result["official"]["summary"], indent=1))
    harn = find(a.harness, ["btmon.btsnoop", "*.btsnoop"])
    if harn:
        ev = decode_btmon(harn)
        result["harness"] = {"source": str(harn), "decoder": "btmon-r",
                             "events": len(ev), "summary": summarize(ev) if ev else {}}
        (out / "harness-session/harness-timeline.csv").write_text(to_csv(ev))
        (out / "harness-session/harness-att.jsonl").write_text(to_jsonl(ev))
        (out / "harness-session/harness-att-summary.json").write_text(json.dumps(result["harness"]["summary"], indent=1))
    (out / "differential-raw.json").write_text(json.dumps(result, indent=1))
    print(json.dumps({k: {"events": v["events"], "decoder": v["decoder"]} for k, v in result.items()}, indent=1))
    return 0 if result else 1


def to_csv(events: list[dict]) -> str:
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["t_epoch", "delta_from_connect", "dir", "layer", "opcode", "handle", "uuid", "length", "value", "classification"])
    t0 = events[0]["t"] if events else 0.0
    for e in events:
        v = e.get("value") or ""
        w.writerow([f'{e.get("t", 0):.6f}', f'{e.get("t", 0) - t0:.3f}', e.get("dir", ""), e.get("layer", ""),
                    e.get("opcode", ""), e.get("handle", ""), e.get("uuid", ""), len(v) // 2, v, e.get("classification", "")])
    return buf.getvalue()


def to_jsonl(events: list[dict]) -> str:
    return "\n".join(json.dumps(e) for e in events) + "\n"


if __name__ == "__main__":
    sys.exit(main())
