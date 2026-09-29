# ArmorX Windows v0.2.0

Public Windows configurator for the BIGBIG WON ARMOR-X Pro.

This is the end-user application. It intentionally does **not** include the internal research/capture UI, Autopilot, raw BLE recording, guided experiments, evidence exports, or experimental unknown-ID tools.

## Public features

- One-button **Connect / Recover** with persistent BLE discovery and Windows BLE-cache fallback.
- Automatic recovery when ARMOR-X Pro wakes after its power-save timeout.
- Model, firmware, and battery display.
- Automatic 144-byte D6 configuration read after connecting.
- Stick limit, deadzone, and curve editing.
- Trigger editing.
- Gyro/sensor editing.
- Turbo editing.
- M1-M4 remapping using supported public mappings, including live-proven Guide/Xbox ID 12.
- Full-image D7 write, persistent save, and exact 144-byte read-back verification.
- Local profile save/load under `%LOCALAPPDATA%\ArmorX\Profiles`.
- Unknown/reserved bytes are preserved from the controller's own configuration image.

## Requirements

- Windows 10 2004+ or Windows 11
- Bluetooth LE adapter
- ARMOR-X Pro powered on and available to Windows Bluetooth

The published self-contained build does not require a separate .NET installation.

## Source build

```powershell
dotnet restore .\windows\ArmorX.Windows\ArmorX.Windows.csproj
dotnet publish .\windows\ArmorX.Windows\ArmorX.Windows.csproj -c Release -r win-x64 --self-contained true
```

## Usage

1. Power on ARMOR-X Pro and close the official mobile app if it is connected to the device.
2. Click **Connect / Recover**.
3. The app reads the controller's current configuration automatically.
4. Edit the desired settings.
5. Click **Apply & Verify**.
6. The app saves the configuration and verifies the complete 144-byte read-back.

For configuration fields whose official UI transformations are not yet proven, the app exposes the exact raw controller value rather than inventing a percentage or label.

## Scope

This public GUI focuses on stable configuration functionality. Research-only capture and experimentation features remain separate from this release.
