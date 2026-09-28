# Linux driver feasibility for the F20

## What is now proven live

Two mutually exclusive USB identities on port 1-7 (see f20-mode-switch.md):

1. **Vendor mode** (`413d:2106`, usage page 0xFF7A, 64-byte unfragmented input+output, no report ID,
   no input node). Silent with no controller.
2. **Xbox mode** (`045e:0b12`, GIP interfaces, xpad binds, `/dev/input/js0` appears) as soon as the
   wireless unit associates.

## Consequence for the target architecture

The planned chain `F20 -> hidraw/libusb -> armorx-inputd -> UHID -> SDL/Steam` is unnecessary for normal
gameplay: in Xbox mode the kernel's xpad already provides a standard joystick, and SDL/Steam/Proton see
`/dev/input/js0` normally. A userspace daemon only adds value if we want the *vendor* protocol (mode A)
for configuration, diagnostics or extra ArmorX features - and that path is a 64-byte vendor report on
usage page 0xFF7A that has not yet been observed carrying data.

Do not start a kernel driver. The remaining work is a userspace decoder for the mode-A report once a
sample with actual payload is captured, which requires a topology that keeps the receiver in mode A
while data flows (for example the vendor app on Windows, or a wired topology).
