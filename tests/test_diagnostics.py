"""Unit tests for the diagnostics module, structured as Arrange-Act-Assert."""
import math

import pytest

from src.domain.diagnostics import (
    Alert,
    AlertCode,
    DiagnosticThresholds,
    Severity,
    evaluate,
)


def _nominal_kwargs(**overrides):
    base = dict(soc=1.0, vdc=48.0, idc=10.0, velocity=10.0, power=500.0)
    base.update(overrides)
    return base


class TestEnums:
    def test_severity_exposes_string_values(self):
        # Assert
        assert Severity.WARNING.value == "warning"
        assert Severity.ERROR.value == "error"

    def test_alert_code_behaves_as_string(self):
        # Assert — str-enum serializes to its value (matters for JSON/dashboard)
        assert AlertCode.SOC_CRITICAL.value == "E-SOC-CRITICAL"
        assert AlertCode.SOC_CRITICAL == "E-SOC-CRITICAL"

    def test_alert_factory_fills_message_from_catalog(self):
        # Act
        alert = Alert.of(AlertCode.SOC_LOW, Severity.WARNING, value=12.0)
        # Assert
        assert alert.code == AlertCode.SOC_LOW
        assert alert.severity == Severity.WARNING
        assert alert.message
        assert alert.value == 12.0


class TestNominalOperation:
    def test_no_alerts_when_every_reading_in_range(self):
        # Arrange
        kwargs = _nominal_kwargs()
        # Act
        alerts = evaluate(**kwargs)
        # Assert
        assert alerts == []


class TestStateOfCharge:
    def test_low_soc_raises_warning(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(soc=0.15))
        # Assert
        assert any(a.code == AlertCode.SOC_LOW for a in alerts)

    def test_critical_soc_raises_error(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(soc=0.02))
        # Assert
        critical = [a for a in alerts if a.code == AlertCode.SOC_CRITICAL]
        assert critical
        assert all(a.severity == Severity.ERROR for a in critical)


class TestDcVoltage:
    def test_voltage_in_warning_band(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(vdc=48.0 * 1.12))
        # Assert
        assert any(a.code == AlertCode.VDC_RANGE_WARN for a in alerts)

    def test_voltage_in_error_band(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(vdc=48.0 * 1.25))
        # Assert
        assert any(a.code == AlertCode.VDC_RANGE_ERROR for a in alerts)


class TestDcCurrent:
    def test_high_current_raises_warning(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(idc=70.0))
        # Assert
        assert any(a.code == AlertCode.IDC_HIGH for a in alerts)

    def test_overcurrent_uses_magnitude_for_regen(self):
        # Arrange — negative (regen) current with large magnitude
        alerts = evaluate(**_nominal_kwargs(idc=-120.0))
        # Assert
        assert any(a.code == AlertCode.IDC_OVERCURRENT for a in alerts)


class TestSpeed:
    def test_high_speed_raises_warning(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(velocity=35.0))
        # Assert
        assert any(a.code == AlertCode.SPEED_HIGH for a in alerts)

    def test_critical_speed_raises_error(self):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(velocity=45.0))
        # Assert
        assert any(a.code == AlertCode.SPEED_CRITICAL for a in alerts)


class TestInvalidData:
    @pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
    def test_invalid_reading_short_circuits_to_single_error(self, bad_value):
        # Arrange / Act
        alerts = evaluate(**_nominal_kwargs(power=bad_value))
        # Assert
        assert len(alerts) == 1
        assert alerts[0].code == AlertCode.DATA_INVALID


class TestCustomThresholds:
    def test_overridden_threshold_changes_outcome(self):
        # Arrange
        thresholds = DiagnosticThresholds(idc_warning=5.0)
        # Act
        alerts = evaluate(**_nominal_kwargs(idc=6.0), thresholds=thresholds)
        # Assert
        assert any(a.code == AlertCode.IDC_HIGH for a in alerts)
