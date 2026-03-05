import pytest
from src.domain.battery import Battery


@pytest.fixture
def battery():
    return Battery(capacity=50_000_000, soc_init=1.0, efficiency_discharge=0.9, efficiency_regen=0.9)


class TestBatteryInit:
    def test_valid_params(self, battery):
        assert battery.soc == 1.0
        assert battery.capacity == 50_000_000

    def test_zero_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity must be positive"):
            Battery(capacity=0)

    def test_soc_out_of_range_raises(self):
        with pytest.raises(ValueError, match="soc_init must be between 0 and 1"):
            Battery(capacity=1000, soc_init=1.5)

    def test_invalid_efficiency_raises(self):
        with pytest.raises(ValueError, match="efficiency_discharge must be between 0 and 1"):
            Battery(capacity=1000, efficiency_discharge=0)


class TestBatteryDischarge:
    def test_discharge_reduces_soc(self, battery):
        initial_soc = battery.soc
        battery.discharge(1000)
        assert battery.soc < initial_soc

    def test_discharge_returns_electrical_energy(self, battery):
        electrical = battery.discharge(900)
        assert electrical == 900 / 0.9

    def test_multiple_discharges_accumulate(self, battery):
        battery.discharge(1000)
        soc1 = battery.soc
        battery.discharge(1000)
        soc2 = battery.soc
        assert soc2 < soc1


class TestBatteryRegen:
    def test_regen_increases_soc(self):
        bat = Battery(capacity=50_000_000, soc_init=0.5)
        initial_soc = bat.soc
        bat.regen(1000)
        assert bat.soc > initial_soc

    def test_regen_returns_recovered_energy(self, battery):
        recovered = battery.regen(1000)
        assert recovered == 1000 * 0.9

    def test_regen_clamps_soc_at_1(self):
        bat = Battery(capacity=100, soc_init=0.99)
        bat.regen(100)
        assert bat.soc == 1.0
