# ArmorX firmware unknown ledger

_generated 2026-09-28 — scope: ArmorX Pro firmware/updater ecosystem (four operator packages), offline/static only_

| id | question | status | priority |
|---|---|---|---|
| `FW-U-001` | Why is the Chinese V41 package 34.8 MB while the international one is 5.8 MB? | **RESOLVED** | high |
| `FW-U-002` | Are the actual V41 firmware payload bytes identical between the CN and international packages? | **RESOLVED** | high |
| `FW-U-003` | What exactly is inside V2224.bup / the V32 / V41 / dongle packages? | **RESOLVED** | high |
| `FW-U-004` | Can the official updater decrypt/decompress the BUP? | **PARTIALLY_RESOLVED** | high |
| `FW-U-005` | Is the ArmorX firmware JieLi .ufw / jl_isd.fw / JLFS or another JieLi format? | **RESOLVED** | high |
| `FW-U-006` | Which image runs on AC6321A? | **RESOLVED** | high |
| `FW-U-007` | Does that image contain our known A5/A4/AB protocol? | **PARTIALLY_RESOLVED** | high |
| `FW-U-008` | Can D2/D6/D7/D8/FC/F6/F7/AB handlers be located in firmware? | **DEFERRED_REQUIRES_NEW_TOOLING** | high |
| `FW-U-009` | Does the firmware reveal the IMU model? | **UNKNOWN** | medium |
| `FW-U-010` | Does the firmware reveal persistent configuration / macro storage? | **PARTIALLY_RESOLVED** | high |
| `FW-U-011` | Can V2224/V32/V41 binary diff identify when major ArmorX features were added? | **PARTIALLY_RESOLVED** | medium |
| `FW-U-012` | Does the updater reveal a standard JieLi bootloader protocol? | **OPEN** | high |
| `FW-U-013` | Is firmware authenticity verified cryptographically or merely checksum-protected? | **PARTIALLY_RESOLVED** | high |
| `FW-U-014` | Is there one MCU doing most of the ArmorX logic, or is AC6321A only a communications coprocessor? | **PARTIALLY_RESOLVED** | high |
| `FW-U-015` | Why do the V41 / V3600 packages carry two .ufw sub-images? | **RESOLVED** | medium |
| `FW-U-016` | Is the F7 step-length value ever produced by the firmware? | **OPEN** | high |
| `FW-U-017` | Is there receiver/F20 (dongle) firmware in the packages, and is it separate from body firmware? | **RESOLVED** | high |
| `FW-U-018` | What is the meaning of the isd_config.ini chip key (6413 / 13462)? | **PARTIALLY_RESOLVED** | low |
| `FW-U-019` | Do the V41 USB-host/2.4G strings mean the controller can host USB devices? | **PARTIALLY_RESOLVED** | medium |
| `FW-U-020` | Is the updater's transfer protocol JieLi UBOOT or a custom USB protocol? | **OPEN** | high |
| `FW-U-021` | Which instruction set does the AC6321A app use and how do we disassemble it? | **DEFERRED_REQUIRES_NEW_TOOLING** | critical |

---

## FW-U-001 — Why is the Chinese V41 package 34.8 MB while the international one is 5.8 MB?

**Status:** RESOLVED  |  **Priority:** high

**Answer:** The Chinese ZIP bundles the 28,032,675-byte Android app BIGBIG_WON_2.22.1226.apk plus Chinese-only change-log text files; the international RAR does not. All firmware payloads and all seven BTUpgrade_V1.9 files are byte-identical.

**Evidence:**
* results/firmware/v41-chinese-vs-international.md
* research/firmware/2026-09-28/v41-chinese-vs-international.json

**Ruled out:**
* different firmware payload
* different compression
* extra drivers/DLLs
* different updater version

## FW-U-002 — Are the actual V41 firmware payload bytes identical between the CN and international packages?

**Status:** RESOLVED  |  **Priority:** high

**Answer:** YES

**Evidence:**
* same SHA-256 for 01战甲X Pro固件-V41.bup and Firmware ArmorX-Pro V41.bup; same for both V3600 dongle .bup files; all 7 updater files identical

## FW-U-003 — What exactly is inside V2224.bup / the V32 / V41 / dongle packages?

**Status:** RESOLVED  |  **Priority:** high

**Answer:** BUP = 'BigBigWon Upgrade Pack' header + one or two sub-images, each stored as a sequence of independent zlib blocks of 32,768 B preceded by (compressed,uncompressed) u32 records. Decompressed result is a raw JieLi JLFS flash image.

**Evidence:**
* results/firmware/bup-format.md
* tools/firmware/armorx_bup.py

**Ruled out:**
* custom encryption on the BUP container itself (plain zlib)

## FW-U-004 — Can the official updater decrypt/decompress the BUP?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** high

**Answer:** Not needed for decompression. The updater's remaining role (device detection, transfer protocol, verification) has not yet been read statically.

**Evidence:**
* BUP payload is plain zlib — no updater is needed to decompress it; encryption lives in the flash image (ENC/chip-key), which the JieLi unpacker already decrypted offline

**Next offline step:** PE static analysis of BUpgrade.exe / Upgrade.dll / BTUpgrade.dll / Devices.dll in the extracted BTUpgrade_V1.9 tree

## FW-U-005 — Is the ArmorX firmware JieLi .ufw / jl_isd.fw / JLFS or another JieLi format?

**Status:** RESOLVED  |  **Priority:** high

**Answer:** JieLi JLFS flash image in the 'jl-new-fw' layout (not the older .ufw container despite the .ufw slot names) running on an AC632N/AC6321A.

**Evidence:**
* format: jl-new-fw from jl-misctools fwunpack_newfw.py
* chip AC632N, PID AC632N_TRANS, uboot.boot + isd_config.ini + app_dir_head + VM + key_mac + BTIF/EXIF/USERIF
* JLBTSDKflash, 632N_LE_UPDATE, ble_ota.bin/edr_ota2.bin

**Ruled out:**
* non-JieLi proprietary format

## FW-U-006 — Which image runs on AC6321A?

**Status:** RESOLVED  |  **Priority:** high

**Answer:** The body app.bin (227,440 B for V41) runs on the AC6321A.

**Evidence:**
* board_ac6321a.c source path inside decrypted app.bin
* app base 0x01E00000, entry 0x01E00120
* chip name AC632N / PID AC632N_TRANS

## FW-U-007 — Does that image contain our known A5/A4/AB protocol?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** high

**Answer:** A frame dispatcher with head/len/checksum validation is present; the individual opcode handlers are not yet located. Absence of literal constants is not evidence of absence.

**Evidence:**
* A real frame dispatcher exists: 'out cmd=%x,%x pa=%x, len=%d', 'in cmd=%x,%x', 'unsupport cmd: 0x%x', 'cmd head err', 'cmd len err', 'cmd sum err'
* literal A5/A4/AB byte sequences are absent from app.bin (expected for compiled code)

**Ruled out:**
* the protocol is implemented in a separate, absent image (the app contains the dispatcher)

**Next offline step:** Disassemble app.bin with a BD19/q32s disassembler and resolve the dispatcher's opcode table; or match against the AC63 SDK HID/gamepad app

**Depends on:** FW-U-021

## FW-U-008 — Can D2/D6/D7/D8/FC/F6/F7/AB handlers be located in firmware?

**Status:** DEFERRED_REQUIRES_NEW_TOOLING  |  **Priority:** high

**Answer:** Not yet located at instruction level. The subsystem strings prove the functionality is in this image.

**Evidence:**
* the app contains the dispatcher, config engine (GAMEPAD_CONFIG_MAX), macro engine (GAMEPAD_MACRO_MAX, 'recort start'), stick/trigger curve model, gyro engine (IMU_*) and a flash-write path ('switchd flash write add=%x, len=%d')

**Next offline step:** Obtain/repurpose a BD19 (q32s) disassembler (ghidra-jieli navigation module, or JieLi's own toolchain) and build the symbol map

**Depends on:** FW-U-021

## FW-U-009 — Does the firmware reveal the IMU model?

**Status:** UNKNOWN  |  **Priority:** medium

**Answer:** No. The IMU driver may be inside a linked library or on a secondary MCU.

**Evidence:**
* app.bin has IMU/gyro logic strings (IMU_TYPE_LEFT/RIGHT, IMU_MODE, IMU_TRIGGER, imu_cal_start, gyro:%d,%d,%d, hw imu init error!)
* no sensor part number, no WHO_AM_I identifier, no I2C address table found in the string corpus or in the AC63 SDK

**Ruled out:**
* QMI8658/ICM/BMI/LSM/MPU/SC7A20/STK8B as *named strings* — none present

**Next offline step:** Search app.bin for I2C/SPI register tables (not name strings); compare against the AC63 SDK iic driver surface

**Next hardware step:** Read the IMU's WHO_AM_I over the controller's own bus (NOT permitted tonight)

**Depends on:** FW-U-021

## FW-U-010 — Does the firmware reveal persistent configuration / macro storage?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** high

**Answer:** The flash layout is mapped at file level (JLFS: uboot.boot, isd_config.ini, app_dir_head/app.bin, cfg_tool.bin, VM, BTIF, EXIF, USERIF, key_mac). The internal structure of VM/EXIF/USERIF is not yet decoded.

**Evidence:**
* JLFS entries VM (262,144 B), BTIF, EXIF, USERIF, key_mac (4,096 B), cfg_tool.bin (722 B)
* 'switchd flash write add=%x, len=%d', 'flash_uuid:', 'mnt/sdfile/res/md5.bin'
* macro/config strings

**Next offline step:** Decode the VM/EXIF/USERIF region layout and the 144-byte D6 config image inside them

## FW-U-011 — Can V2224/V32/V41 binary diff identify when major ArmorX features were added?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** medium

**Answer:** Feature-level timeline derived from strings; instruction-level timeline requires a disassembler.

**Evidence:**
* app.bin sizes 204,564 → 223,960 → 227,440 (V2224 → V32 → V41)
* string-set deltas: V41 adds USB host/device, 2.4 GHz select, DEV_TYPE console descriptors, BLE connection management
* 0% identical 16 KiB blocks between builds

**Next offline step:** Instruction-level diff once FW-U-021 is resolved

**Depends on:** FW-U-021

## FW-U-012 — Does the updater reveal a standard JieLi bootloader protocol?

**Status:** OPEN  |  **Priority:** high

**Answer:** Not yet determined.

**Evidence:**
* BTUpgrade_V1.9 tree extracted, hashes identical between CN and international packages; not yet analysed

**Next offline step:** Static PE analysis of BUpgrade.exe + BTUpgrade.dll/BTUpgrade_HX.dll/USBUpgrade.dll/Devices.dll for VID/PID, HID/WinUSB/SetupAPI use and bootloader command structures

**Next hardware step:** DEFERRED_REQUIRES_HARDWARE (never tonight)

## FW-U-013 — Is firmware authenticity verified cryptographically or merely checksum-protected?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** high

**Answer:** Evidence so far points to checksum/CRC integrity plus a confidentiality-only chip key; no cryptographic signature found. NOT sufficient to claim 'no secure boot'.

**Evidence:**
* BUP container: no signature field observed (magic + version + names + sizes + zlib)
* flash image: uboot.boot is 'compressed: true'; CRC/hash machinery (CRC16/CRC32) is present in the JieLi toolchain and the image uses checksums
* no RSA/ECDSA signature blob located
* isd_config.ini carries a chip key, which is CONFIDENTIALITY (ENC obfuscation), not AUTHENTICITY

**Ruled out:**
* signature visible in the BUP container

**Next offline step:** Read the updater's verification branch and locate the firmware CRC/hash check in app.bin

**Depends on:** FW-U-012

## FW-U-014 — Is there one MCU doing most of the ArmorX logic, or is AC6321A only a communications coprocessor?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** high

**Answer:** STRONG EVIDENCE the AC6321A is the main application MCU, not a thin bridge. A possible secondary MCU (RF front-end / sensor hub) is neither proven nor excluded.

**Evidence:**
* decrypted app.bin contains config engine, macro engine, stick/trigger curves, gyro handling, USB host+device, 2.4G select, console DEV_TYPE conversion, flash write
* vendor identity ZIKWAY/ZJ-XT* inside the image

**Ruled out:**
* AC6321A is a pure BLE/OTA bridge

**Next offline step:** Check whether the app talks to a second MCU over UART (UART init strings, TX-A/TX-B) and what messages it exchanges

**Next hardware step:** Board-level inspection of the second MCU (DEFERRED_REQUIRES_HARDWARE)

## FW-U-015 — Why do the V41 / V3600 packages carry two .ufw sub-images?

**Status:** RESOLVED  |  **Priority:** medium

**Answer:** The pair is the same application packaged for two chip-key production variants; the raw images differ in ~80% of bytes purely because of ENC keying.

**Evidence:**
* slot A and slot B app.bin SHA-256 identical within each package; isd_config.ini differs (chip key 6413 vs 13462); uboot/cfg_tool/p11 identical

**Ruled out:**
* two different builds
* left/right half firmware
* different hardware revisions

## FW-U-016 — Is the F7 step-length value ever produced by the firmware?

**Status:** OPEN  |  **Priority:** high

**Answer:** Not yet determined. Firmware-side search for the F7 dispatcher entry requires disassembly.

**Evidence:**
* app.bin string corpus contains 'xbox info:step=%d', 'jstep[%d] time=%x,%x' (V41) / 'stepj[%d] time=%d' (V2224)
* the app-side provenance work already proved the app consumes an inbound F7 event frame (does not imply the body firmware emits one)

**Next offline step:** Locate the F7 opcode arm of the frame dispatcher once FW-U-021 is resolved

**Next hardware step:** A guarded, read-only F7 listen experiment (already prepared; NOT tonight)

**Depends on:** FW-U-021

## FW-U-017 — Is there receiver/F20 (dongle) firmware in the packages, and is it separate from body firmware?

**Status:** RESOLVED  |  **Priority:** high

**Answer:** YES — dongle firmware is separate and analysed independently; it shares the JieLi uboot/cfg_tool with the body.

**Evidence:**
* V3600-dongle.bup and V3000-dongle.bup are separate packages with their own board codes (0x1e, 0x17) and app.bin (192,536 / 179,376 B)
* dongle app source path xt_dongle.c, strings '*** services, uuid16:%04x,index=%d ***', '!!!error_adv_packet:'

## FW-U-018 — What is the meaning of the isd_config.ini chip key (6413 / 13462)?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** low

**Answer:** It is the ENC key used to obfuscate the app region (CONFIDENTIALITY), not an authentication secret. Whether it is per-chip-batch or per-production-run is unknown.

**Evidence:**
* isd_config.ini 102 bytes, differs per slot; the JieLi unpacker uses it to decrypt the app region

**Ruled out:**
* it is a signature

**Next offline step:** Compare against other BigBigWon/JieLi releases to see how many key values exist

## FW-U-019 — Do the V41 USB-host/2.4G strings mean the controller can host USB devices?

**Status:** PARTIALLY_RESOLVED  |  **Priority:** medium

**Answer:** The app contains both a USB host stack and a USB device (XInput) path plus a 2.4 GHz selection path.

**Evidence:**
* RXCSRH_/TXCSRH_ (USB host channel status/host registers), USB_ERR_STALL_BULK_RECEIVE/SEND, usbh_socket_en, m_xbox_enum_step, usbh_gamepad_ready, 'app select 24g'

**Next offline step:** Determine which USB role is active in which product mode (body vs dongle) from the app's state machine

**Next hardware step:** USB enumeration of the real unit (DEFERRED_REQUIRES_HARDWARE)

**Depends on:** FW-U-021

## FW-U-020 — Is the updater's transfer protocol JieLi UBOOT or a custom USB protocol?

**Status:** OPEN  |  **Priority:** high

**Answer:** Unknown.

**Evidence:**
* not yet analysed

**Next offline step:** PE static analysis of the updater DLLs

**Next hardware step:** DEFERRED_REQUIRES_HARDWARE

**Depends on:** FW-U-012

## FW-U-021 — Which instruction set does the AC6321A app use and how do we disassemble it?

**Status:** DEFERRED_REQUIRES_NEW_TOOLING  |  **Priority:** critical

**Answer:** Architecture is the JieLi BD19-family core; no working offline disassembler was available in this run.

**Evidence:**
* app base 0x01E00000, entry 0x01E00120, board bd19/ac6321a
* the public AC63 SDK ships no Linux disassembler for the core; no BD19/q32s objdump available offline

**Ruled out:**
* ARM/Thumb
* RISC-V
* 8051 (entry/vector layout and SDK core directories are all JieLi-specific)

**Next offline step:** Build/obtain a BD19 disassembler (JieLi toolchain or ghidra-jieli processor module) and produce the canonical symbol map

