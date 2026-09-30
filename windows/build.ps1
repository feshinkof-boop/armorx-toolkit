$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Frontend = Join-Path $Root 'frontend'
$Project = Join-Path $Root 'ArmorX.Windows\ArmorX.Windows.csproj'
$Out = Join-Path $Root 'publish\win-x64'

Write-Host 'ArmorX Studio v0.6.0 build'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Node.js 20+ is required to build the React UI.' }
if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) { throw '.NET 8 SDK is required.' }

Push-Location $Frontend
try {
    npm install
    npm test -- --run
    npm run build
} finally {
    Pop-Location
}

dotnet restore $Project
dotnet build $Project -c Release --no-restore

Remove-Item $Out -Recurse -Force -ErrorAction SilentlyContinue
dotnet publish $Project -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -p:DebugType=None -p:DebugSymbols=false -o $Out

$Exe = Join-Path $Out 'ArmorX-Studio.exe'
if (-not (Test-Path $Exe)) { throw "Expected executable was not produced: $Exe" }
$p = Start-Process $Exe -ArgumentList '--self-test' -PassThru -Wait
if ($p.ExitCode -ne 0) { throw "Self-test failed: $($p.ExitCode)" }

Write-Host "Build complete: $Exe" -ForegroundColor Green
