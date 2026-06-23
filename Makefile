APP_ENV ?= dev
VENV    := .venv
PY      := $(VENV)/bin/python
PIP     := $(VENV)/bin/pip
DC      := APP_ENV=$(APP_ENV) bash scripts/deploy_docker.sh

.DEFAULT_GOAL := help
.PHONY: help venv install test smoke verify report \
        images deploy run down logs \
        dev-up dev dev-back dev-front dev-stop clean \
        twin-up twin-down dev-twin \
        run-carla carla carla-down carla-download

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-13s\033[0m %s\n", $$1, $$2}'

venv: ## Create the Python virtualenv
	@test -d $(VENV) || python3 -m venv $(VENV)

install: venv ## Install backend (pip) + frontend (npm) deps for local dev
	$(PIP) install -q --upgrade pip
	$(PIP) install -q -r requirements.txt
	cd frontend && npm install

test: ## Run the unit test suite on the host
	$(PY) -m pytest

smoke: ## Run the offline end-to-end pipeline smoke test
	$(PY) scripts/smoke_pipeline.py

verify: ## Smoke-test the LIVE deployed stack (API + OPC UA + BaSyx twin-sync)
	docker run --rm --network host -e APP_ENV=$(APP_ENV) --env-file config/.env.$(APP_ENV) \
		-v $(CURDIR)/scripts/verify_stack.py:/app/verify_stack.py:ro \
		marchforce-backend:local python /app/verify_stack.py

report: ## Compile the technical report to PDF (Docker TeX Live; no host install)
	bash scripts/build_report.sh

images: ## Build lean front+back images (pytest runs in the build; red => no image)
	$(DC) build

deploy: ## Bring the self-contained stack up (mosquitto + timescaledb + back + front)
	$(DC) up

run: images deploy ## Build (tests gate) then deploy the whole stack via images
	@echo "Up. Dashboard: http://localhost:8080  ·  API: http://localhost:8000"

logs: ## Follow the deployed stack logs
	$(DC) logs

down: ## Stop the deployed Docker stack (+ telemetry infra)
	$(DC) down
	docker compose -f telemetry-setup/docker-compose.yml down

dev-up: ## Dev infra: TimescaleDB + full BaSyx twin (AAS + Mongo + MQTT)
	docker compose -f telemetry-setup/docker-compose.yml up -d
	docker compose -f basyx-setup/docker-compose.yml up -d

dev: dev-up dev-back dev-twin dev-front ## Dev run with hot reload (API --reload + Vite HMR)

dev-back: ## Start backend (hot reload when APP_ENV=dev)
	APP_ENV=$(APP_ENV) bash scripts/deploy.sh back

dev-front: ## Start frontend (Vite HMR when APP_ENV=dev)
	APP_ENV=$(APP_ENV) bash scripts/deploy.sh front

dev-stop: ## Stop dev services started by deploy.sh
	bash scripts/deploy.sh stop

twin-up: ## Start the BaSyx digital twin (AAS + Mongo + MQTT/OPC UA)
	docker compose -f basyx-setup/docker-compose.yml up -d

twin-down: ## Stop the BaSyx digital twin
	docker compose -f basyx-setup/docker-compose.yml down

dev-twin: ## Run the twin-sync consumer as a process (dev)
	APP_ENV=$(APP_ENV) bash scripts/deploy.sh twin

run-carla: ## ONE command: start CARLA + bring up the whole stack in CARLA mode
	APP_ENV=$(APP_ENV) bash scripts/run_carla.sh

carla-stop: ## Kill CarlaUE4 (and any Carla* child process) on the Windows host
	powershell.exe -Command "Get-Process 'Carla*' -ErrorAction SilentlyContinue | Stop-Process -Force" || true

carla-down: down carla-stop ## Stop CARLA mode: containers + acquisition + CARLA on Windows

carla: ## Launch CARLA on the Windows host (see carla/README.md)
	powershell.exe -ExecutionPolicy Bypass -File carla/start-carla.ps1 -Quality Low

carla-download: ## Download CARLA to the Windows host (~10-20GB)
	powershell.exe -ExecutionPolicy Bypass -File carla/download-carla.ps1

clean: dev-stop ## Stop dev services and remove build/run artifacts
	rm -rf .run frontend/dist
