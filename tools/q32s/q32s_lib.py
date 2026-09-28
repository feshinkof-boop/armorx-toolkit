#!/usr/bin/env python3
"""q32s_lib.py - drive the vendor JieLi q32s toolchain to disassemble raw firmware images.

The vendor toolchain (LLVM 4.0.1 fork, registered targets pi32 / pi32v2 / q32s) ships a
`objdump` that understands ELF32-q32s. Our firmware images are raw flash/`.bin` payloads with
no ELF container, so we wrap the image as a section of a synthetic q32s object with the
assembler's `.incbin`, link it at its true load address with the vendor `ld`, and then
disassemble the resulting ELF. Addresses in the listing are then real firmware addresses.

Everything here is offline and read-only with respect to the firmware images.
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import tempfile

DEFAULT_TOOLCHAIN = pathlib.Path(
    "/home/salamanka/armorx-re/toolchains/jieli/jieli-linux-toolchains-20250324.1")
TOOLCHAIN = pathlib.Path(os.environ.get("Q32S_TOOLCHAIN", DEFAULT_TOOLCHAIN))

#: address mask used by the vendor's own build scripts (25-bit address space)
ADDRESS_MASK = "0x1ffffff"

_LINK_LD = """ENTRY(fw_start)
SECTIONS {
  . = %(base)#x;
  .text : { *(.text) }
  /DISCARD/ : { *(.strtab) *(.symtab) *(.shstrtab) *(.comment) *(.note*) *(.eh_frame) }
}
"""

LINE_RE = re.compile(
    r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}[ \t])+)\s*(.*)$")
# llvm-objdump prints targets as "<symbol+0xNN : 1e22c1e >" and raw constants as decimal
TARGET_RE = re.compile(r":\s*([0-9a-f]{4,8})\s*>")
HEXNUM_RE = re.compile(r"\b0x([0-9a-f]+)\b")
BR_RE = re.compile(r"^(?:if\s*\(.*?\)\s*)?(call|goto)\s+(-?(?:0x[0-9a-f]+|\d+))$")


class ToolchainError(RuntimeError):
    pass


def tool(name: str) -> str:
    for cand in (TOOLCHAIN / "q32s" / "bin" / name, TOOLCHAIN / "common" / "bin" / name):
        if cand.exists():
            return str(cand)
    raise ToolchainError(f"toolchain binary {name!r} not found under {TOOLCHAIN}")


def toolchain_info() -> dict:
    """Record exactly which vendor tools were used and their version output."""
    out: dict[str, object] = {"toolchain_dir": str(TOOLCHAIN)}
    for n in ("objdump", "clang", "ld"):
        try:
            p = subprocess.run([tool(n), "--version"], capture_output=True, text=True, timeout=120)
            out[n] = (p.stdout + p.stderr).strip().splitlines()[:4]
        except Exception as e:  # pragma: no cover - diagnostics only
            out[n] = f"unavailable: {type(e).__name__}"
    return out


def wrap_and_link(image: bytes, base: int, workdir: pathlib.Path, tag: str = "fw") -> pathlib.Path:
    """Wrap a raw image into an ELF32-q32s linked at `base`; return the ELF path."""
    workdir.mkdir(parents=True, exist_ok=True)
    raw = workdir / f"{tag}.bin"
    raw.write_bytes(image)
    asm = workdir / f"{tag}_wrap.s"
    asm.write_text(f'    .section .text\n    .globl fw_start\nfw_start:\n'
                   f'    .incbin "{raw.name}"\n')
    obj = workdir / f"{tag}_wrap.o"
    r = subprocess.run([tool("clang"), "-target", "q32s", "-c", asm.name, "-o", obj.name],
                       cwd=workdir, capture_output=True, text=True, timeout=600)
    if not obj.exists():
        raise ToolchainError(f"clang failed: {r.stdout}{r.stderr}")
    lds = workdir / f"{tag}.ld"
    lds.write_text(_LINK_LD % {"base": base})
    elf = workdir / f"{tag}.elf"
    r = subprocess.run([tool("ld"), "-T", lds.name, obj.name, "-o", elf.name],
                       cwd=workdir, capture_output=True, text=True, timeout=600)
    if not elf.exists():
        raise ToolchainError(f"ld failed: {r.stdout}{r.stderr}")
    return elf


def disassemble(elf: pathlib.Path, start: int | None = None, stop: int | None = None,
                show_bytes: bool = True) -> str:
    cmd = [tool("objdump"), "-D", f"-address-mask={ADDRESS_MASK}", "-print-imm-hex"]
    if not show_bytes:
        cmd.append("-no-show-raw-insn")
    if start is not None:
        cmd.append(f"-start-address={start:#x}")
    if stop is not None:
        cmd.append(f"-stop-address={stop:#x}")
    cmd.append(str(elf))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 and not r.stdout:
        raise ToolchainError(f"objdump failed: {r.stderr[:400]}")
    return r.stdout


def _operand_target(body: str, addr: int, size: int) -> int | None:
    """Resolve a call/goto target when llvm-objdump printed no symbol annotation.

    Encodings seen in the BD19 ROM listing: a negative operand is a PC-relative displacement
    measured from the end of the instruction; a positive operand in the library/ROM space is an
    absolute address (the 32-bit absolute call form).
    """
    m = BR_RE.match(body)
    if not m:
        return None
    op = m.group(2)
    v = int(op, 16) if op.lstrip("-").startswith("0x") else int(op)
    if v < 0:
        return addr + size + v
    return v


def parse_listing(text: str, base: int) -> list[dict]:
    """Parse llvm-objdump output into structured instruction records.

    Each record: addr, offset, size, raw, text, mnemonic, target (absolute or None),
    refs (absolute constant operands that fall inside the image), kind.
    """
    out: list[dict] = []
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        raw = bytes.fromhex(m.group(2).replace("\t", " ").strip())
        body = (m.group(3) or "").strip()
        body = body.split("\t")[0].strip()          # drop "## file.c:12" dbg annotations
        if not body:
            continue
        tgt = None
        tm = TARGET_RE.search(body)
        if tm:
            tgt = int(tm.group(1), 16)     # llvm-objdump resolved the address for us
        else:
            tgt = _operand_target(body, addr, len(raw))
        refs = []
        for hm in HEXNUM_RE.finditer(body):
            v = int(hm.group(1), 16)
            refs.append(v)
        rec = {
            "addr": addr,
            "size": len(raw),
            "raw": raw.hex(),
            "text": body,
            "mnemonic": _mnemonic(body),
            "target": tgt,
            "refs": refs,
            "kind": _kind(body, tgt is not None),
        }
        out.append(rec)
    return out


def _mnemonic(body: str) -> str:
    if body.startswith("if"):
        return "if"
    for kw in ("call", "goto", "rts", "rts=", "reti", "rti", "retx", "rete", "cli", "sti",
               "tbb", "usp", "ssp"):
        if body.startswith(kw):
            return kw.rstrip("=")
    if re.match(r"^r\d+\s*\+=|^-=|\*=|/=|&=\|\|=|\^=|=", body):
        return "mov"
    if body.startswith("["):
        return "store"
    if re.match(r"^r\d+ = \[", body):
        return "load"
    return body.split()[0][:16] if body.split() else "?"


def _kind(body: str, has_target: bool) -> str:
    if body.startswith("call"):
        return "call"
    if body.startswith("goto") or (body.startswith("if") and "goto" in body):
        return "branch"
    if body.startswith(("rts", "reti", "rti", "retx", "rete")):
        return "ret"
    if body.startswith("["):
        return "store"
    if re.match(r"^r\d+ = \[", body):
        return "load"
    if has_target:
        return "loadaddr"
    return "alu"


def analyze_image(image: bytes, base: int, workdir: pathlib.Path, tag: str = "fw") -> dict:
    """Full pass: wrap -> link -> disassemble -> parse. Returns a dict with records."""
    elf = wrap_and_link(image, base, workdir, tag)
    text = disassemble(elf)
    recs = parse_listing(text, base)
    return {"base": base, "size": len(image), "elf": str(elf), "raw_listing": text,
            "instructions": recs}
