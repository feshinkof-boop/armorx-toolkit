#!/usr/bin/env python3
"""Phase 2 generator: per-build APK manifests + version matrix + provenance.

Every value carries an evidence label:
  PROVEN STATIC  - read directly from the binary / AOT asm in this pass
  STRONG EVIDENCE- one inference step away (or verified by a prior pass, re-checked here)
  INFERRED       - derived by convention, not directly observed
  UNKNOWN        - not recoverable; the command attempted is named
"""
import hashlib
import json
import os

OUT = "/home/salamanka/armorx-lab/apk/manifests"
os.makedirs(OUT, exist_ok=True)
RES = "/home/salamanka/armorx-lab/results/version-diff"
os.makedirs(RES, exist_ok=True)

CERT_223 = {
    "subject": "C=cn, ST=sz, L=sz, O=moojiang, OU=moojiang, CN=moojiang",
    "issuer": "C=cn, ST=sz, L=sz, O=moojiang, OU=moojiang, CN=moojiang",
    "serial": "5EA0DB29",
    "validity": "2022-03-18 -> 2049-08-03",
    "sha256_fingerprint": ":".join("547258CA217A1D2B278039EF8174A418A8B005855E218B4A08E76E00F234C78C"[i:i + 2] for i in range(0, 64, 2)),
    "sha1_fingerprint": ":".join("343E87938394162FC9AD6CC18F7E671D555AC794"[i:i + 2] for i in range(0, 40, 2)),
    "v1_signature_file": "META-INF/CERT.RSA",
    "evidence": "PROVEN STATIC - pyaxmlparser/androguard get_certificates on the untouched APK",
}
CERT_224 = {
    "subject": "C=US, O=Android, CN=Android Debug",
    "issuer": "C=US, O=Android, CN=Android Debug",
    "serial": "0DCA795A",
    "validity": "2024-08-12 -> 2051-12-29",
    "sha256_fingerprint": ":".join("44C3BB8C7EA35B3BB11CBFA3C2F5879240DF2E49E39816B4437B9856FBB29541"[i:i + 2] for i in range(0, 64, 2)),
    "sha1_fingerprint": ":".join("E94E3AFA40A54ECEE4EEF83F580393507FCD205A"[i:i + 2] for i in range(0, 40, 2)),
    "v1_signature_file": "META-INF/CERT.RSA",
    "note": "ANDROID DEBUG key - this build is developer-signed, not the release 'moojiang' key used by 2.23",
    "evidence": "PROVEN STATIC - pyaxmlparser/androguard get_certificates on the untouched APK",
}
CERT_408 = {
    "subject": "C=US, ST=California, L=Mountain View, O=Google Inc., OU=Android, CN=Android",
    "issuer": "C=US, ST=California, L=Mountain View, O=Google Inc., OU=Android, CN=Android",
    "serial": "AC945150B4978B64B1083CA763BF26A0998AF05A",
    "validity": "2026-01-15 -> 2056-01-15",
    "sha256_fingerprint": ":".join("F74543340EEE327463105E2AFBA8FBAC0C9CF5FDFEAD32FC9DF712AB09187B62"[i:i + 2] for i in range(0, 64, 2)),
    "sha1_fingerprint": ":".join("A0672685CF725D5ED91928172E62FC0F681FD01B"[i:i + 2] for i in range(0, 40, 2)),
    "v1_signature_file": None,
    "note": "Google Play App Signing certificate shape; base.apk carries NO v1 signature (v2/v3 block only). config.*.apk splits carry META-INF/BNDLTOOL.RSA (Gradle bundle tool).",
    "evidence": "PROVEN STATIC - androguard v2/v3 block on base.apk; reproduced independently by the prior 4.0.8 pass",
}

UUID_TABLE_COMMON = [
    {"uuid": "00000000-0000-1000-8000-00805f9b34fb", "role": "vendor service (matches by UUID equality; the vendor really advertises the all-zero service)",
     "evidence": "PROVEN STATIC - libapp.so string pool"},
    {"uuid": "0000ffe1-0000-1000-8000-00805f9b34fb", "role": "FFE1 - command write characteristic (write-without-response)", "evidence": "PROVEN STATIC"},
    {"uuid": "0000ffe2-0000-1000-8000-00805f9b34fb", "role": "FFE2 - notify/read characteristic (CCCD 01 00)", "evidence": "PROVEN STATIC"},
]
UUID_EXTRA_408 = [
    {"uuid": "0000180a-0000-1000-8000-00805f9b34fb", "role": "180A device information service", "evidence": "PROVEN STATIC"},
    {"uuid": "0000180f-0000-1000-8000-00805f9b34fb", "role": "180F battery service", "evidence": "PROVEN STATIC"},
    {"uuid": "00002a24-0000-1000-8000-00805f9b34fb", "role": "2A24 model number string", "evidence": "PROVEN STATIC"},
    {"uuid": "00002a26-0000-1000-8000-00805f9b34fb", "role": "2A26 firmware revision string", "evidence": "PROVEN STATIC"},
    {"uuid": "00002a19-0000-1000-8000-00805f9b34fb", "role": "2A19 battery level", "evidence": "PROVEN STATIC"},
    {"uuid": "00002902-0000-1000-8000-00805f9b34fb", "role": "2902 client characteristic configuration descriptor", "evidence": "PROVEN STATIC"},
    {"uuid": "0000f530-1212-efde-1523-785feabcd123", "role": "keyboard/doujiang family service", "evidence": "PROVEN STATIC"},
    {"uuid": "0000f531-1212-efde-1523-785feabcd123", "role": "keyboard/doujiang family characteristic", "evidence": "PROVEN STATIC"},
    {"uuid": "0000f532-1212-efde-1523-785feabcd123", "role": "keyboard/doujiang family characteristic", "evidence": "PROVEN STATIC"},
]

DEV_223 = [{"id": 0, "name": "devNone"}, {"id": 1, "name": "devRainbow"}, {"id": 2, "name": "devRainbowS"},
           {"id": 3, "name": "devRainbow2Pro"}, {"id": 4, "name": "devBLITZ_ULT"}, {"id": 5, "name": "devBLITZ_LITE"},
           {"id": 6, "name": "devArmorX"}]
DEV_224 = [{"id": 0, "name": "devNone"}, {"id": 1, "name": "devRainbow"}, {"id": 2, "name": "devRainbowS"},
           {"id": 3, "name": "devRainbow2Pro"}, {"id": 4, "name": "devRainbow2Lite"}, {"id": 5, "name": "devC2SL"},
           {"id": 6, "name": "devBLITZ_ULT"}, {"id": 7, "name": "devCHOCO"}, {"id": 8, "name": "devArmorX"}]
DEV_408 = [{"id": 0, "name": "devNone"}, {"id": 1, "name": "devRainbow"}, {"id": 2, "name": "devRainbowS"},
           {"id": 3, "name": "devRainbow2Pro"}, {"id": 4, "name": "devRainbow3"}, {"id": 5, "name": "devMSY"},
           {"id": 6, "name": "devRainbow2Lite"}, {"id": 7, "name": "devC2SL"}, {"id": 8, "name": "devBLITZ_ULT"},
           {"id": 9, "name": "devCHOCO"}, {"id": 10, "name": "devArmorX"}, {"id": 11, "name": "devGale2"},
           {"id": 12, "name": "devKeyboardDouJiangV1"}]
DEV_EV = "PROVEN STATIC - objs.txt enum objects (Obj!Device@<addr> off_8: int(N), off_10: \"devX\")"

HOSTS = {
    "api": "http://m.bigbigwon.com:8080",
    "oss": ["https://bigbig-won-cn.oss-cn-shanghai.aliyuncs.com", "https://bigbigwon-jp.oss-ap-northeast-1.aliyuncs.com",
            "https://bigwon-germany.oss-eu-central-1.aliyuncs.com", "https://bigwon-us.oss-us-west-1.aliyuncs.com"],
    "www": ["https://www.bigbigwon.com", "https://www.bigbigwon.cn"],
    "evidence": "PROVEN STATIC - libapp.so string pool (same API host in all three builds)",
}

BUILDS = {}

# ---------------------------------------------------------------- 2.23
BUILDS["2.23"] = {
    "build_key": "2.23", "label": "2.23.0609",
    "original_filename": "base.apk",
    "original_path": "/home/salamanka/armorx-lab/apk/original/2.23/base.apk",
    "size_bytes": 35958605,
    "sha256": "7ed18b774bf8beab0ff2ff11bc0669f4cacb9baa5cc309bf277752592a2bc892",
    "sha1": "f5fec9f48ab4ef52d22adf84f5c115970059ef21",
    "package": "com.moojiang.bigbigwon", "versionName": "2.23.0609", "versionCode": 12,
    "app_label": "BIGBIG WON",
    "min_sdk": 21, "target_sdk": 32, "compile_sdk": 33,
    "abi_set": ["arm64-v8a", "armeabi-v7a", "x86_64"],
    "split_structure": None,
    "split_structure_note": "single fat APK; no split manifest attribute; all three ABIs bundled in base.apk",
    "signing_certificate": CERT_223,
    "dart_version": "2.19.6 (stable) (Tue Mar 28 13:41:04 2023 +0000) on \"android_arm64\"",
    "dart_evidence": "PROVEN STATIC - libflutter.so strings (lib/arm64-v8a/libflutter.so)",
    "flutter_engine_hash": "adb4292f3ec25074ca70abcd2d5c7251",
    "flutter_engine_evidence": "PROVEN STATIC - libapp.so snapshot header (magic f5f5dcdc @0x200, feature string)",
    "flutter_version": "3.7.x", "flutter_version_evidence": "INFERRED - Flutter framework version not stored in the APK; inferred from Dart 2.19.6",
    "ble_library": "flutter_reactive_ble", "ble_library_evidence": "PROVEN STATIC - libapp.so strings: package:flutter_reactive_ble/**, package:reactive_ble_mobile/**",
    "server_hosts": HOSTS,
    "server_endpoints": ["/dev/register", "/dev/userLogin", "/dev/queryConfigList", "/dev/addConfig", "/dev/changeConfig",
                         "/dev/renameConfig", "/dev/delConfig", "/dev/shareConfig", "/dev/importShareConfig",
                         "/dev/queryMacroList", "/dev/addMacro", "/dev/changeMacro", "/dev/delMacro",
                         "/dev/queryDefaultConfig", "/dev/setConfig"],
    "device_enum": DEV_223, "armorx_enum_value": 6, "device_enum_evidence": DEV_EV,
    "ble_uuid_table": UUID_TABLE_COMMON,
    "ffe1_ffe2_usage": "FFE1 = write-without-response (all A5/A4/A8 frames), FFE2 = read+notify with CCCD 01 00 subscription; no AE00/AE01/AE02 literal in the build",
    "config_sizes": [88, 144, 240],
    "config_templates": [
        {"len": 88, "pp_off": "0x4b398", "sha256_prefix": "9eaea1d6a42c49a4", "stored_crc": "0x0000", "recomputed_crc": "0xC800"},
        {"len": 144, "pp_off": "0x4b3a0", "sha256_prefix": "1fa5afe2401d17c2", "stored_crc": "0x0000", "recomputed_crc": "0x848A", "family": "Rainbow-family default"},
        {"len": 144, "pp_off": "0x4b3b0", "sha256_prefix": "bc536085f138a2ed", "stored_crc": "0x0000", "recomputed_crc": "0x7F67", "family": "ARMOR-X Pro"},
        {"len": 240, "pp_off": "0x4b3a8", "sha256_prefix": "4baf590a1d3d48ad", "stored_crc": "0x1605", "recomputed_crc": "0x1605", "crc_self_valid": True}],
    "config_evidence": "PROVEN STATIC - pp.txt string literals `String: \"[...]\"` with declared length == total length",
    "config_crc": "CRC-16/MODBUS (init 0xFFFF, poly 0xA001) over bytes 2..end, stored big-endian at bytes 0..1; self-validating images prove it (240B/0x1605)",
    "config_length_rule": "checkConfigLength @0x810a34: len<240 -> len; else list.contains(-2)&&len==240 -> 240; else indexOf(-2). Static field 0xfd4 holds the derived length.",
    "opcode_inventory": {
        "byte_exact_proven_this_pass": {
            "0B": "getZKMVer - A5 04 0B B4 (@0x7617f4 armorx_pro_root, @0x800610 rainbow_root)",
            "D2": "testModeSwitch - A5 05 D2 01 ... (@0x8b1d68 rainbow_test)",
            "D4": "getInputModel - A5 04 D4 7D (@0x8afa98 rainbow_more)",
            "D6": "getDeviceConfig - A5 04 D6 7F (@0x810d2c rainbow_tab_config_1s, @0x8abc64 configs_config)",
            "FC": "DPI write - A5 05 FC <dpi&0x0F> <cks> (@0x7fdee4 writeDpiConfig)"},
        "verified_from_prior_artifacts_and_reconfirmed_by_builder_census": {
            "A5": "short-frame header", "A4": "long/data frame header (fragmentation)",
            "0E": "writeDevice - A5 05 0E 00 B8 (@0x7989bc) - post-write command from config workflows, no inbound parser",
            "D7": "writeDeviceConfig - A4/D7 fragments (@0x79e63c)",
            "D8": "macro write - A4/D8 fragments (@0x797fa0 writeMacroConfig)",
            "EF": "getDeviceUUID - A5 0C EF 00*8 A0 (@0x791a30 armorx_pro_root, @0x7ff67c rainbow_root)",
            "FF": "lighting - writeLightConfig emits A5 control + A4 data frames (@0x7f8158)",
            "10": "frame-length byte 16 observed in writeMacroConfig/writeDeviceConfig/writeLightConfig (NOT an opcode)",
            "70": "frame-length byte 112 observed in writeLightConfig (NOT an opcode)"},
        "absent_no_builder_constructs_it": ["E2", "E4", "F6", "F7", "F8", "D3", "E1", "DD", "AB", "25", "26", "70(as opcode)", "73", "F5", "0D", "04"],
        "absence_evidence": "Builder census over asm/moojiang with the A5/A4/AB-containing function filter: zero producing functions for these bytes (E2 -> no reachable construction path)"},
    "d6_d7_handling": {
        "D6_read": "A5 04 D6 7F; reply reassembled from A4/D6 fragments at offset (idx-1)*15; 144-byte image = 9x15 + 9 last fragment",
        "D7_write": "A4 fragments, 15-byte chunk (hard-coded `mov x, #0xf` / `add x25,x25,#0xf` in writeDeviceConfig @0x79e63c), 1-based index, A4 length byte = chunk+5, ack A5 05 D7 00 81",
        "fragment_chunk": 15, "fragment_chunk_evidence": "PROVEN STATIC - 15 is hard-coded; 2.23 has no subpackageLength() symbol (grep over asm/moojiang returns 0)"},
    "d8_macro": {
        "present": True,
        "implementation": "writeMacroConfig @0x797fa0 -> A4/D8 fragmentation + per-frame sum checksum; no transcribe_frame.dart and no frame_config_macros.dart in this build",
        "payload_reconstruction": "UNKNOWN for 2.23 - the byte-exact D8 payload layout (CRC-16 header, 10-byte step frames, 8 ms granularity) was reconstructed for 4.0.8; the equivalent per-field proof was not re-run on the 2.23 tree in this pass",
        "evidence": "PROVEN STATIC for opcode/presence; field layout STRONG EVIDENCE (same A4/D8 envelope as 2.24/4.0.8)"},
    "fc_f6_dpi": {
        "implementation": "A5 05 FC <dpi & 0x0F> <cks> - single opcode, NO legacy F6 branch, NO device gate (writeDpiConfig @0x7fdee4 stores #0x1f8 = 0xFC unconditionally)",
        "payload": "4-bit selector (and w,x,#0xf before store)", "evidence": "PROVEN STATIC"},
    "e2_presence": {"present": False,
                    "note": "no frame builder or response parser references 0xE2 anywhere in this build",
                    "evidence": "PROVEN STATIC (absence) - builder census + Smi-immediate scan over asm/moojiang"},
    "lighting": {"implementation": "writeLightConfig @0x7f8158 emits an A5 control frame and A4 data frames with opcode FF; colour lists framed as A4 fragments",
                 "evidence": "PROVEN STATIC (opcode/presence)"},
    "turbo": {"implementation": "config-resident: GamepadParam30.turboKey (String hex, field offset 0x54) serialised into the 144-byte parameter list; turbo speed is a separate static (byte 80 in 4.0.8's proven layout)",
              "byte_offsets": "UNKNOWN for 2.23 - the parameter index -> config byte mapping was proven byte-exact only for 4.0.8; not re-derived here",
              "evidence": "PROVEN STATIC for the field's existence/type/offset; STRONG EVIDENCE for config residency"},
    "key_id_table": {
        "summary": "key_remap_t.dart::gamePadKeyName map; label inventory verified from libapp.so strings + asm: A-Z, L3/R3/LB/RB/LT/RT, Select, Start, M1-M4, Alt/Ctrl/Shift/Space/Win/Print. NO Capture, NO Menu, NO M5/M6/M7.",
        "id_binding": "UNKNOWN - the numeric id -> label binding was not re-derived in this pass; the prior baseline's proven ids (0,1,2,3,4,6,7,8,9,10,11,13,14,16,17,18,19,23,24,25,26) transfer only as STRONG EVIDENCE because the enum is not guaranteed stable across builds",
        "evidence": "PROVEN STATIC for label set; UNKNOWN for the full numeric table"},
    "notable": ["fat APK with 3 ABIs (only 2.23 ships armeabi-v7a/x86_64)", "signed with the release 'moojiang' key"],
}

# ---------------------------------------------------------------- 2.24
BUILDS["2.24"] = {
    "build_key": "2.24", "label": "2.24.0919",
    "original_filename": "BIGBIGWON-2.24.0919.apk",
    "original_path": "/home/salamanka/armorx-lab/apk/original/2.24/BIGBIGWON-2.24.0919.apk",
    "size_bytes": 16087829,
    "sha256": "0bae884badc004991e638b0e62a0a6afc07256a5deabd8bb833f0bb36638f305",
    "sha1": "0a19b09d6a2c6feeb62f8946a9986589979f3c76",
    "package": "com.moojiang.bigbigwon", "versionName": "2.24.0919", "versionCode": 24,
    "app_label": "BIGBIG WON",
    "min_sdk": 21, "target_sdk": 34, "compile_sdk": 34,
    "abi_set": ["arm64-v8a"],
    "split_structure": None,
    "split_structure_note": "single APK, arm64-v8a only (armeabi-v7a/x86_64 dropped versus 2.23)",
    "signing_certificate": CERT_224,
    "dart_version": "3.2.3 (stable) (Tue Dec 5 17:58:33 2023 +0000) on \"android_arm64\"",
    "dart_evidence": "PROVEN STATIC - libflutter.so strings",
    "flutter_engine_hash": "f71c76320d35b65f1164dbaa6d95fe09",
    "flutter_engine_evidence": "PROVEN STATIC - libapp.so snapshot header (magic f5f5dcdc @0x200)",
    "flutter_version": "3.16.x", "flutter_version_evidence": "INFERRED - inferred from Dart 3.2.3",
    "ble_library": "flutter_reactive_ble", "ble_library_evidence": "PROVEN STATIC - libapp.so strings: package:flutter_reactive_ble/**, package:reactive_ble_mobile/**",
    "server_hosts": HOSTS,
    "server_endpoints": ["/dev/register", "/dev/userLogin", "/dev/queryConfigList", "/dev/addConfig", "/dev/changeConfig",
                         "/dev/renameConfig", "/dev/delConfig", "/dev/shareConfig", "/dev/importShareConfig",
                         "/dev/queryMacroList", "/dev/addMacro", "/dev/changeMacro", "/dev/delMacro",
                         "/dev/queryDefaultConfig", "/dev/setConfig", "/dev/queryGameList NEW"],
    "device_enum": DEV_224, "armorx_enum_value": 8, "device_enum_evidence": DEV_EV,
    "device_enum_correction": "the label for id 5 is devC2SL, not 'Blitz2' as an earlier research note claimed (objs.txt @9ef981)",
    "ble_uuid_table": UUID_TABLE_COMMON,
    "ffe1_ffe2_usage": "unchanged from 2.23; 180A/180F/2A24/2A26/2A19 literals ARE present as strings in this build",
    "config_sizes": [88, 144, 240, 280, 484],
    "config_templates": [
        {"len": 88, "pp_off": "0x4b510", "sha256_prefix": "9eaea1d6a42c49a4", "stored_crc": "0x0000", "recomputed_crc": "0xC800"},
        {"len": 144, "pp_off": "0x4b518", "sha256_prefix": "1fa5afe2401d17c2", "stored_crc": "0x0000", "recomputed_crc": "0x848A", "family": "Rainbow-family default"},
        {"len": 144, "pp_off": "0x4b540", "sha256_prefix": "bc536085f138a2ed", "stored_crc": "0x0000", "recomputed_crc": "0x7F67", "family": "ARMOR-X Pro"},
        {"len": 240, "pp_off": "0x4b528", "sha256_prefix": "a2dabf5bec6afe49", "stored_crc": "0x0000", "recomputed_crc": "0x6AC7"},
        {"len": 240, "pp_off": "0x4b530", "sha256_prefix": "96dd901075496924", "stored_crc": "0x1605", "recomputed_crc": "0xBC3A", "crc_self_valid": False, "note": "carried over from 2.23; its stored CRC no longer validates - recorded negative"},
        {"len": 240, "pp_off": "0x4b548", "sha256_prefix": "47c992112178bc82", "stored_crc": "0x198B", "recomputed_crc": "0x198B", "crc_self_valid": True},
        {"len": 280, "pp_off": "0x4b520", "sha256_prefix": "8f318f88caedb66b", "stored_crc": "0x0000", "recomputed_crc": "0x878D"},
        {"len": 484, "pp_off": "0x4b538", "sha256_prefix": "a61757a34cbdc20f", "stored_crc": "0xD0A4", "recomputed_crc": "0xD0A4", "crc_self_valid": True}],
    "config_evidence": "PROVEN STATIC - pp.txt string literals",
    "config_crc": "CRC-16/MODBUS over bytes 2..end (same rule; three images of this build self-validate)",
    "config_length_rule": "checkConfigLength unchanged; derived length static moved 0xfd8 -> 0x102c. Router (rainbow_tab_config_1s @0x8aa014): 0x58/0x90/0xF0 legacy, 0x118 -> ConfigsMain280Widget, else ConfigsMain484Widget.",
    "opcode_inventory": {
        "byte_exact_proven_this_pass": {
            "0B": "getZKMVer - A5 04 0B B4 (@0x78c208, @0x8975d4)",
            "D2": "testModeSwitch - A5 05 D2 01 (@0x91e380)",
            "D3": "getMaxSize - A5 04 D3 7C (@0x9157c0 frame_config_macros)",
            "D4": "getOnBoardConfig - A5 04 D4 (@0x91b988)",
            "D6": "getDeviceConfig - A5 04 D6 (@0x8a8798, @0x91433c)",
            "E1": "getConnectModel - A5 04 E1 8A (@0x91b7a8)",
            "E4": "getMTU - A5 04 E4 8D (@0x897724)",
            "F5": "getLogoColorConfig - A5 04 F5 (@0x91cc24)",
            "F6": "legacy DPI - A5 05 F6 00 A0 (@0x894000 writeDpiConfig fallback branch)",
            "F7": "getStepLength - A5 04 F7 A0 (@0x91af58)",
            "F8": "getBriCompConfig - A5 04 F8 (@0x91ae20)"},
        "also_present": ["A5", "A4", "0E (A5 05 0E 00 B8)", "D7 (A4/D7)", "D8 (A4/D8 macro)", "EF (A5 0C EF 00*8 A0)", "FC (DPI)", "FF (lighting)", "0D (writeLogoColorConfig - rainbow_tab_light)"],
        "absent_no_builder_constructs_it": ["E2", "AB", "25", "26", "DD", "70(as opcode)", "73", "04"],
        "absence_evidence": "builder census over asm/moojiang filtered to A5/A4/AB-containing functions"},
    "d6_d7_handling": {
        "D6_read": "A5 04 D6 7F; fragment reassembly in configs_mian (V280/V484), configs_config, configs_config_only_c1, rainbow_tab_config_1s",
        "D7_write": "A4 fragments; chunk = subpackageLength() - 5 where subpackageLength (define.dart @0x7b9064) = 20 for devArmorX (=> 15) and 48/72 for other devices (=> 43/67); 1-based index; A4 length = chunk+5; ack A5 05 D7 00 81",
        "fragment_chunk_armorx": 15,
        "fragment_chunk_evidence": "PROVEN STATIC - subpackageLength switch: devNone 48, devRainbow 20, devRainbowS 20, devRainbow2Pro 20, devRainbow2Lite 48, devC2SL 72, devBLITZ_ULT 48, devCHOCO 20, devArmorX 20"},
    "d8_macro": {
        "present": True,
        "implementation": "writeMacroConfig @0x7ffb5c -> A4/D8 fragmentation; transcribe_frame.dart and frame_config_macros.dart are NEW in this build (frame recording/replay); startTranscribe/stopTranscribe send 0B and FC",
        "payload_reconstruction": "the 4.0.8 pass records the 2.24 twin of TranscribeFrame.toFrameCmd at 0x800524 and _keyByte at 0x800b20 - same encoder as 4.0.8",
        "evidence": "PROVEN STATIC for presence/opcodes; STRONG EVIDENCE for the payload layout (same encoder shape)"},
    "fc_f6_dpi": {
        "implementation": "A5 05 FC <dpi&0x0F> <cks> by default; for curDevice in {devRainbow2Pro(3), devC2SL(5)} the builder overwrites element 2 with #0x1ec = 0xF6 when the zkmVersion static (0x102c, set from the 0B reply) is >= 0x35, and keeps FC when it is < 0x35 (writeDpiConfig @0x894000)",
        "payload": "4-bit selector (and w,x,#0xf)",
        "note": "an earlier note phrased this as 'fw < 0x35 -> F6'; the assembly at 0x8940f4 reads `cmp x1,#0x35; b.lt <skip F6 store>`, i.e. F6 is used when the version is >= 0x35",
        "evidence": "PROVEN STATIC"},
    "e2_presence": {"present": False, "note": "no builder or parser constructs 0xE2 in 2.24",
                    "evidence": "PROVEN STATIC (absence)"},
    "lighting": {"implementation": "writeLightConfig @0x88a5dc emits A5 + A4 frames with opcode FF; startTranscribe also uses FF",
                 "evidence": "PROVEN STATIC (opcode/presence)"},
    "turbo": {"implementation": "config-resident: GamepadParam30.turboKey (String hex, field offset 0x5c) + turboSpeedIdx; serialised via the hex-parse -> parameter index path (same shape as 4.0.8's proven idx 77..80 = bytes 81..84)",
              "byte_offsets": "UNKNOWN for 2.24 - not re-derived byte-exact in this pass",
              "evidence": "PROVEN STATIC for the field's existence/type/offset; STRONG EVIDENCE for config residency"},
    "key_id_table": {
        "summary": "label inventory grew versus 2.23: adds Capture, Tab/Esc/Enter/End/F1-F12, arrow names. Still no Menu, no M5/M6/M7.",
        "id_binding": "UNKNOWN - numeric binding not re-derived in this pass",
        "evidence": "PROVEN STATIC for label set; UNKNOWN for the full numeric table"},
    "notable": ["dev-signed with the ANDROID DEBUG key", "first build with 280/484 config families and transcribe (macro recording)",
                "arm64-v8a only"],
}

# ---------------------------------------------------------------- 4.0.8
BUILDS["4.0.8"] = {
    "build_key": "4.0.8", "label": "4.0.8",
    "original_filename": "BIGBIGWON-4.0.8.apkm",
    "original_path": "/home/salamanka/armorx-lab/apk/original/4.0.8/BIGBIGWON-4.0.8.apkm",
    "companion_original": {"path": "/home/salamanka/armorx-lab/apk/original/4.0.8/base.apk",
                           "note": "byte-identical to the base split inside the APKM",
                           "sha256": "64e0832b1f97d995b40bf994465c277340e96a4f2b6b2fc5ef1eb4e2af9378e2"},
    "size_bytes": 36492532,
    "sha256": "474f66094ebbea8b0242257bbb23fc6b1baa7e54c10f13beb2cd4da14ce73abf",
    "sha1": "6cd397b2b0c9cfa54adbbe3dfc89e19110a3a583",
    "package": "com.moojiang.bigbigwon.mygt", "versionName": "4.0.8", "versionCode": 409,
    "app_label": "BIGBIG WON",
    "min_sdk": 24, "target_sdk": 36, "compile_sdk": 36,
    "abi_set": ["arm64-v8a"],
    "split_structure": {
        "container": "APKM (zip of splits)",
        "splits": [
            {"name": "base.apk", "size": 32854837, "sha256": "64e0832b1f97d995b40bf994465c277340e96a4f2b6b2fc5ef1eb4e2af9378e2",
             "manifest_attrs": 'android:splitTypes="" android:requiredSplitTypes="base__abi,base__density"',
             "contains": "classes.dex + classes2.dex + classes3.dex, resources.arsc, assets/flutter_assets/**, assets/dexopt/**, NO lib/"},
            {"name": "config.arm64_v8a.apk", "size": 11027091, "sha256": "2e9805fc20b0ec88b62c5d107f0c1634a27f47469d63c79c90b842f9f15bd1fb",
             "manifest_attrs": 'split="config.arm64_v8a" android:splitTypes="base__abi"',
             "contains": "lib/arm64-v8a/{libapp.so, libflutter.so, libBugly_Native.so, libdatastore_shared_counter.so}"},
            {"name": "config.en.apk", "size": 41369, "sha256": "00df4a3b837f2e5c067279e65242917e797fa5fa7e9e58905f93e5373a89b959",
             "manifest_attrs": 'split="config.en" android:splitTypes=""'},
            {"name": "config.ar.apk", "size": 20889, "sha256": "172052b2b749db30c5fbfaae36dcbbb5e7e1e393fdd26ece8ab1fd74b9e6d78e",
             "manifest_attrs": 'split="config.ar" android:splitTypes=""'},
            {"name": "config.xxhdpi.apk", "size": 88260, "sha256": "a1998122b37e9edb5271a048a8a433bfadcd8dbfad09da19ad9891e74e7e74a8",
             "manifest_attrs": 'split="config.xxhdpi" android:splitTypes="base__density"'}],
        "note": "the base split carries NO native library; the Dart snapshot lives in the ABI split",
        "evidence": "PROVEN STATIC - unzip listing + androguard on every split's AndroidManifest.xml"},
    "signing_certificate": CERT_408,
    "dart_version": "3.12.2 (stable) (Tue Jun 9 01:11:39 2026 -0700) on \"android_arm64\"",
    "dart_evidence": "PROVEN STATIC - libflutter.so strings (of the ABI split)",
    "flutter_engine_hash": "ace654289f5abc240509fc941453ebc5",
    "flutter_engine_evidence": "PROVEN STATIC - libapp.so snapshot header (magic f5f5dcdc @0x340; the base split has no libapp.so)",
    "flutter_version": "UNKNOWN", "flutter_version_evidence": "UNKNOWN - no Flutter framework version string is stored in the bundle; the Dart runtime is 3.12.2",
    "ble_library": "flutter_blue_plus", "ble_library_evidence": "PROVEN STATIC - libapp.so strings: package:flutter_blue_plus/**, flutter_blue_plus_android/**, flutter_blue_plus_platform_interface/**; zero hits for flutter_reactive_ble",
    "server_hosts": HOSTS,
    "server_endpoints": ["/dev/register", "/dev/userLogin", "/dev/queryConfigList", "/dev/addConfig", "/dev/changeConfig",
                         "/dev/renameConfig", "/dev/delConfig", "/dev/shareConfig", "/dev/importShareConfig",
                         "/dev/queryMacroList", "/dev/addMacro", "/dev/changeMacro", "/dev/delMacro", "/dev/setConfig",
                         "REMOVED vs 2.24: /dev/queryDefaultConfig, /dev/queryGameList"],
    "device_enum": DEV_408, "armorx_enum_value": 10, "device_enum_evidence": DEV_EV,
    "ble_uuid_table": UUID_TABLE_COMMON + UUID_EXTRA_408,
    "ffe1_ffe2_usage": "FFE1 write-without-response / FFE2 notify, unchanged; the F5xx keyboard family service/characteristics are new in this build; still no FFE0 and no AE00/AE01/AE02",
    "config_sizes": [88, 144, 240, 280, 335, 456, 484, 508],
    "config_templates": [
        {"len": 88, "pp_off": "0x58700", "sha256_prefix": "9eaea1d6a42c49a4", "stored_crc": "0x0000", "recomputed_crc": "0xC800"},
        {"len": 144, "pp_off": "0x58708", "sha256_prefix": "1fa5afe2401d17c2", "stored_crc": "0x0000", "recomputed_crc": "0x848A"},
        {"len": 144, "pp_off": "0x58738", "sha256_prefix": "bc536085f138a2ed", "stored_crc": "0x0000", "recomputed_crc": "0x7F67", "family": "ARMOR-X Pro"},
        {"len": 240, "pp_off": "0x58720", "sha256_prefix": "a2dabf5bec6afe49", "stored_crc": "0x0000", "recomputed_crc": "0x6AC7"},
        {"len": 240, "pp_off": "0x58728", "sha256_prefix": "96dd901075496924", "stored_crc": "0x1605", "recomputed_crc": "0xBC3A", "crc_self_valid": False},
        {"len": 240, "pp_off": "0x58740", "sha256_prefix": "47c992112178bc82", "stored_crc": "0x198B", "recomputed_crc": "0x198B", "crc_self_valid": True},
        {"len": 280, "pp_off": "0x58718", "sha256_prefix": "46cb64522b4831b7", "stored_crc": "0x0000", "recomputed_crc": "0x0F1B"},
        {"len": 280, "pp_off": "0x58758", "sha256_prefix": "8f318f88caedb66b", "stored_crc": "0x0000", "recomputed_crc": "0x878D"},
        {"len": 335, "pp_off": "0x58750", "sha256_prefix": "3d79ec00bc56d7f5", "stored_crc": "0x727F", "recomputed_crc": "0x727F", "crc_self_valid": True},
        {"len": 456, "pp_off": "0x58748", "sha256_prefix": "1034629b4cf19310", "stored_crc": "0x3E21", "recomputed_crc": "0x3E21", "crc_self_valid": True},
        {"len": 484, "pp_off": "0x58730", "sha256_prefix": "a61757a34cbdc20f", "stored_crc": "0xD0A4", "recomputed_crc": "0xD0A4", "crc_self_valid": True},
        {"len": 508, "pp_off": "0x58710", "sha256_prefix": "4da4c0bb2aeb8f88", "stored_crc": "0x3722", "recomputed_crc": "0x3722", "crc_self_valid": True}],
    "config_evidence": "PROVEN STATIC - pp.txt string literals (12 unique images)",
    "config_crc": "CRC-16/MODBUS over bytes 2..end; six images (240/335/456/484/508) self-validate -> device-wide rule, not a 144-byte special case",
    "config_length_rule": "checkConfigLength @0x82e648 + defaultConfig() branches on the current length for devArmorX (0x90 -> 144, 0xF0 -> 240): the device type alone does not fix the length",
    "opcode_inventory": {
        "byte_exact_proven_this_pass": {
            "0B": "getZKMVer - A5 04 0B B4 (@0x8b61fc bluetooth_mode, @0x8b6ce4 armorx_pro_root)",
            "D2": "testModeSwitch - A5 05 D2 01 (@0xabaef4)",
            "D3": "getMaxSize - A5 04 D3 7C (@0xac313c)",
            "D4": "getInputModel - A5 04 D4 7D (@0xa84258)",
            "D6": "getDeviceConfig - A5 04 D6 7F (@0x80dbfc)",
            "DD": "getChargingLightEffect - A5 04 DD 86 (@0xace808)",
            "E1": "getConnectModel - A5 04 E1 8A (@0xabd35c)",
            "E2": "readFirmware - A5 04 E2 8B (@0x8b6860)  <-- PRESENT (absent in 2.23/2.24)",
            "E4": "getMTU - A5 04 E4 8D (@0x8b60f0)",
            "F5": "getLogoColorConfig - A5 04 F5 9E (@0xa84a40)",
            "F6": "legacy DPI - A5 05 F6 00 A0 (@0x946750 fallback branch)",
            "F7": "getStepLength - A5 04 F7 A0 (@0x8b4d30)",
            "F8": "getBriCompConfig - A5 04 F8 (@0x8b4c24)",
            "FC": "DPI write - A5 05 FC <dpi&0x0F> <cks> (@0x946750)",
            "73": "light enable state - A5 05 73 00/01 (@0x848ae0 setLightEnable, @0x9f4e74 setLightEnabled)",
            "04": "getBattery - A5 04 04 AD (@0x8b672c)"},
        "from_the_prior_verified_command_index": {
            "70": "lighting config R3 - A5 04 70 (writeApplyLightR3Common @0x844824), A5 10 70 ... over A4 (writeLightConfigR3 @0x844e04), main writeLightConfig @0x84938c",
            "AB": "motion/gyro frames - header 0xAB (writeMotionDpiConfig @0x946158 AB 07 05 25 <lo> <hi> <cks>; getMotionList/getMotionDpi)",
            "25/26": "motion sub-commands under the AB header", "1A": "reset", "1B": "start/stopCalibration",
            "0E": "writeDevice", "A4/A5": "frame headers", "D7": "writeDeviceConfig (A4/D7)", "D8": "macro (A4/D8)",
            "EF": "getDeviceUUID", "A9": "doujiang keyboard empty packet"},
        "absent_no_builder_constructs_it": ["FFE1-family legacy opcodes f6-as-normal-path (kept only as a fw-gated fallback)"],
        "absence_evidence": "builder census + the prior byte-exact command index (command-index.json)"},
    "d6_d7_handling": {
        "D6_read": "A5 04 D6 7F; reassembly by the generic config page state machines (dispatch on A4/A5/D6/D7/DA in configs_mian V280/V484, configs_config); ARMOR-X Pro root screen does NOT issue D6 itself",
        "D7_write": "A4 fragments; chunk = subpackageLength() - 5 (define.dart @0x819190); 1-based index; A4 length = chunk+5; ack A5 05 D7 00 81",
        "fragment_chunk_armorx": 15,
        "fragment_chunk_evidence": "PROVEN STATIC - subpackageLength returns 48/20/20/... per device; 20 - 5 = 15 for ARMOR-X Pro"},
    "d8_macro": {
        "present": True,
        "implementation": "applicationFrameMacro() @0x85c8c0 builds the whole D8 buffer (header + 10-byte step frames + CRC-16) then writeMacroConfig @0x85a670 does A4/D8 fragmentation + checksum + BLE write + 4 ms inter-frame delay + commit frame; TranscribeFrame.toFrameCmd/_keyByte/_stickByte serialise each step",
        "payload_layout": "N = 10 + 10 x frames; [0..1] CRC-16/MODBUS over [2..N-1] big-endian; [2..3] length BE; [4]=0; [5]=trigger key; [6]=runKey; [7]=isRepeat; [8..9]=repeatTime BE; then 10-byte step frames: [0]=((ms/8)&0x0F)<<4, [1]=(ms/8)>>4, [2..5]=key bitmask BE, [6..9]=stick pattern BE; 8 ms granularity, 12-bit -> max 32760 ms; chords = multiple bits in one frame; disable = all-zero 10-byte frame; terminator frame A4 0A D8 <nfrags+1> <sum8>",
        "evidence": "PROVEN STATIC (encode side; readback offsets still unlocated)"},
    "fc_f6_dpi": {
        "implementation": "A5 05 FC <dpi&0x0F> <cks> by default; for curDevice in {devRainbow2Pro(3), devRainbow3(4), devGale2(11), devC2SL(7)} the builder overwrites element 2 with #0x1ec = 0xF6 when the version static (0xb6c, set from the 0B reply) is >= 0x35 (writeDpiConfig @0x946750). Motion/gyro DPI is a separate AB 07 05 25 <u16 LE> <cks> frame (writeMotionDpiConfig @0x946158).",
        "payload": "normal DPI = 4-bit selector; motion DPI = 16-bit little-endian",
        "evidence": "PROVEN STATIC"},
    "e2_presence": {"present": True,
                    "implementation": "BluetoothModel::readFirmware @0x8b6860 builds the byte-exact frame A5 04 E2 8B (A5 @0x9467b8-style stores, opcode Smi #0x1c4). No E2 branch found in the ARMOR-X Pro dispatcher closure in this build.",
                    "evidence": "PROVEN STATIC"},
    "lighting": {"implementation": "writeLightConfig @0x84938c emits A5 control + A4 data frames (opcode FF, sub-command 05, count/mask 3F); writeLightConfigR3 @0x844e04 = A5 10 70 <5 payload>; writeApplyLightR3Common @0x844824 = A5 04 70; LED sets travel as bitmasks via encodeLedIdBit/lightIdsToMask; charging-light effect DD; brightness compensation F8; light enable 73; logo colour F5; R3 colour triple (LightColorRainBow3::toList)",
                 "evidence": "PROVEN STATIC (opcodes/presence)"},
    "turbo": {"implementation": "config-resident, no per-write turbo frame: config byte 80 = turbo speed index (from global static 0xb60 -> parameter idx 76), bytes 81..84 = turboKey u32 BIG-ENDIAN (GamepadParam30.turboKey, hex string, field offset 0x5c; split MSB-first into parameter indices 77,78,79,80)",
              "default": "the embedded ARMOR-X Pro 144 image ships bytes 80..84 = 00 00 00 00 00 (turbo off)",
              "correction": "sendAllTurboKeySpeed and writeTurboClick DO exist in this bundle, but only inside the keyboard/doujiang subsystem (widgets/kb_doujiang/util/hitbox_key_sender_manager.dart @0x9d15e4 / @0x9d52e0). The earlier note 'a grep over the whole asm tree finds neither symbol' is wrong. Neither is used by the gamepad turbo path, so the config-resident model stands.",
              "evidence": "PROVEN STATIC"},
    "key_id_table": {
        "summary": "mapKeys occupies config bytes 112..143 (32 slots). Independent re-extraction of key_remap_t.dart::gamePadKeyName @0x92d69c in this pass reproduced the prior table exactly: 0:A 1:B 3:X 4:Y 6:LB 7:RB 8:LT 9:RT 10:Select 11:Start 13:L3 14:R3 15:Capture 16:up 17:down 18:left 19:right 22:Menu 23:M1 24:M2 25:M3 26:M4 27:M5 28:M6 29:M7; ids 2,5,12,20,21,30,31,32,33 carry no label in the build; macro pseudo-keys 34..49 exist separately",
        "id_binding": "PROVEN STATIC (re-verified against key-id-table.md)",
        "evidence": "PROVEN STATIC"},
    "notable": ["Google Play App Signing certificate", "PairIP-wrapped Java shell (com.pairip.application.Application)",
                "package id renamed to com.moojiang.bigbigwon.mygt", "arm64-v8a only, split bundle",
                "Dart namespace still package:moojiang/"],
}

# ---- write per-build manifests
for k, v in BUILDS.items():
    v["manifest_version"] = 1
    v["generated_from"] = "local originals under /home/salamanka/armorx-lab/apk/original/ (no download)"
    with open(os.path.join(OUT, k + ".json"), "w") as f:
        json.dump(v, f, indent=1)
    print("wrote", os.path.join(OUT, k + ".json"))

# ---- version matrix
matrix = {
    "version": 1,
    "generated": "from the three local originals; every row carries file+offset evidence and an evidence label",
    "builds": ["2.23", "2.24", "4.0.8"],
    "rows": [
        {"field": "original filename", "2.23": "base.apk", "2.24": "BIGBIGWON-2.24.0919.apk", "4.0.8": "BIGBIGWON-4.0.8.apkm (+ base.apk)",
         "class": "behaviour changed", "evidence": "file listing", "label": "PROVEN STATIC"},
        {"field": "sha256", "2.23": "7ed18b77…c892", "2.24": "0bae884b…f305", "4.0.8": "474f6609…3abf", "class": "unchanged",
         "evidence": "sha256sum of the untouched originals", "label": "PROVEN STATIC"},
        {"field": "package name", "2.23": "com.moojiang.bigbigwon", "2.24": "com.moojiang.bigbigwon", "4.0.8": "com.moojiang.bigbigwon.mygt",
         "class": "renamed-restructured", "evidence": "AndroidManifest.xml package= (2.23 base.apk offset 0xb54 chunk; 4.0.8 base split)", "label": "PROVEN STATIC"},
        {"field": "versionName / versionCode", "2.23": "2.23.0609 / 12", "2.24": "2.24.0919 / 24", "4.0.8": "4.0.8 / 409",
         "class": "expanded", "evidence": "manifest attrs", "label": "PROVEN STATIC"},
        {"field": "signing certificate", "2.23": "CN=moojiang (release key) 5472…78C", "2.24": "CN=Android Debug 44C3…541", "4.0.8": "Google App Signing F745…B62",
         "class": "behaviour changed", "evidence": "v1 CERT.RSA (2.23/2.24) and v2/v3 signing block (4.0.8)", "label": "PROVEN STATIC"},
        {"field": "minSdk", "2.23": 21, "2.24": 21, "4.0.8": 24, "class": "behaviour changed", "evidence": "uses-sdk minSdkVersion", "label": "PROVEN STATIC"},
        {"field": "targetSdk", "2.23": 32, "2.24": 34, "4.0.8": 36, "class": "expanded", "evidence": "uses-sdk targetSdkVersion", "label": "PROVEN STATIC"},
        {"field": "ABI set", "2.23": "arm64-v8a, armeabi-v7a, x86_64", "2.24": "arm64-v8a", "4.0.8": "arm64-v8a (ABI split)",
         "class": "removed", "evidence": "lib/ entries per APK", "label": "PROVEN STATIC"},
        {"field": "split-APK structure", "2.23": "none (fat APK)", "2.24": "none", "4.0.8": "APKM: base + config.arm64_v8a + config.en + config.ar + config.xxhdpi",
         "class": "expanded", "evidence": "APKM listing + each split's AndroidManifest split=/splitTypes= attrs", "label": "PROVEN STATIC"},
        {"field": "Dart runtime", "2.23": "2.19.6", "2.24": "3.2.3", "4.0.8": "3.12.2",
         "class": "expanded", "evidence": "libflutter.so version banner string", "label": "PROVEN STATIC"},
        {"field": "Flutter framework", "2.23": "3.7.x", "2.24": "3.16.x", "4.0.8": "UNKNOWN",
         "class": "unknown", "evidence": "not stored in the bundle; 4.0.8 in particular has no version string", "label": "INFERRED"},
        {"field": "BLE library", "2.23": "flutter_reactive_ble", "2.24": "flutter_reactive_ble", "4.0.8": "flutter_blue_plus",
         "class": "behaviour changed", "evidence": "libapp.so string pool package paths", "label": "PROVEN STATIC"},
        {"field": "server host", "2.23": "m.bigbigwon.com:8080", "2.24": "m.bigbigwon.com:8080", "4.0.8": "m.bigbigwon.com:8080",
         "class": "unchanged", "evidence": "libapp.so string pool", "label": "PROVEN STATIC"},
        {"field": "server endpoints", "2.23": "15 (…queryDefaultConfig, setConfig)",
         "2.24": "16 (+queryGameList)", "4.0.8": "14 (-queryDefaultConfig, -queryGameList)",
         "class": "removed", "evidence": "string pool /dev/* literals", "label": "PROVEN STATIC"},
        {"field": "ARMOR-X Pro device enum", "2.23": 6, "2.24": 8, "4.0.8": 10,
         "class": "renamed-restructured", "evidence": "objs.txt Obj!Device@90e4a1 / @9ef961 / @b2eec1 off_8", "label": "PROVEN STATIC"},
        {"field": "device enum size", "2.23": 7, "2.24": 9, "4.0.8": 13,
         "class": "expanded", "evidence": "objs.txt enum object count", "label": "PROVEN STATIC"},
        {"field": "vendor service / FFE1 / FFE2", "2.23": "00000000-… / FFE1 write / FFE2 notify",
         "2.24": "same", "4.0.8": "same (+180A,180F,2A24,2A26,2A19,2902,F530-F532)",
         "class": "expanded", "evidence": "libapp.so UUID literals", "label": "PROVEN STATIC"},
        {"field": "config families (bytes)", "2.23": "88/144/240 (4 templates)", "2.24": "88/144/240/280/484 (8 templates)",
         "4.0.8": "88/144/240/280/335/456/484/508 (12 templates)",
         "class": "expanded", "evidence": "pp.txt default-config string literals, declared length == total length", "label": "PROVEN STATIC"},
        {"field": "ARMOR-X Pro config length", "2.23": 144, "2.24": 144, "4.0.8": "144 (or 240 - negotiated via defaultConfig)",
         "class": "behaviour changed", "evidence": "bc536085 template present in all three; 4.0.8 defaultConfig branches 0x90->144, 0xF0->240", "label": "PROVEN STATIC"},
        {"field": "config CRC rule", "2.23": "CRC-16/MODBUS over 2..end", "2.24": "same (3 images self-validate)", "4.0.8": "same (6 images self-validate)",
         "class": "expanded", "evidence": "recomputed CRC == stored CRC on the embedded images", "label": "PROVEN STATIC"},
        {"field": "config length static field", "2.23": "0xfd4", "2.24": "0x102c", "4.0.8": "0xb6c",
         "class": "renamed-restructured", "evidence": "StoreStaticField in the 0B reply handler", "label": "PROVEN STATIC"},
        {"field": "opcode inventory (proven builders)", "2.23": "0B,0E,EF,D2,D4,D6,D7,D8,FC,FF (+A4/A5)",
         "2.24": "+D3,E1,E4,F6,F7,F8,F5,0D", "4.0.8": "+E2,DD,70,73,04,AB(05/25,05/26),1A,1B",
         "class": "expanded", "evidence": "frame-builder census + byte-exact reconstruction over each asm tree", "label": "PROVEN STATIC"},
        {"field": "E2 readFirmware", "2.23": "absent", "2.24": "absent", "4.0.8": "A5 04 E2 8B (@0x8b6860)",
         "class": "expanded", "evidence": "no builder/parser constructs 0xE2 in 2.23/2.24; 4.0.8 readFirmware builds it", "label": "PROVEN STATIC"},
        {"field": "D6 read / D7 write", "2.23": "A5 04 D6 7F / A4 fragments, hard-coded 15-byte chunk",
         "2.24": "same / chunk = subpackageLength()-5 (=15 for ARMOR-X Pro)",
         "4.0.8": "same / chunk = subpackageLength()-5 (=15)",
         "class": "behaviour changed", "evidence": "writeDeviceConfig bodies; subpackageLength switch in define.dart", "label": "PROVEN STATIC"},
        {"field": "D8 macro", "2.23": "present: A4/D8 fragmentation (writeMacroConfig @0x797fa0); no transcribe_frame.dart",
         "2.24": "present + frame recording (transcribe_frame.dart, frame_config_macros.dart new)",
         "4.0.8": "present, payload reconstructed byte-exact (10+10N, CRC-16, 8 ms granularity)",
         "class": "expanded", "evidence": "writeMacroConfig bodies / d8-macro reconstruction", "label": "PROVEN STATIC (2.24/4.0.8); payload layout UNKNOWN for 2.23"},
        {"field": "FC/F6 DPI", "2.23": "A5 05 FC <sel&0x0F>, no F6 branch, no device gate",
         "2.24": "FC default; F6 for {devRainbow2Pro, devC2SL} when static 0x102c >= 0x35",
         "4.0.8": "FC default; F6 for {devRainbow2Pro, devRainbow3, devGale2, devC2SL} when static 0xb6c >= 0x35; motion DPI = AB 07 05 25 <u16 LE>",
         "class": "expanded", "evidence": "writeDpiConfig bodies; `cmp x1,#0x35; b.lt <skip F6 store>`", "label": "PROVEN STATIC"},
        {"field": "lighting", "2.23": "writeLightConfig -> A5 + A4/FF", "2.24": "same (+0D writeLogoColorConfig)",
         "4.0.8": "A5 04 70 / A5 10 70 R3, main writeLightConfig FF+05+3F, additional DD/F8/73/F5",
         "class": "expanded", "evidence": "light config builder census", "label": "PROVEN STATIC"},
        {"field": "turbo", "2.23": "config-resident (GamepadParam30.turboKey @0x54)",
         "2.24": "config-resident (@0x5c)", "4.0.8": "config-resident, byte 80 = speed idx, bytes 81..84 = turboKey u32 BE",
         "class": "unchanged", "evidence": "turboKey field + hex-parse serialisation; 4.0.8 offsets proven byte-exact", "label": "PROVEN STATIC (4.0.8); byte offsets UNKNOWN for 2.23/2.24"},
        {"field": "key-ID table", "2.23": "labels up to M4; no Capture/Menu/M5-M7",
         "2.24": "+Capture, keyboard labels", "4.0.8": "+Menu, M5/M6/M7; full 0..49 id table (re-verified)",
         "class": "expanded", "evidence": "key_remap_t.dart::gamePadKeyName + string pool", "label": "PROVEN STATIC (4.0.8); label sets only (numeric binding UNKNOWN) for 2.23/2.24"},
        {"field": "device enum id 5 label (2.24)", "2.23": "devBLITZ_LITE", "2.24": "devC2SL (NOT 'Blitz2')", "4.0.8": "devMSY (different namespace position)",
         "class": "behaviour changed", "evidence": "objs.txt @9ef981", "label": "PROVEN STATIC"},
        {"field": "queryDefaultConfig / queryGameList endpoints", "2.23": "both present", "2.24": "both present", "4.0.8": "both removed",
         "class": "removed", "evidence": "string pool /dev/* literals", "label": "PROVEN STATIC"},
        {"field": "transcribe / frame_config_macros modules", "2.23": "absent", "2.24": "present", "4.0.8": "present",
         "class": "expanded", "evidence": "asm/moojiang/units/transcribe_frame.dart, widgets/general/frame_config_macros.dart", "label": "PROVEN STATIC"},
        {"field": "280/484 serializer modules", "2.23": "absent", "2.24": "present (gamepadset280/484, base_gamepadset)", "4.0.8": "present",
         "class": "expanded", "evidence": "asm/moojiang/units listing", "label": "PROVEN STATIC"},
    ],
}
with open(os.path.join(OUT, "version-matrix.json"), "w") as f:
    json.dump(matrix, f, indent=1)

# ---- results/version-diff
with open(os.path.join(RES, "static-version-matrix.json"), "w") as f:
    json.dump(matrix, f, indent=1)

lines = []
lines.append("# Static APK version matrix - BIGBIG WON 2.23.0609 / 2.24.0919 / 4.0.8")
lines.append("")
lines.append("Built from the three **local originals** only (no download). Every row carries evidence")
lines.append("(binary / AOT-asm location) and one label: PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN.")
lines.append("")
lines.append("Extracted trees: `/home/salamanka/armorx-lab/apk/extracted/{2.23,2.24,4.0.8}/`.")
lines.append("Per-build manifests: `/home/salamanka/armorx-lab/apk/manifests/{2.23,2.24,4.0.8}.json`.")
lines.append("")
lines.append("## A. Identity, packaging, signing")
lines.append("")
lines.append("| field | 2.23.0609 | 2.24.0919 | 4.0.8 | class | evidence | label |")
lines.append("|---|---|---|---|---|---|---|")
def cell(x):
    if isinstance(x, (list, dict)):
        return ", ".join(map(str, x)) if isinstance(x, list) else json.dumps(x)
    return str(x)
order_a = ["original filename", "sha256", "package name", "versionName / versionCode", "signing certificate",
           "minSdk", "targetSdk", "ABI set", "split-APK structure"]
order_b = ["Dart runtime", "Flutter framework", "BLE library", "server host", "server endpoints",
           "ARMOR-X Pro device enum", "device enum size", "vendor service / FFE1 / FFE2",
           "config families (bytes)", "ARMOR-X Pro config length", "config CRC rule", "config length static field",
           "opcode inventory (proven builders)", "E2 readFirmware", "D6 read / D7 write", "D8 macro", "FC/F6 DPI",
           "lighting", "turbo", "key-ID table", "device enum id 5 label (2.24)",
           "queryDefaultConfig / queryGameList endpoints", "transcribe / frame_config_macros modules",
           "280/484 serializer modules"]
for key, title in (("A. Identity, packaging, signing", order_a), ("B. Runtime, protocol, config", order_b)):
    if key.startswith("B"):
        lines.append("")
        lines.append("## B. Runtime, transport, protocol and config")
        lines.append("")
        lines.append("| field | 2.23.0609 | 2.24.0919 | 4.0.8 | class | evidence | label |")
        lines.append("|---|---|---|---|---|---|---|")
    for r in matrix["rows"]:
        if r["field"] not in title:
            continue
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (
            r["field"], cell(r["2.23"]), cell(r["2.24"]), cell(r["4.0.8"]), r["class"], r["evidence"], r["label"]))
lines.append("")
lines.append("## C. Evidence anchors used in this pass")
lines.append("")
lines.append("| anchor | what it proves |")
lines.append("|---|---|")
lines.append("| `unzip -l` on the originals | split layout, member hashes |")
lines.append("| pyaxmlparser + androguard on each AndroidManifest | package / versionName / versionCode / minSdk / targetSdk / split attrs / signer |")
lines.append("| `strings` on `lib/<abi>/libapp.so` | BLE library, UUIDs, hosts, endpoints, device labels |")
lines.append("| libflutter.so version banner | Dart runtime version |")
lines.append("| libapp.so snapshot header (`f5 f5 dc dc` + engine hash) | Flutter engine hash |")
lines.append("| `objs.txt` (`Obj!Device@<addr>` `off_8`/`off_10`) | device enum ids and names |")
lines.append("| `pp.txt` config string literals | config families, template hashes, stored vs recomputed CRC |")
lines.append("| frame-builder census over `asm/moojiang` | which opcodes are constructed, and which are absent |")
lines.append("| `reconstruct_frames.py` register-map extraction | byte-exact frames (checksums match the live-proven ones) |")
with open(os.path.join(RES, "static-version-matrix.md"), "w") as f:
    f.write("\n".join(lines) + "\n")

print("wrote matrix + report")
