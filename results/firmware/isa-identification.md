# ArmorX firmware ISA identification — q32s (BD19) evidence

**Question:** which instruction set does the decrypted ArmorX `app.bin` use?
**Answer:** `STRONG EVIDENCE` for the JieLi **q32s** ISA (`ELF32-q32s`, the BD19 core) — the same
ISA as the AC63 SDK's own ROM.

## Method and result

The public AC63 SDK ships `cpu/bd19/tools/rom.lst`, a **full disassembly** of the BD19 ROM dump
(11,325 lines, 9,747 parsed instructions) annotated `file format ELF32-q32s`. It is an independent
encoding oracle: its byte columns give real, chip-specific instruction encodings with their lengths.

### Instruction length histogram (from `rom.lst`)

| length | count | share |
|---|---|---|
| 2 bytes | 6,588 | 67.6 % |
| 4 bytes | 2,539 | 26.0 % |
| 6 bytes | 620 | 6.4 % |

This 16/32/48-bit variable-length pattern is characteristic of the JieLi q32s/`pi32v2` family — not
ARM (4/2-byte Thumb), not RISC-V (2/4-byte), not 8051 (1–3 byte).

### Opcode-prefix enrichment test

The 48 most frequent two-byte prefixes in the ROM disassembly were counted in every decrypted
`app.bin` at **any byte alignment**, against a 1 MiB random baseline:

| image | size | prefix hits | hits per MiB |
|---|---|---|---|
| random baseline | 1,048,576 | 749 | 749 |
| V41 body `app.bin` | 227,440 | 21,552 | **99,362** |
| V32 body `app.bin` | 223,960 | 21,257 | **99,525** |
| V2224 `app.bin` | 204,564 | 19,573 | **100,329** |
| V3600 dongle `app.bin` | 192,536 | 18,408 | **100,252** |
| V3000 dongle `app.bin` | 179,376 | 17,050 | **99,669** |
| SDK `cpu/bd19/tools/ota.bin` | 223,440 | 22,975 | 107,819 |

**Enrichment ≈ 133×** over the random baseline, uniformly across body and dongle builds. A
non-code byte stream cannot produce this; the images are **q32s code**.

## Independent corroboration (SDK component identity)

* `cfg_tool.bin` in the ArmorX V41 image is **byte-identical** (SHA-256 `0ccc2fd57959…`) to
  `cpu/bd19/tools/cfg_tool.bin` in the stock AC63 SDK — the vendor ships the unmodified upstream
  config tool.
* `uboot.boot` and `p11_code.bin` are **byte-identical across all five packages** (body and dongle);
  `p11_code.bin` differs from the SDK's copy (vendor-modified resource), `cfg_tool.bin` does not.
* The SDK `ota.bin` is an OTA *container* (header lists `ble_ota.bin`), not a plain app image —
  useful as a stock reference but not directly diffable against `app.bin`.

## What is still missing

A **working offline disassembler/decoder for q32s** was not produced in this shift. `rom.lst` gives
encodings for ROM instructions only, and building a full variable-length decoder (with the
immediate/register field layout for all 2/4/6-byte forms) is a task of its own. Consequently:

* instruction boundaries in `app.bin` cannot yet be walked reliably;
* the frame dispatcher (`out cmd=%x,%x pa=%x`) and the D2/D6/D7/D8/FC/F7 handlers cannot yet be
  resolved by cross-referencing their debug strings;
* `FW-U-021` is therefore **PARTIALLY_RESOLVED**: the ISA is established, the decoder is not.

**Next offline step:** build the q32s decoder from `rom.lst` (it self-documents field layouts by
example) or obtain JieLi's own `objdump` (Windows `.exe` in the Windows SDK) and run it under an
emulated/compatible environment, then produce the canonical symbol map (phase 33/12).

## Provenance of the tooling used

See `research/firmware/2026-09-28/tool-provenance.json`. Public repositories, exact commits:

| repository | commit | date | URL |
|---|---|---|---|
| `fw-AC63_BT_SDK` | `fdc018de8162` | 2025-03-18 | https://github.com/Jieli-Tech/fw-AC63_BT_SDK.git |
| `jl-misctools` | `0a5b12db0ef3` | 2025-02-20 | https://github.com/kagaimiq/jl-misctools.git |
| `jl-uboot-tool` | `adb3f18889e8` | 2025-03-16 | https://github.com/kagaimiq/jl-uboot-tool.git |
| `Android-JL_OTA` | `4bf054e1ae6e` | 2026-07-02 | https://github.com/Jieli-Tech/Android-JL_OTA.git |

Only these four public repositories were used for **format knowledge** — none for hardware access.
No firmware was uploaded to any third-party service. A CRC shim
(`/home/salamanka/armorx-re/jieli-shim/crcmod.py`, pure-Python CRC-16, verified against the
`123456789` check values `0x31c3` (XMODEM) and `0x29b1` (CCITT-FALSE)) substitutes for the
`crcmod` dependency so the JieLi tools run unmodified.
