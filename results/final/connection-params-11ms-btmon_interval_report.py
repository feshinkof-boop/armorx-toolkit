#!/usr/bin/env python3
"""
btmon_interval_report.py -- offline argument/validation helper.

Parses `btmon` TEXT output (e.g. `btmon -r capture.btsnoop > btmon.txt`, or a live
`btmon` transcript) and reports, for every connection event, the negotiated LE
connection interval -- plus who most plausibly initiated the change.

WHY THIS EXISTS
    The ARMOR-X Pro peripheral requests a 7.50 ms connection interval. Android
    clamps peripheral requests up to 11.25 ms (9 x 1.25 ms); Linux/BlueZ does not.
    Any 11.25 ms experiment therefore needs a deterministic read-out of the
    *negotiated* interval from the capture, not the value anyone asked for.
    "Ask" and "negotiated" differ, and this script prints both.

SAFETY
    This is a purely offline text parser. It never opens a socket, never talks to
    BlueZ/the kernel, and never touches an adapter. Input is a file path.
    (btmon itself was run by someone else; this only reads its saved output.)

USAGE
    python3 btmon_interval_report.py <btmon-output.txt> [--json]
    python3 btmon_interval_report.py --self-test

EXIT CODES
    0 ok | 1 parse found nothing | 2 usage/IO error | 3 self-test failure

ATTRIBUTION MODEL (and its honest limits)
    btmon/HCI can see *that* an LE Connection Update command was issued and *that*
    an L2CAP Connection Parameter Update Request arrived. It CANNOT see whether the
    host application asked for a priority -- that is a host/userspace fact, invisible
    on the wire. So:

      PERIPHERAL_REQUEST : an L2CAP 0x12 "Connection Parameter Update Request" was
                           RECEIVED (i.e. the peer asked) shortly before the change.
      CENTRAL_REQUEST    : an L2CAP 0x12 was SENT by us (a central asking the peer),
                           or an HCI update was sent with no peer request.
                           => origin is host-side; app-vs-stack is NOT visible here.
      STACK_AUTOMATIC    : an HCI LE Connection Update was SENT by the host with no
                           L2CAP 0x12 on the wire either way.
                           => labelled STACK_AUTOMATIC by convention (nothing on the
                              wire says the app asked), NOT because the app is known
                              to be uninvolved.
      CONNECTION_ESTABLISHMENT : the LE Connection Complete event itself (no update).
      UNKNOWN            : change observed with no attributable precursor in-window.

    Treat CENTRAL_REQUEST/STACK_AUTOMATIC as "host-initiated, app intent unobservable".
    To close that gap, correlate with the platform log (e.g. Android
    `BluetoothGatt: onConnectionUpdated` / flutter_blue_plus MethodChannel traces).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNIT_MS = 1.25  # LE connection interval unit
SUPV_UNIT_MS = 10.0  # LE supervision timeout unit

# A precursor (L2CAP request / HCI update command) is associated with an update
# completion only if it precedes it by at most this many seconds.
PRECURSOR_WINDOW_S = 3.0

# Top-level btmon record markers.
_TL_RE = re.compile(r"^\s*[<>@!]\s+\S")

_RE_HANDLE_ADDR = re.compile(r"Handle:\s*(\d+)\s+Address:")
_RE_HANDLE_PLAIN = re.compile(r"^\s*Handle:\s*(\d+)\s*$")
_RE_TS = re.compile(r"(\d+\.\d+)\s*$")

_RE_CONN_INTERVAL = re.compile(r"Connection interval:\s*([\d.]+)\s*msec\s*\(0x([0-9a-fA-F]+)\)")
_RE_MIN_INTERVAL = re.compile(r"Min connection interval:\s*([\d.]+)\s*msec\s*\(0x([0-9a-fA-F]+)\)")
_RE_MAX_INTERVAL = re.compile(r"Max connection interval:\s*([\d.]+)\s*msec\s*\(0x([0-9a-fA-F]+)\)")
_RE_CONN_LATENCY = re.compile(r"Connection latency:\s*(\d+)")
_RE_SUPV = re.compile(r"Supervision timeout:\s*([\d.]+)\s*msec")
_RE_ROLE = re.compile(r"Role:\s*(\w+)")

# L2CAP LE signalling, numeric form (btmon prints both forms depending on version)
_RE_L2CAP_REQ_NUM = re.compile(
    r"Connection Parameter Update Request \(0x12\).*?\n"
    r"^\s*Min interval:\s*(\d+)\s*\n"
    r"^\s*Max interval:\s*(\d+)\s*\n"
    r"^\s*Peripheral latency:\s*(\d+)\s*\n"
    r"^\s*Timeout multiplier:\s*(\d+)",
    re.M,
)
_RE_L2CAP_RSP_NUM = re.compile(r"Connection Parameter Update Response \(0x13\)")
_RE_L2CAP_RESULT = re.compile(r"Result:\s*(.+?)\s*$", re.M)


@dataclass
class Record:
    index: int
    kind: str                  # CONNECTION_ESTABLISHMENT | CONNECTION_UPDATE
    handle: int | None
    time_s: float | None
    interval_ms: float
    interval_raw: int
    latency: int | None = None
    supervision_timeout_ms: float | None = None
    role: str | None = None
    initiator: str = "UNKNOWN"
    precursor: dict = field(default_factory=dict)
    line_no: int = 0


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _split_records(text: str) -> list[tuple[int, list[str]]]:
    """Split btmon text into (start_line_no, lines) top-level records."""
    out: list[tuple[int, list[str]]] = []
    cur: list[str] = []
    start = 0
    for i, line in enumerate(text.splitlines(), start=1):
        if _TL_RE.match(line):
            if cur:
                out.append((start, cur))
            cur = [line]
            start = i
        elif cur:
            cur.append(line)
    if cur:
        out.append((start, cur))
    return out


def _ts(lines: list[str]) -> float | None:
    for line in lines:
        m = _RE_TS.search(line.rstrip())
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def _handle(lines: list[str]) -> int | None:
    for line in lines:
        m = _RE_HANDLE_ADDR.search(line)
        if m:
            return int(m.group(1))
        m = _RE_HANDLE_PLAIN.match(line)
        if m:
            return int(m.group(1))
        m = re.search(r"LE Connection (?:Update )?Complete \(0x0\d\)", line)
    for line in lines:
        m = re.search(r"Handle:\s*(\d+)\b", line)
        if m:
            return int(m.group(1))
    return None


def parse(text: str) -> tuple[list[Record], list[dict]]:
    """Return (interval records, precursor events) in chronological order."""
    records: list[Record] = []
    precursors: list[dict] = []
    idx = 0

    for line_no, lines in _split_records(text):
        head = lines[0]
        blob = "\n".join(lines)
        ts = _ts(lines)
        direction = "sent" if head.lstrip().startswith(("<", "@ ")) else "received"
        if head.lstrip().startswith("@"):
            direction = "mgmt"

        # ---- L2CAP LE-signalling Connection Parameter Update Request (0x12) ----
        if "Connection Parameter Update Request (0x12)" in blob:
            req = {
                "line": line_no, "time_s": ts, "direction": direction,
                "min_raw": None, "max_raw": None, "latency": None, "timeout_raw": None,
            }
            m = _RE_L2CAP_REQ_NUM.search(blob)
            if m:
                req.update(
                    min_raw=int(m.group(1)), max_raw=int(m.group(2)),
                    latency=int(m.group(3)), timeout_raw=int(m.group(4)),
                )
            else:
                # Single-line / differently-formatted variants
                for key, pat in (
                    ("min_raw", r"(?i)min(?:\.|imum)? interval:\s*(\d+)"),
                    ("max_raw", r"(?i)max(?:\.|imum)? interval:\s*(\d+)"),
                    ("latency", r"(?i)peripheral latency:\s*(\d+)"),
                    ("timeout_raw", r"(?i)timeout multiplier:\s*(\d+)"),
                ):
                    mm = re.search(pat, blob)
                    if mm:
                        req[key] = int(mm.group(1))
            req["kind"] = "L2CAP_CONN_PARAM_UPDATE_REQUEST"
            precursors.append(req)
            continue

        if "Connection Parameter Update Response (0x13)" in blob:
            res = re.search(r"Result:\s*(.+)", blob)
            precursors.append({
                "line": line_no, "time_s": ts, "direction": direction,
                "kind": "L2CAP_CONN_PARAM_UPDATE_RESPONSE",
                "result": (res.group(1).strip() if res else None),
            })
            continue

        # ---- HCI LE Connection Update command (host -> controller) ----
        if "HCI Command: LE Connection Update" in blob:
            mn = _RE_MIN_INTERVAL.search(blob)
            mx = _RE_MAX_INTERVAL.search(blob)
            precursors.append({
                "line": line_no, "time_s": ts, "direction": direction,
                "kind": "HCI_LE_CONNECTION_UPDATE_COMMAND",
                "min_raw": int(mn.group(2), 16) if mn else None,
                "max_raw": int(mx.group(2), 16) if mx else None,
                "min_ms": float(mn.group(1)) if mn else None,
                "max_ms": float(mx.group(1)) if mx else None,
            })
            continue

        # ---- LE Connection Complete / LE Connection Update Complete ----
        is_establish = "LE Connection Complete" in blob or "LE Enhanced Connection Complete" in blob
        is_update = "LE Connection Update Complete" in blob
        if not (is_establish or is_update):
            continue

        mi = _RE_CONN_INTERVAL.search(blob)
        if not mi:
            # A failed/aborted update carriers no interval; skip but keep the fact.
            if is_update:
                idx += 1
                records.append(Record(
                    index=idx,
                    kind="CONNECTION_UPDATE",
                    handle=_handle(lines), time_s=ts,
                    interval_ms=float("nan"), interval_raw=-1,
                    line_no=line_no,
                ))
            continue

        interval_ms = float(mi.group(1))
        interval_raw = int(mi.group(2), 16)
        lat = _RE_CONN_LATENCY.search(blob)
        sup = _RE_SUPV.search(blob)
        role = _RE_ROLE.search(blob)

        idx += 1
        records.append(Record(
            index=idx,
            kind="CONNECTION_ESTABLISHMENT" if is_establish else "CONNECTION_UPDATE",
            handle=_handle(lines),
            time_s=ts,
            interval_ms=interval_ms,
            interval_raw=interval_raw,
            latency=int(lat.group(1)) if lat else None,
            supervision_timeout_ms=float(sup.group(1)) if sup else None,
            role=role.group(1) if role else None,
            line_no=line_no,
        ))

    _attribute(records, precursors)
    return records, precursors


def _attribute(records: list[Record], precursors: list[dict]) -> None:
    for rec in records:
        if rec.kind == "CONNECTION_ESTABLISHMENT":
            rec.initiator = "CONNECTION_ESTABLISHMENT"
            rec.precursor = {"note": "creation-time interval; the LE Create Connection "
                                     "command carries the offered window"}
            continue

        cands = [
            p for p in precursors
            if p["time_s"] is not None
            and rec.time_s is not None
            and rec.time_s - PRECURSOR_WINDOW_S <= p["time_s"] <= rec.time_s
        ]
        if not cands:
            rec.initiator = "UNKNOWN"
            rec.precursor = {"note": "no attributable precursor within window"}
            continue

        # Precedence. An L2CAP Connection Parameter Update Request is the CAUSE of
        # the exchange; any HCI LE Connection Update command that follows it is the
        # stack *applying* the request, not an independent host decision. So look for
        # the most recent L2CAP request first, and only fall back to a bare HCI
        # command when the peer never asked.
        reqs = [p for p in cands if p["kind"] == "L2CAP_CONN_PARAM_UPDATE_REQUEST"]
        cmds = [p for p in cands if p["kind"] == "HCI_LE_CONNECTION_UPDATE_COMMAND"]

        chosen: dict | None = None
        if reqs:
            # The peer (or, for CENTRAL_REQUEST, we) opened the exchange; any HCI
            # command in the window is the stack applying it.
            chosen = reqs[-1]
        if chosen is None:
            chosen = cmds[-1] if cmds else cands[-1]

        last = chosen
        rec.precursor = last

        if last["kind"] == "L2CAP_CONN_PARAM_UPDATE_REQUEST":
            rec.initiator = "PERIPHERAL_REQUEST" if last["direction"] == "received" \
                else "CENTRAL_REQUEST"
            # Record the applying HCI command alongside the request so the read-out
            # shows the full round trip in one place.
            applier = [c for c in cmds
                       if c["time_s"] is not None and last["time_s"] is not None
                       and c["time_s"] >= last["time_s"]]
            if applier:
                rec.precursor = dict(last)
                rec.precursor["applied_by_hci_command"] = {
                    "line": applier[-1]["line"], "time_s": applier[-1]["time_s"],
                    "min_raw": applier[-1].get("min_raw"), "max_raw": applier[-1].get("max_raw"),
                }
        elif last["kind"] == "HCI_LE_CONNECTION_UPDATE_COMMAND":
            # No L2CAP request on the wire -> host-initiated; app intent unobservable.
            rec.initiator = "STACK_AUTOMATIC"
        else:  # a response we did not request; keep the update but flag it
            rec.initiator = "UNKNOWN"

        # A request immediately followed by our HCI update and a response is a
        # peripheral-request round trip -- record it explicitly.
        if rec.initiator == "PERIPHERAL_REQUEST":
            req = last
            if req.get("min_raw") is not None and rec.interval_raw >= 0:
                rec.precursor["applied_interval_raw"] = rec.interval_raw
                rec.precursor["requested_vs_applied"] = (
                    f"requested {req['min_raw']}/{req['max_raw']} "
                    f"-> applied {rec.interval_raw} "
                    f"({req['min_raw'] * UNIT_MS} ms -> {rec.interval_raw * UNIT_MS} ms)"
                )


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report(records: list[Record], precursors: list[dict], *, as_json: bool, src: str) -> str:
    if as_json:
        return json.dumps({
            "source": src,
            "connection_events": [asdict(r) for r in records],
            "precursors": precursors,
        }, indent=1, default=str)

    out: list[str] = []
    out.append(f"# btmon connection-interval report")
    out.append(f"# source: {src}")
    out.append(f"# records: {len(records)}   precursors: {len(precursors)}")
    out.append("")
    if not records:
        out.append("(no LE Connection Complete / Connection Update Complete events found)")
        return "\n".join(out)

    out.append(f"{'#':>3}  {'line':>6}  {'t(s)':>12}  {'handle':>7}  "
               f"{'interval':>10}  {'raw':>5}  {'lat':>4}  {'timeout':>9}  initiator")
    out.append("-" * 100)
    for r in records:
        iv = "n/a" if r.interval_raw < 0 else f"{r.interval_ms:g} ms"
        out.append(
            f"{r.index:>3}  {r.line_no:>6}  "
            f"{(f'{r.time_s:.6f}' if r.time_s is not None else '-'):>12}  "
            f"{(f'0x{r.handle:04x}' if r.handle is not None else '-'):>7}  "
            f"{iv:>10}  {(r.interval_raw if r.interval_raw >= 0 else '-'):>5}  "
            f"{(r.latency if r.latency is not None else '-'):>4}  "
            f"{(f'{r.supervision_timeout_ms:g} ms' if r.supervision_timeout_ms is not None else '-'):>9}  "
            f"{r.initiator}"
        )
    out.append("")

    # Peripheral-request round trips are the interesting case for this lab.
    trips = [r for r in records if r.initiator == "PERIPHERAL_REQUEST"]
    if trips:
        out.append("Peripheral-requested updates (requested vs negotiated):")
        for r in trips:
            note = r.precursor.get("requested_vs_applied", "?")
            out.append(f"  line {r.line_no}: {note}   (handle "
                       f"{f'0x{r.handle:04x}' if r.handle is not None else '?'})")
        out.append("")

    out.append("Intervals seen (negotiated):")
    seen: dict[float, int] = {}
    for r in records:
        if r.interval_raw >= 0:
            seen[r.interval_ms] = seen.get(r.interval_ms, 0) + 1
    for ms in sorted(seen):
        out.append(f"  {ms:g} ms (raw {int(round(ms / UNIT_MS))})  x{seen[ms]}")
    out.append("")
    out.append("NOTE: the wire shows whether the PEER asked; it cannot show whether the")
    out.append("      local APP asked. STACK_AUTOMATIC therefore means 'host-initiated,")
    out.append("      app intent unobservable from HCI' -- correlate with platform logs.")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Self-test (offline, synthetic fixture -- no adapter involved)
# ---------------------------------------------------------------------------

SELF_TEST_FIXTURE = """\
< HCI Command: LE Extended Create Connection (0x08|0x0043) plen 26   #8 [hci0] 4.100000
        Peer address: AA:BB:CC:DD:EE:FF (OUI AA-BB-CC)
        Min connection interval: 30.00 msec (0x0018)
        Max connection interval: 50.00 msec (0x0028)
> HCI Event: LE Meta Event (0x3e) plen 19                  #9 [hci0] 4.500000
      LE Enhanced Connection Complete (0x0a)
        Status: Success (0x00)
        Handle: 64
        Role: Central (0x00)
        Peer address: AA:BB:CC:DD:EE:FF (OUI AA-BB-CC)
        Connection interval: 30.00 msec (0x0018)
        Connection latency: 0 (0x0000)
        Supervision timeout: 5000 msec (0x01f4)
< HCI Command: LE Connection Update (0x08|0x0013) plen 14  #20 [hci0] 5.200000
        Handle: 64 Address: AA:BB:CC:DD:EE:FF (OUI AA-BB-CC)
        Min connection interval: 7.50 msec (0x0006)
        Max connection interval: 7.50 msec (0x0006)
        Connection latency: 0 (0x0000)
        Supervision timeout: 5000 msec (0x01f4)
> HCI Event: LE Meta Event (0x3e) plen 10                  #21 [hci0] 5.400000
      LE Connection Update Complete (0x03)
        Status: Success (0x00)
        Handle: 64 Address: AA:BB:CC:DD:EE:FF (OUI AA-BB-CC)
        Connection interval: 7.50 msec (0x0006)
        Connection latency: 0 (0x0000)
        Supervision timeout: 5000 msec (0x01f4)
> ACL Data RX: Handle 64 flags 0x02 dlen 16                #22 [hci0] 9.900000
      LE L2CAP: Connection Parameter Update Request (0x12) ident 1 len 8
        Min interval: 6
        Max interval: 6
        Peripheral latency: 0
        Timeout multiplier: 200
< ACL Data TX: Handle 64 flags 0x00 dlen 10                #23 [hci0] 9.901000
      LE L2CAP: Connection Parameter Update Response (0x13) ident 1 len 2
        Result: Connection Parameters accepted (0x0000)
< HCI Command: LE Connection Update (0x08|0x0013) plen 14  #24 [hci0] 9.902000
        Handle: 64 Address: AA:BB:CC:DD:EE:FF (OUI AA-BB-CC)
        Min connection interval: 11.25 msec (0x0009)
        Max connection interval: 11.25 msec (0x0009)
        Connection latency: 0 (0x0000)
        Supervision timeout: 2000 msec (0x00c8)
> HCI Event: LE Meta Event (0x3e) plen 10                  #25 [hci0] 10.100000
      LE Connection Update Complete (0x03)
        Status: Success (0x00)
        Handle: 64 Address: AA:BB:CC:DD:EE:FF (OUI AA-BB-CC)
        Connection interval: 11.25 msec (0x0009)
        Connection latency: 0 (0x0000)
        Supervision timeout: 2000 msec (0x00c8)
"""


def self_test() -> int:
    records, precursors = parse(SELF_TEST_FIXTURE)
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    check(len(records) == 3, f"expected 3 interval records, got {len(records)}")
    check(len(precursors) >= 4, f"expected >=4 precursors, got {len(precursors)}")
    if len(records) != 3:
        print("SELF-TEST FAILED:", *failures, sep="\n  ")
        return 3

    r0, r1, r2 = records

    check(r0.kind == "CONNECTION_ESTABLISHMENT", f"r0 kind {r0.kind}")
    check(r0.initiator == "CONNECTION_ESTABLISHMENT", f"r0 init {r0.initiator}")
    check(r0.interval_ms == 30.0, f"r0 interval {r0.interval_ms}")
    check(r0.interval_raw == 0x18, f"r0 raw {r0.interval_raw}")
    check(r0.handle == 64, f"r0 handle {r0.handle}")
    check(r0.role == "Central", f"r0 role {r0.role}")
    check(r0.supervision_timeout_ms == 5000.0, f"r0 supv {r0.supervision_timeout_ms}")

    check(r1.kind == "CONNECTION_UPDATE", f"r1 kind {r1.kind}")
    check(r1.initiator == "STACK_AUTOMATIC", f"r1 init {r1.initiator}")
    check(r1.interval_ms == 7.5, f"r1 interval {r1.interval_ms}")
    check(r1.interval_raw == 6, f"r1 raw {r1.interval_raw}")

    check(r2.kind == "CONNECTION_UPDATE", f"r2 kind {r2.kind}")
    check(r2.initiator == "PERIPHERAL_REQUEST", f"r2 init {r2.initiator}")
    check(r2.interval_ms == 11.25, f"r2 interval {r2.interval_ms}")
    check(r2.interval_raw == 9, f"r2 raw {r2.interval_raw}")
    check(r2.supervision_timeout_ms == 2000.0, f"r2 supv {r2.supervision_timeout_ms}")
    check("requested 6/6 -> applied 9" in r2.precursor.get("requested_vs_applied", ""),
          f"r2 requested_vs_applied {r2.precursor.get('requested_vs_applied')!r}")

    # Round-trip unit maths used throughout.
    check(abs(11.25 / UNIT_MS - 9) < 1e-9, "11.25 ms must be 9 units")
    check(abs(7.5 / UNIT_MS - 6) < 1e-9, "7.5 ms must be 6 units")

    if failures:
        print("SELF-TEST FAILED:")
        for f in failures:
            print("  -", f)
        return 3

    print("SELF-TEST PASSED")
    print(f"  {len(records)} interval records, {len(precursors)} precursors")
    print("  sequence: 30.00 ms (establishment) -> 7.50 ms (STACK_AUTOMATIC/stack) "
          "-> 11.25 ms (PERIPHERAL_REQUEST, clamped from 7.50 ms)")
    print()
    print(report(records, precursors, as_json=False, src="<synthetic self-test fixture>"))
    return 0


# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    args = [a for a in argv[1:] if not a.startswith("--")]
    as_json = "--json" in argv
    if len(args) != 1:
        print(__doc__)
        return 2

    try:
        with open(args[0], "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        print(f"error: cannot read {args[0]}: {exc}", file=sys.stderr)
        return 2

    records, precursors = parse(text)
    print(report(records, precursors, as_json=as_json, src=args[0]))
    return 0 if records else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
