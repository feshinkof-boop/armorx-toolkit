#!/usr/bin/env python3
"""Phase 1 baseline collector for armorx-lab.

Writes:
  baselines/host/host-baseline.txt   - OS/kernel/CPU/RAM/disk/network/BT/USB snapshot
  baselines/host/tool-versions.json  - version + path for every research tool
Read-only: never changes radio or network state.
"""
import json, os, shutil, subprocess, sys, datetime

LAB = "/home/salamanka/armorx-lab"
HOST = os.path.join(LAB, "baselines/host")
os.makedirs(HOST, exist_ok=True)
CLEAN_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/salamanka/.local/bin"


def run(cmd, shell=True, env_path=CLEAN_PATH):
    env = dict(os.environ)
    env["PATH"] = env_path
    try:
        p = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=120, env=env)
        out = (p.stdout or "").rstrip()
        err = (p.stderr or "").rstrip()
        return out if out else err
    except Exception as e:
        return f"<error: {e}>"


def first_line(s):
    return (s or "").splitlines()[0] if (s or "").strip() else ""


def which(name, env_path=CLEAN_PATH):
    env = dict(os.environ); env["PATH"] = env_path
    for d in env_path.split(":"):
        p = os.path.join(d, name)
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None


# ---------------------------------------------------------------- host baseline
now = datetime.datetime.now().astimezone()
sec = []
def add(title, cmds):
    sec.append(f"\n{'='*72}\n{title}\n{'='*72}")
    for label, cmd in cmds:
        out = run(cmd)
        sec.append(f"\n$ {cmd}\n# {label}\n{out}")

sec.append("ARMORX-LAB HOST BASELINE")
sec.append(f"collected: {now.isoformat()}")
sec.append(f"hostname: {run('hostname')}")

add("OS / KERNEL / ARCH", [
    ("os-release", "cat /etc/os-release"),
    ("uname", "uname -a"),
    ("lsb", "lsb_release -a 2>/dev/null || true"),
])
add("CPU", [
    ("model", "grep -m1 'model name' /proc/cpuinfo"),
    ("logical CPUs", "nproc"),
    ("lscpu summary", "lscpu | grep -E 'Model name|Architecture|CPU\\(s\\)|Thread|Core|Socket|MHz' "),
])
add("MEMORY", [
    ("free -h", "free -h"),
    ("MemTotal", "grep -E '^MemTotal|^SwapTotal' /proc/meminfo"),
])
add("DISK", [
    ("df -h / /home /var", "df -h / /home /var 2>/dev/null"),
    ("lsblk", "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT 2>/dev/null"),
])
add("NETWORK INTERFACES", [
    ("ip -br addr", "ip -br addr"),
    ("ip addr (full)", "ip addr"),
    ("ip route", "ip route"),
    ("default gateway", "ip route show default"),
    ("ip -br link", "ip -br link"),
])
add("PRIMARY WIFI wlp3s0 ASSOCIATION (read-only)", [
    ("iw dev wlp3s0 link", "iw dev wlp3s0 link"),
    ("nmcli device status wlp3s0", "nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2>/dev/null | grep wlp3s0 || true"),
    ("iw dev", "iw dev"),
])
add("RFKILL", [
    ("rfkill list", "rfkill list"),
])
add("BLUETOOTH ADAPTERS (read-only)", [
    ("bluetoothctl list", "bluetoothctl list 2>/dev/null"),
    ("btmgmt info (hci0)", "btmgmt -i 0 info 2>/dev/null; btmgmt info 2>/dev/null"),
    ("hciconfig", "hciconfig -a 2>/dev/null || true"),
])
add("USB DEVICES", [
    ("lsusb", "lsusb"),
    ("lsusb -t", "lsusb -t"),
])
add("PCI / RADIO HW", [
    ("lspci net/bt", "lspci 2>/dev/null | grep -iE 'network|bluetooth|wireless|ethernet' || true"),
])

open(os.path.join(HOST, "host-baseline.txt"), "w").write("\n".join(sec) + "\n")
print("wrote host-baseline.txt", len("\n".join(sec)), "chars")


# ---------------------------------------------------------------- tool versions
V = os.path.join(LAB, "ble/bumble/venv")
VENV_PATH = f"{V}/bin:" + CLEAN_PATH

def rec(name, path, version, note=None, source=None):
    d = {"name": name, "path": path, "version": version}
    if note: d["note"] = note
    if source: d["source"] = source
    return d

tools = []

# adb / android sdk
adb_p = which("adb")
tools.append(rec("adb", adb_p, first_line(run(f"{adb_p} version")) if adb_p else None,
                 source="apt: adb 1:34.0.5-12build1" if adb_p else None))
sdk_home = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or ""
sdkman = which("sdkmanager")
if not sdkman:
    for c in ["/usr/lib/android-sdk/cmdline-tools/latest/bin/sdkmanager",
              os.path.expanduser("~/Android/Sdk/cmdline-tools/latest/bin/sdkmanager"),
              "/opt/android-sdk/cmdline-tools/latest/bin/sdkmanager"]:
        if os.path.exists(c): sdkman = c; break
tools.append(rec("Android SDK (ANDROID_HOME / sdkmanager)", sdkman,
                 first_line(run(f"{sdkman} --version")) if sdkman else "MISSING",
                 note=f"ANDROID_HOME={sdk_home or '(unset)'}"))
emul = which("emulator")
tools.append(rec("Android emulator", emul, first_line(run(f"{emul} -version")) if emul else "MISSING"))

# java toolchain
java_p = which("java")
tools.append(rec("java", java_p, first_line(run(f"{java_p} -version 2>&1")) if java_p else "MISSING",
                 source="apt: default-jre-headless 2:1.25-77"))
javac_p = which("javac")
tools.append(rec("javac", javac_p, first_line(run(f"{javac_p} -version")) if javac_p else "MISSING",
                 note="not installed (only default-jre-headless installed; JDK not in Phase-1 scope)"))

# python / pip / git
py = "/usr/bin/python3.14" if os.path.exists("/usr/bin/python3.14") else which("python3")
tools.append(rec("python3", py, run(f"{py} --version")))
tools.append(rec("pip", "/usr/bin/python3 -m pip", first_line(run("/usr/bin/python3 -m pip --version"))))
git_p = which("git")
tools.append(rec("git", git_p, first_line(run(f"{git_p} --version")) if git_p else "MISSING"))

# decompilers / RE
jadx_p = which("jadx")
tools.append(rec("jadx", jadx_p, first_line(run(f"{jadx_p} --version 2>&1")) if jadx_p else "MISSING",
                 note="installed manually from GitHub release (not in Ubuntu 26.04 apt)",
                 source="https://github.com/skylot/jadx/releases/download/v1.5.6/jadx-1.5.6.zip -> /opt/jadx"))
apktool_p = which("apktool")
tools.append(rec("apktool", apktool_p, first_line(run(f"{apktool_p} --version 2>&1")) if apktool_p else "MISSING",
                 source="apt: apktool 2.7.0+dfsg-7.1ubuntu1"))
ghidra_p = None
for c in ["/opt/ghidra", "/usr/share/ghidra", os.path.expanduser("~/ghidra"), os.path.expanduser("~/tools/ghidra")]:
    if os.path.exists(c): ghidra_p = c; break
tools.append(rec("Ghidra", ghidra_p, "MISSING" if not ghidra_p else run(f"ls {ghidra_p} | head -1"),
                 note="not installed; not in Phase-1 install list"))
blutter_p = None
for c in ["/home/salamanka/armorx/re/blutter/blutter.py", os.path.expanduser("~/blutter/blutter.py")]:
    if os.path.exists(c): blutter_p = c; break
blutter_ver = "MISSING"
if blutter_p:
    blutter_ver = first_line(run("git -C /home/salamanka/armorx/re/blutter log -1 --format='%h %ci'")) or "present"
tools.append(rec("Blutter", blutter_p, blutter_ver,
                 note="pre-existing checkout; dartvm builds: " + run("ls /home/salamanka/armorx/re/blutter/bin")))
# readelf/objdump/nm/strings
binutils = {}
for t in ["readelf", "objdump", "nm", "strings"]:
    p = which(t)
    binutils[t] = (p, first_line(run(f"{p} --version 2>&1")) if p else "MISSING")
bver = binutils["readelf"][1]
for t in ["readelf", "objdump", "nm", "strings"]:
    tools.append(rec(t, binutils[t][0], binutils[t][1], source=f"GNU binutils {bver}"))

# frida / bumble (venv)
frida_p = f"{V}/bin/frida"
tools.append(rec("frida", frida_p if os.path.exists(frida_p) else None,
                 run(f"{frida_p} --version") if os.path.exists(frida_p) else "MISSING",
                 source="pip (venv): frida-tools 14.10.4 / frida 17.19.0"))
fs = None
for root in ["/opt", "/usr/local", os.path.expanduser("~")]:
    hit = run(f"find {root} -maxdepth 6 -name 'frida-server*' 2>/dev/null | head -1")
    if hit and "error" not in hit and hit.strip():
        fs = hit.strip(); break
tools.append(rec("frida-server", fs, "MISSING" if not fs else "present",
                 note="not present locally; must be pushed to target device per-arch"))
bumble_p = f"{V}/bin/bumble-console"
tools.append(rec("Bumble (bumble)", bumble_p if os.path.exists(bumble_p) else None,
                 run(f"{V}/bin/python -c \"from importlib.metadata import version;print(version('bumble'))\"") if os.path.exists(f"{V}/bin/python") else "MISSING",
                 note="venv /home/salamanka/armorx-lab/ble/bumble/venv; no 'python -m bumble' entrypoint, use bumble-* CLIs or import bumble",
                 source="pip (venv): bumble 0.0.218"))

# bluetooth stack
tools.append(rec("BlueZ (bluetoothd)", which("bluetoothd") or which("bluetoothctl"),
                 run("bluetoothd -v 2>&1") or run("dpkg -s bluez | grep -i ^Version"),
                 source="apt: bluez 5.85-4ubuntu0.2"))
tools.append(rec("btmgmt", which("btmgmt"), run("btmgmt --version 2>&1")))
tools.append(rec("bluetoothctl", which("bluetoothctl"), run("dpkg -s bluez | grep -i ^Version"),
                 source="bluez 5.85"))
tools.append(rec("btmon", which("btmon"), run("btmon --version 2>&1") or "present (bluez 5.85)"))

# capture / proxy
tools.append(rec("tshark", which("tshark"), first_line(run("tshark --version 2>&1")),
                 source="apt: tshark 4.6.4-1"))
dumpcap_p = which("dumpcap")
tools.append(rec("dumpcap", dumpcap_p, first_line(run(f"{dumpcap_p} --version 2>&1")) if dumpcap_p else "MISSING",
                 note="wireshark-common installed with setuid=false (noninteractive debconf)"))
tools.append(rec("wireshark (CLI)", which("wireshark"), "MISSING" if not which("wireshark") else "present",
                 note="wireshark GUI not installed; libwireshark19 + wireshark-common present"))
tools.append(rec("mitmproxy", which("mitmproxy"), first_line(run("mitmproxy --version 2>&1")),
                 source="apt: mitmproxy 8.1.1-4"))
tools.append(rec("pipx", which("pipx"), run("pipx --version 2>&1"), source="apt: pipx 1.8.0-1"))

# misc
openssl_p = which("openssl")
tools.append(rec("openssl", openssl_p, first_line(run(f"{openssl_p} version")) if openssl_p else "MISSING"))
unzip_p = which("unzip")
tools.append(rec("unzip", unzip_p, first_line(run(f"{unzip_p} -v 2>&1")) if unzip_p else "MISSING"))
sq = which("sqlite3")
tools.append(rec("sqlite3", sq, first_line(run(f"{sq} --version")) if sq else "MISSING",
                 note="CLI not installed; libsqlite3-0 3.46.1-9ubuntu0.3 present (binary lib). Not in Phase-1 install list."))

res = {
    "collected": now.isoformat(),
    "host": run("hostname"),
    "collected_by": "armorx-lab phase1",
    "path_used": CLEAN_PATH + f" (venv bin prepended for frida/bumble: {V}/bin)",
    "missing": [t["name"] for t in tools if str(t.get("version", "")).strip() in ("MISSING", "", "None", "present")],
    "tools": tools,
}
open(os.path.join(HOST, "tool-versions.json"), "w").write(json.dumps(res, indent=2) + "\n")
print("wrote tool-versions.json")
print("MISSING:", res["missing"])
