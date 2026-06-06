"""Unit tests for the twin-sync service, structured as Arrange-Act-Assert."""
from src.application.twin_sync_service import TwinSyncService
from src.domain.dtos import ProcessedTelemetryDto
from src.infra.config import MqttConfig
from tests.fakes import FakeBus


class _FakeTwin:
    def __init__(self):
        self.synced: list[ProcessedTelemetryDto] = []

    def sync_processed(self, sample: ProcessedTelemetryDto) -> None:
        self.synced.append(sample)


def _processed(**overrides):
    base = dict(
        session_id="s", timestamp=1.0, velocity=12.0, acceleration=0.0,
        vdc=48.0, idc=5.0, power=600.0, energy=10.0, soc=0.8,
        distance=1.0, avg_power=600.0, specific_consumption=0.0, autonomy=100.0,
    )
    base.update(overrides)
    return ProcessedTelemetryDto(**base).model_dump_json()


class TestTwinSync:
    def test_forwards_processed_sample_to_twin(self):
        # Arrange
        bus, twin = FakeBus(), _FakeTwin()
        service = TwinSyncService(bus, twin)

        # Act
        service.process_message(MqttConfig.TOPIC_PROCESSED, _processed(power=999.0))

        # Assert
        assert len(twin.synced) == 1
        assert twin.synced[0].power == 999.0

    def test_run_subscribes_to_processed_topic(self):
        # Arrange
        bus, twin = FakeBus(), _FakeTwin()

        # Act
        TwinSyncService(bus, twin).run()

        # Assert
        assert MqttConfig.TOPIC_PROCESSED in bus.subscriptions
