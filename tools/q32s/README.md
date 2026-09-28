# q32s tooling (ArmorX firmware code navigation)

Offline, static analysis of the ArmorX V41 firmware image. No hardware, no BLE, no flashing.

## Toolchain

The disassembler is the vendor's own: JieLi's Linux toolchain, an **LLVM 4.0.1 fork** whose
registered targets are `pi32`, `pi32v2` and `q32s`. The AC63 SDK's `download.bat` names the same
toolchain (`C:/JL/pi32/bin/llvm-objdump.exe`) together with the `-address-mask=0x1ffffff` and
`-print-dbg` switches that produced the SDK's own `rom.lst`.

Source: JieLi package manager (`https://pkgman.jieliapp.com/s/linux-toolchain`, redirecting to
`jl-update.oss-cn-shenzhen.aliyuncs.com/jieli-linux-toolchains-20250805.1.tar.xz`).

Local state at the time of writing: the archive downloads to 27,253,727 bytes, but extraction
reports `Unexpected EOF`, i.e. **the local copy is a truncated archive**. The `q32s`, `common`
and `pi32v2` trees extract intact and were validated end-to-end anyway (see below), and the whole
validation was reproduced from a second extraction. Re-download to get a complete copy; the CDN
ETag md5 (`22a619513462abfc4d86ed50b2922ef7`) does not match the local copy's md5
(`cbfd672df512b63753b3e9b52050360e`), so the ETag is not a plain md5 of this object.

Point the tools at a toolchain with the `Q32S_TOOLCHAIN` env var (defaults to
`/home/salamanka/armorx-re/toolchains/jieli/jieli-linux-toolchains-20250324.1`).

## Why the wrapper exists

The firmware images are raw flash payloads with no ELF container, and LLVM 4.0 does not support
`--adjust-vma` or raw-binary disassembly. So the image is embedded as a `.text` section with the
vendor `clang` (`.incbin`) and linked at its true load address with the vendor `ld`; addresses in
the listing are then real firmware addresses.

## Pipeline

```bash
export Q32S_TOOLCHAIN=/path/to/jieli-linux-toolchains-*/
APP='research/firmware/2026-09-28/unpacked/cmp__*X*Pro*slot0/ji/files/app.bin'

python3.14 tools/q32s/q32s_validate.py                    # rom.lst cross-validation
python3.14 tools/q32s/q32s_analyze.py "$APP" 0x01E00000 v41   # disassemble + functions + xrefs
python3.14 tools/q32s/q32s_switch.py  "$APP" 0x01E00000 v41   # tbb switch tables
python3.14 tools/q32s/q32s_dispatch.py v41 "$APP" 0x01E00000 0x1e08772   # opcode -> handler map
python3.14 tools/q32s/q32s_dump.py <elf> 0x1e08860 0x1e08920 # window dump
python3.14 tools/q32s/q32s_reports.py                     # reports + symbol map
```

## Method notes that matter

* `-print-imm-hex` is required: without it the listing prints decimal immediates and cannot be
  compared against the vendor's own listing style.
* String pointers frequently land **inside** a literal (ANSI-escaped format strings, shared
  runs), so xref resolution must map a pointer to the containing literal and keep the suffix the
  pointer actually sees. Requiring an exact literal-start match loses ~90% of xrefs.
* `tbb`/`tbh` are PC-relative table branches with the case table inline in the instruction
  stream. The table is never executed, so a linear disassembly renders it as garbage. Entry
  counts come from the preceding bounds check; the base the entries are relative to is chosen by
  scoring, which is a best fit rather than a proof.
* The image is decoded **linearly from offset 0**, so "code coverage" is a decode rate, not a
  code/data split. Suspect data regions by `<unkown instruction>` markers and by never being a
  branch target.
* Function boundaries come from control-flow evidence (call targets, code after returns, the
  entry point), not from a symbol table.

## Verification

`q32s_validate.py` reconstructs the BD19 mask ROM from the bytes printed in the vendor's
`rom.lst` and re-disassembles it: **9,746 instructions compared, 100.0% exact text match, 100.0%
instruction-length match, identical branch targets.** `tests/test_q32s.py` pins this as a test
(plus parser, control-flow-target, switch-table and dispatcher-extraction tests).
