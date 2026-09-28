# D2 unknown ledger

UNKNOWN ID: D2-U-001
Question: Which write type does the 4.0.8 app use for the D2 enable?
Why unresolved: The 4.0.8 call site goes through a stored async callback; the write type is not encoded there
Evidence already checked: D2 enable call site 0xacf8cc -> 0xabaef4; the 2.22/2.23 path (write-without-response); LIVE differential variant A (Write Request 0x12) - refuted as an explanation of the silence
What would resolve it: decoding the callback target in 4.0.8 (static) - NOTE: no longer HIGH priority, because the write type demonstrably does not change device behaviour
Requires hardware: NO (static)
Risk: none
Priority: LOW (informational)

UNKNOWN ID: D2-U-002
Question: What is the 0x24 comparison in the 2.24 analysisData?
Why unresolved: Tagged Smi ambiguity (36 as a length vs 0x24 as an element)
Evidence already checked: 2.24 analysisData @0x91d130
What would resolve it: Fuller decode of that function
Requires hardware: NO
Risk: none
Priority: MEDIUM

UNKNOWN ID: D2-U-003
Question: What does byte[15]/[16] mean?
Why unresolved: The app's decoded page never reads them; our live capture saw LT move byte[15]
Evidence already checked: live captures; analysisData field reads
What would resolve it: A parser decode in another build, or an fw dump
Requires hardware: NO
Risk: none
Priority: LOW

UNKNOWN ID: D2-U-004
Question: What does the trailer byte[17] mean?
Why unresolved: Never read by the page; our captures carry a checksum there
Evidence already checked: analysisData
What would resolve it: static decode of another consumer
Requires hardware: NO
Risk: none
Priority: LOW

UNKNOWN ID: D2-U-005
Question: What does the alternate 4.0.8 branch @0xad0c80 do?
Why unresolved: Out of scope of the D2 question
Evidence already checked: the gate's failure target
What would resolve it: decode of that branch
Requires hardware: NO
Risk: none
Priority: LOW

UNKNOWN ID: D2-U-006
Question: Is the D2 echo itself meaningful to the device?
Why unresolved: The app discards it; we treat it as an ack
Evidence already checked: all four builds' gates
What would resolve it: a device-side observation
Requires hardware: YES
Risk: none
Priority: LOW

UNKNOWN ID: D2-U-007
Question: Why does the real unit not stream after a D2 enable?
Why unresolved: Not explained by anything in the reconstructed workflow
Evidence already checked: static reconstruction + 5 live variants + power states + config states
What would resolve it: device-side or firmware evidence (or a fw dump)
Requires hardware: YES
Risk: UNKNOWN
Priority: CRITICAL

UNKNOWN ID: D2-U-008
Question: Does the device require a bonded/encrypted link before it will report input in test mode?
Why unresolved: every harness run to date, including all four differential variants, used an unbonded, unencrypted link
Evidence already checked: static reconstruction (no bonding logic found in the app's D2 path); all live captures
What would resolve it: capture the official app's link against this unit and check whether bonding/encryption is established; then repeat variant C0 on a bonded link
Requires hardware: YES
Risk: low (pairing only; no configuration write)
Priority: HIGH

UNKNOWN ID: D2-U-009
Question: Do the official app's connection parameters (interval, latency, supervision timeout, MTU, link lifetime) differ from the harness's?
Why unresolved: not yet compared; no side-by-side session capture of app-vs-harness on the same unit
Evidence already checked: our own sessions show an MTU exchange and a stable link
What would resolve it: an HCI capture of the phone's session with the unit, diffed against ours
Requires hardware: YES (phone + unit)
Risk: none (passive capture)
Priority: HIGH

## Update — official-vs-harness session differential (2026-09-27, PARTIAL)

The official-app session could **not** be captured (`ANDROID_HCI_CAPTURE_UNAVAILABLE`: no ADB
transport to the phone). Consequences for the two open hypotheses — recorded as **narrowing, not
resolution**:

- **D2-U-008** (bonding/encryption prerequisite): **UNKNOWN, still open.** The harness link is now
  *measured* as unbonded and unencrypted (no pairing, no SMP, no encryption events in the HCI
  capture). The official side is unobservable, so this is neither supported nor refuted.
- **D2-U-009** (MTU / PHY / connection parameters / link lifetime): **UNKNOWN, partially narrowed.**
  Harness side measured: role Central, peer address type Public, connection interval **7.50 ms**,
  peripheral latency **0**, supervision timeout **2000 ms**, ATT MTU negotiated **64**
  (server 64 / client 517), one `LE Connection Update` at t≈24.9 s. PHY is **not reported** by this
  adapter's capture, so no PHY comparison is possible from our side alone. Official values:
  NOT_CAPTURED.
- **D2-U-007**: unchanged — still UNKNOWN, and explicitly **not** reclassified as a harness
  divergence, since the official behaviour has never been observed.

New harness-side observation (about our implementation, **not** evidence of a missing precondition):
`HARNESS_EXTRA_WRITE_D2_PRECLEAR` — the harness sends D2 OFF before the D2 enable; the
reconstructed official workflow showed no such pre-clear.

## Update — OFFICIAL ANDROID SESSION CAPTURED (2026-09-27, COMPLETE)

The official BIGBIG WON 4.0.8 session was captured on the real phone (vivo V2304A, HCI snoop via
bugreport; snoop sha256 bbaf10bd337a840ee0316291cd53f442859b55d8ce10c2414973d9c59248ba2f) and
compared with the preserved harness session. Classification: **OFFICIAL_WORKS_HARNESS_SILENT**.

- **D2-U-008** (bonding/encryption): **REFUTED.** The ArmorX is absent from the phone's 8 bonded
  devices; the capture contains 0 SMP frames and 0 encryption-change events. Official streams on an
  unbonded, unencrypted link — the same state as the harness.
- **D2-U-009** (MTU/PHY/connection parameters): **SUPPORTED (not causal).** MTU is equal (64 both;
  Android merely opened with the default 23 then exchanged 512->64) and no PHY update occurred, but
  the connection-interval profile differs: official 30->7.5->30->11.25 ms across four link-layer
  updates, harness 7.50 ms with one. This is the EARLIEST proven material difference
  (`OFFICIAL_CONNECTION_INTERVAL_DIFFERENT`).
- **D2-U-007** (why the harness is silent): **NARROWED, still UNKNOWN.** Eliminated by direct
  evidence: D2 value (`a505d2017d`), ATT write type (Write Command 0x52), handle (0x0075), the echo,
  MTU, CCCD behaviour (handle 0x0078), and security state — all identical between official and
  harness. Leading remaining candidate: the pre-D2 device-info + full-config read burst the harness
  omits (EF `a50cef0000000000000000a0`, E2 `a504e28b`, D4 `a504d47d`, D6 `a504d67f` + 8 reply
  fragments), observed ~9 s before the official D2 enable. Recorded as
  `EXTRA_OFFICIAL_WRITE_OBSERVED`, **not** as a proven precondition. Secondary candidate: the
  interval difference.
- The stream is **event-driven**: the official app received **0** frames while nothing was pressed
  and 155 frames while A was pressed (press/release/press/release, bit index 0). The harness's
  historical "0 idle frames" was therefore never evidence of failure by itself.
