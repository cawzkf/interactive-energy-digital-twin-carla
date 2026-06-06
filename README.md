# Interactive Energy Digital Twin (CARLA)

Energy digital twin for the MarchForce prototype: a simplified longitudinal model
estimates instantaneous power and accumulated energy from vehicle telemetry
(CARLA today, real B.O.M. later), streamed over an MQTT bus, persisted in
TimescaleDB, mirrored to an Asset Administration Shell (Eclipse BaSyx) and exposed
over OPC UA, with a real-time React dashboard. Layered per RAMI 4.0.

## Prerequisites

- **Docker** + **Docker Compose** (the whole stack runs in containers)
- **GNU make**
- Linux or WSL2 (developed on WSL2). CARLA acquisition is optional and runs on a
  Windows host — see [carla/README.md](carla/README.md). Without CARLA the stack
  uses the built-in simulator as the data source.

No Python/Node install is needed to *run* the stack — only to develop with hot
reload (`make install`).

## Quickstart (one command)

```bash
make run        # build lean images (unit tests gate the build) + bring the stack up
make verify     # smoke-test the live stack (API + OPC UA + BaSyx twin-sync)
make down       # stop everything
```

`make run` brings up: MQTT broker (reused from BaSyx), TimescaleDB, processing,
API + WebSocket, OPC UA server, the digital twin (BaSyx) and the dashboard.

| Service | URL |
|---|---|
| Dashboard (web) | http://localhost:8080 |
| API + WebSocket | http://localhost:8000 |
| OPC UA server | `opc.tcp://<host>:4840/marchforce/` |
| BaSyx AAS (REST) | http://localhost:8081 |
| BaSyx Web UI | http://localhost:3000 |

The dashboard shows the real host IP for the OPC UA/MQTT/BaSyx endpoints (not
`localhost`), so external clients (e.g. UAExpert) can connect.

To drop the digital-twin layer (box/standalone, own broker): `WITH_TWIN=0 make run`.

## Configuration

Everything is configured by environment, selected with `APP_ENV` (`dev` |
`staging` | `prod`) — nothing is hardcoded. Files live in `config/.env.<env>`;
copy [config/.env.example](config/.env.example) to create new ones. Secrets
(`.env.staging`, `.env.prod`, `.env.local`) are gitignored.

```bash
APP_ENV=prod make run      # selects config/.env.prod
```

## Development (hot reload)

```bash
make install               # backend (venv) + frontend (npm) deps
make dev                   # API --reload + Vite HMR, infra reused from BaSyx
```

- Dashboard (Vite HMR): http://localhost:4173 · API: http://localhost:8000

## CARLA (optional)

```bash
make carla-download        # download CARLA to the Windows host (~10-20 GB, once)
make run-carla             # start CARLA + bring up the whole stack in CARLA mode
```

Drive with **WASD** (S reverses), chase camera follows the car. Delete the
`carla/` folder to remove CARLA support entirely.

## Tests & report

```bash
make test                  # unit suite (pytest, AAA pattern)
make smoke                 # offline end-to-end pipeline (fakes, no infra)
make verify                # live stack smoke test (needs `make run` first)
make report                # compile the technical report to PDF (Docker TeX Live)
```

## Documentation

- [docs/architecture.md](docs/architecture.md) — components and RAMI 4.0 layering
- [docs/energy_model.md](docs/energy_model.md) — the longitudinal energy model
- [docs/telemetry.md](docs/telemetry.md) — the telemetry pipeline end to end
- `make help` — all available targets
