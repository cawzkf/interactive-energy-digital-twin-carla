param(
  [string]$ProjectRoot = "\\wsl.localhost\Ubuntu\home\cawzk\interactive-energy-digital-twin-carla"
)
$ErrorActionPreference = 'Stop'

$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

$wheel = "C:\CARLA\PythonAPI\carla\dist\carla-0.9.16-cp312-cp312-win_amd64.whl"
Write-Host "Installing carla client + deps..."
& $py -m pip install --quiet --user $wheel pydantic paho-mqtt python-dotenv structlog

$env:ACQ_SOURCE = 'carla'
$env:CARLA_HOST = 'localhost'
$env:MQTT_HOST = 'localhost'
$env:APP_ENV = 'dev'
$env:PYTHONPATH = $ProjectRoot

Write-Host "Starting acquisition (CARLA localhost:2000 -> MQTT localhost:1883)..."
Push-Location $ProjectRoot
try { & $py -m src.acquisition_main } finally { Pop-Location }