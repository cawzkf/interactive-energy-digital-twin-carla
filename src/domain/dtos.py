
from pydantic import BaseModel

from src.domain.diagnostics import Alert


class UpdateRequestDto(BaseModel):
    """
    Model the request for the update endpoint,
    containing the velocity, acceleration, and time step.

    :param velocity: Current velocity of the vehicle (m/s)
    :param acceleration: Current acceleration of the vehicle (m/s^2)
    :param dt: Time step for the update (s)
    """
    velocity: float
    acceleration: float
    dt: float
    x: float | None = None
    y: float | None = None


class UpdateResponseDto(BaseModel):
    """
    Model the response of the update endpoint,
    containing the power, total mechanical energy, state of charge,
    and electrical energy used or recovered.

    :param power: The power at the current state (W)
    :param mech_energy_total: The total mechanical energy (J)
    :param soc: The state of charge of the battery (0 to 1)
    :param electrical_used_or_recovered: The electrical energy used or recovered (J)
    """
    power: float
    mech_energy_total: float
    soc: float
    electrical_used_or_recovered: float
    distance_total: float
    avg_power: float
    specific_consumption: float
    estimated_autonomy: float


class RawTelemetryDto(BaseModel):
    """
    Raw acquisition message published on the MQTT logical bus.

    Represents what the acquisition layer (CARLA today, RS485 bridge tomorrow)
    measures before any energy processing. Vdc/Idc are optional: they are filled
    when measured at the DC bus, and derived by the processing service otherwise.

    :param session_id: Identifier of the test session this sample belongs to
    :param timestamp: Unix epoch (seconds) when the sample was acquired
    :param velocity: Longitudinal velocity of the vehicle (m/s)
    :param acceleration: Longitudinal acceleration of the vehicle (m/s^2)
    :param dt: Time step since the previous sample (s)
    :param vdc: Measured DC bus voltage (V), if available
    :param idc: Measured DC bus current (A), if available
    """
    session_id: str
    timestamp: float
    velocity: float
    acceleration: float
    dt: float
    vdc: float | None = None
    idc: float | None = None
    x: float | None = None
    y: float | None = None


class ProcessedTelemetryDto(BaseModel):
    """
    Processed telemetry message published on the MQTT logical bus and persisted.

    Carries the energy indicators derived by the domain model plus the DC bus
    grandezas (Vdc, Idc, Pdc) expected by the MarchForce telemetry table.

    :param session_id: Identifier of the test session this sample belongs to
    :param timestamp: Unix epoch (seconds) when the sample was acquired
    :param velocity: Longitudinal velocity of the vehicle (m/s)
    :param acceleration: Longitudinal acceleration of the vehicle (m/s^2)
    :param vdc: DC bus voltage (V), measured or derived
    :param idc: DC bus current (A), measured or derived
    :param power: Instantaneous mechanical power (W)
    :param energy: Accumulated mechanical energy (J)
    :param soc: Battery state of charge (0 to 1)
    :param distance: Accumulated distance (m)
    :param avg_power: Moving-average power (W)
    :param specific_consumption: Specific consumption (Wh/m)
    :param autonomy: Estimated autonomy at current average power (s)
    """
    session_id: str
    timestamp: float
    velocity: float
    acceleration: float
    vdc: float
    idc: float
    power: float
    energy: float
    soc: float
    distance: float
    avg_power: float
    specific_consumption: float
    autonomy: float
    x: float | None = None
    y: float | None = None
    alerts: list[Alert] = []
