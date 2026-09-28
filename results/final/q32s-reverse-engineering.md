# Breaking the q32s bottleneck (offline, no hardware touched)

## Result in one line

The vendor's own q32s toolchain was located and put to work, so the ArmorX V41 firmware is now disassembled and navigable: instruction boundaries, call graph, string xrefs, switch tables and the ArmorX command dispatcher are all recovered statically.

## What was found and how it was verified

* The AC63 SDK build scripts name the toolchain explicitly: `download.bat` sets `OBJDUMP=C:/JL/pi32/bin/llvm-objdump.exe` and passes `-address-mask=0x1ffffff` and `-print-dbg`, i.e. the vendor's disassembler is a **custom LLVM fork** whose target for this chip is `q32s` (JieLi's public docs list AC632N/AW31N/AW33N as the q32s parts).
* JieLi publishes a **Linux** build of that toolchain; the q32s `objdump`, `clang` and `ld` used here come from it. `objdump -version` reports `LLVM version 4.0.1` with registered targets `pi32`, `pi32v2`, `q32s`.
* The firmware image is raw, so it is wrapped as a `.text` section via the vendor `clang` (`.incbin`) and linked at its real load base with the vendor `ld`; addresses in the listing are therefore true firmware addresses.

### Independent validation

The vendor SDK ships `rom.lst`, a full disassembly of the BD19 mask ROM. Because that listing prints raw instruction bytes, the ROM was reconstructed and re-disassembled with our pipeline: **9746 instructions compared, 100.0% exact text match, 100.0% length match** (AGREES with the vendor listing). This validates the ISA model, the wrap/link path and the address handling in one shot, and it was reproduced after a second extraction of the toolchain archive.

### V41 coverage

* image: 227440 bytes at 0x1e00000; 82944 instructions decoded; instruction sizes {'2': 56377, '4': 22386, '6': 4181}
* functions recovered (call targets + code after returns + entry): 1416
* calls resolved: 4662; string references: 879 to 759 distinct strings
* switch tables: 69 found, 48 at >=0.9 target-alignment confidence
* ROM/library symbol names available for cross-reference: 442

### Caveats (do not over-read the numbers)

* The image was disassembled **linearly from offset 0**, so the code percentage is a decode-rate, not a code/data split: string and data regions are decoded as instructions too. Regions whose decode contains `<unkown instruction>` or an address that is never a branch target are the ones to suspect as data.
* The switch-table base model is chosen by alignment scoring, which cannot fully discriminate because so much of the image decodes: the model recorded per table is a best fit, not a proof. Only tables at 1.0 confidence should be relied on without a second check.
* Function boundaries come from control-flow evidence, not from symbol tables; the boundary of a function that is only entered through a table is not guaranteed.

### Method summary

1. toolchain inventory from the SDK build scripts, then the vendor Linux toolchain;
2. raw image -> ELF32-q32s at 0x01e00000 (vendor clang + ld);
3. vendor objdump with `-print-imm-hex` (hex immediates, without which the listing cannot be matched against the vendor's own style);
4. structured parse into records (address, bytes, length, text, control-flow target, kind, referenced constants);
5. function recovery, call graph, string xrefs (resolving pointers that land *inside* a literal, which is the common case for ANSI-escaped format strings);
6. `tbb` switch-table recovery; dispatcher extraction.

