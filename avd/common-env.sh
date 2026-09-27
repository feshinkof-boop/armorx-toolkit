# armorx-lab :: Android SDK / AVD environment
#
# Source this from any script in avd/:
#     . "$(dirname "$0")/common-env.sh"
#
# These paths reflect the toolchain that was actually installed and verified on
# this host (see results/final/avd-frida-readiness.md for the evidence log).

export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"

export SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
export AVDMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/avdmanager"
export EMULATOR="$ANDROID_HOME/emulator/emulator"
export ADB="$ANDROID_HOME/platform-tools/adb"

# frida lives in its own venv
export LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export FRIDA_PY="$LAB_ROOT/.venv-frida/bin/python"
export FRIDA_CLI="$LAB_ROOT/.venv-frida/bin/frida"
export BUMBLE_PY="$LAB_ROOT/.venv-bumble/bin/python"
