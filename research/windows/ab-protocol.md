# Windows DevMgr long-packet receive paths: A4 and AB — 2026-09-25

Advances the `0xAB` open question from `docs/usb-protocol.md` using the preserved
34 MB `objdump -d` disassembly of Assistant 1.0.6.1 `DevMgr.dll`
(sha256 653cb321…, working set `~/armorx_research/devmgr_static/`).

All labels below are PROVEN_STATIC (disassembly dataflow); device-side semantics
of AB remain UNKNOWN.

## Receive dispatcher: CUsbRecvThread::OnRecvData

The persistent receive worker dispatches on `packet[0]` (log tag
`CUsbRecvThread::OnRecvData` @0x10242a74):

```
0x1004a9a3:  cmp $0xA4,%al   -> A4 branch (Long Packet log @0x10242ad4)
0x1004ace0:  cmp $0xAB,%al   -> AB branch (Short Packet log @0x10242b08)
else                       -> A5 short path (dispatch to CUsbCmd/FromPacket, prior work)
```

## A4 branch (Windows mirror of the Android D6/D7 reassembly)

- Guard: frame length must be > 8 (`cmp $0x8,%edi; jbe skip` @0x1004a9ee) and
  fragment index must be 1 for the first fragment (`cmpb $0x1,0x3(%esi)` @0x1004a9f7).
- On fragment index 1: reads the 16-bit little-endian value at frame bytes 6..7
  (`mov 0x6(%esi),%ax` @0x1004aa01) as the total expected image size, allocates a
  0x20-byte `CRecvPacket` (ctor log `CRecvPacket::CRecvPacket` @0x10240fc4,
  call @0x1004aa74/0x1004aa8a; init helper 0x100429b0 @0x1004aaa0), and stores the
  expected total into the wrapper.
  - Frame bytes 6..7 of an A4/D6 or A4/D7 fragment-1 are image bytes 2..3 — the
    config's big-endian declared length (e.g. 0x0090 = 144) read here as LE
    0x9000>>8? — precisely: `ch=frame[6], cl=frame[7]; movzwl` yields
    `frame[7]<<8 | frame[6]`, i.e. big-endian read of image bytes 2..3 = the
    declared length. So the wrapper's expected size is exactly the config's
    declared length field. Cross-version note: Android reads the same declared
    length via checkConfigLength; the two clients agree on the envelope.
- Later fragments (index != 1) append via `CRecvPacket::Write`-family helpers
  (0x10042750 @0x1004ab26 appends, 0x10042940 @0x1004ab2e returns completion
  `al`); on completion the reassembled image is copied into a fresh 0x800-byte
  `CPacket` via `CPacket::Write` (0x1003dce0, log `CPacket::Write` @0x1023f4a4;
  buffer alloc 0x800 @0x1004abab) and delivered upward through the owner's
  vtable slot +8 (`call *0x8(%eax)` @0x1004ae44 in the AB path; same pattern in
  the A4 completion path).
- Fragment-1 arrival while a reassembly is already active restarts the wrapper
  (`cmpl $0x0,0x28(%eax)` @0x1004aacd -> re-init).

## AB branch (newly decoded)

- Entry: `cmp $0xAB,%al` @0x1004ace0, logged as `RECV->Short Packet` — the log
  label is misleading; the AB branch performs STREAM REASSEMBLY, not short-frame
  dispatch.
- The AB frame's own bytes 2..3 are read as a 16-bit BE length (`mov 0x2(%esi),%ax`
  @0x1004acfe, same `ch/al -> movzwl` decode as A4).
- The branch then:
  1. logs length (0x247 = line 583 source);
  2. validates an owner chain (`obj+0x24 -> +0x4 -> +0x84` @0x1004ad2f-0x1004ad3d,
     requiring a non-null callback object with `+0x90` flag clear);
  3. scans forward in the accumulated stream for the NEXT `0xAB` marker
     (`movb $0xab,-0x75(%ebp)` then search call 0x100165b0 @0x1004aebb) — i.e.
     AB frames are self-delimiting by their header byte, and reassembly collects
     everything between consecutive AB markers;
  4. writes the delimited span into a 0x800-byte `CPacket` via `CPacket::Write`
     (0x1003dce0 @0x1004ae26) and delivers it through the same owner vtable +8
     dispatch as A4;
  5. allocates a fresh 0x800 buffer for the next span.
- Conclusion: `0xAB` is a SECOND long-frame envelope on the same transport,
  delimited by start-marker scanning rather than fragment indices. No producer of
  AB was found in DevMgr.dll's send path except `CUsbSendThread::WriteToUsb`,
  which SENDS an AB frame when the queued packet's first byte is 0xAB
  (`cmp $0xab,%al` @0x1004a037) with special inter-transfer pacing:
  - if AB length (bytes 2..3) == 0x0E: `Sleep(500)` BEFORE the transfer
    (`push $0x1f4` @0x1004a0c2) and `Sleep(200)` AFTER (`push $0xc8` @0x1004a187);
  - if AB length == 0x70: `Sleep(10)` AFTER (`push $0xa` @0x1004a170);
  - both sends use the same `libusb_interrupt_transfer` (0x1004cc50) with
    timeout 0x1388 (5000 ms) and `m_nBulkSize` length.
- Android: no AB builder or parser exists in either analyzed APK build
  (UNKNOWN_ANDROID; the Android clients use A4 for long transfers).

## What remains UNKNOWN

- Which device or feature emits AB frames (the send path exists and is paced,
  implying real usage by some product, but no producer call site feeding an
  0xAB-first packet was identified beyond the WriteToUsb branch itself).
- The AB payload layout beyond the 2..3 length field and AB-marker delimiting.
- Whether the F20/ARMOR-X Pro pair ever produces AB traffic (no live AB capture).
