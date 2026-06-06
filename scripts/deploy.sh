#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_ENV="${APP_ENV:-dev}"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
RUN_DIR="$ROOT/.run"
ENV_FILE="$ROOT/config/.env.$APP_ENV"
TARGET="${1:-all}"

mkdir -p "$RUN_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
fi
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
FRONT_PORT="${FRONT_PORT:-4173}"

log() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }

start_service() {
  local name="$1"; shift
  local pidfile="$RUN_DIR/$name.pid"
  if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    log "$name already running (pid $(cat "$pidfile"))"
    return
  fi
  log "starting $name"
  APP_ENV="$APP_ENV" nohup "$@" >"$RUN_DIR/$name.log" 2>&1 &
  echo $! >"$pidfile"
}

stop_all() {
  log "stopping services"
  for pidfile in "$RUN_DIR"/*.pid; do
    [[ -e "$pidfile" ]] || continue
    local pid; pid="$(cat "$pidfile")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" && log "stopped $(basename "$pidfile" .pid) (pid $pid)"
    fi
    rm -f "$pidfile"
  done
}

deploy_back() {
  [[ -x "$PY" ]] || { echo "venv missing — run 'make install' first"; exit 1; }
  log "deploying backend (APP_ENV=$APP_ENV, source=${ACQ_SOURCE:-carla})"
  start_service processing  "$PY" -m src.processing_main
  if [[ "$APP_ENV" == "dev" ]]; then
    log "dev mode: API with hot reload"
    start_service api "$PY" -m uvicorn src.api.server:app \
      --host "$API_HOST" --port "$API_PORT" --reload --reload-dir src
  else
    start_service api "$PY" -m uvicorn src.api.server:app \
      --host "$API_HOST" --port "$API_PORT"
  fi
  start_service acquisition "$PY" -m src.acquisition_main
  log "backend up — API on http://localhost:$API_PORT (logs in .run/)"
}

deploy_front() {
  command -v npm >/dev/null || { echo "npm not found — install Node.js"; exit 1; }
  if [[ "$APP_ENV" == "dev" ]]; then
    log "dev mode: Vite dev server with HMR"
    ( cd frontend && npm install --silent )
    start_service frontend bash -c "cd '$ROOT/frontend' && npm run dev -- --host --port $FRONT_PORT"
  else
    log "building frontend (static)"
    ( cd frontend && npm install --silent && npm run build )
    start_service frontend bash -c "cd '$ROOT/frontend' && npm run preview -- --host --port $FRONT_PORT"
  fi
  log "frontend up — http://localhost:$FRONT_PORT"
}

deploy_twin() {
  [[ -x "$PY" ]] || { echo "venv missing — run 'make install' first"; exit 1; }
  log "deploying twin-sync (BASYX_URL=${BASYX_URL:-http://localhost:8081})"
  start_service twin-sync "$PY" -m src.twin_main
}

case "$TARGET" in
  all)   deploy_back; deploy_front ;;
  back)  deploy_back ;;
  front) deploy_front ;;
  twin)  deploy_twin ;;
  stop)  stop_all ;;
  *) echo "unknown target: $TARGET (use: all | back | front | twin | stop)"; exit 1 ;;
esac
