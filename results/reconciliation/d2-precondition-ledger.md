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
| **write type (response vs no-response)** | UNKNOWN (no-response proven in 2.22/2.23 path) | write-without-response (PROVEN STATIC) | UNKNOWN | UNKNOWN | 2.23: BleDeviceInteractor::writeCharacterisiticWithoutResponse @0x4d0eb4 | POSSIBLY - the one untested difference |

Final column vocabulary: YES / NO / POSSIBLY / UNKNOWN.
