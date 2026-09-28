# Direct ARMOR-X USB (2026-09-28)

Capture: `results/experiments/armorx-direct-usb-20260928-151903`, sha256 in `results/f20/direct-armorx-identity.json`.

## Result

The body, connected by its own USB port, is **byte-for-byte the same vendor personality as the F20**:
`413d:2106` Zikway "HID zk", bcdDevice 1.00, no serial, one HID interface, endpoints `0x83` IN / `0x03`
OUT both 64 bytes, and a **29-byte report descriptor with the identical SHA-256**
(`f0e418de...bb366f`) on usage page `0xFF7A`.

And it is **silent**. Over 357 s: 12 interrupt IN URBs, 3 interrupt OUT URBs, **zero payload-bearing
frames**, last activity at t=183.4 s. An A-button press at t\u2248290 s produced nothing at all.

## Why the operator had to disambiguate

The direct device is indistinguishable from the F20 by USB evidence alone - same IDs, same strings, same
descriptor hash, same endpoints, no serial - so the wire cannot say which unit it is. A one-shot popup
asked, and the operator answered ARMOR-X PRO body. **This conclusion would otherwise have been
unsupportable.**

## Identity is dynamic, and it round-trips

* insertion, no controller -> `413d:2106`
* wireless assembly associates -> `045e:0b12` (Xbox, xpad, js0), after two failed re-enumerations
* assembly powers off -> back to `413d:2106`, this time cleanly in one step
* body connected directly -> `413d:2106` again

## Consequence for the static USB-host trio

The device-side vendor interface carries no input, so the trio cannot be validated against it. The
architecture that remains consistent with everything observed is:

    Xbox controller -> ARMOR-X internal USB HOST -> normalized state -> state+0x1d4 -> D2

and the firmware strings now support it directly: the trio reference
`usbh_socket_en = %d, m_xbox_enum_step= %d, usbh_gamepad_ready= %d, usbh_gamepadp = %p` - a USB-host
socket enable, an **Xbox enumeration step** counter, and the gamepad pointer. That is host-side
enumeration of the attached controller, not a device-side report path.
