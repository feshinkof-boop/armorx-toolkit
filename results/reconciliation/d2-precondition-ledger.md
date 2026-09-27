# D2 precondition ledger

| Candidate precondition | 4.0.8 | 2.24 | 2.23 | 2.22 | Evidence | Needed by harness? |
|---|---|---|---|---|---|---|
| 0B first | NO | NO | NO | NO | PROVEN STATIC: no such call on the D2 path | NO (we send it anyway; verified harmless-as-far-as-known) |
| EF first | NO | NO | NO | NO | PROVEN STATIC | NO |
| D4 first | NO | NO | NO | NO | PROVEN STATIC | NO |
| D6 first | NO | NO | NO | NO | PROVEN STATIC | NO |
| controller attached | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | no explicit check found; implied by the connection | POSSIBLY |
| specific gamepad mode | NO | NO | NO | NO | PROVEN STATIC (nothing reads D4 fields) | NO |
| specific onboard mode | NO | NO | NO | NO | PROVEN STATIC | NO |
| firmware/version threshold | NO | NO | NO | NO | PROVEN STATIC | NO |
| device enum branch | NO | NO | NO | NO | PROVEN STATIC | NO |
| FFE2 subscription | YES (after enable) | YES (after enable) | YES (after enable) | YES (at connect) | PROVEN STATIC | YES (we already do) |
| unsubscribe/re-subscribe | NO | NO | NO | NO | PROVEN STATIC | NO |
| MTU negotiation | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | no MTU code on this path | UNKNOWN |
| delay/timer | NO | NO | NO | NO | PROVEN STATIC | NO |
| additional start command | NO | NO | NO | NO | PROVEN STATIC | NO |
| UI state flag | NO | NO | NO | NO | PROVEN STATIC | NO |
| **write type (response vs no-response)** | **NO - live-tested** (variant A, ATT-verified `Write Request 0x12` + `Write Response 0x13`): echo only, 0 frames | write-without-response (PROVEN STATIC) | UNKNOWN (4.0.8) / write-without-response (PROVEN STATIC, 2.22/2.23) | `raw/tshark-att.txt`; @0x4d0eb4 | **NO (refuted)** |
| **CCCD renewal after the D2 enable** | **NO - live-tested** (variant B): 0 frames | NO | NO | `raw/att-control-plane.json` | **NO (refuted)** |
| **same-connection re-enable** | **NO - live-tested** (variant C): 0 frames | NO | NO | `raw/tshark-att.txt` | **NO (refuted)** |
| bonding / encryption state before input reporting | UNKNOWN | UNKNOWN | UNKNOWN | not tested; every run so far has been unbonded | POSSIBLY (new leading candidate) |
| connection parameters (interval / latency / timeout / MTU / link lifetime) | UNKNOWN | UNKNOWN | UNKNOWN | not compared against the official app | POSSIBLY (new leading candidate) |

Final column vocabulary: YES / NO / POSSIBLY / UNKNOWN.
