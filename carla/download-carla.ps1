param(
  [string]$Version = '0.9.16',
  [string]$Dest = 'C:\CARLA'
)

$ErrorActionPreference = 'Stop'
$base = 'https://carla-releases.b-cdn.net/Windows'
$mainUrl = "$base/CARLA_$Version.zip"
$mapsUrl = "$base/AdditionalMaps_$Version.zip"
$mainZip = Join-Path $env:TEMP "CARLA_$Version.zip"
$mapsZip = Join-Path $env:TEMP "AdditionalMaps_$Version.zip"

if (Test-Path (Join-Path $Dest 'CarlaUE4.exe')) {
  Write-Host "CARLA already present in $Dest - nothing to do."
  exit 0
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

Write-Host "Downloading CARLA $Version main package ..."
curl.exe -L --fail --retry 3 -o $mainZip $mainUrl

Write-Host "Extracting main package to $Dest ..."
Expand-Archive -Path $mainZip -DestinationPath $Dest -Force

Write-Host "Downloading additional maps ..."
curl.exe -L --fail --retry 3 -o $mapsZip $mapsUrl
$importDir = Join-Path $Dest 'Import'
New-Item -ItemType Directory -Force -Path $importDir | Out-Null
Copy-Item $mapsZip -Destination $importDir -Force

$importBat = Join-Path $Dest 'ImportAssets.bat'
if (Test-Path $importBat) {
  Write-Host "Importing additional maps ..."
  & $importBat
}

Remove-Item $mainZip, $mapsZip -Force -ErrorAction SilentlyContinue
Write-Host "Done. Set CARLA_HOME=$Dest"
