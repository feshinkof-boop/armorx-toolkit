# BigBigWon `Upgrade Pack` (`.bup`) container format

Reverse-engineered offline from five real packages; all offsets verified against all five.

```text
offset  size  field
0x00    22    magic "BigBigWon Upgrade Pack" + 2 NUL
0x16    4     header version (0x00010000)
0x1A    1     sub-image count flag
0x1B    1     board/model code (0x1d=V41 body, 0x1e=V3600 dongle, 0x16=V32, 0x17=V3000, 0x00=V2224)
0x1F    0x04  version string, 4 chars ("V41", "V36", "V32", "V30", "2224")
0x2B    32    image name slot A (".ufw" name; "null.bin"/"1.bin" when unused)
0x5B    32    image name slot B
0x8B    4     slot A compressed span (u32 LE, optional)
then, per sub-image:
        n * { u32 compressed_len, u32 uncompressed_len, <zlib stream> }
```

## Payload encoding

* The payload is a **sequence of independently-compressed zlib blocks**, each inflating to exactly **32,768 (0x8000)** bytes (the last block may be shorter).
* Each block is preceded by an 8-byte record `(compressed_len, uncompressed_len)`.
* A block whose `compressed_len > uncompressed_len` is a zlib **stored** block (`78 9c 00 …`), i.e. incompressible data is passed through untouched.
* The decompressed result is a **raw JieLi flash image** (not a JieLi `.ufw` container, despite the `.ufw` in the slot name): it already contains `uboot.boot` + `isd_config.ini` + `app_dir_head` in JLFS layout.

## Verified instances

| package | image | compressed span | image bytes | chunks |
|---|---|---|---|---|
| `01战甲X Pro固件-V41.bup` | XT_XBOX_update_s_v41_20230208.uf | 35 chunks | 1,124,288 | 35 |
| `Firmware USB dongle V3600.bup` | XT_DONGLE_update_v36_20221116.uf | 31 chunks | 989,120 | 31 |
| `战甲pro固件V32.bup` | null.bin | 34 chunks | 1,109,440 | 34 |
| `接收器固件V3000-dongle.bup` | null.bin | 29 chunks | 937,920 | 29 |
| `ArmorX-Pro-Firmware-V2224.bup` | 1.bin | 32 chunks | 1,037,760 | 32 |

## Tooling

* `tools/firmware/armorx_bup.py` — strict, bounds-checked parser/unpacker (`info` / `walk` / `unpack` subcommands).
* `tools/firmware/armorx_fw_pipeline.py` — one command: hash → unpack → JieLi-unpack → manifest.
* `tools/firmware/armorx_fw_compare.py` — cross-version comparison table.

