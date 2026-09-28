# ARMOR-X handoff — 2026-09-28 firmware/updater ecosystem shift

- `overnight.bundle` — 110191888 bytes (RE-CUT 2026-09-28, HEAD `174915d`)
  - sha256 `650bbf2b70b9a4d2b49fdb54325ee70b1b23c3cd182ebe8b808f9c030e5b071b`
- `firmware-shift.patch` — 156367 bytes, sha256 `54486ebf3793bb9cb02d6e37f4d764157e7bb99be0460b309e997cdea28ea827`
  - the four commits `b33c723..174915d` (`research: inventory ArmorX firmware packages`,
    `research: reconstruct the BigBigWon BUP container and JieLi unpack pipeline`,
    `research: map the ArmorX firmware ecosystem, images and updater`,
    `research: identify the ArmorX firmware ISA and stock SDK components`)
  - **verified**: `git apply --check` against a pristine `b33c723` worktree applies cleanly.
- Bundle clone re-verified: HEAD `174915d`, suite **312 passed, 12 subtests passed** (clone: 310 passed, 2 skipped)
  (the two skips are the private-Blutter-tree guard and the evidence-tree-absent guard).

## New in this cut (four vendor packages unpacked offline; no hardware touched)

- **BUP container decoded**: header + sub-images stored as zlib blocks of 32768 B preceded by
  `(compressed, uncompressed)` u32 records. Tooling: `tools/firmware/armorx_bup.py`,
  `armorx_fw_pipeline.py`, `armorx_fw_compare.py`, `armorx_fw_reports.py`.
- **CN vs international V41 answered**: 34.8 MB vs 5.8 MB = the bundled 28 MB Android APK plus
  Chinese-only text files; all firmware payloads and all 7 updater files are byte-identical.
- **All seven flash images unpacked and decrypted** (JieLi `jl-new-fw`, AC632N/AC6321A, app base
  `0x01E00000`, entry `0x01E00120`); seven plaintext `app.bin` recovered.
- Vendor debug strings prove the app carries the frame dispatcher, config engine, macro engine,
  stick/trigger curves, gyro engine, USB host+device, 2.4 GHz select and the console `DEV_TYPE_*`
  table, so the AC6321A is the main application MCU rather than a BLE bridge.
- Reports: `results/firmware/download-provenance.md`, `results/firmware/v41-chinese-vs-international.md`,
  `results/firmware/bup-format.md`, `results/firmware/firmware-ecosystem.md`,
  `results/final/armorx-firmware-master-report.md`,
  `results/reconciliation/firmware-unknown-ledger.json` (21 entries) and its `.md`.
- Blocker: no BD19/q32s disassembler was available offline (ledger `FW-U-021`, priority critical).
- No updater binary was executed: no disposable VM or Wine sandbox exists on this host.

---

# ARMOR-X handoff — 2026-09-27/28 overnight shift, key-map closure + RT analog

- `overnight.bundle` — 109867524 bytes (RE-CUT 2026-09-28, HEAD `0e59a66`)
  - sha256 `c438096916206745562c7a05a330b0a20338d2d955414b65c9a82341bb20e983`
- `overnight-shift-range.bundle` — 693459 bytes
  - sha256 `ded1d59e1e41f6ad40a1db934327d89c0f4e49bdb779d4f048f430a358e15260`
- `overnight.patch` — 4260850 bytes
  - sha256 `95cf34925cebcb91d3f9321229bfc16f98c9d98b30a3b1c2f3bcd8278e1d9b54`

## New in this cut (F7 read probed live, read-only)

- `f7-read-probe.patch` — 87932 bytes, sha256 `a19a62e0817fc6889aa729503399f8f64a6c285f0d201fd7a7b1f7a0efdd7023`
  - the single commit `c36d71a..0e59a66` (`research: probe F7 step-length read path`)
  - **verified**: `git apply --check` against a pristine `c36d71a` worktree applies cleanly.
- Bundle clone re-verified: HEAD `0e59a66`, suite **284 passed, 1 skipped**.
- Result: `F7_NO_REPLY_LINK_HEALTHY` — `A5 04 F7 A0` twice, zero notifications, while `0B` and the FC
  DPI control answered before/between/after in 23-30 ms. **`F7_WRITE_ONLY` is NOT concluded.**
- Runner `automation/scripts/f7-read-probe.py` is read-only by construction (allow-list guard).

## Previous cut (DPI / trigger-travel protocol, static only)

- `dpi-trigger-protocol.patch` — 117100 bytes, sha256 `1b38961711bc731089effa33cd0c5f8b08404ea5ea64efb0a99fadc1882f3719`
  - the single commit `9224bdf..c36d71a` (`research: reconstruct DPI and trigger-travel protocol`)
  - **verified**: `git apply --check` against a pristine `9224bdf` worktree applies cleanly.
- Bundle clone re-verified: HEAD `c36d71a`, suite **273 passed, 1 skipped**.
- Headline: **F7 is the stick step-length / "step accuracy" setting — the trigger-travel hypothesis
  is recorded as CONTRADICTED.** FC has three separated roles; F6 is its legacy twin.
- New tool `automation/scripts/frame-literal-scan.py` reconstructs frames + checksums from the AOT
  image; it reproduces every live-answered frame exactly.

## Previous cut (RT digital id 9 proven)

- `rt-bit9-confirmation.patch` — 528969 bytes, sha256 `56f1dcb646c760323704ed2ef3428168e1005fdd709eb044bd0e40eda73f4ecc`
  - the single commit `3bddfe2..9224bdf` (`research: prove RT digital id 9`)
  - **verified**: `git apply --check` against a pristine `3bddfe2` worktree applies cleanly.
- Bundle clone re-verified: HEAD `9224bdf`, suite **258 passed, 1 skipped** (a git-ignored `.bin`).
- The key map is now complete: **27/27 physical controls proven live** (RT = digital id 9,
  mask `0x00000200`, analog byte `[16]`).

## Previous cut (RT analog piggyback)

- `rt-analog-piggyback.patch` — 456158 bytes, sha256 `c0355881897ff0071a4d0e9d17cca0b66f5ab7ea1bd5ce7b56d54ce0f062f038`
  - the single commit `e91996a..3bddfe2` (`research: test RT analog state through D2 piggyback sampling`)
  - **verified**: `git apply --check` against a pristine `e91996a` worktree applies cleanly.
- Bundle clone re-verified: HEAD `3bddfe2`, suite **244 passed, 1 skipped** (the skip is a git-ignored
  `.bin` fixture absent from a checkout).

## Previous cut

- `keymap-closure.patch` — 110630 bytes, sha256 `8b1313a14bffc61529069f5eca5cf5ad29dff908e52f48d2b93203763f416c65`
  - the single commit `2916b84..e91996a` (`research: close remaining ArmorX physical key map`)
  - **verified**: `git apply --check` against a pristine `2916b84` worktree applies cleanly (19 files).

## How to use

Complete bundle (recommended, verified):

```
git clone -b research/physical-armorx-live-2026-09-27 overnight.bundle armorx-lab
```

Range bundle (680 KB, **requires the recipient to already have base commit `9f57cc7`**):

```
git fetch overnight-shift-range.bundle research/physical-armorx-live-2026-09-27:overnight
```

Patch (verified to apply cleanly on `9f57cc7`):

```
git checkout 9f57cc7 && git am overnight.patch     # 11 commits, 182 files changed
```

## Verification performed this shift (2026-09-28 cut)

- Plain clone of the re-cut `overnight.bundle` → **HEAD `e91996a`** on `research/physical-armorx-live-2026-09-27`;
  the suite inside the clone reports **228 passed, 1 skipped, 12 subtests passed** — the single skip is
  `test_official_fixtures.py` reporting that a git-ignored `.bin` baseline fixture is absent from the
  checkout (global `*.bin` ignore rule), not a failure.
- `keymap-closure.patch` verified against a pristine `2916b84` worktree.

## Verification performed in the previous cut

- `git bundle verify`: complete history, sha1.
- Plain clone of the complete bundle → HEAD `0286036` on branch `research/physical-armorx-live-2026-09-27`, **817 files**, all key deliverables present.
- 25 guard tests passed **inside the restored clone** (`test_overnight_deliverables.py`, `test_harness_streaming_finding.py`, `test_offline_causal_run.py`) — the handoff is runnable, not just complete.
- `git apply --check` of `overnight.patch` against a pristine `9f57cc7` worktree: applies cleanly (182 files changed, 80,380 insertions, 361 deletions).
- Secret scan of the one environment file the patch carries (`automation/plasma-session.env`): **0** matches for token/secret/password/api-key/bearer/credential patterns; it holds session environment variables only (DBUS_SESSION_BUS_ADDRESS, DISPLAY, WAYLAND_DISPLAY, XAUTHORITY, XDG_*). No credentials appear in this handoff.
- No remote exists for this repository, and no push was attempted. This is not a failure state.

## Notes for the recipient

- The harness **is not silent**: see `results/reconciliation/d2-u007-harness-streaming-reconciliation.md`.
- Read `results/final/real-armorx-master-report.md` first; it supersedes every earlier handoff.
- `results/reconciliation/master-unknown-ledger.md` carries the 20 open items with their next steps.


## q32s navigation pass (2026-09-28) — tip `f5c542fcfd4a37f54484546cba58853bfe9b3dc9`

* `q32s-navigation.bundle` — full history + branch tip `f5c542fcfd4a37f54484546cba58853bfe9b3dc9` (110,325,338 bytes)
* `q32s-navigation.patch` — 174915d..f5c542fcfd4a37f54484546cba58853bfe9b3dc9 (893,510 bytes), applies cleanly on `174915d`

Verify:
```bash
git clone q32s-navigation.bundle /tmp/verify && cd /tmp/verify
git checkout 174915d && git apply --check ../q32s-navigation.patch   # clean
git apply ../q32s-navigation.patch && python3.14 -m pytest tests/ -q # 323 passed, 4 skipped, 12 subtests
```
The 4 skips are the real-data/toolchain tests: they need the vendor toolchain under
`/home/salamanka/armorx-re/toolchains/` and the extracted firmware under
`research/firmware/2026-09-28/` (both git-ignored). In the working repo, all 327 pass.

To reproduce the analysis: `tools/q32s/README.md` (toolchain provenance, wrapper rationale,
pipeline commands, and the method notes that cost real debugging time).

## Firmware-semantics pass (2026-09-28) - newest

- `armorx-firmware-semantics.bundle` - branch `research/physical-armorx-live-2026-09-27`, tip `8b79c4684f07b9145584f11880b007fb2a1f2afe`
- `armorx-firmware-semantics.patch` - `git diff 8b79c4684f07b9145584f11880b007fb2a1f2afe^..8b79c4684f07b9145584f11880b007fb2a1f2afe`; verified to apply cleanly on the
  **pre-pass tip** and to leave a suite of **339 passed / 4 skipped / 12 subtests** after applying.
- Base of this pass: `f5c542f` (327 passed / 12 subtests), branch `research/physical-armorx-live-2026-09-27`.
- Read first: `results/firmware/armorx-command-dispatch-full.{json,md,dot}`,
  `results/final/armorx-firmware-master-report.md` section 31,
  `results/reconciliation/firmware-unknown-ledger.{json,md}`.
- The 4 skips in a fresh clone are the image-dependent q32s tests: they need the unpacked V41
  `app.bin` and the JieLi toolchain, both of which are deliberately not in git.

### What this pass changed

- **FW-U-024 CLOSED**: `r9` = frame start (magic at +0, length at +1, opcode at +2, payload at +3).
- **Dispatch correction**: the parser uses `tbh` jump tables, not an if/else chain; Fc/F6 are NOT in
  any extracted table and fall to the default handler.
- **D6/D7/D8/D9 recovered** as addresses with semantics; the 144-byte config is written through
  220-byte records validated by a CRC-16/MODBUS nibble-table routine (`0x1e05628`, validator `0x1e0566a`).
- New unknowns FW-U-028/029/030 added rather than hidden.

## Protocol family reconciliation (2026-09-28) - newest

- `armorx-family-reconciliation.bundle` (branch `research/physical-armorx-live-2026-09-27`, tip `eb9e168ae5b92e0fabf48d7169951dfdb62101d7`)
- `armorx-family-reconciliation.patch` - `git diff eb9e168ae5b92e0fabf48d7169951dfdb62101d7^..eb9e168ae5b92e0fabf48d7169951dfdb62101d7`; verified to apply cleanly on the
  pre-pass tip and to leave **355 passed / 4 skipped / 12 subtests** in a fresh clone.
- Previous tip: `8b79c46`; before that `f5c542f`.
- Read first: `results/reconciliation/protocol-family-model.{json,md}`,
  `results/reconciliation/live-family-corpus.{json,md}`,
  `results/final/armorx-firmware-master-report.md` section 32.

### Headline

A5 and A4 are **one opcode space with two framing modes**, proven on both sides:

- wire: `results/experiments/physical-20260927-170455-noop-d7/raw-tx-rx.log` - A5 request answered by
  10 A4 fragments whose payloads reassemble to 144 bytes with SHA-256 `bdef9c61...` (the durable
  baseline);
- firmware: `0x1e05dc0` sets magic 0xA5 and flips it to 0xA4 when the payload does not fit, with
  `nfrags = (len+2)/(capacity-5)` reproducing the 10-fragment stream exactly.

Also closed: frame checksum is sum8 at `0x1e05dae` (FW-U-025). Retired the `0x1e0aff2`/`0x1e0a944`
"0B compare" false positives. See section 32.6 of the master report for the corrections.
## Config persistence pass (2026-09-28) - newest

- `armorx-config-persistence.bundle` / `.patch` - branch `research/physical-armorx-live-2026-09-27`,
  tip `2de236f`; patch verified to apply on the pre-pass tip, fresh clone **364 passed / 4 skipped**.
- Read first: `results/firmware/d7-persistence-callgraph.{json,md,dot}` and section 33 of
  `results/final/armorx-firmware-master-report.md`.
- Headline: the config descriptor is `0x3120 + index*0x400 + 0x44` (3 slots x 1024 B) held at
  `[0x4850+0x1b0]`; D7 writes that RAM/VM shadow and reloads it, which is *why* an immediate D6
  readback is STAGED_OK and not durable. The commit is a tail call to library `0x3003ec`, whose code
  is in no artifact on disk -> FW-U-032/033, and no vendor API name is invented for it.
