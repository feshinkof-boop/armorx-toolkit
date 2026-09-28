# ARMOR-X firmware symbol map

Recovered from the V41 body image (227440 bytes at 0x1e00000).
Grades: PROVEN STATIC / STRONG EVIDENCE / INFERRED. Names are only as strong as the grade on the row.

| address | name | category | grade | evidence |
|---|---|---|---|---|
| `0x01e00000` | `fw_start` | entry/startup | PROVEN STATIC | image load base; startup stub clears BSS and copies .data (verified by disassembly) |
| `0x01e00120` | `armorx_entry_point` | entry/startup | PROVEN STATIC | JLFS app directory entry-point field for the V41 body image |
| `0x01e042d0` | `user_cfg_engine` | config engine | STRONG EVIDENCE | references 'USER_CFG...warning_tone_v/poweroff_tone_v', 'auto_off_time', 'init mac addr', 'imu_not calibrated' |
| `0x01e0494a` | `config_auto_off_and_mac` | config engine | STRONG EVIDENCE | references 'USER_CFGauto_off_time:%d' and 'G>>>init mac addr!!!' |
| `0x01e04b38` | `app_select_24g` | 2.4G | STRONG EVIDENCE | references '------app select 24g--------' |
| `0x01e05856` | `macro_engine_config` | macro engine | STRONG EVIDENCE | references 'GAMEPAD_MACRO_MAX =%d' |
| `0x01e05c66` | `record_build_with_hash` | flash/VM | STRONG EVIDENCE | indexes 0xDC-byte records (r4 += r5 * 0xdc), zero-fills, hashes 8 bytes at record+2, stores the byte-reversed result at record+0, logs '...len=%d crc=%x' |
| `0x01e06216` | `enum_switch_0_to_10` | config engine | STRONG EVIDENCE | bounds check 'if (r0 > 0xa)' followed by a tbb table branch: an 11-way switch |
| `0x01e0642c` | `armorx_f7_response_build` | protocol TX | STRONG EVIDENCE | single call site, inside the F7 handler, passing opcode 0xF6: the F7 settings path emits an F6 frame rather than an F7 reply |
| `0x01e06e8a` | `frame_err_length` | protocol parser | PROVEN STATIC | unique reference to the command-length error literal; called from the frame handler |
| `0x01e0701c` | `frame_err_head` | protocol parser | PROVEN STATIC | unique reference to '...cmd head err %x %x'; called from the frame handler |
| `0x01e070da` | `frame_err_checksum` | protocol parser | PROVEN STATIC | unique reference to the checksum-error literal; called from the frame handler |
| `0x01e071fe` | `stick_curve_engine` | stick | STRONG EVIDENCE | references 'stick curve init %d: point1(%d,%d), point2(%d,%d)' and 'sensor curve[%d]: dir, min, curve, speed, y_div_x, smooth' |
| `0x01e08772` | `armorx_cmd_dispatch` | command dispatcher | PROVEN STATIC | compares the frame opcode against D2/D4/D7/F7/F8/F9/FA/FF and calls the frame head/length/checksum error printers |
| `0x01e08772` | `frame_parse_and_dispatch` | protocol parser | PROVEN STATIC | same function as armorx_cmd_dispatch: validates then dispatches |
| `0x01e08860` | `armorx_f7_handler` | F7 | PROVEN STATIC | fall-through block of the dispatcher's rOP != 0xF7 test |
| `0x01e08912` | `armorx_f9_handler` | unknown opcode | PROVEN STATIC | goto target of the dispatcher's rOP == 0xF9 test |
| `0x01e08944` | `armorx_d4_handler` | D4 | PROVEN STATIC | fall-through block of the dispatcher's rOP != 0xD4 test (second D4 site) |
| `0x01e0898e` | `armorx_fa_handler` | unknown opcode | PROVEN STATIC | fall-through block of the dispatcher's rOP != 0xFA test |
| `0x01e08a68` | `armorx_d7_handler` | D7 | PROVEN STATIC | goto target of the dispatcher's rOP == 0xD7 test |
| `0x01e08b86` | `armorx_f8_handler` | F6/F7/F8 config | PROVEN STATIC | goto target of the dispatcher's rOP == 0xF8 test |
| `0x01e08d24` | `armorx_d2_handler` | D2 | PROVEN STATIC | fall-through block of the dispatcher's rOP != 0xD2 test inside armorx_cmd_dispatch |
| `0x01e0914a` | `armorx_2f_handler` | unknown opcode | PROVEN STATIC | goto target of the dispatcher's rOP == 0x2F test |
| `0x01e0944e` | `armorx_ff_response_handler` | protocol TX | PROVEN STATIC | goto target of the dispatcher's rOP == 0xFF test (response envelope family) |
| `0x01e0aff2` | `ble_transport_layer` | BLE | INFERRED | contains compares against A5 and 0B and 3 references to the 0B query opcode, calls the frame handler |
| `0x01e0ebcc` | `imu_axis_dump` | gyro/IMU | INFERRED | references a '%d,%d,%d,%d' literal attributed to the IMU calibration area |
| `0x01e12714` | `user_cfg_bt_name` | config engine | STRONG EVIDENCE | references 'USER_CFGread bt name err' and 'pps/hid/modules/bt/ble_multi.c' |
| `0x01e12db4` | `imu_type_and_unsupported_cmd` | gyro/IMU | INFERRED | references 'IMU_TYPE_RIGHT'/'IMU_TYPE_LEFT' and 'unsupport cmd: 0x%x'; single function mixing the unsupported-command default with IMU type naming |
| `0x01e139aa` | `usbd_auto_detect_init` | USB device | STRONG EVIDENCE | references 'usbd auto det init' |
| `0x01e1569a` | `gyro_calibration` | gyro/IMU | STRONG EVIDENCE | references '... gyro CAL data now:%d,%d,%d' |
| `0x01e16368` | `zikway_2g4_deal` | 2.4G | STRONG EVIDENCE | references '...pp_zikway_deal', 'mode=%x, mac:', ' tx busy!' |
| `0x01e2155a` | `sdfile_mount` | storage | STRONG EVIDENCE | references '[SDFILE]sdfile mount failed!!!' |

## Command dispatcher map (from `armorx_cmd_dispatch`)

Function `0x1e08772` .. `0x1e0948c`, 1027 instructions examined.

| opcode | compare at | test | handler | family | evidence |
|---|---|---|---|---|---|
| 0x02 | `0x1e08864` | != | `0x1e08868` | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x05 | `0x1e08e5e` | != | `0x1e08e62` | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x0d | `0x1e091de` | != | `0x1e091e2` | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x19 | `0x1e08826` | == | `0x1e08d32` | UNKNOWN | PROVEN STATIC (opcode compared in the frame handler) |
| 0x1b | `0x1e0882a` | != | `0x1e0882e` | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0x2f | `0x1e08d1a` | == | `0x1e0914a` | unknown family seen in dispatch chain | PROVEN STATIC (opcode compared in the frame handler) |
| 0x70 | `0x1e0893a` | == | `0x1e093e4` | unknown family seen in dispatch chain | PROVEN STATIC (opcode compared in the frame handler) |
| 0xd2 | `0x1e08d1e` | != | `0x1e08d24` | D2 input-report enable/disable (live: A5 05 D2 01 7D / A5 05 D2 00 7C) | STRONG EVIDENCE (fell through the != test) |
| 0xd4 | `0x1e087c8` | != | `0x1e087ce` | D4 query (live: A5 04 D4 7D -> A5 07 D4 11 01 00 92) | STRONG EVIDENCE (fell through the != test) |
| 0xd4 | `0x1e0893e` | != | `0x1e08944` | D4 query (live: A5 04 D4 7D -> A5 07 D4 11 01 00 92) | STRONG EVIDENCE (fell through the != test) |
| 0xd7 | `0x1e08854` | == | `0x1e08a68` | D7 configuration write | PROVEN STATIC (opcode compared in the frame handler) |
| 0xef | `0x1e08e8c` | != | `0x1e08e92` | UNKNOWN | STRONG EVIDENCE (fell through the != test) |
| 0xf7 | `0x1e0885a` | != | `0x1e08860` | F7 stick step-length / step accuracy | STRONG EVIDENCE (fell through the != test) |
| 0xf8 | `0x1e08982` | == | `0x1e08b86` | F8 brightness-compensation config (app: A5 04 F8) | PROVEN STATIC (opcode compared in the frame handler) |
| 0xf9 | `0x1e087c2` | == | `0x1e08912` | unknown family seen in dispatch chain | PROVEN STATIC (opcode compared in the frame handler) |
| 0xfa | `0x1e08988` | != | `0x1e0898e` | unknown family seen in dispatch chain | STRONG EVIDENCE (fell through the != test) |

Note: the dispatcher region contains nested switches as well as the top-level opcode chain, so low-valued entries (0x00-0x1b, 0x0d, 0x19, 0x1b, 0xef) are sub-command tests, not top-level opcodes. The top-level families are the ones that match the live protocol: 0x2F, 0x70, 0xD2, 0xD4, 0xD7, 0xF7, 0xF8, 0xF9, 0xFA, 0xFF.

## Live anchors cross-checked against firmware

| family | live behaviour | firmware | verdict |
|---|---|---|---|
| 0B | A5 04 0B B4 -> A5 05 0B 30 E5 | 0B compared in 0x1e0aff2 (transport) and 0x1e0a944 | live query has a reply; firmware shows the 0B compares outside armorx_cmd_dispatch |
| D2 | A5 05 D2 01 7D / A5 05 D2 00 7C | dispatcher rOP != 0xD2 -> fall-through 0x1e08d24 | consistent |
| D4 | A5 04 D4 7D -> A5 07 D4 11 01 00 92 | dispatcher tests 0xD4 twice (0x1e087c8, 0x1e0893e) | consistent; two distinct D4 code paths exist in firmware |
| D7 | configuration write | dispatcher rOP == 0xD7 -> 0x1e08a68 | consistent |
| F7 | A5 04 F7 A0 -> NO reply live | falls through rOP != 0xF7 to 0x1e08860, which reads the byte after the opcode and only acts on values 0/1, and emits an F6 frame in that case | firmware offers a concrete reason for the silence: no reply frame is built on the non-0/1 path |
| F8 | app sends A5 04 F8 | dispatcher rOP == 0xF8 -> 0x1e08b86 | consistent |
| FC / F6 | A5 05 FC 80 26 -> A5 05 FF FC A5 | no FC compare found in the dispatcher; F6 appears only as the opcode emitted by the F7 path | CONTRADICTION with the assumption that FC is handled in this dispatcher |

## Symbol categories

* **2.4G**: `0x01e16368` zikway_2g4_deal (STRONG EVIDENCE), `0x01e04b38` app_select_24g (STRONG EVIDENCE)
* **BLE**: `0x01e0aff2` ble_transport_layer (INFERRED)
* **D2**: `0x01e08d24` armorx_d2_handler (PROVEN STATIC)
* **D4**: `0x01e08944` armorx_d4_handler (PROVEN STATIC)
* **D7**: `0x01e08a68` armorx_d7_handler (PROVEN STATIC)
* **F6/F7/F8 config**: `0x01e08b86` armorx_f8_handler (PROVEN STATIC)
* **F7**: `0x01e08860` armorx_f7_handler (PROVEN STATIC)
* **USB device**: `0x01e139aa` usbd_auto_detect_init (STRONG EVIDENCE)
* **command dispatcher**: `0x01e08772` armorx_cmd_dispatch (PROVEN STATIC)
* **config engine**: `0x01e042d0` user_cfg_engine (STRONG EVIDENCE), `0x01e12714` user_cfg_bt_name (STRONG EVIDENCE), `0x01e0494a` config_auto_off_and_mac (STRONG EVIDENCE), `0x01e06216` enum_switch_0_to_10 (STRONG EVIDENCE)
* **entry/startup**: `0x01e00120` armorx_entry_point (PROVEN STATIC), `0x01e00000` fw_start (PROVEN STATIC)
* **flash/VM**: `0x01e05c66` record_build_with_hash (STRONG EVIDENCE)
* **gyro/IMU**: `0x01e1569a` gyro_calibration (STRONG EVIDENCE), `0x01e0ebcc` imu_axis_dump (INFERRED), `0x01e12db4` imu_type_and_unsupported_cmd (INFERRED)
* **macro engine**: `0x01e05856` macro_engine_config (STRONG EVIDENCE)
* **protocol TX**: `0x01e0944e` armorx_ff_response_handler (PROVEN STATIC), `0x01e0642c` armorx_f7_response_build (STRONG EVIDENCE)
* **protocol parser**: `0x01e0701c` frame_err_head (PROVEN STATIC), `0x01e070da` frame_err_checksum (PROVEN STATIC), `0x01e06e8a` frame_err_length (PROVEN STATIC), `0x01e08772` frame_parse_and_dispatch (PROVEN STATIC)
* **stick**: `0x01e071fe` stick_curve_engine (STRONG EVIDENCE)
* **storage**: `0x01e2155a` sdfile_mount (STRONG EVIDENCE)
* **unknown opcode**: `0x01e08912` armorx_f9_handler (PROVEN STATIC), `0x01e0898e` armorx_fa_handler (PROVEN STATIC), `0x01e0914a` armorx_2f_handler (PROVEN STATIC)

Categories with no entry here stay unknown: checksum helper, D6/D8 handlers, lighting, USB host, Xbox, OTA, bootloader hooks, 0B handler. Absence is a statement about this pass, not about the firmware.
