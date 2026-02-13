"""Domain model of vehicle energy based on longitudinal dynamics."""

import math
import structlog
logger = structlog.get_logger(__name__)

class EnergyModel:
    """Energy model for a vehicle, calculating the power and energy based on."""
    def __init__(
        self,
        mass: float,
        drag_coefficient: float,
        frontal_area: float,
        rolling_resistance_coefficient: float,
        air_density: float = 1.225,
        gravity: float = 9.81,
    ):
        if mass <= 0:
            raise ValueError("mass must be positive")
        if drag_coefficient < 0:
            raise ValueError("drag_coefficient must be non-negative")
        if frontal_area <= 0:
            raise ValueError("frontal_area must be positive")
        if rolling_resistance_coefficient < 0:
            raise ValueError("rolling_resistance_coefficient must be non-negative")
        if air_density <= 0:
            raise ValueError("air_density must be positive")

        self.mass = mass
        self.drag_coefficient = drag_coefficient
        self.frontal_area = frontal_area
        self.rolling_resistance_coefficient = rolling_resistance_coefficient
        self.air_density = air_density
        self.gravity = gravity
        self.energy: float = 0.0

    def update(self, velocity: float, acceleration: float, dt: float) -> tuple[float, float]:
        """
        Update the energy model based on the current velocity,
        acceleration, and time step.

        :param velocity: Current velocity of the vehicle (m/s)
        :param acceleration: Current acceleration of the vehicle (m/s^2)
        :param dt: Time step for the update (s)
        :return: Tuple containing the power (W) and total energy (J)
        """

        if dt <= 0:
            raise ValueError("dt must be positive")

        f_inertial = self.mass * acceleration
        f_aero = 0.5 * self.air_density * self.drag_coefficient * self.frontal_area * velocity**2
        f_roll = self.rolling_resistance_coefficient * self.mass * self.gravity
        logger.info(
            "[Calculating forces]",
            f_inertial=f_inertial,
            f_aero=f_aero,
            f_roll=f_roll,
        )

        f_total = f_inertial + f_aero + f_roll
        power = f_total * velocity

        logger.info(
            "[Calculating power]",
            f_total=f_total,
            velocity=velocity,
            power=power,
        )

        if power > 0:
            previous_energy = self.energy
            self.energy += power * dt
            if not math.isclose(self.energy, previous_energy, rel_tol=1e-9):
                logger.info(
                    "[Accumulating energy]",
                    power=power,
                    dt=dt,
                    total_energy=self.energy,
                )
        return power, self.energy

    def reset_energy(self) -> None:
        """
        Reset of the accumulated energy.

        :return: None
        """
        self.energy = 0.0
        logger.info("[Energy reset]", total_energy=self.energy)



