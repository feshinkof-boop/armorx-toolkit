# ArmorX Pro V41 — Chinese package vs international package

## The size question, answered

```text
Chinese V41 zip        36,528,812 bytes
International RAR       6,070,709 bytes
difference             30,458,103 bytes
```

**The entire difference is the bundled Android application `BIGBIG_WON_2.22.1226.apk` (28,032,675 bytes) plus 3 Chinese-only text file(s), which the international package does not contain.**

The firmware payloads and the whole Windows updater tree are **byte-identical** in both.

## Byte-identical payloads

| file (CN, identical in INT) | size | SHA-256 |
|---|---|---|
| `BTUpgrade_V1.9/BTUpgrade.dll` | 340,512 | `dbb16755f15c99afa37e324cfbb1ec2cb25a2504ce66657fc37a8223f4917821` |
| `BTUpgrade_V1.9/BTUpgrade_HX.dll` | 364,576 | `c2ee97a4975182146b9093492e68a3336cdd529d97696ea4d013066ec9c4dda6` |
| `BTUpgrade_V1.9/BUpgrade.exe` | 2,088,960 | `385aeca9d1ead883ace8759a5362a01711e092c9f9808750dca6f4c4c0c4619c` |
| `BTUpgrade_V1.9/Devices.dll` | 2,135,040 | `e8888d62f792293f88170b5ffe1830d18d17039f08b8d839f010b762040f2a21` |
| `BTUpgrade_V1.9/Skin.dll` | 86,645 | `0ddb8d7c5b0b6efe904e6645c9fd95a48f968cd221de8908a7ea0b7f4184478f` |
| `BTUpgrade_V1.9/USBUpgrade.dll` | 8,704 | `fad660bc7e006c58f37db9d75b72bf30c089ef62fc4e72673cbfd424d247b5e5` |
| `BTUpgrade_V1.9/Upgrade.dll` | 2,489,856 | `d4a4bf0bca2b564a3616dc7c81983b4083e3387ad918a215d8013a9f07f283a3` |
| `BTUpgrade_V1.9/bugrade.log` | 1,951 | `b8cd424a86cfef31f55a45aef038b85176d9d23a15dd6c7604c95c560593cf29` |

## Chinese-only files

| file | size | SHA-256 |
|---|---|---|
| `01 升级教程 请看官网链接.txt` | 99 | `27c6009c7a8b06704658e2972a9fbb7f363967881193fe72e53ca6299d0f3108` |
| `01战甲X Pro固件-V41.bup` | 2,126,734 | `80eeaf1fe07ed8150cf288a3e0e522cab818ca46e3a13c0adc41f2235b08cc90` |
| `01接收器固件-V3600-dongle.bup` | 1,847,656 | `e9ef748e6e2d9e0859cba933851ff1649711387abe7ebeb4d28783324a9b8c6f` |
| `BIGBIG_WON_2.22.1226.apk` | 28,032,675 | `3fdbbae3c54c399aea6076e5edc65066420433db7c9e88d5f12a171670529c2c` |
| `更新日志 APP版本.txt` | 1,340 | `f571b9ea9a0c4b564d8bc689ce20d62e5365d58e81ed8ed056938801c6330afe` |
| `更新日志 固件版本.txt` | 2,707 | `a93eaeae5f7afa5dc4a3bd543e737092c19e27512725df0ae8a59671253b0bf6` |

## Consequences

* A user who already has the app can take **either** package; flashing either yields the same controller firmware.
* `BIGBIG_WON_2.22.1226.apk` is the **2.22** app generation, i.e. the CN package ships an app *older* than the 4.0.8 APK already analysed in this project — a historical artifact for the app-side timeline, not new firmware.

## Verdict

> Are the actual V41 firmware payloads identical? **YES** — `01战甲X Pro固件-V41.bup` and `Firmware ArmorX-Pro V41.bup` have the same SHA-256, as do the two V3600 dongle `.bup` files and all seven `BTUpgrade_V1.9/` files.

