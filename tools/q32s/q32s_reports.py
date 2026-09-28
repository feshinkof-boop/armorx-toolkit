#!/usr/bin/env python3
"""q32s_reports.py - generate the q32s / firmware symbol-map deliverables.

Every measured number in the output is read from the recorded artifacts in results/q32s/ and
results/firmware/; nothing is transcribed by hand. The symbol map itself is the analysis
conclusion, and each entry carries its own confidence grade and the evidence behind it.

Outputs:
  results/final/q32s-reverse-engineering.md
  results/final/armorx-firmware-symbol-map.md
  results/q32s/q32s-isa.json
  results/q32s/q32s-symbol-map.json
"""
from __future__ import annotations

import json
import pathlib

REPO = pathlib.Path("/home/salamanka/armorx-lab")
Q = REPO / "results" / "q32s"
F = REPO / "results" / "firmware"
FIN = REPO / "results" / "final"

# ---------------------------------------------------------------- symbol map data
# grade: PROVEN STATIC  = address and role fixed by code structure (dispatch compare, error
#                         printer call, unique string reference)
#        STRONG EVIDENCE = role follows from several independent strings/behaviour
#        INFERRED        = consistent with evidence, not otherwise confirmed
SYMBOLS = [
    # (address, name, category, grade, evidence)
    (0x01E00120, "armorx_entry_point", "entry/startup", "PROVEN STATIC",
     "JLFS app directory entry-point field for the V41 body image"),
    (0x01E00000, "fw_start", "entry/startup", "PROVEN STATIC",
     "image load base; startup stub clears BSS and copies .data (verified by disassembly)"),
    (0x01E08772, "armorx_cmd_dispatch", "command dispatcher", "PROVEN STATIC",
     "compares the frame opcode against D2/D4/D7/F7/F8/F9/FA/FF and calls the frame "
     "head/length/checksum error printers"),
    (0x01E0701C, "frame_err_head", "protocol parser", "PROVEN STATIC",
     "unique reference to '...cmd head err %x %x'; called from the frame handler"),
    (0x01E070DA, "frame_err_checksum", "protocol parser", "PROVEN STATIC",
     "unique reference to the checksum-error literal; called from the frame handler"),
    (0x01E06E8A, "frame_err_length", "protocol parser", "PROVEN STATIC",
     "unique reference to the command-length error literal; called from the frame handler"),
    (0x01E08D24, "armorx_d2_handler", "D2", "PROVEN STATIC",
     "fall-through block of the dispatcher's rOP != 0xD2 test inside armorx_cmd_dispatch"),
    (0x01E08944, "armorx_d4_handler", "D4", "PROVEN STATIC",
     "fall-through block of the dispatcher's rOP != 0xD4 test (second D4 site)"),
    (0x01E08A68, "armorx_d7_handler", "D7", "PROVEN STATIC",
     "goto target of the dispatcher's rOP == 0xD7 test"),
    (0x01E08860, "armorx_f7_handler", "F7", "PROVEN STATIC",
     "fall-through block of the dispatcher's rOP != 0xF7 test"),
    (0x01E08B86, "armorx_f8_handler", "F6/F7/F8 config", "PROVEN STATIC",
     "goto target of the dispatcher's rOP == 0xF8 test"),
    (0x01E08912, "armorx_f9_handler", "unknown opcode", "PROVEN STATIC",
     "goto target of the dispatcher's rOP == 0xF9 test"),
    (0x01E0898E, "armorx_fa_handler", "unknown opcode", "PROVEN STATIC",
     "fall-through block of the dispatcher's rOP != 0xFA test"),
    (0x01E0914A, "armorx_2f_handler", "unknown opcode", "PROVEN STATIC",
     "goto target of the dispatcher's rOP == 0x2F test"),
    (0x01E0944E, "armorx_ff_response_handler", "protocol TX", "PROVEN STATIC",
     "goto target of the dispatcher's rOP == 0xFF test (response envelope family)"),
    (0x01E0642C, "armorx_f7_response_build", "protocol TX", "STRONG EVIDENCE",
     "single call site, inside the F7 handler, passing opcode 0xF6: the F7 settings path "
     "emits an F6 frame rather than an F7 reply"),
    (0x01E071FE, "stick_curve_engine", "stick", "STRONG EVIDENCE",
     "references 'stick curve init %d: point1(%d,%d), point2(%d,%d)' and "
     "'sensor curve[%d]: dir, min, curve, speed, y_div_x, smooth'"),
    (0x01E05856, "macro_engine_config", "macro engine", "STRONG EVIDENCE",
     "references 'GAMEPAD_MACRO_MAX =%d'"),
    (0x01E16368, "zikway_2g4_deal", "2.4G", "STRONG EVIDENCE",
     "references '...pp_zikway_deal', 'mode=%x, mac:', ' tx busy!'"),
    (0x01E04B38, "app_select_24g", "2.4G", "STRONG EVIDENCE",
     "references '------app select 24g--------'"),
    (0x01E042D0, "user_cfg_engine", "config engine", "STRONG EVIDENCE",
     "references 'USER_CFG...warning_tone_v/poweroff_tone_v', 'auto_off_time', "
     "'init mac addr', 'imu_not calibrated'"),
    (0x01E12714, "user_cfg_bt_name", "config engine", "STRONG EVIDENCE",
     "references 'USER_CFGread bt name err' and 'pps/hid/modules/bt/ble_multi.c'"),
    (0x01E0494A, "config_auto_off_and_mac", "config engine", "STRONG EVIDENCE",
     "references 'USER_CFGauto_off_time:%d' and 'G>>>init mac addr!!!'"),
    (0x01E05C66, "record_build_with_hash", "flash/VM", "STRONG EVIDENCE",
     "indexes 0xDC-byte records (r4 += r5 * 0xdc), zero-fills, hashes 8 bytes at record+2, "
     "stores the byte-reversed result at record+0, logs '...len=%d crc=%x'"),
    (0x01E06216, "enum_switch_0_to_10", "config engine", "STRONG EVIDENCE",
     "bounds check 'if (r0 > 0xa)' followed by a tbb table branch: an 11-way switch"),
    (0x01E1569A, "gyro_calibration", "gyro/IMU", "STRONG EVIDENCE",
     "references '... gyro CAL data now:%d,%d,%d'"),
    (0x01E0EBCC, "imu_axis_dump", "gyro/IMU", "INFERRED",
     "references a '%d,%d,%d,%d' literal attributed to the IMU calibration area"),
    (0x01E12DB4, "imu_type_and_unsupported_cmd", "gyro/IMU", "INFERRED",
     "references 'IMU_TYPE_RIGHT'/'IMU_TYPE_LEFT' and 'unsupport cmd: 0x%x'; single "
     "function mixing the unsupported-command default with IMU type naming"),
    (0x01E139AA, "usbd_auto_detect_init", "USB device", "STRONG EVIDENCE",
     "references 'usbd auto det init'"),
    (0x01E2155A, "sdfile_mount", "storage", "STRONG EVIDENCE",
     "references '[SDFILE]sdfile mount failed!!!'"),
    (0x01E08772 + 0x0, "frame_parse_and_dispatch", "protocol parser", "PROVEN STATIC",
     "same function as armorx_cmd_dispatch: validates then dispatches"),
    (0x01E0AFF2, "ble_transport_layer", "BLE", "INFERRED",
     "contains compares against A5 and 0B and 3 references to the 0B query opcode, "
     "calls the frame handler"),
]

LIVE_ANCHORS = [
    ("0B", "A5 04 0B B4 -> A5 05 0B 30 E5", "0B compared in 0x1e0aff2 (transport) and 0x1e0a944",
     "live query has a reply; firmware shows the 0B compares outside armorx_cmd_dispatch"),
    ("D2", "A5 05 D2 01 7D / A5 05 D2 00 7C", "dispatcher rOP != 0xD2 -> fall-through 0x1e08d24",
     "consistent"),
    ("D4", "A5 04 D4 7D -> A5 07 D4 11 01 00 92", "dispatcher tests 0xD4 twice (0x1e087c8, 0x1e0893e)",
     "consistent; two distinct D4 code paths exist in firmware"),
    ("D7", "configuration write", "dispatcher rOP == 0xD7 -> 0x1e08a68", "consistent"),
    ("F7", "A5 04 F7 A0 -> NO reply live", "falls through rOP != 0xF7 to 0x1e08860, which reads "
     "the byte after the opcode and only acts on values 0/1, and emits an F6 frame in that case",
     "firmware offers a concrete reason for the silence: no reply frame is built on the "
     "non-0/1 path"),
    ("F8", "app sends A5 04 F8", "dispatcher rOP == 0xF8 -> 0x1e08b86", "consistent"),
    ("FC / F6", "A5 05 FC 80 26 -> A5 05 FF FC A5", "no FC compare found in the dispatcher; F6 "
     "appears only as the opcode emitted by the F7 path", "CONTRADICTION with the assumption "
     "that FC is handled in this dispatcher"),
]


def load(p: pathlib.Path):
    return json.loads(p.read_text())


def main() -> int:
    cov = load(Q / "v41-coverage.json")
    val = load(Q / "rom-validation.json")
    tables = load(Q / "v41-switch-tables.json")
    xrefs = load(Q / "v41-string-xrefs.json")
    funcs = load(Q / "v41-functions.json")
    disp = load(F / "armorx-command-dispatch.json")
    romsym = load(Q / "rom-symbols.json")
    high = [t for t in tables if (t.get("base_confidence") or 0) >= 0.9]

    isa = {
        "architecture": "q32s",
        "platform": "AC632N / AC6321A (BD19 family)",
        "toolchain": "JieLi Linux toolchain, LLVM 4.0.1 fork",
        "registered_llvm_targets": ["pi32", "pi32v2", "q32s"],
        "instruction_lengths": cov["insn_size_histogram"],
        "address_mask": "0x1ffffff",
        "load_base": "0x01e00000",
        "switch_instructions": ["tbb", "tbh"],
        "rom_symbols_available": len(romsym),
        "source_of_ground_truth": "cpu/bd19/tools/rom.lst (vendor llvm-objdump listing)",
        "validation": {"instructions_compared": val["compared"],
                       "exact_text_match_pct": val["exact_pct"],
                       "instruction_length_pct": val["length_pct"],
                       "verdict": val["verdict"]},
    }
    (Q / "q32s-isa.json").write_text(json.dumps(isa, indent=2) + "\n")

    sym = {"image": "V41 body app.bin", "base": "0x01e00000",
           "image_size": cov["image_size"], "symbols": [
               {"address": f"{a:#x}", "name": n, "category": c, "grade": g, "evidence": e}
               for a, n, c, g, e in sorted(SYMBOLS)]}
    (Q / "q32s-symbol-map.json").write_text(json.dumps(sym, indent=1) + "\n")

    # ------------------------------------------------------------ q32s report
    lines = [
        "# Breaking the q32s bottleneck (offline, no hardware touched)", "",
        "## Result in one line", "",
        "The vendor's own q32s toolchain was located and put to work, so the ArmorX V41 firmware "
        "is now disassembled and navigable: instruction boundaries, call graph, string xrefs, "
        "switch tables and the ArmorX command dispatcher are all recovered statically.", "",
        "## What was found and how it was verified", "",
        "* The AC63 SDK build scripts name the toolchain explicitly: `download.bat` sets "
        "`OBJDUMP=C:/JL/pi32/bin/llvm-objdump.exe` and passes `-address-mask=0x1ffffff` and "
        "`-print-dbg`, i.e. the vendor's disassembler is a **custom LLVM fork** whose target for "
        "this chip is `q32s` (JieLi's public docs list AC632N/AW31N/AW33N as the q32s parts).",
        "* JieLi publishes a **Linux** build of that toolchain; the q32s `objdump`, `clang` and "
        "`ld` used here come from it. `objdump -version` reports `LLVM version 4.0.1` with "
        "registered targets `pi32`, `pi32v2`, `q32s`.",
        "* The firmware image is raw, so it is wrapped as a `.text` section via the vendor "
        "`clang` (`.incbin`) and linked at its real load base with the vendor `ld`; addresses in "
        "the listing are therefore true firmware addresses.", "",
        "### Independent validation",
        "",
        f"The vendor SDK ships `rom.lst`, a full disassembly of the BD19 mask ROM. Because that "
        f"listing prints raw instruction bytes, the ROM was reconstructed and re-disassembled "
        f"with our pipeline: **{val['compared']} instructions compared, "
        f"{val['exact_pct']}% exact text match, {val['length_pct']}% length match** "
        f"({val['verdict']}). This validates the ISA model, the wrap/link path and the address "
        f"handling in one shot, and it was reproduced after a second extraction of the "
        f"toolchain archive.", "",
        "### V41 coverage",
        "",
        f"* image: {cov['image_size']} bytes at {cov['base']}; {cov['instructions']} "
        f"instructions decoded; instruction sizes "
        f"{cov['insn_size_histogram']}",
        f"* functions recovered (call targets + code after returns + entry): "
        f"{cov['functions_recovered']}",
        f"* calls resolved: {cov['calls_resolved']}; string references: {cov['string_refs']} "
        f"to {cov['distinct_strings_referenced']} distinct strings",
        f"* switch tables: {len(tables)} found, {len(high)} at >=0.9 target-alignment "
        f"confidence",
        f"* ROM/library symbol names available for cross-reference: {len(romsym)}", "",
        "### Caveats (do not over-read the numbers)",
        "",
        "* The image was disassembled **linearly from offset 0**, so the code percentage is a "
        "decode-rate, not a code/data split: string and data regions are decoded as "
        "instructions too. Regions whose decode contains `<unkown instruction>` or an address "
        "that is never a branch target are the ones to suspect as data.",
        "* The switch-table base model is chosen by alignment scoring, which cannot fully "
        "discriminate because so much of the image decodes: the model recorded per table is a "
        "best fit, not a proof. Only tables at 1.0 confidence should be relied on without a "
        "second check.",
        "* Function boundaries come from control-flow evidence, not from symbol tables; the "
        "boundary of a function that is only entered through a table is not guaranteed.", "",
        "### Method summary",
        "",
        "1. toolchain inventory from the SDK build scripts, then the vendor Linux toolchain;",
        "2. raw image -> ELF32-q32s at 0x01e00000 (vendor clang + ld);",
        "3. vendor objdump with `-print-imm-hex` (hex immediates, without which the listing "
        "cannot be matched against the vendor's own style);",
        "4. structured parse into records (address, bytes, length, text, control-flow target, "
        "kind, referenced constants);",
        "5. function recovery, call graph, string xrefs (resolving pointers that land *inside* "
        "a literal, which is the common case for ANSI-escaped format strings);",
        "6. `tbb` switch-table recovery; dispatcher extraction.", "",
    ]
    (FIN / "q32s-reverse-engineering.md").write_text("\n".join(lines) + "\n")

    # ------------------------------------------------------------ symbol map report
    sl = ["# ARMOR-X firmware symbol map", "",
          f"Recovered from the V41 body image ({cov['image_size']} bytes at {cov['base']}).",
          "Grades: PROVEN STATIC / STRONG EVIDENCE / INFERRED. Names are only as strong as the "
          "grade on the row.", "",
          "| address | name | category | grade | evidence |", "|---|---|---|---|---|"]
    for a, n, c, g, e in sorted(SYMBOLS):
        sl.append(f"| `{a:#010x}` | `{n}` | {c} | {g} | {e} |")
    sl += ["", "## Command dispatcher map (from `armorx_cmd_dispatch`)", "",
           f"Function `{disp['function']}` .. `{disp['function_end']}`, "
           f"{disp['instructions_examined']} instructions examined.", "",
           "| opcode | compare at | test | handler | family | evidence |", "|---|---|---|---|---|---|"]
    for h in disp["handlers"]:
        sl.append(f"| {h['opcode_hex']} | `{h['compare_at']}` | {h['test']} | `{h['handler']}` | "
                  f"{h['family']} | {h['evidence']} |")
    sl += ["", "Note: the dispatcher region contains nested switches as well as the top-level "
           "opcode chain, so low-valued entries (0x00-0x1b, 0x0d, 0x19, 0x1b, 0xef) are "
           "sub-command tests, not top-level opcodes. The top-level families are the ones that "
           "match the live protocol: 0x2F, 0x70, 0xD2, 0xD4, 0xD7, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF.",
           "", "## Live anchors cross-checked against firmware", "",
           "| family | live behaviour | firmware | verdict |", "|---|---|---|---|"]
    for fam, live, fw, verdict in LIVE_ANCHORS:
        sl.append(f"| {fam} | {live} | {fw} | {verdict} |")
    sl += ["", "## Symbol categories", ""]
    cats: dict[str, list[str]] = {}
    for a, n, c, g, _e in SYMBOLS:
        cats.setdefault(c, []).append(f"`{a:#010x}` {n} ({g})")
    for c in sorted(cats):
        sl.append(f"* **{c}**: " + ", ".join(cats[c]))
    sl += ["", "Categories with no entry here stay unknown: checksum helper, D6/D8 handlers, "
           "lighting, USB host, Xbox, OTA, bootloader hooks, 0B handler. Absence is a statement "
           "about this pass, not about the firmware."]
    (FIN / "armorx-firmware-symbol-map.md").write_text("\n".join(sl) + "\n")

    print("wrote:")
    for p in (Q / "q32s-isa.json", Q / "q32s-symbol-map.json",
              FIN / "q32s-reverse-engineering.md", FIN / "armorx-firmware-symbol-map.md"):
        print(f"  {p.relative_to(REPO)}  ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
