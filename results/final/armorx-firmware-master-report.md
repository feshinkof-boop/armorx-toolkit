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
Instruction-level ISA identification was **not achieved**: no BD19/q32s disassembler was available
offline (`FW-U-021`). ARM/Thumb, RISC-V and 8051 are ruled out by the SDK core layout and entry
convention.

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
