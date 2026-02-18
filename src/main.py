from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.domain.dtos import UpdateRequestDto
from infra.carla_client import CarlaClient

import structlog

logger = structlog.get_logger(__name__)

def main():
    """
    Main function to demonstrate the usage of the VehicleEnergySystem, EnergyModel, and Battery classes.

    :return: None
    """

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

    carla_client = CarlaClient()
    carla_client.connect()
    carla_client.spawn_vehicle()
    logger.info("[CARLA CLIENT INITIALIZED]")
    try:
        while True:
            carla_client.apply_control(throttle=0.5)
            state = carla_client.tick()

            if state is None:
                logger.warning("No state received from CARLA. Skipping update.")
                continue

            req = state
            resp = vehicle_system.update(req)
            logger.info("[VEHICLE STATE]", velocity=state['velocity'], acceleration=state['acceleration'], dt=state['dt'])
            logger.info("[ENERGY SYSTEM]", power=resp.power, mech_energy_total=resp.mech_energy_total, soc=resp.soc)

    except KeyboardInterrupt:
        logger.warning("Exiting...")

    finally:
        carla_client.destroy()

if __name__ == "__main__":
    main()