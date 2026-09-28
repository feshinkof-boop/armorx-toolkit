# ArmorX RT/LT writers (V41, static)

## The enumeration result

There is **no direct store anywhere in the image** that writes `0x4ecc+0x0c` (LT) or `0x4ecc+0x0d` (RT).
Scanning every `[reg + off]` access for `off` in `0x8c..0xa0` with per-function base resolution against
`0x4e40` produced zero writers. The **only** writer is the 28-byte struct copy at `0x1e0dadc`:

```
0x1e0dadc:  r1 = sp+1080 ; r2 = 0x1c ; r0 = r12+0x8c ; call 0x2f92e4
```

which runs only **after** `0x1e0dad2` finds the compared 14 bytes different. So `0x4ecc` is a mirror of the
last-sent state, not the live state.

## Where the live state is assembled

`sp+1080`, immediately before the compare:

```
1e0da54:  b[sp+1092] = sextra(r13, 8, 1)   ; struct+0x0c = packed BIT 8  (LT)
1e0da62:  b[sp+1093] = sextra(r13, 9, 1)   ; struct+0x0d = packed BIT 9  (RT)
1e0da60:  r2 = r0 >> 0x18
1e0da66:  if ((r2 & 0xf)  == 0) skip
1e0da72:  call 0x1e0a5f2 (r0 = r2, r1 = sp+1080)
1e0da76:  if ((r2 & 0xf0) == 0) goto exit
1e0da82:  call 0x1e0a656 (r0 = r2, r1 = sp+1080)
```

* The low and high nibbles of `r2` select **which producer fills the normalized struct** - a source mux.
* The LT/RT **digital** bytes at `+0x0c`/`+0x0d` are set from packed bits 8 and 9 *before* the producers run,
  so the producers can overwrite them with analogue values. That ordering is what a bit/analogue overlap needs.

## Consequence

The answer to "when is RT refreshed" is inside **`0x1e0a5f2`** and **`0x1e0a656`** - those two functions,
not any literal store to `0x4ecc`. They are now the bounded next target. RT is **not** claimed solved.
