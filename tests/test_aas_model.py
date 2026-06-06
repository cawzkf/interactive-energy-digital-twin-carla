"""Unit tests for the canonical telemetry model, structured as Arrange-Act-Assert."""
from src.domain.aas_model import TELEMETRY_VARIABLES
from src.domain.dtos import ProcessedTelemetryDto


class TestCanonicalModel:
    def test_every_mapped_field_exists_on_processed_dto(self):
        # Arrange
        dto_fields = set(ProcessedTelemetryDto.model_fields)
        # Act
        mapped_fields = [field for _, field, _ in TELEMETRY_VARIABLES]
        # Assert
        for id_short, field, _ in TELEMETRY_VARIABLES:
            assert field in dto_fields, f"{field} ({id_short}) missing on ProcessedTelemetryDto"
        assert len(mapped_fields) == len(set(mapped_fields))  # no duplicates

    def test_idshorts_are_unique(self):
        # Arrange / Act
        id_shorts = [id_short for id_short, _, _ in TELEMETRY_VARIABLES]
        # Assert
        assert len(id_shorts) == len(set(id_shorts))
