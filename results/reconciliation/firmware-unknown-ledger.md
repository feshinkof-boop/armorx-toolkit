# ArmorX firmware unknown ledger

_generated 2026-09-28 — scope: ArmorX Pro firmware/updater ecosystem (four operator packages), offline/static only | q32s pass 2026-09-28: firmware code navigation_

| id | question | status | priority |
|---|---|---|---|
| `FW-U-001` | Why is the Chinese V41 package 34.8 MB while the international one is 5.8 MB? | **RESOLVED** | high |
| `FW-U-002` | Are the actual V41 firmware payload bytes identical between the CN and international packages? | **RESOLVED** | high |
| `FW-U-003` | What exactly is inside V2224.bup / the V32 / V41 / dongle packages? | **RESOLVED** | high |
| `FW-U-004` | Can the official updater decrypt/decompress the BUP? | **PARTIALLY_RESOLVED** | high |
| `FW-U-005` | Is the ArmorX firmware JieLi .ufw / jl_isd.fw / JLFS or another JieLi format? | **RESOLVED** | high |
| `FW-U-006` | Which image runs on AC6321A? | **RESOLVED** | high |
| `FW-U-007` | Does that image contain our known A5/A4/AB protocol? | **PARTIALLY_RESOLVED** | high |
| `FW-U-008` | Can D2/D6/D7/D8/FC/F6/F7/AB handlers be located in firmware? | **PARTIALLY_RESOLVED** | high |
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
| `FW-U-021` | Which instruction set does the AC6321A app use, and how do we disassemble it? | **RESOLVED** | critical |
| `FW-U-022` | How much of the vendor firmware is stock JieLi SDK code? | **RESOLVED** | high |
| `FW-U-023` | Where are the D6, D8, FC, F6, AB and 0B families handled, if not in armorx_cmd_dispatch? | **OPEN** | high |
| `FW-U-024` | Does the handler base register (r9) point at the frame start or at the payload? | **OPEN** | critical |
| `FW-U-025` | Which function computes the protocol checksum (live-proven: sum of preceding bytes)? | **OPEN** | high |
| `FW-U-026` | What does the firmware use to decide when a D2 report is sent (the event-driven behaviour)? | **PARTIALLY_RESOLVED** | high |
| `FW-U-027` | Is there a lighting/RGB handler and an identifiable IMU part in the image? | **OPEN** | medium |

## Detail

### FW-U-001 — RESOLVED

**Q:** Why is the Chinese V41 package 34.8 MB while the international one is 5.8 MB?

**A:** The Chinese ZIP bundles the 28,032,675-byte Android app BIGBIG_WON_2.22.1226.apk plus Chinese-only change-log text files; the international RAR does not. All firmware payloads and all seven BTUpgrade_V1.9 files are byte-identical.

Evidence: results/firmware/v41-chinese-vs-international.md; research/firmware/2026-09-28/v41-chinese-vs-international.json

### FW-U-002 — RESOLVED

**Q:** Are the actual V41 firmware payload bytes identical between the CN and international packages?

**A:** YES

Evidence: same SHA-256 for 01战甲X Pro固件-V41.bup and Firmware ArmorX-Pro V41.bup; same for both V3600 dongle .bup files; all 7 updater files identical

### FW-U-003 — RESOLVED

**Q:** What exactly is inside V2224.bup / the V32 / V41 / dongle packages?

**A:** BUP = 'BigBigWon Upgrade Pack' header + one or two sub-images, each stored as a sequence of independent zlib blocks of 32,768 B preceded by (compressed,uncompressed) u32 records. Decompressed result is a raw JieLi JLFS flash image.

Evidence: results/firmware/bup-format.md; tools/firmware/armorx_bup.py

### FW-U-004 — PARTIALLY_RESOLVED

**Q:** Can the official updater decrypt/decompress the BUP?

**A:** Not needed for decompression. The updater's remaining role (device detection, transfer protocol, verification) has not yet been read statically.

Evidence: BUP payload is plain zlib — no updater is needed to decompress it; encryption lives in the flash image (ENC/chip-key), which the JieLi unpacker already decrypted offline

Next offline step: PE static analysis of BUpgrade.exe / Upgrade.dll / BTUpgrade.dll / Devices.dll in the extracted BTUpgrade_V1.9 tree

### FW-U-005 — RESOLVED

**Q:** Is the ArmorX firmware JieLi .ufw / jl_isd.fw / JLFS or another JieLi format?

**A:** JieLi JLFS flash image in the 'jl-new-fw' layout (not the older .ufw container despite the .ufw slot names) running on an AC632N/AC6321A.

Evidence: format: jl-new-fw from jl-misctools fwunpack_newfw.py; chip AC632N, PID AC632N_TRANS, uboot.boot + isd_config.ini + app_dir_head + VM + key_mac + BTIF/EXIF/USERIF; JLBTSDKflash, 632N_LE_UPDATE, ble_ota.bin/edr_ota2.bin

### FW-U-006 — RESOLVED

**Q:** Which image runs on AC6321A?

**A:** The body app.bin (227,440 B for V41) runs on the AC6321A.

Evidence: board_ac6321a.c source path inside decrypted app.bin; app base 0x01E00000, entry 0x01E00120; chip name AC632N / PID AC632N_TRANS

### FW-U-007 — PARTIALLY_RESOLVED

**Q:** Does that image contain our known A5/A4/AB protocol?

**A:** Partly: string xrefs now resolve into the image and the A5 frame handler exists, but no plaintext A5/A4/AB constant table was found. The dispatcher compares the opcode against D2/D4/D7/F7/F8/F9/FA/FF, which matches the live families.

Evidence: A real frame dispatcher exists: 'out cmd=%x,%x pa=%x, len=%d', 'in cmd=%x,%x', 'unsupport cmd: 0x%x', 'cmd head err', 'cmd len err', 'cmd sum err'; literal A5/A4/AB byte sequences are absent from app.bin (expected for compiled code)

Next offline step: Disassemble app.bin with a BD19/q32s disassembler and resolve the dispatcher's opcode table; or match against the AC63 SDK HID/gamepad app

### FW-U-008 — PARTIALLY_RESOLVED

**Q:** Can D2/D6/D7/D8/FC/F6/F7/AB handlers be located in firmware?

**A:** Partly: with the q32s toolchain the dispatcher is located at 0x1e08772 and D2/D4/D7/F7/F8/F9/FA/FF handler entries are recovered; D6, D8, FC, F6, AB and 0B are NOT compared in this chain, so those families are handled outside it.

Evidence: the app contains the dispatcher, config engine (GAMEPAD_CONFIG_MAX), macro engine (GAMEPAD_MACRO_MAX, 'recort start'), stick/trigger curve model, gyro engine (IMU_*) and a flash-write path ('switchd flash write add=%x, len=%d')

Next offline step: Obtain/repurpose a BD19 (q32s) disassembler (ghidra-jieli navigation module, or JieLi's own toolchain) and build the symbol map

### FW-U-009 — UNKNOWN

**Q:** Does the firmware reveal the IMU model?

**A:** No. The IMU driver may be inside a linked library or on a secondary MCU.

Evidence: app.bin has IMU/gyro logic strings (IMU_TYPE_LEFT/RIGHT, IMU_MODE, IMU_TRIGGER, imu_cal_start, gyro:%d,%d,%d, hw imu init error!); no sensor part number, no WHO_AM_I identifier, no I2C address table found in the string corpus or in the AC63 SDK

Next offline step: Search app.bin for I2C/SPI register tables (not name strings); compare against the AC63 SDK iic driver surface

### FW-U-010 — PARTIALLY_RESOLVED

**Q:** Does the firmware reveal persistent configuration / macro storage?

**A:** The flash layout is mapped at file level (JLFS: uboot.boot, isd_config.ini, app_dir_head/app.bin, cfg_tool.bin, VM, BTIF, EXIF, USERIF, key_mac). The internal structure of VM/EXIF/USERIF is not yet decoded.

Evidence: JLFS entries VM (262,144 B), BTIF, EXIF, USERIF, key_mac (4,096 B), cfg_tool.bin (722 B); 'switchd flash write add=%x, len=%d', 'flash_uuid:', 'mnt/sdfile/res/md5.bin'; macro/config strings

Next offline step: Decode the VM/EXIF/USERIF region layout and the 144-byte D6 config image inside them

### FW-U-011 — PARTIALLY_RESOLVED

**Q:** Can V2224/V32/V41 binary diff identify when major ArmorX features were added?

**A:** Feature-level timeline derived from strings; instruction-level timeline requires a disassembler.

Evidence: app.bin sizes 204,564 → 223,960 → 227,440 (V2224 → V32 → V41); string-set deltas: V41 adds USB host/device, 2.4 GHz select, DEV_TYPE console descriptors, BLE connection management; 0% identical 16 KiB blocks between builds

Next offline step: Instruction-level diff once FW-U-021 is resolved

### FW-U-012 — OPEN

**Q:** Does the updater reveal a standard JieLi bootloader protocol?

**A:** Not yet determined.

Evidence: BTUpgrade_V1.9 tree extracted, hashes identical between CN and international packages; not yet analysed

Next offline step: Static PE analysis of BUpgrade.exe + BTUpgrade.dll/BTUpgrade_HX.dll/USBUpgrade.dll/Devices.dll for VID/PID, HID/WinUSB/SetupAPI use and bootloader command structures

### FW-U-013 — PARTIALLY_RESOLVED

**Q:** Is firmware authenticity verified cryptographically or merely checksum-protected?

**A:** Evidence so far points to checksum/CRC integrity plus a confidentiality-only chip key; no cryptographic signature found. NOT sufficient to claim 'no secure boot'.

Evidence: BUP container: no signature field observed (magic + version + names + sizes + zlib); flash image: uboot.boot is 'compressed: true'; CRC/hash machinery (CRC16/CRC32) is present in the JieLi toolchain and the image uses checksums; no RSA/ECDSA signature blob located; isd_config.ini carries a chip key, which is CONFIDENTIALITY (ENC obfuscation), not AUTHENTICITY

Next offline step: Read the updater's verification branch and locate the firmware CRC/hash check in app.bin

### FW-U-014 — PARTIALLY_RESOLVED

**Q:** Is there one MCU doing most of the ArmorX logic, or is AC6321A only a communications coprocessor?

**A:** STRONG EVIDENCE the AC6321A is the main application MCU, not a thin bridge. A possible secondary MCU (RF front-end / sensor hub) is neither proven nor excluded.

Evidence: decrypted app.bin contains config engine, macro engine, stick/trigger curves, gyro handling, USB host+device, 2.4G select, console DEV_TYPE conversion, flash write; vendor identity ZIKWAY/ZJ-XT* inside the image

Next offline step: Check whether the app talks to a second MCU over UART (UART init strings, TX-A/TX-B) and what messages it exchanges

### FW-U-015 — RESOLVED

**Q:** Why do the V41 / V3600 packages carry two .ufw sub-images?

**A:** The pair is the same application packaged for two chip-key production variants; the raw images differ in ~80% of bytes purely because of ENC keying.

Evidence: slot A and slot B app.bin SHA-256 identical within each package; isd_config.ini differs (chip key 6413 vs 13462); uboot/cfg_tool/p11 identical

### FW-U-016 — OPEN

**Q:** Is the F7 step-length value ever produced by the firmware?

**A:** Not yet determined. Firmware-side search for the F7 dispatcher entry requires disassembly.

Evidence: app.bin string corpus contains 'xbox info:step=%d', 'jstep[%d] time=%x,%x' (V41) / 'stepj[%d] time=%d' (V2224); the app-side provenance work already proved the app consumes an inbound F7 event frame (does not imply the body firmware emits one)

Next offline step: Locate the F7 opcode arm of the frame dispatcher once FW-U-021 is resolved

### FW-U-017 — RESOLVED

**Q:** Is there receiver/F20 (dongle) firmware in the packages, and is it separate from body firmware?

**A:** YES — dongle firmware is separate and analysed independently; it shares the JieLi uboot/cfg_tool with the body.

Evidence: V3600-dongle.bup and V3000-dongle.bup are separate packages with their own board codes (0x1e, 0x17) and app.bin (192,536 / 179,376 B); dongle app source path xt_dongle.c, strings '*** services, uuid16:%04x,index=%d ***', '!!!error_adv_packet:'

### FW-U-018 — PARTIALLY_RESOLVED

**Q:** What is the meaning of the isd_config.ini chip key (6413 / 13462)?

**A:** It is the ENC key used to obfuscate the app region (CONFIDENTIALITY), not an authentication secret. Whether it is per-chip-batch or per-production-run is unknown.

Evidence: isd_config.ini 102 bytes, differs per slot; the JieLi unpacker uses it to decrypt the app region

Next offline step: Compare against other BigBigWon/JieLi releases to see how many key values exist

### FW-U-019 — PARTIALLY_RESOLVED

**Q:** Do the V41 USB-host/2.4G strings mean the controller can host USB devices?

**A:** The app contains both a USB host stack and a USB device (XInput) path plus a 2.4 GHz selection path.

Evidence: RXCSRH_/TXCSRH_ (USB host channel status/host registers), USB_ERR_STALL_BULK_RECEIVE/SEND, usbh_socket_en, m_xbox_enum_step, usbh_gamepad_ready, 'app select 24g'

Next offline step: Determine which USB role is active in which product mode (body vs dongle) from the app's state machine

### FW-U-020 — OPEN

**Q:** Is the updater's transfer protocol JieLi UBOOT or a custom USB protocol?

**A:** Unknown.

Evidence: not yet analysed

Next offline step: PE static analysis of the updater DLLs

### FW-U-021 — RESOLVED

**Q:** Which instruction set does the AC6321A app use, and how do we disassemble it?

**A:** Resolved: the vendor's own q32s disassembler was obtained (JieLi Linux toolchain, LLVM 4.0.1 fork, registered targets pi32/pi32v2/q32s). Wrapping the raw image as an ELF32-q32s section and linking at 0x01e00000 gives a real disassembly. Independent validation: the BD19 ROM reconstructed from rom.lst re-disassembles with 9,746/9,746 exact matches (100.0% text, length and branch-target agreement).

Evidence: app base 0x01E00000, entry 0x01E00120, board bd19/ac6321a; SDK cpu/bd19/tools/rom.lst is a full disassembly of the BD19 ROM, annotated 'file format ELF32-q32s' (9,747 parsed instructions; lengths 2/4/6 bytes = 16/32/48-bit); opcode-prefix enrichment: the 48 most frequent ROM two-byte prefixes occur ~99,000-100,300 times per MiB in every app.bin vs 749 per MiB in random data (approx. 133x); results/firmware/isa-identification.md

### FW-U-022 — RESOLVED

**Q:** How much of the vendor firmware is stock JieLi SDK code?

**A:** The bootloader, config tool and resource blob are shared stock JieLi components; only app.bin and isd_config.ini are vendor-distinct. This makes a stock-SDK-vs-ArmorX app diff the most promising offline route to isolating ArmorX-specific code once the ISA decoder exists.

Evidence: ArmorX V41 cfg_tool.bin is byte-identical (SHA-256 0ccc2fd57959...) to the stock AC63 SDK cpu/bd19/tools/cfg_tool.bin; uboot.boot (a64171c3cf41...) and p11_code.bin are byte-identical across all five packages, body and dongle; p11_code.bin differs from the SDK copy (vendor-modified resource); public repo commits recorded in research/firmware/2026-09-28/tool-provenance.json

Next offline step: Diff a stock AC63 SDK demo build's app image against ArmorX app.bin once q32s decoding works

### FW-U-023 — OPEN

**Q:** Where are the D6, D8, FC, F6, AB and 0B families handled, if not in armorx_cmd_dispatch?

**A:** Not yet answered. The dispatcher chain does not test those opcodes, so either a second dispatcher exists, or the frames reach the device through a different path (transport-level or a different service).

Evidence: 0x1e08772 compares only 0x2F/0x70/0xD2/0xD4/0xD7/0xF7/0xF8/0xF9/0xFA/0xFF; 0x1e0aff2 compares 0xA5 and 0x0B (three 0B references) and calls the frame handler; 0x1e0a944 compares 0x0B twice; results/firmware/armorx-command-dispatch.json

Next offline step: Extract the compare structure of 0x1e0aff2 and 0x1e0a944 (0B lives there), and de-nest the sub-switches in 0x1e08772 to see whether D6/D8/FC are reached under a sub-command byte.

### FW-U-024 — OPEN

**Q:** Does the handler base register (r9) point at the frame start or at the payload?

**A:** Not yet answered. For a 4-byte frame the byte at frame[3] is the checksum, so this decides whether the F7 read is being interpreted as a value write or is rejected.

Evidence: armorx_cmd_dispatch reads payload bytes as b[r9 + 0x2], b[r9 + 0x3], b[r9 + 0x4]; the F7 handler compares b[r9+0x3] against 0x2 and the D4 path reads b[r9+0x3]/b[r9+0x4]; live frames are A5 04 F7 A0 (last byte is the checksum) and A5 04 D4 7D

Next offline step: Read the frame handler prologue and its caller to fix r9's origin, then re-read the F7 handler with that base.

### FW-U-025 — OPEN

**Q:** Which function computes the protocol checksum (live-proven: sum of preceding bytes)?

**A:** Not yet answered. The frame handler validates and reports a checksum failure, but the summing routine itself is not yet identified.

Evidence: frame_err_checksum (0x1e070da) is the checksum-error printer called from the frame handler; 0x1e05c66 builds 0xDC-byte records and hashes 8 bytes with '...len=%d crc=%x' (record integrity, not necessarily the frame checksum)

Next offline step: Follow the call made between the length check and the checksum-error branch in 0x1e08772; the callee is the checksum routine.

### FW-U-026 — PARTIALLY_RESOLVED

**Q:** What does the firmware use to decide when a D2 report is sent (the event-driven behaviour)?

**A:** Partly: the handler entry point is known, but the send condition inside it has not been read out yet.

Evidence: D2 handler entry recovered at 0x1e08d24 (fall-through of the rOP != 0xD2 test); live: no D2 frames are produced for analog-only change; a digital trigger produces a report carrying both the RT digital bit and the RT analog byte

Next offline step: Read 0x1e08d24 and find the dirty-flag/compare that gates report construction, then match it against the capture evidence.

### FW-U-027 — OPEN

**Q:** Is there a lighting/RGB handler and an identifiable IMU part in the image?

**A:** Not answered. The strings prove the subsystems exist; no opcode family or part identity is established.

Evidence: 'switch_lights=%x' and 'led_check failed, reset setting' strings exist and resolve to code; IMU logic strings exist ('IMU_TYPE_LEFT/RIGHT', 'imu_not calibrated', 'gyro CAL data now:%d,%d,%d'); no WHO_AM_I value, I2C address or IMU part number appears in the plaintext strings

Next offline step: Trace the callers of 0x1e1569a (gyro calibration) for the sensor bus accesses, and find the opcode family that reaches the switch_lights code.

