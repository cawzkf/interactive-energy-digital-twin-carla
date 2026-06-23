#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_ENV="${APP_ENV:-dev}"
CARLA_HOST="${CARLA_HOST:-172.28.0.1}"
CARLA_PORT="${CARLA_PORT:-2000}"

mkdir -p .run
log() { printf '\033[1;35m[carla]\033[0m %s\n' "$*"; }

log "launching CARLA on the Windows host"
powershell.exe -ExecutionPolicy Bypass -File "$(wslpath -w carla/start-carla.ps1)" -Quality Low || true

log "waiting for CARLA at $CARLA_HOST:$CARLA_PORT"
ready=0
for _ in $(seq 1 120); do
  if timeout 1 bash -c "cat < /dev/null > /dev/tcp/$CARLA_HOST/$CARLA_PORT" 2>/dev/null; then
    ready=1; break
  fi
  sleep 2
done
[[ "$ready" == "1" ]] && log "CARLA is up" || log "timeout waiting for CARLA — continuing anyway"

log "bringing up the stack in CARLA mode (processing + twin-sync in Docker)"
APP_ENV="$APP_ENV" ACQ_SOURCE=carla bash scripts/deploy_docker.sh up

# The carla Python client only runs on Windows (win_amd64 wheel).
# Launch run-acquisition.ps1 via PowerShell so it connects to CARLA locally
# and publishes to MQTT (localhost:1883 on Windows → basyx-setup mosquitto via WSL2 port-forward).
log "starting Windows acquisition (CARLA -> MQTT via PowerShell)"
ACQ_PS="$(wslpath -w carla/run-acquisition.ps1)"
powershell.exe -ExecutionPolicy Bypass \
  -File "$ACQ_PS" -ProjectRoot "$(wslpath -w "$ROOT")" &
echo $! >.run/acq-win.pid
log "acquisition launched on Windows (pid $(cat .run/acq-win.pid)). Dashboard: http://localhost:8080"
log "  AAS REST : http://localhost:8081"
log "  AAS MQTT : marchforce/aas/{TimeSeries,EnergyEfficiency}/..."
