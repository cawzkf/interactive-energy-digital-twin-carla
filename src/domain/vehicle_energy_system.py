from collections import deque

from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.dtos import UpdateResponseDto, UpdateRequestDto

POWER_HISTORY_SIZE = 50


class VehicleEnergySystem:
    def __init__(self, energy_model: EnergyModel, battery: Battery):
        self.energy_model = energy_model
        self.battery = battery
        self._distance: float = 0.0
        self._electrical_energy_total: float = 0.0
        self._power_history: deque[float] = deque(maxlen=POWER_HISTORY_SIZE)

    def update(self, request: UpdateRequestDto) -> UpdateResponseDto:
        power, mech_energy_total = self.energy_model.update(
            request.velocity,
            request.acceleration,
            request.dt,
        )

        self._distance += abs(request.velocity) * request.dt
        self._power_history.append(power)

        step_mech = power * request.dt

        if power > 0:
            electrical = self.battery.discharge(step_mech)
            self._electrical_energy_total += electrical
        else:
            electrical = self.battery.regen(-step_mech)

        avg_power = sum(self._power_history) / len(self._power_history)

        if self._distance > 0:
            specific_consumption = (self._electrical_energy_total / 3600.0) / self._distance
        else:
            specific_consumption = 0.0

        if avg_power > 0:
            remaining_energy = self.battery.soc * self.battery.capacity
            estimated_autonomy = remaining_energy / avg_power
        else:
            estimated_autonomy = 0.0

        return UpdateResponseDto(
            power=power,
            mech_energy_total=mech_energy_total,
            soc=self.battery.soc,
            electrical_used_or_recovered=electrical,
            distance_total=self._distance,
            avg_power=avg_power,
            specific_consumption=specific_consumption,
            estimated_autonomy=estimated_autonomy,
        )
