# PROVENANCE — Phase 2 APK version matrix

**No download was needed or performed for this phase.** All three builds were already present on
this host as untouched local files under `/home/salamanka/armorx-lab/apk/original/`. Every value in
`apk/manifests/*.json` and `results/version-diff/*` was produced from those local files (plus the
already-existing Blutter asm trees, which are *derived* artifacts of the same binaries).

## Where each original came from on this host

| Build | Local path | Size | SHA-256 (re-verified in this pass) | Prior origin record on this host |
|---|---|---|---|---|
| 2.23.0609 | `/home/salamanka/armorx-lab/apk/original/2.23/base.apk` | 35,958,605 | `7ed18b774bf8beab0ff2ff11bc0669f4cacb9baa5cc309bf277752592a2bc892` | prior artifact manifest `~/armorx-re/repo/research/artifact-manifest-2026-09-25.md`: "Google Drive share (user), 2026-09-25"; hash matches `~/armorx-re/repo/research/apk-2.23.0609/identity.json` |
| 2.24.0919 | `/home/salamanka/armorx-lab/apk/original/2.24/BIGBIGWON-2.24.0919.apk` | 16,087,829 | `0bae884badc004991e638b0e62a0a6afc07256a5deabd8bb833f0bb36638f305` | prior artifact manifest: "local APK collection (prior session)"; hash matches `apk-2.24.0919/identity.json` |
| 4.0.8 | `/home/salamanka/armorx-lab/apk/original/4.0.8/BIGBIGWON-4.0.8.apkm` | 36,492,532 | `474f66094ebbea8b0242257bbb23fc6b1baa7e54c10f13beb2cd4da14ce73abf` | handoff bundle already analysed on this host; hash matches `~/armorx-re/repo/research/mygt-4.0.8/provenance.md` |
| 4.0.8 (base split) | `/home/salamanka/armorx-lab/apk/original/4.0.8/base.apk` | 32,854,837 | `64e0832b1f97d995b40bf994465c277340e96a4f2b6b2fc5ef1eb4e2af9378e2` | byte-identical copy of the `base.apk` member inside the APKM — **not** an independent build |

SHA-1 values (also computed in this pass, not previously recorded):

| Build | SHA-1 |
|---|---|
| 2.23.0609 base.apk | `f5fec9f48ab4ef52d22adf84f5c115970059ef21` |
| 2.24.0919 APK | `0a19b09d6a2c6feeb62f8946a9986589979f3c76` |
| 4.0.8 APKM | `6cd397b2b0c9cfa54adbbe3dfc89e19110a3a583` |
| 4.0.8 base.apk | `74f22af1c957b0561e2ef9a193e2943a59c9c29a` |

## What was written where

| Artifact | Produced by |
|---|---|
| `apk/extracted/2.23/`, `apk/extracted/2.24/` | `unzip` of the two single APKs |
| `apk/extracted/4.0.8/splits/` + `apk/extracted/4.0.8/{base,config.*}/` | `unzip` of the APKM, then of each split |
| `apk/manifests/{2.23,2.24,4.0.8}.json` | `scripts/collect_meta.py` + `scripts/build_manifests.py` |
| `apk/manifests/version-matrix.json` | `scripts/build_manifests.py` |
| `apk/manifests/_raw/meta.json`, `_raw/keyid_maps*.json` | raw collector output kept for audit |
| `results/version-diff/static-version-matrix.{md,json}` | `scripts/build_manifests.py` |
| `static/strings/*.strings` | `strings -a -n 6` over each `libapp.so` (evidence dumps) |
| `static/frames/*-frames.json` | `reconstruct_frames.py` (prior-research tool) over each Blutter tree |

The originals themselves were **never modified** — only read (`sha256sum`, `unzip -l`, `unzip -d` into
`extracted/`, and read-only tools such as pyaxmlparser/androguard/`strings`).

## Derived inputs reused (not re-derived)

The Blutter asm trees for the three builds already existed on disk and were **not** regenerated
(Blutter is slow; the trees are complete):

| Build | Tree | Dart runtime |
|---|---|---|
| 2.23.0609 | `/home/salamanka/armorx/re/blutter_out/asm/moojiang` | 2.19.6 |
| 2.24.0919 | `/home/salamanka/armorx/re/v224/blutter_out/asm/moojiang` | 3.2.3 |
| 4.0.8 | `/home/salamanka/armorx-re/mygt408/blutter_out/asm/moojiang` | 3.12.2 |

Each tree's `pp.txt`/`objs.txt` were re-read in this pass to re-verify the device enum, config
families and opcode inventory rather than copying the earlier documents.

## Integrity check of the derived trees

Two independent checks were run in this pass to confirm each Blutter tree belongs to the binary
extracted here (rather than trusting the prior labelling):

1. **Engine hash** in the `libapp.so` snapshot header of the APK extracted in this pass — recorded
   per build in the manifests (`adb4292f…` 2.23, `f71c7632…` 2.24, `ace65428…` 4.0.8).
2. **Content match**: the Dart string-pool literal that each tree's `pp.txt` holds at a known offset
   was located verbatim in the corresponding `libapp.so`:

| Build | `pp.txt` offset | literal length | found verbatim in the APK's `libapp.so` |
|---|---|---|---|
| 2.23 | `[pp+0x4b3b0]` (ARMOR-X Pro 144 template) | 336 B | yes |
| 2.24 | `[pp+0x4b538]` (484 template) | 1,535 B | yes |
| 4.0.8 | `[pp+0x58710]` (508 template) | 1,135 B | yes |

Function code addresses cited from each tree (e.g. `getZKMVer @0x7617f4` for 2.23,
`writeDpiConfig @0x894000` for 2.24, `readFirmware @0x8b6860` for 4.0.8) all resolve inside the
matching `libapp.so`, so the trees and the extracted binaries are the same builds.

Nothing under `~/armorx-re/repo` was written to; the repository stayed clean.
