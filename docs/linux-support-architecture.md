# Linux support architecture for the ARMOR-X Pro (Part G)

Decision document, written 2026-09-27/28. It answers one question per layer: where does support belong,
and why not somewhere else. Nothing here was built against hardware.

## The split that drives every decision

**Configuration support** (read/write the pad's settings: mappings, DPI, lighting, macros) and **game
input support** (make the pad behave like a game controller in games) are *different problems* with
different failure modes, and they must not be bundled behind one component.

- Configuration is a **BLE** activity on the custom FFE1/FFE2 service (`A5`/`A4` frames). It is
  request/response, low rate, and needs the protocol logic we have reconstructed.
- Game input, for a *Bluetooth* pad, is the **kernel/BlueZ input path** (`hidp`/`hog` → `uhid` →
  `/dev/input`), or, for a pad used as a plain HID device over USB, the in-kernel `usbhid`/`hid-generic`
  path. Applications consuming `evdev` need nothing from us.
- The 2.4 GHz dongle (F20-family receiver) is a **third** path: a vendor USB HID device (`413D:2106` on
  the Windows side) whose semantics live in vendor software, not in our BLE work.

## Layer-by-layer decisions

| layer | verdict | why |
|---|---|---|
| **userspace BlueZ D-Bus client** | **YES - this is the configuration support** | `bleak`/`dbus` already proved able to connect, subscribe and write on this unit; the protocol needs only GATT. No privileges beyond the user's Bluetooth access. |
| **a long-running daemon** | **YES, but thin and only for state** | the device is stateful (D2 is a runtime mode; config is a 144-byte image with a CRC). A daemon is justified to serialize access and to guarantee "D2 off before disconnect" - not to hold protocol logic that belongs in the client library. |
| **GUI backend** | **YES - a consumer of the daemon** | the GUI must not own the protocol or the device session; it calls the daemon so two windows cannot interleave writes on one link. |
| **`uinput` layer** | **NO for configuration; MAYBE for input remapping only** | `uinput` is for *injecting* input events. If we ever want to remap non-standard buttons into a virtual gamepad, that is a separate, input-side component - it has nothing to do with reading the configuration. |
| **kernel driver** | **NO** | everything needed is reachable from userspace: GATT for configuration, the existing HID/BT input stack for game input. A custom driver would add maintenance and breakage for zero capability gain, and it is not needed to write settings or to move button presses into games. |
| **USB / F20 layer** | **SEPARATE component, and diagnostic-first** | the dongle is a different transport with vendor semantics (see `windows-usb-static-closure.md`). It should be a separate module behind the same configuration abstraction, never tangled into the BLE client. |

## Consequence for the code we are building

The offline backend (Part H) implements the **configuration** side behind a transport interface, with
the BLE client as one implementation and a recorded/replay transport as another. That keeps the
protocol testable with no radio, and it makes the daemon a policy layer rather than a place where
protocol bugs hide.

## What this document deliberately does NOT claim

- It does not claim the pad's non-standard buttons are usable in games today: that is an *input-side*
  question (HID descriptor + the device's own modes), not answered here.
- It does not claim a kernel driver is required for anything we currently want to do.
- It does not claim the F20 dongle speaks the same protocol as the BLE link; the evidence points the
  other way (vendor `.ufw`/OTA toolchain on the Windows side).
