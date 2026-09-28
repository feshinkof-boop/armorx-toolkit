# ARMOR-X Pro — firmware / updater ecosystem master report

Canonical firmware document for the ARMOR-X Pro research project. Offline/static analysis of four
operator-supplied packages. **No hardware was touched, nothing was flashed, no BLE/USB device was
contacted.** Evidence grades: `PROVEN` / `STRONG EVIDENCE` / `INFERRED` / `UNKNOWN` / `CONTRADICTED`.

Supporting artifacts:

| artifact | path |
|---|---|
| original inventory (hashes, metadata) | `research/firmware/2026-09-28/originals-inventory.json` |
| download provenance | `results/firmware/download-provenance.{md,json}` |
| CN vs international V41 | `results/firmware/v41-chinese-vs-international.{md,json}` |
| BUP container format | `results/firmware/bup-format.md` |
| ecosystem / components / cross-version | `results/firmware/firmware-ecosystem.md` |
| machine-readable manifest | `research/firmware/2026-09-28/firmware-manifest.json` |
| string corpus (all images) | `research/firmware/2026-09-28/string-corpus.json` |
| unknown ledger | `results/reconciliation/firmware-unknown-ledger.{json,md}` |
| tools | `tools/firmware/armorx_bup.py`, `armorx_fw_pipeline.py`, `armorx_fw_compare.py`, `armorx_fw_reports.py` |

---

## 1. Packages

Four originals, preserved read-only under `research/firmware/2026-09-28/originals/`:

| file | bytes | format | source |
|---|---|---|---|
| `战甲Xpro 固件V41.zip` | 36,528,812 | ZIP (stored) | CN OSS bucket `固件正式版/ArmorX-Pro-Firmware/` |
| `战甲Xpro 固件V32 20220815.rar` | 3,364,439 | RAR5 | CN OSS bucket (URL recovered) |
| `ArmorX-Pro-Firmware-V2224.bup` | 970,968 | BUP | CN OSS bucket (URL recovered) |
| `Firmware ArmorX-Pro V41.rar` | 6,070,709 | RAR5 | US OSS bucket (URL recovered) |

## 2. Provenance

Three of four URLs recovered from a read-only copy of Firefox `places.sqlite` (no Chromium profile
exists on the host); the fourth (`V41.zip`) has no history row and is recorded as **not recovered**
(host/path *inferred* only). Full table in `results/firmware/download-provenance.md`.
No checksums are published next to any download — the hashes in this document were computed here.

## 3. Hashes

`originals-inventory.json` records for every original: absolute path, size, mtime, inode, mode,
`file(1)`, MIME, xattrs, and **SHA-256 / SHA-1 / MD5 / BLAKE2b** (BLAKE3 unavailable — no `b3sum`).
Example: `战甲Xpro 固件V41.zip` = `2554f7eba6df55d6748fabd414ee9c5219bc171d1c5a595c000e890a1b95a77c`.
Extraction trees: `chinese-v41/`, `intl-v41/`, `v32/` (separate, never merged).

## 4. Chinese vs international V41

**The 34.8 MB vs 5.8 MB difference is fully explained: the Chinese ZIP bundles the 28,032,675-byte
Android app `BIGBIG_WON_2.22.1226.apk` plus Chinese-only change-log text files.** All firmware
payloads and all seven `BTUpgrade_V1.9/` files are **byte-identical** between the two packages.

## 5. Firmware targets

| product | image name | board code | flash image | app.bin |
|---|---|---|---|---|
| ArmorX Pro body V41 | `XT_XBOX_update_s_v41_20230208.ufw` / `…20230209.ufw` | 0x1d | 1,124,288 | 227,440 |
| dongle V3600 | `XT_DONGLE_update_v36_20221116.ufw` / `…HJX…` | 0x1e | 989,120 | 192,536 |
| body V32 | `XT_XBOX_update_s_v32_20220806.ufw` | 0x16 | 1,109,440 | 223,960 |
| dongle V3000 | `XT_DONGLE_update_v30_20220809.ufw` | 0x17 | 937,920 | 179,376 |
| body V2224 | `XT_XBOX_update_s_v24_20220613.ufw` | 0x00 | 1,037,760 | 204,564 |

Body images are ~1.1 MB and dongle images ~0.95 MB; both use the same JieLi uboot.

## 6. BUP format

`BigBigWon Upgrade Pack`: 0x8B-byte header (magic, version, board code, 4-char version string, two
32-byte image-name slots, slot-A span) followed by sub-images stored as back-to-back **zlib blocks of
32,768 B**, each preceded by a `(compressed_len, uncompressed_len)` u32 record. Incompressible blocks
are stored (`78 9c 00 …`). Full spec: `results/firmware/bup-format.md`. Parser:
`tools/firmware/armorx_bup.py`.

## 7. Updater architecture

`BTUpgrade_V1.9/` ships `BUpgrade.exe` (2,088,960) plus `Upgrade.dll`, `Devices.dll`, `BTUpgrade.dll`,
`BTUpgrade_HX.dll`, `Skin.dll`, `USBUpgrade.dll` and `bugrade.log`. All seven files are byte-identical
in the CN and international V41 packages. V32 ships a *different, older* updater as a nested 7z
(`墨将升级工具BUpgrade v1.1(log).7z`). **Static PE analysis of these binaries was not completed in
this pass** — see `FW-U-012` / `FW-U-020` in the ledger.

## 8. Updater dynamic behaviour

**NOT PERFORMED — deliberately.** Executing an untrusted Windows updater was only permitted in a
disposable/isolated environment, and no VM or Wine sandbox exists on this host (Wine is not
installed). Rather than run it unsandboxed, the branch was deferred; nothing was executed.

## 9. JieLi evidence — `PROVEN`

`AC632N` chip name, `AC632N_TRANS` PID, `JLBTSDKflash`, `632N_LE_UPDATE`, `UPDATE_JUMP`,
`uboot.boot`, `isd_config.ini`, `app_dir_head`, `VM`, `BTIF`, `EXIF`, `USERIF`, `key_mac`,
`ble_ota.bin`, `edr_ota2.bin`, `ble_app_ota.bin`, `uart_user.bin`, `btctrler`, `btstack`,
`H4_Controller`, `link_layer`, `----RCSP_BLE----`, `mnt/sdfile/res/md5.bin`.
The images parse with the public JieLi unpacker as `format: jl-new-fw`, **FS version 11**,
`flash size 0x07F000`, `spl: top/uboot.boot (compressed)`.

## 10. CPU / ISA

The application targets **JieLi AC6321A** (`board_ac6321a.c` inside the app; `bd19` board directory;
AC63 SDK ships `board_ac632n_demo_cfg.h` / `board_ac6321a_demo_cfg.h` under `cpu/bd19`).

**ISA = JieLi q32s (`ELF32-q32s`, BD19 core)** — `STRONG EVIDENCE`. The SDK's
`cpu/bd19/tools/rom.lst` is a full disassembly of the BD19 ROM (9,747 parsed instructions, lengths
2/4/6 bytes = 16/32/48-bit); counting the 48 most frequent ROM opcode prefixes in each decrypted
`app.bin` at any alignment gives **~99,000–100,300 hits per MiB versus 749 per MiB in random data
(≈133× enrichment)**, uniform across body and dongle builds. ARM/Thumb, RISC-V and 8051 are ruled
out. A working q32s **decoder was not built** in this shift, so instruction boundaries still cannot
be walked (`FW-U-021`, PARTIALLY_RESOLVED). Details: `results/firmware/isa-identification.md`.

## 11. Memory map

| region | address / offset |
|---|---|
| app base | `0x01E00000` |
| entry point | `0x01E00120` (31,457,568) |
| JLFS: `uboot.boot` | flash 0x000A0 (4,831 B) |
| JLFS: `isd_config.ini` | flash 0x0137F (102 B) |
| JLFS: `app_dir_head` / `app.bin` | app-area base 0x2000 / offset 0x120 |
| JLFS: `cfg_tool.bin` | app-area 0x37990 (722 B) |
| JLFS: `VM` | 0x3B000 (262,144 B) |
| JLFS: `BTIF` / `EXIF` / `USERIF` | 0x7B000 / 0x7C000 / 0x7D000 |
| JLFS: `key_mac` | 0x7F000 (4,096 B) |
| `p11_code.bin` (resource) | 4,128 B |

## 12. Executable images

Seven flash images extracted and unpacked; seven `app.bin` files recovered **in plaintext**
(the app region is ENC-obfuscated with the per-image chip key from `isd_config.ini`, which the JieLi
unpacker resolves). `uboot.boot`, `cfg_tool.bin` and `p11_code.bin` are byte-identical across **all**
packages (body and dongle).

## 13. Protocol handlers

The decrypted app contains a real frame dispatcher — `out cmd=%x,%x pa=%x, len=%d:`,
`in cmd=%x,%x, len=%d:`, `unsupport cmd: 0x%x`, `cmd head err %x %x`, `cmd len err %x`,
`cmd sum err %x %x` — i.e. head/length/checksum validation matching the project's established BLE
frame contract. Individual opcode handler addresses require disassembly (`FW-U-007`).

## 14. D2

Related strings: `m_gpad_mode`, `USER_CMD_SYNC_GPAD_STU`, `app_key_evnet`, `key_press_long`,
`KEY_EVT_CLEAN_PARING`. Handler address: **not located** (`FW-U-008`).
The project's D2 knowledge (18-byte `A5 12 02` event frames, digital mask bytes 3..6, axes 7..14,
LT byte 15, RT byte 16, RT id 9) remains app/protocol-side knowledge; the firmware-side producer was
not disassembled.

## 15. D6 / D7

Config engine strings: `GAMEPAD_CONFIG_MAX`, `m_gpad_cfg_idx`, `m_gpad_current_defp[%d].att.key`,
`config_num = %d`, `gamepad_setting_check failed, reset setting`, `switchd flash write add=%x, len=%d`,
`flash_uuid:`. The 144-byte config machinery was **not** located at instruction level.
The project's durability rule is unaffected: `STAGED_OK != DURABLE_OK`.

## 16. D8 / macros

Macro engine strings: `GAMEPAD_MACRO_MAX`, `recort start setting=%d, key=%d, max=%d`, key-event and
config-slot strings. Consistent with the established `A4`-fragment + `A4 05 D8 <nfrags+1>` commit
contract. Handler address: **not located** (`FW-U-008`).

## 17. DPI (FC/F6)

The app carries stick/trigger curve strings — `joystick[%d] deadzone=%d %d,turn=%d %d`,
`trigger[%d] deadzone=%d %d,turn=%d`, `sensor curve[%d]: dir, min, curve, speed, y_div_x, smooth`.
No `FC`/`F6` literal was found (expected). Numeric-vs-index DPI remains `UNKNOWN` (`DPI-U-003`),
selector `0x80` remains unexplained.

## 18. F7

Step-related strings only: `xbox info:step=%d,pid=%x,version=%x mac:` and
`... jstep[%d] time=%x,%x` (V41) / `stepj[%d] time=%d` (V2224). **`CONTRADICTED` stands: F7 is not
trigger travel.** Whether the body firmware ever emits the F7 event the app waits for is still
`OPEN` (`FW-U-016`); the strongest negative from the live experiment remains
`F7_NO_REPLY_LINK_HEALTHY`, never `F7_WRITE_ONLY`.

## 19. Motion / gyro

The gyro engine is in the app: `IMU key = 0X%x`, `IMU_TYPE_LEFT`, `IMU_TYPE_RIGHT`, `IMU_MODE`,
`IMU_TRIGGER`, `IMU_TRIGGER`, `imu_cal_start`, `gyro CAL pre data`, `gyro:%d,%d,%d`,
`hw imu init error!`. **IMU model: UNKNOWN** — no part number, no `WHO_AM_I` identifier, no I2C
address table in the string corpus, and no IMU driver in the public AC63 SDK (`FW-U-009`).

## 20. Lighting

No `RGB`/`LED`/`WS2812`/`PWM`/brightness-effect strings found in the string corpus of any image.
Lighting opcode and effect table: `UNKNOWN` from firmware in this pass.

## 21. Persistent storage

JLFS file-level layout is mapped (section 11): `VM` (262,144 B), `BTIF`, `EXIF`, `USERIF`, `key_mac`,
`cfg_tool.bin`. Flash-write path strings: `switchd flash write add=%x, len=%d`, `flash_uuid:`,
`mnt/sdfile/res/md5.bin`. The **internal** structure of VM/EXIF/USERIF and the 144-byte config image
are not decoded (`FW-U-010`).

## 22. OTA

`STRONG EVIDENCE` of the standard JieLi OTA machinery: `ble_ota.bin`, `edr_ota2.bin`,
`ble_app_ota.bin`, `uart_user.bin`, `632N_LE_UPDATE`, `UPDATE_JUMP`, `----RCSP_BLE----`, `*_OTA`,
`>>>write item:%x err:%x`, `>>>exif addr:%x len:%x`, `mnt/sdfile/res/md5.bin`.
The connection to the BUP updater path is `INFERRED` (both are JieLi OTA carriers) — not proven.

## 23. Security / signature / encryption

* **Confidentiality:** the app region is ENC-obfuscated with a per-image **chip key** (`6413` /
  `13462`) read from `isd_config.ini`. Keys were also visible inside the image as `chipkey 190D` /
  `3496` in an earlier decode of the raw JLFS listing.
* **Authenticity:** no signature blob (RSA/ECDSA) was located in the BUP container or at the JLFS
  level. CRC/checksum machinery is present. **Checksum-protected is the current best characterisation;
  claiming or denying secure boot is not supported** (`FW-U-013`).
* Encrypted ≠ signed; the chip key provides confidentiality only.
* No chip key, MAC or link key material is reproduced in public docs beyond what is already plaintext
  in the vendor's own released firmware.

## 24. USB / bootloader

`STRONG EVIDENCE` that the app itself implements **USB host and USB device (XInput)**: `RXCSRH_*`,
`TXCSRH_Error`, `USB_ERR_STALL_BULK_RECEIVE/SEND`, `usbh_socket_en`, `m_xbox_enum_step`,
`usbh_gamepad_ready`, `s_is_connected_to_pc`, `usbd_dev_type`, `usbd_uac_mic_transfer`,
plus `---------app select 24g--------` for 2.4 GHz selection and a full `DEV_TYPE_*` multi-console
table. The updater's own USB bootloader protocol is **not yet reconstructed** (`FW-U-020`).

## 25. Receiver firmware

Dongle firmware is a separate product line: board codes 0x1e (V3600) / 0x17 (V3000), `xt_dongle.c`
source path, `*** services, uuid16:%04x,index:%d ***`, `!!!error_adv_packet:`, app sizes 192,536 /
179,376 B. It shares the JieLi uboot + `cfg_tool.bin` + `p11_code.bin` with the body. The known
receiver identity (`413D:2106`, usage page FF7A, usage 0001) was **not** re-verified here (no USB
interaction permitted tonight).

## 26. Cross-version diff

`app.bin` sizes: **204,564 (V2224) → 223,960 (V32) → 227,440 (V41)** body; **179,376 → 192,536**
dongle. String sets: 1,774 → 1,926 → 1,954 (body).
V41 adds over V2224: USB host/device stack strings, `app select 24g`, the `DEV_TYPE_*` console
descriptor set, BLE connection management (`ble dev connect…`, `ble notify open`), `IMU_TRIGGER`,
`KEY_EVT_CLEAN_PARING`, `USER_CMD_5V_IN`, `ER_DET=%d`. The `stepj` → `jstep` rename is the only
step-related delta.
Instruction-level diff: blocked by missing tooling (`FW-U-021`); block hashing shows 0 % identical
16 KiB blocks between any two body builds.

## 27. Hardware-ownership conclusion

`STRONG EVIDENCE` that **one JieLi AC6321A is the main application MCU**: the decrypted app.bin
contains the frame dispatcher, config engine, macro engine, stick/trigger curve model, gyro engine,
flash-write path, USB host+device stack, 2.4 GHz selection, multi-console conversion, and the vendor
identity (`ZIKWAY`, `ZJ-XT*`) — not a thin BLE/OTA bridge. Whether a secondary MCU exists
(RF front-end or sensor hub) is **neither proven nor excluded** (`FW-U-014`).

## 28. Unresolved questions

See `results/reconciliation/firmware-unknown-ledger.{json,md}` (21 entries). Highest priority:
`FW-U-021` (BD19/q32s disassembler → symbol map), then `FW-U-007/008` (handler locations),
`FW-U-012/020` (updater + bootloader protocol), `FW-U-013` (verification path).

## 29. Future hardware experiments (all DEFERRED — nothing was done tonight)

1. Guarded **read-only** F7 listen experiment (already prepared in the app-side pass) to settle
   `FW-U-016`.
2. USB enumeration of the real unit to confirm the USB host/device roles and the dongle identity.
3. Board-level inspection for a possible second MCU (UART TX-A/TX-B) to settle `FW-U-014`.
4. Flash read-back of VM/EXIF/USERIF to validate the storage model (`FW-U-010`).

---

**Bottom line:** the firmware ecosystem is fully unpacked offline — BUP container decoded, JieLi
AC632N/AC6321A JLFS images extracted and **decrypted**, all seven `app.bin` recovered, and the
vendor's own debug strings give a detailed picture of the application (dispatcher, config, macro,
curves, gyro, USB, 2.4G, multi-console). The blocking gap is instruction-level disassembly tooling
for the BD19 core, not the data.

---

## 30. q32s pass (2026-09-28) — firmware code navigation achieved

The instruction-level blocker is gone. The vendor's own disassembler was located and used, so the
V41 body image is disassembled and navigable. Details: `results/final/q32s-reverse-engineering.md`
and `results/final/armorx-firmware-symbol-map.md`.

* Toolchain: JieLi Linux toolchain, LLVM 4.0.1 fork, registered targets `pi32`/`pi32v2`/`q32s`
  (the AC63 SDK's `download.bat` names the same toolchain and its `-address-mask`/`-print-dbg`
  switches, which is what `rom.lst` was produced with).
* Validation: the BD19 ROM reconstructed from `rom.lst` re-disassembles with **9,746/9,746 exact
  matches** (100.0% text, length and branch-target agreement). Reproduced after a second
  extraction of the toolchain archive.
* V41 coverage: 82,944 instructions, 1,416 recovered functions, 4,662 resolved calls,
  879 string references to 759 distinct strings, 69 switch tables (48 at >=0.9 alignment
  confidence). Coverage caveat: the image is decoded linearly from offset 0, so these are
  decode statistics, not a code/data split.
* **Command dispatcher found: `armorx_cmd_dispatch` at `0x1e08772`** — it validates the frame
  (calling the head/length/checksum error printers at 0x1e0701c / 0x1e06e8a / 0x1e070da) and then
  dispatches on the opcode byte with an if/else chain. Recovered entries: 0x2F->0x1e0914a,
  0x70->0x1e093e4, 0xD2->0x1e08d24, 0xD4->0x1e08944 (and 0x1e087ce), 0xD7->0x1e08a68,
  0xF7->0x1e08860, 0xF8->0x1e08b86, 0xF9->0x1e08912, 0xFA->0x1e0898e, 0xFF->0x1e0944e.
  Recorded in `results/firmware/armorx-command-dispatch.{json,md}`.
* The chain does **not** test D6, D8, FC, F6, AB or 0B — a negative result, recorded as such in
  the ledger (FW-U-023). 0B compares live in 0x1e0aff2 (three) and 0x1e0a944 (two).
* F7: the handler exists. It reads the byte after the opcode, only acts on values 0/1, and on
  that path emits a frame with opcode **0xF6** via 0x1e0642c (single call site, inside the F7
  handler) — so the F7 settings path's acknowledgement is an F6 frame, not an F7 reply. This is
  a candidate explanation for the silent live F7 read; it depends on the unresolved base-register
  question FW-U-024 and is therefore graded STRONG EVIDENCE, not proof.
* FC/F6: no FC compare exists in the dispatcher, and F6 appears only as the opcode emitted by the
  F7 path. This **contradicts** the assumption that FC is handled in this dispatcher and is
  recorded as a contradiction, not smoothed over.

---

## §31 - Firmware semantics pass (2026-09-28): parser base, dispatch tables, D6/D7/D8

This section records the second firmware-semantics pass. All addresses are from the decrypted V41
`app.bin` (base `0x01E00000`). Nothing here required hardware.

### 31.1 FW-U-024 CLOSED - the handler base register

`armorx_cmd_dispatch` (0x1e08772) resolves its arguments in the prologue:

```
1e08778: r13 = r0          ; arg0 -> transport/state context
1e0877e: r9  = r1          ; arg1 -> the frame
1e08792: r1  = b[r9 + 0x2] ; the opcode, compared against the opcode table below
```

So **r9 = frame start**: `r9+0` = magic (0xA5), `r9+1` = length, `r9+2` = opcode, `r9+3..` = payload.
The highest field read anywhere in the parser is `r9+7`. Consequence: for a **4-byte frame the
payload byte at `r9+3` is the checksum byte** - the F7 handler's `b[r9+3]` read is a payload read
that, for `A5 04 F7 A0`, reads the checksum `0xA0`.

### 31.2 DISPATCH CORRECTION - the parser uses jump tables, not an if/else chain

The previous pass's compare-only extractor could not see this. The parser splits the opcode into
four ranges and uses **two `tbh` jump tables** plus one chain plus one sub-table:

| opcode range | mechanism |
|---|---|
| 0x0B..0x1B | `tbh` table at `0x1e089c4` (17 cases) |
| 0x2F..0xE0 | if/else chain at `0x1e08d1a` (0x2F, 0x70, 0xD2, 0xD4, 0xD7, 0xF7, 0xF8, 0xF9, 0xFA) |
| 0xE1..0xE5 | `tbh` table at `0x1e08a04` (5 cases) |
| 0xE6..0xFF | `0x1e08e8c` accepts **only 0xEF**; everything else -> default `0x1e08ff2` |
| (second level) | `tbh` table at `0x1e09060` dispatches **0xD4..0xD9** |

Table entry encoding, verified on both tables: `target = table_start + entry*2`, `table_start` being
the instruction immediately after the `tbh`. All four parser tables resolve with **100% of targets
on instruction boundaries inside the parser**.

### 31.3 Handlers recovered in this pass

| opcode | handler | semantics | grade |
|---|---|---|---|
| 0x0B | `0x1e089e8` | status query; loads the constant 0x32 into a 1-byte reply (`r1 = 0x0B` in the handler confirms the case mapping) | STRONG EVIDENCE |
| 0x19 | `0x1e08d24` | state set; shares the D2 block, writes `state+0x11` (D2 writes `state+0x10`) | STRONG EVIDENCE |
| 0x05 | `0x1e08e62`+`0x1e08e78` | **factory/diagnostic** sub-dispatch on `payload[0] & 0x7F` (6 cases -> 0x1e0701c, 0x1e070da, 0x1e07156, 0x1e0710a, 0x1e04a92) | STRONG EVIDENCE |
| 0xD6 | `0x1e0921c` | reads `[state+0x1b0]` and replies with the big-endian 16-bit field at +2..3 | STRONG EVIDENCE |
| 0xD7 | `0x1e09232` | **config write**: `len-4` payload bytes -> 144-byte (0x90) staging at `sp+560`, validated by `0x1e0566a`, then a 4-iteration loop calling the record writer `0x1e05c66`, finalised by `0x1e069c2`/`0x1e059a2` | PROVEN STATIC |
| 0xD8 | `0x1e0928c` | **single 220-byte (0xDC) record write**, validated by `0x1e0566a`, index = `payload[2]`, into the array at `[state+0x1b8]` with stride 0xDC | PROVEN STATIC |
| 0xD9 | `0x1e09346` | **record read** (index = `payload[0]`, < 4), replies with 0xD9 | PROVEN STATIC |

### 31.4 The 144-byte config is stored as 220-byte records

`D7` stages **0x90 = 144 bytes** and then writes through `0x1e05c66`, which builds a **0xDC = 220-byte
record**. `0x1e0566a` is the shared record-header validator: length = big-endian 16-bit at `[2..3]`
(rejected if < 4 or > max), then it computes `0x1e05628(ptr+2, len-2)` and compares against the
big-endian 16-bit value at `[0..1]`. `0x1e05628` is a reflected (LSB-first) nibble-table CRC-16 with
init `0xFFFF` - i.e. the **CRC-16/MODBUS** family that the live work independently validated on the
144-byte config (stored `0x2c40` = computed `0x2c40` on the baseline, `0xbfd4` on the mutant).

### 31.5 F7 silence explained (still NOT called write-only)

With `r9` settled, the F7 handler `0x1e08860` reads `b[r9+3]` = **payload[0]**. It stores that byte
at `state+0x150` and continues to the builder `0x1e0642c` (an F6 emission path) only for the values
`0` and `1`. A live `A5 04 F7 A0` carries **no payload byte**, so the handler reads the checksum
`0xA0` - neither 0 nor 1 - stores it, and produces no reply. That is STRONG EVIDENCE for the
observed silence and is **not** promoted to `F7_WRITE_ONLY`.

### 31.6 Corrections and new unknowns (not buried)

* **FC and F6 are not in any extracted dispatch table**, and `0x1e08e8c` accepts only `0xEF` above
  0xE5 - so both fall to the default handler `0x1e08ff2`. The assumed location of the FC/F6 DPI
  handlers is **CONTRADICTED**; they must be reached from another entry point.
* **FW-U-029 (new, high):** firmware `0xD6` returns a single 16-bit value, which contradicts the
  live-observed 144-byte D6 read. The opcode attribution of that live read must be re-checked.
* **FW-U-028 (new):** the CRC routine loads its table base from the immediate `0x1e29900`, but the
  CRC-16/MODBUS nibble table occurs exactly once in the image at `0x1e297e0` (delta 0x120), and the
  bytes at `0x1e29900` are the assert string `P33 SYS SOFT RESET : P3_PR_PWR[4]=1`.
* **FW-U-030 (new, low):** the 0x0B handler's constant `0x32` vs the live reply payload `0x30`.

### 31.7 Tooling

`tools/q32s/q32s_tables.py` recovers range-gated `tbh`/`tbb` tables (the extractor now walks through
the index-scaling instruction to the bounds check and names the raw opcode register behind the
rebase). Image-wide it finds **102 tables, 38 fully aligned** - a candidate pool
for other dispatchers beyond the command parser. `tools/q32s/q32s_dispatch_full.py` builds the merged
dispatch model (34 routes) and `tools/firmware/fw_ledger_report.py` renders the
unknown ledger deterministically from its JSON.

---

## §32 - Protocol family reconciliation (2026-09-28): A5/A4 are ONE opcode space

### 32.1 The contradiction is resolved - there was never a second namespace

The earlier "A5/D6 returns 16 bits" versus "live D6 read 144 bytes" contradiction is closed, and the
live label was right. `A5` and `A4` are not independent command namespaces: they are the two
**framing modes** of a single opcode space.

Raw wire evidence, `results/experiments/physical-20260927-170455-noop-d7/raw-tx-rx.log`:

```
TX a5040bb4                          A5, 4 bytes      status query
RX a5050b30e5                        A5, 5 bytes      status reply
TX a414d7012c40009033ff000000000000000000be   A4, 20 bytes, ordinal 01
TX a414d702..  a414d703.. ... a414d709       A4, 20 bytes, ordinals 02..09
TX a40ed70a010d191a1b1c1d1e1f65      A4, 14 bytes, ordinal 0a   config write
RX a505d70081                        A5, 5 bytes      acknowledgement
TX a504d67f                          A5, 4 bytes      config read (0x7f = sum8 of a5+04+d6)
RX a414d6012c40...bd ... a40ed60a...64        A4, ordinals 01..0a  config response
```

The ten `A4/D6` payloads reassemble to **144 bytes** whose SHA-256 is
`bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6` - the project's durable config
baseline, an exact match. All 24 frames satisfy the frame checksum (sum8).

### 32.2 Firmware proof of the framing rule

`0x1e05dc0` is the frame builder and it decides the magic by SIZE:

```
1e05dc4: r2 = 0xa5 ; b[r4+0] = 0xA5            default: single frame
1e05dcc: r2 = h[r1+0x4]                        payload length from the descriptor
1e05dce: r3 = capacity - 4
1e05dd2: ifs (r2 <= r3) goto <single-frame tail>
1e05dd6: r2 = 0xa4 ; b[r4+0] = 0xA4            does not fit -> fragmented
1e05dda-1e05de4: nfrags = (len + 2) / (capacity - 5)
```

For 144 bytes in a 20-byte buffer: `(144+2)/15 = 9.73 -> 10 fragments`, i.e. `9 x 15 + 1 x 9 = 144` -
exactly the observed wire shape. The `A5/D6` handler `0x1e0921c` extracts the record's big-endian
**length** field (bytes 2..3 = `0x0090` = 144) from the descriptor at `[state+0x1b0]`; the builder then
streams the whole 144-byte record. So the handler is a record-read, not a bare 16-bit query.

### 32.3 The frame checksum (FW-U-025, frame half) - `0x1e05dae`

```
1e05db2: r3 = b[r0 ++= 1]
1e05db6: r2 += r3
1e05dbc: r0 = r2.l (u)
```

Plain **sum8**, distinct from the record CRC-16/MODBUS at `0x1e05628`. Verified against every frame
in the log. The two mechanisms must never be conflated.

### 32.4 Response path and the FF echo (explains A5/FC)

`0x1e09426` (reached by D6/D7/D8/D9) is `0x1e0642c` (post a response entry, else send directly via
`0x1e06418`) followed by `0x1fd3d0` (transport send). It then emits an **A5/FF frame whose payload is
the request's opcode byte** (`0x1e09446: r2 = r9 + 2`, `0x1e0944a: r1 = 0xff`) and, for a non-FF
request, jumps to the shared tail `0x1e08e5a`. That is exactly live `A5 05 FC 80 26 -> A5 05 FF FC A5`,
and the local corpus confirms one FF echo per FC request (2 and 2).

### 32.5 RX has no magic check

A whole-image search finds **no compare against 0xA4, 0xA5 or 0xAB**, so the RX parser `0x1e08772`
accepts either framing. The magic is decided only on the transmit side (`0x1e064b4` checks
`b[frame+0] == 0xA5`, `0x1e064ce/0x1e064d4` accept `0xA4`, `0x1e064da` reads the ordinal at `frame[3]`).

### 32.6 Retired false positives (corrections, not buried)

* `0x1e0aff2` and `0x1e0a944` were carried in the ledger as "0B compare hotspots". They are
  **not** protocol dispatchers: `0x1e0a97c`/`0x1e0a98c` compute `r0 = r9 | 1 ; if (r0 != 0xb)`, a test
  for the value pair **{0x0A, 0x0B}**, and `0x1e0a944` is a `tbb` dispatch on an index <= 6 selecting
  string pointers; `0x1e0aff2` is a 32-iteration mask-table builder over `r15+0x124`.
* `tools/ble/parse_btsnoop.py` initially used a 20-byte record header and mis-decoded direction and
  timestamp; btmon writes the 24-byte shape `orig, incl, flags, drops, ts`.

---

## §33 - Config persistence chain (2026-09-28): D7 -> record writer -> out-of-image NV API

### 33.1 The chain, with the instruction that shows each link

| address | role | key instruction |
|---|---|---|
| `0x1e09232` | D7 handler: stage + slot loop | `1e09240` copy, `1e09248` validate(0x90), `1e0926c` record write |
| `0x1e06998` | slot -> digital-bit | `1e069a6` masks `0x7800000` = bits **23..26** = M1..M4 |
| `0x1e05c66` | record writer | `1e05c78` `r4 += r5*0xDC`, `1e05c98` CRC-16 over 8 bytes, `1e05cae` `[0x4850+0x1b4] = 3` |
| `0x1e069c2` | save | `1e069d4` tail-call `0x3003ec(descriptor, mode, 0x90)` |
| `0x1e059a2` | slot select + reload | `1e059b0` `index*0x400`, `1e059ba` `+0x44`, `1e059c4` -> `[0x4850+0x1b0]` |
| `0x1e0580c` | slot validate | `1e05816` `0x1e0566a(descriptor, 0x90)`; invalid -> `1e05826` defaults `0x1e056b6` |

### 33.2 Storage model

The active config descriptor is `0x3120 + index*0x400 + 0x44`, with **index clamped to 0..2 - three
slots of 1024 bytes** - and it is stored at `[0x4850+0x1b0]`, the very pointer the D6 handler reads.
Record stride is `0xDC` (220) in the array at `[0x4850+0x1b8]`; the config record itself is
`0x90` (144) with the `[BE16 CRC][BE16 length]` header. The active slot index is kept at
`[0x4850+0x14]` and a write sets `[0x4850+0x1b4] = 3`.

### 33.3 STAGED_OK is now PROVEN; DURABLE_OK is not

**PROVEN STATIC:** the readback path reads the descriptor at `[0x4850+0x1b0]`, i.e. the RAM/VM
shadow at `0x3120 + index*0x400 + 0x44`. A D7 write updates that shadow and then re-selects and
reloads the slot (`0x1e059a2` -> `0x1e0580c`), so an immediate D6 readback returns the new bytes with
**no flash commit involved**. That is exactly the observed STAGED_OK.

**Not resolvable statically:** the commit is the library call `0x3003ec`, the only link in the chain
that leaves the app image. Its code is in no artifact we hold - `app.bin` ends at `0x01E37870`, the
SDK `rom.lst` covers only `0x100000-0x106fff`, `cpu/bd19/maskrom_stubs.ld` names only `0x106xxx`
symbols, and `p11_code.bin` is 4096 bytes. So whether `0x3003ec` writes flash synchronously or leaves
it to a VM flush **cannot be decided from the material on disk** (recorded as FW-U-032, and the flush
trigger as FW-U-033). No vendor API name is invented for it.

### 33.4 Corrections

* The claim that config bytes **112..115** gate which records D7 rewrites is **wrong**. `0x1e06998`
  maps slot *i* to digital bit `23+i`, and the handler then reads `staging[0x70 + bit]`, i.e. config
  bytes **135..138**.
* `0x1e0aff2` is a **13,346-byte** function that references `switchd flash write add=%x, len=%d`. The
  earlier note calling it a mask-table builder was incomplete (it is still not a protocol
  dispatcher, which was the point of the retirement).
* `0x1e12db4` was labelled "IMU naming" in an earlier pass; by string xref it is the
  **`gamepad_setting_check failed, reset setting`** handler.

---

## §34 - Persistence closure attempt (2026-09-28): the boundary, measured

**0x3003ec has exactly one call site in the entire 227,440-byte image** - `0x1e069d4` inside
`0x1e069c2`. There is no second caller, so there is no length/buffer/mode variation anywhere in this
firmware to widen the ABI from. What is proven is the call shape: `r0` = descriptor
`[0x4850+0x1b0]`, `r1` = mode byte passed through from the D7 handler, `r2` = `0x90` (144).

The library it lives in is large: **1,324 call sites to 1,300 distinct targets** across
`0x1f0000-0x31ffff`, with only the standard ones identified (`0x301148` memset in the record writer,
`0x306b64/0x306c1a` at startup, `0x300970/0x30095a` in the builder). None of those bytes are in
`app.bin`, the SDK `rom.lst`, `maskrom_stubs.ld` or `p11_code.bin`.

**Dirty-flag xrefs.** The only proven writer is `0x1e05cae` (`[r0+0x1b4] = 3`, inside the record
writer, right after the header CRC is stored). The only proven reader is `0x1e0684c`
(`r0 = [r5+0x1b4]`, with `r5 = 0x4850` loaded two instructions earlier), which ORs it with
`[r5+0x1c4]` and early-outs at `0x1e06856`.

**Caveat that matters.** `0x1e06842` - the reader - references `dev_type` diagnostics and is called
from the dispatcher, from three functions that reference `usbh_gamepad_ready= %d, usbh_gamepadp = %p`
(`0x1e096b4`, `0x1e09ad4`, `0x1e09ce0`), and from `0x1e0aff2`. That places `state+0x1b4` on USB-host
gamepad report paths. *Calling value 3 a "dirty level" or "pending record count" is not supported by
the code read so far*, and the flag may not be the BLE config dirty bit at all.

**No flush trigger was found.** No timer, task, idle, power or disconnect hook reaching the shadow
appeared. FW-U-033 stays open; FW-U-032 is now `DEFERRED_REQUIRES_LIBRARY_BINARY` - behaviour proven
to the call boundary, identity unavailable - which is a stronger and more honest classification than
"UNKNOWN".

---

## §35 - The D2 report engine (2026-09-28): builder, payload layout and send gate

The `A5 12 02` frame is built at **`0x1e0db0c`** with opcode `0x02` and a **14-byte payload**; the frame
length byte is `0x12` = 14 + 4. A second `0x02` variant with a **28-byte payload** is built at
`0x1e0db5e`. Both live inside the 13,346-byte manager `0x1e0aff2`.

**The payload layout is derived, not assumed.** `0x1e07464` serialises the payload field by field:
`rev8` on the u32 at `+0x00`, then `rev8`+`>>16` on the s16 values at `+0x04`, `+0x06`, `+0x08`,
`+0x0a`, then `0x1e07444` at `+0x0e`. That is `{u32 digital mask, s16 x4, LT/RT}` = 4+8+1+1 = 14,
which reproduces the live field map ([3..6] mask, [7..14] axes, [15] LT, [16] RT) from the code.

**Send gate.** `0x1e0dae6` reads `b[cfg+0x10]` and skips the report entirely when it is zero;
`0x1e0dae0` sets a repeat counter `b[cfg+0x3a] = 0x64` (100) and `0x1e0db1c`..`0x1e0db2c` decrement it
while jumping back to re-send; `0x1e0db38` requires `b[cfg+0x11] != 0` for the 28-byte variant.

**D2 handler.** `0x1e08d24` writes `b[r8+0x10]`, or `b[r8+0x11]` when the selector is `0x19`. So D2 is
not merely on/off - it selects between two report variants, and the two gates above are exactly those
two flags.

**Still open:** the trigger side. Nothing here explains yet why idle produces zero frames while a
button press produces them; `0x1e0aff2` is reached from `0x1e0a9b4`, which was not traced.
