#!/usr/bin/env python3
"""Tests for the q32s tooling: listing parser, control-flow targets, switch tables,
dispatcher extraction, and (when the vendor toolchain is present) end-to-end disassembly
validated against the vendor's own BD19 ROM listing.
"""
from __future__ import annotations

import json
import pathlib
import random
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools" / "q32s"))

import q32s_lib  # noqa: E402
import q32s_switch  # noqa: E402
import q32s_dispatch  # noqa: E402

ROM_LST = pathlib.Path(
    "/home/salamanka/armorx-re/jieli-tools/fw-AC63_BT_SDK/cpu/bd19/tools/rom.lst")
APP = next((REPO / "research/firmware/2026-09-28/unpacked").glob(
    "cmp__*X*Pro*slot0/ji/files/app.bin"), None)
BASE = 0x01E00000


def toolchain_available() -> bool:
    try:
        pathlib.Path(q32s_lib.tool("objdump")).exists()
        return True
    except Exception:
        return False


needs_toolchain = pytest.mark.skipif(not toolchain_available(),
                                     reason="vendor q32s toolchain not installed")
needs_rom = pytest.mark.skipif(not ROM_LST.exists(), reason="BD19 rom.lst not present")
needs_app = pytest.mark.skipif(APP is None or not APP.exists(), reason="V41 app.bin absent")


# ---------------------------------------------------------------- listing parser
SAMPLE = """
/tmp/fw.elf:\tfile format ELF32-q32s

Disassembly of section .text:

fw_start:
 1e00000:    76 01            \t[--sp] = {rets, r6-r4}
 1e00002:    c0 f3 05 28      \tgoto 0x500a <fw_start+0x22C1E : 1e022c1e >
 1e00006:    42 e0 05 30      \tif (r2 < 0x4) goto -0x6 <fw_start+0x0 : 1e00000 >
 1e0000a:    bf f3 7a fe      \tcall -0x30c <fw_start+0x4432 : 1e04432 >
 1e0000e:    c0 ff 8c fc 00 00\tr0 = 0xfc8c
 1e00014:    20 00            \trts
 1e00016:    46 01            \t<unkown instruction>
 1e00018:    11 70            \tr1 = 0x1
"""


def test_parse_listing_records_and_sizes():
    recs = q32s_lib.parse_listing(SAMPLE, BASE)
    assert [r["size"] for r in recs] == [2, 4, 4, 4, 6, 2, 2, 2]
    assert [r["addr"] for r in recs] == [BASE + 0, BASE + 2, BASE + 6, BASE + 0xA,
                                         BASE + 0xE, BASE + 0x14, BASE + 0x16, BASE + 0x18]
    assert recs[0]["raw"] == "7601"


def test_parse_listing_strips_debug_annotations_and_keeps_semantics():
    txt = ' 100000:    c0 f3 05 28      \tgoto 0x500a <_startup : 10500e >\t\t\t  ## startup.S:26:0\n'
    rec = q32s_lib.parse_listing(txt, 0x100000)[0]
    assert "##" not in rec["text"]
    assert rec["text"] == "goto 0x500a <_startup : 10500e >"


def test_targets_prefer_the_symbol_annotation():
    recs = q32s_lib.parse_listing(SAMPLE, BASE)
    assert recs[1]["target"] == 0x1E022C1E          # from the <... : addr > annotation
    assert recs[2]["target"] == 0x01E00000          # negative operand, measured from insn end
    assert recs[3]["target"] == 0x1E04432           # negative operand -> end-relative
    assert recs[4]["target"] is None                # plain constant load is not control flow


def test_operand_target_absolute_when_positive():
    # broadcast ROM/library calls print an absolute address with no annotation
    assert q32s_lib._operand_target("call 0x1fb7d2", 0x1E00000, 4) == 0x1FB7D2
    assert q32s_lib._operand_target("goto -0x10", 0x1E00000, 2) == 0x1E00000 - 0x10 + 2
    assert q32s_lib._operand_target("r0 = 0x10", 0x1E00000, 4) is None


def test_kind_and_mnemonic_classification():
    cases = {
        "call -0x30c <x : 1e04432 >": "call",
        "goto 0x500a <x : 1e022c1e >": "branch",
        "if (r2 < 0x4) goto -0x6": "branch",
        "rts": "ret",
        "[--sp] = {rets, r6-r4}": "store",
        "r0 = [r1 + 0x4]": "load",
        "r0 = 0xfc8c": "alu",
    }
    for text, kind in cases.items():
        rec = q32s_lib.parse_listing(f" 1000:    00 00 \t{text}\n", 0x1000)[0]
        assert rec["kind"] == kind, text


def test_parse_listing_never_crashes_on_garbage():
    rng = random.Random(1234)
    for _ in range(300):
        n = rng.randint(1, 24)
        body = "".join(rng.choice("0123456789abcdef \t<>:x+-=[]()ifgoto") for _ in range(n))
        line = f" 1e0000:    {' '.join('%02x' % rng.randrange(256) for _ in range(2))} \t{body}\n"
        q32s_lib.parse_listing(line, BASE)      # must not raise


def test_parse_listing_tolerates_truncated_and_empty_input():
    assert q32s_lib.parse_listing("", BASE) == []
    assert q32s_lib.parse_listing("no instructions here\n", BASE) == []
    assert q32s_lib.parse_listing(" 1e0000:    \t\n", BASE) == []


# ---------------------------------------------------------------- dispatcher
def _norm(text: str) -> str:
    """Compare instruction semantics, not symbol annotations, as q32s_validate.py does."""
    import re as _re
    return _re.sub(r"\s+", " ", _re.sub(r"<[^>]*>", "", text)).strip()


def _recs(spec):
    out = []
    a = BASE
    for text, tgt in spec:
        size = 4
        out.append({"addr": a, "size": size, "raw": "00000000", "text": text,
                    "mnemonic": q32s_lib._mnemonic(text), "target": tgt, "refs": [],
                    "kind": q32s_lib._kind(text, tgt is not None)})
        a += size
    return out


def test_dispatch_extracts_opcode_to_handler():
    spec = [
        ("if (r1 == 0xd7) goto 0x100 <fw : 1e00100 >", 0x1E00100),
        ("if (r1 != 0xf7) goto 0x200 <fw : 1e00200 >", 0x1E00200),
        ("r1 = b[r9 + 0x3] (u)", None),
    ]
    res = q32s_dispatch.extract(b"\x00" * 64, BASE, BASE, BASE + 0x40, _recs(spec))
    got = {e["opcode"]: e["handler"] for e in res["handlers"]}
    assert got[0xD7] == "0x1e00100"
    assert got[0xF7] == hex(BASE + 8)       # fall-through block after the != test
    assert res["handlers"][0]["evidence"].startswith("PROVEN STATIC")


def test_dispatch_ignores_non_opcode_and_out_of_range_constants():
    spec = [("if (r1 == 0x1e2) goto 0x100 <fw : 1e00100 >", 0x1E00100),
            ("if (r5 == 0xd2) goto 0x100 <fw : 1e00100 >", 0x1E00100)]
    res = q32s_dispatch.extract(b"\x00" * 64, BASE, BASE, BASE + 0x40, _recs(spec))
    assert res["handlers"] == []            # >0xFF value and non-opcode register both dropped


def test_dispatch_tracks_a_named_opcode_register():
    spec = [("if (r8 == 0xd6) goto 0x100 <fw : 1e00100 >", 0x1E00100)]
    recs = _recs(spec)
    assert q32s_dispatch.extract(b"\x00" * 64, BASE, BASE, BASE + 0x40, recs)["handlers"] == []
    res = q32s_dispatch.extract(b"\x00" * 64, BASE, BASE, BASE + 0x40, recs, opcode_reg="r8")
    assert res["handlers"][0]["handler"] == "0x1e00100"


# ---------------------------------------------------------------- switch tables
def test_switch_table_recovery_path():
    # tbb at BASE+4, preceded by a bounds check giving 3 cases, table right after the branch
    entries = [0x10, 0x20, 0x30]
    body = b"\x34\x00" + b"\xa0\x00" + b"".join(e.to_bytes(2, "little") for e in entries)
    body += b"\x20\x00" * 8
    image = bytearray(b"\x00" * 0x100)
    image[4:4 + len(body)] = body
    recs = _recs([("if (r0 > 0x2) goto 0x80 <fw : 1e00080 >", 0x1E00080)])
    recs[0]["addr"] = BASE + 4
    tbb = {"addr": BASE + 6, "size": 2, "raw": "a000", "text": "tbb [r0]", "mnemonic": "tbb",
           "target": None, "refs": [], "kind": "branch"}
    recs.append(tbb)
    for tgt in (BASE + 0x18, BASE + 0x28, BASE + 0x38):
        recs.append({"addr": tgt, "size": 2, "raw": "2000", "text": "rts",
                     "mnemonic": "rts", "target": None, "refs": [], "kind": "ret"})
    tables = q32s_switch.find_tables(bytes(image), BASE, recs)
    assert len(tables) == 1
    t = tables[0]
    assert t["entries"] == 3 and t["op"] == "tbb"
    assert t["base_confidence"] == 1.0
    # entries are offsets from the table start: BASE+8 + 0x10 == BASE+0x18
    assert [int(c, 16) for c in t["cases"]] == [BASE + 0x18, BASE + 0x28, BASE + 0x38]


# ---------------------------------------------------------------- real data
@needs_rom
def test_real_rom_listing_parses_into_contiguous_runs():
    import re
    text = ROM_LST.read_text(errors="replace")
    ins = []
    for line in text.splitlines():
        m = re.match(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*\t", line)
        if m:
            ins.append((int(m.group(1), 16), bytes.fromhex(m.group(2))))
    assert len(ins) == 9747
    runs, cur = [], [ins[0]]
    for prev, nxt in zip(ins, ins[1:]):
        if nxt[0] == prev[0] + len(prev[1]):
            cur.append(nxt)
        else:
            runs.append(cur)
            cur = [nxt]
    runs.append(cur)
    assert len(runs) == 10
    assert sum(len(b) for _a, b in ins) == 27052


@needs_toolchain
@needs_rom
def test_vendor_toolchain_agrees_with_vendor_listing():
    """End-to-end: re-disassemble the reconstructed ROM and require an exact match."""
    import re
    text = ROM_LST.read_text(errors="replace")
    vendor = []
    for line in text.splitlines():
        m = re.match(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*\t(.*)$", line)
        if m:
            vendor.append({"addr": int(m.group(1), 16), "raw": bytes.fromhex(m.group(2)),
                           "text": re.split(r"\s+##", m.group(3))[0].strip()})
    runs, cur = [], [vendor[0]]
    for prev, nxt in zip(vendor, vendor[1:]):
        if nxt["addr"] == prev["addr"] + len(prev["raw"]):
            cur.append(nxt)
        else:
            runs.append(cur)
            cur = [nxt]
    runs.append(cur)
    work = pathlib.Path("/home/salamanka/.hermes/cache/scratch/q32s/test_romval")
    exact = compared = 0
    for i, run in enumerate(runs[:3]):          # first three runs keep the test quick
        image = b"".join(v["raw"] for v in run)
        base = run[0]["addr"]
        elf = q32s_lib.wrap_and_link(image, base, work, tag=f"t{i}")
        mine = {r["addr"]: r for r in q32s_lib.parse_listing(q32s_lib.disassemble(elf), base)}
        for v in run:
            m = mine.get(v["addr"])
            if m is None:
                continue
            compared += 1
            exact += (_norm(m["text"]) == _norm(v["text"]))
    assert compared > 1000
    assert exact == compared


@needs_toolchain
@needs_app
def test_v41_image_disassembles_with_expected_entry_code():
    recs = None
    work = pathlib.Path("/home/salamanka/.hermes/cache/scratch/q32s/test_v41")
    image = APP.read_bytes()
    elf = q32s_lib.wrap_and_link(image[:0x400], BASE, work, tag="head")
    recs = q32s_lib.parse_listing(q32s_lib.disassemble(elf), BASE)
    assert len(recs) > 50
    assert all(r["size"] in (2, 4, 6) for r in recs)
    assert any(r["kind"] == "call" for r in recs)


@needs_app
def test_published_analysis_artifacts_are_consistent():
    q = REPO / "results" / "q32s"
    cov = json.loads((q / "v41-coverage.json").read_text())
    funcs = json.loads((q / "v41-functions.json").read_text())
    tables = json.loads((q / "v41-switch-tables.json").read_text())
    xrefs = json.loads((q / "v41-string-xrefs.json").read_text())
    assert cov["instructions"] > 80000
    assert cov["functions_recovered"] == len(funcs) > 1000
    assert cov["string_refs"] == sum(e["n_xrefs"] for e in xrefs)
    assert len(tables) > 50
    assert all(t["entries"] >= 2 for t in tables)
    assert all("handler" in h for h in json.loads(
        (REPO / "results" / "firmware" / "armorx-command-dispatch.json").read_text())["handlers"])
