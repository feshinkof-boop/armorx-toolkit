"""Execution of the declarative C0/C1/C2 case steps, with no dependency on a BLE stack.

This lives apart from `d2-differential.py` on purpose: the script exits at import time when `bleak`
is missing, which would make the case executor untestable without a Bluetooth environment. Here the
executor takes any duck-typed client, so `tests/test_d2_runner.py` can drive every branch - including
the operator-cancel path - offline, with no adapter, no device and no popup.

Safety rules encoded here:
  * only frames produced by `d2_cases` are ever written (the case definition is the whitelist);
  * the operator dialog is awaited ASYNCHRONOUSLY so notification callbacks keep running while the
    popup is on screen - a blocking wait would drop exactly the frames the experiment looks for;
  * a non-zero dialog exit means the operator pressed CANCEL/STOP: raise OperatorCancelled so the
    caller can return the device to a safe state instead of continuing;
  * an empty observation window is NORMAL (D2 input is event-driven) and is never reported as a
    failure.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import time
from typing import Any, Iterable, Sequence

FFE1 = "0000ffe1-0000-1000-8000-00805f9b34fb"   # control write characteristic
FFE2 = "0000ffe2-0000-1000-8000-00805f9b34fb"   # notify characteristic

PROMPT_SCRIPT = str(pathlib.Path(__file__).resolve().parent.parent / "operator-dialog-kdialog.sh")
PROMPT_COMMAND = ["bash", PROMPT_SCRIPT]

OBSERVE_DEFAULT_S = 10.0


class OperatorCancelled(Exception):
    """Raised when the operator pressed CANCEL/STOP on a popup: stop safely, never continue."""


def observe_window() -> float:
    """Observation window in seconds (D2_OBSERVE_S overrides the default)."""
    try:
        v = float(os.environ.get("D2_OBSERVE_S", OBSERVE_DEFAULT_S))
    except ValueError:
        return OBSERVE_DEFAULT_S
    return v if v > 0 else OBSERVE_DEFAULT_S


async def run_steps(client: Any, rec: Any, steps: Iterable[dict]) -> None:
    """Execute a case step list against `client`, recording everything through `rec`."""
    for st in steps:
        op = st["op"]
        if op == "sanity":
            continue  # performed by the caller before the case body
        if op == "write":
            frame = bytes.fromhex(st["frame"])
            mode = "with_response" if st.get("response") else "without_response"
            await client.write_gatt_char(FFE1, frame, response=bool(st.get("response", False)))
            rec.log("TX", FFE1, frame, label=st["label"], write_mode=mode)
        elif op == "sleep":
            rec.mark("sleep", st.get("why", ""))
            await asyncio.sleep(float(st["seconds"]))
        elif op == "wait_fragments":
            prefix, want = st["prefix"], int(st["expect_min"])
            rec.mark("wait_fragments", f"{prefix} expect>={want}")
            deadline = time.monotonic() + float(st["seconds"])
            while time.monotonic() < deadline:
                if sum(1 for f in rec.frames if f["hex"].startswith(prefix)) >= want:
                    break
                await asyncio.sleep(0.05)
            got = sum(1 for f in rec.frames if f["hex"].startswith(prefix))
            rec.mark("fragments_received", f"{got} (expected >= {want})")
        elif op == "cccd_renew":
            try:
                await client.stop_notify(FFE2)
                rec.mark("cccd_unsubscribe_done")
                await asyncio.sleep(1.0)
                await client.start_notify(FFE2, rec.on_notify)
                rec.mark("cccd_resubscribe_done")
            except Exception as exc:
                rec.mark("cccd_renew_error", str(exc))
        elif op == "operator_prompt":
            rec.mark("operator_prompt_raised", st["action_id"])
            proc = await asyncio.create_subprocess_exec(
                *PROMPT_COMMAND, "--id", st["action_id"], "--title", st["title"],
                "--message", st["message"], "--button", st["button"],
                "--cancel", st.get("cancel_button", "CANCEL / STOP"),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            ack = await proc.wait()
            rec.mark("operator_prompt_result", f"action_id={st['action_id']} rc={ack}")
            if ack != 0:
                rec.mark("operator_cancelled", st["action_id"])
                raise OperatorCancelled(st["action_id"])
        elif op == "observe":
            n = observe_window()
            rec.mark("observe_start", f"{n}s")
            await asyncio.sleep(n)
            valid = sum(1 for f in rec.frames if f["kind"] == "valid_status")
            rec.mark("observe_end",
                     f"valid_status_frames={valid} (event-driven: zero idle frames is NORMAL, not failure)")
        else:
            raise RuntimeError(f"unknown step {op!r}")


def verdict_from_frames(frames: Sequence[dict]) -> dict:
    """Classify an observation outcome using the corrected, event-driven vocabulary.

    A physical press must have happened for a case to mean anything: absence of frames is only
    interpretable alongside whether the operator actually pressed a button.
    """
    valid = [f for f in frames if f.get("kind") == "valid_status"]
    masks = [int(f["mask"], 16) for f in valid if f.get("mask")]
    keys = sorted({k for f in valid for k in (f.get("keys") or [])})
    transitions = 0
    prev = None
    for m in masks:
        bit0 = m & 1
        if bit0 != prev:
            transitions += 1
            prev = bit0
    if not valid:
        return {"verdict": "NO_IDLE_FRAMES_OBSERVED",
                "meaning": "expected when nothing was pressed; NOT a failure",
                "valid_frames": 0}
    if keys == [0] and transitions >= 4:
        return {"verdict": "A_TWICE_PROVEN", "valid_frames": len(valid), "keys": keys,
                "transitions": transitions, "meaning": "PRESS/RELEASE/PRESS/RELEASE for key A"}
    if keys == [0]:
        return {"verdict": "BUTTON_FRAMES_RECEIVED", "valid_frames": len(valid), "keys": keys,
                "transitions": transitions}
    return {"verdict": "BUTTON_FRAMES_RECEIVED_OTHER_KEYS", "valid_frames": len(valid), "keys": keys,
            "transitions": transitions}
