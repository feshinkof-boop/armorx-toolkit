# Frame-literal inventory (all commands, four builds)

Generated 2026-09-28 by `automation/scripts/frame-literal-scan.py` — the static backlog inventory
for the families adjacent to the F7/FC/F6 phase (AB motion/gyro, lighting, D8, config).

Each row is a frame the app builds as a `List<int>` literal. `cks ok = False` and `complete=False`
mark the frames whose bytes are runtime-computed (only the literal prefix is static; the writers
`writeDpiConfig` / `writeStepLengthConfig` are the known cases). The checksum column verifies the
`sum8`-over-preceding-bytes rule.

## 2.22.0901 (10 frames)

| group | opcode | function | addr | frame | len | complete | cks ok |
|---|---|---|---|---|---|---|---|
| sanity/version | 0B | `[closure] dynamic async_op(dynamic, dynamic,` | 0x7ab7f8 | `A5 04 0B B4` | 4 | True | True |
| sanity/version | 0B | `[closure] dynamic async_op(dynamic, dynamic,` | 0x7a9b8c | `A5 04 0B B4` | 4 | True | True |
| device write | 0E | `[closure] static dynamic async_op(dynamic, d` | 0x79c5d4 | `A5 05 0E 00 B8` | 5 | True | True |
| test mode | D2 | `[closure] dynamic async_op(dynamic, dynamic,` | 0x8e3be4 | `A5 05 D2 01 7D` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch1(/* No info */)` | 0x8e1efc | `A5 05 D2 00 7C` | 5 | True | True |
| input model | D4 | `[closure] dynamic async_op(dynamic, dynamic,` | 0x89adac | `A5 04 D4 7D` | 4 | True | True |
| config read | D6 | `[closure] dynamic async_op(dynamic, dynamic,` | 0x89bff8 | `A5 04 D6 7F` | 4 | True | True |
| config read | D6 | `[closure] dynamic async_op(dynamic, dynamic,` | 0x8a60f4 | `A5 04 D6 7F` | 4 | True | True |
| device UUID | EF | `[closure] dynamic async_op(dynamic, dynamic,` | 0x7aadd0 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| device UUID | EF | `[closure] dynamic async_op(dynamic, dynamic,` | 0x79c074 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |

## 2.23.0609 (12 frames)

| group | opcode | function | addr | frame | len | complete | cks ok |
|---|---|---|---|---|---|---|---|
| sanity/version | 0B | `_ getZKMVer(/* No info */) async` | 0x7617f4 | `A5 04 0B B4` | 4 | True | True |
| sanity/version | 0B | `_ getZKMVer(/* No info */) async` | 0x800610 | `A5 04 0B B4` | 4 | True | True |
| device write | 0E | `static _ writeDevice(/* No info */) async` | 0x7989bc | `A5 05 0E 00 B8` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch(/* No info */) async` | 0x8b1d68 | `A5 05 D2 01 7D` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch1(/* No info */)` | 0x881a78 | `A5 05 D2 00 7C` | 5 | True | True |
| input model | D4 | `_ getInputModel(/* No info */) async` | 0x8afa98 | `A5 04 D4 7D` | 4 | True | True |
| config read | D6 | `_ getDeviceConfig(/* No info */) async` | 0x8abc64 | `A5 04 D6 7F` | 4 | True | True |
| config read | D6 | `_ getDeviceConfig(/* No info */) async` | 0x810d2c | `A5 04 D6 7F` | 4 | True | True |
| device UUID | EF | `_ getDeviceUUID(/* No info */) async` | 0x791a30 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| device UUID | EF | `_ getDeviceUUID(/* No info */) async` | 0x7ff67c | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| DPI / transcribe | FC | `_ getDpi(/* No info */) async` | 0x8af8ec | `A5 05 FC 80 26` | 5 | True | True |
| DPI / transcribe | FC | `static _ writeDpiConfig(/* No info */) async` | 0x7fdee4 | `A5 05 FC 07` | 5 | False | None |

## 2.24.0919 (34 frames)

| group | opcode | function | addr | frame | len | complete | cks ok |
|---|---|---|---|---|---|---|---|
| sanity/version | 0B | `_ getZKMVer(/* No info */) async` | 0x78c208 | `A5 04 0B B4` | 4 | True | True |
| sanity/version | 0B | `_ getZKMVer(/* No info */) async` | 0x8975d4 | `A5 04 0B B4` | 4 | True | True |
| device write | 0E | `_ writeDevice(/* No info */) async` | 0x8a9e20 | `A5 05 0E 00 B8` | 5 | True | True |
| device write | 0E | `static _ writeDevice(/* No info */) async` | 0x8003b0 | `A5 05 0E 00 B8` | 5 | True | True |
| reset | 1A | `_ reset(/* No info */) async` | 0x8918f0 | `A5 05 1A 00 C4` | 5 | True | True |
| calibration | 1B | `_ startCalibration(/* No info */) async` | 0x887810 | `A5 06 1B 01 01 C8` | 6 | True | True |
| calibration | 1B | `_ startCalibration(/* No info */) async` | 0x9195dc | `A5 06 1B 00 01 C7` | 6 | True | True |
| calibration | 1B | `_ stopCalibration(/* No info */) async` | 0x8875f8 | `A5 06 1B 01 00 C7` | 6 | True | True |
| calibration | 1B | `_ stopCalibration(/* No info */) async` | 0x888b58 | `A5 06 1B 00 00 C6` | 6 | True | True |
| test mode | D2 | `_ testModeSwitch(/* No info */) async` | 0x911308 | `A5 05 D2 01 7D` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch(/* No info */) async` | 0x911308 | `A5 05 D2 00 7C` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch(/* No info */) async` | 0x91e380 | `A5 05 D2 01 7D` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch1(/* No info */)` | 0x93371c | `A5 05 D2 00 7C` | 5 | True | True |
| max size | D3 | `_ getMaxSize(/* No info */) async` | 0x9157c0 | `A5 04 D3` | 4 | False | None |
| input model | D4 | `_ getOnBoardConfig(/* No info */) async` | 0x91b988 | `A5 04 D4 7D` | 4 | True | True |
| config read | D6 | `_ getDeviceConfig(/* No info */) async` | 0x91433c | `A5 04 D6 7F` | 4 | True | True |
| config read | D6 | `_ getDeviceConfig(/* No info */) async` | 0x8a8798 | `A5 04 D6 7F` | 4 | True | True |
| connect mode | E1 | `_ getConnectModel(/* No info */) async` | 0x91b7a8 | `A5 04 E1 8A` | 4 | True | True |
| connect mode | E1 | `static _ writeConnectModeConfig(/* No info *` | 0x894b1c | `A5 06 E1 00 00` | 6 | False | None |
| MTU | E4 | `_ getMTU(/* No info */) async` | 0x897724 | `A5 04 E4 8D` | 4 | True | True |
| device UUID | EF | `_ getDeviceUUID(/* No info */) async` | 0x7b4c48 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| device UUID | EF | `_ getDeviceUUID(/* No info */) async` | 0x8972a4 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| logo colour | F5 | `_ getLogoColorConfig(/* No info */) async` | 0x91cc24 | `A5 04 F5 9E` | 4 | True | True |
| logo colour | F5 | `_ writeLogoColorConfig(/* No info */) async` | 0x8b9258 | `A5 0D F5` | 13 | False | None |
| legacy DPI | F6 | `_ getDpi(/* No info */) async` | 0x91b090 | `A5 05 F6 80 20` | 5 | True | True |
| legacy DPI | F6 | `_ getDpi(/* No info */) async` | 0x91b090 | `A5 04 F6 9F` | 4 | True | True |
| legacy DPI | F6 | `static _ writeDpiConfig(/* No info */) async` | 0x894000 | `A5 05 F6 07` | 5 | False | None |
| step-length (stick) | F7 | `_ getStepLength(/* No info */) async` | 0x91af58 | `A5 04 F7 A0` | 4 | True | True |
| step-length (stick) | F7 | `static _ writeStepLengthConfig(/* No info */` | 0x892cf4 | `A5 F7 7F 7F` | None | False | None |
| brightness compensation | F8 | `_ getBriCompConfig(/* No info */) async` | 0x91ae20 | `A5 04 F8 A1` | 4 | True | True |
| brightness compensation | F8 | `static _ writeBriCompConfig(/* No info */) a` | 0x892364 | `A5 07 F8 00 00` | 7 | False | None |
| DPI / transcribe | FC | `_ getDpi(/* No info */) async` | 0x91b090 | `A5 05 FC 80 26` | 5 | True | True |
| DPI / transcribe | FC | `_ startTranscribe(/* No info */) async` | 0x82d038 | `A5 0B FC 01` | 11 | False | None |
| DPI / transcribe | FC | `_ stopTranscribe(/* No info */) async` | 0x8293ec | `A5 0B FC 00` | 11 | False | None |

## 4.0.8 (40 frames)

| group | opcode | function | addr | frame | len | complete | cks ok |
|---|---|---|---|---|---|---|---|
| battery | 04 | `_ getBattery(/* No info */) async` | 0x8b672c | `A5 04 04 AD` | 4 | True | True |
| motion & gyro | 05 | `_ getMotionDpi(/* No info */) async` | 0xacea28 | `AB 05 05 25 DA` | 5 | True | True |
| motion & gyro | 05 | `_ getMotionList(/* No info */) async` | 0xace914 | `AB 05 05 26 DB` | 5 | True | True |
| motion & gyro | 05 | `static _ writeMotionDpiConfig(/* No info */)` | 0x946158 | `AB 07 05 25 00` | 7 | False | None |
| sanity/version | 0B | `_ getZKMVer(/* No info */) async` | 0x8b61fc | `A5 04 0B B4` | 4 | True | True |
| sanity/version | 0B | `_ getZKMVer(/* No info */) async` | 0x8b6ce4 | `A5 04 0B B4` | 4 | True | True |
| device write | 0E | `static _ writeDevice(/* No info */) async` | 0x827ddc | `A5 05 0E 00 B8` | 5 | True | True |
| reset | 1A | `_ reset(/* No info */) async` | 0x943668 | `A5 05 1A 00 C4` | 5 | True | True |
| calibration | 1B | `_ startCalibration(/* No info */) async` | 0x9e1a08 | `A5 06 1B 01 00` | 6 | False | None |
| calibration | 1B | `_ stopCalibration(/* No info */) async` | 0x9e17fc | `A5 06 1B 00 00` | 6 | False | None |
| lighting | 70 | `static _ writeApplyLightR3Common(/* No info ` | 0x844824 | `A5 04 70` | 4 | False | None |
| lighting | 70 | `static _ writeLightConfigR3(/* No info */) a` | 0x844e04 | `A5 10 70 02 00 0A FF FF` | 16 | False | None |
| light enable | 73 | `_ getLightEnableState(/* No info */)` | 0xa848e0 | `A5 04 73` | 4 | False | None |
| light enable | 73 | `_ setLightEnable(/* No info */)` | 0x848ae0 | `A5 05 73` | 5 | False | None |
| light enable | 73 | `_ setLightEnabled(/* No info */)` | 0x9e6340 | `A5 05 73` | 5 | False | None |
| light enable | 73 | `_ setLightEnabled(/* No info */)` | 0x9f4e74 | `A5 05 73` | 5 | False | None |
| test mode | D2 | `_ testModeSwitch(/* No info */) async` | 0xabaef4 | `A5 05 D2 01 7D` | 5 | True | True |
| test mode | D2 | `_ testModeSwitch(/* No info */) async` | 0xabaef4 | `A5 05 D2 00 7C` | 5 | True | True |
| max size | D3 | `_ getMaxSize(/* No info */) async` | 0xac313c | `A5 04 D3` | 4 | False | None |
| input model | D4 | `_ getInputModel(/* No info */) async` | 0xa84258 | `A5 04 D4 7D` | 4 | True | True |
| config read | D6 | `_ getDeviceConfig(/* No info */) async` | 0x80dbfc | `A5 04 D6 7F` | 4 | True | True |
| charging light | DD | `_ getChargingLightEffect(/* No info */) asyn` | 0xace808 | `A5 04 DD 86` | 4 | True | True |
| charging light | DD | `static _ writeChargingLightEffectConfig(/* N` | 0x9441a4 | `A5 07 DD` | 7 | False | None |
| connect mode | E1 | `_ getConnectModel(/* No info */) async` | 0xabd35c | `A5 04 E1 8A` | 4 | True | True |
| connect mode | E1 | `static _ writeConnectModeConfig(/* No info *` | 0x947444 | `A5 06 E1 00 00` | 6 | False | None |
| firmware read | E2 | `_ readFirmware(/* No info */) async` | 0x8b6860 | `A5 04 E2 8B` | 4 | True | True |
| MTU | E4 | `_ getMTU(/* No info */) async` | 0x8b60f0 | `A5 04 E4 8D` | 4 | True | True |
| device UUID | EF | `_ getDeviceUUID(/* No info */) async` | 0xacf618 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| device UUID | EF | `_ getDeviceUUID(/* No info */) async` | 0xab9084 | `A5 0C EF 00 00 00 00 00 00 00 00 A0` | 12 | True | True |
| logo colour | F5 | `_ getLogoColorConfig(/* No info */) async` | 0xa84a40 | `A5 04 F5 9E` | 4 | True | True |
| logo colour | F5 | `_ writeLogoColorConfig(/* No info */) async` | 0x848338 | `A5 0D F5` | 13 | False | None |
| legacy DPI | F6 | `_ getDpi(/* No info */) async` | 0x8b4e3c | `A5 05 F6 80 20` | 5 | True | True |
| legacy DPI | F6 | `_ getDpi(/* No info */) async` | 0x8b4e3c | `A5 04 F6 9F` | 4 | True | True |
| legacy DPI | F6 | `static _ writeDpiConfig(/* No info */) async` | 0x946750 | `A5 05 F6 00` | 5 | False | None |
| step-length (stick) | F7 | `_ getStepLength(/* No info */) async` | 0x8b4d30 | `A5 04 F7 A0` | 4 | True | True |
| step-length (stick) | F7 | `static _ writeStepLengthConfig(/* No info */` | 0x9445d4 | `A5 F7 00 10` | None | False | None |
| brightness compensation | F8 | `_ getBriCompConfig(/* No info */) async` | 0x8b4c24 | `A5 04 F8 A1` | 4 | True | True |
| DPI / transcribe | FC | `_ getDpi(/* No info */) async` | 0x8b4e3c | `A5 05 FC 80 26` | 5 | True | True |
| DPI / transcribe | FC | `_ startTranscribe(/* No info */) async` | 0x9afc1c | `A5 0B FC 01` | 11 | False | None |
| DPI / transcribe | FC | `_ stopTranscribe(/* No info */) async` | 0x9ac304 | `A5 0B FC 00` | 11 | False | None |

