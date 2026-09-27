#!/usr/bin/env python3
"""Independent manifest cross-check with androguard (silent)."""
import logging
logging.disable(logging.CRITICAL)
from androguard.core.apk import APK

files = {
    "2.23": "apk/original/2.23/base.apk",
    "2.24": "apk/original/2.24/BIGBIGWON-2.24.0919.apk",
    "4.0.8": "apk/original/4.0.8/base.apk",
    "4.0.8/split/arm64_v8a": "apk/extracted/4.0.8/splits/config.arm64_v8a.apk",
    "4.0.8/split/en": "apk/extracted/4.0.8/splits/config.en.apk",
    "4.0.8/split/ar": "apk/extracted/4.0.8/splits/config.ar.apk",
    "4.0.8/split/xxhdpi": "apk/extracted/4.0.8/splits/config.xxhdpi.apk",
}
for k, f in files.items():
    a = APK(f)
    print("#####", k)
    print("  pkg=%s vName=%s vCode=%s" % (a.get_package(), a.get_androidversion_name(), a.get_androidversion_code()))
    print("  minSdk=%s targetSdk=%s maxSdk=%s compileSdk=%s" % (
        a.get_min_sdk_version(), a.get_target_sdk_version(),
        a.get_max_sdk_version(), a.get_effective_target_sdk_version()))
    raw = a.get_android_manifest_axml().get_xml()
    import re
    m = re.search(rb'<manifest[^>]*>', raw)
    print("  manifest_tag:", m.group(0).decode('utf-8', 'replace')[:400] if m else "?")
