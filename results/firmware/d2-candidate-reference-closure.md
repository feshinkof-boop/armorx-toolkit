# D2 candidate-buffer reference closure (V41, static)

The candidate has **four** references, and they form two report paths plus a copy in and a copy out.

| site | role |
|---|---|
| `0x1e0e29c`-`0x1e0e2c2` | 2nd variant builder - `r2 = sp+1080` **directly**, length `0x0e` or `0x1c` from `state+0x35` |
| `0x1e0e3c6`/`0x1e0e3d6` | second candidate-construction sequence (same packaging as `0x1e0da54`..) |
| `0x1e0db90` | copy OUT: `sp+1080 -> sp+996`, 28 bytes |
| `0x1e0cd24`-`0x1e0cd2e` | **population from `r13`**: 28 bytes copied INTO the candidate |

## The load-bearing one

`0x1e0e2b6`/`0x1e0e2c2`: `r0 = r14+0x24 ; r3 = r1 ; r2 = sp+1080 ; r1 = 0x2 ; call 0x1e0642c` - the 28-byte
variant sends the **candidate struct itself**, not a copy. So both variants share one candidate and one
serializer: **field order cannot differ between them** (option B refuted).

`0x1e0cd2e`: `r0 = r4 (sp+1080) ; r1 = r13 ; r2 = 0x1c ; call 0x2fa092` copies 28 bytes from `r13` into the
candidate. **This is a proven way for analogue LT/RT to reach `+0x0c`/`+0x0d`**, which is option A of the
brief and makes the packed-bit seeding a default/fallback rather than the sole source.

## Tool trap worth keeping

This disassembly renders **stack offsets in decimal** (`b[sp+1092]`) while globals are hex. A hex-only
store scan therefore misses every stack-based candidate write - which is exactly what happened in the
previous pass. Done deliberately here: offsets are handled in both forms.

## Still open

* whether `r13` is the live/analogue source (proven to exist, not proven to be the live one)
* the USB trio bodies (`0x1e096b4`, `0x1e09ad4`, `0x1e09ce0`) - head only, fifth pass deferred
* re-reading the raw live D2 corpus to check the real distribution of bytes 15/16
