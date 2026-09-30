# ArmorX Studio v0.6.0 — Windows

ArmorX Studio is now the recommended Windows application for ARMOR-X Pro, replacing the legacy v0.2.1 interface.

## Highlights

- Responsive **React + TypeScript** interface inside a .NET 8 / WebView2 host.
- Dark and light themes.
- Dedicated **Button Test** with live L3/R3, stick position, A/B/X/Y, D-pad, LB/RB and animated analog LT/RT pressure.
- Visual stick/deadzone/curve-byte and trigger editors.
- Gyro, turbo and M1–M4 mapping.
- Local profiles and diagnostics.
- Contextual **?** help with recommended guidance and the loaded baseline/default.
- About dialog.
- System tray with connection, battery and active profile.
- **Macro Studio** with draggable 1–16 step cards, chords, hold/gap timing, tap/long-press/cycle modes, validation and JSON import/export.

## Guarded configuration writes

ArmorX Studio does not expose a raw command console. Its normal Apply & Verify workflow requires two agreeing live reads, known-editable-only merge, exact diff and SHA-256 review, explicit confirmation, a pre-commit re-read, a complete pre-write backup, one D7 transaction plus one persistence action, and **two exact 144-byte read-backs**.

Macro Studio is **offline only** in v0.6.0. Device macro installation remains a separate research gate.

## Downloads

- **ArmorX-Studio-v0.6.0-Setup.exe** — recommended per-user Windows installer.
- **ArmorX-Studio-v0.6.0-win-x64.zip** — portable self-contained application folder.
- **ArmorX-Studio-v0.6.0-source.zip** — Windows application source.
- **ArmorX-Studio-v0.6.0-SHA256SUMS.txt** — SHA-256 checksums.

The app is self-contained for .NET 8. Microsoft Edge **WebView2 Runtime** is required and is normally already installed on supported Windows 10/11 systems.

## Compatibility

The directly validated ARMOR-X Pro baseline remains model **ZJ-XT**, firmware **2741**. Other firmware versions have not been independently hardware-validated.

This is an unofficial community project and is not affiliated with BIGBIG WON, MOJHON, Microsoft, or Xbox.
