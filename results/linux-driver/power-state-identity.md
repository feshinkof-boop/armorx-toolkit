# Power state selects the USB identity (2026-09-28)

Capture `results/experiments/armorx-power-button-20260928-160852/usbmon/power-button.pcap` (sha256 in the JSON artifact, not committed).

## The transition

Baseline: the body was connected by its own USB port with the **power button unpressed and a RED LED**.
In that state it was `413d:2106` - the same vendor HID personality as the F20 - and silent.

One physical action: press the power button ON. No cable was touched.

Result, on the same port `1-7`:

* two failed descriptor reads (-32), then a fresh enumeration
* `045e:0b12`, Microsoft, "Controller", bcdDevice 5.18, serial `09710769957143`
* xpad binds, `/dev/input/js0` appears
* GIP interrupt IN reports begin streaming at about 4 ms, 32 bytes each on 64-byte-max endpoints,
  with an announce packet and sequence-numbered type `0x20` packets carrying tag `0x2c 0x01`

## What this means

Vendor mode and Xbox mode are not separate hardware paths - they are **power states of the same unit**:

| state | LED | identity | behaviour |
|---|---|---|---|
| USB powered, unit off | red | `413d:2106` vendor HID | silent; companion-app/config channel |
| powered on | other | `045e:0b12` Xbox GIP | live 4 ms input stream via xpad |

That also explains the earlier F20 observations: its vendor-to-Xbox switch was not "association" per se
but the assembly powering up, and the reverse switch was the unit going back to standby.

## Unresolved

The body's Xbox identity presents exactly the same VID/PID/bcdDevice **and the same serial** as the F20's
Xbox identity. With only one controller available, "fixed firmware constant" and "forwarded from the
attached controller" cannot be told apart. A second controller with a different serial would settle it.
