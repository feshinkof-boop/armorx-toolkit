# sp+24 provenance and the r13 copy source (V41, static)

## Answer

**sp+24 is a POINTER, not a tagged value.** The store that feeds the D2 copy is
`0x1e0aeba: [sp+24] = r13`, and `r13` was set at `0x1e0ae74` to `r14 + 0x1d4` - a plain address.
The tagged-pointer reading recorded in the previous pass is **refuted**: no high-byte tag is produced
at this store.

## Producer block `0x1e0ae74`-`0x1e0aec2`

```
0x1e0ae6c  call 0x1e094de(r0 = sp+40)     ; fill a 28-byte LOCAL input record at sp+40
0x1e0ae74  r13 = r14 + 0x1d4              ; the persistent record
0x1e0ae7e  call 0x2fbf4a(r13, sp+40, 0x1c); compare record vs local
0x1e0ae82  if (r0 == 0) goto 0x1e0aea6    ; equal -> skip the copy
0x1e0ae8a  call 0x2fbf36(r13, sp+40, 0x1c); copy ONLY when different
0x1e0aea6  call 0x1fb956                  ; tick
0x1e0aeaa  r0 = r0 - [r15 + 0x11c]
0x1e0aeb6  if (r0 < 0xa) goto 0x1e0bab8
0x1e0aeba  [sp+24] = r13                  ; only on this branch
```

So the object copied into the D2 candidate is the **28-byte persistent input-state record at
`[r14 + 0x1d4]`**, which maintains its own change detection (compare `0x2fbf4a`, copy `0x2fbf36`)
against a local record at `sp+40` filled by `0x1e094de`. `sp+24` holds its address, and only on the
branch where the tick delta is `>= 0xa`.

Related: `0x1e0cd36` uses `r7 = r8 + 0x1d6` (record+2) and passes `candidate+0x0c` with it to `0x1e0a114`.

## Not claimed

* The packed-word blocks (`0x1e0da40`, `0x1e0e390`) derive bits 8/9 from a value I have **not** proven is
  `sp+24`; register reuse across blocks is the likely explanation of the earlier tag reading, and it must
  be re-tested before any claim either way.
* The `r14` base value was not re-resolved this pass.

## Other writers of sp+24 in the region

`0x1e0ce0c`, `0x1e0d0ba`, `0x1e0d16e`, `0x1e0d57c`, `0x1e0d9c8` (all pointer saves/restores),
`0x1e0f586`, plus `0x1e0a082: b[sp+24] = r8` which is a **byte** store in a different function and does
not belong to this slot's use here.
