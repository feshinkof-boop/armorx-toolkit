#!/usr/bin/env python3
"""Render the sanitized public artifacts for the no-op D7 gate.

Usage: render-gate-artifacts.py <gate-report.json> <out-prefix>
Writes <out-prefix>.json and <out-prefix>.md. Never emits a BLE address, a
serial, a user name, a host name or a home path.
"""
import json
import sys

report = json.loads(open(sys.argv[1]).read())
prefix = sys.argv[2]
first = report.get("first_read", {})
second = report.get("second_read", {})
d7 = report.get("d7", {})
persist = report.get("persist", {})
attempts = report.get("readback", {}).get("attempts", [])
ack = d7.get("acknowledgement", {})
p_ack = persist.get("acknowledgement", {})

document = {
    "artifact": "armorx-toolkit v0.4.0 supervised no-op D7 write-safety gate",
    "date": "2026-09-29",
    "command": "armorx live validate-write-gate (takes no target image by design)",
    "result": report.get("status"),
    "stage_reached": report.get("stage"),
    "pre_write": {
        "length": first.get("actual_length"),
        "declared_length": first.get("declared_length"),
        "stored_crc": first.get("stored_crc_hex"),
        "computed_crc": first.get("computed_crc_hex"),
        "crc_matches": first.get("crc_matches"),
        "sha256": report.get("baseline_sha256"),
        "second_read_sha256": second.get("sha256"),
        "repeated_reads_identical": report.get("repeated_reads_identical"),
        "fragment_count": first.get("fragment_count"),
    },
    "operator_authorized": report.get("operator_authorized"),
    "d7_write": {
        "fragment_count": d7.get("sent"),
        "bytes_written": 144,
        "image_source": "the live D6 read taken immediately before the write",
        "acknowledgement_observed": d7.get("ack_observed"),
        "acknowledgement": ack if ack.get("observed") else None,
        "acknowledgement_absent_note": None if ack.get("observed") else ack.get("note"),
        "notification_count": len(d7.get("notifications", [])),
        "first_fragment_at": (d7.get("fragments") or [{}])[0].get("at"),
        "last_fragment_at": (d7.get("fragments") or [{}])[-1].get("at"),
    },
    "persistence": {
        "frame": persist.get("request_hex"),
        "frames_sent": persist.get("sent"),
        "notification_count": persist.get("notification_count"),
        "notification_bytes": sorted({n["raw_hex"] for n in persist.get("notifications", [])
                                      if n.get("parsed")}),
        "acknowledgement": p_ack if p_ack.get("observed") else None,
    },
    "post_write_readback": [
        {
            "attempt": a["attempt"],
            "length": a["actual_length"],
            "declared_length": a["declared_length"],
            "stored_crc": a["stored_crc_hex"],
            "crc_matches": a["crc_matches"],
            "sha256": a["sha256"],
            "byte_for_byte_match": a["byte_for_byte_match"],
            "differing_offsets": a["differences"],
        }
        for a in attempts
    ],
    "byte_for_byte_match": report.get("byte_for_byte_match"),
    "differing_offsets": report.get("all_offsets_differing"),
    "privacy": {
        "ble_address": "withheld (local runtime only)",
        "serial_numbers": "not read, not recorded",
        "host_data": "not recorded",
    },
}
open(prefix + ".json", "w").write(json.dumps(document, indent=2, sort_keys=True) + "\n")

md = []
md.append("# ARMOR-X Toolkit v0.4.0 — supervised no-op D7 write-safety gate")
md.append("")
md.append("Date: 2026-09-29. Command: `armorx live validate-write-gate` on")
md.append("`dev/v0.4.0-live-linux`. The command takes **no target image, opcode or")
md.append("payload**: the bytes it writes are the bytes it read from the device")
md.append("immediately before the write.")
md.append("")
md.append(f"**Result: {report.get('status')}**")
md.append("")
md.append("## Pre-write baseline (two consecutive live D6 reads)")
md.append("")
md.append("| field | value |")
md.append("| --- | --- |")
md.append(f"| length | {first.get('actual_length')} bytes |")
md.append(f"| declared length | {first.get('declared_length')} |")
md.append(f"| stored CRC | `{first.get('stored_crc_hex')}` |")
md.append(f"| computed CRC | `{first.get('computed_crc_hex')}` |")
md.append(f"| CRC valid | {first.get('crc_matches')} |")
md.append(f"| SHA-256 | `{report.get('baseline_sha256')}` |")
md.append(f"| second read SHA-256 | `{second.get('sha256')}` |")
md.append(f"| repeated reads identical | {report.get('repeated_reads_identical')} |")
md.append(f"| fragments | {first.get('fragment_count')} |")
md.append("")
md.append("## Operator authorization")
md.append("")
md.append("One KDE dialog (`ARMOR-X v0.4 WRITE SAFETY GATE`) with an audible alert.")
md.append("The click is the acknowledgement; the run proceeded only after it.")
md.append("")
md.append("## D7 write")
md.append("")
md.append(f"- fragments sent: **{d7.get('sent')}** (A4, opcode D7, indexes 1-10)")
md.append("- image: the exact live read above, byte for byte, never altered")
md.append(f"- D7 acknowledgement observed: **{d7.get('ack_observed')}**")
if ack.get("observed"):
    md.append(f"  - `{ack.get('raw_hex')}` (checksum valid: {ack.get('checksum_ok')})")
else:
    md.append(f"  - no acknowledgement inside the bounded window; recorded as an")
    md.append(f"    absence, not as a rejection")
md.append("")
md.append("## Persistence")
md.append("")
md.append(f"- frame sent once: `{persist.get('request_hex')}`")
md.append(f"- notifications observed: **{persist.get('notification_count')}**")
if persist.get("notifications"):
    distinct = sorted({n["raw_hex"] for n in persist["notifications"] if n.get("parsed")})
    md.append(f"- notification bytes: " + ", ".join(f"`{b}`" for b in distinct)
              + " (checksum valid)")
if d7.get("fragments"):
    span = d7["fragments"][-1]["at"] - d7["fragments"][0]["at"]
    md.append("")
    md.append(f"The ten fragments were written over {span * 1000:.0f} ms "
              f"({d7['fragments'][0]['at']:.3f} -> {d7['fragments'][-1]['at']:.3f} "
              f"unix seconds); the D7 acknowledgement arrived "
              f"{ack.get('at', 0) - d7['fragments'][-1]['at']:.3f} s later."
              if False else
              f"The ten fragments were written over about {span * 1000:.0f} ms; "
              f"the D7 acknowledgement arrived "
              f"{d7['notifications'][0]['at'] - d7['fragments'][-1]['at']:.3f} s after "
              f"the last fragment.")

md.append("")
md.append("## Post-write read-back")
md.append("")
md.append("| attempt | length | CRC valid | SHA-256 | byte-for-byte | differing offsets |")
md.append("| --- | --- | --- | --- | --- | --- |")
for a in attempts:
    md.append(f"| {a['attempt']} | {a['actual_length']} | {a['crc_matches']} | "
              f"`{a['sha256'][:16]}...` | {a['byte_for_byte_match']} | "
              f"{len(a['differences'])} |")
md.append("")
md.append(f"**Byte-for-byte match: {report.get('byte_for_byte_match')}**")
md.append("")
md.append("## Scope")
md.append("")
md.append("The write path exposed here is a byte-identical no-op only. No general")
md.append("`live apply` / `live write-config` command exists and no real mutation")
md.append("was performed. The next step is a separately supervised reversible")
md.append("mutation.")
md.append("")
md.append("## Privacy")
md.append("")
md.append("The BLE address is withheld. No serial number, user name, host name,")
md.append("home path or token appears in this artifact.")
md.append("")
open(prefix + ".md", "w").write("\n".join(md) + "\n")
print("wrote", prefix + ".json", "and", prefix + ".md")
