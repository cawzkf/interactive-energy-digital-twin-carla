import pytest
from src.domain.energy_model import EnergyModel


@pytest.fixture
def model():
    return EnergyModel(
        mass=1500,
        drag_coefficient=0.3,
        frontal_area=2.2,
        rolling_resistance_coefficient=0.015,
    )


class TestEnergyModelInit:
    def test_valid_params(self, model):
        assert model.mass == 1500
        assert model.energy == 0.0

    def test_negative_mass_raises(self):
        with pytest.raises(ValueError, match="mass must be positive"):
            EnergyModel(mass=-1, drag_coefficient=0.3, frontal_area=2.2, rolling_resistance_coefficient=0.015)

    def test_negative_drag_raises(self):
        with pytest.raises(ValueError, match="drag_coefficient must be non-negative"):
            EnergyModel(mass=1500, drag_coefficient=-0.1, frontal_area=2.2, rolling_resistance_coefficient=0.015)

    def test_zero_frontal_area_raises(self):
        with pytest.raises(ValueError, match="frontal_area must be positive"):
            EnergyModel(mass=1500, drag_coefficient=0.3, frontal_area=0, rolling_resistance_coefficient=0.015)


class TestEnergyModelUpdate:
    def test_stationary_vehicle_zero_power(self, model):
        power, energy = model.update(velocity=0.0, acceleration=0.0, dt=0.1)
        assert power == 0.0
        assert energy == 0.0

    def test_constant_velocity_positive_power(self, model):
        power, energy = model.update(velocity=10.0, acceleration=0.0, dt=0.1)
        assert power > 0
        assert energy > 0

    def test_accelerating_increases_power(self, model):
        p1, _ = model.update(velocity=10.0, acceleration=0.0, dt=0.1)
        model.reset_energy()
        p2, _ = model.update(velocity=10.0, acceleration=2.0, dt=0.1)
        assert p2 > p1

    def test_energy_accumulates(self, model):
        _, e1 = model.update(velocity=10.0, acceleration=1.0, dt=0.1)
        _, e2 = model.update(velocity=10.0, acceleration=1.0, dt=0.1)
        assert e2 > e1

    def test_negative_dt_raises(self, model):
        with pytest.raises(ValueError, match="dt must be positive"):
            model.update(velocity=10.0, acceleration=0.0, dt=-0.1)

    def test_reset_energy(self, model):
        model.update(velocity=10.0, acceleration=1.0, dt=0.1)
        assert model.energy > 0
        model.reset_energy()
        assert model.energy == 0.0
