# official-vs-harness-session — official-vs-harness-session-20260927-190741

**Status: PARTIAL** — harness session complete; official-app session not captured
(`ANDROID_HCI_CAPTURE_UNAVAILABLE`).

## Layout

```
device-discovery.txt                scan output for the session
differential-raw.json               raw output of the session-diff decoder
C0/                                 the control session's own result.json / identity.json / services.json
app-identity.json                  installed app could NOT be inspected; repo 4.0.8 APK sha256 recorded
android-prestate.txt               exact ADB/network diagnostics and their output
android-bond-security.json         UNKNOWN (unreadable), explicitly not guessed
official-session/
  raw/CAPTURE_UNAVAILABLE.txt      why there is no btsnoop
  official-timeline.csv            header only (no capture)
  official-hci-summary.json        {"captured": false, ...}
  official-gatt-sequence.json      {"captured": false, ...}
  official-button-test.json        not performed (nothing to measure against)
harness-session/
  raw/btmon.btsnoop                binary HCI capture
  raw/btmon.txt                    decoded trace (btmon -r)
  raw/btmon-live.txt               live line-buffered trace (the file that actually holds the traffic)
  harness-timeline.csv             normalized events
  harness-att-summary.json         decoder-level rollup (from session-diff.py)
  probe-readback.bin, id15-probe-result.json   the D6 readback
  harness-att.jsonl                normalized ATT JSONL
  harness-hci-summary.json         link/ATT parameters
  harness-gatt-sequence.json       control-plane sequence with timestamps
official-vs-harness-diff.md/.json  staged comparison
first-divergence.json              UNKNOWN, with the reason and the non-divergences listed
final-d6.bin / final-d6.json       configuration integrity read
verdict.md                         the full verdict
```

## Harness session (the part that succeeded)

Role Central, peer address type Public, interval 7.50 ms, latency 0, supervision timeout 2000 ms,
ATT MTU negotiated 64, unbonded/unencrypted, one `LE Connection Update` at t≈24.9 s.
Control plane: CCCD subscribe → `0B` `a5040bb4`@25.012 → D2 OFF@27.017 → **D2 ENABLE
`a505d2017d`@28.521 as ATT Write Command (0x52)** → 10 s idle → D2 OFF@38.531 → disconnect@42.147.
Valid `A5 12 02` frames: **0**.

## Safety

Runtime-only: discovery, identity reads, the proven `0B` query, D2 enable/disable, notification and
CCCD operations, passive capture, D6 read. No D7/D8, no configuration/DPI/lighting/macro write, no
RCSP/AE01/OTA/firmware/bootloader command, no flash access, no guessed command, and **no unknown
official-app traffic was replayed** (none was captured to replay).

## Completion attempts

- **20260927-192908** — official-app capture attempted, **blocked at the ADB transport**
  (`USB_DEVICE_NOT_PRESENT`: no USB device after an acknowledged operator setup request, and
  `adb connect ...:5555` refused). See `official-session/completion-20260927-192908/verdict.md`.
  The harness measurements above are unaffected and were not recaptured.
