# F20 USB init sequence

Enumeration is entirely standard: device descriptors, configuration, and one HID class request for the
29-byte report descriptor. Full detail is in the usbmon capture
`results/experiments/f20-usb-baseline-20260928-145536/usbmon/f20-insertion.pcap`, which was started
before insertion and runs continuously.

No vendor class control requests were observed during enumeration.
