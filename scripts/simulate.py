"""
Synthetic simulation — runs the full energy pipeline without CARLA or BaSyx.
Simulates a vehicle accelerating, cruising, and braking.
"""

from src.domain.battery import Battery
from src.domain.dtos import UpdateRequestDto
from src.domain.energy_model import EnergyModel
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.infra.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)

DT = 0.1
TOTAL_TIME = 60.0


def velocity_profile(t: float) -> tuple[float, float]:
    if t < 15:
        acc = 2.0
        vel = acc * t
    elif t < 40:
        acc = 0.0
        vel = 30.0
    else:
        acc = -1.5
        vel = max(0.0, 30.0 + acc * (t - 40))
        if vel == 0.0:
            acc = 0.0
    return vel, acc


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
    system = VehicleEnergySystem(energy_model, battery)

    steps = int(TOTAL_TIME / DT)
    t = 0.0

    logger.info("simulation_start", total_time=TOTAL_TIME, dt=DT, steps=steps)

    for i in range(steps):
        vel, acc = velocity_profile(t)
        request = UpdateRequestDto(velocity=vel, acceleration=acc, dt=DT)
        resp = system.update(request)

        if i % 50 == 0:
            logger.info(
                "vehicle_update",
                t=round(t, 1),
                velocity=round(vel, 2),
                acceleration=round(acc, 2),
                power=round(resp.power, 1),
                soc=round(resp.soc, 6),
                energy=round(resp.mech_energy_total, 1),
                distance=round(resp.distance_total, 1),
                avg_power=round(resp.avg_power, 1),
                consumption_wh_m=round(resp.specific_consumption, 6),
                autonomy_s=round(resp.estimated_autonomy, 1),
            )

        t += DT

    logger.info(
        "simulation_end",
        final_soc=round(resp.soc, 6),
        total_distance=round(resp.distance_total, 1),
        total_energy=round(resp.mech_energy_total, 1),
        final_autonomy=round(resp.estimated_autonomy, 1),
    )


if __name__ == "__main__":
    main()
