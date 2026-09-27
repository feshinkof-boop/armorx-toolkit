# APK version inventory (three builds, all local)

No download was performed: every build already existed on this host and was copied (never moved,
never modified) into `apk/original/`.

| Build | File | SHA-256 | SHA-1 | Size | Package | versionName / Code | Signer | minSdk / targetSdk | ABIs | Layout |
|---|---|---|---|---|---|---|---|---|---|---|
| 2.23.0609 | `apk/original/2.23/base.apk` | `7ed18b774bf8beab0ff2ff11bc0669f4cacb9baa5cc309bf277752592a2bc892` | see `apk/manifests/2.23.json` | 35,958,605 | com.moojiang.bigbigwon | 2.23.0609 / 12 | CN=moojiang `5472…78C` | 21 / 32 | arm64-v8a, armeabi-v7a, x86_64 | fat APK |
| 2.24.0919 | `apk/original/2.24/BIGBIGWON-2.24.0919.apk` | `0bae884badc004991e638b0e62a0a6afc07256a5deabd8bb833f0bb36638f305` | see `apk/manifests/2.24.json` | 16,087,829 | com.moojiang.bigbigwon | 2.24.0919 / 24 | **CN=Android Debug** `44C3…541` | 21 / 34 | arm64-v8a | fat APK |
| 4.0.8 | `apk/original/4.0.8/BIGBIGWON-4.0.8.apkm` (base split `apk/original/4.0.8/base.apk`) | `474f66094ebbea8b0242257bbb23fc6b1baa7e54c10f13beb2cd4da14ce73abf` (base `64e0832b1f97d995b40bf994465c277340e96a4f2b6b2fc5ef1eb4e2af9378e2`) | see `apk/manifests/4.0.8.json` | 36,492,532 | com.moojiang.bigbigwon.mygt | 4.0.8 / 409 | Google Play App Signing `F745…B62` (no v1) | 24 / 36 | arm64-v8a only | APKM: base + config.{arm64_v8a,en,ar,xxhdpi} |

Full per-build field set (BLE library, Dart/Flutter, hosts, device enum, UUID table, config families,
opcode inventory, D6/D7, D8, FC/F6, E2, lighting, turbo, key IDs): `apk/manifests/<version>.json`.
Machine-readable comparison: `apk/manifests/version-matrix.json`.
Provenance (exact source path on this host + the two-way Blutter-tree matching): `apk/manifests/PROVENANCE.md`.

Notable provenance caveats, stated honestly:

* 2.24 is signed with an **Android Debug** certificate — it is a debug build, not a store build.
* 2.23's APK was supplied as `base.apk`; the identical file also exists on this host as
  `mojiangzhushou.apk` (same sha256), i.e. one artifact, two filenames.
* 4.0.8 is a Play-distributed APKM; its base split carries no native code — the Dart snapshot lives
  in the ABI split, so analysing `base.apk` alone would miss the whole protocol implementation.
