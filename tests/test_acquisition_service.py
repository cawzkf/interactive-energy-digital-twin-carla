"""Unit tests for the acquisition service, structured as Arrange-Act-Assert."""
from src.application.acquisition_service import AcquisitionService, make_session_id
from src.domain.dtos import RawTelemetryDto, UpdateRequestDto
from src.infra.config import MqttConfig
from tests.fakes import FakeBus


def _states():
    yield UpdateRequestDto(velocity=0.0, acceleration=2.0, dt=0.1)
    yield UpdateRequestDto(velocity=10.0, acceleration=1.0, dt=0.1)
    yield UpdateRequestDto(velocity=20.0, acceleration=0.0, dt=0.1)


class TestAcquisitionRun:
    def test_publishes_every_state_to_the_raw_topic(self):
        # Arrange
        bus = FakeBus()
        service = AcquisitionService(bus, session_id="sess-x")

        # Act
        service.run(_states())

        # Assert
        assert len(bus.published) == 3
        assert all(topic == MqttConfig.TOPIC_RAW for topic, _ in bus.published)

    def test_disconnects_after_completing(self):
        # Arrange
        bus = FakeBus()
        service = AcquisitionService(bus, session_id="sess-x")

        # Act
        service.run(_states())

        # Assert
        assert bus.connected is False

    def test_payload_is_valid_raw_telemetry(self):
        # Arrange
        bus = FakeBus()
        service = AcquisitionService(bus, session_id="sess-x")

        # Act
        service.run(_states())

        # Assert
        first = RawTelemetryDto.model_validate_json(bus.published[0][1])
        assert first.session_id == "sess-x"
        assert first.velocity == 0.0
        assert first.timestamp > 0


class TestSessionId:
    def test_has_expected_prefix_and_suffix(self):
        # Act
        session_id = make_session_id()
        # Assert
        assert session_id.startswith("sess-")
        assert len(session_id) > len("sess-")
