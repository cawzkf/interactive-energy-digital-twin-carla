import math
from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel

from src.infra.config import AcquisitionConfig


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AlertCode(StrEnum):
    OK = "OK"
    DATA_INVALID = "E-DATA-INVALID"
    SOC_LOW = "W-SOC-LOW"
    SOC_CRITICAL = "E-SOC-CRITICAL"
    VDC_RANGE_WARN = "W-VDC-RANGE"
    VDC_RANGE_ERROR = "E-VDC-RANGE"
    IDC_HIGH = "W-IDC-HIGH"
    IDC_OVERCURRENT = "E-IDC-OVERCURRENT"
    SPEED_HIGH = "W-SPEED-HIGH"
    SPEED_CRITICAL = "E-SPEED-CRITICAL"
    COMM_STALE = "E-COMM-STALE"
    PERSIST = "E-PERSIST"
    MQTT = "E-MQTT"


DESCRIPTIONS: dict[AlertCode, str] = {
    AlertCode.OK: "Sistema operando normalmente",
    AlertCode.DATA_INVALID: "Leitura inválida (NaN/inf) no processamento",
    AlertCode.SOC_LOW: "Estado de carga baixo",
    AlertCode.SOC_CRITICAL: "Estado de carga crítico",
    AlertCode.VDC_RANGE_WARN: "Tensão do barramento DC fora da faixa esperada",
    AlertCode.VDC_RANGE_ERROR: "Tensão do barramento DC muito fora da faixa",
    AlertCode.IDC_HIGH: "Corrente DC elevada",
    AlertCode.IDC_OVERCURRENT: "Sobrecorrente no barramento DC",
    AlertCode.SPEED_HIGH: "Velocidade elevada",
    AlertCode.SPEED_CRITICAL: "Velocidade crítica",
    AlertCode.COMM_STALE: "Telemetria interrompida (sem dados recentes)",
    AlertCode.PERSIST: "Falha ao persistir a amostra no banco",
    AlertCode.MQTT: "Falha de comunicação com o broker MQTT",
}


class Alert(BaseModel):
    """A single diagnostic event surfaced to the dashboard."""
    code: AlertCode
    severity: Severity
    message: str
    value: float | None = None

    @classmethod
    def of(cls, code: AlertCode, severity: Severity, value: float | None = None) -> "Alert":
        return cls(code=code, severity=severity, message=DESCRIPTIONS[code], value=value)


@dataclass
class DiagnosticThresholds:
    soc_warning: float = 0.20
    soc_critical: float = 0.05
    vdc_warn_band: float = 0.10
    vdc_error_band: float = 0.20
    idc_warning: float = 60.0
    idc_critical: float = 100.0
    speed_warning: float = 33.0
    speed_critical: float = 42.0


def _is_invalid(*values: float) -> bool:
    return any(math.isnan(v) or math.isinf(v) for v in values)


def evaluate(
    *,
    soc: float,
    vdc: float,
    idc: float,
    velocity: float,
    power: float,
    thresholds: DiagnosticThresholds | None = None,
) -> list[Alert]:
    """Evaluate a processed sample and return the list of active alerts."""
    th = thresholds or DiagnosticThresholds()
    alerts: list[Alert] = []

    if _is_invalid(soc, vdc, idc, velocity, power):
        alerts.append(Alert.of(AlertCode.DATA_INVALID, Severity.ERROR))
        return alerts

    if soc <= th.soc_critical:
        alerts.append(Alert.of(AlertCode.SOC_CRITICAL, Severity.ERROR, round(soc * 100, 1)))
    elif soc <= th.soc_warning:
        alerts.append(Alert.of(AlertCode.SOC_LOW, Severity.WARNING, round(soc * 100, 1)))

    nominal = AcquisitionConfig.NOMINAL_DC_VOLTAGE
    deviation = abs(vdc - nominal) / nominal if nominal > 0 else 0.0
    if deviation >= th.vdc_error_band:
        alerts.append(Alert.of(AlertCode.VDC_RANGE_ERROR, Severity.ERROR, round(vdc, 2)))
    elif deviation >= th.vdc_warn_band:
        alerts.append(Alert.of(AlertCode.VDC_RANGE_WARN, Severity.WARNING, round(vdc, 2)))

    idc_mag = abs(idc)
    if idc_mag >= th.idc_critical:
        alerts.append(Alert.of(AlertCode.IDC_OVERCURRENT, Severity.ERROR, round(idc, 2)))
    elif idc_mag >= th.idc_warning:
        alerts.append(Alert.of(AlertCode.IDC_HIGH, Severity.WARNING, round(idc, 2)))

    if velocity >= th.speed_critical:
        alerts.append(Alert.of(AlertCode.SPEED_CRITICAL, Severity.ERROR, round(velocity, 2)))
    elif velocity >= th.speed_warning:
        alerts.append(Alert.of(AlertCode.SPEED_HIGH, Severity.WARNING, round(velocity, 2)))

    return alerts
