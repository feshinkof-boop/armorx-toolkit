# ArmorX Studio for Windows — v0.6 development

This branch replaces the old WPF-only v0.2.1 interface with a responsive
**React + TypeScript** UI hosted inside a .NET 8 / WebView2 Windows application.

The proven Windows BLE/config backend from v0.2.1 is retained and hardened; the
frontend does not send raw BLE frames.

## Architecture

- **Frontend:** React + TypeScript + Vite
- **Host:** .NET 8 WPF + Microsoft WebView2
- **Bluetooth:** Windows BLE APIs through the existing C# transport
- **Live button test:** Windows.Gaming.Input Gamepad API (read-only)
- **Tray:** Windows NotifyIcon
- **Profiles/backups:** %LOCALAPPDATA%\ArmorX
- **Macros:** offline V41 JSON builder/validator in the React UI

## Current UI

- responsive sidebar/mobile-width navigation;
- dark/light theme toggle;
- dashboard with battery, firmware, active profile and pending changes;
- visual stick/deadzone and raw curve-byte editors;
- visual LT/RT editor;
- gyro/turbo/rear-button mapping;
- profile library;
- **Macro Studio** with draggable timeline cards, chord palette, hold/gap timing,
  1–16 steps, import/export, and no device macro write;
- **Button Test** page with live A/B/X/Y, D-pad, LB/RB, animated L3/R3 stick
  clicks, stick position, and analog LT/RT pressure;
- ? hover/focus help on tunable fields with evidence wording and the loaded
  device baseline/default;
- About dialog;
- end-user diagnostics;
- Windows system tray showing connection, battery and active profile.

## Write safety

The normal GUI uses a review token:

1. read configuration twice and require exact equality + valid CRC;
2. merge only public editable offsets into the fresh device image;
3. show exact byte diff and target/current hashes;
4. require explicit React confirmation;
5. re-read the device before the write and refuse if the reviewed state changed;
6. save a complete pre-write backup;
7. send one D7 transaction and one persistence command;
8. require **two** exact 144-byte read-backs.

No arbitrary opcode/payload console exists.

## Build

Requirements: Node.js 20+ and .NET 8 SDK.

    .\windows\build.ps1

Development:

    .\windows\run-dev.ps1

## Scope boundary

The macro editor is offline in this development line. It builds the recovered
portable V41 macro JSON shape but does not claim that device macro installation
has been proven.
