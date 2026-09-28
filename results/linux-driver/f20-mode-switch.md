# F20 dual identity: vendor HID <-> Xbox controller

Capture `results/experiments/f20-usb-baseline-20260928-145536` (usbmon0, tcpdump started before insertion, stopped after the
session; sha256 of the full-session pcap is in `results/f20/f20-dual-identity.json`).

## The finding

The receiver is not a fixed USB device. It switches identity on wireless association, on the **same
physical port 1-7**, with three failed re-enumeration attempts in between:

| kernel time | event |
|---|---|
| 19321.864 | usb 1-7: new full-speed USB device number 5 |
| 19322.001 | hid-generic 0003:413D:2106.0003: hiddev1,hidraw2 |
| 19341.276 | hid-generic 0003:413D:2106.0004: hiddev1,hidraw2 (again) |
| 19542.747 | usb 1-7: USB disconnect, device number 5 |
| 19543.118 | usb 1-7: new full-speed USB device number 6 |
| 19543.248 | unable to read config index 0 descriptor/start: -71 |
| 19543.839 | usb 1-7: new full-speed USB device number 7 |
| 19543.951 | device descriptor read/64, error -32 |
| 19544.276 | usb usb1-port7: attempt power cycle |
| 19544.655 | usb 1-7: new full-speed USB device number 8 |
| 19544.876 | New USB device found, idVendor=045e, idProduct=0b12, bcdDevice= 5.18 |
| 19544.876 | Product: Controller / Manufacturer: Microsoft / SerialNumber: 3039373130373639393537313433 |
| 19544.937 | input: Microsoft Xbox Series S|X Controller as .../1-7/1-7:1.0/input/input19 |
| 19544.957 | usbcore: registered new interface driver xpad |

## Mode A - no controller associated: vendor HID

`413d:2106` Zikway "HID zk", bcdDevice 1.00, full speed, one HID interface, endpoints `0x83` IN and
`0x03` OUT, both 64 bytes. The 29-byte report descriptor (sha256 in the JSON) is a single application
collection on **usage page 0xFF7A** with a 64-byte input and a 64-byte output, **no report ID and no
standard gamepad usages** - which is why the kernel makes `hidraw2` but no `/dev/input/event` node.

**Receiver-alone traffic: none.** Over 155 s: 12 interrupt IN URBs, 3 interrupt OUT URBs, zero bytes of
payload, last activity at t=73.6 s. There is no idle heartbeat to map.

## Mode B - controller associated: Microsoft Xbox controller

`045e:0b12`, bcdDevice 5.18, manufacturer Microsoft, product "Controller", serial `09710769957143`
(ASCII). Three vendor-specific interfaces (subclass 71, protocol 208 = Xbox GIP). Interface 0 is claimed
by **xpad**: `0x02` OUT 64 B bInterval 4, `0x82` IN 64 B bInterval 2. `/dev/input/js0` and `event18`
appear; the device is a normal joystick on this box.

Traffic jumps from 3 interrupt IN URBs to **17,164**, GIP shaped, roughly 8 ms cadence:

```
02 20 02 1c 7e ed 87 91 cf 24 00 00 5e 04 12 0b 05 00 18 00 04 00 00 00 08 04 01 00 01 00 01 00   <- GIP announce (0x02): VID 045e PID 0b12 bcd 0518
20 00 01 2c 01 00 00 ... f8 2a a6 0d f8 2a a6 0d                                                   <- GIP input (0x20), sequence 0x01
20 00 02 2c 01 00 00 ... 38 4a a6 0d 38 4a a6 0d                                                   <- sequence 0x02
```

Host side during init: `05 20 00 01 00`, `0a 20 01 03 00 01 14`, `06 20 02 02 01 00`.

## What this changes

The earlier expectation that the F20 keeps exposing its vendor HID interface while a controller is
connected is **contradicted**: in Xbox mode the HID interface is replaced by GIP interfaces. The
vendor-mode 64-byte FF7A report therefore belongs to the **no-controller / vendor-app** path, not to
normal gameplay, and any ArmorX vendor protocol on this receiver has to be reached in mode A.

## Not done

Per-control input mapping popups were not run this pass, the female USB port was left untouched, and the
static USB trio is still not correlated with these live fields.
