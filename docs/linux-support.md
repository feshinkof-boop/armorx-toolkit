# Linux support foundation

This document describes what the toolkit can and cannot do on Linux today, and
which parts are deliberately left unfinished until hardware is available.

## What works today, without hardware

* `armorx device list` walks `/sys/bus/usb/devices` and reports every USB device,
  marking the ones whose identity is recognized. It reads only files.
* `armorx device inspect <path|vid:pid>` explains one device, with the meaning
  and the *limits* of each recognition.
* `armorx device doctor` reports whether this machine could talk to hardware:
  sysfs availability, hidraw nodes and their readability, recognized identities,
  the xpad module, and what the GIP stream is expected to look like.
* `armorx.transport` provides a mock transport for tests and an optional
  read-only hidraw transport. Writes are refused.

## Recognized identities

```text
413D:2106   Zikway / "HID zk"   vendor HID personality, usage page 0xFF7A
                                endpoints 0x03 OUT and 0x83 IN, 64 bytes, 8 ms
045E:0B12   Microsoft / "Controller"   Xbox GIP personality, xpad binds interface 0
```

Two things must be said plainly, and the code says them too:

* `413D:2106` is **not** evidence of a radio-link state, a power state, or which
  physical unit is attached. The ARMORX Pro body and the F20 receiver present a
  byte-for-byte identical identity, including the 29-byte report descriptor, and
  expose no serial number, so software cannot tell them apart.
* `045E:0B12` is what an Xbox controller presents. Seeing it does not by itself
  prove an ARMORX Pro is in the path.

The one transition that was observed is a power transition: with USB connected
and the unit powered off, the device presents `413D:2106`; pressing the power
button re-enumerates it on the same port as `045E:0B12`, and xpad takes over.
The reverse transition was observed when the unit returned to standby.

## What is deliberately not implemented

* No kernel driver. No module needed to be written for the observed behaviour:
  in the Xbox personality the in-tree `xpad` driver already binds and produces a
  standard gamepad, and in the vendor personality the interface carried no input
  traffic in any capture.
* No userspace HID driver daemon. A daemon would only be justified if the vendor
  interface were later shown to carry input, which it has not been.
* No writes of any kind: no configuration, DPI, lighting, macro, RCSP, firmware
  or bootloader operations.

## Permission notes

Reading a hidraw node needs access to that node; on most distributions that means
group membership or a udev rule. The toolkit never asks for write access, and
`armorx device doctor` reports unreadable nodes as a diagnostic rather than an
error.

## What hardware would unblock

1. Confirming that a fresh device always enumerates as the vendor personality
   before the power button is pressed, with several power cycles.
2. Capturing the vendor interface while the companion app performs one known
   action, to establish whether it carries configuration traffic.
3. A larger set of GIP captures covering the first two minutes after
   enumeration, to explain the 32 to 48 byte transition.
