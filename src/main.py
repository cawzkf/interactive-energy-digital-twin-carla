from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.domain.dtos import UpdateRequestDto
import structlog

logger = structlog.get_logger(__name__)

def main():
    """
    Main function to demonstrate the usage of the VehicleEnergySystem, EnergyModel, and Battery classes.

    :return: None
    """
    battery = Battery(capacity=50_000_000, soc_init=1.0)
    battery.discharge(mech_energy=10_000)
    battery.regen(mech_energy=5_000)

    energy_model = EnergyModel(
        mass=1500,
        drag_coefficient=0.3,
        frontal_area=2.2,
        rolling_resistance_coefficient=0.015,
    )

    battery = Battery(
        capacity=50_000_000,
        soc_init=1.0,
        efficiency_discharge=0.9,
        efficiency_regen=0.9,
    )

    vehicle_system = VehicleEnergySystem(energy_model, battery)

    logger.info("[Estado inicial SoC]:", soc_init=battery.soc)

    electrical_used = battery.discharge(mech_energy=10_000)

    logger.info("[Eletricidade usada]:", electri_used=electrical_used)
    logger.info("[SoC após descarga]:", soc_discharge=battery.soc)

    electrical_recovered = battery.regen(mech_energy=5_000)

    logger.info("[Eletricidade recuperada]:", electri_recovered=electrical_recovered)
    logger.info("[SoC após regeneração]:", soc_regen=battery.soc)

    req = UpdateRequestDto(velocity=10.0, acceleration=1.0, dt=0.1)
    resp = vehicle_system.update(req)

    logger.info(resp)

if __name__ == "__main__":
    main()