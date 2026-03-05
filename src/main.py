from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.application.twin_service import TwinService
from src.infra.carla_client import CarlaClient
from src.infra.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def main():
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

    twin_service = TwinService()
    basyx_available = twin_service.check_connection()

    carla_client = CarlaClient()
    carla_client.connect()
    carla_client.spawn_vehicle()
    logger.info("carla_client_initialized")

    try:
        while True:
            carla_client.apply_control(throttle=0.5)
            state = carla_client.tick()

            if state is None:
                logger.warning("no_state_received")
                continue

            resp = vehicle_system.update(state)
            logger.info(
                "vehicle_update",
                velocity=round(state.velocity, 3),
                acceleration=round(state.acceleration, 3),
                power=round(resp.power, 2),
                soc=round(resp.soc, 4),
                energy=round(resp.mech_energy_total, 2),
                distance=round(resp.distance_total, 2),
                avg_power=round(resp.avg_power, 2),
                consumption_wh_m=round(resp.specific_consumption, 6),
                autonomy_s=round(resp.estimated_autonomy, 1),
            )

            if basyx_available:
                twin_service.sync(state, resp)

    except KeyboardInterrupt:
        logger.warning("exiting")

    finally:
        carla_client.destroy()


if __name__ == "__main__":
    main()
