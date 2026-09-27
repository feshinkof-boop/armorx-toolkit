# Official app vs Linux harness — normalized session differential

**Overall status: PARTIAL.** The harness stage is fully captured and decoded. The official-app stage
was **not captured**: `ANDROID_HCI_CAPTURE_UNAVAILABLE` (no ADB transport, so no btsnoop, no
bugreport, no logcat). Comparison is therefore **staged-by-stage with the official column empty** —
and deliberately **not** substituted with guesses or with static-analysis assumptions.

## CONNECTION

| field | official | harness |
|---|---|---|
| captured | NO | yes |
| role | NOT_CAPTURED | **Central** |
| peer address type | NOT_CAPTURED | **Public** |
| connection interval | NOT_CAPTURED | **7.50 ms** (0x0006) |
| peripheral latency | NOT_CAPTURED | **0** |
| supervision timeout | NOT_CAPTURED | **2000 ms** (0x00c8) |
| PHY | NOT_CAPTURED | not reported by this adapter's capture |
| link-layer updates | NOT_CAPTURED | 1 `LE Connection Update` at t≈24.9 s |

## SECURITY

| field | official | harness |
|---|---|---|
| pre-existing bond | **UNKNOWN** (unreadable) | **none** |
| pairing / SMP activity | NOT_CAPTURED | **zero events** |
| encryption before D2 | NOT_CAPTURED | **not encrypted** |

The harness link is unbonded and unencrypted. That is the `D2-U-008` condition, now **measured** for
our side — but with no official capture, it remains an untested hypothesis, not a finding.

## ATT / GATT

| field | official | harness |
|---|---|---|
| ATT MTU (server rx / client rx) | NOT_CAPTURED | **64 / 517** → negotiated **64** |
| service/characteristic discovery | NOT_CAPTURED | Read By Group Type ×4, Read By Type ×1, Read ×8 |
| CCCD operation | NOT_CAPTURED | one write, handle `0x0078`, value `0100` |
| FFE1 / FFE2 handles | NOT_CAPTURED | `0x0075` / `0x0077` (CCCD `0x0078`) |
| notification enable timing | NOT_CAPTURED | before the 0B query (t≈25.0 s) |

## APPLICATION SEQUENCE

| step | official | harness |
|---|---|---|
| connection → first write | NOT_CAPTURED | CCCD subscribe |
| all writes before D2 | NOT_CAPTURED | CCCD subscribe → **0B query `a5040bb4`** → **D2 OFF `a505d2007c`** |
| 0B control query | NOT_CAPTURED | sent t=25.01 → reply `a5050b30e5` t=25.03 |
| D2 enable | NOT_CAPTURED | t=**28.52**, ATT **Write Command (0x52)** = write-without-response |
| D2 response | NOT_CAPTURED | 5-byte echo only (t=28.54) |

## RX

| field | official | harness |
|---|---|---|
| idle `A5 12 02` frames | NOT_CAPTURED | **0** |
| button frames | NOT_CAPTURED | 0 (no physical action was justified) |
| notifications total | NOT_CAPTURED | 4 (1× 0B reply, 3× D2 echoes) |

## EXIT

| step | official | harness |
|---|---|---|
| D2 disable | NOT_CAPTURED | t=38.53, Write Command, echo received |
| CCCD teardown | NOT_CAPTURED | none observed on the link before disconnect |
| disconnect | NOT_CAPTURED | `Disconnect Complete` at t≈42.1 s |

## Notable absences relative to the brief's expectations

The brief anticipated pairs such as `OFFICIAL_LINK_ENCRYPTED_BEFORE_D2 / HARNESS_UNENCRYPTED`. Only
the harness half of each pair could be measured, so **no paired finding is asserted**. The harness
values that *would* become interesting if the official session turns out to differ are recorded
above as measured facts, unpaired.

Also observed here that was **not** in the static reconstruction: BlueZ issues a link-layer
`LE Connection Update` shortly after connecting, and the harness sends a **D2 OFF before the D2
enable** (a pre-clear our harness adds; the official static workflow showed no such pre-clear).
That second one is a real harness-side extra, recorded as `HARNESS_EXTRA_WRITE_D2_PRECLEAR` — an
observation about **our** side, not evidence about the missing precondition.
