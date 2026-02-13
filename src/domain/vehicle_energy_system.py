from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.dtos import UpdateResponseDto, UpdateRequestDto

class VehicleEnergySystem:
    def __init__(self, energy_model: EnergyModel, battery: Battery):
        self.energy_model = energy_model
        self.battery = battery


    def update(self, request: UpdateRequestDto) -> UpdateResponseDto:
        """
        Update the vehicle energy system based on the current velocity,
        acceleration, and time step.

        :param request: UpdateRequestDto containing velocity, acceleration, and dt
        :return: UpdateResponseDto containing power, mech_energy_total,
        soc, and electrical_used_or_recovered
        """
        power, mech_energy_total = self.energy_model.update(
            request.velocity,
            request.acceleration,
            request.dt)

        step_mech = power * request.dt

        if power > 0:
            electrical_used = self.battery.discharge(step_mech)
            return UpdateResponseDto(
                power=power,
                mech_energy_total=mech_energy_total,
                soc=self.battery.soc,
                electrical_used_or_recovered=electrical_used
            )
        else:
            electrical_recovered = self.battery.regen(-step_mech)
            return UpdateResponseDto(
                power=power,
                mech_energy_total=mech_energy_total,
                soc=self.battery.soc,
                electrical_used_or_recovered=electrical_recovered
            )

