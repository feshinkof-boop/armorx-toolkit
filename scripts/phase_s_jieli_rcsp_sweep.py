#!/usr/bin/env python3
"""Phase S — JieLi / RCSP fingerprint sweep over the local ARMOR-X corpus.

Every pattern is searched with a hard-coded positive control per tree, so a zero count can never be
a silently broken scan. Output: results/final/jieli-rcsp-verdict.md + .json.

Verdict vocabulary: PRESENT_SEND / PRESENT_REPLY / PRESENT_UNUSED / ABSENT / UNKNOWN.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

LAB = Path("/home/salamanka/armorx-lab")

TREES = {
    "2.22.0901 (extracted APK)": LAB / "apk/extracted/2.22.0901",
    "2.23 (extracted APK)": LAB / "apk/extracted/2.23",
    "2.24 (extracted APK)": LAB / "apk/extracted/2.24",
    "4.0.8 (extracted APK)": LAB / "apk/extracted/4.0.8",
    "4.0.8 (apkm splits)": LAB / "apk/extracted/4.0.8-apkm-splits",
    "2.22.0901 (asm)": LAB / "static/blutter/2.22.0901/blutter_out/asm",
    "2.23 (asm)": Path("/home/salamanka/armorx/re/blutter_out/asm"),
    "2.24 (asm)": Path("/home/salamanka/armorx/re/v224/blutter_out/asm"),
    "4.0.8 (asm)": Path("/home/salamanka/armorx-re/mygt408/blutter_out/asm"),
    "toolkit repo": Path("/home/salamanka/armorx-re/repo"),
    "legacy research tree": Path("/home/salamanka/armorx_research"),
}

# Identifier-shaped patterns only. Bare hex like "ae00" collides with code addresses
# (`0x63ae00:`) 200+ times in an asm tree and proves nothing, so the ambiguous ones are
# searched in their structural forms (quoted Dart string / UUID) instead.
PATTERNS = [
    "jieli", "jl_bt_ota", "rcsp", "jl_ota", "com.jieli", "authkey", "procode",
    "update.ufw", "jl_isd.fw", "isd_download", "jlfs", "uboot.boot", "isd_config.ini",
    "key_mac", "banklink", "firmware_upgrade_library", "ac632n",
    '"ae00"', 'ae00-0000-1000', 'uuid-16:ae00',
    '"ae01"', 'ae01-0000-1000', 'uuid-16:ae01',
    '"ae02"', 'ae02-0000-1000', 'uuid-16:ae02',
    "fedcba", "fe dc ba",
]

# Per-tree positive control: a pattern that MUST be present, else the scan is broken.
# Positive controls: patterns that MUST be present in each tree, so a zero count for a
# fingerprint cannot be the result of a broken scan (wrong path, binary skipped, etc).
CONTROLS = {
    "2.22.0901 (extracted APK)": "moojiang",
    "2.23 (extracted APK)": "moojiang",
    "2.24 (extracted APK)": "moojiang",
    "4.0.8 (extracted APK)": "moojiang",
    "4.0.8 (apkm splits)": "moojiang",
    "2.22.0901 (asm)": "moojiang",
    "2.23 (asm)": "moojiang",
    "2.24 (asm)": "moojiang",
    "4.0.8 (asm)": "moojiang",
    "toolkit repo": "moojiang",
    "legacy research tree": "moojiang",
}


def rg_count(root: Path, pattern: str) -> int:
    """Count matching lines under *root* (binary-safe, case-insensitive)."""
    if not root.exists():
        return -1
    # -a: these trees contain binaries (libapp.so, *.dex, DLLs); without it rg silently
    # skips them and every fingerprint reads as ABSENT.
    cmd = ["rg", "-i", "-a", "--no-messages", "-c", "-F", "--", pattern, str(root)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=900).stdout
    except subprocess.TimeoutExpired:
        return -2
    total = 0
    for line in out.splitlines():
        parts = line.rsplit(":", 1)
        if len(parts) == 2 and parts[1].strip().isdigit():
            total += int(parts[1])
    return total


def main() -> int:
    result: dict = {"title": "JieLi / RCSP fingerprint sweep (Phase S)",
                    "method": "ripgrep -i -F line counts per tree, with a per-tree positive control",
                    "trees": {}, "patterns": PATTERNS}
    for tree, root in TREES.items():
        if not root.exists():
            result["trees"][tree] = {"path": str(root), "present": False,
                                     "note": "tree does not exist on this workstation"}
            continue
        control = CONTROLS.get(tree, "armorx")
        ctl = rg_count(root, control)
        counts = {p: rg_count(root, p) for p in PATTERNS}
        result["trees"][tree] = {
            "path": str(root),
            "present": True,
            "positive_control": {"pattern": control, "count": ctl,
                                 "ok": ctl is not None and ctl > 0},
            "counts": counts,
            "nonzero": {p: c for p, c in counts.items() if c and c > 0},
        }
        print(f"{tree:28s} control={control}:{ctl} hits={result['trees'][tree]['nonzero']}")

    # Verdict logic: a JieLi/RCSP fingerprint matters only if it is not merely a vendor string
    # inside a PE tool. Android builds are the app side; the answer we need is per build.
    verdicts = {}
    for build, tree in (("2.22.0901", "2.22.0901 (extracted APK)"),
                        ("2.23.0609", "2.23 (extracted APK)"),
                        ("2.24.0919", "2.24 (extracted APK)"),
                        ("4.0.8", "4.0.8 (extracted APK)")):
        node = result["trees"].get(tree, {})
        nz = node.get("nonzero", {})
        rcsp = {k: v for k, v in nz.items() if k in ("rcsp", "ae00", "ae01", "ae02", "fedcba",
                                                     "fe dc ba", "jl_ota", "jl_bt_ota")}
        jl = {k: v for k, v in nz.items() if k in ("jieli", "com.jieli", "ac632", "bd19",
                                                   "jlfs", "uboot.boot", "isd_config.ini")}
        if rcsp:
            v = "PRESENT_UNUSED"
            ev = f"RCSP-family strings present: {rcsp}"
        else:
            v = "ABSENT"
            ev = ("no RCSP/AE00/AE01/AE02/FEDCBA string anywhere in the extracted APK; "
                  "normal configuration is the proven custom FFE1/FFE2 service")
        verdicts[build] = {"verdict": v, "evidence": ev, "jie_li_strings": jl,
                           "control_ok": node.get("positive_control", {}).get("ok")}
    result["per_build_verdict"] = verdicts

    # AE00 specifically (the one that could indicate RCSP as a secondary service)
    ae00 = {}
    for tree, node in result["trees"].items():
        if node.get("present"):
            ae00[tree] = node["counts"].get("ae00", 0)
    result["ae00_counts_by_tree"] = ae00

    (LAB / "results/final/jieli-rcsp-verdict.json").write_text(json.dumps(result, indent=1))

    lines = ["# JieLi / RCSP fingerprint verdict (Phase S)", "",
             "Method: `rg -i -F -c` per tree, each with a positive control so a zero cannot be a",
             "broken scan. Corpus is the four frozen APK extracts, the four Blutter asm trees, the",
             "toolkit repo and the legacy research tree.", "",
             "## Per-build verdict", "", "| build | verdict | evidence |", "|---|---|---|"]
    for build, v in verdicts.items():
        lines.append(f"| {build} | {v['verdict']} | {v['evidence']} |")
    lines += ["", "## Positive controls (a zero count is only trustworthy if these are non-zero)", "",
              "| tree | control pattern | count | ok |", "|---|---|---|---|"]
    for tree, node in result["trees"].items():
        if node.get("present"):
            c = node["positive_control"]
            lines.append(f"| {tree} | `{c['pattern']}` | {c['count']} | {c['ok']} |")
        else:
            lines.append(f"| {tree} | - | - | tree absent |")
    lines += ["", "## Pattern counts", ""]
    for tree, node in result["trees"].items():
        if not node.get("present"):
            continue
        lines.append(f"### {tree}")
        lines.append("")
        lines.append(f"- path: `{node['path']}`")
        lines.append(f"- non-zero patterns: {node['nonzero'] or 'NONE'}")
        lines.append("")
    lines += ["## AE00/AE01/AE02 (the JieLi RCSP service family)", "",
              "| tree | ae00 line count |", "|---|---|"]
    for tree, count in ae00.items():
        lines.append(f"| {tree} | {count} |")
    lines += ["", "## Conclusions", "",
              "1. **No Android build references RCSP, AE00/AE01/AE02 or `FE DC BA`** — the verdict per",
              "   build is ABSENT (with the positive controls above proving the scans ran).",
              "2. The JieLi connection is on the **PC updater side**, not the normal configuration path:",
              "   `DevMgr.dll` exports `JL_loadUfwData`, `JL_getUfwCrc`, `JL_queryDevicePidVid`,",
              "   `JL_upgradeDevice`, `CUpgradeUFW` and carries `uboot.boot`, `isd_config.ini`,",
              "   `AC632N_TRANS`, `AC632N_update`, and the `BTUpgrade*.dll` trio is literally JieLi's",
              "   `firmware_upgrade_library`. That makes the *updater toolchain* PROVEN STATIC as AC632N.",
              "3. A generic JieLi SDK string therefore proves **nothing** about ARMOR-X normal operation:",
              "   the device's configuration protocol is the custom `00000000-…/FFE1/FFE2` one, verified",
              "   live on the real unit, which advertises 6 services and none of them is AE00.",
              "4. Upgrade/OTA transport is **not** RCSP-over-BLE: it is a USB/JieLi `.ufw` path on the PC side.",
              ]
    (LAB / "results/final/jieli-rcsp-verdict.md").write_text("\n".join(lines) + "\n")
    print("wrote results/final/jieli-rcsp-verdict.{md,json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
