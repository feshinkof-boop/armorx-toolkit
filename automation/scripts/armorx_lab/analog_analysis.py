#!/usr/bin/env python3
"""Pure analysis for RT analog piggyback sampling - no BLE imports, so it is fully unit-testable.

Method: analog-only movement emits no D2 frame at all (proven: full stick travel and full RT travel
produced zero frames). So analog state can only be sampled inside frames whose TRANSMISSION was caused
by a digital event. A (bit 0) is the known-good digital trigger; the analog fields are read from the
frames that A caused.

Everything here takes plain dicts of the shape written by rt-analog-piggyback.py:
  {"per_frame": [{"t": float, "mask": int, "lt": int, "rt": int, "hex": str}, ...], ...}
"""
from __future__ import annotations

import statistics
from collections import Counter

LT_INDEX, RT_INDEX = 15, 16
A_BIT = 0                       # the digital report trigger used in every window
DEFAULT_MIN_DELTA = 8           # a "material" move of the dominant byte value
DEFAULT_MIN_FRACTION = 0.6      # how much of the window must sit on that value to count as consistent


def bytes_stats(values: list[int]) -> dict:
    """Measured statistics for one analog byte. Nothing is assumed about the numeric rest value."""
    values = [v for v in values if v is not None]
    if not values:
        return {"n": 0, "mode": None, "median": None, "min": None, "max": None,
                "distinct": {}, "dominant": None, "dominant_fraction": None, "range": None}
    c = Counter(values)
    dom, dom_n = c.most_common(1)[0]
    return {"n": len(values), "mode": dom, "median": statistics.median(values),
            "min": min(values), "max": max(values),
            "distinct": {str(k): v for k, v in sorted(c.items())},
            "dominant": dom, "dominant_fraction": round(dom_n / len(values), 3),
            "range": max(values) - min(values)}


def a_triggered(per_frame: list[dict]) -> list[dict]:
    """Frames whose transmission was caused by the digital trigger - the piggyback carriers."""
    return [f for f in per_frame if (f.get("mask") or 0) & (1 << A_BIT)]


def bit_frames(per_frame: list[dict], bit: int) -> list[dict]:
    return [f for f in per_frame if (f.get("mask") or 0) & (1 << bit)]


def idle_frames(per_frame: list[dict]) -> list[dict]:
    return [f for f in per_frame if not (f.get("mask") or 0)]


def bits_seen(per_frame: list[dict]) -> list[int]:
    return sorted({b for f in per_frame for b in (f.get("bits") or [])})


def hold_segments(per_frame: list[dict], bit: int) -> list[dict]:
    """Contiguous spans where `bit` is set, with the number of trigger-caused frames inside each."""
    segs, state, start = [], None, None
    for f in per_frame:
        s = 1 if (f.get("mask") or 0) & (1 << bit) else 0
        if s != state:
            if state == 1 and start is not None:
                segs.append({"start": start, "end": f["t"]})
            start = f["t"] if s == 1 else None
            state = s
    if state == 1 and start is not None:
        segs.append({"start": start, "end": None})
    for s in segs:
        end = s["end"] if s["end"] is not None else float("inf")
        inner = [f for f in a_triggered(per_frame) if s["start"] <= f["t"] < end]
        s["a_frames"] = len(inner)
        s["rt_values"] = sorted({f.get("rt") for f in inner if f.get("rt") is not None})
        s["lt_values"] = sorted({f.get("lt") for f in inner if f.get("lt") is not None})
    return segs


def a_burst_segments(per_frame: list[dict], gap: float = 0.5) -> list[dict]:
    """The trigger-caused bursts, split by a gap in time. Independent of any digital bit, so the
    "does the effect repeat" criterion never depends on the finding being measured."""
    trig = sorted(a_triggered(per_frame), key=lambda f: f["t"])
    segs = []
    for f in trig:
        if segs and f["t"] - segs[-1]["last"] <= gap:
            segs[-1]["last"] = f["t"]
            segs[-1]["frames"].append(f)
        else:
            segs.append({"start": f["t"], "last": f["t"], "frames": [f]})
    for s in segs:
        s["a_frames"] = len(s["frames"])
        s["rt_values"] = sorted({f.get("rt") for f in s["frames"] if f.get("rt") is not None})
        s["lt_values"] = sorted({f.get("lt") for f in s["frames"] if f.get("lt") is not None})
        s.pop("frames")
    return segs


def compare(label: str, base_stats: dict, win_stats: dict,
            min_delta: int = DEFAULT_MIN_DELTA, min_fraction: float = DEFAULT_MIN_FRACTION) -> dict:
    """Did this byte materially AND consistently leave its baseline value?

    Material = the window's dominant value is at least `min_delta` away from the baseline's dominant
    value. Consistent = at least `min_fraction` of the window's frames sit on that dominant value.
    Both are required, so one stray frame can never carry a verdict.
    """
    if not base_stats.get("n") or not win_stats.get("n"):
        return {"label": label, "verdict": "INSUFFICIENT_FRAMES",
                "baseline": base_stats, "window": win_stats, "delta": None}
    delta = win_stats["dominant"] - base_stats["dominant"]
    moved = abs(delta) >= min_delta and (win_stats.get("dominant_fraction") or 0) >= min_fraction
    return {"label": label, "verdict": "CHANGED" if moved else "NO_CHANGE",
            "baseline_dominant": base_stats["dominant"], "window_dominant": win_stats["dominant"],
            "delta": delta, "window_dominant_fraction": win_stats.get("dominant_fraction"),
            "min_delta_required": min_delta, "min_fraction_required": min_fraction,
            "baseline": base_stats, "window": win_stats}


def analyse_window(result: dict) -> dict:
    """Per-window summary built ONLY from trigger-caused frames (plus idle, as the return check)."""
    pf = result.get("per_frame") or []
    return {
        "valid_frames": len(pf), "bits_seen": bits_seen(pf), "masks": result.get("masks"),
        "a_triggered_frames": len(a_triggered(pf)),
        "a_triggered_lt": bytes_stats([f["lt"] for f in a_triggered(pf)]),
        "a_triggered_rt": bytes_stats([f["rt"] for f in a_triggered(pf)]),
        "all_frames_lt": bytes_stats([f["lt"] for f in pf]),
        "all_frames_rt": bytes_stats([f["rt"] for f in pf]),
        "idle_frames": len(idle_frames(pf)),
        "idle_rt": bytes_stats([f["rt"] for f in idle_frames(pf)]),
        "idle_lt": bytes_stats([f["lt"] for f in idle_frames(pf)]),
    }


def classify_lt_control(baseline: dict, control: dict) -> dict:
    """P1: does the A-triggered frame carry the LT analog value while LT is held? Validates the method."""
    base, win = analyse_window(baseline), analyse_window(control)
    if not base["a_triggered_frames"] or not win["a_triggered_frames"]:
        return {"verdict": "INSUFFICIENT_FRAMES", "baseline": base, "control": win}
    cmp_lt = compare("lt_positive_control", base["a_triggered_lt"], win["a_triggered_lt"])
    cmp_rt = compare("rt_must_stay_flat", base["a_triggered_rt"], win["a_triggered_rt"])
    ok = cmp_lt["verdict"] == "CHANGED" and cmp_rt["verdict"] == "NO_CHANGE"
    return {"verdict": "LT_ANALOG_PIGGYBACK_PROVEN" if ok else "D2_ANALOG_PIGGYBACK_METHOD_NOT_VALIDATED",
            "lt": cmp_lt, "rt_cross_check": cmp_rt, "baseline": base, "control": win}


def classify_rt(baseline: dict, rt_run: dict, repeats: list[dict] | None = None) -> dict:
    """P2: does byte [16] carry RT's analog value in A-caused frames?

    Criteria reported separately and mechanically rather than folded into one boolean:
      1 A-caused frames present, 3 the byte moves consistently, 4 it returns to baseline at rest,
      5 the effect repeats, and (reported, not required) whether RT also shows a digital bit.
    Criterion 2 of the brief - "RT itself produces no independent digital bit" - is REPORTED, not
    assumed: if a bit appears while RT is held, that is recorded as a new observation rather than
    being silently ignored or used to invalidate the analog result.
    """
    base, win = analyse_window(baseline), analyse_window(rt_run)
    runs = [win] + [analyse_window(r) for r in (repeats or [])]
    if not base["a_triggered_frames"] or not any(r["a_triggered_frames"] for r in runs):
        return {"verdict": "INSUFFICIENT_FRAMES", "baseline": base, "runs": runs}
    cmp_rt = compare("rt_analog", base["a_triggered_rt"], win["a_triggered_rt"])
    cmp_lt = compare("lt_cross_check_must_stay_flat", base["a_triggered_lt"], win["a_triggered_lt"])
    returned = (win["idle_rt"]["dominant"] == base["a_triggered_rt"]["dominant"]) if win["idle_rt"]["n"] else None
    changed_dom = win["a_triggered_rt"]["dominant"]
    # repeat = at least two trigger bursts in this window AND at least two in every repeat window,
    # each burst sitting on the changed value. Bit-independent by construction.
    def bursts_at_value(res):
        return [s for s in a_burst_segments(res.get("per_frame") or [])
                if s["rt_values"] == [changed_dom]]
    repeated_holds = bursts_at_value(rt_run)
    repeat_ok = len(repeated_holds) >= 2
    for extra in (repeats or []):
        repeat_ok = repeat_ok and len(bursts_at_value(extra)) >= 2
    digital_bit = 9 in (win["bits_seen"] or [])
    proven = (cmp_rt["verdict"] == "CHANGED" and cmp_lt["verdict"] == "NO_CHANGE"
              and repeat_ok and returned is not False)
    # Name the outcome for what was actually observed. The brief's name is
    # RT_ANALOG_ONLY_PROVEN_LIVE, but that name asserts "no digital bit", and on the real unit a
    # digital bit (9) DID appear while RT was held - so the analog result must not be labelled
    # "analog only". Report the analog finding under its own name and carry the digital bit beside it.
    if proven and digital_bit:
        name = "RT_ANALOG_PROVEN_LIVE__PLUS_DIGITAL_BIT_OBSERVED"
    elif proven:
        name = "RT_ANALOG_ONLY_PROVEN_LIVE"
    else:
        name = "RT_ANALOG_NOT_OBSERVED_IN_D2_PIGGYBACK"
    return {"verdict": name,
            "criteria": {"1_a_frames_present": win["a_triggered_frames"] > 0,
                         "2_no_rt_digital_bit": not digital_bit,
                         "3_byte16_moves_consistently": cmp_rt["verdict"] == "CHANGED",
                         "4_returns_to_baseline_at_rest": returned,
                         "5_effect_repeats": repeat_ok,
                         "6_byte15_flat": cmp_lt["verdict"] == "NO_CHANGE"},
            "rt_digital_bit_observed": digital_bit,
            "rt_analog": cmp_rt, "lt_cross_check": cmp_lt,
            "observed_range": [win["a_triggered_rt"]["min"], win["a_triggered_rt"]["max"]],
            "repeat_bursts_at_changed_value": len(repeated_holds),
            "rt_digital_bit_holds": len(hold_segments(rt_run.get("per_frame") or [], 9)),
            "baseline": base, "runs": runs}
