# Dynamic version diff (Phase 9) — NOT ATTEMPTED, with the exact blocker

The cross-version dynamic matrix was **not** produced, because only one of the three builds can
execute on this host. This is a documented blocker, not a failure of the harness.

| Build | Dynamic availability | Why |
|---|---|---|
| 2.23.0609 | WORKING | ships an `x86_64` ABI → runs natively on `android-33;google_apis;x86_64`; Frida platform hooks attached and captured BLE/network calls |
| 2.24.0919 | BLOCKED | arm64-v8a only: `INSTALL_FAILED_NO_MATCHING_ABIS` on API 33; installs under API 30 ARM translation but dies with SIGILL in `libndk_translation` at launch |
| 4.0.8 | BLOCKED (`DYNAMIC_AVD_4.0.8_BLOCKED_BY_ABI`) | arm64-v8a-only split APK; identical SIGILL under translation. Installing an arm64 AVD is impossible here: `PANIC: Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host` |

What is ready to run the moment an arm64 target exists (a physical device via USB, or an arm64 host):

* virtual ARMOR-X peripheral (verified working) and its launch/attach commands;
* `frida/hooks/{2.23,2.24,4.0.8}/entry-*.js` + `frida/run-hooks.py` with the platform-level BLE and
  network hook groups (verified to attach and fire on 2.23);
* btsnoop capture + correlation guide;
* `automation/experiment-matrix/matrix.json` (L01–L08) driving the same workflow against every build.

Required observations per build, once runnable: scan filter and advertising-name requirement,
connection sequence, service enumeration order, characteristic subscription, initial writes,
command order and timing, retry logic, `0B`/`EF`/`D6`/`E2` handling, identity reads, server
registration call, disconnect/reconnect and sleep behaviour — each classified as WIRE PROTOCOL
CHANGE / TRANSPORT IMPLEMENTATION CHANGE / UI CHANGE / SERVER-API CHANGE / DEVICE-ENUM CHANGE /
TIMING CHANGE / UNKNOWN.
