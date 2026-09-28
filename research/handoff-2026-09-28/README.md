# ARMOR-X research handoff — 2026-09-28

This branch is the public research handoff for the live ARMOR-X Pro reverse-engineering work.

## Source state

- Local research branch: `research/physical-armorx-live-2026-09-27`
- Verified local HEAD: `87478461e662ede8f056cbcf8b35b44c10c8fbd5`
- Local commit count: **83**
- Tracked files in the full lab branch: **1130**
- Worktree at handoff: **clean**
- Local suite: **495 passed + 12 subtests**
- Fresh-clone suite: **489 passed + 6 skipped**
- Latest complete Git bundle: `armorx-physical-full-8747846.bundle`
  - size: **110,536,081 bytes**
  - SHA-256: `d04c77cf3fa9651482cd841497f3d5f9b50574b54402fd2f684f838636e7f0ee`

## What is mirrored here

The Google Drive handoff was inventoried before publication: **85 direct items** plus **11 overnight patch-series files**.

This GitHub research branch mirrors the **text handoff/patch series and metadata**. The large Git bundles, raw USB/Bluetooth captures, Android bugreports/APKs, emulator images and local runtime/session artifacts are deliberately not copied into the public repository.

That keeps the public branch useful and reproducible without publishing bulky/raw host or device artifacts.

See `MANIFEST.json` for the complete Drive inventory used for this handoff.

## Latest proven research state

The current local line of research includes:

- direct ARMOR-X USB power-state identity switching:
  - USB-powered/off vendor personality: `413d:2106`, FF7A vendor HID
  - powered-on operating personality: `045e:0b12`, Xbox GIP / xpad
- F20 and ARMOR-X vendor-mode descriptor identity correspondence
- live GIP field mapping for A, M1, M2, LT, RT and stick fields
- startup 32-byte vs steady-state 48-byte GIP input forms
- RT digital bit 9 (`0x00000200`) synthesized internally from the analogue RT byte
- `r4` proven as the current candidate mask
- `r5` proven as persistent `[r15+0x1d0]`
- `r5 & r4` corrected from “changed-bit set” to an **intersection gate**
- first creator of RT mask bit 9 localized through `0x1e0a426`
- current next target: reverse `0x1e0a426` and close the trigger threshold/scaling + D2 emission rule

## Safety / publication notes

This branch does **not** modify `main`, release tags, or public release assets.

The public patch archive is a research handoff. It should not be confused with the end-user Windows release.

Raw captures remain outside GitHub; their findings are represented by the committed research patches and reports.
