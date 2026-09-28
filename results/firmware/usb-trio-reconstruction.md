# USB-host parser trio - bounded static pass (2026-09-28)

Status: **progressed, not complete.** No field-level reconstruction is claimed.

| function | size | callers | calls | branches | switch table |
|---|---|---|---|---|---|
| `0x1e096b4` | 1056 | `0x1e0a6bc`, `0x1e0aff2`, `0x1e0e414` | 53 | 15 | `0x1e096cc` |
| `0x1e09ad4` | 524 | `0x1e0aff2` | 30 | 4 | `0x1e09ae8` |
| `0x1e09ce0` | 284 | `0x1e0aff2` | 14 | 13 | `0x1e09cfc` |

All three contain their **own type dispatch**: `0x1e09ad4` tests `if (r0 > 0x6) goto 0x1e09c4c` and then
`tbb [r0]`, i.e. seven cases plus a default, with case targets including `0x1e09c0e` and `0x1e09c4c`.

## The decisive string

```
usbh_socket_en = %d, m_xbox_enum_step= %d, usbh_gamepad_ready= %d, usbh_gamepadp = %p
```

referenced by `0x1e096b4` and `0x1e09ce0`. It names a USB-host socket enable flag, an **Xbox
enumeration step** counter, the ready flag and the gamepad pointer. Combined with the live result that
the body's own USB is silent, this places the trio squarely in the ARMOR-X **USB host** path - the body
enumerating and reading the Xbox controller it is attached to - rather than in any device-side report
path.

## What is still open

* which of the seven `0x1e09ad4` cases corresponds to which device/enumeration state
* the report field offsets, because no live payload for this path has been obtained yet
* the exact store that reaches `state+0x1d4` from this path
