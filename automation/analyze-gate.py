#!/usr/bin/env python3
"""Summarise an armorx live validate-write-gate report (offline, read-only)."""
import json
import sys

report = json.loads(open(sys.argv[1]).read())
d7 = report.get("d7", {})
persist = report.get("persist", {})
readback = report.get("readback", {})
attempts = readback.get("attempts", [])
print("status:", report.get("status"), "| stage:", report.get("stage"))
print("baseline sha:", report.get("baseline_sha256"))
print("first read :", report.get("first_read", {}).get("actual_length"),
      report.get("first_read", {}).get("stored_crc_hex"),
      report.get("first_read", {}).get("crc_matches"))
print("second read:", report.get("second_read", {}).get("sha256"),
      "| repeated identical:", report.get("repeated_reads_identical"))
print("authorized:", report.get("operator_authorized"))
print("d7 fragments sent:", d7.get("sent"))
print("d7 ack:", d7.get("ack_observed"), d7.get("acknowledgement"))
print("d7 notifications:", len(d7.get("notifications", [])))
print("persist sent:", persist.get("sent"), persist.get("request_hex"))
print("0E notifications:", persist.get("notification_count"),
      persist.get("acknowledgement"))
print("readback attempts:", len(attempts))
for a in attempts:
    print("  attempt", a["attempt"], "len", a["actual_length"], "crc",
          a["crc_matches"], "sha", a["sha256"][:16], "match",
          a["byte_for_byte_match"], "diffs", len(a["differences"]))
print("final equal:", report.get("byte_for_byte_match"),
      "| target diff:", report.get("all_offsets_differing"))
