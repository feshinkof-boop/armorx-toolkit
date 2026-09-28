# ArmorX D7 persistence chain (V41)

Built from instruction evidence only; every claim names the instruction that shows it.

## Chain

### `0x1e09232` - D7 handler: memcpy(sp+560, frame+3, len-4); validate via 0x1e0566a(len 0x90); loop 4 slots

- 1e09240: call 0x2fdb80 (copy)
- 1e09248: call 0x1e0566a with r1 = 0x90
- 1e09254: call 0x1e06998 (slot -> digital bit)
- 1e0926c: call 0x1e05c66 (record write)

### `0x1e06998` - slot index -> digital-mask bit position

- 1e069a6: if ((r5 & 0x7800000) == 0) skip — mask bits 23..26
- 1e069ae/1e069b2: returns the bit position of the n-th set bit
- 1e069bc: returns 0x20 when not found
- consequence: the four D7 slots map to digital-mask bits 23..26 = M1..M4 in the live key map

### `0x1e05c66` - record writer: record = base + index*0xDC; memset 220; header [2]=0,[3]=0x0A,[5]=index,[6]=0x20; CRC-16 over [2..9] (len-2 where len=10); CRC stored big-endian at [0..1]; then [0x4850+0x1b4] = 3

- 1e05c78: r4 += r5 * 0xdc
- 1e05c84: call 0x301148 (memset 220)
- 1e05c88-1e05c92: header fields
- 1e05c98: call 0x1e05628 with r1 = 8
- 1e05ca0/1e05ca4: CRC written BE to [1],[0]
- 1e05cae: [0x4850 + 0x1b4] = 3

### `0x1e069c2` - FINALIZER: tail-calls the out-of-image library with (descriptor, arg, 0x90)

- 1e069c8: r1 = [0x4850 + 0x1b0] (the descriptor)
- 1e069ce: r2 = 0x90
- 1e069d4: goto 0x3003ec

### `0x3003ec` - LIBRARY CALL - the actual nonvolatile write (code absent from every artifact)

- args: r0 = descriptor, r1 = mode/flag byte (b[r5+0x42]), r2 = 0x90 (144)
- status: call site PROVEN STATIC; the callee's implementation is NOT in app.bin, not in the SDK rom.lst (which covers 0x100000-0x106fff only), not in p11_code.bin (4096 B), and not named by any ABSOLUTE symbol in the SDK linker scripts

### `0x1e059a2` - config slot select + reload: r0 = slot index (clamped to <= 2); descriptor = 0x3120 + index*0x400 + 0x44; stores it at [0x4850+0x1b0]; stores the active index at [0x4850+0x14]; calls 0x1e0580c

- 1e059b0: r0 = r4 << 0xa (index * 1024)
- 1e059b2: r8 = 0x3120
- 1e059ba: r1 = r0 + 0x44
- 1e059c4: [r12 + 0x1b0] = r1
- 1e059d4/1e059d8: call 0x1e0580c
- 1e059da: b[r12 + 0x14] = r4

### `0x1e0580c` - config slot validator/loader: validate(descriptor, 0x90) via 0x1e0566a; on failure print, then reset defaults via 0x1e056b6

- 1e05812: r1 = 0x90
- 1e05816: call 0x1e0566a
- 1e05818: if (r0 != 0) return (valid)
- 1e05824: call 0x1e056b6 (defaults)
- 1e0582e-1e05834: constants 0xc00 (=3*1024), 0x90, 0xdc, 0xdc in the diagnostic print

### `0x1e056b6` - reset defaults for a failed slot (called only from the loader's invalid path)

- 1e05826: call 0x1e056b6 with r0 = the descriptor

## Storage model

- **slots**: 3, index 0..2, stride 0x400 (1024 bytes)
- **slot_base**: 0x3120 + index*0x400
- **record_offset_within_slot**: 0x44
- **record_header**: [0..1] CRC-16/MODBUS big-endian over [2..len); [2..3] big-endian length; [4..] payload
- **config_record_length**: 0x0090 = 144
- **record_alloc_size**: 0xDC = 220 (the array at [0x4850+0x1b8])
- **active_slot_state**: [0x4850+0x14]
- **descriptor_state**: [0x4850+0x1b0]
- **write_indicator_state**: [0x4850+0x1b4] = 3 after a record write

## STAGED_OK vs DURABLE_OK

- **staged_ok**: PROVEN STATIC mechanism: the readback path (0x1e0921c and the loader) reads the descriptor at [0x4850+0x1b0], which points into the RAM/VM shadow at 0x3120 + index*0x400 + 0x44. A D7 write updates that shadow and the D7 handler then re-selects/reloads the slot (0x1e059a2 -> 0x1e0580c), so an immediate readback returns the new bytes without any flash commit.
- **durable_ok**: the commit is the out-of-image library call 0x3003ec from 0x1e069c2. Whether that call writes flash synchronously or leaves it to a VM flush is decided inside the library, which we do not hold.
- **classification**: STAGED_OK: PROVEN STATIC. DURABLE_OK trigger (timer/event/synchronous): NOT RESOLVABLE STATICALLY with the artifacts on disk - FW-U-032.

## Corrections

- The brief (and my earlier note) said config bytes 112..115 (0x70+i) gate which records D7 rewrites. The code maps slot i through 0x1e06998 to digital bit 23+i and then reads staging[0x70 + bit], i.e. config bytes 135..138. 112..115 is wrong; 135..138 is what the instructions index.
- 0x1e0aff2 is a 13,346-byte function that references 'switchd flash write add=%x, len=%d'; it is not a small mask-table helper as the previous pass implied. It is still not a protocol dispatcher (that part of the retirement stands).
