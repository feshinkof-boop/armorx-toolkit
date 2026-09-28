# F20 receiver: live USB enumeration (pristine, 2026-09-28)

Capture: `results/experiments/f20-usb-baseline-20260928-145536/` (usbmon0, tcpdump, started BEFORE insertion).
Operator ACK: `results/runtime/operator-actions/f20_connect_pristine.json`, clicked 2026-09-28T14:56:49-04:00.

## Identity - REVERIFIED LIVE

| field | value |
|---|---|
| bus / port | bus 1, **port 1-7** (xhci_hcd), device 5 |
| VID:PID | **413d:2106** (`Zikway` / `HID zk`) |
| bcdDevice | 1.00 |
| bcdUSB | 2.00 |
| speed | **full speed, 12 Mbps** |
| bDeviceClass | 0 (per-interface) |
| bMaxPacketSize0 | 64 |
| MaxPower | 400 mA, bus powered |
| configurations | 1, one interface |
| interface | 0, alt 0, class 3 (HID), subclass 0, protocol 0 |
| endpoints | `0x83` EP3 IN interrupt, `0x03` EP3 OUT interrupt, both **64 bytes**, bInterval 8 |
| HID | bcdHID 1.11, report descriptor length **29** |
| driver | `hid-generic` -> `hiddev1`, **hidraw2** |
| input nodes | **none** - no `/dev/input/eventN`, no `/dev/input/jsN` |

sudo-visible dmesg: `usb 1-7: new full-speed USB device number 5 using xhci_hcd`, then
`hid-generic 0003:413D:2106.0003: hiddev1,hidraw2: USB HID v1.11 Device [Zikway HID zk]`.

## Hypothesis status against live evidence

* `413D:2106` - **PROVEN LIVE**
* Usage page `FF7A` - **PROVEN LIVE** (first item of the report descriptor)
* `64-byte logical report` - **PROVEN LIVE** (report count 0x40 and wMaxPacketSize 0x40)

## Receiver-alone baseline (female port EMPTY, controller OFF)

During 155 s of continuous capture the F20 produced **12 interrupt IN URBs and 3 interrupt OUT URBs and
NO data on any of them** - every IN returned empty. Its last activity was at t=73.6 s, i.e. it went
**completely silent after enumeration**. So the receiver alone emits **no periodic reports**; there is no
"connection state" polled frame to observe until a wireless unit associates.
