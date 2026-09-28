#!/usr/bin/env python3
"""q32s_dump.py - dump a disassembly window from a cached q32s ELF.

Uses the vendor objdump with -start-address/-stop-address against the ELF produced by
q32s_analyze.py, so it is instant and does not re-wrap the image.

Usage: q32s_dump.py <elf> <start-hex> [<stop-hex>] [--no-raw]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import q32s_lib  # noqa: E402


def main(argv: list[str]) -> int:
    elf = argv[1]
    start = int(argv[2], 16)
    stop = int(argv[3], 16) if len(argv) > 3 else start + 0x200
    show = "--no-raw" not in argv
    print(q32s_lib.disassemble(pathlib.Path(elf), start=start, stop=stop, show_bytes=show))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
