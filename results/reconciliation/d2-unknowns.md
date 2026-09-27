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
