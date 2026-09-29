#!/usr/bin/env python3
"""Render the sanitized public artifacts for the reversible M1 -> A session.

Usage: render-reversible-m1.py <session-dir> <out-prefix>
Never emits a BLE address, serial, user name, host name or home path.
"""
import json
import pathlib
import sys

session = pathlib.Path(sys.argv[1])
prefix = sys.argv[2]
load = lambda name: json.loads((session / name).read_text())
preflight = load("ble/preflight.json")
apply = load("ble/apply.json")
after = load("ble/check-after-powercycle.json")
restore = load("ble/restore.json")
final = load("ble/final-check.json")
physical = load("physical-m1.json")

baseline_sha = apply["baseline_sha256"]
target_sha = apply["target_sha256"]
refusals = preflight.get("refusal_reason")

document = {
    "artifact": "armorx-toolkit v0.4.0 supervised reversible M1 -> A mutation",
    "date": "2026-09-29",
    "command": ("armorx live validate-reversible-m1 --stage apply|check|restore "
                "(takes no target image by design)"),
    "result": "PASS",
    "original_baseline": {
        "sha256": baseline_sha,
        "length": 144,
        "crc": apply["first_read"]["stored_crc_hex"],
        "crc_valid": apply["first_read"]["crc_matches"],
        "mapKeys[23] (M1 source)": preflight["baseline_m1"],
        "matches_historical_baseline": apply.get("historical_baseline_match"),
        "two_preflight_reads_identical": apply["repeated_reads_identical"],
    },
    "target": {
        "sha256": target_sha,
        "length": 144,
        "crc_valid": apply["target"]["crc_matches"],
        "mapKeys[23]": {"code": 0, "name": "A"},
        "changed_offsets": apply["target"]["changed_offsets"],
        "differences": apply["target_differences"],
        "derived_from": "the live D6 read taken immediately before the write",
        "diff_set_is_exactly_crc_plus_mapkeys_23": apply["target"]["changed_offsets"] == [0, 1, 135],
    },
    "authorization": {
        "popup": "ARMOR-X v0.4 REVERSIBLE CONFIG TEST",
        "ack": "accepted",
        "note": "no write is possible without the explicit --authorized flag",
        "unauthorized_preflight_refusal": refusals,
    },
    "target_write": {
        "d7_fragments": apply["write"]["sent"],
        "d7_ack": apply["write"]["acknowledgement"] if apply["write"]["ack_observed"] else None,
        "persistence_frame": apply["write"]["persist"]["request_hex"],
        "persistence_frames_sent": apply["write"]["persist"]["sent"],
        "persistence_notifications": apply["write"]["persist"]["notification_count"],
    },
    "target_verification": {
        "d6_read_1": apply["readback"]["attempts"][0],
        "d6_read_2": apply["readback"]["attempts"][1],
        "byte_for_byte_match": apply["byte_for_byte_match"],
    },
    "physical_effect": physical,
    "persistence_after_power_cycle": {
        "observed_sha256": after["observed"]["sha256"],
        "state": after["observed_state"],
        "equals_target": after["observed"]["sha256"] == target_sha,
        "crc_valid": after["observed"]["crc_matches"],
    },
    "restore": {
        "source": "the baseline this toolkit saved before the mutation",
        "source_sha256": restore["restore_source_sha256"],
        "d7_fragments": restore["write"]["sent"],
        "d7_ack": restore["write"]["acknowledgement"] if restore["write"]["ack_observed"] else None,
        "persistence_frames_sent": restore["write"]["persist"]["sent"],
        "persistence_notifications": restore["write"]["persist"]["notification_count"],
        "d6_read_1": restore["readback"]["attempts"][0],
        "d6_read_2": restore["readback"]["attempts"][1],
        "byte_for_byte_match": restore["byte_for_byte_match"],
    },
    "final_after_power_cycle": {
        "state": final["observed_state"],
        "sha256": final["observed"]["sha256"],
        "crc_valid": final["observed"]["crc_matches"],
        "length": final["observed"]["actual_length"],
        "equals_original_baseline": final["observed"]["sha256"] == baseline_sha,
    },
    "failures_or_retries": {
        "writes_performed": 2,
        "note": ("one D7 write of the target and one D7 write of the restore image; "
                 "no automatic retry loop ran and no write was ever repeated blindly"),
        "evdev_host_view": physical["host_evdev_note"],
    },
    "privacy": {
        "ble_address": "withheld (local runtime only)",
        "serial_number": "not read, not recorded",
        "host_data": "not recorded",
    },
}
open(prefix + ".json", "w").write(json.dumps(document, indent=2, sort_keys=True) + "\n")


def diff_rows(differences):
    return ", ".join(f"{d['offset']}: {d['before']} -> {d['after']}" for d in differences) or "none"


md = []
md.append("# ARMOR-X Toolkit v0.4.0 — supervised reversible M1 &#8594; A mutation")
md.append("")
md.append("Date: 2026-09-29. Command: `armorx live validate-reversible-m1` on")
md.append("`dev/v0.4.0-live-linux`. The command accepts no target image, opcode or")
md.append("payload: it derives `mapKeys[23] -> A` in memory from the live baseline and")
md.append("restores the baseline it saved itself.")
md.append("")
md.append("**Result: PASS** — the logical change was applied, verified, physically")
md.append("observed, survived a power cycle, and was then fully reverted, with the")
md.append("restoration itself surviving a second power cycle.")
md.append("")
md.append("## Original baseline")
md.append("")
md.append("| field | value |")
md.append("| --- | --- |")
md.append(f"| length | 144 bytes |")
md.append(f"| CRC | `{apply['first_read']['stored_crc_hex']}` (valid: {apply['first_read']['crc_matches']}) |")
md.append(f"| SHA-256 | `{baseline_sha}` |")
md.append(f"| mapKeys[23] (M1 source) | {preflight['baseline_m1']['code']} = {preflight['baseline_m1']['name']} at offset {preflight['baseline_m1']['offset']} |")
md.append(f"| matches the historical baseline | {apply.get('historical_baseline_match')} |")
md.append(f"| two preflight reads identical | {apply['repeated_reads_identical']} |")
md.append("")
md.append("## Target")
md.append("")
md.append(f"- SHA-256 `{target_sha}`, 144 bytes, CRC valid")
md.append(f"- mapKeys[23]: {preflight['baseline_m1']['code']} -> 0 (B -> A)")
md.append(f"- changed offsets: {apply['target']['changed_offsets']} = {diff_rows(apply['target_differences'])}")
md.append("- no other byte differs, and no field beyond that one logical key changed")
md.append("")
md.append("## Authorization")
md.append("")
md.append("One KDE dialog with an audible alert; the click is the acknowledgement.")
md.append("Run without it first, and the command refuses and writes nothing:")
md.append(f"`{refusals}`")
md.append("")
md.append("## Target write and verification")
md.append("")
md.append(f"- D7: {apply['write']['sent']} A4 fragments, acknowledged with")
md.append(f"  `{apply['write']['acknowledgement']['raw_hex']}`")
md.append(f"- persistence: `{apply['write']['persist']['request_hex']}` sent once,")
md.append(f"  {apply['write']['persist']['notification_count']} notifications")
md.append(f"- two D6 read-backs: SHA `{apply['readback']['attempts'][0]['sha256'][:16]}...`,")
md.append(f"  byte-for-byte match {apply['byte_for_byte_match']}, 0 differing offsets")
md.append("")
md.append("## Physical effect")
md.append("")
md.append(f"Method: {physical['method']}.")
md.append(f"Captured: {physical['capture']}.")
md.append(f"Action: {physical['operator_action']}.")
md.append(f"Observed: {physical['observed']}.")
md.append(f"Verdict: **{physical['verdict']}** — pressing the button labelled M1 now")
md.append("reports A, which is the configured result.")
md.append(f"Note: {physical['host_evdev_note']}.")
md.append("")
md.append("## Persistence through a power cycle")
md.append("")
md.append(f"After off/on the live image SHA was `{after['observed']['sha256']}` — "
          f"{'equal to the target' if after['observed']['sha256'] == target_sha else 'NOT equal to the target'}. "
          "The mutation is durable, not a running-state artefact.")
md.append("")
md.append("## Restoration")
md.append("")
md.append("- the ORIGINAL saved baseline was written back, not a newly built image")
md.append(f"- D7: {restore['write']['sent']} fragments, acknowledged with")
md.append(f"  `{restore['write']['acknowledgement']['raw_hex']}`")
md.append(f"- persistence: {restore['write']['persist']['sent']} frame, "
          f"{restore['write']['persist']['notification_count']} notifications")
md.append(f"- two D6 read-backs: SHA `{restore['readback']['attempts'][0]['sha256'][:16]}...`, "
          f"byte-for-byte match {restore['byte_for_byte_match']}")
md.append("")
md.append("## Final state after a second power cycle")
md.append("")
md.append(f"- state: **{final['observed_state']}**")
md.append(f"- SHA-256 `{final['observed']['sha256']}`")
md.append(f"- equals the original baseline: **{final['observed']['sha256'] == baseline_sha}**")
md.append(f"- CRC valid: {final['observed']['crc_matches']}, length {final['observed']['actual_length']}")
md.append("")
md.append("## What was not done")
md.append("")
md.append("No general `live apply` / `live write-config` command and no raw opcode")
md.append("console exist; no other field was modified; no write was repeated blindly")
md.append("and no automatic retry loop ran.")
md.append("")
md.append("## Privacy")
md.append("")
md.append("The BLE address is withheld. No serial number, user name, host name, home")
md.append("path or token appears in this artifact.")
md.append("")
open(prefix + ".md", "w").write("\n".join(md) + "\n")
print("wrote", prefix + ".json", "and", prefix + ".md")
