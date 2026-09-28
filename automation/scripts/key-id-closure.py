#!/usr/bin/env python3
"""One physical control, one popup, one analysis. For the key-ID closure session.

Sequence per control (the shorter proven-good form - C0 proved the pre-clear is harmless, so it is
omitted to reduce wire traffic):

    discover -> connect -> read identity -> subscribe FFE2 -> sanity 0B (reply required)
    -> D2 ON -> ONE popup naming ONE physical control -> observe -> D2 OFF -> disconnect

Rules enforced here, because the historical misattributions came from breaking them:
  * ONE control per popup. There is no mode that accepts two.
  * a bit counts as mapping evidence only if the mask is an ISOLATED SINGLE BIT during that control's
    own window; several bits => AMBIGUOUS_MULTI_BIT and no name is assigned.
  * press ORDER is never used to attribute a bit to a control.
  * the analog channels are read at the frame contract's offsets: [15] = LT analog, [16] = RT analog.

Usage:
  key-id-closure.py --control "RT" --outdir DIR [--observe 12]
Exit: 0 = analysed (see classification), 1 = OPERATOR_CANCELLED, 5 = connect failed, 6 = sanity failed
"""
from __future__ import annotations

import argparse, asyncio, json, pathlib, re, subprocess, sys, time
from datetime import datetime, timezone

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
from armorx_lab.frames import parse_button_frame          # noqa: E402

try:
    from bleak import BleakClient, BleakScanner
except Exception as exc:                                   # pragma: no cover
    print(f"FATAL: bleak unavailable: {exc}")
    sys.exit(3)

FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"
FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"
ID_CHARS = {"2a24": "00002a24-0000-1000-8000-00805f9b34fb",
            "2a26": "00002a26-0000-1000-8000-00805f9b34fb"}
D2_ON = bytes.fromhex("A505D2017D")
D2_OFF = bytes.fromhex("A505D2007C")
Q_0B = bytes.fromhex("A5040BB4")
MFR_PREFIX = bytes.fromhex("5a4a2d5854")
KNOWN_ADDRESS = "2D:37:35:6D:66:11"
# The canonical dialog helper lives one level up (automation/), NOT beside this script. Pointing at the
# wrong path made `bash <missing>` exit 127, which an earlier version of this file misreported as an
# operator cancel - so the popup never appeared and the operator was never asked. Resolve it explicitly
# and refuse to run if it is missing, rather than silently treating a missing file as a human decision.
DIALOG = str(_HERE.parent / "operator-dialog-kdialog.sh")
LT_ANALOG_INDEX, RT_ANALOG_INDEX = 15, 16     # verified against d2-frame-contract.md


def iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


async def find_device(timeout: float = 20.0):
    devs = await BleakScanner.discover(timeout=timeout, return_adv=True)
    by_addr = by_mfr = None
    for address, (dev, adv) in devs.items():
        name = dev.name or adv.local_name or ""
        if name.startswith("ARMOR-X Pro"):
            return dev, adv
        if address.upper() == KNOWN_ADDRESS:
            by_addr = (dev, adv)
        if any(bytes(v).startswith(MFR_PREFIX) for v in (adv.manufacturer_data or {}).values()):
            by_mfr = (dev, adv)
    return by_addr or by_mfr or (None, None)


def classify_window(frames: list[dict], analog_seen: dict) -> dict:
    """Turn one control's captured window into a classification and its supporting numbers."""
    valid = [f for f in frames if f["valid"]]
    masks = [f["mask"] for f in valid]
    nonzero = [m for m in masks if m]
    bits = sorted({i for m in nonzero for i in range(32) if m >> i & 1})

    # transitions of the union mask over time (only meaningful when a single bit is involved)
    states, prev = [], None
    for m in masks:
        b = 1 if m else 0
        if prev is None or b != prev:
            states.append(b)
        prev = b

    single = len(bits) == 1
    analog_moved = any(v["moved"] for v in analog_seen.values())

    if valid and single and nonzero and states == [1, 0, 1, 0]:
        verdict = "MAPPED"
    elif valid and single and nonzero:
        verdict = "SINGLE_BIT_INCOMPLETE_SEQUENCE"
    elif len(bits) > 1:
        verdict = "AMBIGUOUS_MULTI_BIT"
    elif not valid and analog_moved:
        verdict = "ANALOG_ONLY"
    elif not valid:
        verdict = "NO_REPORT_OBSERVED"
    else:
        verdict = "UNCLASSIFIED"

    return {"verdict": verdict, "valid_frames": len(valid), "frames_total": len(frames),
            "nonzero_mask_frames": len(nonzero), "bits": bits, "isolated_single_bit": single,
            "transitions": states, "analog": analog_seen}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--control", required=True)
    ap.add_argument("--outdir", required=True, type=pathlib.Path)
    ap.add_argument("--observe", type=float, default=12.0)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    ctl, s = args.control, slug(args.control)

    if not pathlib.Path(DIALOG).exists():
        print(f"DIALOG_MISSING: {DIALOG}")
        return 7

    dev, _adv = await find_device()
    if not dev:
        print("CONNECT_FAILED: device not found")
        return 5

    frames: list[dict] = []
    t0 = time.monotonic()
    analog_seen = {"lt": {"index": LT_ANALOG_INDEX, "min": None, "max": None, "moved": False},
                   "rt": {"index": RT_ANALOG_INDEX, "min": None, "max": None, "moved": False}}

    def on_notify(_c, data: bytearray) -> None:
        raw = bytes(data)
        f = parse_button_frame(raw) if (len(raw) == 18 and raw[0] == 0xA5 and raw[2] == 0x02) else None
        rec = {"t": round(time.monotonic() - t0, 3), "ts": iso(), "hex": raw.hex(),
               "valid": bool(f and f.checksum_ok),
               "mask": f.mask if f else None,
               "len": len(raw), "checksum_ok": bool(f and f.checksum_ok)}
        if f and f.checksum_ok:
            for key, idx in (("lt", LT_ANALOG_INDEX), ("rt", RT_ANALOG_INDEX)):
                v = raw[idx]
                a = analog_seen[key]
                a["min"] = v if a["min"] is None else min(a["min"], v)
                a["max"] = v if a["max"] is None else max(a["max"], v)
                if v != 0:
                    a["moved"] = True
        frames.append(rec)

    client = BleakClient(dev, timeout=25.0)
    await client.connect()
    identity = {}
    tx = []
    cancelled = False
    try:
        for k, uuid in ID_CHARS.items():
            try:
                identity[k] = bytes(await client.read_gatt_char(uuid)).hex()
            except Exception:
                identity[k] = None
        await client.start_notify(FFE2, on_notify)
        await asyncio.sleep(0.5)
        # sanity: the control channel must answer before we change runtime mode
        got_0b = False
        await client.write_gatt_char(FFE1, Q_0B, response=False)
        tx.append(Q_0B.hex())
        dl = time.monotonic() + 4.0
        while time.monotonic() < dl:
            if any(f["hex"].startswith("a5050b") for f in frames):
                got_0b = True
                break
            await asyncio.sleep(0.1)
        if not got_0b:
            print("SANITY_FAILED: no 0B reply")
            return 6
        await client.write_gatt_char(FFE1, D2_ON, response=False)
        tx.append(D2_ON.hex())
        await asyncio.sleep(0.4)

        # --- the ONE popup for this ONE control ---
        if ctl.strip().lower().startswith(("l stick", "r stick")):
            # an analog stick: ask for full travel and return, twice - a stick is not a button
            which = "LEFT" if ctl.strip().lower().startswith("l stick") else "RIGHT"
            msg = (f"Push the {which} stick fully in ONE direction, then let it return to centre.\n\n"
                   f"Do that TWICE.\n\nAfter the second return, click DONE.")
        elif ctl.strip().upper().startswith("RT"):
            # RT is an analog trigger: the digital bit has never appeared, so ask for full travel
            msg = ("Press RT fully TWICE.\n\nFor each press: pull it fully, then release it fully.\n\n"
                   "After the second release, click DONE.")
        else:
            msg = (f"Press {ctl} TWICE.\n\nDo not press any other controller control.\n\n"
                   f"After the second press/release, click DONE.")
        proc = await asyncio.create_subprocess_exec(
            "bash", DIALOG, "--id", f"armorx_keymap_{s}", "--title", f"ArmorX Key Map \u2014 {ctl}",
            "--message", msg, "--button", "DONE", "--cancel", "CANCEL / STOP",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        rc = await proc.wait()
        # Exit codes are meaningful and must not be conflated:
        #   0 = DONE clicked (ACK), 1 = operator pressed CANCEL/STOP, 2 = dialog failed,
        #   3 = no graphical session, 127 = the helper script was not found at all.
        # Only rc == 1 is an operator decision. Anything else is a harness fault and must be reported
        # as such - never as OPERATOR_CANCELLED.
        if rc == 1:
            cancelled = True
        elif rc != 0:
            print(f"DIALOG_FAILED: rc={rc} (this is a harness fault, NOT an operator cancel)")
            return 7
        # post-popup idle window: zero frames here is NORMAL (D2 input is event-driven)
        await asyncio.sleep(args.observe)
    finally:
        try:
            await client.write_gatt_char(FFE1, D2_OFF, response=False)
            tx.append(D2_OFF.hex())
            await asyncio.sleep(0.6)
        except Exception:
            pass
        try:
            await client.disconnect()
        except Exception:
            pass

    result = {"control": ctl, "action_id": f"armorx_keymap_{s}", "started": iso(),
              "identity": identity, "tx": tx, "cancelled": cancelled,
              "analysis": classify_window(frames, analog_seen)}
    (args.outdir / f"window-{s}.jsonl").write_text(
        "\n".join(json.dumps(f) for f in frames) + ("\n" if frames else ""))
    (args.outdir / f"result-{s}.json").write_text(json.dumps(result, indent=1) + "\n")

    a = result["analysis"]
    print(f"CONTROL {ctl}: {a['verdict']}")
    print(f"  valid={a['valid_frames']} nonzero={a['nonzero_mask_frames']} bits={a['bits']} "
          f"transitions={a['transitions']}")
    print(f"  analog LT[15]={analog_seen['lt']} RT[16]={analog_seen['rt']}")
    if cancelled:
        print("OPERATOR_CANCELLED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
