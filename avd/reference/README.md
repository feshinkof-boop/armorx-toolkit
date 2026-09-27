# REFERENCE AVD (clean baseline)

**Goal:** observe the BIGBIG WON builds exactly as an ordinary user would, with
no instrumentation and no system tampering. Captures from this device are the
trustworthy *baseline*; anything surprising found here is real app behaviour.

## Characteristics

* System image: `system-images;android-33;google_apis;x86_64` (Android 13).
* `android-33` `google_apis` is a **non-Play** image → `adb root` works, but we
  do **not** use it here.
* No `-writable-system`, no frida-server, no extra `-prop`, no `-packet-streamer-endpoint`.
* Dedicated AVD home: `avd/reference/avd-home/` (never shared with research).
* Verified ABI: `ro.product.cpu.abilist = x86_64` (no ARM translation).

## What runs here

| Build | Result on REFERENCE |
|-------|---------------------|
| 2.23  | installs and runs natively (has an `x86_64` split) |
| 2.24  | `INSTALL_FAILED_NO_MATCHING_ABIS` (arm64-only, image has no ARM translation) |
| 4.0.8 | `INSTALL_FAILED_NO_MATCHING_ABIS` (arm64-only split APK) |

So the REFERENCE device is, today, a **2.23-only** baseline. For 2.24/4.0.8 the
reference capture has to come from a physical arm64 device (see
`results/final/avd-frida-readiness.md`).

## Commands

```bash
cd /home/salamanka/armorx-lab/avd/reference
./create-reference-avd.sh          # create (idempotent, --force)
./launch-reference.sh              # boot headless on :5554
./launch-reference.sh &            # ... then in another shell:
$ANDROID_HOME/platform-tools/adb -s emulator-5554 wait-for-device
adb -s emulator-5554 install -r /home/salamanka/armorx-lab/apk/original/2.23/base.apk
adb -s emulator-5554 shell monkey -p com.moojiang.bigbigwon -c android.intent.category.LAUNCHER 1
```

Kill it with `adb -s emulator-5554 emu kill`.
