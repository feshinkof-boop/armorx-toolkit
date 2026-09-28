# RT change-mask provenance (2026-09-28)

## The two operands

```
0x1e0cf44  r4 = [sp+1080]        ; candidate mask (candidate + 0x00)
0x1e0cef8  r4 = r2 | 0x200       ; same memory, built with bit 9 SET
0x1e0cef4  r1 = r2 & 0xfffffdff  ; same memory, bit 9 CLEARED  (0xfffffdff == ~0x200)
0x1e0cf48  r5 = [r15 + 0x1d0]    ; persistent mask field
0x1e0cfce  r0 = r5 & r4
```

**Correction to the previous pass**: I called `r5 & r4` a changed-bit set. It is not. Both operands are
masks - one persistent (`r15+0x1d0`), one current (the candidate mask) - so the expression is an
**intersection**, not a change.

## The gate

```
0x1e0cf4c  if ((r5 & r4) == 0) goto 0x1e0d012
```

When the intersection is empty the synthesis block is skipped entirely. So the digital trigger bytes are
written only when a bit is present in **both** the persistent field and the current mask.

## Edge class

```
0x1e0cfc0  r0 = b[r15+0x25]     ; toggle state
0x1e0cfca  b[r15+0x25] = r1     ; stored back
```

The toggled value selects the rising arm (write `0xff`) or the falling arm (write `0x00`).

## The persistent field

Four writers (`0x1e0b4d8`, `0x1e0b856`, `0x1e0bedc`, `0x1e0bf7c`) and seven readers inside
`0x1e0b400-0x1e0bf80`. Its meaning is **not proven** and it is therefore not named.
