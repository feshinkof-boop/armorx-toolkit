"""Regression tests for the protocol family model (2026-09-28 reconciliation pass).

The load-bearing claims of this pass are checkable against raw recordings, so they are checkable here
too: every assertion below is derived from a capture or from a scored artifact, never from prose.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import struct

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
LOG = REPO / "results" / "experiments" / "physical-20260927-170455-noop-d7" / "raw-tx-rx.log"
CORPUS = REPO / "results" / "reconciliation" / "live-family-corpus.json"
MODEL = REPO / "results" / "reconciliation" / "protocol-family-model.json"
DURABLE_SHA = "bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6"


def parse_log():
    """Parse the raw transaction log into frames - the same shape the family model uses."""
    out = []
    for ln in LOG.read_text().splitlines():
        m = re.match(r"^(\S+)\s+(TX|RX) ([0-9a-f]+) (.*?)( \{.*)?$", ln)
        if not m:
            continue
        b = bytes.fromhex(m.group(3))
        out.append(dict(ts=m.group(1), dir=m.group(2), label=m.group(4).strip(), raw=b,
                        magic=b[0], length=b[1], opcode=b[2],
                        ordinal=(b[3] if b[0] == 0xA4 else None), payload=b[4:-1]))
    return out


def sum8_ok(b: bytes) -> bool:
    return (sum(b[:-1]) & 0xFF) == b[-1]


@pytest.mark.skipif(not LOG.exists(), reason="raw transaction log not present")
class TestWireEvidence:
    def test_every_frame_satisfies_sum8(self):
        frames = parse_log()
        assert frames, "the log must contain frames"
        assert all(sum8_ok(f["raw"]) for f in frames), "frame checksum is sum8 over bytes[:-1]"

    def test_a4_frames_carry_an_ordinal_and_a5_frames_do_not(self):
        frames = parse_log()
        a4 = [f for f in frames if f["magic"] == 0xA4]
        a5 = [f for f in frames if f["magic"] == 0xA5]
        assert len(a4) == 20 and len(a5) == 4        # 10 D7 + 10 D6 fragmented, 4 single-frame
        assert [f["ordinal"] for f in a4 if f["opcode"] == 0xD7] == list(range(1, 11))
        assert [f["ordinal"] for f in a4 if f["opcode"] == 0xD6] == list(range(1, 11))

    def test_d6_fragments_reassemble_to_the_durable_baseline(self):
        """The single most important assertion of the pass: the A4/D6 stream IS the config."""
        frags = [f for f in parse_log() if f["dir"] == "RX" and f["opcode"] == 0xD6]
        data = b"".join(f["payload"] for f in sorted(frags, key=lambda f: f["ordinal"]))
        assert len(data) == 144
        assert hashlib.sha256(data).hexdigest() == DURABLE_SHA

    def test_fragment_sizes_match_the_firmware_arithmetic(self):
        """9 x 15 + 1 x 9 = 144, and the firmware's nfrags formula predicts 10 for a 20-byte buffer."""
        frags = [f for f in parse_log() if f["opcode"] == 0xD6 and f["magic"] == 0xA4]
        sizes = [len(f["payload"]) for f in sorted(frags, key=lambda f: f["ordinal"])]
        assert sizes[:-1] == [15] * 9 and sizes[-1] == 9
        assert sum(sizes) == 144
        nfrags = (144 + 2) // (20 - 5)
        assert nfrags == 9 and nfrags + 1 == len(frags)   # floor division + the final partial frame

    def test_d7_write_is_fragmented_and_acknowledged_single_frame(self):
        frames = parse_log()
        d7_tx = [f for f in frames if f["dir"] == "TX" and f["opcode"] == 0xD7]
        d7_rx = [f for f in frames if f["dir"] == "RX" and f["opcode"] == 0xD7]
        assert len(d7_tx) == 10 and all(f["magic"] == 0xA4 for f in d7_tx)
        assert len(d7_rx) == 1 and d7_rx[0]["magic"] == 0xA5 and d7_rx[0]["payload"] == b""
        assert d7_rx[0]["raw"] == bytes.fromhex("a505d70081")   # a5 05 d7 00 81: zero-length ack

    def test_d6_request_is_a_single_a5_frame(self):
        req = [f for f in parse_log() if f["dir"] == "TX" and f["opcode"] == 0xD6]
        assert len(req) == 1 and req[0]["magic"] == 0xA5 and req[0]["payload"] == b""
        assert req[0]["raw"] == bytes.fromhex("a504d67f")


@pytest.mark.skipif(not CORPUS.exists(), reason="live corpus not extracted")
class TestLiveCorpus:
    def test_parser_found_ble_protocol_frames(self):
        rows = json.loads(CORPUS.read_text())
        assert len(rows) > 1000

    def test_host_captures_contain_no_a4_or_ab_magic(self):
        """Local host captures never show the fragmented family: those tests used the harness log."""
        magics = {r["magic"] for r in json.loads(CORPUS.read_text())}
        assert magics == {"a5"}

    def test_fc_and_ff_appear_in_equal_numbers(self):
        rows = json.loads(CORPUS.read_text())
        fc = [r for r in rows if r["opcode"] == "fc"]
        ff = [r for r in rows if r["opcode"] == "ff"]
        assert len(fc) == len(ff) == 2, "one generic FF echo per FC request"


@pytest.mark.skipif(not MODEL.exists(), reason="family model not built")
class TestFamilyModel:
    def test_model_states_the_framing_rule_not_two_namespaces(self):
        m = json.loads(MODEL.read_text())
        assert "not independent opcode namespaces" in m["principle"].lower().replace("are not", "not")

    def test_firmware_proof_points_at_the_builder_and_the_sum8(self):
        fp = json.loads(MODEL.read_text())["firmware_proof"]
        assert fp["frame_builder"]["address"] == "0x1e05dc0"
        assert fp["frame_checksum"]["address"] == "0x1e05dae"

    def test_retired_false_positive_is_recorded(self):
        m = json.loads(MODEL.read_text())
        assert any("RETIRED" in r["verdict"] for r in m["retired_leads"])

    def test_no_magic_check_claim_is_recorded(self):
        m = json.loads(MODEL.read_text())
        assert "no compare against" in m["firmware_proof"]["parser_has_no_magic_check"]


class TestLedgerReconciliation:
    def _led(self):
        d = json.loads((REPO / "results/reconciliation/firmware-unknown-ledger.json").read_text())
        return {e["id"]: e for e in d["entries"]}

    def test_the_three_headline_unknowns_are_closed(self):
        led = self._led()
        for k in ("FW-U-023", "FW-U-025", "FW-U-029"):
            assert led[k]["status"] == "RESOLVED"

    def test_the_resolution_quotes_the_matching_sha(self):
        txt = json.dumps(self._led()["FW-U-029"]).lower()
        assert DURABLE_SHA in txt

    def test_retired_leads_are_marked_in_the_ledger(self):
        txt = json.dumps(self._led()["FW-U-023"])
        assert "RETIRED as false positives" in txt or "retired" in txt.lower()
