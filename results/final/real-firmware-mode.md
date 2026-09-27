# ARMOR-X Pro — PHASE T: real-firmware mode hunt (static, hardware untouched)

Date: 2026-09-27 (UTC)
Scope: read-only. No flash/erase/write/command was sent to any hardware. No APK was modified or re-signed.
Report path: `/home/salamanka/armorx-lab/results/final/real-firmware-mode.md`
Machine-readable companion: `/home/salamanka/armorx-lab/results/final/firmware-inventory.json`
Frozen copies: `/home/salamanka/armorx-lab/firmware/original/`
Third-party tools: `/home/salamanka/armorx-lab/tools/vendor/`

Evidence labels used: PROVEN LIVE / PROVEN STATIC / STRONG EVIDENCE / INFERRED / UNKNOWN / CONTRADICTED.

---

## 0. Headline

**No ARMOR-X body firmware image and no F20-receiver firmware image exists anywhere under
`/home/salamanka`.** There is no `.ufw`, no `jl_isd.fw`, no `update.ufw`, no `isd_config.ini`, and no
`uboot.boot` file on disk — the only occurrences of those names are **string literals inside the
Windows updater's PE binaries** and **inside a public third-party AC632N sample used here as a
positive control**. Therefore:

* item (3) unpack-a-real-container step was executed against a **positive control** (a genuine
  JieLi/JLFS AC632N-family OTA image taken from the public `AC632Nuke` repo), not against an
  ARMOR-X image — because no ARMOR-X image was found;
* item (4) protocol-fingerprint search inside a parsed firmware image was executed on that positive
  control and is **negative for all ARMOR-X-specific fingerprints** (expected — it is not ARMOR-X
  firmware);
* the ARMOR-X firmware-update path is nonetheless **PROVEN STATIC** to be a JieLi/AC632N path
  (`DevMgr.dll` + the JieLi `firmware_upgrade_library` DLLs), which is the substantive gain of this
  phase.

The negative result is a *distribution* fact, not a *platform* fact: the updater downloads firmware
at run time from a vendor HTTP endpoint (see §4), so the images were never present on this host.

---

## 1. Search space and exact patterns used

Whole-home search, excluding build/VCS/cache noise. Reproduce with:

```bash
# name-based sweep
find /home/salamanka -xdev -type f \
  \( -iname '*.ufw' -o -iname '*.fw' -o -iname 'jl_isd*' -o -iname 'update.ufw' \
     -o -iname 'isd_config*' -o -iname 'uboot.boot' -o -iname 'key_mac*' \
     -o -iname '*.hex' -o -iname '*.img' -o -iname '*.rom' -o -iname '*.dump' \
     -o -iname '*.apk' -o -iname '*.apkm' -o -iname '*.xapk' \
     -o -iname '*.exe' -o -iname '*.dll' -o -iname '*.msi' -o -iname '*.cab' \) 2>/dev/null

# directory-name sweep
find /home/salamanka -xdev -type d \
  \( -iname '*armorx*' -o -iname '*bigbigwon*' -o -iname '*f20*' \
     -o -iname '*jieli*' -o -iname '*jl_*' \) 2>/dev/null

# content sweep (JieLi/JLFS container fingerprints), skipping heavy trees
find /home/salamanka -xdev -type f -size +1k -size -200M \
  ! -path '*/.cache/*' ! -path '*/.config/*' ! -path '*/Android/Sdk/*' ! -path '*/src/*' \
  ! -path '*/.npm/*' ! -path '*/.rustup/*' ! -path '*/.cargo/*' ! -path '*/node_modules/*' \
  ! -path '*/site-packages/*' ! -path '*/.hermes/*' ! -path '*/.git/*' 2>/dev/null \
| xargs -r -d '\n' grep -l -a -m1 -E 'JLFS|isd_config\.ini|uboot\.boot|key_mac|AC632N|CUpgradeRainbow'
```

Files scanned: 510,947 under `/home/salamanka` (whole home, `-xdev`).

Result of the **name** sweep for firmware containers: **zero** `.ufw` / `.fw` / `jl_isd.fw` /
`update.ufw` / `isd_config.ini` / `uboot.boot` / `key_mac` files, anywhere.

Result of the **content** sweep: every hit was a PE binary, a text handoff, or the positive control
(§5). No hit was a flashable container.

---

## 2. Candidates found (all frozen in `firmware/original/`)

Full machine-readable detail (sha256, size, entropy, magic, fingerprints, frozen sha256) in
`firmware-inventory.json`. Summary:

| Candidate | Size | Entropy | Magic (first 32 B) | Container verdict | Label |
|---|---|---|---|---|---|
| `DevMgr.dll` (×4 byte-identical copies) | 7,299,472 | 7.63 | `4d5a…` (PE32 `MZ`) | Windows PE DLL — **not** firmware; **contains a JieLi AC632N UFW upgrade subsystem** | PROVEN STATIC |
| `WndMgr.dll` | 24,313,232 | 7.00 | `4d5a…` (PE32) | Windows PE DLL, UI — not firmware | PROVEN STATIC |
| `NetMgr.dll` | 2,234,768 | 6.63 | `4d5a…` (PE32) | Windows PE DLL, cloud client — not firmware | PROVEN STATIC |
| `BigBigWonAssistant.exe` | 583,056 | 6.61 | `4d5a…` (PE32) | updater main exe — not firmware | PROVEN STATIC |
| `BTUpgrade.dll` | 351,152 | 7.50 | `4d5a…` (PE32) | JieLi `firmware_upgrade_library` — not firmware | PROVEN STATIC |
| `BTUpgrade_HX.dll` | 375,216 | 7.55 | `4d5a…` (PE32) | JieLi `firmware_upgrade_library` (huajuxin variant) — not firmware | PROVEN STATIC |
| `BTUpgrade_n.dll` | 351,152 | 7.50 | `4d5a…` (PE32) | JieLi `firmware_upgrade_library` — not firmware | PROVEN STATIC |
| `USBUpgrade.dll` | 19,344 | 6.99 | `4d5a…` (PE32) | USB upgrade helper — not firmware | PROVEN STATIC |
| `BIGBIGWON_Assistant_1.0.6.1.zip` | 53,391,727 | 7.999 | `504b…` (`PK`, ZIP) | Windows installer; **contains no firmware file** (116 entries: DLLs, crash-reporter, html tips) | PROVEN STATIC |
| `BIGBIGWON-4.bin` | 36,492,532 | 7.997 | `504b…` (`PK`, ZIP) | **ZIP of APK splits** (`base.apk`, `config.*.apk`) — an app package mislabelled `.bin`; **excluded from the firmware claim** | PROVEN STATIC |
| `armorx-handoff.hex` | 67,352 | 4.00 | `…()` ASCII | hex-encoded git bundle (ASCII); not firmware | PROVEN STATIC |
| `PC_AC632N_ota.bin` **(positive control)** | 150,764 | 6.70 | `0120ea4c 80000000 7ca60000 09000000 …` | **genuine JieLi JLFS "new-fw" OTA container**; entry table = `ble_ota.bin`, `edr_ota2.bin`, `ble_app_ota.bin`, `uart_user.bin`; also embeds the string `AC632N_update` | PROVEN STATIC (third-party sample, **not** ARMOR-X) |
| `PC_AC632N_ota_decrypted.bin` | 150,764 | 6.70 | same as above | `fwunpack_newfw.py` output of the control | PROVEN STATIC |
| `PC_rom.image` | 28,672 | 6.78 | `c0f30528…` | BD19 mask-ROM image (third-party) | PROVEN STATIC (third-party) |

**Excluded from the firmware claim** — the four frozen research APKs (app packages, already
analysed):

```
785684ec28a6fe0b111597933527b1cc0e53c3332ed4cc8c8db4112539c0361c  apk/original/2.22.0901/BIGBIG_WON_2.22.0901.apk
7ed18b774bf8beab0ff2ff11bc0669f4cacb9baa5cc309bf277752592a2bc892  apk/original/2.23/base.apk
0bae884badc004991e638b0e62a0a6afc07256a5deabd8bb833f0bb36638f305  apk/original/2.24/BIGBIGWON-2.24.0919.apk
64e0832b1f97d995b40bf994465c277340e96a4f2b6b2fc5ef1eb4e2af9378e2  apk/original/4.0.8/base.apk
```

None of those APKs contains a bundled firmware asset — an entry-name sweep across every `.apk`/
`.apkm` in the lab found only the usual `DebugProbesKt.bin` / `AssetManifest.bin` / annotation
artifacts, no `.ufw`/`jl_isd.fw`/firmware payload.

---

## 3. The updater binaries carry a JieLi / AC632N firmware-upgrade subsystem (PROVEN STATIC)

`DevMgr.dll` (sha256 `653cb3219abd09338c1590375a60162e6e4fd7b72c1856aaa7b796b7da7d709c`;
byte-identical copies at `armorx_research/{devmgr_static,dongle_baseline_v13/artifacts}/DevMgr.dll`,
`armorx_handoff/project/raw_private/current/DevMgr.dll`) contains, inter alia:

**Imports / API names (JieLi upgrade library):**
```
JL_loadUfwData        JL_getUfwCrc        JL_getUfwPidVid
JL_queryDevicePidVid  JL_upgradeDevice    JL_getUfwDataCrc
```

**Class / method names (C++ RTTI, MSVC-mangled, in the string table):**
```
CUpgradeUFW::PrepareForUpgrade / ::LoadUpgradeDLL / ::IsValidUpgradeFile
CUpgradeUFW::GetUpgradeDisk / ::LoopProcess
CUpgradeRainbow3Thread::Upgrade_JieLi
CUpgradeRainbow3DongleThread::Upgrade_JieLi
UPGRADE_STEP_BIN / UPGRADE_STEP_FOT / UPGRADE_STEP_UFW
CDeviceMgr::ReadyForUfw_UDisk_Delegate   CDeviceMgr::GetTestUfwFile
CUpgradeRainbow3DongleThread::Upgrade_NearLink   CUpgradeRainbow3Thread::Upgrade_NearLink
```

**Container / file-name literals:**
```
uboot.boot (×8)      isd_config.ini (×28)      JLUFW (×5)
AC632N_TRANS         AC632N_update
ble_ota.bin          ble_app_ota.bin           edr_ota2.bin   uart_user.bin
/*.ufw   (file-open filter)                    .?AVCUpgradeUFW@@
```

`BTUpgrade.dll` / `BTUpgrade_HX.dll` / `BTUpgrade_n.dll` are the JieLi SDK's own upgrade library —
their embedded PDB paths and exports prove it:

```
BTUpgrade.dll     E:\git_109\firmware_upgrade_library_yeyang\src\dll\Release\dll.pdb
BTUpgrade_HX.dll  E:\git_109\firmware_upgrade_library_026huajuxin\src\dll\Release\dll.pdb
BTUpgrade_n.dll   E:\git_109\firmware_upgrade_library_yeyang\src\dll\Release\dll.pdb
exports: JL_upgradeDevice  JL_upgradeDeviceByPath  JL_setDualUbootMode
```

**Interpretation.** The vendor's own PC updater ships a JieLi firmware-upgrade library and drives
it with `.ufw` files, `isd_config.ini` / `uboot.boot` handling and an `AC632N_*` chip tag, alongside
`Upgrade_JieLi` methods on both the body (`Rainbow3Thread`) and dongle (`Rainbow3DongleThread`)
upgrade threads. That is a **PROVEN STATIC** fact about the *update toolchain*.

**It is not** proof that the flash image actually residing in the ARMOR-X body is an AC632N image —
no such image was available to inspect. Distinguish the two claims carefully.

**Incidental-match discipline.** The `SFC` byte-pair counts (WndMgr=2, installer zip=2,
`BIGBIGWON-4.bin`=5) and the single `key_mac` hit in `WndMgr.dll` are **incidental** — high-entropy
binary data producing 3-char byte coincidences; no surrounding code or metadata makes them
structural. Every other fingerprint hit above sits inside a real string table adjacent to related
symbols and is **meaningful**.

---

## 4. Where the firmware actually lives (INFERRED, corroborated)

The updater downloads firmware at run time instead of bundling it:

* `NetMgr.dll` and `WndMgr.dll` expose the vendor API base:
  `http://m.bigbigwon.com:8080/dev/…` including **`/dev/queryFirewareList`** (sic — "Fireware"),
  plus `/dev/queryConfigList`, `/dev/changeConfig`, `/dev/userLogin`, etc.
* The installer ships HTML help pages literally named
  `html/DongleFirmwareUpgradeTip_{en_us,zh_cn,…}.html` and
  `html/FirmwareUpgradeTip_{en_us,zh_cn,…}.html`, i.e. the upgrade flow prompts the user to obtain
  firmware, rather than carrying it.

So the real images are server-side and were never materialised on this workstation. Retrieving them
is out of scope for a read-only static pass and was **not** performed (no vendor firmware was
downloaded).

---

## 5. Positive control — the tooling works and would have caught a real container

Public tooling was fetched (attribution kept, nothing vendored into public-release code):

| Repo | Commit | Date |
|---|---|---|
| `https://github.com/kagaimiq/jl-misctools` | `0a5b12db0ef38f3042acffbe2452730a37fd2405` | 2025-02-20 |
| `https://github.com/tpunix/AC632Nuke` | `6f179f2b0ae5b3d6bc9885ec4f3d7cb82d0bdee9` | 2022-01-20 |

Located tool: `tools/vendor/jl-misctools/firmware/fwunpack_newfw.py`
(sha256 `b263277648102eb259fd658f974a3d30ed6f15f6b0bff307de186fab040820af`).

Positive control = `tools/vendor/AC632Nuke/mboot/tools/ota.bin`
(sha256 `3595c8d0f367b40b6da4e64d19c99304339f2bd6f86fdd119359f471bee21940`, 150,764 B) — a genuine
JieLi "new-fw"/JLFS OTA image named by the AC632Nuke project.

```
$ python3 fwunpack_newfw.py pc/ota.bin
#
# pc/ota.bin
#
[!] Could not locate the base offset of the firmware.
# EXIT=0 ; produced ota.bin_unpack/{jlfw.yaml, decrypted.bin}
```

`jlfw.yaml` → `format: jl-new-fw`; `decrypted.bin` parses a JLFS entry table whose names are
`ble_ota.bin`, `edr_ota2.bin`, `ble_app_ota.bin`, `uart_user.bin`, and embeds the literal
`AC632N_update`. **Every one of those four names occurs in `DevMgr.dll`** (`ble_ota.bin` ×8,
`ble_app_ota.bin` ×8, `edr_ota2.bin` ×10, `uart_user.bin` ×8), and `AC632N_update` occurs in both.
That name-set identity is the strongest cross-link this phase produced between the vendor updater
and the AC632N OTA format.

**Positive-control conclusion:** the detection + unpack path is exercised and works against a real
JieLi JLFS container; the empty result for ARMOR-X is therefore a genuine absence, not a tooling
failure.

### Protocol-fingerprint search inside the parsed control (item 4)

Run against `decrypted.bin`:

| Fingerprint | Count | Meaning |
|---|---|---|
| `ZJ-XT` | 0 | absent |
| `2741` | 0 | absent |
| `413D` / `413d` | 0 | absent |
| `AE00` / `AE01` / `AE02` | 0 | absent |
| `FE DC BA` | 0 | absent |
| `AC632` | 1 | **meaningful** — inside the literal `AC632N_update` |
| `BD19` | 0 | absent |
| `0x0090` (144) config length | n/a | not a config blob; N/A |
| `0xA001` CRC polynomial | 0 | **see note** |

**CRC note.** The task's expected CRC polynomial `0xA001` (CRC-16/IBM-Modbus, reflected) does **not**
match the JieLi container CRC: `jl-misctools/firmware/jltech/crc.py` defines
`jl_crc16 = crcmod.mkCrcFun(0x11021, initCrc=0x0000, rev=False)` — i.e. **CRC-16/CCITT, polynomial
`0x1021`** (stated as `0x11021`). `0xA001` is therefore a property of the ARMOR-X *config blob*, not
of the JieLi *firmware container*; it was not expected to appear here and did not. Recorded so the
two are not conflated later.

---

## 6. Platform evidence level AFTER this phase

**AC6321A / AC632N / BD19 (ARMOR-X body): remains STRONG EVIDENCE — not upgraded to PROVEN.**

Reasoning, split by claim:

* “The ARMOR-X vendor's PC updater contains a JieLi upgrade subsystem that tags AC632N and handles
  `.ufw` / `uboot.boot` / `isd_config.ini`” — **PROVEN STATIC** (this phase, `DevMgr.dll` +
  `BTUpgrade*.dll`).
* “The ARMOR-X body flash image is a JLFS/AC632N image” — **UNKNOWN**. No image exists on this host;
  the container was never inspected. The task said it may still be UNKNOWN; it is, and it is left
  UNKNOWN rather than upgraded.
* “The ARMOR-X body uses an AC6321A-family SoC” — **STRONG EVIDENCE** (unchanged in kind from the
  prior handoff: FCC identification + QFN32 layout + GPIO names; now additionally reinforced, on the
  *toolchain* side only, by the updater's AC632N path).

No new CONTRADICTED or PROVEN-LIVE facts arose. No hardware was contacted this phase.

---

## 7. F20 USB receiver / dongle — separate section

The F20 receiver path was **not** conflated with ARMOR-X body firmware, and this phase found **no
F20 firmware image** either.

* The updater's dongle flash path is a **separate, non-JieLi-`.ufw` mechanism** — it shells out to a
  DFU flasher. From `devmgr_dfu_analysis.json` (derived from the same `DevMgr.dll`) and the DLL
  strings:
  ```
  CUpgradeRainbow3DongleThread::Upgrade_NearLink
  -bs25dfu -pid:0x2106 -vid:0x413d -usage:0x01 -usagepage:0xffb1 -bin:%s
  %s\GamepadAssistant\BurnTool\BurnTool.exe
  ```
  i.e. the dongle is flashed via **`bs25dfu` / `BurnTool.exe`**, with target `VID:PID = 413D:2106`
  (the historical F20 receiver ID), whereas the body uses the JieLi UFW path. Two different
  mechanisms — keep them distinct.
* `USBUpgrade.dll` (19,344 B) is present in the installer but contains no firmware and no JieLi
  strings.
* No `.bin`/`.ufw` receiver firmware payload exists anywhere under `/home/salamanka`.

Note on `413D`: the prior handoff records `413D` as **JieLi's USB vendor ID** (validated against
`usb.ids` by `devmgr_device_id_table.json`). The dongle therefore matches a JieLi-owned VID while
its DFU tool identifies as `bs25dfu`. Whether the F20 receiver silicon is JieLi, a BS25-family part,
or something else is **UNKNOWN** and must not be settled from the VID alone. This phase adds no
evidence either way, and no F20 image to analyse.

---

## 8. Deliverables

* `/home/salamanka/armorx-lab/results/final/real-firmware-mode.md` — this report.
* `/home/salamanka/armorx-lab/results/final/firmware-inventory.json` — machine-readable inventory
  (path, sha256, size, entropy, magic_hex, file_type, fingerprints, role, kind, frozen_copy,
  frozen_sha256, evidence label per candidate).
* `/home/salamanka/armorx-lab/firmware/original/` — frozen byte-identical copies of every candidate.
* `/home/salamanka/armorx-lab/tools/vendor/` — `jl-misctools` (kagaimiq) and `AC632Nuke` (tpunix) at
  the commits in §5.

Nothing outside `firmware/`, `tools/vendor/` and the two report files was written.
