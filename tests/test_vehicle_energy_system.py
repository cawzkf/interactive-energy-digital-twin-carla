import pytest
from src.domain.energy_model import EnergyModel
from src.domain.battery import Battery
from src.domain.vehicle_energy_system import VehicleEnergySystem
from src.domain.dtos import UpdateRequestDto


@pytest.fixture
def system():
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
    return VehicleEnergySystem(energy_model, battery)


def make_request(velocity=10.0, acceleration=0.0, dt=0.1):
    return UpdateRequestDto(velocity=velocity, acceleration=acceleration, dt=dt)


class TestVehicleEnergySystemUpdate:
    def test_returns_all_fields(self, system):
        resp = system.update(make_request())
        assert resp.power is not None
        assert resp.mech_energy_total is not None
        assert resp.soc is not None
        assert resp.electrical_used_or_recovered is not None
        assert resp.distance_total is not None
        assert resp.avg_power is not None
        assert resp.specific_consumption is not None
        assert resp.estimated_autonomy is not None

    def test_distance_accumulates(self, system):
        system.update(make_request(velocity=10.0, dt=0.1))
        r2 = system.update(make_request(velocity=10.0, dt=0.1))
        assert r2.distance_total == pytest.approx(2.0, abs=0.01)

    def test_soc_decreases_with_positive_power(self, system):
        resp = system.update(make_request(velocity=10.0, acceleration=1.0))
        assert resp.soc < 1.0

    def test_avg_power_single_step(self, system):
        resp = system.update(make_request(velocity=10.0))
        assert resp.avg_power == pytest.approx(resp.power)

    def test_avg_power_converges(self, system):
        for _ in range(50):
            resp = system.update(make_request(velocity=10.0))
        assert resp.avg_power > 0

    def test_specific_consumption_positive(self, system):
        for _ in range(10):
            resp = system.update(make_request(velocity=10.0))
        assert resp.specific_consumption > 0

    def test_estimated_autonomy_positive(self, system):
        resp = system.update(make_request(velocity=10.0))
        assert resp.estimated_autonomy > 0

    def test_estimated_autonomy_decreases_over_time(self, system):
        for _ in range(10):
            resp = system.update(make_request(velocity=10.0, acceleration=2.0))
        autonomy_early = resp.estimated_autonomy

        for _ in range(100):
            resp = system.update(make_request(velocity=10.0, acceleration=2.0))
        assert resp.estimated_autonomy < autonomy_early

    def test_stationary_vehicle(self, system):
        resp = system.update(make_request(velocity=0.0, acceleration=0.0))
        assert resp.power == 0.0
        assert resp.distance_total == 0.0
        assert resp.specific_consumption == 0.0
        assert resp.estimated_autonomy == 0.0
