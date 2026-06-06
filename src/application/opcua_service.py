import asyncio
import json
import threading

from asyncua import Server

from src.domain.aas_model import TELEMETRY_MODEL
from src.infra.config import AcquisitionConfig, MqttConfig, OpcuaConfig, VehicleConfig
from src.infra.logger import get_logger
from src.infra.mqtt_client import MqttClient

logger = get_logger(__name__)

TECHNICAL_DATA: dict[str, float] = {
    "TotalMass": VehicleConfig.TOTAL_MASS,
    "DragCoefficient": VehicleConfig.DRAG_COEFFICIENT,
    "FrontalArea": VehicleConfig.FRONTAL_AREA,
    "RollingResistance": VehicleConfig.ROLLING_RESISTANCE,
    "NominalDcVoltage": AcquisitionConfig.NOMINAL_DC_VOLTAGE,
    "BatteryCapacityJ": VehicleConfig.BATTERY_CAPACITY_J,
}


class OpcuaService:
    """OPC UA server exposing the digital twin (RAMI 4.0 communication layer).

    The address space mirrors the AAS V3 structure: the root object carries the
    shell idShort, and the IDTA submodels (TimeSeries, EnergyEfficiency,
    TechnicalData) hang directly off it as child objects, each holding its
    submodel-element variables. The dynamic submodels are built from the
    canonical model and updated from the MQTT bus; TechnicalData is static.
    Endpoint, namespace and shell name are configured via OpcuaConfig.
    """

    def __init__(self) -> None:
        self._latest: dict = {}
        self._lock = threading.Lock()

    def _on_processed(self, topic: str, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return
        with self._lock:
            self._latest = data

    async def run(self) -> None:
        bus = MqttClient(client_id="opcua")
        bus.connect()
        bus.subscribe(MqttConfig.TOPIC_PROCESSED, self._on_processed)
        bus.loop_start()

        server = Server()
        await server.init()
        server.set_endpoint(OpcuaConfig.endpoint())
        server.set_server_name(OpcuaConfig.SERVER_NAME)
        idx = await server.register_namespace(OpcuaConfig.NAMESPACE)
        shell = await server.nodes.objects.add_object(idx, OpcuaConfig.SHELL_NAME)

        nodes = []
        for submodel, variables in TELEMETRY_MODEL.items():
            group = await shell.add_object(idx, submodel)
            for id_short, field, scale in variables:
                node = await group.add_variable(idx, id_short, 0.0)
                nodes.append((node, field, scale))

        technical = await shell.add_object(idx, "TechnicalData")
        for id_short, value in TECHNICAL_DATA.items():
            await technical.add_variable(idx, id_short, float(value))

        async with server:
            logger.info(
                "opcua_server_started",
                endpoint=OpcuaConfig.endpoint(),
                shell=OpcuaConfig.SHELL_NAME,
                submodels=[*TELEMETRY_MODEL.keys(), "TechnicalData"],
            )
            while True:
                with self._lock:
                    data = dict(self._latest)
                for node, field, scale in nodes:
                    value = data.get(field)
                    if value is not None:
                        await node.write_value(float(value) * scale)
                await asyncio.sleep(OpcuaConfig.UPDATE_INTERVAL)
