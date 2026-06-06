"""Unit tests for the environment configuration, structured as Arrange-Act-Assert."""
from src.infra.config import DbConfig, SourceType


class TestSourceType:
    def test_exposes_carla_and_sim_values(self):
        # Assert
        assert SourceType.CARLA.value == "carla"
        assert SourceType.SIM.value == "sim"


class TestDbConfigDsn:
    def test_full_dsn_override_takes_precedence(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("TELEMETRY_DSN", "postgresql://u:p@h:5432/db")
        # Act
        dsn = DbConfig.dsn()
        # Assert
        assert dsn == "postgresql://u:p@h:5432/db"

    def test_builds_dsn_from_individual_parts(self, monkeypatch):
        # Arrange
        monkeypatch.delenv("TELEMETRY_DSN", raising=False)
        # Act
        dsn = DbConfig.dsn()
        # Assert
        assert dsn.startswith("postgresql://")
        assert f"@{DbConfig.HOST}:{DbConfig.PORT}/{DbConfig.NAME}" in dsn
