import structlog

logger = structlog.get_logger(__name__)

class Battery:
    def __init__(
            self,
            capacity: float,
            soc_init: float = 1.0,
            efficiency_discharge: float = 0.9,
            efficiency_regen: float = 0.9,
    ):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if not (0 <= soc_init <= 1):
            raise ValueError("soc_init must be between 0 and 1")
        if not (0 < efficiency_discharge <= 1):
            raise ValueError("efficiency_discharge must be between 0 and 1")
        if not (0 < efficiency_regen <= 1):
            raise ValueError("efficiency_regen must be between 0 and 1")


        self.capacity = capacity
        self.soc = soc_init
        self.efficiency_discharge = efficiency_discharge
        self.efficiency_regen = efficiency_regen


    def discharge(self, mech_energy: float) -> float:
        """
        Discharge the battery to provide the required mechanical energy.

        :param mech_energy: The mechanical energy required (in J).
        :return: The electrical energy drawn from the battery (in J).
        """
        electrical_needed = mech_energy / self.efficiency_discharge
        delta_soc = electrical_needed / self.capacity
        self.soc -= delta_soc
        logger.info("[Battery discharge]", mech_energy=mech_energy, electrical_needed=electrical_needed, delta_soc=delta_soc, soc=self.soc)
        return electrical_needed

    def regen(self, mech_energy: float) -> float:
        """
        Regenerate the battery with the given mechanical energy.

        :param mech_energy: The mechanical energy available for regeneration (in J).
        :return: The electrical energy recovered and stored in the battery (in J).
        """
        electrical_recovered = mech_energy * self.efficiency_regen
        delta_soc = electrical_recovered / self.capacity
        self.soc += delta_soc
        self.soc = max(0.0, min(self.soc, 1.0))
        logger.info(
            "[Battery regen]",
                    mech_energy=mech_energy,
                    electrical_recovered=electrical_recovered,
                    delta_soc=delta_soc,
                    soc=self.soc,
            )
        return electrical_recovered
