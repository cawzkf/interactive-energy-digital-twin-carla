import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from src.domain.diagnostics import DiagnosticThresholds
from src.infra.config import AcquisitionConfig, MqttConfig, VehicleConfig
from src.infra.logger import get_logger, setup_logging
from src.infra.mqtt_client import MqttClient
from src.infra.timescale_repository import TimescaleRepository

setup_logging()
logger = get_logger(__name__)


class LiveHub:
    """Fan-out of processed telemetry to all connected WebSocket clients."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        self._loop: asyncio.AbstractEventLoop | None = None
        self.latest: dict | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def ingest_from_mqtt(self, _topic: str, payload: str) -> None:
        if self._loop is None:
            return
        self._loop.call_soon_threadsafe(self._enqueue, payload)

    def _enqueue(self, payload: str) -> None:
        try:
            self.latest = json.loads(payload)
        except json.JSONDecodeError:
            return
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(payload)

    async def register(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        if self.latest is not None:
            await ws.send_text(json.dumps(self.latest))

    def unregister(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast_loop(self) -> None:
        while True:
            payload = await self._queue.get()
            dead: list[WebSocket] = []
            for ws in self._clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._clients.discard(ws)


hub = LiveHub()
repo: TimescaleRepository | None = None
mqtt_client: MqttClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global repo, mqtt_client
    hub.bind_loop(asyncio.get_running_loop())

    repo = TimescaleRepository()
    repo.init_schema()

    mqtt_client = MqttClient(client_id="api")
    mqtt_client.connect()
    mqtt_client.subscribe(MqttConfig.TOPIC_PROCESSED, hub.ingest_from_mqtt)
    mqtt_client.loop_start()

    broadcaster = asyncio.create_task(hub.broadcast_loop())
    logger.info("api_ready")
    try:
        yield
    finally:
        broadcaster.cancel()
        if mqtt_client is not None:
            mqtt_client.disconnect()
        if repo is not None:
            repo.close()


app = FastAPI(title="MarchForce Telemetry API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/latest")
def latest() -> dict:
    return hub.latest or {}


@app.get("/api/endpoints")
def endpoints() -> dict:
    return {
        "host": os.getenv("PUBLIC_HOST", ""),
        "opcua_port": int(os.getenv("OPCUA_PORT", "4840")),
        "mqtt_port": MqttConfig.PORT,
        "basyx_port": int(os.getenv("BASYX_PORT", "8081")),
    }


def _default_config() -> dict:
    th = DiagnosticThresholds()
    return {
        "vehicle": {
            "mass_vehicle": VehicleConfig.MASS_VEHICLE,
            "mass_driver": VehicleConfig.MASS_DRIVER,
            "total_mass": VehicleConfig.TOTAL_MASS,
            "drag_coefficient": VehicleConfig.DRAG_COEFFICIENT,
            "frontal_area": VehicleConfig.FRONTAL_AREA,
            "rolling_resistance": VehicleConfig.ROLLING_RESISTANCE,
            "battery_capacity_j": VehicleConfig.BATTERY_CAPACITY_J,
            "nominal_dc_voltage": AcquisitionConfig.NOMINAL_DC_VOLTAGE,
        },
        "alerts": {
            "soc_warning": th.soc_warning,
            "soc_critical": th.soc_critical,
            "idc_warning": th.idc_warning,
            "idc_critical": th.idc_critical,
            "speed_warning": th.speed_warning,
            "speed_critical": th.speed_critical,
        },
    }


current_config = _default_config()


@app.get("/api/config")
def get_config() -> dict:
    return current_config


@app.post("/api/config")
def set_config(update: dict) -> dict:
    for section in ("vehicle", "alerts"):
        if section in update:
            current_config[section].update(update[section])
    current_config["vehicle"]["total_mass"] = (
        current_config["vehicle"]["mass_vehicle"]
        + current_config["vehicle"]["mass_driver"]
    )
    if mqtt_client is not None:
        mqtt_client.publish(MqttConfig.TOPIC_CONFIG, json.dumps(current_config))
    logger.info("config_published")
    return current_config


@app.get("/api/sessions")
def list_sessions() -> list[dict]:
    assert repo is not None
    return repo.list_sessions()


@app.get("/api/sessions/{session_id}/telemetry")
def session_history(session_id: str, limit: int = 5000) -> list[dict]:
    assert repo is not None
    return repo.get_history(session_id, limit=limit)


@app.websocket("/ws/live")
async def ws_live(ws: WebSocket) -> None:
    await hub.register(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.unregister(ws)
    except Exception:
        hub.unregister(ws)
