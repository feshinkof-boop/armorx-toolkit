# Windows bridge probe timing review vs verified Android init — 2026-09-25

Reviews the standalone Windows probe (vendor_init_probe_v2, run 1) against the
now-verified Android initialization order, per the workflow requirement. No new
commands are proposed; this only evaluates timing/state fidelity.

## Verified Android vendor-command subsequence (2.23)

```
[connect]
  CCCD 01 00 on FFE2 (subscribeCharacteristic; interactor subScribeToCharacteristic)
  -> immediately: 0B (A5 04 0B B4)                  [no delay after subscribe]
0B reply -> store zkm -> GATT reads 2A24, 2A26, 2A19 (standard characteristics)
2A26 read completion -> EF (A5 0C EF 00×8 A0)      [gated on device-info read]
EF reply -> devUuid -> server register
[config page opened]
  500 ms Future.delayed -> D6 (A5 04 D6 7F)
```

Key gating facts (PROVEN_STATIC):
- 0B is NOT gated on any reply; it fires as soon as the FFE2 subscription is
  placed (armorx_pro_root build() path).
- EF IS gated on the 2A26 (Firmware Revision) GATT read completing — a standard
  characteristic read, not a vendor frame.
- D6 is page-triggered with a 500 ms delay after the config page opens.
- No sleeps exist between subscribe/0B/EF; each step is event-driven.

## Probe vs Android

| Android step | Probe (run 1) | Fidelity assessment |
|---|---|---|
| persistent IN | pre-posted IN, re-armed after each completion | matches vendor receive choreography |
| 0B | sent first | matches (0B ungated) |
| collect after 0B | collects | matches |
| EF after 2A26 read | sent second, after collect window | acceptable: the 2A26 gate is a GATT read unavailable over HID; sending EF after 0B's window approximates the order (0B reply -> ... -> EF). No evidence the device requires the 2A26 read first. |
| 500 ms before D6 | probe collects/idles before D6 | matches the only measured protocol delay |
| D6 | sent third | matches |
| E2 | not sent (gated on D6 reply) | matches plan |

## Recommendation (documented before any live use; NOT yet applied)

Keep the exact command bytes unchanged. If a future solid-white run is desired,
optionally insert the one Android-observed delay before D6 (500 ms) if the
probe does not already idle ≥500 ms there; no other timing change is justified
by the Android evidence. The 2A26 gate cannot and should not be emulated over
HID (standard GATT reads are not part of the HID transport).

## Live-gate status (unchanged)

Real send requires explicit operator confirmation: F20 LED SOLID WHITE,
ARMOR-X Pro ON, Xbox controller physically disconnected, 413D:2106 present,
no USB 045E node. Not confirmed during this pass — no live send performed.
