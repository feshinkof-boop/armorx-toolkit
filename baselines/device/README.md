# Device baselines (baselines/device/)

One directory per physical controller. Nothing here is written by hand: every file is produced by
`automation/scripts/real_device_harness.py`.

```
baselines/device/<serial>/
  baseline_<serial>_144.bin     raw config image as read with A5 04 D6 7F
  baseline_<serial>_144.json    manifest: sha256, crc_ok, declared_len, mapkeys, captured_at,
                                request/reply hex, and (only after a proven round trip)
                                restore_verified: true + roundtrip_sha256
  identity.json                 written by `identify`: 0B version reply, EF uuid, MTU
  session-*.jsonl               state-machine log for every session (see logs/device/)
```

Rules
* A baseline is only usable as a restore source once `crc_ok` is true AND the manifest carries
  `restore_verified: true`, which requires an actual D7 write followed by a byte-identical D6
  read-back (`real_device_harness.py verify-restore`).
* Never edit a captured `.bin`. If the device changes, capture a new baseline with a new timestamp.
* Keep the first baseline of each session: it is the only trustworthy record of "as found" state.

Currently captured baselines: **none** — no ARMOR-X has been reachable from this host yet.
