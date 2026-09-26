$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Project = Join-Path $Root 'ArmorX.Windows\ArmorX.Windows.csproj'
$Out = Join-Path $Root 'publish\win-x64'

Write-Host 'ArmorX Windows v0.2.0 public build'
Write-Host 'Checking .NET 8 SDK...'

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    Write-Host 'ERROR: .NET 8 SDK is not installed.' -ForegroundColor Red
    Write-Host 'Install: winget install --id Microsoft.DotNet.SDK.8 -e --source winget' -ForegroundColor Cyan
    exit 2
}

& dotnet restore $Project
if ($LASTEXITCODE -ne 0) { throw "dotnet restore failed with exit code $LASTEXITCODE" }

Remove-Item $Out -Recurse -Force -ErrorAction SilentlyContinue
& dotnet publish $Project `
    -c Release `
    -r win-x64 `
    --self-contained true `
    -p:PublishSingleFile=true `
    -p:IncludeNativeLibrariesForSelfExtract=true `
    -p:DebugType=None `
    -p:DebugSymbols=false `
    -o $Out
if ($LASTEXITCODE -ne 0) { throw "dotnet publish failed with exit code $LASTEXITCODE" }

$Exe = Join-Path $Out 'ArmorX-Windows.exe'
if (-not (Test-Path $Exe)) { throw "Expected executable was not produced: $Exe" }
Write-Host "Build complete: $Exe" -ForegroundColor Green
