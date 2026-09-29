$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
dotnet run --project (Join-Path $Root 'ArmorX.Windows\ArmorX.Windows.csproj')
