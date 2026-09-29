$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location (Join-Path $Root 'frontend')
try {
    npm install
    npm run build
} finally {
    Pop-Location
}
dotnet run --project (Join-Path $Root 'ArmorX.Windows\ArmorX.Windows.csproj')
