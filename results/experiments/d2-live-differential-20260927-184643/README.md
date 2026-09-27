# D2 live differential experiment — d2-live-differential-20260927-184643

Four cleanly separated cases, each on a fresh connection, 20 s passive observation, **no button
presses** (none was justified). Purpose: find out whether the real D2 silence is caused by ATT
write semantics, notification/CCCD state, harness orchestration, or something else.

## Result in one line

**All four cases produced zero valid button-test frames** →
`CASE 6 — none succeed` →
`D2-U-007 REMAINS UNKNOWN — PROTOCOL-LEVEL CANDIDATES TESTED HERE DID NOT EXPLAIN THE SILENCE.`

## Cases

| case | D2 enable write | ATT op (verified) | valid `A5 12 02` | notifications |
|---|---|---|---|---|
| C0 harness control | without response | Write Command `0x52` | **0** | 4 (1×0B reply + 3 echoes) |
| A write-with-response | **with response** | **Write Request `0x12` + Write Response `0x13`** | **0** | 4 (1 + 3) |
| B explicit CCCD renewal | without response, then unsubscribe/resubscribe | Write Command + CCCD `0000`/`0100` | **0** | 3 (1 + 2) |
| C same-connection re-enable | without response ×2 | Write Command `0x52` ×2 | **0** | 6 (1 + 5) |

Success criterion (never met): ≥5 valid frames in the window, incl. ≥1 with no button interaction
requested. Every rejected candidate is classified in `parser-results.json`: the 5-byte `A5 05 D2 …`
transactions are echoes, not button-test frames.

## Identity / control channel

`2D:37:35:6D:66:11` · `ARMOR-X Pro_11` · mfr `5a4a2d5854` (ZJ-XT) · `2A24=ZJ-XT`,
`2A26=2741`, `2A19=0x3d` (61 %) · control check `a5040bb4` → `a5050b30e5` OK.

## Files

- `experiment.json` — machine-readable result
- `parser-results.json` — RX classification incl. rejected candidates
- `timeline.csv`, `tx-rx.jsonl` — aggregate timelines (per-case copies inside each case dir)
- `C0-harness-control/`, `A-write-with-response/`, `B-cccd-renewal/`, `C-reenable/` — per-case
  `result.json`, `identity.json`, `services.json`, `timeline-*.csv`, `tx-rx-*.jsonl`
- `raw/btmon.btsnoop` (binary HCI capture), `raw/btmon.txt` (full text decode),
  `raw/att-control-plane.json`, `raw/att-windows.json`
- `tshark-att.txt` — ATT evidence **and** the honest record that tshark could not decode btatt
- `final-d6.bin`, `final-d6.json` — post-experiment configuration integrity (CONFIG_BASELINE_MATCH)
- `physical-a-validation.json` — not performed, with the reason
- `verdict.md`

## Safety / scope

Runtime-only: BLE discovery, identity reads, `0B` control check, D2 enable/disable, notification
and CCCD operations, passive capture, D6 read. **No** D7/D8, no configuration/DPI/lighting/macro
write, no RCSP/OTA, no firmware or bootloader command, no guessed command.
