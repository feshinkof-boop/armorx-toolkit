# D2 unknown ledger

UNKNOWN ID: D2-U-001
Question: Which write type does the 4.0.8 app use for the D2 enable?
Why unresolved: The 4.0.8 call site goes through a stored async callback; the write type is not encoded there
Evidence already checked: D2 enable call site 0xacf8cc -> 0xabaef4; the 2.22/2.23 path (write-without-response)
What would resolve it: A live variant test, or decoding the callback target in 4.0.8
Requires hardware: YES
Risk: low (toggle only)
Priority: HIGH

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
