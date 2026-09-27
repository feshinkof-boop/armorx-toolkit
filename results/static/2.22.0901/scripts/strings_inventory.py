#!/usr/bin/env python3
"""Full-APK string/asset inventory for BIGBIG_WON 2.22.0901.
Extracts strings from decompressed members, dedups, classifies.
Writes raw dumps + a markdown inventory.
"""
import subprocess, os, re, hashlib, json

EX = "/home/salamanka/armorx-lab/apk/extracted/2.22.0901"
OUT = "/home/salamanka/armorx-lab/results/static/2.22.0901"
PP = "/home/salamanka/armorx-lab/static/blutter/2.22.0901/blutter_out/pp.txt"
os.makedirs(OUT, exist_ok=True)

ARTIFACTS = {
    "classes.dex": f"{EX}/classes.dex",
    "lib_arm64_libapp.so": f"{EX}/lib/arm64-v8a/libapp.so",
    "lib_armeabi_libapp.so": f"{EX}/lib/armeabi-v7a/libapp.so",
    "lib_x86_64_libapp.so": f"{EX}/lib/x86_64/libapp.so",
    "lib_arm64_libflutter.so": f"{EX}/lib/arm64-v8a/libflutter.so",
    "lib_armeabi_libflutter.so": f"{EX}/lib/armeabi-v7a/libflutter.so",
    "lib_x86_64_libflutter.so": f"{EX}/lib/x86_64/libflutter.so",
    "resources.arsc": f"{EX}/resources.arsc",
    "bledata.proto": f"{EX}/bledata.proto",
    "AndroidManifest.xml": f"{EX}/AndroidManifest.xml",
    "DebugProbesKt.bin": f"{EX}/DebugProbesKt.bin",
}
# assets text files
for root, _, files in os.walk(f"{EX}/assets"):
    for f in files:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, EX)
        if rel.endswith((".json", ".js", ".css", ".proto", ".txt")):
            ARTIFACTS["asset:" + rel] = p
for f in os.listdir(f"{EX}/google/protobuf"):
    ARTIFACTS["google/" + f] = f"{EX}/google/protobuf/{f}"

RAW = {}
ALL = set()
for name, path in ARTIFACTS.items():
    out = subprocess.run(["strings", "-a", "-n", "4", path], capture_output=True).stdout.decode("latin1")
    lines = [l for l in out.splitlines() if l.strip()]
    RAW[name] = lines
    ALL.update(lines)
    # dump
    with open(os.path.join(OUT, f"strings-{name.replace('/','_')}.txt"), "w") as fh:
        fh.write("\n".join(lines) + "\n")

# Dart pool string literals (canonical Dart string set)
pp = open(PP, "rb").read().decode("latin1")
dart = re.findall(r'String: "(.*)"', pp)
dart = [d.replace('\\"', '"').replace("\\n", "\n") for d in dart]
DART = set(dart)
ALL.update(DART)
with open(os.path.join(OUT, "strings-dart-pool-pp.txt"), "w") as fh:
    fh.write("\n".join(sorted(DART)) + "\n")

print("artifact string counts:")
for k, v in RAW.items():
    print(f"  {k}: {len(v)}")
print("dart pool strings:", len(DART), "grand-total unique:", len(ALL))

# ---------------- classification ----------------
def uniq_sorted(pred, src=ALL):
    return sorted({s for s in src if pred(s)})

def dump(name, items):
    with open(os.path.join(OUT, f"class-{name}.txt"), "w") as fh:
        fh.write("\n".join(items) + "\n")

ble = uniq_sorted(lambda s: re.search(r'\b(A5|A4|A8)\b|FFE1|FFE2|ffe1|ffe2|GATT|gatt|characteristic|Characteristic|notify|indicate|MTU|ble_flutter|flutter_reactive_ble|reactive_ble|bledata|BluetoothGatt|serviceUuid|scanMode|writeWith|write-with', s))
dev = uniq_sorted(lambda s: re.search(r'devRainbow|devArmorX|devNone|ARMOR-X|AEMOR-X|ArmorX|armorx|Rainbow|BLITZ|Blitz|CHOCO|Gale|C2SL|MSY|DouJiang|device_armor|device_rainbow', s))
urls = uniq_sorted(lambda s: re.search(r'https?://|\.com|\.cn|\.aliyuncs\.com|:\d{2,5}\b|/dev/', s))
errs = uniq_sorted(lambda s: re.search(r'Error|error|Exception|exception|failed|Failed|fail |invalid|Invalid|assert|Assertion|warn|WARN|TODO|debug|Debug', s))
plugins = uniq_sorted(lambda s: re.search(r'^package:|_release\.kotlin_module|^io\.flutter|flutter\.dev|FlutterPlugin|MethodChannel|EventChannel|shared_preferences|url_launcher|device_info_plus|package_info_plus|permission_handler|fluttertoast|path_provider|sqflite', s))
for n, items in (("ble_protocol", ble), ("device_models", dev), ("server_urls", urls), ("error_debug", errs), ("flutter_plugins", plugins)):
    dump(n, items)
    print(f"class {n}: {len(items)}")

json.dump({k: len(v) for k, v in RAW.items()}, open(os.path.join(OUT, "_artifact-string-counts.json"), "w"), indent=1)