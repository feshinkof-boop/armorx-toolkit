# D2 official-app vs Linux harness differential — 2026-09-27

This note records the sanitized live result of comparing a real BIGBIG WON 4.0.8 Android Button Test session with the preserved Linux/Bleak harness session on the same ARMOR-X Pro / ZJ-XT firmware 2741 unit.

## Verdict

**COMPLETE — `OFFICIAL_WORKS_HARNESS_SILENT`.**

The official app received valid 18-byte `A5 12 02` Button Test reports from the real ARMOR-X Pro. The preserved Linux harness session received none.

The D2 enable transaction itself is identical in both sessions:

```text
value:   A5 05 D2 01 7D
ATT op:  Write Command (0x52)
handle:  0x0075 (FFE1)
```

Therefore the current divergence is not explained by the D2 value, ATT write type, or characteristic handle.

## Important correction: D2 is event-driven

The official app produced **zero** `A5 12 02` frames while Button Test was idle.

During a controlled A-button-twice action, it produced **155 valid frames**. The observed state transitions were:

```text
PRESS    mask 00000001
RELEASE  mask 00000000
PRESS    mask 00000001
RELEASE  mask 00000000
```

Only bit 0 was set for A. While the button was held, valid 18-byte frames repeated at roughly 12 ms cadence.

This corrects an earlier experimental assumption: **zero idle D2 frames is normal and must not be used as a failure criterion.** Future D2 validation must include an actual physical button action.

## Connection/session comparison

| field | official Android session | Linux harness | result |
|---|---|---|---|
| role | Central | Central | same |
| peer address type | Public | Public | same |
| bonded | no | no | same |
| encrypted | no | no | same |
| ATT MTU | 64 | 64 | same |
| FFE1 / FFE2 / CCCD handles | 0x0075 / 0x0077 / 0x0078 | same | same |
| D2 enable | `A5 05 D2 01 7D` | same | same |
| D2 ATT op | Write Command 0x52 | same | same |
| final observed connection interval | **11.25 ms** | **7.50 ms** | different |
| idle `A5 12 02` frames | 0 | 0 | same |
| A-button frames | 155 | not obtained in preserved harness session | different test coverage |

No SMP or encryption-change events were present in the working official session, so bonding/encryption is not a prerequisite for the observed Button Test behavior.

PHY equality is **not** claimed: no PHY-update event was observed in the official trace, while the preserved Linux capture did not report a directly comparable PHY value.

## First application-level sequence difference

The official app performs a read-oriented device-info/config burst before enabling D2:

```text
connect
-> MTU / CCCD
-> EF
-> 0B
-> E2
-> D4
-> full D6 read
-> D2 enable
```

Observed requests included:

```text
EF  A5 0C EF 00 00 00 00 00 00 00 00 A0
0B  A5 04 0B B4
E2  A5 04 E2 8B
D4  A5 04 D4 7D
D6  A5 04 D6 7F
D2  A5 05 D2 01 7D
```

The preserved harness session instead used:

```text
connect
-> MTU / CCCD
-> 0B
-> D2 OFF pre-clear
-> D2 enable
```

The extra official `EF -> E2 -> D4 -> D6` reads are recorded as **`EXTRA_OFFICIAL_WRITE_OBSERVED`**, not as a proven missing precondition. Correlation is not causality.

Likewise, the harness-only D2 OFF pre-clear is a protocol-sequence difference, not yet a proven cause.

### D4 note

This official 4.0.8 session observed:

```text
TX: A5 04 D4 7D
RX: A5 07 D4 11 01 00 92
```

This is clean live evidence for this session. Historical conflicting D4 expectations remain separately documented until reconciled across their original contexts; this note does not erase that provenance.

## Hypothesis status

- **D2-U-008 — bonding/encryption prerequisite: REFUTED.** The official app streams on an unbonded, unencrypted link.
- **D2-U-009 — MTU/PHY/connection/session difference: SUPPORTED, not causal.** MTU is equal; PHY is not directly comparable; the connection-interval profile differs.
- **D2-U-007 — why the harness remains silent: NARROWED, still UNKNOWN.** The D2 value, ATT operation, handle, MTU, CCCD path, and security state no longer explain the difference.

The leading protocol-level candidates are now:

1. the harness's D2 OFF pre-clear;
2. the official pre-D2 read burst (`EF / E2 / D4 / D6`);
3. if those do not matter, the differing connection/session timing profile.

## Configuration integrity

A fresh D6 read after the official session matched the existing durable baseline SHA-256:

```text
bdef9c619dba4836c89073df6e63860a21ad26a1c0b92946ae68fb68a895beb6
```

This is a readback-integrity confirmation only. The baseline remains **DURABLE_OK** from the earlier write/readback/settle/power-cycle validation. Immediate readback alone remains **STAGED_OK**.

## Next controlled experiment

The next D2 test should use **real A-button input**, not idle-frame count:

1. current harness sequence, including D2 OFF pre-clear -> D2 ON -> press A twice;
2. if silent, remove the pre-clear -> D2 ON -> press A twice;
3. if still silent, reproduce only the documented read-oriented official burst `EF -> 0B -> E2 -> D4 -> D6`, then D2 ON -> press A twice;
4. only if all three fail, investigate the official 11.25 ms vs harness 7.50 ms connection-interval difference.

No undocumented command replay is justified by this result.
