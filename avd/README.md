# armorx-lab / avd — REFERENCE vs RESEARCH split

Two independent AVD families, both created from **x86_64 `google_apis` system
images**, each with its own `ANDROID_AVD_HOME` so their state never mixes:

| Family      | Directory                    | Purpose                                                        | System image                        | Guest ABI               |
|-------------|------------------------------|----------------------------------------------------------------|-------------------------------------|-------------------------|
| **REFERENCE** | `avd/reference/avd-home/`  | Clean, minimally modified golden baseline. Used to observe the *unmodified* app: what it does out of the box. No instrumentation, no `-writable-system`, no extra properties. | `system-images;android-33;google_apis;x86_64` | x86_64 only |
| **RESEARCH**  | `avd/research/avd-home/`   | Instrumented / debug device. Frida server, `-writable-system`, extra debug props, virtual-Bluetooth (netsim). Everything invasive happens here. | `system-images;android-33;google_apis;x86_64` and `system-images;android-30;google_apis;x86_64` | API33: x86_64 only; API30: x86_64 **+ arm64-v8a via libndk_translation** |

## Why two families

* A REFERENCE capture must be trustworthy: if we ever tamper with system
  properties or push a frida-agent, the capture is no longer a clean baseline.
* A RESEARCH device is expected to be dirty — it is where Frida, `-writable-system`
  and the virtual-Bluetooth bridge are wired in.
* Keeping them in separate `ANDROID_AVD_HOME` directories means the REFERENCE
  userdata is never touched by research instrumentation.

## ABI reality on this host (x86_64) — important

This host is x86_64. Native `arm64` system images **cannot** run here:

```
PANIC: Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host.
```

(vendor-documented behaviour — arm64-v8a system images require an arm64 host.)

The workaround for arm64-only *apps* is **binary translation inside an x86_64
guest**, which only exists on the Android 11 (API 30) `google_apis` image:

| Image                                   | `ro.product.cpu.abilist`                                  | native bridge              |
|-----------------------------------------|-----------------------------------------------------------|----------------------------|
| `system-images;android-33;google_apis;x86_64` | `x86_64`                                             | none                       |
| `system-images;android-30;google_apis;x86_64` | `x86_64,x86,arm64-v8a,armeabi-v7a,armeabi`           | `libndk_translation.so`    |

Consequence, per BIGBIG WON build (verified — see `results/final/avd-frida-readiness.md`):

| Build | ABIs in APK                    | API 33 x86_64 | API 30 x86_64 (translation) |
|-------|--------------------------------|---------------|------------------------------|
| 2.23  | arm64-v8a, armeabi-v7a, x86_64 | **installs + runs natively** | runs |
| 2.24  | arm64-v8a only                 | `INSTALL_FAILED_NO_MATCHING_ABIS` | installs, **crashes on launch (SIGILL in libndk_translation)** |
| 4.0.8 | arm64-v8a only (split APK)     | `INSTALL_FAILED_NO_MATCHING_ABIS` | installs, **crashes on launch (SIGILL in libndk_translation)** |

## Installing split APKs without touching signatures

The 4.0.8 build ships as an `.apkm` (a ZIP of split APKs). We **never re-sign or
modify** the APKs. All splits must be installed in one atomic session with
`install-multiple`; Android validates that every split is signed by the same
certificate as `base.apk`:

```bash
# extract the splits (read-only operation on the .apkm)
mkdir -p /home/salamanka/armorx-lab/apk/extracted/4.0.8-apkm-splits
unzip -o /home/salamanka/armorx-lab/apk/original/4.0.8/BIGBIGWON-4.0.8.apkm \
      -d /home/salamanka/armorx-lab/apk/extracted/4.0.8-apkm-splits

# install atomically, preserving original signatures
adb -s emulator-5556 install-multiple -r \
    base.apk config.arm64_v8a.apk config.en.apk config.xxhdpi.apk config.ar.apk
```

Installing `base.apk` alone fails with
`INSTALL_FAILED_MISSING_SPLIT: Missing split for com.moojiang.bigbigwon.mygt` —
that is expected, not a defect.

## Scripts

* `reference/create-reference-avd.sh` — creates the clean baseline AVD.
* `reference/launch-reference.sh`     — boots it (headless-capable).
* `research/create-research-avd.sh`   — creates the instrumented AVDs.
* `research/launch-research.sh`       — boots with virtual-Bluetooth endpoint.
* `research/install-app.sh`           — installs a build (handles split APKs).
* `research/push-frida-server.sh`     — pushes + starts the matching frida-server.
