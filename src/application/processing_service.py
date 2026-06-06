import json

from src.application.ports import MessageBus, TelemetryRepository
from src.domain.battery import Battery
from src.domain.diagnostics import Alert, AlertCode, DiagnosticThresholds, Severity, evaluate
from src.domain.dtos import (
    ProcessedTelemetryDto,
    RawTelemetryDto,
    UpdateRequestDto,
)
from src.domain.energy_model import EnergyModel
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.infra.config import AcquisitionConfig, MqttConfig, VehicleConfig
from src.infra.logger import get_logger

logger = get_logger(__name__)


def derive_dc_bus(power: float, electrical_step: float, dt: float, soc: float,
                  nominal_voltage: float) -> tuple[float, float]:
    """Derive Vdc/Idc from electrical power until real bus measurement exists."""
    vdc = nominal_voltage * (0.95 + 0.10 * max(0.0, min(soc, 1.0)))
    p_elec = (electrical_step / dt) if dt > 0 else 0.0
    if power < 0:
        p_elec = -p_elec
    idc = p_elec / vdc if vdc > 0 else 0.0
    return vdc, idc


class ProcessingService:
    def __init__(self, mqtt_client: MessageBus, repository: TelemetryRepository) -> None:
        self._mqtt = mqtt_client
        self._repo = repository
        self._systems: dict[str, VehicleEnergySystem] = {}
        self._mass = VehicleConfig.TOTAL_MASS
        self._drag = VehicleConfig.DRAG_COEFFICIENT
        self._frontal_area = VehicleConfig.FRONTAL_AREA
        self._rolling = VehicleConfig.ROLLING_RESISTANCE
        self._battery_capacity = VehicleConfig.BATTERY_CAPACITY_J
        self._nominal_voltage = AcquisitionConfig.NOMINAL_DC_VOLTAGE
        self._thresholds = DiagnosticThresholds()

    def _build_energy_system(self) -> VehicleEnergySystem:
        energy_model = EnergyModel(
            mass=self._mass,
            drag_coefficient=self._drag,
            frontal_area=self._frontal_area,
            rolling_resistance_coefficient=self._rolling,
        )
        battery = Battery(
            capacity=self._battery_capacity,
            soc_init=1.0,
            efficiency_discharge=0.9,
            efficiency_regen=0.9,
        )
        return VehicleEnergySystem(energy_model, battery)

    def _system_for(self, session_id: str) -> VehicleEnergySystem:
        system = self._systems.get(session_id)
        if system is None:
            system = self._build_energy_system()
            self._systems[session_id] = system
            self._repo.ensure_session(session_id, source=AcquisitionConfig.SOURCE)
            logger.info("processing_session_started", session=session_id)
        return system

    def update_config(self, topic: str, payload: str) -> None:
        """Apply a live config update (vehicle params + alert thresholds)."""
        cfg = json.loads(payload)
        v = cfg.get("vehicle", {})
        if "mass_vehicle" in v and "mass_driver" in v:
            self._mass = float(v["mass_vehicle"]) + float(v["mass_driver"])
        for key, attr in (
            ("drag_coefficient", "_drag"), ("frontal_area", "_frontal_area"),
            ("rolling_resistance", "_rolling"), ("battery_capacity_j", "_battery_capacity"),
            ("nominal_dc_voltage", "_nominal_voltage"),
        ):
            if key in v:
                setattr(self, attr, float(v[key]))
        a = cfg.get("alerts", {})
        for key in ("soc_warning", "soc_critical", "idc_warning", "idc_critical",
                    "speed_warning", "speed_critical"):
            if key in a:
                setattr(self._thresholds, key, float(a[key]))
        self._systems.clear()
        logger.info("config_updated", mass=self._mass, nominal_voltage=self._nominal_voltage)

    def process_message(self, topic: str, payload: str) -> None:
        raw = RawTelemetryDto.model_validate_json(payload)
        system = self._system_for(raw.session_id)

        resp = system.update(
            UpdateRequestDto(
                velocity=raw.velocity,
                acceleration=raw.acceleration,
                dt=raw.dt,
            )
        )

        if raw.vdc is not None and raw.idc is not None:
            vdc, idc = raw.vdc, raw.idc
        else:
            vdc, idc = derive_dc_bus(
                resp.power, resp.electrical_used_or_recovered, raw.dt, resp.soc,
                self._nominal_voltage,
            )

        alerts = evaluate(
            soc=resp.soc,
            vdc=vdc,
            idc=idc,
            velocity=raw.velocity,
            power=resp.power,
            thresholds=self._thresholds,
        )

        processed = ProcessedTelemetryDto(
            session_id=raw.session_id,
            timestamp=raw.timestamp,
            velocity=raw.velocity,
            acceleration=raw.acceleration,
            vdc=round(vdc, 3),
            idc=round(idc, 3),
            power=round(resp.power, 2),
            energy=round(resp.mech_energy_total, 2),
            soc=round(resp.soc, 6),
            distance=round(resp.distance_total, 2),
            avg_power=round(resp.avg_power, 2),
            specific_consumption=round(resp.specific_consumption, 6),
            autonomy=round(resp.estimated_autonomy, 1),
            x=raw.x,
            y=raw.y,
            alerts=alerts,
        )

        try:
            self._repo.insert(processed)
        except Exception as e:
            logger.error("persist_failed", session=raw.session_id, error=str(e))
            processed.alerts.append(Alert.of(AlertCode.PERSIST, Severity.ERROR))

        for a in alerts:
            logger.warning("telemetry_alert", code=a.code.value, severity=a.severity.value,
                           value=a.value, session=raw.session_id)

        self._mqtt.publish(MqttConfig.TOPIC_PROCESSED, processed.model_dump_json())

    def run(self) -> None:
        self._repo.init_schema()
        self._mqtt.connect()
        self._mqtt.subscribe(MqttConfig.TOPIC_RAW, self.process_message)
        self._mqtt.subscribe(MqttConfig.TOPIC_CONFIG, self.update_config)
        logger.info("processing_start", topic=MqttConfig.TOPIC_RAW)
        self._mqtt.loop_forever()
