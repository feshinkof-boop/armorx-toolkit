#!/usr/bin/env python3
import json, os
OUT = "/home/salamanka/armorx-lab/results/overnight/20260927-203902/branches/d4-reconciliation"

def cks(h):
    b = [int(h[i:i+2],16) for i in range(0,len(h),2)]
    return sum(b[:-1]) & 0xFF

# ---------- d4-matrix.json ----------
matrix = {
 "schema": "armorx-d4-evidence-matrix/v1",
 "generated": "2026-09-27",
 "generated_by": "Hermes subagent (d4-reconciliation branch)",
 "frame_convention": {
   "form": "A5 <LEN> <OPCODE> <payload...> <CHECKSUM>",
   "LEN": "TOTAL frame length in bytes (verified: every A5/A4 frame in the corpus has LEN == len(frame)). NB the task brief's phrasing 'LEN counts the bytes after it' does NOT match the corpus.",
   "CHECKSUM": "sum(all bytes except the final checksum byte) & 0xFF"
 },
 "rows": [
  {"#":1,"date":"(static)","app_build":"2.22.0901","kind":"static","request":"A5 04 D4 7D","response":"A5 06 D4 <g> <o> <cks> (layout only; no reply exists statically)","req_len":4,"resp_len":"6 (min, INFERRED)","req_cks_recomputed":"0x7D","resp_cks_recomputed":"n/a (layout)","source":"static/blutter/2.22.0901/blutter_out; results/reconciliation/d4-reconstruction.{md,json}","static_or_live":"static","confidence":"PROVEN STATIC (request + index-3/index-4 parser reads)"},
  {"#":2,"date":"(static)","app_build":"2.23.0609","kind":"static","request":"A5 04 D4 7D","response":"A5 06 D4 <g> <o> <cks> (layout only)","req_len":4,"resp_len":"6 (min, INFERRED)","req_cks_recomputed":"0x7D","resp_cks_recomputed":"n/a","source":"armorx-re/repo blutter 2.23 (getInputModel @0x8afa98; rx @0x8af690/0x8097cc)","static_or_live":"static","confidence":"PROVEN STATIC"},
  {"#":3,"date":"(static)","app_build":"2.24.0919","kind":"static","request":"A5 04 D4 7D","response":"A5 06 D4 <g> <o> <cks> (layout only)","req_len":4,"resp_len":"6 (min, INFERRED)","req_cks_recomputed":"0x7D","resp_cks_recomputed":"n/a","source":"armorx-re/repo v224 blutter (getOnBoardConfig @0x91b988; prints 板载mode)","static_or_live":"static","confidence":"PROVEN STATIC"},
  {"#":4,"date":"(static)","app_build":"4.0.8","kind":"static","request":"A5 04 D4 7D","response":"A5 06 D4 <g> <o> <cks> (layout only)","req_len":4,"resp_len":"6 (min, INFERRED)","req_cks_recomputed":"0x7D","resp_cks_recomputed":"n/a","source":"armorx-re/mygt408/blutter_out (getInputModel @0xa84258; prints 板载mode)","static_or_live":"static","confidence":"PROVEN STATIC"},
  {"#":5,"date":"2026-09-27","app_build":"2.22.0901 (AVD API33)","kind":"virtual","request":"A5 04 D4 7D","response":"A5 06 D4 00 00 7F","req_len":4,"resp_len":6,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"0x7F","source":"results/static/2.22.0901/d4-dynamic-verification.md; ble/virtual-armorx/logs/2220901-d4-live.{hex,jsonl}","static_or_live":"live (against VIRTUAL peripheral)","confidence":"PROVEN LIVE (exchange) but the reply is a CONSTRUCTED virtual default (chosen state 0x00/0x00)"},
  {"#":6,"date":"2026-09-27","app_build":"2.22.0901 (AVD)","kind":"virtual","request":"A5 04 D4 7D","response":"A5 06 D4 00 00 80 (deliberately wrong cks)","req_len":4,"resp_len":6,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"0x7F (recorded 0x80)","source":"ble/virtual-armorx/logs/2220901-d4-badcksum.jsonl","static_or_live":"live (virtual probe)","confidence":"PROVEN LIVE (probe: app does NOT validate inbound D4 checksum)"},
  {"#":7,"date":"2026-09-27","app_build":"2.22.0901 (AVD)","kind":"virtual","request":"A5 04 D4 7D","response":"A5 04 D4 00 (truncated, no cks)","req_len":4,"resp_len":4,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"n/a","source":"ble/virtual-armorx/logs/2220901-d4-truncated.jsonl","static_or_live":"live (virtual probe)","confidence":"PROVEN LIVE (probe: index-4 read has no length guard -> RangeError)"},
  {"#":8,"date":"2026-09-27","app_build":"4.0.8 (official app)","kind":"real","request":"A5 04 D4 7D","response":"A5 07 D4 11 01 00 92","req_len":4,"resp_len":7,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"0x92","source":"results/experiments/official-vs-harness-session-20260927-190741/official-session/.../official-att.jsonl (frame 6259); official-timeline.csv; results/overnight/20260927-203902/official-timeline-canonical.json; logcat-official.txt:1288,1295","static_or_live":"live (real ARMOR-X Pro, HCI snoop)","confidence":"PROVEN LIVE - decisive: logcat prints 板载mode = 1 == data[4]=0x01"},
  {"#":9,"date":"2026-09-27","app_build":"Linux harness (no app version)","kind":"real","request":"A5 04 D4 7D","response":"A5 07 D4 11 01 00 92","req_len":4,"resp_len":7,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"0x92","source":"results/experiments/physical-20260927-{162448,165347,174445-buttons}/raw-tx-rx.log; tests/vectors/real-device-vectors.json","static_or_live":"live (real ARMOR-X Pro x3 sessions)","confidence":"PROVEN LIVE"},
  {"#":10,"date":"2026-09-23 (imported)","app_build":"(brief / older docs)","kind":"assumption","request":"A5 04 D4 7D","response":"A5 06 D4 00 00 7F (claimed REAL)","req_len":4,"resp_len":6,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"0x7F","source":"armorx-re/repo/docs/real-device/live-findings.md:25; results/final/remaining-real-hardware-unknowns.md:36","static_or_live":"neither (assumed)","confidence":"CONTRADICTED as a real-hardware reply (5 live captures show A5 07 D4 11 01 00 92)"},
  {"#":11,"date":"2026-09-27","app_build":"2.22.0901 (AVD)","kind":"virtual (pre-handler)","request":"A5 04 D4 7D","response":"(none - command_unknown, reply_bytes_sent:0)","req_len":4,"resp_len":0,"req_cks_recomputed":"0x7D","resp_cks_recomputed":"n/a","source":"results/static/2.22.0901/virtual-armorx-compat.md §B","static_or_live":"live (virtual, D4 handler not yet implemented)","confidence":"PROVEN LIVE (older virtual vintage: D4 unanswered)"},
  {"#":12,"date":"(static vectors)","app_build":"all","kind":"virtual-constructed","request":"A5 04 D4 7D","response":"A5 06 D4 06 03 88 / A5 06 D4 06 00 85 / A5 06 D4 01 01 81","req_len":4,"resp_len":"6 each","req_cks_recomputed":"0x7D","resp_cks_recomputed":"0x88 / 0x85 / 0x81","source":"results/reconciliation/d4-reconstruction.json test_vectors; apk/manifests/*.json","static_or_live":"neither (constructed, never on wire)","confidence":"PROVEN STATIC (arithmetic) - never transmitted"}
 ],
 "distinct_request_forms": 1,
 "distinct_reply_forms": 6,
 "reply_forms": ["A5 06 D4 00 00 7F (virtual default)","A5 06 D4 00 00 80 (bad-cks probe)","A5 04 D4 00 (truncated probe)","A5 07 D4 11 01 00 92 (REAL)","A5 06 D4 06 03 88 | 06 00 85 | 01 01 81 (test vectors, 3)","(none) older virtual command_unknown"],
 "families": 2,
 "family_note": "Two families: (F1) 6-byte CONSTRUCTED A5 06 D4 ... (virtual default + static vectors, chosen state 00/00) and (F2) 7-byte REAL A5 07 D4 11 01 00 92 (real hardware, official + harness).",
 "explanations": {
   "software_generation_changing_the_query": {"verdict":"CONTRADICTED","why":"request A5 04 D4 7D is byte-identical in 2.22.0901, 2.23.0609, 2.24.0919, 4.0.8 (static) and in 2.22 virtual + 4.0.8 official + harness live; the sender is only renamed/relocated (getOnBoardConfig<->getInputModel, widget->BluetoothModel)."},
   "device_mode_state": {"verdict":"SUPPORTED","why":"payload VALUES differ because device state differs: virtual test used chosen 0x00/0x00; the real unit returned 0x11/0x01 (logcat 板载mode = 1 == data[4]=0x01). Layout unchanged."},
   "request_variant": {"verdict":"CONTRADICTED","why":"only one request form exists anywhere in the corpus."},
   "parser_error": {"verdict":"PARTIAL (already corrected)","why":"an earlier static pass mis-read a tagged Smi index (mov x16,#8 -> index 4, not 8) and inferred a reply field at the wrong offset; corrected and documented in d4-reconstruction/smi-audit. It is NOT the cause of the 06-vs-07 conflict, which is provenance (virtual vs real), not parsing."},
   "old_assumption": {"verdict":"SUPPORTED - PRIMARY","why":"A5 06 D4 00 00 7F is the virtual peripheral's default reply / the 'brief' value; two older docs (live-findings.md, remaining-real-hardware-unknowns.md) mis-recorded it as the REAL reply. That misrecording is the conflict."},
   "virtual_peripheral_used_earlier": {"verdict":"SUPPORTED - PRIMARY","why":"A5 06 D4 00 00 7F originates as the virtual ARMOR-X peripheral default (armorx_protocol.py / virtual_armorx.py), fed with chosen --d4-gamepad-mode/--d4-onboard-mode."},
   "genuine_protocol_variant": {"verdict":"PARTIAL -> NO across versions","why":"the request and the reply FIELD LAYOUT (index3/index4) are invariant; only the real frame has one extra payload byte (index5=0x00) vs the constructed 6-byte minimum. The static 'total_len 6' was explicitly INFERRED/UNKNOWN(>=6); the real length is 7. This is the real length being unknown, not a per-version variant."}
 },
 "grading": {
   "D4_request":"PROVEN STATIC + PROVEN LIVE",
   "D4_reply_field_layout_index3_index4":"PROVEN STATIC + PROVEN LIVE",
   "real_D4_reply_bytes":"PROVEN LIVE (A5 07 D4 11 01 00 92)",
   "claim_real_reply_is_A5_06_D4_00_00_7F":"CONTRADICTED",
   "static_total_len_6":"INFERRED -> superseded; real ARMOR-X Pro length = 7 (the 6 remains a valid parser floor)",
   "value_domain_of_index3_index4":"UNKNOWN",
   "across_generation_semantic_change":"CONTRADICTED (no change)"
 },
 "checksum_summary": {"frames_verified":23,"corpus_frames_swept":227,"mismatches":["D4-REP-BADCKSUM (deliberate probe: recorded 0x80, recomputed 0x7F)","D4-REP-TRUNCATED (deliberate probe: no checksum byte)"]}
}
json.dump(matrix, open(os.path.join(OUT,"d4-matrix.json"),"w"), indent=2, ensure_ascii=False)
print("wrote d4-matrix.json")
