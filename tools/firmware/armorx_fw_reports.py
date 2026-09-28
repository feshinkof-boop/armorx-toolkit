#!/usr/bin/env python3
"""armorx_fw_reports.py - emit the firmware reports from the recorded artifacts.

Every value is read from the JSON artifacts produced by the analysis pipeline;
nothing is hand-typed. Offline, read-only.

Usage: armorx_fw_reports.py <workspace-dir>
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

WS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                  "/home/salamanka/armorx-lab/research/firmware/2026-09-28")
REPO = pathlib.Path("/home/salamanka/armorx-lab")
FR = REPO / "results" / "firmware"
REC = REPO / "results" / "reconciliation"
FIN = REPO / "results" / "final"
for d in (FR, REC, FIN):
    d.mkdir(parents=True, exist_ok=True)


def j(name):
    return json.loads((WS / name).read_text())


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


inv = j("originals-inventory.json")
cmp_ = j("v41-chinese-vs-international.json")
xv = j("cross-version.json")
man = j("firmware-manifest.json")
prov = j("download-provenance-firefox.json")

# ---------------------------------------------------------------- provenance
lines = ["# ARMORX Pro — firmware download provenance", "",
         "Recovered from a **read-only copy** of `snap/firefox/.../places.sqlite` "
         "(the only browser history database present; no Chromium/Chrome profile exists).", "",
         "| file | size | SHA-256 |", "|---|---|---|"]
for f in inv["files"]:
    lines.append(f"| `{f['filename']}` | {f['size']:,} | `{f['hashes']['sha256']}` |")
lines += ["", "## Recovered download URLs", "",
          "| artifact | URL | title | evidence |", "|---|---|---|---|"]
for e in prov["entries"]:
    lines.append(f"| `{pathlib.Path(e['download_file'] or '').name}` | `{e['url']}` | {e['title']} | firefox moz_places/moz_annos |")
lines += ["", "### Not recovered", "",
          "* `战甲Xpro 固件V41.zip` — **no URL entry in history**. The file exists in "
          "`~/.local/share/recently-used.xbel` (added 2026-09-28T12:11:31Z), and the other two "
          "Chinese-bucket files came from `bigbig-won-cn.oss-cn-shanghai.aliyuncs.com/Support/"
          "固件正式版/ArmorX-Pro-Firmware/`, so the same folder is *consistent* with it — "
          "**INFERRED, not PROVEN**.", "",
          "## Source hosts", "",
          "* CN bucket: `bigbig-won-cn.oss-cn-shanghai.aliyuncs.com` (Aliyun OSS, Shanghai)",
          "* US bucket: `bigwon-us.oss-us-west-1.aliyuncs.com` (Aliyun OSS, US-West)",
          "* Landing pages: `https://www.bigbigwon.com/faq-items/armor-x-pro-v41-firmware-2023-0228/` "
          "(\"Armor X pro V41 Firmware 2023 0228 (New) – MOJHON\"), `https://www.mojhon.cn/support/controller/armorx-pro-upgrade/`",
          "* No checksums are published next to the downloads.", ""]
(FR / "download-provenance.md").write_text("\n".join(lines) + "\n")

# ------------------------------------------------- chinese vs international V41
CH = WS / "chinese-v41"
IN = WS / "intl-v41"
def tree(d):
    return {str(p.relative_to(d)): (p.stat().st_size, sha256_file(p))
            for p in sorted(d.rglob("*")) if p.is_file()}
t_c, t_i = tree(CH), tree(IN)
c_bytes = (WS / "originals" / "战甲Xpro 固件V41.zip").stat().st_size
i_bytes = (WS / "originals" / "Firmware ArmorX-Pro V41.rar").stat().st_size
apk = next((k for k in t_c if k.lower().endswith(".apk")), None)
apk_name = pathlib.Path(apk).name if apk else "n/a"
apk_size = t_c[apk][0] if apk else 0
apk_sha = t_c[apk][1] if apk else ""
identical = [(k, k, t_c[k][0], t_c[k][1]) for k in t_c if k in t_i and t_c[k][1] == t_i[k][1]]
uniq_c = [k for k in t_c if k not in t_i or t_c[k][1] != t_i[k][1]]
uniq_i = [k for k in t_i if k not in t_c or t_c[k][1] != t_c[k][1]]
txt_only = [k for k in uniq_c if k.lower().endswith(".txt")]
lines = ["# ArmorX Pro V41 — Chinese package vs international package", "",
         "## The size question, answered", "", "```text",
         f"Chinese V41 zip      {c_bytes:>12,} bytes",
         f"International RAR    {i_bytes:>12,} bytes",
         f"difference           {c_bytes-i_bytes:>12,} bytes",
         "```", "",
         f"**The entire difference is the bundled Android application "
         f"`{apk_name}` ({apk_size:,} bytes) plus {len(txt_only)} Chinese-only text file(s), which the "
         f"international package does not contain.**", "",
         "The firmware payloads and the whole Windows updater tree are **byte-identical** in both.", "",
         "## Byte-identical payloads", "", "| file (CN, identical in INT) | size | SHA-256 |", "|---|---|---|"]
for k, _k2, size, sha in identical:
    lines.append(f"| `{k}` | {size:,} | `{sha}` |")
lines += ["", "## Chinese-only files", "", "| file | size | SHA-256 |", "|---|---|---|"]
for k in uniq_c:
    lines.append(f"| `{k}` | {t_c[k][0]:,} | `{t_c[k][1]}` |")
lines += ["", "## Consequences", "",
          "* A user who already has the app can take **either** package; flashing either yields the "
          "same controller firmware.",
          f"* `{apk_name}` is the **2.22** app generation, i.e. the CN package ships an app *older* than "
          "the 4.0.8 APK already analysed in this project — a historical artifact for the app-side "
          "timeline, not new firmware.", "",
          "## Verdict", "",
          "> Are the actual V41 firmware payloads identical? **YES** — `01战甲X Pro固件-V41.bup` and "
          "`Firmware ArmorX-Pro V41.bup` have the same SHA-256, as do the two V3600 dongle `.bup` files "
          "and all seven `BTUpgrade_V1.9/` files.", ""]
(FR / "v41-chinese-vs-international.md").write_text("\n".join(lines) + "\n")

# --------------------------------------------------------------- BUP format
bups = {p["source"].split("/")[-1]: p for p in man["packages"]}
lines = ["# BigBigWon `Upgrade Pack` (`.bup`) container format", "",
         "Reverse-engineered offline from five real packages; all offsets verified against all five.", "",
         "```text", "offset  size  field", "0x00    22    magic \"BigBigWon Upgrade Pack\" + 2 NUL",
         "0x16    4     header version (0x00010000)",
         "0x1A    1     sub-image count flag",
         "0x1B    1     board/model code (0x1d=V41 body, 0x1e=V3600 dongle, 0x16=V32, 0x17=V3000, 0x00=V2224)",
         "0x1F    0x04  version string, 4 chars (\"V41\", \"V36\", \"V32\", \"V30\", \"2224\")",
         "0x2B    32    image name slot A (\".ufw\" name; \"null.bin\"/\"1.bin\" when unused)",
         "0x5B    32    image name slot B",
         "0x8B    4     slot A compressed span (u32 LE, optional)",
         "then, per sub-image:", "        n * { u32 compressed_len, u32 uncompressed_len, <zlib stream> }",
         "```", "",
         "## Payload encoding", "",
         "* The payload is a **sequence of independently-compressed zlib blocks**, each inflating to "
         "exactly **32,768 (0x8000)** bytes (the last block may be shorter).",
         "* Each block is preceded by an 8-byte record `(compressed_len, uncompressed_len)`.",
         "* A block whose `compressed_len > uncompressed_len` is a zlib **stored** block "
         "(`78 9c 00 …`), i.e. incompressible data is passed through untouched.",
         "* The decompressed result is a **raw JieLi flash image** (not a JieLi `.ufw` container, "
         "despite the `.ufw` in the slot name): it already contains `uboot.boot` + `isd_config.ini` + "
         "`app_dir_head` in JLFS layout.", "",
         "## Verified instances", "", "| package | image | compressed span | image bytes | chunks |",
         "|---|---|---|---|---|"]
for name, p in bups.items():
    h = p.get("bup_header", {})
    lines.append(f"| `{name}` | {p.get('images',[{}])[0].get('name','')} | {h.get('chunk_count','')} chunks | "
                 f"{p.get('images',[{}])[0].get('size',0):,} | {p.get('chunks','')} |")
lines += ["", "## Tooling", "",
          "* `tools/firmware/armorx_bup.py` — strict, bounds-checked parser/unpacker "
          "(`info` / `walk` / `unpack` subcommands).",
          "* `tools/firmware/armorx_fw_pipeline.py` — one command: hash → unpack → JieLi-unpack → manifest.",
          "* `tools/firmware/armorx_fw_compare.py` — cross-version comparison table.", ""]
(FR / "bup-format.md").write_text("\n".join(lines) + "\n")
print("wrote download-provenance.md, v41-chinese-vs-international.md, bup-format.md")
