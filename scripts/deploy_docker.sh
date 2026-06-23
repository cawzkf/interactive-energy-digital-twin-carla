#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

APP_ENV="${APP_ENV:-dev}"
ENV_FILE="config/.env.$APP_ENV"
COMPOSE="docker compose -f deploy/docker-compose.yml"
BASYX_COMPOSE="docker compose -f basyx-setup/docker-compose.yml"

WITH_TWIN="${WITH_TWIN:-1}"
PROFILES=""
if [[ "$WITH_TWIN" == "1" ]]; then
  PROFILES="$PROFILES --profile twin"
else
  PROFILES="$PROFILES --profile own-broker"
fi
if [[ "${ACQ_SOURCE:-sim}" != "carla" ]]; then PROFILES="$PROFILES --profile sim-acq"; fi

_ACQ_OVERRIDE="${ACQ_SOURCE:-}"
if [[ -f "$ENV_FILE" ]]; then
  set -a; source "$ENV_FILE"; set +a
fi
[[ -n "$_ACQ_OVERRIDE" ]] && export ACQ_SOURCE="$_ACQ_OVERRIDE"
export APP_ENV

if [[ "$WITH_TWIN" == "1" ]]; then
  export MQTT_HOST="host.docker.internal"
else
  export MQTT_HOST="mosquitto"
fi

export PUBLIC_HOST="${PUBLIC_HOST:-$(hostname -I 2>/dev/null | awk '{print $1}')}"

FRONTEND_REPO="${FRONTEND_REPO:-}"
FRONTEND_BRANCH="${FRONTEND_BRANCH:-main}"
FRONTEND_DIR="${FRONTEND_DIR:-.frontend-src}"

log() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }

ensure_frontend() {
  if [[ -z "$FRONTEND_REPO" ]]; then
    export FRONTEND_CONTEXT="$ROOT/frontend"
    return
  fi
  if [[ ! -d "$FRONTEND_DIR/.git" ]]; then
    log "cloning frontend repo $FRONTEND_REPO ($FRONTEND_BRANCH)"
    git clone --depth 1 -b "$FRONTEND_BRANCH" "$FRONTEND_REPO" "$FRONTEND_DIR"
  elif [[ "${1:-}" == "refresh" ]]; then
    log "updating frontend repo ($FRONTEND_BRANCH)"
    git -C "$FRONTEND_DIR" fetch --depth 1 origin "$FRONTEND_BRANCH"
    git -C "$FRONTEND_DIR" reset --hard "origin/$FRONTEND_BRANCH"
  fi
  export FRONTEND_CONTEXT="$ROOT/$FRONTEND_DIR"
}

cmd="${1:-up}"
case "$cmd" in
  build)
    ensure_frontend refresh
    log "test gate: building backend test stage (pytest must pass)"
    docker build -f docker/backend.Dockerfile --target test -t marchforce-backend:test .
    log "tests passed — building lean runtime images (frontend from $FRONTEND_CONTEXT)"
    APP_ENV="$APP_ENV" FRONTEND_CONTEXT="$FRONTEND_CONTEXT" $COMPOSE $PROFILES build
    ;;
  up)
    ensure_frontend
    if [[ "$WITH_TWIN" == "1" ]]; then
      log "bringing up the digital twin (BaSyx: AAS + Mongo + MQTT/OPC UA)"
      $BASYX_COMPOSE up -d
    fi
    log "starting stack (APP_ENV=$APP_ENV, source=${ACQ_SOURCE:-sim}, twin=$WITH_TWIN)"
    APP_ENV="$APP_ENV" FRONTEND_CONTEXT="$FRONTEND_CONTEXT" $COMPOSE $PROFILES up -d
    log "dashboard: http://localhost:8080  ·  API: http://localhost:8000"
    log "OPC UA (communication layer): opc.tcp://${PUBLIC_HOST:-localhost}:4840"
    if [[ "$WITH_TWIN" == "1" ]]; then
      log "BaSyx AAS (digital twin): http://localhost:8081  ·  AAS UI: http://localhost:3000"
    fi
    ;;
  down)
    for pidfile in .run/acquisition.pid .run/acq-win.pid; do
      if [[ -f "$pidfile" ]]; then
        kill "$(cat "$pidfile")" 2>/dev/null || true
        rm -f "$pidfile"
      fi
    done
    APP_ENV="$APP_ENV" $COMPOSE $PROFILES down
    if [[ "$WITH_TWIN" == "1" ]]; then $BASYX_COMPOSE down; fi
    ;;
  logs)
    APP_ENV="$APP_ENV" $COMPOSE logs -f --tail=100
    ;;
  *)
    echo "unknown command: $cmd (use: build | up | down | logs)"; exit 1 ;;
esac
