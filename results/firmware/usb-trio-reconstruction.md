# USB-host parser trio - reconstruction status (2026-09-28)

Status: **structurally reconstructed, not field-matched.** No live host-side buffer has been observed,
so no offset equivalence with the PC-visible report is claimed.

| function | size | callers | calls | branches | switch table |
|---|---|---|---|---|---|
| `0x1e096b4` | 1056 | `0x1e0a6bc`, `0x1e0aff2`, `0x1e0e414` | 53 | 15 | `0x1e096cc` |
| `0x1e09ad4` | 524 | `0x1e0aff2` | 30 | 4 | `0x1e09ae8` |
| `0x1e09ce0` | 284 | `0x1e0aff2` | 14 | 13 | `0x1e09cfc` |

Diagnostic string referenced by `0x1e096b4` and `0x1e09ce0`:

```
usbh_socket_en = %d, m_xbox_enum_step= %d, usbh_gamepad_ready= %d, usbh_gamepadp = %p
```

## 0x1e09ad4 - enumeration/state dispatcher (new, instruction level)

```
0x1e09ad4  [--sp] = {rets, r6-r4}
0x1e09ad6  sp += -0xc0
0x1e09ad8  if (r0 > 0x6) goto 0x1e09c4c        ; default
0x1e09ae8  tbb [r0]
```

Seven cases, resolved from the range-gated table:

| case | target | shape |
|---|---|---|
| 0 | `0x1e09b35` | 36 instructions, 8 calls, writes three stack bytes |
| 1 | `0x1e09b9d` | **96 instructions, 19 calls** - the large arm, fills a stack record at `sp+168..171` |
| 2,3,4 | `0x1e09aee` | shared setup arm |
| 5,6 | `0x1e09b32` | 2 instructions, falls through |
| default | `0x1e09c4c` | out-of-range |

The shared arm `0x1e09aee` builds a transfer-like object:

```
0x1e09aee  r4 = [r4 + 0x0]
0x1e09af2  r0 = 0x1
0x1e09af4  b[r4 + 0x5] = r0
0x1e09af6  b[r1 + 0x9] = r0
0x1e09afa  r1 = 0xc00
0x1e09afe  h[r4 + 0x2] = r1          ; 3072
0x1e09b0c  h[r4 + 0x0] = r0
```

`0xc00` (3072 bytes) written into a halfword field of that object is a transfer/buffer length, which
places this arm in USB transfer setup, not in report parsing.

## 0x1e096b4 - parser with repeated big-endian 4-byte field extraction

Five sites repeat the same two-instruction sequence:

```
0x1e09750  r0 = r0 >> 0x10
0x1e0975a  r0 = r0 >> 0x8
0x1e09796 / 0x1e097a0   (same)
0x1e097da / 0x1e097e4   (same)
0x1e09852 / 0x1e0985c   (same)
0x1e0989e / 0x1e098a8   (same)
```

so the function extracts **big-endian** 32-bit fields, at least five of them. That is a real tension with
the live Xbox report, whose axis and trigger fields read as little-endian. It is recorded as an open
tension, not reconciled by assumption: the host-side buffer may be byte-swapped, or the fields it
extracts may not be the ones the PC sees.

## What remains open

* the identity of the host-side receive buffer and its length (no live capture of that bus exists)
* whether the big-endian extraction operates on the same fields as the PC-visible report
* the meaning of cases 0/1/5/6 beyond their shapes
* the store that carries host input into `state+0x1d4`
