
from pydantic import BaseModel

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