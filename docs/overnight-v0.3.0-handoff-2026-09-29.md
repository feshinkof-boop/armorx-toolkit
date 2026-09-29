# Overnight v0.3.0 shift handoff, 2026-09-29

## Timing and state

| item | value |
| --- | --- |
| shift | unattended offline shift |
| starting commit (main) | `github/main` as fetched at shift start |
| starting research tip | `8747846` (untouched) |
| branch worked on | `dev/v0.3.0-offline-2026-09-29` |
| ending commit | see `git log -1` on that branch |
| commits created | 5 during the overnight shift on the dev branch; 2 post-shift repair/documentation commits; 1 on a separate research branch |
| research branch created | `research/xbox-rt-threshold-2026-09-29` (tip `e302829`) |

## Tests

| state | result |
| --- | --- |
| before | the public suite as shipped on `main` |
| after | **98 passed, 0 failed, 0 skipped** in GitHub Actions on Python 3.10, 3.11, 3.12 and 3.13 after the post-shift CI repair; the overnight local run was 96 passed before the two regression tests were added |

No test was skipped or deleted. Nothing requires hardware: discovery runs against a synthetic
sysfs tree, GIP and framing tests use synthetic bytes built from the documented layout.

## Post-shift CI repair

GitHub Actions was present and caught one host-dependent diagnostic test that the overnight local
run did not expose. On a clean runner with no `xpad` module loaded,
`test_doctor_on_a_tree_without_devices` failed because `doctor()` treated the missing module as
fatal even though no Xbox personality was attached.

Commit `e653317` fixed the behavior instead of weakening the test:

* no Xbox personality + no `xpad` => `xpad_module=not_needed`, diagnosis remains successful;
* Xbox personality present + no `xpad` => `xpad_module=missing`, diagnosis fails with an actionable hint;
* Xbox personality + `xpad` loaded => `xpad_module=present`.

Two deterministic regression tests now mock the module state so the result does not depend on the
host running pytest. GitHub Actions run `36532070949` passed all four supported Python versions
(3.10-3.13), with **98 passed** in the 3.11 job.

## What was added

```text
src/armorx/protocol.py   A5/A4 framing, sum-mod-256 checksum, fragment build and index-keyed
                         reassembly, opcode table with evidence levels, stream splitting
src/armorx/gip.py        offline type-0x20 input parser, both observed report forms, proven
                         offsets only, unknown byte spans retained
src/armorx/device.py     sysfs discovery, classification with explicit caveats, doctor()
src/armorx/transport.py  Transport protocol, scripted mock, optional read-only hidraw
src/armorx/cli.py        groups: device list|inspect|doctor, protocol decode|build|opcodes|
                         describe-image, gip decode|forms
tests/                   5 new modules, 96 tests total in the suite
docs/                    v0.3.0-release-plan.md, linux-support.md, offline-tools.md,
                         cli.md section, usb-protocol.md personality/GIP section
RELEASE_NOTES_v0.3.0-draft.md, CHANGELOG.md Unreleased section
```

## Release readiness

* Package version left at **0.2.0**. The intended bump to 0.3.0 is documented in the changelog
  under Unreleased and in the draft release notes. No tag, no published release, no merge to main.
* Draft PR against `main` opened (see the report). It is a draft and must not be merged.
* Acceptance criteria and non-goals are in `docs/v0.3.0-release-plan.md`.

## Hardware validation still required

1. Identity recognition was implemented from captures; a fresh unit has never been seen by this code.
2. The vendor interface has never carried payload in any capture - unknown whether it ever does.
3. The 32 to 48 byte GIP transition cause is unknown.
4. The RT digital path is proven statically and has never been observed end to end.
5. `armorx device doctor`'s hidraw-permission diagnostics were exercised only against synthetic nodes.
6. The Windows application remains unvalidated (no VM, no Wine).

## Blockers recorded

* `BLOCKER-HW-001` no USB device present this shift: recognition and doctor paths cannot be
  exercised against real hardware.
* `BLOCKER-HW-002` no Android device: the community import shapes stay unvalidated against a real client.
* `BLOCKER-ENV-001` the Hermes interpreter has no pytest; the suite runs with `/usr/bin/python3.14`.


## 0x1e0a426 (static side quest) - RESULT

**PROVEN STATIC.** 166 bytes, one caller in the image (`0x1e0cee8`). ABI: `r0` = channel index
(the caller passes 1), `r1` = current reading (the candidate RT byte read at `0x1e0cee2`),
`r4` = base pointer supplied by the caller. Per-channel state at `base+index`:
`+0x76` previous reading, `+0x78` mode, `+0x7a` hysteresis counter, `+0x7c` armed byte.
Return value is `0xFF` or `0x00` derived from the armed byte - never an analogue value.

Rule set: decreasing with mode 0 sets mode 1, clears armed, and arms only on a drop of at least
`0x1f`; further decreases need 3 consecutive samples to clear armed; increasing with mode 1
clears armed; other increases need 5 consecutive samples and a rise of at least `0x1e` to clear
armed; equal values arm. `previous := current` unconditionally, then return `0xFF` if armed.

**Consequence for the D2 question:** the caller writes that `0xFF`/`0x00` straight into the
candidate RT byte at `sp+1093` and drives mask bit `0x200` from the same non-zero test. When this
path runs, the RT byte in a D2 frame is the *armed decision*, not the analogue reading. This is a
candidate explanation both for the observed `0, 17, 27, 96, 255` spread and for why an
analogue-only change need not produce the same event.

**New observation from the caller window (not yet written into the research artifact):** the RT
block is gated on a state byte at `r8+0x1db` (`0x1e0cedc: r0 = b[r8+0x1db]; if (r0 == 0) goto
0x1e0cf44`), mirroring the LT block gated on `r8+0x1d6` at `0x1e0ceb6`. That is worth folding into
`results/firmware/rt-threshold-0x1e0a426.md` on the research branch.

**Open:** whether LT ever uses this helper (LT's byte is set to `0xff` directly in the synthesis
block); the mode byte beyond its 0/1 role; the caller context that supplies `r4`.

Research commit: `e302829` on `research/xbox-rt-threshold-2026-09-29`, pushed. The existing
research branch `research/physical-armorx-live-2026-09-27` was left untouched at `8747846`.

## Recommended next 10 tasks, in priority order

1. Fold the `r8+0x1db` / `r8+0x1d6` gate observation into the research artifact and re-verify the
   caller's `r4` provenance.
2. Reverse the remaining half of the D2 emission gate: order the synthesis block against the
   14-byte memcmp by dominance, closing whether an analogue-only change can emit.
3. Add a PCAP reader behind an optional extra so `armorx capture inspect` can consume usbmon files,
   with no new mandatory dependency.
4. Add import/export validation and content hashing for shareable configuration and macro files,
   with a schema version field.
5. Extend `device doctor` to emit a copy-pasteable diagnostics bundle for issue reports.
6. Validate `armorx device list` against several real USB topologies (needs hardware).
7. Explain the 32 to 48 byte GIP transition with a dedicated capture series (needs hardware).
8. Reverse `0x1e0a426`'s mode byte semantics and confirm whether LT shares the helper.
9. Add fuzzing or property tests for `parse_frame`, `split_stream` and `parse_gip_input`.
10. Prepare the 0.3.0 version bump commit once hardware validation of discovery is available.

## Is the tree safe for a draft v0.3.0 RC?

Yes for a **draft**. Every added feature is offline, tested and documented, the suite is green with
no skips, and no command can write to a device. It is not ready to be called validated: no added
path has been exercised against real hardware, so v0.3.0 should stay a draft until the hardware
items above are closed.
