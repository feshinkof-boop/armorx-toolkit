# Overnight shift status

Started: 2026-09-27T20:39:02.618184-04:00
Repo: /home/salamanka/armorx-lab @ research/physical-armorx-live-2026-09-27
Base commit at start: 9f57cc7 (clean worktree)

Hardware doors: all closed tonight (no popups, no sounds, no adapter, no ArmorX, no phone, no ADB).

## Done (this shift)

| part | deliverable | file |
|---|---|---|
| 0 | repo/worktree discovery + night rules | `manifest.json` |
| 1 | 5055 artifacts / 1.11 GB hashed, 200 duplicate groups | `evidence-inventory.json`, `evidence-inventory.md`, `evidence-duplicates.json` |
| 2 | canonical official timeline + independent verification (155 frames, 8 frags, 4 link updates) | `official-timeline-canonical.json/.csv`, `official-timeline-verification.json` |
| 9 | dated corrections applied to repo docs that implied idle silence = failure | appended blocks in `results/final/*`, `results/reconciliation/*` |
| 10 | real official fixtures + parser tests | `fixtures/official-fixtures.json`, `tests/vectors/official-button-test-fixtures.json`, `tests/test_official_fixtures.py` |
| 11 | C0/C1/C2 causal cases, offline-tested, wired into the harness | `automation/scripts/d2_cases.py`, `tests/test_d2_cases.py` |
| 12 | in-sequence single-popup A-twice prompt with click=ACK, cancel-safe | `automation/scripts/d2_cases.py`, `d2-differential.py` |

## Running (parallel static branches)

Deliverables land under `branches/<name>/`. See `branches/` when complete.

| branch | parts | question it answers |
|---|---|---|
| ef-e2-d4-d6-origin | 3, 5 | where EF/0B/E2/D4/D6 come from, and whether the burst is one gated init sequence or independent requests |
| d6-app-dependency | 4 | does the full D6 read populate app state that Button Test reads? |
| d2-state-machine | 6 | explicit state machine + state deltas around D2, per version |
| cross-version-pred2-matrix | 7 | is the official pre-D2 burst generic app init or D2-specific, across 2.22/2.23/2.24/4.0.8 |
| d2u002-0x24 | 8 | what 0x24 is in the 2.24 parser (Smi 18 hypothesis) |
| historical-d2-reinterpretation | 9 | per-run reclassification to NO_IDLE_FRAMES_OBSERVED and the strongest press-present runs |
| connection-params-11ms | 13, 14 | who initiated each interval change; the exact Linux mechanism for 11.25 ms |
| d4-reconciliation | 15 | exhaustive D4 matrix with recomputed checksums |
| d8-macro-reconciliation | 16 | D8/macro static closure, A4 layout proof, chunk-class selector, vectors |
| config-byte-map | 20 | 144-byte config evidence map, CRC/length arithmetic |

## Queued (dispatched next)

key-map (21), windows-usb-static (22), capture-corpus (23), apk-exhaustive (24), fc-dpi-ab-lighting (17-19).

## Still needs hardware (deferred)

- C0/C1/C2 live causal run with a real A-twice press (harness is ready; see the causal run plan).
- Single-press capture for the unresolved key ids (RT/id 9 etc.) - one button per popup.
- 11.25 ms connection-interval experiment (mechanism documented; not applied).
- D8/DPI/lighting/motion writes - read-first plans only, never tonight.
