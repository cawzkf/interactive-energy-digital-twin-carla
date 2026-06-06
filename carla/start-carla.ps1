param(
  [string]$CarlaHome = $env:CARLA_HOME,
  [int]$Port = 2000,
  [ValidateSet('Low', 'Epic')][string]$Quality = 'Low',
  [switch]$OffScreen
)

if (-not $CarlaHome) { $CarlaHome = 'C:\CARLA' }
$exe = Join-Path $CarlaHome 'CarlaUE4.exe'

if (-not (Test-Path $exe)) {
  Write-Error "CarlaUE4.exe not found in '$CarlaHome'. Set CARLA_HOME or run carla\download-carla.ps1."
  exit 1
}

$carlaArgs = @("-carla-rpc-port=$Port", "-quality-level=$Quality")
if ($OffScreen) { $carlaArgs += '-RenderOffScreen' }

Write-Host "Starting CARLA: $exe $($carlaArgs -join ' ')"
$proc = Start-Process -FilePath $exe -ArgumentList $carlaArgs -PassThru
Write-Host "CARLA started (PID $($proc.Id)) on port $Port. Stop it with: Stop-Process -Id $($proc.Id)"
