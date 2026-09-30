#define MyAppName "ArmorX Studio"
#define MyAppVersion "0.6.0"
#define MyAppPublisher "ArmorX Toolkit Community"
#define MyAppExeName "ArmorX-Studio.exe"
#define BuildRoot "..\..\artifacts\win-x64"

[Setup]
AppId={{6F8EC802-1C51-4E8F-925B-0A9ED6A2D2A1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/feshinkof-boop/armorx-toolkit
AppSupportURL=https://github.com/feshinkof-boop/armorx-toolkit/issues
DefaultDirName={localappdata}\Programs\ArmorX Studio
DefaultGroupName=ArmorX Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\artifacts\installer
OutputBaseFilename=ArmorX-Studio-v0.6.0-Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0.19041
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupLogging=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\..\LICENSE

[Files]
Source: "{#BuildRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ArmorX Studio"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\ArmorX Studio"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch ArmorX Studio"; Flags: nowait postinstall skipifsilent
