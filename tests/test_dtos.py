"""Unit tests for the telemetry DTOs, structured as Arrange-Act-Assert."""
import json

from src.domain.diagnostics import Alert, AlertCode, Severity
from src.domain.dtos import (
    ProcessedTelemetryDto,
    RawTelemetryDto,
    UpdateRequestDto,
)


def _processed(**overrides):
    base = dict(
        session_id="s", timestamp=1.0, velocity=1.0, acceleration=0.0,
        vdc=48.0, idc=5.0, power=100.0, energy=10.0, soc=0.9,
        distance=1.0, avg_power=100.0, specific_consumption=0.0, autonomy=10.0,
    )
    base.update(overrides)
    return ProcessedTelemetryDto(**base)


class TestRawTelemetryDto:
    def test_json_roundtrip_preserves_fields(self):
        # Arrange
        raw = RawTelemetryDto(
            session_id="sess-1", timestamp=1700000000.0,
            velocity=10.0, acceleration=1.0, dt=0.1,
        )
        # Act
        parsed = RawTelemetryDto.model_validate_json(raw.model_dump_json())
        # Assert
        assert parsed == raw
        assert parsed.vdc is None
        assert parsed.idc is None

    def test_optional_bus_measurements_are_kept(self):
        # Arrange / Act
        raw = RawTelemetryDto(
            session_id="s", timestamp=1.0, velocity=0.0, acceleration=0.0,
            dt=0.1, vdc=48.0, idc=5.0,
        )
        # Assert
        assert raw.vdc == 48.0
        assert raw.idc == 5.0


class TestProcessedTelemetryDto:
    def test_alerts_serialize_as_string_codes(self):
        # Arrange
        dto = _processed(alerts=[Alert.of(AlertCode.SOC_LOW, Severity.WARNING, 12.0)])
        # Act
        payload = json.loads(dto.model_dump_json())
        # Assert
        assert payload["alerts"][0]["code"] == "W-SOC-LOW"
        assert payload["alerts"][0]["severity"] == "warning"

    def test_alerts_default_to_empty_list(self):
        # Arrange / Act
        dto = _processed()
        # Assert
        assert dto.alerts == []


class TestUpdateRequestDto:
    def test_stores_kinematic_fields(self):
        # Arrange / Act
        req = UpdateRequestDto(velocity=5.0, acceleration=1.0, dt=0.1)
        # Assert
        assert req.velocity == 5.0
        assert req.acceleration == 1.0
        assert req.dt == 0.1
