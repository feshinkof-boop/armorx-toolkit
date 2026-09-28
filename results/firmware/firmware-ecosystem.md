# ArmorX Pro firmware ecosystem — component identification, JieLi evidence, cross-version

Offline/static analysis of four operator-supplied packages. No hardware was touched.
Evidence grades: `PROVEN` / `STRONG EVIDENCE` / `INFERRED` / `UNKNOWN` / `CONTRADICTED`.

## 1. Packages

| # | original file | size | SHA-256 | format |
|---|---|---|---|---|
| 1 | `战甲Xpro 固件V41.zip` | 36,528,812 | `2554f7eba6df55d6748fabd414ee9c5219bc171d1c5a595c000e890a1b95a77c` | ZIP (store) |
| 2 | `战甲Xpro 固件V32 20220815.rar` | 3,364,439 | see `originals-inventory.json` | RAR5 |
| 3 | `ArmorX-Pro-Firmware-V2224.bup` | 970,968 | see `originals-inventory.json` | BUP |
| 4 | `Firmware ArmorX-Pro V41.rar` | 6,070,709 | see `originals-inventory.json` | RAR5 |

Originals are preserved read-only under `research/firmware/2026-09-28/originals/`.

## 2. Package contents

**Chinese V41 zip (8 files + APK):** `01 固件升级 请勿关机.txt`, `01战甲X Pro固件-V41.bup` (2,126,734),
`01接收器固件-V3600-dongle.bup` (1,847,656), `BIGBIG_WON_2.22.1226.apk` (28,032,675),
`BTUpgrade_V1.9/` (7 files: `BUpgrade.exe`, `BTUpgrade.dll`, `BTUpgrade_HX.dll`, `Devices.dll`,
`Skin.dll`, `Upgrade.dll`, `USBUpgrade.dll`, `bugrade.log`), `更新日志 APP版本.txt`,
`更新日志 固件版本.txt`.

**International V41 rar:** `Firmware ArmorX-Pro V41.bup` (2,126,734), `Firmware USB dongle V3600.bup`
(1,847,656), `upgrade log-Firmware.txt`, `BTUpgrade_V1.9/` (same 7 files, byte-identical).

**V32 rar:** `墨将升级工具BUpgrade v1.1(log).7z` (1,668,629 — nested archive, older updater),
`Pro版固件-战甲 V32/战甲pro固件V32.bup` (1,048,972), `Pro版固件-战甲 V32/接收器固件V3000-dongle.bup`
(866,148), two Chinese change-log text files.

## 3. BUP → flash-image → JieLi unpack

`bup` (see `bup-format.md`) → raw flash image → JieLi JLFS image (`uboot.boot`, `isd_config.ini`,
`app_dir_head`, `VM`, `BTIF`, `EXIF`, `USERIF`, `key_mac`).

```text
.format / jl-new-fw
chip ................. AC632N            (unpacker-reported chip name)
PID .................. AC632N_TRANS      (plaintext string inside the image)
flash size ........... 0x07F000 (520,192 B)
FS version ........... 11
entry-point .......... 31,457,568 = 0x01E00120   → app base 0x01E00000
base-offset .......... 0
spl .................. top/uboot.boot (compressed)
app-files ............ files/app.bin, files/cfg_tool.bin
res-files ............ files/p11_code.bin
```

The app region is **ENC-obfuscated with a per-image chip key** read from `isd_config.ini`; the
unpacker decrypts it. Plaintext `app.bin` is therefore recovered **offline** — `DECRYPTED: YES`.

## 4. Images extracted (all seven payloads)

| package | slot | image name | image bytes | app.bin bytes | app.bin SHA-256 (head) | chip key |
|---|---|---|---|---|---|---|
| CN/US/V41 body | 0 | `XT_XBOX_update_s_v41_20230208.ufw` | 1,124,288 | 227,440 | `302a700be0…` | 6413 |
| V41 body | 1 | `XT_XBOX_update_s_v41_20230209.ufw` | 1,124,288 | 227,440 | `302a700be0…` | 13462 |
| V3600 dongle | 0 | `XT_DONGLE_update_v36_20221116.ufw` | 989,120 | 192,536 | `1e55990417…` | 6413 |
| V3600 dongle | 1 | `XT_DONGLE_updateHJX_v36_20221116.ufw` | 989,120 | 192,536 | `1e55990417…` | 13462 |
| V32 body | 0 | `null.bin` (slot B declares `XT_XBOX_update_s_v32_20220806.ufw`) | 1,109,440 | 223,960 | `fef5f9e615…` | 6413 |
| V3000 dongle | 0 | `null.bin` (slot B declares `XT_DONGLE_update_v30_20220809.ufw`) | 937,920 | 179,376 | `bc6a8b823b…` | 6413 |
| V2224 | 0 | `1.bin` (slot B declares `XT_XBOX_update_s_v24_20220613.ufw`) | 1,037,760 | 204,564 | `59e9f9755d…` | 6413 |

**Why two slots?** Both slots of the V41 body pair are the *same application* (`app.bin` SHA-256
identical) but carry **different `isd_config.ini` chip keys** (6413 vs 13462) — the pair is a
production-line duplicate for two chip-key variants, not two different builds.
`302a700be0…` vs the slot-1 image's 80-%-different raw bytes are explained exactly by ENC: same
plaintext, different key.

**Shared across all products:** `uboot.boot` (`a64171c3cf41…`), `cfg_tool.bin` (`0ccc2fd57959…`) and
`p11_code.bin` (`d37e34cc8200…`) are **byte-identical in every package, body and dongle alike** —
one JieLi uboot + one config tool for the whole family; only `app.bin` + `isd_config.ini` differ.

## 5. JieLi evidence (PROVEN)

* `AC632N` chip name, `AC632N_TRANS` PID, `JLBTSDKflash`, `UPDATE_JUMP`, `uboot.boot`,
  `isd_config.ini`, `app_dir_head`, `VM`, `BTIF`, `EXIF`, `USERIF`, `key_mac`
* OTA image names: `ble_ota.bin`, `edr_ota2.bin`, `ble_app_ota.bin`, `uart_user.bin`
* BT stack modules: `btctrler`, `btstack`, `H4_Controller`, `link_layer`, `632N_LE_UPDATE`
* Format parses with the public **JieLi tooling** (`jl-misctools/fwunpack_newfw.py`): `format: jl-new-fw`
* Board source path in the app: `../../../../apps/hid/board/bd19/board_ac6321a.c`

## 6. CPU / ISA

* `STRONG EVIDENCE` the application core is **JieLi AC6321A** (board file `board_ac6321a.c`, chip name
  `AC632N`, PID `AC632N_TRANS`, `bd19` board directory).
* The AC63 SDK ships per-core toolchains under `cpu/{bd19,bd29,br23,br25,br30,br34}` and board configs
  named `board_ac632n_demo_cfg.h` / `board_ac6321a_demo_cfg.h` → **AC632N/AC6321A are BD19-family**.
* Instruction set: **q32s (`ELF32-q32s`)** — `STRONG EVIDENCE`. The SDK's `cpu/bd19/tools/rom.lst`
  (full BD19 ROM disassembly, 16/32/48-bit instruction lengths) supplies 48 opcode prefixes that
  occur **≈133× more often** in every `app.bin` than in random data. No q32s *decoder* exists
  offline yet, so this is an ISA identification, not a disassembly
  (`results/firmware/isa-identification.md`, ledger `FW-U-021`).

## 7. What the application contains (string evidence, PROVEN)

Source-tree strings recovered from the decrypted `app.bin`:

* `../../../../user/app/game_pade/xt_xbox_slave.c` — the ArmorX application source
* `../../../../apps/hid/board/bd19/board_ac6321a.c`
* `../../../../apps/hid/modules/bt/ble_multi.c`
* `../../../../apps/common/third_party_profile/jieli/gatt_common/le_gatt_common.c`

Protocol / behaviour strings:

* `out cmd=%x,%x pa=%x, len=%d:`, `in cmd=%x,%x, len=%d:`, `unsupport cmd: 0x%x`,
  `cmd head err %x %x`, `cmd len err %x`, `cmd sum err %x %x` → **a real frame dispatcher with
  head/length/checksum validation exists in firmware**
* `xbox cmd in/out`, `xbox info:step=%d,pid=%x,version=%x mac:` → host-side XBOX protocol layer
* `m_gpad_mode`, `m_gpad_cfg_idx`, `m_gpad_current_defp[%d].att.key`, `GAMEPAD_CONFIG_MAX`,
  `GAMEPAD_MACRO_MAX`, `recort start setting=%d, key=%d, max=%d` → **config + macro engine**
* `joystick[%d] deadzone=%d %d,turn=%d %d`, `trigger[%d] deadzone=%d %d,turn=%d`,
  `sensor curve[%d]: dir, min, curve, speed, y_div_x, smooth` → **stick/trigger curve model**
* `IMU key = 0X%x`, `IMU_TYPE_LEFT`, `IMU_TYPE_RIGHT`, `IMU_MODE`, `IMU_TRIGGER`, `imu_cal_start`,
  `gyro:%d,%d,%d`, `hw imu init error!` → **gyro engine**; no sensor part number anywhere (UNKNOWN)
* `switchd flash write add=%x, len=%d`, `flash_uuid:`, `link_key`, `mac:`, `cfg_tool.bin`, `btif`, `VM`
* `---RXCSRH_DataError`, `TXCSRH_Error`, `---USB_ERR_STALL_BULK_RECEIVE/SEND`, `usbh_socket_en`,
  `m_xbox_enum_step`, `usbh_gamepad_ready` → **USB host + USB device (XInput) in the app**
* `---------app select 24g--------` → **2.4 GHz mode selection**
* `DEV_TYPE_PS3 / PS4 / PS4 PARTY3 / PS4 S1 / PS5 / SWITCH / X360 / XBOX ONE / XBOX SERIESX` →
  multi-console conversion
* `USER_CMD_SYNC_GPAD_STU`, `USER_CMD_SYNC_BAT_STU`, `CMD_TEST_MODE`, `USER_CMD_5V_IN`,
  `app_bt_debond`, `ble notify open`, `[APP_ZK]P3_PINR_CON` (`ZK` = ZIKWAY vendor tag)
* `ZIKWAY`, `ZJ-XT*`, `2741`, powers-of-two keymask table (`0x80,0x10,0x08,0x40,0x20,0x02,0x04,0x01`)
  in the plaintext data region around `0x23470`
* `----RCSP_BLE----`, `*_OTA`, `>>>write item:%x err:%x`, `>>>exif addr:%x len:%x`,
  `mnt/sdfile/res/md5.bin` → **JieLi RCSP/OTA implementation with debug strings**

### Absence that must be read carefully

The literal byte sequences of our BLE frames (`A5 04 0B B4`, `A5 12 02`, `A5 05 D2 …`) do **not**
appear in `app.bin`. That is expected for compiled code (constants are built in registers or live in
tables) and is **not** evidence of absence — see `firmware-unknown-ledger.json`.

## 8. Cross-version comparison (string-set level)

| firmware | app.bin bytes | strings | relation to V41 |
|---|---|---|---|
| V41 body | 227,440 | 1,954 | baseline |
| V32 body | 223,960 | 1,926 | −82 V41-only strings |
| V2224 | 204,564 | 1,774 | −180 V41-only strings |
| V3600 dongle | 192,536 | 1,599 | −355 |
| V3000 dongle | 179,376 | 1,538 | −416 |

Block-level hashing shows **0 % of 16 KiB blocks identical** between any body builds — the code is
dense and every build differs throughout (expected without an instruction-level diff tool).

**V41-only strings that constitute feature evidence** (not present in V32 or V2224):

* `---------app select 24g--------` and the `24g` select path
* `---RXCSRH_DataError`, `---RXCSRH_Error Request In again`, `---USB_ERR_STALL_BULK_RECEIVE`,
  `TXCSRH_Error`, `USB_ERR_STALL_BULK_SEND`, `usbh_socket_en`, `m_xbox_enum_step`,
  `usbh_gamepad_ready`, `[1mep in=%d close`, `[1mep out=%d close`, `[1musbd_uac_mic_transfer`,
  `[1ms_is_connected_to_pc`
* `DEV_TYPE_*` table entries (`X360`, `XBOX ONE`, `XBOX SERIESX`, `SWITCH`, `PS3/PS4/PS5` descriptors)
* `... jstep[%d] time=%x,%x` (V2224 spells it `stepj[%d] time=%d`)
* `IMU_TRIGGER`, `KEY_EVT_CLEAN_PARING`, `USER_CMD_5V_IN`, `ER_DET=%d`, `[1mauto det dev = %d`
* `ble dev connect...`, `ble disconnected...`, `ble notify open`

**Reading:** between V2224 and V41 the body firmware gained a **USB host/device stack, 2.4 GHz
selection, console descriptor/DEV_TYPE handling and BLE connection-management paths**. The name change
`stepj` → `jstep` plus the `step=` field in the XBOX info line are the only step-related strings; the
step-length feature itself is not newly introduced in V41 at string level.

## 9. Hardware ownership (project question)

`STRONG EVIDENCE` that **one JieLi AC6321A runs most of the ArmorX logic**:

* the decrypted `app.bin` is a full application (227 KB) with the config engine, macro engine,
  stick/trigger curve model, gyro handling and flash-write path, not a thin BLE bridge;
* it contains USB host **and** USB device/XInput code, 2.4 GHz selection and multi-console protocol
  conversion;
* the vendor identity (`ZIKWAY`, `ZJ-XT*`) and the `user/app/game_pade/xt_xbox_slave.c` application
  path are inside this image.

Not proven: whether a *second* MCU exists for RF front-end or sensors. The dongle firmware is a
separate product (`xt_dongle.c`, `1e55990417…`) that links the same JieLi uboot and config tool.

## 10. Unproven / open

* Instruction-level disassembly (no BD19/q32s disassembler offline) — `DEFERRED_REQUIRES_NEW_TOOLING`
* Location of the D2/D6/D7/D8/FC/F7/AB handlers in `app.bin` — see the ledger
* IMU part number — no sensor string or `WHO_AM_I` table found; `UNKNOWN`
* Whether firmware authenticity is cryptographically verified — see `firmware-unknown-ledger.json`
