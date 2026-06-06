#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_ENV="${APP_ENV:-dev}"
CARLA_HOST="${CARLA_HOST:-10.255.255.254}"
CARLA_PORT="${CARLA_PORT:-2000}"

mkdir -p .run
log() { printf '\033[1;35m[carla]\033[0m %s\n' "$*"; }

ACQ_RUNNER=(.venv/bin/python)
ensure_carla_env() {
  if ! command -v poetry >/dev/null 2>&1; then
    log "poetry not found — using .venv (the carla wheel may be missing)"
    return
  fi
  if ! poetry run python -c "import carla" >/dev/null 2>&1; then
    log "provisioning CARLA env with Poetry (carla group)"
    command -v python3.10 >/dev/null 2>&1 && poetry env use python3.10 >/dev/null 2>&1 || true
    poetry install --with carla -q
  fi
  ACQ_RUNNER=(poetry run python)
}

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

log "bringing up the stack in CARLA mode (no in-container acquisition)"
APP_ENV="$APP_ENV" ACQ_SOURCE=carla bash scripts/deploy_docker.sh up

ensure_carla_env
log "starting host acquisition (CARLA -> MQTT) via: ${ACQ_RUNNER[*]}"
APP_ENV="$APP_ENV" ACQ_SOURCE=carla MQTT_HOST=localhost \
  nohup "${ACQ_RUNNER[@]}" -m src.acquisition_main >.run/acquisition.log 2>&1 &
echo $! >.run/acquisition.pid
log "acquisition started (pid $(cat .run/acquisition.pid)). Dashboard: http://localhost:8080"
