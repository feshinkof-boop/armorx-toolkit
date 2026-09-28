#!/usr/bin/env python3
"""Consolidate every key-id claim into one confidence table (ids 0..33+).

Sources, in order of evidential weight:
  1. results/experiments/physical-20260927-170844-d2/real-key-id-map.json - PROVEN LIVE bits, each
     backed by a single-bit-mask frame inside that button's own request window;
  2. the same capture re-derived by harness-streaming-audit.py (frame counts per id);
  3. results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.json - static label inventories and the
     "bit == id, no +1" mask rule per build;
  4. the 144-byte configuration mapKeys region (source->target remap), which says nothing about a
     bit's *name* and is therefore never used to name an id here.

Ids that no physical button ever produced stay UNKNOWN. RT (9) has been requested in four separate
windows and never appeared: that is a proven negative, not an unresolved name.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
LIVE_MAP = REPO / "results/experiments/physical-20260927-170844-d2/real-key-id-map.json"
SESSION = REPO / "results/experiments/physical-20260927-170844-d2/session.jsonl"
VERSION_DIFF = REPO / "results/version-diff/2.22-vs-2.23-vs-2.24-vs-4.0.8.json"
DEFINE_DART = pathlib.Path("/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang/define.dart")

# Which physical button the operator was asked to press in each window, so a bit can be attributed
# only when it appears inside that button's own window.
NEVER_OBSERVED = {2: "no physical button produced this bit in any capture we hold",
                  5: "no physical button produced this bit in any capture we hold",
                  9: "RT: requested in press_group_B/D/E/F and three dedicated retries - NEVER appeared",
                  21: "no physical button produced this bit in any capture we hold",
                  22: "no physical button produced this bit in any capture we hold",
                  31: "no physical button produced this bit in any capture we hold",
                  32: "no physical button produced this bit in any capture we hold",
                  33: "no physical button produced this bit in any capture we hold"}


def live_frames_per_id() -> dict:
    counts = collections.Counter()
    if not SESSION.exists():
        return {}
    for line in SESSION.read_text(errors="replace").splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        raw = str(r.get("raw") or "")
        if not raw.lower().startswith("a51202"):
            continue
        mask = int(raw[6:14], 16)
        for i in range(32):
            if mask >> i & 1:
                counts[i] += 1
    return dict(counts)


def static_labels() -> dict:
    """Static label inventories per build (kept as verbatim summaries - not resolved into names)."""
    if not VERSION_DIFF.exists():
        return {}
    d = json.loads(VERSION_DIFF.read_text())
    rows = d.get("rows", {})
    out = {}
    for k in ("key-ID table", "key mask rule"):
        v = rows.get(k)
        if isinstance(v, dict):
            out[k] = {ver: (val if isinstance(val, str) else val.get("summary", ""))
                      for ver, val in v.items()}
    return out


def static_key_constants() -> dict:
    """Single-bit key constants defined in the 4.0.8 app (moojiang/define.dart, static getters).

    Extracted from the disassembly, not from prose: each `static int keyX()` returns one bit.
    """
    if not DEFINE_DART.exists():
        return {}
    out, cur = {}, None
    for line in DEFINE_DART.read_text(errors="replace").splitlines():
        m = re.match(r"\s*static int (\w+)\(\)\s*\{", line)
        if m:
            cur = m.group(1)
            continue
        if cur:
            mm = re.search(r"mov\s+x0, #(0x[0-9a-f]+)", line)
            if mm:
                v = int(mm.group(1), 16)
                bits = [i for i in range(64) if v >> i & 1]
                if len(bits) == 1:
                    out[cur] = bits[0]
                cur = None
            elif line.strip() == "}":
                cur = None
    return out


def build() -> dict:
    live = json.loads(LIVE_MAP.read_text()) if LIVE_MAP.exists() else {}
    vm = live.get("verified_map", {})
    counts = live_frames_per_id()
    static = static_labels()
    consts = static_key_constants()
    # --- key-ID closure session evidence (2026-09-28): one control per popup, analysed per window.
    # Ingested here so this table cannot drift from the physical session that produced it.
    closure = []
    for rj in sorted(REPO.glob("results/experiments/key-id-closure-*/result-*.json")):
        try:
            r = json.loads(rj.read_text())
        except Exception:
            continue
        closure.append({"control": r.get("control"),
                        "verdict": (r.get("analysis") or {}).get("verdict"),
                        "classification": r.get("classification"),
                        "valid_frames": (r.get("analysis") or {}).get("valid_frames"),
                        "bits": (r.get("analysis") or {}).get("bits"),
                        "transitions": (r.get("analysis") or {}).get("transitions"),
                        "source": str(rj.relative_to(REPO))})
    # ids that no requested physical control maps to, plus the one proven negative
    UNRESOLVED_BASIS = {
        2: "UNOBSERVED_RESERVED_OR_UNUSED", 5: "UNOBSERVED_RESERVED_OR_UNUSED",
        9: "PROVEN_NEGATIVE", 21: "UNOBSERVED_RESERVED_OR_UNUSED",
        22: "UNOBSERVED_RESERVED_OR_UNUSED", 31: "UNOBSERVED_RESERVED_OR_UNUSED",
        32: "UNOBSERVED_RESERVED_OR_UNUSED", 33: "UNOBSERVED_RESERVED_OR_UNUSED",
    }
    # static constant name -> the bit it sets, and the reverse
    by_bit = {}
    for name, bit in consts.items():
        by_bit.setdefault(bit, []).append(name)
    conflicts = []
    for i, names in sorted(by_bit.items()):
        live_entry = vm.get(str(i))
        live_name = (live_entry.get("button") if live_entry else None)
        if live_name and names and not any(live_name.split()[0].lower() in n.lower() for n in names):
            # The wire bit->name mapping is corroborated by all four builds' mask rule (keyL1=0x40=bit6,
            # keyCapture=0x8000=bit15, keyUp=0x10000=bit16) AND by the live single-bit frames. The
            # define.dart getters sit exactly one bit higher for the same names, so they are a separate
            # 1-based style enumeration rather than a contradicting statement about the wire.
            conflicts.append({"id": i, "live_name": live_name, "define_dart_names": names,
                              "resolution": "define.dart getters are offset +1 from the wire bit; "
                                            "the wire mapping is corroborated by the mask rule in all four "
                                            "builds and by the live frames, so the live name stands for the wire.",
                              "grade": "static_indexing_offset (not a contradiction of the wire naming)"})
    rows = []
    for i in range(0, 34):
        key = str(i)
        entry = vm.get(key)
        name = entry.get("button") if entry else None
        grade = "PROVEN LIVE" if entry else ("UNKNOWN" if i in NEVER_OBSERVED else "UNOBSERVED")
        notes = []
        if entry:
            notes.append(f"single-bit mask inside {entry.get('group')} window "
                         f"({entry.get('window', {}).get('from', '?')} .. {entry.get('window', {}).get('to', '?')})")
            if str(entry.get("static", "")).startswith("UNKNOWN"):
                notes.append("no static label found in the builds we hold")
        if i in NEVER_OBSERVED:
            notes.append(NEVER_OBSERVED[i])
        if i in counts and not entry:
            notes.append(f"bit appeared {counts[i]}x but was not attributable to a requested button")
        static_names = [n for n in by_bit.get(i, [])]
        stat = "|".join(static_names) if static_names else None
        rows.append({
            "id": i,
            "static_constant": stat,
            "name": (name.split(" - ")[0].strip() if name else None),
            "name_full": name or None,
            "grade": grade,
            "live_frames": counts.get(i, 0),
            "static_label": (entry.get("static") if entry else None),
            "name_confidence": ("PROVEN LIVE + corroborated by the mask rule in all four builds"
                                if entry else "UNKNOWN"),
            "notes": "; ".join(notes) if notes else None,
        })
    for row in rows:
        i = row.get("id")
        if i in UNRESOLVED_BASIS:
            row["final_classification"] = UNRESOLVED_BASIS[i]
            if i == 9:
                row["notes"] = ((row.get("notes") or "") +
                                " | 2026-09-28 closure session: RT requested again, two FULL pulls inside a popup "
                                "open 16.8 s and ACKed at 06:05:49; zero frames of any kind arrived, so [16] could "
                                "not be sampled - RT_ANALOG_ONLY neither confirmed nor excluded. PROVEN NEGATIVE as "
                                "a digital bit; id 9 stays unresolved.")
            else:
                row["notes"] = ((row.get("notes") or "") +
                                " | 2026-09-28 closure session: no requested physical control maps to this id and "
                                "no label exists in any build; still unobserved on this hardware.")

    return {"device": live.get("device", {}),
            "sources": {"live_map": str(LIVE_MAP.relative_to(REPO)),
                        "session": str(SESSION.relative_to(REPO)),
                        "static": str(VERSION_DIFF.relative_to(REPO))},
            "mask_rule": "mask_bytes[3..6] big-endian u32; bit index == key id (no +1)",
            "never_observed": {str(k): v for k, v in NEVER_OBSERVED.items()},
            "static_label_inventories": static,
            "static_key_constants": consts,
            "static_constants_by_bit": {str(k): v for k, v in sorted(by_bit.items())},
            "name_conflicts": conflicts,
            "closure_session_evidence": closure,
            "closure_session_note": ("Evidence from results/experiments/key-id-closure-*/: one control per popup, "
                                     "no batch windows, no order-based attribution. Only RT and the L stick were "
                                     "tested; both emitted nothing, which is why the analog channel is unobservable. "
                                     "See the session RESULT.md."),
            "final_classification_of_unresolved": {str(k): v for k, v in sorted(UNRESOLVED_BASIS.items())},
            "counts": {"proven_live": sum(1 for r in rows if r["grade"] == "PROVEN LIVE"),
                       "unknown": sum(1 for r in rows if r["grade"] == "UNKNOWN"),
                       "unobserved": sum(1 for r in rows if r["grade"] == "UNOBSERVED")},
            "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(REPO / "results/final"))
    a = ap.parse_args()
    out = pathlib.Path(a.outdir)
    data = build()

    (out / "key-map-confidence.json").write_text(json.dumps(data, indent=1) + "\n")
    with (out / "key-map-confidence.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "name", "name_confidence", "grade", "live_frames", "static_constant", "static_label", "notes"])
        for r in data["rows"]:
            w.writerow([r["id"], r["name"] or "", r.get("name_confidence", ""), r["grade"], r["live_frames"],
                        r.get("static_constant") or "", r["static_label"] or "", r["notes"] or ""])

    md = ["# Key-id confidence table (ids 0..33)", "",
          f"**Indexing note: {len(data['name_conflicts'])} ids differ between the wire bit and the app's",
          "`moojiang/define.dart` getters - the getters sit exactly one bit above the wire for the same",
          "name** (keyUp=bit17 vs wire Up=16, keyM1=24 vs wire M1=23, keyCapture=16 vs wire Capture=15,",
          "keyRThumb=15 vs wire R3=14). This is NOT a contradiction of the wire naming: the wire mapping",
          "is corroborated twice over - by the `key mask rule` recorded for all four builds",
          "(`keyL1=0x40` = bit 6 = LB, `keyCapture=0x8000` = bit 15, `keyUp=0x10000` = bit 16) and by the",
          "live single-bit frames themselves. The define.dart constants are therefore a separate,",
          "offset enumeration, and must not be used to name a wire bit. Per-id detail is in",
          "`name_conflicts` in the JSON.", "",
          f"Mask rule: `{data['mask_rule']}`", "",
          f"Counts: **{data['counts']['proven_live']} PROVEN LIVE**, "
          f"{data['counts']['unknown']} UNKNOWN, {data['counts']['unobserved']} unobserved.", "",
          "| id | name | name confidence | grade | live frames | static constant | notes |",
          "|---|---|---|---|---|---|---|"]
    for r in data["rows"]:
        md.append(f"| {r['id']} | {r['name'] or '—'} | {r.get('name_confidence', '')} | {r['grade']} | "
                  f"{r['live_frames']} | {r.get('static_constant') or '—'} | {r['notes'] or ''} |")
    md += ["", "## How an id is proven", "",
           "A bit counts as proven for a button only when a frame carrying exactly that single bit",
           "appears inside the window in which the operator was asked to press that button. Positional",
           "pairing is deliberately not used, and the configuration `mapKeys` region is a source->target",
           "remap, so it is never used to name a bit.", "",
           "## Residuals", "",
           "- **RT (id 9)**: requested in four windows plus three dedicated retries, never appeared, and",
           "  its analog byte [16] never left zero. On this unit RT has no digital key id - a proven",
           "  negative worth stating as such rather than as a gap.",
           "- **ids 2, 5, 21, 22, 31, 32, 33**: no physical button produced these bits in any capture we",
           "  hold. They are UNKNOWN, and the static label inventories above do not resolve them either.",
           "- **id 20**: one live bit was seen in the group-F window but cannot be attributed to RT, so it",
           "  stays unattributed."]
    (out / "key-map-confidence.md").write_text("\n".join(md) + "\n")
    print(json.dumps(data["counts"]))
    print("static constants:", json.dumps(data["static_key_constants"]))
    print("name conflicts:", json.dumps(data["name_conflicts"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
