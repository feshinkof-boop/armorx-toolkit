# Offline protocol and capture tools

These commands never touch a device. They exist so that a contributor can
analyse a capture, validate a fixture, or build a frame without owning hardware.

## Frame decoding

```bash
armorx protocol decode "A5 04 0B B4"
armorx protocol decode "A5 04 0B B4 A5 05 D2 01 7D" --stream
```

`--stream` walks pipelined frames using the length byte, so a raw byte dump can
be inspected without manual splitting. A frame with a bad checksum is reported
with `checksum_ok: false` rather than being silently dropped; pass
`require_checksum` through the Python API if you want strictness.

## Opcodes

```bash
armorx protocol opcodes
```

Every row carries an evidence level. Opcodes that were never recovered are absent
from the table, and `describe_opcode()` reports them as `unknown` rather than
inventing a name.

## Building frames offline

```bash
armorx protocol build --opcode 0B
armorx protocol build --opcode D2 --payload 01
armorx protocol build --opcode D7 --fragment 3 --payload "00 01 02"
armorx protocol describe-image --opcode D7 --image "<144 bytes>"
```

Building is construction only. The toolkit does not transmit, and there is no
command that sends bytes to hardware.

## Fragment reassembly

```python
from armorx import protocol

image = protocol.reassemble_a4(frames, opcode=0xD6)   # exactly 144 bytes
```

Reassembly is keyed by the fragment index because pipelined write-without-response
traffic can interleave fragments. A missing fragment raises instead of zero-filling.

## GIP input reports

```bash
armorx gip decode "<48 bytes>"
armorx gip forms
```

The parser exposes only proven fields and reports every byte it does not claim as
an `unknown_span`. It accepts both observed lengths, and the 32 to 48 byte
transition is recorded as unknown rather than explained.
